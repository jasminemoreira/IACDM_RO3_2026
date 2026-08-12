from __future__ import annotations

from pathlib import Path

import pytest

from t24.cli import carregar
from t24.query_service import QueryService

RAIZ = Path(__file__).resolve().parent.parent
CATALOGO = RAIZ / "catalog"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture(scope="session")
def carregado():
    """O catalogo de exemplo, cuja topologia esta fixada em specs/datasets/ground-truth.md."""
    return carregar(CATALOGO)


@pytest.fixture(scope="session")
def servico(carregado) -> QueryService:
    return QueryService(carregado)


@pytest.fixture
def fixtures() -> Path:
    return FIXTURES
