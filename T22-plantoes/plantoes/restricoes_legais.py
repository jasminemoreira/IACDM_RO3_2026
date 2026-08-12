"""M-02 restricoes-legais — restrições de origem legal (CLT).

Fonte de TODO parâmetro numérico deste módulo: specs/references/clt-jornada.md,
transcrito literalmente do planalto.gov.br. Nenhum número inventado (S1).

INV-2: restrição de origem legal é SEMPRE rígida e NUNCA tem peso.

A natureza de cada regra depende do REGIME DO CONTRATO da pessoa — não é
propriedade global do sistema (art. 59-A é exceção expressa ao art. 59, e seu
parágrafo único absorve o repouso semanal). Aplicar as regras cumulativamente
sobre um contrato 12x36 rejeita escalas legais, e o sintoma parece "falta de
gente".
"""

from __future__ import annotations

from datetime import timedelta

from .dominio import (
    Contexto,
    Escala,
    Natureza,
    Origem,
    Pessoa,
    Regime,
    Violacao,
)

# Parâmetros legais — cada um com artigo citado (specs/references/clt-jornada.md)
HORAS_INTERJORNADA = 11  # L1, CLT art. 66
HORAS_REPOUSO_SEMANAL = 24  # L2, CLT art. 67
HORAS_DESCANSO_12X36 = 36  # L3, CLT art. 59-A (tolerância zero, CIE-04)
HORAS_TRABALHO_12X36 = 12  # L3, CLT art. 59-A
HORAS_JORNADA_MAXIMA = 10  # L4, CLT art. 59 (8h + 2h extras)

FONTE = {
    "L1": "CLT art. 66",
    "L2": "CLT art. 67",
    "L3": "CLT art. 59-A",
    "L4": "CLT art. 59",
}


def se_aplica(id_regra: str, regime: Regime) -> bool:
    """Quais regras legais valem sob cada regime.

    Sob 12x36 (art. 59-A): L1 é satisfeita por construção (as 36h contêm as
    11h); L2 é absorvida pela remuneração mensal pactuada (§ único); L4 é
    inaplicável (o caput é exceção expressa ao art. 59). Sobra L3, que passa a
    ser a regra fiscalizada — e que em V(1)/V(2) não era verificada por
    ninguém (REG-01).
    """
    if regime is Regime.DOZE_TRINTA_SEIS:
        return id_regra == "L3"
    return id_regra in ("L1", "L2", "L4")


def _viol(id_regra: str, descricao: str, pessoa_id: str, data=None) -> Violacao:
    return Violacao(
        restricao_id=id_regra,
        origem=Origem.LEGAL,
        natureza=Natureza.RIGIDA,  # INV-2
        fonte=FONTE[id_regra],
        descricao=descricao,
        peso=0,  # INV-2: legal nunca tem peso
        pessoa_id=pessoa_id,
        data=data,
    )


# --------------------------------------------------------------------------
# Modo GERAÇÃO — aplicar como restrições CP-SAT
# --------------------------------------------------------------------------


def pares_proibidos(ctx: Contexto) -> set[tuple[str, str]]:
    """L1 compilada em sucessões proibidas.

    Como os turnos têm horário fixo (A1), o intervalo entre um turno no dia d e
    outro no dia d+1 é conhecido na construção do modelo. Vira uma tabela de
    pares, e usa o mesmo mecanismo de H3 — sem aritmética temporal no solver.
    """
    turnos = ctx.instancia.tipos_de_turno
    return {
        (a.id, b.id)
        for a in turnos
        for b in turnos
        if a.intervalo_ate(b) < HORAS_INTERJORNADA
    }


