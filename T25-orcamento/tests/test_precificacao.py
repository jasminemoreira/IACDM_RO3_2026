"""CA-2 exatidao contabil · CA-4 modelo sem preco · CA-3 janela.

Ground truth vem de specs/technical/rate-card-llm.md, nao do codigo.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from t25.janela import janela_de, proximo_reset
from t25.precificador import Precificador, Uso
from t25.rate_card import ModeloSemPreco, RateCard

from .conftest import AGOSTO, SETEMBRO


@pytest.fixture
def rc(rate_card_path):
    return RateCard.carregar(rate_card_path)


# ---------- CA-2: exatidao contabil contra ground truth ----------

def test_custo_quatro_categorias_exato(rc):
    """As QUATRO categorias somadas ao nano. Ground truth calculado a mao a
    partir de specs/technical/rate-card-llm.md §1 e §2 para claude-opus-5."""
    uso = Uso(
        tokens_entrada=1_000,        # x 5.000 nano = 5.000.000
        tokens_cache_leitura=2_000,  # x   500 nano = 1.000.000
        tokens_cache_escrita=400,    # x 6.250 nano = 2.500.000
        tokens_saida=300,            # x25.000 nano = 7.500.000
    )
    esperado = 5_000_000 + 1_000_000 + 2_500_000 + 7_500_000
    assert Precificador(rc).custo(uso, "claude-opus-5", AGOSTO) == esperado


def test_custo_cache_1h_e_16x_o_de_5m(rc):
    """1,25x vs 2,0x sobre o preco de entrada: valores distintos e exatos."""
    p = Precificador(rc)
    u5m = Uso(0, 0, 1_000, 0, cache_escrita_1h=False)
    u1h = Uso(0, 0, 1_000, 0, cache_escrita_1h=True)
    assert p.custo(u5m, "claude-opus-5", AGOSTO) == 1_000 * 6_250
    assert p.custo(u1h, "claude-opus-5", AGOSTO) == 1_000 * 10_000


def test_preco_promocional_sonnet5_dentro_e_fora_da_vigencia(rc):
    """A promocao termina em 2026-08-31 (specs/technical/rate-card-llm.md §1)."""
    assert rc.preco("claude-sonnet-5", "entrada", AGOSTO) == 2_000
    assert rc.preco("claude-sonnet-5", "entrada", SETEMBRO) == 3_000
    assert rc.preco("claude-sonnet-5", "saida", AGOSTO) == 10_000
    assert rc.preco("claude-sonnet-5", "saida", SETEMBRO) == 15_000


def test_aritmetica_e_inteira_sem_ponto_flutuante(rc):
    """Nenhum custo pode voltar como float — nano e inteiro por decisao."""
    c = Precificador(rc).custo(Uso(7, 3, 1, 11), "claude-haiku-4-5", AGOSTO)
    assert isinstance(c, int)
    assert c == 7 * 1_000 + 3 * 100 + 1 * 1_250 + 11 * 5_000


# ---------- CA-4: modelo sem preco vigente ----------

def test_modelo_desconhecido_levanta_em_vez_de_devolver_zero(rc):
    with pytest.raises(ModeloSemPreco):
        rc.preco("modelo-que-nao-existe", "entrada", AGOSTO)


def test_categoria_desconhecida_levanta(rc):
    with pytest.raises(ModeloSemPreco):
        rc.preco("claude-opus-5", "categoria-inventada", AGOSTO)


def test_preco_sem_fonte_e_recusado_na_carga(tmp_path):
    """Invariante I5 de specs/models: preco sem fonte nao entra."""
    ruim = tmp_path / "ruim.json"
    ruim.write_text(
        '{"precos":[{"modelo":"m","categoria":"entrada","nano_por_token":1,'
        '"vigente_desde":"2000-01-01","vigente_ate":null,"fonte":""}]}',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="fonte"):
        RateCard.carregar(ruim)


# ---------- CA-1: a reserva de pior caso ----------

def test_pior_caso_inclui_prompt_e_saida(rc):
    """pior_caso = bytes x preco_entrada + max_tokens x preco_saida (V(3))."""
    esperado = 94 * 5_000 + 100 * 25_000
    assert Precificador(rc).pior_caso("claude-opus-5", 94, 100, AGOSTO) == esperado


def test_pior_caso_rejeita_max_tokens_invalido(rc):
    with pytest.raises(ValueError):
        Precificador(rc).pior_caso("claude-opus-5", 94, 0, AGOSTO)


# ---------- CA-3: janela ----------

def test_janela_mensal_utc():
    j = janela_de(AGOSTO)
    assert j.inicio == datetime(2026, 8, 1, tzinfo=timezone.utc)
    assert j.fim == datetime(2026, 9, 1, tzinfo=timezone.utc)
    assert proximo_reset(AGOSTO) == j.fim


def test_janela_de_dezembro_vira_para_janeiro():
    j = janela_de(datetime(2026, 12, 15, tzinfo=timezone.utc))
    assert j.fim == datetime(2027, 1, 1, tzinfo=timezone.utc)


def test_janela_rejeita_instante_sem_fuso():
    with pytest.raises(ValueError):
        janela_de(datetime(2026, 8, 10, 12, 0))
