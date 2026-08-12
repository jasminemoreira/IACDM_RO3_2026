"""M-03/M-04 — precificação, precedência, trace e invariantes.

Origem dos valores esperados: `specs/datasets/casos-armadilha.md` §E.
"""

from datetime import date
from decimal import Decimal

import pytest

from app.dominio.dinheiro import Dinheiro
from app.dominio.modelo_dominio import (
    ESCOPO_GERAL,
    ConjuntoDeRegras,
    DescontoPct,
    EmpateInsoluvel,
    Faixa,
    MotivoCodigo,
    PrecoUnitario,
    Produto,
    Regra,
    ResultadoTrace,
    Vigencia,
)
from app.dominio.motor_precificacao import precificar

D = date(2026, 8, 12)
VIG = Vigencia(date(2026, 1, 1))


def regra(id_, escopo, minimo, maximo, valor, prio=0, vigencia=VIG, pct=None):
    efeito = DescontoPct(Decimal(pct)) if pct else PrecoUnitario(Dinheiro.de_texto(valor))
    return Regra(id_, escopo, Faixa(minimo, maximo), efeito, prio, vigencia)


PROD_1003 = Produto("SKU-1003", "Papel A4", Dinheiro.de_texto("24,90"))
PROD_1001 = Produto("SKU-1001", "Caneta", Dinheiro.de_texto("2,50"))
PROD_1009 = Produto("SKU-1009", "Pasta", Dinheiro.de_texto("3,20"))

REGRAS_1003 = [
    regra("R-A", "SKU-1003", 1, 4, "24,90"),
    regra("R-B", "SKU-1003", 5, 19, "23,40"),
    regra("R-C", "SKU-1003", 20, 99, "21,90"),
    regra("R-D", "SKU-1003", 100, None, "19,90"),
]


def test_p01_trace_exaustivo():
    """P-01: qtd 50 → 21,90 e as faixas 1–4, 5–19 e 100+ listadas."""
    p = precificar(ConjuntoDeRegras(REGRAS_1003), PROD_1003, 50, D)
    assert p.preco_unitario.iso() == "21.90"
    assert p.total.iso() == "1095.00"
    assert len(p.trace.vereditos) == 4  # I-3: TODAS aparecem
    assert p.trace.vencedora == "R-C"
    perdedoras = {v.regra_id: v.codigo for v in p.trace.vereditos if v.regra_id != "R-C"}
    assert set(perdedoras) == {"R-A", "R-B", "R-D"}
    assert all(c is MotivoCodigo.FORA_DA_FAIXA for c in perdedoras.values())


@pytest.mark.parametrize("qtd,esperado", [(19, "23.40"), (20, "21.90")])
def test_p02_p03_bordas_faixa_fechada(qtd, esperado):
    """P-02/P-03 + A-11: intervalo FECHADO dos dois lados, sem off-by-one."""
    p = precificar(ConjuntoDeRegras(REGRAS_1003), PROD_1003, qtd, D)
    assert p.preco_unitario.iso() == esperado


def test_p05_lacuna_cai_no_preco_base():
    """P-05 + I-2: ausência de regra não é erro; o trace declara."""
    regras = [regra("R-1", "SKU-1009", 1, 9, "3,20"), regra("R-2", "SKU-1009", 20, 99, "2,75")]
    p = precificar(ConjuntoDeRegras(regras), PROD_1009, 15, D)
    assert p.preco_unitario.iso() == "3.20"
    assert p.trace.resultado is ResultadoTrace.PRECO_BASE
    assert p.trace.vencedora is None
    assert len(p.trace.vereditos) == 2  # I-3 vale também aqui


def test_p07_derrota_por_prioridade():
    """P-07: regra `*` prio 50 vence a de SKU prio 0 → 2,50 − 10% = 2,25."""
    regras = [
        regra("R-SKU", "SKU-1001", 200, None, "1,85", prio=0),
        regra("R-GERAL", ESCOPO_GERAL, 500, None, None, prio=50, pct=10),
    ]
    p = precificar(ConjuntoDeRegras(regras), PROD_1001, 600, D)
    assert p.preco_unitario.iso() == "2.25"
    assert p.total.iso() == "1350.00"
    assert p.trace.vencedora == "R-GERAL"
    derrotada = next(v for v in p.trace.vereditos if v.regra_id == "R-SKU")
    # Casou E perdeu — são coisas diferentes, e é isso que responde
    # "por que NÃO ganhei o desconto X".
    assert derrotada.codigo is MotivoCodigo.PERDEU_POR_PRIORIDADE


