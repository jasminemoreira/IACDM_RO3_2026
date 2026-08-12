"""M-04 avaliador — custo, violações, distribuição e derivação de fronteira.

Três responsabilidades coesas: todas são "percorrer a escala por pessoa"
(ARQ-07 resolvido em V(3) tirando daqui a fábrica de Contexto, que virou
construtor do próprio `Contexto` no domínio).

Cliente do catálogo, não dono das regras: chama `restricoes_legais` e
`restricoes_modelo` no modo *verificar*. INV-1 diz que o resultado sobre uma
escala recém-gerada deve ser zero violações rígidas.
"""

from __future__ import annotations

from datetime import timedelta
from statistics import median, pstdev

from . import restricoes_legais, restricoes_modelo
from .dominio import (
    Avaliacao,
    Contexto,
    Escala,
    Fronteira,
    Instancia,
    Natureza,
)


class FronteiraInvalida(Exception):
    """A escala de origem tem violações rígidas: propagar seu estado espalharia
    o erro para os meses seguintes sem sinal (CTL-01). Contornável com
    consentimento explícito (ASS-05)."""

    def __init__(self, escala_id: str, violacoes):
        self.escala_id = escala_id
        self.violacoes = violacoes
        super().__init__(
            f"a escala '{escala_id}' tem {len(violacoes)} violação(ões) rígida(s); "
            "propagar sua fronteira espalharia o erro. Use --aceitar-historico "
            "para prosseguir registrando a decisão."
        )


def avaliar(escala: Escala, ctx: Contexto) -> Avaliacao:
    """Verifica TODAS as restrições sobre uma escala concreta."""
    violacoes = tuple(
        restricoes_legais.verificar(escala, ctx) + restricoes_modelo.verificar(escala, ctx)
    )
    custo_por_restricao: dict[str, int] = {}
    for v in violacoes:
        if v.natureza is Natureza.FLEXIVEL:
            custo_por_restricao[v.restricao_id] = (
                custo_por_restricao.get(v.restricao_id, 0) + v.peso
            )
    custo = sum(custo_por_restricao.values())
    return Avaliacao(
        violacoes=violacoes,
        custo=custo,
        custo_por_restricao=dict(sorted(custo_por_restricao.items())),
        distribuicao=distribuicao(escala, ctx),
    )


def distribuicao(escala: Escala, ctx: Contexto) -> dict:
    """Carga por pessoa (ETI-03), em forma AGREGADA.

    ETI-04: o relatório expõe estatísticas, não uma lista nominal da carga de
    todo mundo. O detalhe nominal só aparece quando a CLI recebe --pessoa.
    """
    inst = ctx.instancia
    por_pessoa: dict[str, dict] = {}
    for pessoa in sorted(inst.pessoas, key=lambda p: p.id):
        pids = escala.plantoes_de(pessoa.id)
        plantoes = [inst.plantao(p) for p in pids]
        por_pessoa[pessoa.id] = {
            "total": len(plantoes),
            "noturnos": sum(
                1 for p in plantoes if inst.turno(p.tipo_de_turno_id).noturno
            ),
            "fins_de_semana": len({p.data for p in plantoes if p.fim_de_semana}),
        }

    resumo = {}
    for chave in ("total", "noturnos", "fins_de_semana"):
        valores = [d[chave] for d in por_pessoa.values()] or [0]
        resumo[chave] = {
            "minimo": min(valores),
            "mediana": round(median(valores), 2),
            "maximo": max(valores),
            "desvio": round(pstdev(valores), 2) if len(valores) > 1 else 0.0,
        }
    return {"resumo": resumo, "por_pessoa": por_pessoa}


