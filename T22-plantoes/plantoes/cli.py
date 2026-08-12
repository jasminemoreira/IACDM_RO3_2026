"""M-11 cli — adaptador de entrada: os 5 casos de uso + tomada de ciência.

UC-1 gerar · UC-2 consultar · UC-3 trocar · UC-4 responder · UC-5 conformidade
+ `trocas` (UX-01: sem notificações, sem este comando o destinatário nunca sabe
que precisa responder, e o fluxo de troca não tem como começar).

A orquestração vive em funções puras (`_uc_*`) chamáveis sem argparse (ARQ-01).
Mensagens citam a regra e o artigo, não o id interno (UX-02).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

from . import carregador, diagnostico, gerador_sintetico, solver_cpsat, troca as m_troca
from .avaliador import FronteiraInvalida, avaliar, derivar_fronteira
from .dominio import Contexto, EstadoEscala, EstadoTroca, Natureza
from .repositorio_json import ErroDeRepositorio, Repositorio
from dataclasses import replace


def _agora() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _limite_positivo(texto: str) -> float:
    """C-01: um limite não-positivo chegava ao solver e voltava como
    MODEL_INVALID, cuja mensagem culpa o programa — quando a culpa é do
    argumento. Recusado no parsing, com exit 2."""
    try:
        valor = float(texto)
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{texto}' não é um número")
    if valor <= 0:
        raise argparse.ArgumentTypeError(
            f"o limite de tempo deve ser maior que zero (recebi {texto})"
        )
    return valor


def _exigir_pessoa(inst, pessoa_id: str) -> None:
    """A-01: id de pessoa inexistente era silencioso — um erro de digitação
    ficava indistinguível de 'você não tem plantões'."""
    if pessoa_id and pessoa_id not in {p.id for p in inst.pessoas}:
        raise carregador.ErroDeValidacao(
            [
                f"pessoa '{pessoa_id}' não existe nesta escala. "
                "Confira o id — ele diferencia maiúsculas de minúsculas."
            ]
        )


def _ctx_de(inst) -> Contexto:
    return Contexto.sem_historico(inst)


def _contexto_com_historico(inst, repo: Repositorio, anteriores: list[str], aceitar: bool):
    escalas, ctxs = [], []
    for eid in anteriores:
        e = repo.carregar_escala(eid)
        i = carregador.carregar(Path("dados") / f"instancia_{eid}.json")
        escalas.append(e)
        ctxs.append(Contexto.sem_historico(i))
    fronteira = derivar_fronteira(escalas, ctxs, inst, aceitar_historico=aceitar)
    return Contexto(inst, fronteira)


# --------------------------------------------------------------------------
# UC-1 — gerar
# --------------------------------------------------------------------------


def _uc_gerar(args) -> int:
    repo = Repositorio(args.dados)
    try:
        inst = carregador.carregar(args.instancia)
    except carregador.ErroDeValidacao as e:
        print("A instância tem problemas de configuração:\n" + str(e), file=sys.stderr)
        return 2

    conflitos = diagnostico.analisar(inst)
    if conflitos:
        print("Não existe escala possível para esta instância:", file=sys.stderr)
        for c in conflitos[:10]:
            print(f"  - {c}", file=sys.stderr)
        if len(conflitos) > 10:
            print(f"  ... e mais {len(conflitos) - 10} conflito(s)", file=sys.stderr)
        return 3

    escala_id = args.id
    if repo.existe(args.id):
        if not args.force:
            atual = repo.carregar_bruta(args.id)
            n = len(atual.eventos)
            print(
                f"A escala '{args.id}' já existe"
                + (f" e tem {n} evento(s) registrado(s)" if n else "")
                + ".\nUse --force para gerar uma nova versão"
                + (f" (a atual, com seus {n} evento(s), será preservada)." if n
                   else " (a atual será preservada)."),
                file=sys.stderr,
            )
            return 4
        # B-01: --force NÃO sobrescreve. V(3) especifica escala nova com id
        # novo; a anterior continua existindo e imutável, e as trocas que a
        # referenciam seguem apontando para um artefato real.
        escala_id = repo.proximo_id_de_regeracao(args.id)

    try:
        ctx = (
            _contexto_com_historico(inst, repo, args.anterior, args.aceitar_historico)
            if args.anterior
            else _ctx_de(inst)
        )
    except FronteiraInvalida as e:
        print(str(e), file=sys.stderr)
        for v in e.violacoes[:5]:
            print(f"  - {v}", file=sys.stderr)
        return 5

    resultado = solver_cpsat.gerar(ctx, escala_id, limite_s=args.limite)
    if resultado.escala is None:
        print(
            f"Não foi possível gerar a escala ({resultado.status}): "
            f"{resultado.motivo}",
            file=sys.stderr,
        )
        return 3

    a = avaliar(resultado.escala, ctx)
    escala = replace(
        resultado.escala, custo=a.custo, custo_por_restricao=a.custo_por_restricao
    )
    repo.salvar_escala(escala)
    Path(args.dados).mkdir(parents=True, exist_ok=True)
    (Path(args.dados) / f"instancia_{escala_id}.json").write_text(
        Path(args.instancia).read_text(encoding="utf-8"), encoding="utf-8"
    )

    if escala_id != args.id:
        print(
            f"A escala '{args.id}' foi PRESERVADA intacta. A nova versão é "
            f"'{escala_id}'."
        )
    print(f"Escala '{escala.id}' gerada como RASCUNHO em {resultado.segundos}s.")
    print(f"  alocações: {len(escala.alocacoes)}   custo: {a.custo}")
    if a.custo_por_restricao:
        print(
            "  custo por restrição: "
            + ", ".join(f"{k}={v}" for k, v in a.custo_por_restricao.items())
        )
    rigidas = a.rigidas
    print(f"  violações rígidas: {len(rigidas)}")
    if not resultado.otimalidade_provada:
        print(
            "  ATENÇÃO: o limite de tempo foi atingido — esta é a melhor escala "
            "encontrada, mas não está provado que é a melhor possível."
        )
    print(f"Publique com: plantoes publicar --id {escala.id}")
    return 0


def _uc_publicar(args) -> int:
    repo = Repositorio(args.dados)
    bruta = repo.carregar_bruta(args.id)
    if bruta.estado_escala is EstadoEscala.PUBLICADA:
        print(f"A escala '{args.id}' já está publicada.")
        return 0
    repo.salvar_escala(replace(bruta, estado_escala=EstadoEscala.PUBLICADA))
    print(f"Escala '{args.id}' publicada. A partir de agora aceita trocas.")
    return 0


# --------------------------------------------------------------------------
# UC-2 — consultar
# --------------------------------------------------------------------------


def _uc_consultar(args) -> int:
    repo = Repositorio(args.dados)
    escala = repo.carregar_escala(args.id)
    inst = carregador.carregar(Path(args.dados) / f"instancia_{args.id}.json")
    _exigir_pessoa(inst, args.pessoa)

    linhas = []
    for aloc in escala.alocacoes:
        if args.pessoa and aloc.pessoa_id != args.pessoa:
            continue
        p = inst.plantao(aloc.plantao_id)
        t = inst.turno(p.tipo_de_turno_id)
        linhas.append((p.data, aloc.pessoa_id, t.nome, p.habilitacao_id, p.id))
    linhas.sort()

    if not linhas:
        print("Nenhum plantão para os filtros informados.")
        return 0

    print(f"Escala '{escala.id}' ({escala.estado_escala.value}) — {len(linhas)} plantão(ões)")
    print(f"{'DATA':<12} {'PESSOA':<8} {'TURNO':<14} {'HABILITAÇÃO':<12} PLANTÃO")
    for d, pes, turno, hab, pid in linhas:
        print(f"{d.isoformat():<12} {pes:<8} {turno:<14} {hab:<12} {pid}")
    return 0


# --------------------------------------------------------------------------
# UC-3 / UC-4 / trocas
# --------------------------------------------------------------------------


def _uc_trocar(args) -> int:
    repo = Repositorio(args.dados)
    escala = repo.carregar_bruta(args.id)
    inst = carregador.carregar(Path(args.dados) / f"instancia_{args.id}.json")
    _exigir_pessoa(inst, args.pessoa)
    _exigir_pessoa(inst, args.com)
    ctx = _ctx_de(inst)
    trocas = repo.listar_trocas()
    novo_id = f"t{len(trocas) + 1:03d}"
    try:
        if args.meu_plantao and args.plantao_dele:
            t = m_troca.solicitar_plantoes(
                novo_id, escala, ctx, args.pessoa, args.com,
                args.meu_plantao, args.plantao_dele, _agora(),
            )
        else:
            t = m_troca.solicitar(
                novo_id, escala, ctx, args.pessoa, args.com, _agora()
            )
    except m_troca.TrocaInvalida as e:
        print(f"Não foi possível criar a troca: {e}", file=sys.stderr)
        return 2

    repo.salvar_troca(t)
    pa = inst.plantao(t.plantao_do_solicitante_id)
    pb = inst.plantao(t.plantao_do_destinatario_id)
    print(f"Troca '{t.id}' criada e PENDENTE.")
    print(f"  {t.solicitante_id}: {pa.data.isoformat()} ({pa.id})")
    print(f"  {t.destinatario_id}: {pb.data.isoformat()} ({pb.id})")
    print(
        f"{t.destinatario_id} precisa responder com: "
        f"plantoes responder --troca {t.id} --pessoa {t.destinatario_id} --aceitar"
    )
    return 0


def _uc_responder(args) -> int:
    repo = Repositorio(args.dados)
    trocas = repo.listar_trocas()
    alvo = next((t for t in trocas if t.id == args.troca), None)
    if alvo is None:
        print(f"Troca '{args.troca}' não encontrada.", file=sys.stderr)
        return 2
    if args.pessoa != alvo.destinatario_id:
        print(
            f"A troca '{alvo.id}' é dirigida a '{alvo.destinatario_id}', "
            f"não a '{args.pessoa}'.",
            file=sys.stderr,
        )
        return 2

    escala = repo.carregar_bruta(alvo.escala_id)
    inst = carregador.carregar(Path(args.dados) / f"instancia_{alvo.escala_id}.json")
    ctx = _ctx_de(inst)
    hoje = date.fromisoformat(args.hoje) if args.hoje else date.today()

    try:
        r = m_troca.responder(
            alvo, args.aceitar, escala, ctx, args.pessoa, _agora(), hoje
        )
    except m_troca.TrocaInvalida as e:
        print(f"{e}", file=sys.stderr)
        return 2

    repo.salvar_troca(r.troca)
    if r.evento is not None:
        repo.anexar_evento(alvo.escala_id, r.evento)

    if r.aceita:
        print(f"Troca '{alvo.id}' EFETIVADA.")
        if r.delta_custo:
            sinal = "+" if r.delta_custo > 0 else ""
            print(f"  custo da escala: {sinal}{r.delta_custo}")
            for k, v in sorted((r.termos_piorados or {}).items()):
                print(f"    piorou {k}: +{v}")
        else:
            print("  custo da escala inalterado.")
        return 0

    print(f"Troca '{alvo.id}' {r.troca.estado_troca.value.upper()}.")
    print(f"  motivo: {r.motivo}")
    return 0 if r.troca.estado_troca is EstadoTroca.RECUSADA else 6


def _uc_trocas(args) -> int:
    repo = Repositorio(args.dados)
    todas = repo.listar_trocas()
    caixa = m_troca.de(todas, args.pessoa)
    if not caixa["recebidas"] and not caixa["enviadas"]:
        # A-01: `trocas` não carrega instância, então não há cadastro para
        # validar o id contra. O que dá para fazer sem inventar validação é
        # não deixar o silêncio parecer resposta.
        conhecida = any(
            args.pessoa in (t.solicitante_id, t.destinatario_id) for t in todas
        )
        print(
            f"Nenhuma troca pendente para '{args.pessoa}'."
            + ("" if conhecida else " (este id não aparece em nenhuma troca — "
               "confira se está correto)")
        )
        return 0
    if caixa["recebidas"]:
        print("AGUARDANDO SUA RESPOSTA:")
        for t in caixa["recebidas"]:
            print(
                f"  {t.id}  de {t.solicitante_id}  "
                f"({t.plantao_do_solicitante_id} ↔ {t.plantao_do_destinatario_id})"
            )
    if caixa["enviadas"]:
        print("ENVIADAS, AGUARDANDO O OUTRO:")
        for t in caixa["enviadas"]:
            print(
                f"  {t.id}  para {t.destinatario_id}  "
                f"({t.plantao_do_solicitante_id} ↔ {t.plantao_do_destinatario_id})"
            )
    return 0


def _uc_cancelar(args) -> int:
    repo = Repositorio(args.dados)
    trocas = repo.listar_trocas()
    alvo = next((t for t in trocas if t.id == args.troca), None)
    if alvo is None:
        print(f"Troca '{args.troca}' não encontrada.", file=sys.stderr)
        return 2
    try:
        repo.salvar_troca(m_troca.cancelar(alvo, args.pessoa, _agora()))
    except m_troca.TrocaInvalida as e:
        print(f"{e}", file=sys.stderr)
        return 2
    print(f"Troca '{alvo.id}' cancelada.")
    return 0


# --------------------------------------------------------------------------
# UC-5 — conformidade
# --------------------------------------------------------------------------


def _uc_conformidade(args) -> int:
    repo = Repositorio(args.dados)
    escala = repo.carregar_escala(args.id)
    inst = carregador.carregar(Path(args.dados) / f"instancia_{args.id}.json")
    _exigir_pessoa(inst, args.pessoa)
    ctx = _ctx_de(inst)
    a = avaliar(escala, ctx)

    print(f"RELATÓRIO DE CONFORMIDADE — escala '{escala.id}'")
    print(f"  período: {escala.inicio} a {escala.fim}")
    print(f"  estado: {escala.estado_escala.value}   eventos: {len(escala.eventos)}")
    print()
    rigidas, flexiveis = a.rigidas, a.flexiveis
    print(f"VIOLAÇÕES RÍGIDAS: {len(rigidas)}")
    for v in rigidas:
        print(f"  [{v.restricao_id}] {v}")
    print()
    print(f"VIOLAÇÕES FLEXÍVEIS: {len(flexiveis)}   custo total: {a.custo}")
    for k, v in a.custo_por_restricao.items():
        print(f"  {k}: {v}")
    print()
    print("DISTRIBUIÇÃO (agregada)")
    for chave, r in a.distribuicao["resumo"].items():
        print(
            f"  {chave:<16} mín {r['minimo']}  mediana {r['mediana']}  "
            f"máx {r['maximo']}  desvio {r['desvio']}"
        )
    if args.pessoa:
        d = a.distribuicao["por_pessoa"].get(args.pessoa)
        if d:
            print(f"\nSUA CARGA ({args.pessoa})")
            for k, v in d.items():
                print(f"  {k}: {v}")
    return 0 if not rigidas else 7


def _uc_gerar_dados(args) -> int:
    d = gerador_sintetico.gerar(
        n_pessoas=args.pessoas,
        n_dias=args.dias,
        semente=args.semente,
        inviavel=args.inviavel,
    )
    destino = Path(args.saida)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"Instância sintética gravada em {destino} "
        f"({args.pessoas} pessoas, {args.dias} dias, semente {args.semente}"
        + (", INVIÁVEL de propósito" if args.inviavel else "")
        + ")."
    )
    return 0


# --------------------------------------------------------------------------


def construir_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="plantoes",
        description="Distribuidor de plantões com restrições, trocas e aprovação.",
    )
    p.add_argument("--dados", default="dados", help="diretório de dados (padrão: dados)")
    sub = p.add_subparsers(dest="comando", required=True)

    g = sub.add_parser("gerar", help="UC-1: gera a escala do período")
    g.add_argument("--instancia", required=True)
    g.add_argument("--id", required=True)
    g.add_argument(
        "--limite", type=_limite_positivo, default=solver_cpsat.LIMITE_PADRAO_S
    )
    g.add_argument("--anterior", action="append", default=[],
                   help="id de escala anterior (repetível) para derivar a fronteira")
    g.add_argument("--aceitar-historico", action="store_true",
                   help="propaga a fronteira mesmo se a escala anterior tiver violações")
    g.add_argument("--force", action="store_true")
    g.set_defaults(func=_uc_gerar)

    pub = sub.add_parser("publicar", help="publica um rascunho (passa a aceitar trocas)")
    pub.add_argument("--id", required=True)
    pub.set_defaults(func=_uc_publicar)

    c = sub.add_parser("consultar", help="UC-2: mostra a escala vigente")
    c.add_argument("--id", required=True)
    c.add_argument("--pessoa")
    c.set_defaults(func=_uc_consultar)

    t = sub.add_parser("trocar", help="UC-3: solicita troca com um par")
    t.add_argument("--id", required=True, help="id da escala")
    t.add_argument("--pessoa", required=True, help="quem solicita")
    t.add_argument("--com", required=True, help="com quem")
    t.add_argument("--meu-plantao")
    t.add_argument("--plantao-dele")
    t.set_defaults(func=_uc_trocar)

    r = sub.add_parser("responder", help="UC-4: aceita ou recusa uma troca")
    r.add_argument("--troca", required=True)
    r.add_argument("--pessoa", required=True)
    grupo = r.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--aceitar", action="store_true")
    grupo.add_argument("--recusar", dest="aceitar", action="store_false")
    r.add_argument("--hoje", help="data de referência (AAAA-MM-DD), para teste")
    r.set_defaults(func=_uc_responder)

    lt = sub.add_parser("trocas", help="lista trocas pendentes recebidas e enviadas")
    lt.add_argument("--pessoa", required=True)
    lt.set_defaults(func=_uc_trocas)

    cc = sub.add_parser("cancelar", help="cancela uma troca que você solicitou")
    cc.add_argument("--troca", required=True)
    cc.add_argument("--pessoa", required=True)
    cc.set_defaults(func=_uc_cancelar)

    k = sub.add_parser("conformidade", help="UC-5: relatório de conformidade")
    k.add_argument("--id", required=True)
    k.add_argument("--pessoa", help="detalha a carga desta pessoa")
    k.set_defaults(func=_uc_conformidade)

    gd = sub.add_parser("gerar-dados", help="gera instância sintética reprodutível")
    gd.add_argument("--saida", required=True)
    gd.add_argument("--pessoas", type=int, default=30)
    gd.add_argument("--dias", type=int, default=30)
    gd.add_argument("--semente", type=int, default=0)
    gd.add_argument("--inviavel", action="store_true")
    gd.set_defaults(func=_uc_gerar_dados)

    return p


def main(argv=None) -> int:
    args = construir_parser().parse_args(argv)
    try:
        return args.func(args)
    except (ErroDeRepositorio, carregador.ErroDeValidacao) as e:
        print(f"{e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
