"""POL-1 a POL-4 — catalogo de politicas (modulo puro, sem I/O)."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from t28agenda.canonical_event import UTC, Event, EventKey, TimeSpec
from t28agenda.policies import ESCALATE, Resolution, resolve
from t28agenda.reconciler import (
    Ancestor, AncestorSide, Conflict, IDENTITY_COLLISION, SAME_FIELD, STRUCTURED_FIELD,
)

T0 = datetime(2026, 11, 2, 12, 0, tzinfo=UTC)


def ev(**changes) -> Event:
    base = Event(
        uid="p@t28",
        start=TimeSpec(datetime(2026, 11, 5, 12, 0, tzinfo=UTC)),
        end=TimeSpec(datetime(2026, 11, 5, 13, 0, tzinfo=UTC)),
        dtstamp=T0, last_modified=T0, summary="base",
    )
    return base.with_fields(**changes)


def conflito(a: Event, b: Event, base_a: Event, base_b: Event, klass=SAME_FIELD, fields=("summary",)):
    return Conflict(EventKey("p@t28"), klass, fields, a, b, base_a, base_b)


def ancestral(seq_a=0, seq_b=0, base: Event | None = None) -> Ancestor:
    base = base or ev()
    return Ancestor(EventKey("p@t28"), AncestorSide(base, "", "", seq_a), AncestorSide(base, "", "", seq_b))


def test_pol1_precedencia_por_delta_de_sequence():
    """POL-1 compara o DELTA relativo ao ancestral de cada lado, nao o SEQUENCE
    absoluto — que diverge entre provedores por construcao (V(3) Regra 1)."""
    base = ev()
    a = ev(summary="A", sequence=11)   # ancestral do lado A estava em 10 -> delta 1
    b = ev(summary="B", sequence=3)    # ancestral do lado B estava em 0  -> delta 3
    outcome = resolve(conflito(a, b, base, base), "pol1", ancestral(seq_a=10, seq_b=0))
    assert isinstance(outcome, Resolution)
    assert outcome.winner == "b", "comparou SEQUENCE absoluto em vez do delta"


def test_pol1_desempate_por_dtstamp():
    base = ev()
    a = ev(summary="A", sequence=1, dtstamp=T0 + timedelta(minutes=5))
    b = ev(summary="B", sequence=1, dtstamp=T0)
    outcome = resolve(conflito(a, b, base, base), "pol1", ancestral())
    assert isinstance(outcome, Resolution) and outcome.winner == "a"


def test_pol1_sem_criterio_algum_escala():
    """NEGATIVO: cascata esgotada nao pode devolver estado indefinido (ASS-05)."""
    base = ev()
    a = ev(summary="A")
    b = ev(summary="B")
    assert resolve(conflito(a, b, base, base), "pol1", ancestral()) == ESCALATE


def test_pol2_sem_last_modified_escala():
    """NEGATIVO: politica sem o dado de entrada que consome nao decide (SCI-01)."""
    base = ev()
    a = ev(summary="A", last_modified=None)
    b = ev(summary="B", last_modified=None)
    assert resolve(conflito(a, b, base, base), "pol2", ancestral()) == ESCALATE


def test_pol2_vence_o_mais_recente():
    base = ev()
    a = ev(summary="A", last_modified=T0)
    b = ev(summary="B", last_modified=T0 + timedelta(hours=1))
    outcome = resolve(conflito(a, b, base, base), "pol2", ancestral())
    assert isinstance(outcome, Resolution) and outcome.winner == "b"


def test_pol3_lado_prioritario_configuravel():
    base = ev()
    a, b = ev(summary="A"), ev(summary="B")
    for lado in ("a", "b"):
        outcome = resolve(conflito(a, b, base, base), "pol3", ancestral(), priority_side=lado)
        assert isinstance(outcome, Resolution) and outcome.winner == lado


def test_pol4_mescla_campos_disjuntos():
    base = ev()
    a = ev(location="Sala 9")
    b = ev(summary="novo titulo")
    outcome = resolve(conflito(a, b, base, base, fields=()), "pol4", ancestral())
    assert isinstance(outcome, Resolution)
    assert outcome.event.location == "Sala 9" and outcome.event.summary == "novo titulo"


def test_pol4_colisao_real_no_mesmo_campo_escala():
    """NEGATIVO: mesmo campo com valores diferentes nao mescla."""
    base = ev()
    a, b = ev(summary="A"), ev(summary="B")
    assert resolve(conflito(a, b, base, base), "pol4", ancestral()) == ESCALATE


def test_campo_estruturado_escala_em_qualquer_politica():
    """NEGATIVO (R-A1): nenhuma politica pode decidir sozinha em attendees/RRULE."""
    base = ev()
    a, b = ev(attendees=("mailto:a@x",)), ev(attendees=("mailto:b@x",))
    for politica in ("pol1", "pol2", "pol3", "pol4"):
        c = conflito(a, b, base, base, klass=STRUCTURED_FIELD, fields=("attendees",))
        assert resolve(c, politica, ancestral()) == ESCALATE


def test_identity_collision_escala_em_qualquer_politica():
    """NEGATIVO (ASS-12): sem ancestral nao ha delta, entao nada a comparar."""
    a, b = ev(summary="A"), ev(summary="B")
    c = conflito(a, b, None, None, klass=IDENTITY_COLLISION, fields=())
    for politica in ("pol1", "pol2", "pol3", "pol4"):
        assert resolve(c, politica, None) == ESCALATE


def test_politica_manual_nunca_resolve_sozinha():
    base = ev()
    a, b = ev(summary="A"), ev(summary="B")
    assert resolve(conflito(a, b, base, base), "manual", ancestral()) == ESCALATE


def test_politica_desconhecida_e_erro():
    base = ev()
    with pytest.raises(ValueError):
        resolve(conflito(ev(), ev(), base, base), "pol9", ancestral())
