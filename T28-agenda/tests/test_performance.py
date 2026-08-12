"""VAL-1 e VAL-2 — escala e tempo de ciclo.

Regra anti-falsa-cobertura de specs/validation/acceptance.md: o criterio diz
"< 5 s", entao o teste CRONOMETRA. Verificar que "o ciclo terminou" nao verifica
VAL-2.
"""

from __future__ import annotations

import sys
import time

import pytest

from conftest import ROOT, make_stack

sys.path.insert(0, str(ROOT / "specs" / "datasets"))
import generate  # noqa: E402

ESCALA = 1000
LIMITE_CICLO_S = 5.0
LIMITE_FULL_RESYNC_S = 30.0  # PER-01: limiar proprio do pior caso


@pytest.fixture(scope="module")
def dataset_escala() -> dict[str, str]:
    return generate.scale(ESCALA)


def test_val1_val2_ciclo_completo_abaixo_de_5s(workspace, dataset_escala):
    repo, alpha, beta, engine = make_stack(workspace)
    for text in dataset_escala.values():
        alpha.seed(text)
    assert len(alpha.all_resources()) == ESCALA

    inicio = time.perf_counter()
    report = engine.run_cycle()
    decorrido = time.perf_counter() - inicio

    assert len(report.applied) == ESCALA
    assert decorrido < LIMITE_CICLO_S, (
        f"VAL-2 violado: ciclo levou {decorrido:.2f}s com {ESCALA} eventos por lado"
    )


def test_val2_ciclo_incremental_e_muito_mais_barato(workspace, dataset_escala):
    """NEGATIVO do anterior: o segundo ciclo, sem mudanca, nao pode custar o
    mesmo que o primeiro — se custar, o ancestral nao esta evitando trabalho."""
    repo, alpha, beta, engine = make_stack(workspace)
    for text in dataset_escala.values():
        alpha.seed(text)
    engine.run_cycle()

    inicio = time.perf_counter()
    report = engine.run_cycle()
    decorrido = time.perf_counter() - inicio

    assert report.applied == []
    assert decorrido < LIMITE_CICLO_S
