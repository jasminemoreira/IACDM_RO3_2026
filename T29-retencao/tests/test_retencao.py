"""Testes da política de retenção e do downsampling, contra as SPECS.

Fontes: specs/technical/politica-retencao.md (R6 divisibilidade, R7 xff, R9 tiers),
specs/validation/criterios-aceitacao.md (CA-3 e as invariantes I3, I6, I7).
"""

import pytest

from tsz.downsampler import aggregate
from tsz.retention import default_tiers, plan, validate
from tsz.series import Point, SeriesError, TierSpec


def tier(spp, ret, agg="average", xff=0.5, min_age=0):
    return TierSpec(spp, ret, agg, xff, min_age)


# --- CA-3 / I3: divisibilidade (R6) ---------------------------------------------------


def test_ca3_divisibilidade_valida():
    """R6: 300/60 = 5. O default do projeto.

    O default é de DOIS tiers de propósito: um terceiro nível de 1 h seria derivado do de
    5 min e, com `average` nos dois, violaria D2. Um default que a própria `validate()`
    recusaria seria pior que um default modesto.
    """
    tiers = default_tiers()
    assert len(tiers) == 2
    validate(tiers)


def test_default_tiers_passa_pela_propria_validacao():
    """O default não pode violar as regras que o módulo ao lado impõe."""
    validate(default_tiers())
    validate(default_tiers(raw_seconds_per_point=1))
    validate(default_tiers(raw_seconds_per_point=10))


def test_tres_niveis_exigem_agregacao_associativa():
    """A alternativa documentada para três níveis: intermediário associativo."""
    validate(
        [
            tier(60, 15 * 86400, "average"),
            tier(300, 90 * 86400, "max", min_age=40 * 3600),
            tier(3600, 730 * 86400, "max", min_age=10 * 86400),
        ]
    )


def test_ca3_divisibilidade_invalida_180_600():
    """O exemplo LITERAL de R6: 180s não pode preceder 600s (600/180 = 3,33)."""
    with pytest.raises(SeriesError, match="3.33|divisível"):
        validate([tier(180, 15 * 86400), tier(600, 90 * 86400)])


def test_ca3_ordem_dos_tiers_do_fino_para_o_grosseiro():
    """R6: dos de maior resolução para os de menor. O inverso é erro."""
    with pytest.raises(SeriesError, match="grosseiro|MAIOR"):
        validate([tier(300, 90 * 86400), tier(60, 15 * 86400)])


# --- I7: perda silenciosa (R9) --------------------------------------------------------


def test_i7_retencao_menor_que_idade_rejeitada():
    """R9: se a origem não sobrevive até a idade de derivação, o dado é apagado antes."""
    with pytest.raises(SeriesError, match="perda\\s+silenciosa|I7"):
        validate(
            [
                tier(60, 3600),  # cru retém 1h
                tier(300, 90 * 86400, min_age=40 * 3600),  # exige 40h + 5min
            ]
        )


def test_i7_limite_exato_e_aceito():
    """A fronteira: retenção == min_age + resolução do destino é suficiente."""
    validate([tier(60, 40 * 3600 + 300), tier(300, 90 * 86400, min_age=40 * 3600)])


def test_i7_um_segundo_abaixo_do_limite_e_rejeitado():
    with pytest.raises(SeriesError, match="perda\\s+silenciosa|I7"):
        validate([tier(60, 40 * 3600 + 299), tier(300, 90 * 86400, min_age=40 * 3600)])


# --- D2: `average` não é associativo sob re-agregação ---------------------------------


def test_d2_average_encadeado_rejeitado():
    """`average` de `average` não é o `average` do conjunto. Só do cru."""
    with pytest.raises(SeriesError, match="associativa"):
        validate(
            [
                tier(60, 86400 * 20, "average"),
                tier(300, 86400 * 90, "average", min_age=3600),
                tier(3600, 86400 * 730, "average", min_age=7200),
            ]
        )


@pytest.mark.parametrize("agg", ["min", "max", "sum", "last"])
def test_d2_metodos_associativos_podem_ser_encadeados(agg):
    """min/max/sum/last SÃO associativos — a cascata é legítima com eles."""
    validate(
        [
            tier(60, 86400 * 20, agg),
            tier(300, 86400 * 90, agg, min_age=3600),
            tier(3600, 86400 * 730, agg, min_age=7200),
        ]
    )


# --- CA-3 / I6: xFilesFactor ----------------------------------------------------------


def pontos(n, base=1786464000):
    return [Point(base + i, 10.0) for i in range(n)]