def aplicar(modelo, x, ctx: Contexto) -> None:
    """Aplica as restrições legais ao modelo CP-SAT.

    `x` é o dicionário {(pessoa_id, plantao_id): BoolVar}.
    """
    inst = ctx.instancia
    proibidos = pares_proibidos(ctx)
    dias = inst.dias

    for pessoa in sorted(inst.pessoas, key=lambda p: p.id):
        regime = inst.contrato_de(pessoa).regime

        # ---- L1: sucessões proibidas por interjornada (art. 66) ----
        if se_aplica("L1", regime):
            for d, prox in zip(dias, dias[1:]):
                for p1 in inst.plantoes_do_dia(d):
                    for p2 in inst.plantoes_do_dia(prox):
                        if (p1.tipo_de_turno_id, p2.tipo_de_turno_id) in proibidos:
                            v1 = x.get((pessoa.id, p1.id))
                            v2 = x.get((pessoa.id, p2.id))
                            if v1 is not None and v2 is not None:
                                modelo.Add(v1 + v2 <= 1)

            # fronteira: o último turno do período anterior também restringe o dia 0
            fr = ctx.fronteira_de(pessoa.id)
            if fr.ultimo_tipo_de_turno_id and dias:
                for p0 in inst.plantoes_do_dia(dias[0]):
                    if (fr.ultimo_tipo_de_turno_id, p0.tipo_de_turno_id) in proibidos:
                        v = x.get((pessoa.id, p0.id))
                        if v is not None:
                            modelo.Add(v == 0)

        # ---- L2: repouso semanal de 24h (art. 67) ----
        # Janela deslizante de 7 dias com ao menos 1 dia inteiro livre.
        if se_aplica("L2", regime):
            for i in range(0, max(0, len(dias) - 6)):
                janela = dias[i : i + 7]
                vars_janela = [
                    x[(pessoa.id, p.id)]
                    for d in janela
                    for p in inst.plantoes_do_dia(d)
                    if (pessoa.id, p.id) in x
                ]
                if vars_janela:
                    modelo.Add(sum(vars_janela) <= len(janela) - 1)

        # ---- L3: regime 12x36 (art. 59-A) ----
        # Trabalhou no dia d => não trabalha em d+1 (36h de descanso).
        if se_aplica("L3", regime):
            for d, prox in zip(dias, dias[1:]):
                hoje = [
                    x[(pessoa.id, p.id)]
                    for p in inst.plantoes_do_dia(d)
                    if (pessoa.id, p.id) in x
                ]
                amanha = [
                    x[(pessoa.id, p.id)]
                    for p in inst.plantoes_do_dia(prox)
                    if (pessoa.id, p.id) in x
                ]
                for a in hoje:
                    for b in amanha:
                        modelo.Add(a + b <= 1)
            fr = ctx.fronteira_de(pessoa.id)
            if fr.ultimo_tipo_de_turno_id and dias:
                # trabalhou no último dia do período anterior => folga no dia 0
                for p0 in inst.plantoes_do_dia(dias[0]):
                    v = x.get((pessoa.id, p0.id))
                    if v is not None:
                        modelo.Add(v == 0)


# --------------------------------------------------------------------------
# Modo VERIFICAÇÃO — mesma declaração, sobre escala concreta
# --------------------------------------------------------------------------


def _dias_trabalhados(escala: Escala, ctx: Contexto, pessoa: Pessoa) -> dict:
    """{data: TipoDeTurno} do que a pessoa trabalha na escala."""
    inst = ctx.instancia
    resultado = {}
    for pid in escala.plantoes_de(pessoa.id):
        pl = inst.plantao(pid)
        resultado[pl.data] = inst.turno(pl.tipo_de_turno_id)
    return resultado


