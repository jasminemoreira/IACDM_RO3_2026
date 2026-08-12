"""Fixtures da suíte.

REGRA DURA DESTA SUÍTE (mitigação de AP1, declarada na Fase 6): todo valor
esperado vem de um ARTEFATO escrito antes do código — `specs/datasets/
casos-armadilha.md`, `specs/validation/criterios-aceitacao.md` ou um invariante
de `specs/technical/architecture.md`. Cada teste cita o id da sua origem. Um
teste cujo valor esperado saia do que o código devolve não pertence aqui.
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import pytest

from app.adaptadores.repositorio_sqlite import RepositorioSQLite
from app.dominio.modelo_dominio import ESCOPO_GERAL
from app.servico_aplicacao import ServicoAplicacao

RAIZ = Path(__file__).resolve().parent.parent
FIXTURE = RAIZ / "specs" / "datasets" / "tabela-legada.csv"
AGORA = datetime(2026, 8, 12, 10, 0, 0)
HOJE = AGORA.date()


def csv_bruto() -> bytes:
    """A planilha suja, exatamente como está no ground truth."""
    return FIXTURE.read_bytes()


def csv_corrigido() -> bytes:
    """Cópia com os DOIS defeitos plantados removidos.

    Serve aos testes que precisam de um conjunto publicável. Os defeitos em si
    são verificados nos testes de CS-3, contra o arquivo bruto.
    """
    t = FIXTURE.read_text(encoding="utf-8")
    t = t.replace("SKU-1003;Papel A4 500fl (resma);24,90;15;60;22,50;promo fevereiro\n", "")
    t = t.replace("SKU-1007;Mouse USB;31,00;50;", "SKU-1007;Mouse USB;29,90;50;")
    return t.encode("utf-8")


@pytest.fixture
def repo(tmp_path):
    r = RepositorioSQLite(tmp_path / "teste.db")
    yield r
    r.fechar()


@pytest.fixture
def servico(repo):
    # A-04: o relógio é INJETADO. Congelá-lo é o que torna I-1 testável.
    return ServicoAplicacao(repo, agora=lambda: AGORA)


@pytest.fixture
def servico_publicado(servico):
    """Serviço com a planilha corrigida importada e publicada (versão 1)."""
    servico.importar(csv_corrigido(), substituir=True)
    servico.publicar("Testador", "publicação de teste")
    return servico


@pytest.fixture
def cliente(tmp_path):
    from fastapi.testclient import TestClient

    from app.main import criar_app

    app = criar_app(tmp_path / "api.db")
    app.state.servico._agora = lambda: AGORA
    return TestClient(app)


# --------------------------------------------------------------------------
# §A de casos-armadilha.md — as 26 linhas válidas de paridade (CS-1).
# Transcrito do artefato: (sku, preço esperado em ISO, quantidade de teste).
# --------------------------------------------------------------------------
PARIDADE_A = [
    ("SKU-1001", "2.50", 5),
    ("SKU-1001", "2.30", 30),
    ("SKU-1001", "2.10", 100),
    ("SKU-1001", "1.85", 250),
    ("SKU-1002", "12.90", 3),
    ("SKU-1002", "11.60", 25),
    ("SKU-1002", "10.30", 120),
    ("SKU-1003", "24.90", 2),
    ("SKU-1003", "23.40", 10),
    ("SKU-1003", "21.90", 50),
    ("SKU-1003", "19.90", 150),
    ("SKU-1004", "4.75", 4),
    ("SKU-1004", "4.20", 40),
    ("SKU-1004", "3.60", 120),
    ("SKU-1005", "38.00", 2),
    ("SKU-1005", "35.00", 12),
    ("SKU-1005", "31.50", 30),
    ("SKU-1006", "189.90", 1),
    ("SKU-1006", "179.90", 5),
    ("SKU-1006", "165.00", 15),
    ("SKU-1007", "29.90", 6),
    ("SKU-1007", "27.40", 20),
    ("SKU-1007", "24.90", 80),
    ("SKU-1008", "79.00", 3),
    ("SKU-1008", "72.50", 8),
    ("SKU-1008", "66.90", 25),
]
