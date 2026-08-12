"""M-02 recurrence — expansao de series dentro da expansion_window.

S6 Tier 1: a expansao e feita por `recurring-ical-events`, que trata RRULE,
EXDATE, RDATE e instancias destacadas por RECURRENCE-ID de fabrica (REF-9 e
specs/examples/reference-snippets.md). Escrever expansor proprio e proibido —
e a fonte n.1 de bug relatada no levantamento de competidores.

A unidade de entrada e um VCALENDAR com o mestre e suas excecoes agrupados por
UID (achado IMP-03): expandir um VEVENT isolado perderia as excecoes.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

import recurring_ical_events
from icalendar import Calendar

from .canonical_event import UTC, EventKey, Occurrence
from .normalizer import vevent_to_canonical

# Teto por serie (MEC-D): protege contra RRULE sem UNTIL/COUNT — cenario SEC-01,
# em que FREQ=SECONDLY expandiria indefinidamente.
MAX_INSTANCES_PER_SERIES = 10_000


@dataclass(frozen=True, slots=True)
class ExpansionWindow:
    """Janela de EXPANSAO de recorrencia.

    Distinta de `observability_window`, que e do provedor e decide PRESENCA
    (achado ASS-11 / correcao C-3). Os dois nomes nunca se substituem.
    """

    start: datetime
    end: datetime

    @staticmethod
    def default(today: datetime) -> ExpansionWindow:
        return ExpansionWindow(today - timedelta(days=30), today + timedelta(days=365))


def build_calendar(ics_resources: list[str]) -> Calendar:
    """Agrupa recursos ics num unico VCALENDAR — mestre e excecoes juntos."""
    cal = Calendar()
    cal.add("PRODID", "-//T28-agenda//PT-BR//")
    cal.add("VERSION", "2.0")
    for text in ics_resources:
        source = Calendar.from_ical(text)
        for comp in source.walk():
            if comp.name in ("VEVENT", "VTIMEZONE"):
                cal.add_component(comp)
    return cal


def expand(
    calendar: Calendar,
    window: ExpansionWindow,
    origin: str = "",
    calendar_tz: str = "UTC",
) -> list[Occurrence]:
    """VCALENDAR -> ocorrencias materializadas dentro da janela, em UTC."""
    out: list[Occurrence] = []
    counts: dict[str, int] = {}
    for comp in recurring_ical_events.of(calendar).between(window.start, window.end):
        event = vevent_to_canonical(comp, calendar_tz)
        if event.cancelled or event.transparency.upper() == "TRANSPARENT":
            continue  # nao ocupa: STATUS:CANCELLED / TRANSP:TRANSPARENT
        counts[event.uid] = counts.get(event.uid, 0) + 1
        if counts[event.uid] > MAX_INSTANCES_PER_SERIES:
            raise ValueError(
                f"serie {event.uid} excede {MAX_INSTANCES_PER_SERIES} instancias na janela"
            )
        start_utc, end_utc = event.occupies()
        out.append(
            Occurrence(
                key=EventKey(event.uid, event.recurrence_id),
                start_utc=start_utc,
                end_utc=end_utc,
                summary=event.summary,
                origin=origin,
                all_day=event.all_day,
            )
        )
    return sorted(out, key=lambda o: (o.start_utc, o.end_utc, str(o.key)))


def now_utc() -> datetime:
    return datetime.now(tz=UTC)
