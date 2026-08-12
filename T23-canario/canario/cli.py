"""M-12 cli — superfície do operador e composition root.

ÚNICO módulo do sistema que escreve no terminal. O domínio emite eventos, a CLI
observa e imprime — é o que preserva a pureza do núcleo de decisão.

Instala o tratador de SIGINT que aciona `coordenador.abortar()`: num laço
monothread, é assim que o aborto do operador vira atendível (achado UX-02).
"""

from __future__ import annotations

import argparse
import signal
import sys
from typing import Sequence

from .alvo_de_implantacao import AlvoSimulado, Papel
from .configuracao import Configuracao, ConfiguracaoInvalida
from .coordenador import (
    Aquecendo,
    Concluido,
    Coordenador,
    ErroDeColeta,
    Estado,
    Evento,
    JulgamentoConcluido,
    MudouEstado,
    PesoAplicado,
)
from .relogio import RelogioVirtual
from .simulador_de_cenario import CENARIOS, SimuladorDeCenario

SIMBOLO = {
    Estado.AQUECENDO: "~",
    Estado.PROGREDINDO: ">",
    Estado.PAUSADO: "!",
    Estado.REVERTIDO: "x",
    Estado.PROMOVIDO: "+",
}


def _imprimir(evento: Evento) -> None:
    t = evento.instante
    if isinstance(evento, PesoAplicado):
        d = evento.distribuicao
        print(
            f"[{t:>4}] peso  canário {evento.peso_canario:>3}%  |  "
            f"estável {d[Papel.ESTAVEL]:>3}%  baseline {d[Papel.BASELINE]:>3}%  "
            f"canário {d[Papel.CANARIO]:>3}%"
        )
    elif isinstance(evento, Aquecendo):
        # Sem esta linha, o silêncio durante os primeiros 50 pontos seria
        # indistinguível de travamento para quem olha o terminal (achado UX-01).
        print(
            f"[{t:>4}] ~     aquecendo: {evento.metrica} com {evento.coletadas} "
            f"amostras, faltam {evento.faltam}"
        )
    elif isinstance(evento, JulgamentoConcluido):
        s = evento.score
        valor = "indefinido" if s.indefinido else f"{s.valor:.1f}"
        vereditos = "  ".join(f"{n}={v.value}" for n, v in s.vereditos.items())
        marca = "ok " if evento.aprovado else "REPROVADO"
        print(f"[{t:>4}] julga score {valor:>10}  {marca}  {vereditos}")
    elif isinstance(evento, ErroDeColeta):
        print(
            f"[{t:>4}] erro  {evento.metrica}: {evento.consecutivos} consecutivos "
            f"({evento.motivo}) — erro de coleta, NÃO falha do canário"
        )
    elif isinstance(evento, MudouEstado):
        print(
            f"[{t:>4}] {SIMBOLO[evento.para]}     {evento.de.value} → "
            f"{evento.para.value}: {evento.motivo}"
        )
    elif isinstance(evento, Concluido):
        print(f"[{t:>4}] {SIMBOLO[evento.estado]}     {evento.estado.value.upper()}")
        print(f"       motivo: {evento.motivo}")


def construir_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="canario",
        description=(
            "Coordenador de implantação canário com rollback automático por métrica. "
            "Julga o canário contra um BASELINE PAREADO (nunca contra a estável de "
            "vida longa) por comparação concorrente Mann-Whitney U."
        ),
    )
    p.add_argument(
        "cenario",
        choices=sorted(CENARIOS),
        help="cenário simulado a executar (uc1 saudável, uc2 degradado, "
        "uc3 ruído comum, uc4 coletor fora)",
    )
    p.add_argument("--semente", type=int, default=None, help="semente do RNG (padrão: a do cenário)")
    # Sem valores padrão: é o único parâmetro do sistema sem fonte
    # bibliográfica, e exigi-lo do operador é o que torna a decisão atribuível.
    p.add_argument(
        "--guarda-taxa-erro",
        type=float,
        required=True,
        help="OBRIGATÓRIO, sem fonte na literatura: taxa de erro do canário que "
        "dispara rollback imediato sem aguardar significância estatística",
    )
    p.add_argument(
        "--guarda-latencia-p99",
        type=float,
        required=True,
        help="OBRIGATÓRIO, sem fonte na literatura: latência p99 (ms) do canário "
        "que dispara rollback imediato",
    )
    p.add_argument("--limiar-score", type=float, default=100.0)
    p.add_argument("--duracao-maxima", type=int, default=400)
    return p


