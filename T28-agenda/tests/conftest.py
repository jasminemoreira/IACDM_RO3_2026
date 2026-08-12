"""Fixtures de teste. Os testes verificam specs/validation/acceptance.md e
specs/datasets/expected.md — nao o comportamento do codigo."""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from t28agenda.normalizer import to_canonical, to_ics  # noqa: E402
from t28agenda.providers import ProviderAlpha, ProviderBeta, Scenario, WriteOp  # noqa: E402
from t28agenda.repository import Repository  # noqa: E402
from t28agenda.sync_engine import SyncEngine  # noqa: E402

FIXTURES = ROOT / "specs" / "datasets" / "fixtures"
ANCHOR = datetime.fromisoformat("2026-11-02T12:00:00+00:00")


@pytest.fixture
def fixtures() -> Path:
    if not FIXTURES.exists():  # gera sob demanda: o dataset e deterministico
        sys.path.insert(0, str(ROOT / "specs" / "datasets"))
        import generate

        generate.main(str(FIXTURES))
    return FIXTURES


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    return tmp_path / "ws"


def make_stack(workspace: Path, scenario_b: Scenario | None = None, window=None):
    alpha = ProviderAlpha(workspace / "alpha")
    beta = ProviderBeta(workspace / "beta", scenario_b, window)
    repo = Repository(workspace / "sync.db")
    return repo, alpha, beta, SyncEngine(repo, alpha, beta)


@pytest.fixture
def stack(workspace: Path):
    return make_stack(workspace)


def seed(provider, ics_path: Path) -> str:
    return provider.seed(ics_path.read_text())


def edit(provider, uid: str, bump_sequence: bool = True, **changes):
    """Edicao EXTERNA ao sincronizador — e o que ele precisa detectar."""
    for provider_id, ics in provider.all_resources().items():
        event = to_canonical(ics, provider.dialect)
        if event.uid != uid:
            continue
        if bump_sequence:
            changes["sequence"] = event.sequence + 1
            changes.setdefault("last_modified", (event.last_modified or ANCHOR) + timedelta(minutes=1))
        updated = event.with_fields(**changes)
        provider.write(WriteOp("update", ics=to_ics(updated, provider.dialect), provider_id=provider_id))
        return provider_id
    raise AssertionError(f"uid {uid} ausente no provedor {provider.name}")


def delete(provider, uid: str) -> None:
    for provider_id, ics in provider.all_resources().items():
        if to_canonical(ics, provider.dialect).uid == uid:
            provider.write(WriteOp("delete", provider_id=provider_id))
            return
    raise AssertionError(f"uid {uid} ausente no provedor {provider.name}")


def event_of(provider, uid: str):
    for ics in provider.all_resources().values():
        event = to_canonical(ics, provider.dialect)
        if event.uid == uid:
            return event
    return None
