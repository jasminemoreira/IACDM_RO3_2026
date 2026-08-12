"""M-01 `dinheiro` — I-5 (decimal exato) e a regra de separador (N-06)."""

from decimal import Decimal

import pytest

from app.dominio.dinheiro import Dinheiro, ErroFormato, texto_tem_separador_ambiguo

# Origem: specs/datasets/casos-armadilha.md §B, caso N-06 — tabela literal.
N06 = [
    ("1.299,00", "1299.00"),
    ("1.189,50", "1189.50"),
    ("21,90", "21.90"),
    ("1.299", "1299.00"),
    ("21.90", "21.90"),
    ("2.5", "2.50"),
    ("1.234.567", "1234567.00"),
    ("R$ 1.299", "1299.00"),
]


@pytest.mark.parametrize("entrada,esperado", N06)
def test_n06_regra_de_separador(entrada, esperado):
    d = Dinheiro.de_texto(entrada)
    assert isinstance(d, Dinheiro), f"{entrada!r} deveria parsear"
    assert d.iso() == esperado


def test_n06_ambiguidade_e_sinalizada():
    """MEC-05/X7: parsear pela regra, mas NUNCA em silêncio."""
    assert texto_tem_separador_ambiguo("1.299") is True
    assert texto_tem_separador_ambiguo("2.500") is True
    assert texto_tem_separador_ambiguo("21,90") is False
    assert texto_tem_separador_ambiguo("21.90") is False


def test_mec02_espaco_nao_quebravel_e_menos_unicode():
    """MEC-02: tolerância por princípio, não por lista."""
    assert Dinheiro.de_texto("R$ 1.299,00").iso() == "1299.00"
    assert Dinheiro.de_texto(" 1.299,00 ").iso() == "1299.00"
    assert isinstance(Dinheiro.de_texto("−1,00"), ErroFormato)


# Origem: §C de casos-armadilha.md — motivos de rejeição, um por caso.
@pytest.mark.parametrize(
    "entrada,trecho_do_motivo",
    [
        ("", "ausente"),          # R-02
        (None, "ausente"),        # R-02
        ("-1,00", "negativo"),    # R-03
        ("-10%", "não-monetário"),  # R-04
        ("a partir de 50", "inválido"),  # relacionado a R-05
    ],
)
def test_rejeicoes_de_formato(entrada, trecho_do_motivo):
    e = Dinheiro.de_texto(entrada)
    assert isinstance(e, ErroFormato)
    assert trecho_do_motivo in e.motivo


def test_p09_decimal_exato_half_up():
    """Origem: §E, caso P-09 — 33% sobre R$4,75 = R$3,18, nunca 3.1825…"""
    base = Dinheiro.de_texto("4,75")
    assert base.aplicar_pct(Decimal(67)).iso() == "3.18"


def test_i5_nunca_float():
    """I-5: dinheiro é inteiro de centavos; nada de binário no caminho."""
    d = Dinheiro.de_texto("0,10")
    soma = Dinheiro(sum(d.centavos for _ in range(10)))
    assert soma.iso() == "1.00"  # 0.1*10 em float daria 0.9999999999999999
    assert isinstance(d.centavos, int)


def test_apresentacao_e_derivada_do_iso():
    """LIN-04/W10: ISO é normativo; pt-BR é apresentação."""
    d = Dinheiro.de_texto("1.189,50")
    assert d.iso() == "1189.50"
    assert str(d) == "R$ 1.189,50"


def test_dinheiro_nunca_negativo():
    with pytest.raises(ValueError):
        Dinheiro(-1)
