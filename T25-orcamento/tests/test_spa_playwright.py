"""Smoke test do modulo M-10 painel-web num navegador real.

E o unico teste que executa painel.js. Os testes HTTP cobrem painel-api, nao a SPA.
Sobe o gateway num servidor uvicorn de verdade e dirige o Chromium.
"""

from __future__ import annotations

import socket
import threading
import time

import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright  # noqa: E402

from t25.identidade import Identidade  # noqa: E402
from t25.persistencia import ENTIDADE, GLOBAL  # noqa: E402

from .conftest import AGOSTO, NANO_USD  # noqa: E402


def _porta_livre() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    porta = s.getsockname()[1]
    s.close()
    return porta


@pytest.fixture
def servidor(tmp_path):
    import uvicorn

    from app import construir
    from t25.upstream import UpstreamSimulado

    up = UpstreamSimulado({"uso": {"input_tokens": 20, "output_tokens": 80}})
    app = construir(
        banco=str(tmp_path / "spa.db"), upstream=up, senha_operador="segredo", retencao_dias=0
    )
    p = app.state.persistencia
    p.criar_entidade("eb", "Equipe Busca", 8192, 16, AGOSTO)
    p.definir_teto(GLOBAL, "", 50 * NANO_USD, "teste", AGOSTO)
    p.definir_teto(ENTIDADE, "eb", NANO_USD // 100, "teste", AGOSTO)  # USD 0,01
    chave = Identidade(p).emitir("eb")

    porta = _porta_livre()
    cfg = uvicorn.Config(app, host="127.0.0.1", port=porta, log_level="error")
    srv = uvicorn.Server(cfg)
    t = threading.Thread(target=srv.run, daemon=True)
    t.start()
    for _ in range(100):
        if srv.started:
            break
        time.sleep(0.05)
    yield f"http://127.0.0.1:{porta}", chave, p
    srv.should_exit = True
    t.join(timeout=5)


def test_spa_login_e_leitura_do_painel(servidor):
    """UC-5 no navegador: operador entra, ve consumo, saldo e o reset em UTC."""
    base, chave, _p = servidor

    with sync_playwright() as pw:
        nav = pw.chromium.launch()
        pg = nav.new_page()

        # Gera consumo real antes de olhar o painel.
        for _ in range(4):
            pg.request.post(
                f"{base}/v1/messages",
                headers={"x-api-key": chave, "content-type": "application/json"},
                data='{"model":"claude-opus-5","max_tokens":100,'
                '"messages":[{"role":"user","content":"oi"}]}',
            )

        pg.goto(base)
        assert "T25" in pg.title()

        # A tabela so aparece depois do login: o painel comeca protegido.
        assert pg.locator("#painel").is_hidden()

        pg.fill("#senha", "errada")
        pg.click("#form-login button")
        pg.wait_for_selector("#erro-login:not(:empty)")
        assert "inválida" in pg.inner_text("#erro-login")
        assert pg.locator("#painel").is_hidden()  # segue protegido

        pg.fill("#senha", "segredo")
        pg.click("#form-login button")
        pg.wait_for_selector("#linhas tr")

        linha = pg.inner_text("#linhas tr")
        assert "Equipe Busca" in linha
        assert "$0.0100" in linha  # teto da entidade
        assert "tokens de saída" in linha  # explica por que negaria

        # O reset precisa estar em UTC e visivel (decisao b7fbe77c).
        cabecalho = pg.inner_text("#janela")
        assert "UTC" in cabecalho and "2026-09-01" in cabecalho

        # Estado global renderizado
        assert pg.inner_text("#g-teto") == "$50.0000"

        nav.close()


def test_spa_operador_altera_teto_pela_interface(servidor):
    """UC-5 completo: a alteracao feita na tela chega ao backend."""
    base, _chave, p = servidor

    with sync_playwright() as pw:
        nav = pw.chromium.launch()
        pg = nav.new_page()
        pg.goto(base)
        pg.fill("#senha", "segredo")
        pg.click("#form-login button")
        pg.wait_for_selector("#linhas tr")

        pg.fill("#linhas input[type=number]", "0.25")
        pg.click("#linhas form.linha-teto button")
        pg.wait_for_function(
            "() => document.querySelector('#linhas tr').innerText.includes('$0.2500')"
        )

        assert p.ler_teto(p.conexao(), ENTIDADE, "eb") == 250_000_000
        linha = p.conexao().execute(
            "SELECT ator FROM auditoria_teto ORDER BY id DESC LIMIT 1"
        ).fetchone()
        assert linha["ator"] == "operador"  # a alteracao e atribuivel
        nav.close()
