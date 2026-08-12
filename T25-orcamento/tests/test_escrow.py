"""CA-1 invariante · CA-6 nenhum caminho deixa reserva aberta · CA-7 crash
CA-8 invariante I2 · CA-9 defesas contra abuso · CA-11 sinal de A8 violada."""

from __future__ import annotations

import logging

from t25.escrow import Escrow, Motivo
from t25.janela import janela_de
from t25.persistencia import ENTIDADE, GLOBAL, Persistencia

from .conftest import AGOSTO, NANO_USD, SETEMBRO


def _cont(p, escopo, ent, instante):
    return p.ler_contador(p.conexao(), escopo, ent, janela_de(instante).chave)


# ---------- CA-1 ----------

def test_reserva_compromete_saldo_antes_de_gastar(montar):
    _, p, _, _ = montar(teto_entidade=1.0)
    d = Escrow(p).reservar("eb", 300_000_000, AGOSTO, 100, 8192, 16)
    assert d.permitido and d.codigo_motivo == Motivo.OK
    c = _cont(p, ENTIDADE, "eb", AGOSTO)
    # O comprometido inclui a reserva: e isso que impede N concorrentes de passar.
    assert c.reservado_nano == 300_000_000
    assert c.confirmado_nano == 0
    assert c.comprometido_nano == 300_000_000


def test_nega_quando_teto_da_entidade_nao_comporta(montar):
    _, p, _, _ = montar(teto_entidade=1.0, teto_global=50.0)
    d = Escrow(p).reservar("eb", 2 * NANO_USD, AGOSTO, 100, 8192, 16)
    assert not d.permitido
    assert d.codigo_motivo == Motivo.TETO_ENTIDADE
    assert d.escopo_estourado == ENTIDADE


def test_nega_quando_teto_global_nao_comporta_o_mais_restritivo_vence(montar):
    """Teto da entidade folgado, global apertado: o global deve barrar."""
    _, p, _, _ = montar(teto_entidade=100.0, teto_global=1.0)
    d = Escrow(p).reservar("eb", 2 * NANO_USD, AGOSTO, 100, 8192, 16)
    assert not d.permitido
    assert d.codigo_motivo == Motivo.TETO_GLOBAL
    assert d.escopo_estourado == GLOBAL


def test_nega_quando_nao_ha_teto_configurado(tmp_path):
    p = Persistencia(str(tmp_path / "x.db"))
    p.criar_entidade("eb", "EB", 8192, 16, AGOSTO)
    d = Escrow(p).reservar("eb", 1, AGOSTO, 100, 8192, 16)
    assert not d.permitido and d.codigo_motivo == Motivo.SEM_TETO


# ---------- CA-9: defesas contra abuso de reserva ----------

def test_nega_max_tokens_acima_do_limite_da_entidade(montar):
    """GAM-01: max_tokens enorme consumiria o teto global sem gastar nada."""
    _, p, _, _ = montar(max_tokens=1000)
    d = Escrow(p).reservar("eb", 1, AGOSTO, 999_999, 1000, 16)
    assert not d.permitido and d.codigo_motivo == Motivo.MAX_TOKENS_ACIMA_DO_LIMITE


def test_nega_reservas_simultaneas_acima_do_limite(montar):
    """GAM-03: o teto de max_tokens limita UMA requisicao, nao o agregado."""
    _, p, _, _ = montar(teto_entidade=100.0, max_reservas=2)
    e = Escrow(p)
    assert e.reservar("eb", 1_000, AGOSTO, 10, 8192, 2).permitido
    assert e.reservar("eb", 1_000, AGOSTO, 10, 8192, 2).permitido
    d = e.reservar("eb", 1_000, AGOSTO, 10, 8192, 2)
    assert not d.permitido and d.codigo_motivo == Motivo.RESERVAS_SIMULTANEAS


# ---------- CA-6: nenhum caminho deixa reserva aberta ----------

def test_reconciliar_troca_reserva_por_custo_real(montar):
    _, p, _, _ = montar()
    e = Escrow(p)
    d = e.reservar("eb", 300_000_000, AGOSTO, 100, 8192, 16)
    assert e.reconciliar(d.id_reserva, 120_000_000) is True
    c = _cont(p, ENTIDADE, "eb", AGOSTO)
    assert c.reservado_nano == 0
    assert c.confirmado_nano == 120_000_000


