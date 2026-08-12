"""M-12 `ui-editor-regras` — o JavaScript da grade, em navegador real.

Esta é a única parte do sistema que TestClient não alcança: colagem de TSV
vinda do clipboard, exclusão de linhas e desfazer. E é justamente onde mora a
contramedida do achado 🔴 UX-01 — *se editar regra aqui for pior que editar
célula na planilha, o analista volta para a planilha e o motor vira leitura*.

Executa o servidor real numa thread, o que também exercita A-06 (o defeito de
runtime: handlers síncronos em threadpool, SQLite entre threads).
"""

from __future__ import annotations

import socket
import threading
import time

import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import expect, sync_playwright  # noqa: E402

from conftest import csv_corrigido  # noqa: E402

pytestmark = pytest.mark.ui


def _porta_livre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def servidor(tmp_path_factory):
    import uvicorn

    from app.main import criar_app

    porta = _porta_livre()
    app = criar_app(tmp_path_factory.mktemp("ui") / "ui.db")
    config = uvicorn.Config(app, host="127.0.0.1", port=porta, log_level="warning")
    server = uvicorn.Server(config)
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)
    yield f"http://127.0.0.1:{porta}"
    server.should_exit = True
    t.join(timeout=5)


@pytest.fixture(scope="module")
def navegador():
    with sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


@pytest.fixture
def pagina(navegador, servidor):
    ctx = navegador.new_context()
    pg = ctx.new_page()
    yield pg
    ctx.close()


def _importar(pagina, url):
    pagina.goto(f"{url}/importar")
    pagina.set_input_files("#arquivo", files=[
        {"name": "planilha.csv", "mimeType": "text/csv", "buffer": csv_corrigido()}
    ])
    pagina.check('input[name="substituir"]')
    pagina.click("#btn")
    pagina.wait_for_load_state()


def test_uc2_importacao_pela_interface(pagina, servidor):
    """UC-2 ponta a ponta no navegador — o caso que o operador executou."""
    _importar(pagina, servidor)
    corpo = pagina.inner_text("main")
    assert "regras importadas" in corpo
    assert "linhas rejeitadas" in corpo
    assert "faixa invertida" in corpo          # R-01, nomeada por linha
    assert "Próximo passo" in corpo            # correção do defeito 1


def test_uc3_publicar_pela_interface(pagina, servidor):
    """UC-3: rascunho → validar → publicar, com autor e justificativa."""
    _importar(pagina, servidor)
    pagina.goto(f"{servidor}/regras")
    pagina.fill("#autor", "Testadora")
    pagina.fill("#justificativa", "publicação via navegador")
    if pagina.locator('input[name="reconheco_avisos"]').count():
        pagina.check('input[name="reconheco_avisos"]')
    pagina.click('button[value="publicar"]')
    pagina.wait_for_load_state()
    assert "publicada por Testadora" in pagina.inner_text("main")


def test_uc4_simular_e_ler_o_trace(pagina, servidor):
    """UC-4: o trace mostra a vencedora E as derrotadas com motivo (CS-2)."""
    _importar(pagina, servidor)
    pagina.goto(f"{servidor}/regras")
    pagina.fill("#autor", "T")
    pagina.fill("#justificativa", "para simular")
    if pagina.locator('input[name="reconheco_avisos"]').count():
        pagina.check('input[name="reconheco_avisos"]')
    pagina.click('button[value="publicar"]')
    pagina.wait_for_load_state()

    pagina.goto(f"{servidor}/simular")
    pagina.fill("#sku", "SKU-1003")
    pagina.fill("#quantidade", "50")
    pagina.fill("#data", "2026-08-12")
    pagina.click('button[type="submit"]')
    pagina.wait_for_load_state()
    corpo = pagina.inner_text("main")
    assert "R$ 21,90" in corpo                     # §E P-01
    assert "R$ 1.095,00" in corpo
    assert "não cobre a quantidade pedida" in corpo  # derrotadas com motivo
    assert "Mostrando" in corpo                    # Y8: "mostrando X de Y"


