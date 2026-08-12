"""Casos de uso da Fase 0 de ponta a ponta + CA-1 (criterio de acerto), CA-5, CA-10."""

from __future__ import annotations

import asyncio

import httpx
from starlette.testclient import TestClient

from t25.janela import janela_de
from t25.persistencia import ENTIDADE

from .conftest import AGOSTO, NANO_USD, bytes_de


def _cli(app, chave):
    return TestClient(app), {"x-api-key": chave}


# ---------- UC-1 / UC-2 ----------

def test_uc1_requisicao_dentro_do_teto_e_permitida(montar, corpo_requisicao):
    app, p, chave, up = montar(teto_entidade=1.0)
    c, h = _cli(app, chave)
    r = c.post("/v1/messages", json=corpo_requisicao, headers=h)
    assert r.status_code == 200
    assert r.json()["stop_reason"] == "end_turn"
    assert len(up.chamadas) == 1  # a requisicao chegou ao provedor
    cont = p.ler_contador(p.conexao(), ENTIDADE, "eb", janela_de(AGOSTO).chave)
    assert cont.reservado_nano == 0  # reconciliada
    assert cont.confirmado_nano == 20 * 5_000 + 80 * 25_000


def test_uc2_requisicao_que_esgota_e_negada_com_codigo_escopo_e_reset(montar, corpo_requisicao):
    """O corpo do 402 precisa dizer QUAL teto e QUANDO volta (achados UX-01/UX-02)."""
    app, p, chave, up = montar(teto_entidade=0.000001)
    c, h = _cli(app, chave)
    r = c.post("/v1/messages", json=corpo_requisicao, headers=h)
    assert r.status_code == 402
    erro = r.json()["error"]
    assert erro["type"] == "teto_entidade_esgotado"
    assert erro["escopo_estourado"] == "entidade"
    assert erro["reset_em"].endswith("+00:00")
    assert up.chamadas == []  # NADA foi enviado ao provedor


def test_negacao_nao_usa_429_para_nao_confundir_com_rate_limit(montar, corpo_requisicao):
    """UX-02: o app precisa distinguir teto esgotado de 429 do provedor."""
    app, _, chave, _ = montar(teto_entidade=0.000001)
    c, h = _cli(app, chave)
    assert c.post("/v1/messages", json=corpo_requisicao, headers=h).status_code == 402


# ---------- UC-3: CRITERIO DE ACERTO ----------

def test_uc3_invariante_do_teto_sob_concorrencia(montar, corpo_requisicao):
    """CA-1, o criterio de acerto congelado na Fase 0.

    N requisicoes simultaneas contra saldo quase esgotado:
      (a) soma dos custos das ACEITAS <= teto
      (b) toda requisicao apos o esgotamento e NEGADA
    """
    pior_caso = bytes_de(corpo_requisicao) * 5_000 + 100 * 25_000
    cabem = 3
    teto_nano = pior_caso * cabem + pior_caso // 2  # cabem 3, sobra menos que 1
    app, p, chave, _ = montar(
        roteiro={"uso": {"input_tokens": 20, "output_tokens": 80}, "atraso_s": 0.05},
        teto_entidade=teto_nano / NANO_USD,
        teto_global=1000.0,
        max_reservas=64,
    )

    async def carga():
        t = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=t, base_url="http://t") as cli:
            return await asyncio.gather(
                *[
                    cli.post("/v1/messages", json=corpo_requisicao, headers={"x-api-key": chave})
                    for _ in range(20)
                ]
            )

    res = asyncio.run(carga())
    aceitas = [r for r in res if r.status_code == 200]
    negadas = [r for r in res if r.status_code == 402]

    assert len(aceitas) + len(negadas) == 20
    assert len(aceitas) <= cabem  # (b) o excedente foi negado
    assert len(negadas) >= 20 - cabem

    cont = p.ler_contador(p.conexao(), ENTIDADE, "eb", janela_de(AGOSTO).chave)
    assert cont.confirmado_nano <= teto_nano  # (a) INVARIANTE
    assert cont.reservado_nano == 0  # nenhuma reserva ficou aberta
    assert p.verificar_invariantes(janela_de(AGOSTO).chave)["i2_ok"]