def verificar(escala: Escala, ctx: Contexto) -> list[Violacao]:
    inst = ctx.instancia
    violacoes: list[Violacao] = []
    proibidos = pares_proibidos(ctx)

    for pessoa in sorted(inst.pessoas, key=lambda p: p.id):
        regime = inst.contrato_de(pessoa).regime
        trabalhados = _dias_trabalhados(escala, ctx, pessoa)
        fr = ctx.fronteira_de(pessoa.id)

        # ---- L1 ----
        if se_aplica("L1", regime):
            for d, turno in sorted(trabalhados.items()):
                anterior = trabalhados.get(d - timedelta(days=1))
                if anterior and (anterior.id, turno.id) in proibidos:
                    horas = anterior.intervalo_ate(turno)
                    violacoes.append(
                        _viol(
                            "L1",
                            f"descanso de apenas {horas:g}h entre "
                            f"{(d - timedelta(days=1)).isoformat()} e "
                            f"{d.isoformat()}; a lei exige "
                            f"{HORAS_INTERJORNADA}h",
                            pessoa.id,
                            d,
                        )
                    )
            # fronteira com o período anterior
            if fr.ultimo_tipo_de_turno_id and inst.dias:
                d0 = inst.dias[0]
                turno0 = trabalhados.get(d0)
                if turno0 and (fr.ultimo_tipo_de_turno_id, turno0.id) in proibidos:
                    violacoes.append(
                        _viol(
                            "L1",
                            "descanso insuficiente na virada do período anterior "
                            f"para {d0.isoformat()}; a lei exige "
                            f"{HORAS_INTERJORNADA}h",
                            pessoa.id,
                            d0,
                        )
                    )

        # ---- L2 ----
        if se_aplica("L2", regime):
            dias = inst.dias
            for i in range(0, max(0, len(dias) - 6)):
                janela = dias[i : i + 7]
                if all(d in trabalhados for d in janela):
                    violacoes.append(
                        _viol(
                            "L2",
                            f"7 dias seguidos de trabalho a partir de "
                            f"{janela[0].isoformat()} sem "
                            f"{HORAS_REPOUSO_SEMANAL}h de repouso semanal",
                            pessoa.id,
                            janela[0],
                        )
                    )

        # ---- L3 ----
        if se_aplica("L3", regime):
            for d, turno in sorted(trabalhados.items()):
                if turno.duracao_horas != HORAS_TRABALHO_12X36:
                    violacoes.append(
                        _viol(
                            "L3",
                            f"contrato 12x36 alocado em turno de "
                            f"{turno.duracao_horas:g}h",
                            pessoa.id,
                            d,
                        )
                    )
                seguinte = trabalhados.get(d + timedelta(days=1))
                if seguinte:
                    descanso = turno.intervalo_ate(seguinte)
                    if descanso < HORAS_DESCANSO_12X36:
                        violacoes.append(
                            _viol(
                                "L3",
                                f"descanso de {descanso:g}h após o plantão de "
                                f"{d.isoformat()}; o regime 12x36 exige "
                                f"{HORAS_DESCANSO_12X36}h ininterruptas",
                                pessoa.id,
                                d,
                            )
                        )

    return violacoes


def validar_configuracao(inst) -> list[str]:
    """L4 é validação de CONFIGURAÇÃO, não restrição de alocação.

    Um plantão de 12h num contrato de regime comum é ilegal independentemente
    de quem for alocado — a ilegalidade está no cadastro. Restringir isso no
    solver produziria INFEASIBLE mudo.
    """
    erros: list[str] = []
    duracoes = {t.id: t.duracao_horas for t in inst.tipos_de_turno}
    turnos_usados = {p.tipo_de_turno_id for p in inst.plantoes}
    tem_regime_comum = any(c.regime is Regime.COMUM for c in inst.contratos)
    if tem_regime_comum:
        for tid in sorted(turnos_usados):
            if duracoes[tid] > HORAS_JORNADA_MAXIMA:
                erros.append(
                    f"tipo de turno '{tid}' dura {duracoes[tid]:g}h; contratos de "
                    f"regime comum admitem no máximo {HORAS_JORNADA_MAXIMA}h "
                    f"(8h + 2h extras, {FONTE['L4']}). Use regime 12x36 "
                    f"({FONTE['L3']}) ou reduza o turno."
                )
    return erros