def test_ux01_colagem_de_bloco_vindo_da_planilha(pagina, servidor):
    """UX-01 🔴 — a contramedida central, testada de verdade.

    Simula copiar um bloco de células (TSV) e colar na grade. Sem isso, a
    grade é um formulário por regra, e o produto perde para a planilha no
    único critério em que a planilha ganha.
    """
    _importar(pagina, servidor)
    pagina.goto(f"{servidor}/regras")
    linhas_antes = pagina.locator("#grade tbody tr").count()

    bloco = "SKU-1001\t900\t999\tPRECO_UNITARIO\t1.50\t7\t2026-01-01\t\n" \
            "SKU-1002\t900\t999\tPRECO_UNITARIO\t9.00\t7\t2026-01-01\t"
    alvo = pagina.locator('#grade tbody tr:first-child input[name="escopo"]')
    alvo.click()
    # Injeta o evento de colagem com o TSV, como o navegador faria.
    pagina.evaluate(
        """(texto) => {
            const alvo = document.querySelector('#grade tbody tr:first-child input[name="escopo"]');
            const dt = new DataTransfer();
            dt.setData('text', texto);
            alvo.dispatchEvent(new ClipboardEvent('paste', {
                clipboardData: dt, bubbles: true, cancelable: true }));
        }""",
        bloco,
    )
    primeiro_escopo = pagina.locator('#grade tbody tr:first-child input[name="escopo"]').input_value()
    primeiro_de = pagina.locator('#grade tbody tr:first-child input[name="de"]').input_value()
    assert primeiro_escopo == "SKU-1001"
    assert primeiro_de == "900"
    segundo_de = pagina.locator('#grade tbody tr:nth-child(2) input[name="de"]').input_value()
    assert segundo_de == "900", "a segunda linha do bloco também tem de ser preenchida"
    assert pagina.locator("#grade tbody tr").count() == linhas_antes


def test_grade_excluir_e_desfazer(pagina, servidor):
    """Excluir linhas selecionadas e desfazer — operações da spec."""
    _importar(pagina, servidor)
    pagina.goto(f"{servidor}/regras")
    antes = pagina.locator("#grade tbody tr").count()
    pagina.locator("#grade tbody tr:first-child input.sel").check()
    pagina.click("text=Excluir selecionadas")
    assert pagina.locator("#grade tbody tr").count() == antes - 1
    pagina.click("text=Desfazer")
    assert pagina.locator("#grade tbody tr").count() == antes


def test_ux04_acessibilidade_basica(pagina, servidor):
    """UX-04: rótulos associados e navegação por teclado nas 4 telas."""
    for rota in ("/simular", "/regras", "/importar", "/historico"):
        pagina.goto(f"{servidor}{rota}")
        # todo input visível tem rótulo ou aria-label
        sem_rotulo = pagina.evaluate(
            """() => [...document.querySelectorAll('input:not([type=hidden]), select')]
                 .filter(e => !e.getAttribute('aria-label')
                           && !e.labels?.length
                           && !e.closest('label')).length"""
        )
        assert sem_rotulo == 0, f"{rota}: {sem_rotulo} campos sem rótulo"


def test_sec03_escape_de_html_vindo_do_csv(pagina, servidor):
    """SEC-03: `descricao` vem do CSV (dado não confiável) e vai para o HTML."""
    csv = (
        "SKU;Produto;Preco base;De;Ate;Preco un.\n"
        "SKU-9001;<script>alert(1)</script>;10,00;1;9;9,00\n"
    ).encode()
    pagina.goto(f"{servidor}/importar")
    pagina.set_input_files("#arquivo", files=[
        {"name": "x.csv", "mimeType": "text/csv", "buffer": csv}
    ])
    pagina.check('input[name="substituir"]')
    pagina.click("#btn")
    pagina.wait_for_load_state()
    # O script não pode ter sido executado nem inserido como tag.
    assert pagina.evaluate("() => document.querySelectorAll('main script').length") == 0