# ---------- CA-5: politica de cobranca ----------

def test_refusal_sem_saida_nao_e_cobrada(montar, corpo_requisicao):
    """specs/examples §7: recusa antes de qualquer saida nao e cobrada."""
    app, p, chave, _ = montar(
        roteiro={"uso": {"input_tokens": 500, "output_tokens": 0}, "stop_reason": "refusal"}
    )
    c, h = _cli(app, chave)
    assert c.post("/v1/messages", json=corpo_requisicao, headers=h).status_code == 200
    cont = p.ler_contador(p.conexao(), ENTIDADE, "eb", janela_de(AGOSTO).chave)
    assert cont.confirmado_nano == 0
    assert cont.reservado_nano == 0


def test_max_tokens_atingido_e_cobrado_normalmente(montar, corpo_requisicao):
    app, p, chave, _ = montar(
        roteiro={"uso": {"input_tokens": 10, "output_tokens": 100}, "stop_reason": "max_tokens"}
    )
    c, h = _cli(app, chave)
    assert c.post("/v1/messages", json=corpo_requisicao, headers=h).status_code == 200
    cont = p.ler_contador(p.conexao(), ENTIDADE, "eb", janela_de(AGOSTO).chave)
    assert cont.confirmado_nano == 10 * 5_000 + 100 * 25_000


# ---------- CA-6: nenhum caminho deixa reserva aberta ----------

def test_erro_do_provedor_libera_a_reserva(montar, corpo_requisicao):
    app, p, chave, _ = montar(roteiro={"erro": "provedor fora do ar"})
    c, h = _cli(app, chave)
    try:
        c.post("/v1/messages", json=corpo_requisicao, headers=h)
    except RuntimeError:
        pass  # a excecao atravessa o TestClient; o `finally` ja rodou
    cont = p.ler_contador(p.conexao(), ENTIDADE, "eb", janela_de(AGOSTO).chave)
    assert cont.reservado_nano == 0
    assert cont.confirmado_nano == 0


# ---------- CA-4 e validacao de entrada ----------

def test_modelo_sem_preco_e_negado(montar, corpo_requisicao):
    app, _, chave, up = montar()
    c, h = _cli(app, chave)
    r = c.post("/v1/messages", json={**corpo_requisicao, "model": "gpt-inexistente"}, headers=h)
    assert r.status_code == 402
    assert r.json()["error"]["type"] == "modelo_sem_preco_vigente"
    assert up.chamadas == []


def test_max_tokens_ausente_e_recusado(montar, corpo_requisicao):
    """Achado A-04: e de max_tokens que a reserva depende."""
    app, _, chave, _ = montar()
    c, h = _cli(app, chave)
    corpo = {k: v for k, v in corpo_requisicao.items() if k != "max_tokens"}
    r = c.post("/v1/messages", json=corpo, headers=h)
    assert r.status_code == 400


def test_chave_virtual_invalida_e_recusada(montar, corpo_requisicao):
    app, _, _, up = montar()
    c = TestClient(app)
    r = c.post("/v1/messages", json=corpo_requisicao, headers={"x-api-key": "t25-falsa"})
    assert r.status_code == 401
    assert up.chamadas == []


def test_chave_revogada_deixa_de_funcionar(montar, corpo_requisicao):
    from t25.identidade import Identidade

    app, p, chave, _ = montar()
    c, h = _cli(app, chave)
    assert c.post("/v1/messages", json=corpo_requisicao, headers=h).status_code == 200
    assert Identidade(p).revogar(chave, AGOSTO) is True
    assert c.post("/v1/messages", json=corpo_requisicao, headers=h).status_code == 401