def derivar_fronteira(
    escalas_anteriores: list[Escala],
    ctx_anteriores: list[Contexto],
    instancia: Instancia,
    aceitar_historico: bool = False,
) -> dict[str, Fronteira]:
    """Deriva os contadores de fronteira das escalas anteriores.

    - Valida cada escala de origem antes de propagar (CTL-01). Sem a validação,
      um defeito no mês M-1 se propagaria para M, M+1... sem sinal.
    - A janela é a lista recebida, dimensionada pelo `horizonte_meses` do
      contrato (CTL-03) — o limite vem do dado, não de um número inventado.
    - Lista vazia produz fronteiras vazias EXPLÍCITAS: ausência de período
      anterior é o caso correto do primeiro mês, distinto de "não encontrei o
      arquivo" (ASS-02), que o repositório sinaliza como erro.
    """
    if not escalas_anteriores:
        return {p.id: Fronteira() for p in instancia.pessoas}

    for escala, ctx in zip(escalas_anteriores, ctx_anteriores):
        rigidas = [
            v for v in avaliar(escala, ctx).violacoes if v.natureza is Natureza.RIGIDA
        ]
        if rigidas and not aceitar_historico:
            raise FronteiraInvalida(escala.id, rigidas)

    fronteiras: dict[str, Fronteira] = {}
    ultima = escalas_anteriores[-1]
    ctx_ultima = ctx_anteriores[-1]
    inst_ultima = ctx_ultima.instancia

    contratos = {c.id: c for c in instancia.contratos}

    for pessoa in instancia.pessoas:
        # A fronteira carrega DUAS coisas com regras diferentes.
        #
        # 1) Contadores ACUMULADOS (S6/S7): no INRC-II eles acumulam DENTRO do
        #    horizonte de planejamento e são avaliados no fim dele — não
        #    atravessam horizontes. Com horizonte_meses=1, cada mês é um
        #    horizonte próprio e o acumulado é zero. Somar o mês anterior aqui
        #    faz a pessoa "começar" o mês já no teto contratual.
        horizonte = contratos[pessoa.contrato_id].horizonte_meses
        dentro_do_horizonte = (
            escalas_anteriores[-(horizonte - 1) :] if horizonte > 1 else []
        )
        ctxs_horizonte = (
            ctx_anteriores[-(horizonte - 1) :] if horizonte > 1 else []
        )
        total = 0
        fds: set = set()
        for escala, ctx in zip(dentro_do_horizonte, ctxs_horizonte):
            pids = escala.plantoes_de(pessoa.id)
            total += len(pids)
            for pid in pids:
                pl = ctx.instancia.plantao(pid)
                if pl.fim_de_semana:
                    fds.add(pl.data)

        # 2) Estado de BORDA (último turno, sequências em curso): vem SEMPRE da
        #    última escala, independentemente do horizonte — é o que impede
        #    violar interjornada e 12x36 na virada.

        # estado de borda: só a última escala importa
        datas = sorted(
            inst_ultima.plantao(pid).data for pid in ultima.plantoes_de(pessoa.id)
        )
        ultimo_turno = None
        consecutivos = 0
        folgas = 0
        if datas:
            ultimo_dia = inst_ultima.fim
            if datas[-1] == ultimo_dia:
                ultimo_turno = inst_ultima.turno(
                    next(
                        inst_ultima.plantao(pid).tipo_de_turno_id
                        for pid in ultima.plantoes_de(pessoa.id)
                        if inst_ultima.plantao(pid).data == datas[-1]
                    )
                ).id
                # quantos dias seguidos até o fim do período
                dia = ultimo_dia
                trabalhados = set(datas)
                while dia in trabalhados:
                    consecutivos += 1
                    dia -= timedelta(days=1)
            else:
                folgas = (inst_ultima.fim - datas[-1]).days

        fronteiras[pessoa.id] = Fronteira(
            ultimo_tipo_de_turno_id=ultimo_turno,
            dias_trabalhados_consecutivos=consecutivos,
            folgas_consecutivas=folgas,
            total_plantoes=total,
            fins_de_semana_trabalhados=len(fds),
        )
    return fronteiras