def main(argv: Sequence[str] | None = None) -> int:
    args = construir_parser().parse_args(argv)

    cenario = CENARIOS[args.cenario]
    if args.semente is not None:
        from dataclasses import replace

        cenario = replace(cenario, semente=args.semente)

    try:
        cfg = Configuracao(
            guarda_taxa_erro=args.guarda_taxa_erro,
            guarda_latencia_p99=args.guarda_latencia_p99,
            limiar_score=args.limiar_score,
            duracao_maxima=args.duracao_maxima,
        )
    except ConfiguracaoInvalida as e:
        print(f"configuração inválida: {e}", file=sys.stderr)
        return 2

    relogio = RelogioVirtual()
    alvo = AlvoSimulado(cfg)
    fonte = SimuladorDeCenario(cenario, relogio, alvo)
    coordenador = Coordenador(cfg, relogio, fonte, alvo)
    coordenador.assinar(_imprimir)

    print(f"cenário   : {cenario.nome}  (semente {cenario.semente})")
    print(f"decisão   : Mann-Whitney U unicaudal, alfa {cfg.alfa}, "
          f"amostra mínima {cfg.amostra_minima}, janela {cfg.tamanho_janela}")
    print(f"passos    : {list(cfg.pesos)}%  (piso da estável {cfg.piso_estavel}%)")
    print(f"tolerância: {cfg.limite_falhas} falhas, "
          f"{cfg.limite_erros_consecutivos} erros consecutivos, histerese K={cfg.histerese_k}")
    print(f"guarda    : erro >= {cfg.guarda_taxa_erro}, p99 >= {cfg.guarda_latencia_p99}ms "
          f"[SEM FONTE — decisão do operador]")
    # VAL-8: as duas fórmulas de temporização de R-07, tornadas observáveis.
    # A doc do Flagger dá `interval*(maxWeight/stepWeight)` para progressão
    # linear; com sequência explícita de pesos o análogo é `interval*n_passos`.
    promocao_minima = cfg.intervalo * len(cfg.pesos)
    rollback_por_falha = cfg.intervalo * cfg.limite_falhas
    print(f"previsão  : promoção >= {promocao_minima} tiques (intervalo×{len(cfg.pesos)} passos) | "
          f"rollback por falha = {rollback_por_falha} tiques (intervalo×limite_falhas)  [R-07]")
    print("-" * 78)

    signal.signal(signal.SIGINT, lambda *_: coordenador.abortar())

    desfecho = coordenador.executar()

    print("-" * 78)
    print(
        f"desfecho  : {desfecho.estado.value.upper()} em t={desfecho.instante_final}, "
        f"{desfecho.julgamentos} julgamentos, {desfecho.falhas} reprovados"
    )
    if desfecho.promovido:
        folga = desfecho.instante_final - promocao_minima
        print(
            f"temporização: {desfecho.instante_final} >= {promocao_minima} previsto "
            f"(+{folga} de pausas por histerese)  [R-07 conferido]"
        )
    elif desfecho.falhas >= cfg.limite_falhas:
        print(
            f"temporização: rollback em {desfecho.instante_final}, previsto "
            f"{rollback_por_falha}  [R-07 conferido]"
        )
    return 0 if desfecho.promovido else 1


if __name__ == "__main__":
    raise SystemExit(main())