def test_ca3_xff_emite_acima_do_limiar():
    """5/5 = 100% e 3/5 = 60%, ambos ≥ 0,5 ⇒ emitem."""
    assert len(list(aggregate(iter(pontos(5)), 1, 5, "average", 0.5))) == 1
    assert len(list(aggregate(iter(pontos(3)), 1, 5, "average", 0.5))) == 1


def test_ca3_xff_suprime_abaixo_do_limiar():
    """2/5 = 40% < 0,5 ⇒ NÃO emite. 'Indefinido' significa ausente, não nulo."""
    assert list(aggregate(iter(pontos(2)), 1, 5, "average", 0.5)) == []


def test_ca3_xff_no_limiar_exato_emite():
    """R6: 'se MAIS DA METADE for indefinido' ⇒ o limiar é inclusivo."""
    # 3/6 = 50% com xff=0.5
    assert len(list(aggregate(iter(pontos(3)), 1, 6, "average", 0.5))) == 1


def test_ca3_xff_zero_emite_sempre():
    assert len(list(aggregate(iter(pontos(1)), 1, 100, "average", 0.0))) == 1


def test_ca3_xff_um_exige_janela_completa():
    assert list(aggregate(iter(pontos(99)), 1, 100, "average", 1.0)) == []
    assert len(list(aggregate(iter(pontos(100)), 1, 100, "average", 1.0))) == 1


# --- os 5 métodos de agregação de R6 --------------------------------------------------


@pytest.mark.parametrize(
    "fn,esperado",
    [("average", 3.0), ("sum", 15.0), ("min", 1.0), ("max", 5.0), ("last", 5.0)],
)
def test_r6_cinco_metodos_de_agregacao(fn, esperado):
    pts = [Point(1786464000 + i, float(i + 1)) for i in range(5)]
    (out,) = list(aggregate(iter(pts), 1, 5, fn, 0.5))
    assert out.value == esperado


def test_agregacao_desconhecida_e_erro():
    with pytest.raises(SeriesError, match="desconhecida"):
        list(aggregate(iter(pontos(5)), 1, 5, "median", 0.5))


def test_agregado_e_alinhado_a_resolucao_do_destino():
    """Os pontos derivados são alinhados por construção — é o que F1 exige."""
    pts = [Point(1786464000 + i, 1.0) for i in range(20)]
    out = list(aggregate(iter(pts), 1, 5, "average", 0.5))
    assert all(p.ts % 5 == 0 for p in out)


# --- plano de retenção: idempotência e bordas ----------------------------------------


def test_prc01_plano_vazio_quando_ja_derivado():
    """PRC-01/CTL-01: com a marca d'água à frente do horizonte, nada a derivar."""
    tiers = [tier(1, 3600), tier(5, 86400, min_age=10)]
    now = 1786464120
    p = plan(tiers, {0: now - 1, 1: now - 10}, now)
    assert p.derive == []


def test_ctl02_now_e_truncado_para_a_resolucao():
    """CTL-02: sem truncar, um ponto na fronteira entraria e sairia conforme o relógio."""
    tiers = [tier(1, 3600), tier(5, 86400, min_age=10)]
    a = plan(tiers, {0: None, 1: None}, 1786464123)
    b = plan(tiers, {0: None, 1: None}, 1786464124)
    assert a.derive[0][3] == b.derive[0][3], "o horizonte deve ser o mesmo dentro da janela"


def test_lin06_retencao_conta_de_now():
    """LIN-06: a janela é contada a partir de floor(now), não do ponto mais novo."""
    tiers = [tier(60, 3600)]
    now = 1786464000
    p = plan(tiers, {0: now - 100000}, now)
    assert p.expire == [(0, now - 3600)]


def test_plan_valida_a_config_antes_de_planejar():
    """UX-03: caminho ÚNICO de validação — planejar config inválida é erro."""
    with pytest.raises(SeriesError):
        plan([tier(180, 15 * 86400), tier(600, 90 * 86400)], {0: None, 1: None}, 0)


# --- TierSpec: validações de campo ---------------------------------------------------


def test_xff_fora_de_faixa_e_erro():
    with pytest.raises(SeriesError, match="x_files_factor"):
        TierSpec(60, 3600, "average", 1.5)


def test_resolucao_zero_e_erro():
    with pytest.raises(SeriesError, match="seconds_per_point"):
        TierSpec(0, 3600)


def test_agregacao_invalida_em_tierspec():
    with pytest.raises(SeriesError, match="desconhecida"):
        TierSpec(60, 3600, "mediana")
