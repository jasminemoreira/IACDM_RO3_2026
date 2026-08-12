"""Fixtures compartilhadas. Os testes leem das SPECS, não da implementação."""

from __future__ import annotations

import json
import warnings
from pathlib import Path

import pytest

# ofxtools avisa sobre NAME acima de 32 caracteres nos fixtures sintéticos; é
# ruído conhecido do gerador, não sinal do sistema sob teste.
warnings.filterwarnings("ignore", module="ofxtools")

RAIZ = Path(__file__).resolve().parent.parent
PERFIS = RAIZ / "perfis"


@pytest.fixture(scope="session")
def dados(tmp_path_factory) -> Path:
    """Dataset sintético com ground truth. Seed fixa: mesmo dataset toda rodada."""
    from t26.fixtures.gerador import gerar

    destino = tmp_path_factory.mktemp("dados")
    gerar(42, 200, destino, PERFIS / "bancox.json", PERFIS / "livro.json")
    return destino


@pytest.fixture(scope="session")
def ground_truth(dados) -> dict:
    return json.loads((dados / "ground-truth.json").read_text())


@pytest.fixture
def base(tmp_path) -> Path:
    return tmp_path / "teste.db"


@pytest.fixture
def store(base):
    from t26.persistence.store import Store

    st = Store(base)
    yield st
    st.fechar()
