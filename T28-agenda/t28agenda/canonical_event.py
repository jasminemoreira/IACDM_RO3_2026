"""M-01 canonical-event — modelo canonico imutavel e chave de identidade.

Regra normativa: a chave primaria e o UID; para instancia de serie e o par
(UID, RECURRENCE-ID).  RFC 5546 §2.1.5 (specs/references/standards.md REF-2).
O id do provedor NUNCA e identidade — ele vive no mapa de identidade (M-11).

Modulo PURO: sem I/O, sem provedor, sem banco.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

UTC = ZoneInfo("UTC")

# Campos que participam do merge 3-vias por campo (POL-4).
SCALAR_FIELDS = (
    "start",
    "end",
    "all_day",
    "summary",
    "location",
    "description",
    "status",
    "transparency",
)
# Campos que NUNCA mesclam: qualquer mudanca concorrente escala para conflito.
# Regra R-A1 (specs/technical/conflict-model.md): mesclar duas RRULE divergentes
# nao tem semantica definida pela norma, e attendees pertence ao iTIP.
STRUCTURED_FIELDS = ("rrule", "exdate", "rdate", "attendees")


@dataclass(frozen=True, slots=True)
class TimeSpec:
    """Instante absoluto para comparacao + TZID original preservado para gravacao.

    PR-5: comparar em UTC nao pode perder a informacao necessaria para gravar.
    `is_date` marca valor DATE (all-day) contra DATE-TIME — RFC 5545 §3.3.4/3.3.5.
    """

    instant_utc: datetime
    tzid: str | None = None
    is_date: bool = False

    def __post_init__(self) -> None:
        if self.instant_utc.tzinfo is None:
            raise ValueError("TimeSpec.instant_utc precisa ser timezone-aware")

    def as_utc(self) -> datetime:
        return self.instant_utc.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class EventKey:
    uid: str
    recurrence_id: datetime | None = None

    def as_row(self) -> tuple[str, str]:
        """Forma de persistencia. `''` em vez de NULL porque NULL nao compara em
        chave primaria no SQLite (specs/models/data-model.md)."""
        return (self.uid, self.recurrence_id.isoformat() if self.recurrence_id else "")

    @staticmethod
    def from_row(uid: str, recurrence_id: str) -> EventKey:
        return EventKey(uid, datetime.fromisoformat(recurrence_id) if recurrence_id else None)

    def __str__(self) -> str:
        return self.uid if self.recurrence_id is None else f"{self.uid}#{self.recurrence_id.isoformat()}"


@dataclass(frozen=True, slots=True)
class Event:
    """Evento canonico. `sequence`/`dtstamp` sao metadados de revisao LOCAIS de
    cada provedor: entram na precedencia (POL-1) mas NAO no fingerprint nem na
    sincronizacao de conteudo — V(3) Regra 1 / V(4)."""

    uid: str
    start: TimeSpec
    end: TimeSpec
    recurrence_id: datetime | None = None
    sequence: int = 0
    dtstamp: datetime | None = None
    last_modified: datetime | None = None
    summary: str = ""
    location: str = ""
    description: str = ""
    status: str = "CONFIRMED"
    transparency: str = "OPAQUE"
    rrule: str | None = None
    exdate: tuple[datetime, ...] = ()
    rdate: tuple[datetime, ...] = ()
    attendees: tuple[str, ...] = ()

    @property
    def all_day(self) -> bool:
        return self.start.is_date

    @property
    def key(self) -> EventKey:
        return EventKey(self.uid, self.recurrence_id)

    @property
    def cancelled(self) -> bool:
        return self.status.upper() == "CANCELLED"

    def scalar_fields(self) -> dict[str, object]:
        return {name: getattr(self, name) for name in SCALAR_FIELDS}

    def structured_fields(self) -> dict[str, object]:
        return {name: getattr(self, name) for name in STRUCTURED_FIELDS}

    def with_fields(self, **changes: object) -> Event:
        return replace(self, **changes)  # type: ignore[arg-type]

    def occupies(self) -> tuple[datetime, datetime]:
        """Intervalo semiaberto ocupado, em UTC.

        Regra R-A2 (decisao do operador na Fase 0): evento all-day ocupa
        [00:00, 24:00) no fuso do calendario de origem e BLOQUEIA.
        """
        start = self.start.as_utc()
        if self.all_day:
            end = self.end.as_utc() if self.end else start + timedelta(days=1)
            if end <= start:
                end = start + timedelta(days=1)
            return start, end
        return start, self.end.as_utc()


def key(event: Event) -> EventKey:
    return event.key


# --- Side: presenca observavel (V(3) Regra 2 / MEC-C) ------------------------
# `Absent` e "comprovadamente inexistente"; `Unobservable` e "fora da janela de
# observabilidade do provedor ou indeterminado" e NUNCA pode virar delecao.


@dataclass(frozen=True, slots=True)
class Present:
    event: Event
    partial: bool = False  # item resumido vindo de paginacao: nao reconcilia


@dataclass(frozen=True, slots=True)
class Absent:
    pass


@dataclass(frozen=True, slots=True)
class Unobservable:
    reason: str = "fora da observability_window"


Side = Present | Absent | Unobservable

ABSENT = Absent()


@dataclass(frozen=True, slots=True)
class Occurrence:
    """Instancia materializada de um evento dentro de uma expansion_window."""

    key: EventKey
    start_utc: datetime
    end_utc: datetime
    summary: str
    origin: str  # nome do provedor de origem, para o relatorio de sobreposicao
    all_day: bool = False