def test_p08_desempate_por_especificidade():
    """P-08: prioridades iguais → a regra de SKU vence a geral."""
    regras = [
        regra("R-SKU", "SKU-1001", 200, None, "1,85", prio=50),
        regra("R-GERAL", ESCOPO_GERAL, 500, None, None, prio=50, pct=10),
    ]
    p = precificar(ConjuntoDeRegras(regras), PROD_1001, 600, D)
    assert p.preco_unitario.iso() == "1.85"
    assert p.trace.vencedora == "R-SKU"
    derrotada = next(v for v in p.trace.vereditos if v.regra_id == "R-GERAL")
    assert derrotada.codigo is MotivoCodigo.PERDEU_POR_ESPECIFICIDADE


def test_p10_vigencia_exclui_regra():
    """P-10 + CS-4: regra fora de vigência não casa; cai no preço base."""
    futura = Vigencia(date(2026, 3, 1))
    regras = [regra("R-C", "SKU-1003", 20, 99, "21,90", vigencia=futura)]
    p = precificar(ConjuntoDeRegras(regras), PROD_1003, 50, date(2026, 2, 10))
    assert p.preco_unitario.iso() == "24.90"
    assert p.trace.vereditos[0].codigo is MotivoCodigo.FORA_DA_VIGENCIA


def test_i6_empate_insoluvel_falha_ruidosamente():
    """I-6: nunca escolher em silêncio — o defeito é do validador."""
    regras = [
        regra("R-X", "SKU-1003", 1, 100, "10,00", prio=0),
        regra("R-Y", "SKU-1003", 1, 100, "20,00", prio=0),
    ]
    with pytest.raises(EmpateInsoluvel):
        precificar(ConjuntoDeRegras(regras), PROD_1003, 50, D)


def test_i1_determinismo():
    """I-1: mesma entrada + mesmas regras → mesmo preço e mesmo trace."""
    c = ConjuntoDeRegras(REGRAS_1003)
    ref = precificar(c, PROD_1003, 50, D)
    for _ in range(100):
        p = precificar(c, PROD_1003, 50, D)
        assert p.preco_unitario == ref.preco_unitario
        assert [v.codigo for v in p.trace.vereditos] == [v.codigo for v in ref.trace.vereditos]


def test_a10_modelo_volume_nao_graduated():
    """A-10: a faixa atingida vale para TODA a quantidade.

    100 un na faixa 50–199 a R$2,10 → R$210,00.
    Se fosse `graduated` daria R$221,60 (9×2,50 + 40×2,30 + 51×2,10).
    """
    regras = [
        regra("R-1", "SKU-1001", 1, 9, "2,50"),
        regra("R-2", "SKU-1001", 10, 49, "2,30"),
        regra("R-3", "SKU-1001", 50, 199, "2,10"),
    ]
    p = precificar(ConjuntoDeRegras(regras), PROD_1001, 100, D)
    assert p.total.iso() == "210.00"
    assert p.total.iso() != "221.60"


def test_a04_motor_nao_le_o_relogio():
    """A-04, endurecida pelo operador na Fase 1.

    O módulo do motor não pode conter chamada a relógio. Este teste falha se
    alguém introduzir `datetime.now()` no núcleo — que foi a incoerência
    encontrada pelo micro-check S7 entre o contrato `-> Decisao` e A-04.
    """
    import inspect

    from app.dominio import motor_precificacao, resolvedor_precedencia

    for modulo in (motor_precificacao, resolvedor_precedencia):
        fonte = inspect.getsource(modulo)
        assert "datetime.now" not in fonte
        assert "date.today" not in fonte


def test_cs2_nenhum_trace_vazio_e_todo_veredito_tem_codigo():
    """CS-2: nenhuma resposta sem trace; nenhuma candidata sem motivo."""
    for qtd in (1, 5, 19, 20, 50, 99, 100, 500):
        p = precificar(ConjuntoDeRegras(REGRAS_1003), PROD_1003, qtd, D)
        assert p.trace.vereditos, f"trace vazio em qtd={qtd}"
        for v in p.trace.vereditos:
            assert isinstance(v.codigo, MotivoCodigo)
            assert v.detalhe.get("faixa")