def test_reconciliar_e_idempotente(montar):
    _, p, _, _ = montar()
    e = Escrow(p)
    d = e.reservar("eb", 300_000_000, AGOSTO, 100, 8192, 16)
    assert e.reconciliar(d.id_reserva, 120_000_000) is True
    assert e.reconciliar(d.id_reserva, 120_000_000) is False  # nao debita de novo
    assert _cont(p, ENTIDADE, "eb", AGOSTO).confirmado_nano == 120_000_000


def test_liberar_devolve_a_reserva_integralmente(montar):
    _, p, _, _ = montar()
    e = Escrow(p)
    d = e.reservar("eb", 300_000_000, AGOSTO, 100, 8192, 16)
    assert e.liberar(d.id_reserva) is True
    c = _cont(p, ENTIDADE, "eb", AGOSTO)
    assert c.reservado_nano == 0 and c.confirmado_nano == 0
    assert e.liberar(d.id_reserva) is False  # tambem idempotente


# ---------- CA-3 / PRO-01: reserva que atravessa a virada ----------

def test_reserva_de_agosto_reconcilia_na_janela_de_agosto(montar):
    """A reserva grava SUA janela. Reconciliar depois da virada nao pode
    debitar a janela nova (achado PRO-01)."""
    _, p, _, _ = montar()
    e = Escrow(p)
    d = e.reservar("eb", 300_000_000, AGOSTO, 100, 8192, 16)
    e.reconciliar(d.id_reserva, 120_000_000)
    assert _cont(p, ENTIDADE, "eb", AGOSTO).confirmado_nano == 120_000_000
    assert _cont(p, ENTIDADE, "eb", SETEMBRO).confirmado_nano == 0


def test_reset_reverte_o_corte_sem_intervencao(montar):
    """CA-3: entidade esgotada em agosto e atendida em setembro."""
    _, p, _, _ = montar(teto_entidade=1.0)
    e = Escrow(p)
    d = e.reservar("eb", 900_000_000, AGOSTO, 100, 8192, 16)
    e.reconciliar(d.id_reserva, 900_000_000)
    assert not e.reservar("eb", 900_000_000, AGOSTO, 100, 8192, 16).permitido
    assert e.reservar("eb", 900_000_000, SETEMBRO, 100, 8192, 16).permitido


# ---------- CA-11: o clamp precisa GRITAR ----------

def test_clamp_sinaliza_reserva_insuficiente(montar, caplog):
    """Se o custo real exceder a reserva, a premissa A8 foi violada. O clamp
    preserva o invariante mas NAO pode faze-lo em silencio."""
    _, p, _, _ = montar()
    e = Escrow(p)
    d = e.reservar("eb", 1_000_000, AGOSTO, 100, 8192, 16)
    with caplog.at_level(logging.ERROR, logger="t25.escrow"):
        e.reconciliar(d.id_reserva, 9_000_000)
    assert "RESERVA INSUFICIENTE" in caplog.text
    # invariante preservado: nunca confirma mais que o reservado
    assert _cont(p, ENTIDADE, "eb", AGOSTO).confirmado_nano == 1_000_000


# ---------- CA-7 e CA-8 ----------

def test_recuperacao_no_arranque_libera_reservas_orfas(montar):
    """Num processo recem-iniciado nenhuma requisicao pode estar em voo."""
    _, p, _, _ = montar()
    Escrow(p).reservar("eb", 300_000_000, AGOSTO, 100, 8192, 16)
    assert _cont(p, ENTIDADE, "eb", AGOSTO).reservado_nano == 300_000_000
    assert p.recuperar_no_arranque() == 1
    assert _cont(p, ENTIDADE, "eb", AGOSTO).reservado_nano == 0


def test_invariante_i2_soma_das_abertas_igual_ao_reservado(montar):
    _, p, _, _ = montar(teto_entidade=100.0)
    e = Escrow(p)
    e.reservar("eb", 1_000_000, AGOSTO, 10, 8192, 16)
    e.reservar("eb", 2_000_000, AGOSTO, 10, 8192, 16)
    inv = p.verificar_invariantes(janela_de(AGOSTO).chave)
    assert inv["i2_ok"] is True and inv["divergencias"] == []
    assert _cont(p, ENTIDADE, "eb", AGOSTO).reservado_nano == 3_000_000
