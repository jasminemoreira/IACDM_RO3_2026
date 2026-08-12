"""Fixtures da suite. Testes escritos contra specs/validation, nao contra o codigo."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app import construir
from t25.identidade import Identidade
from t25.persistencia import ENTIDADE, GLOBAL
from t25.upstream import UpstreamSimulado

RAIZ = Path(__file__).resolve().parent.parent
NANO_USD = 1_000_000_000

# Instantes fixos: a janela e funcao pura, entao o teste controla o tempo.
AGOSTO = datetime(2026, 8, 10, 12, 0, tzinfo=timezone.utc)
SETEMBRO = datetime(2026, 9, 1, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def rate_card_path() -> str:
    return str(RAIZ / "rate_card.json")


@pytest.fixture
def montar(tmp_path):
    """Monta uma instancia isolada. `roteiro` controla o upstream simulado."""

    def _montar(roteiro=None, teto_entidade=1.0, teto_global=50.0,
                max_tokens=8192, max_reservas=16):
        up = UpstreamSimulado(roteiro or {"uso": {"input_tokens": 20, "output_tokens": 80}})
        app = construir(
            banco=str(tmp_path / "t.db"),
            caminho_rate_card=str(RAIZ / "rate_card.json"),
            upstream=up,
            senha_operador="segredo",
            retencao_dias=0,
        )
        p = app.state.persistencia
        p.criar_entidade("eb", "Equipe Busca", max_tokens, max_reservas, AGOSTO)
        p.definir_teto(GLOBAL, "", round(teto_global * NANO_USD), "teste", AGOSTO)
        p.definir_teto(ENTIDADE, "eb", round(teto_entidade * NANO_USD), "teste", AGOSTO)
        chave = Identidade(p).emitir("eb")
        return app, p, chave, up

    return _montar


@pytest.fixture
def corpo_requisicao():
    return {
        "model": "claude-opus-5",
        "max_tokens": 100,
        "messages": [{"role": "user", "content": "oi"}],
    }


def bytes_de(corpo: dict) -> int:
    return len(json.dumps(corpo).encode("utf-8"))
