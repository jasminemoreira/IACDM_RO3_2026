"""M-03 normalizer — traducao ics <-> canonico, conformidade e fingerprint.

Tier 1 (S6): parsing e serializacao por `icalendar` 7.2.2; VTIMEZONE gerado por
`icalendar.Timezone.from_tzinfo()` (verificado por execucao na Fase 3, achado
REG-04 — nao e Tier 3 escondido).

Fingerprint (MEC-A + V(3) Regra 1): identidade de CONTEUDO, usada para detectar
que uma mudanca vinda do provedor e apenas o eco da nossa propria escrita.
Convencao do projeto, analoga a semantica de ETag (REF-4) — nao e regra normativa.
"""

from __future__ import annotations

import hashlib
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from icalendar import Calendar, Event as IcsEvent, Timezone

from .canonical_event import UTC, Event, TimeSpec

FINGERPRINT_VERSION = 1

# Dialetos dos dois provedores heterogeneos. A diferenca nao e cosmetica: o
# dialeto `beta` TRUNCA a descricao ao gravar, reproduzindo a normalizacao
# semanticamente visivel do provedor que gerou o achado CTL-04.
DIALECTS: dict[str, dict[str, object]] = {
    "alpha": {"id_prop": "X-ALPHA-ID", "truncate_description": None},
    "beta": {"id_prop": "X-BETA-ID", "truncate_description": 200},
}


class ConformanceError(ValueError):
    """Entrada que viola RFC 5545 de forma nao recuperavel (REG-01/MEC-02)."""


def _as_timespec(prop, calendar_tz: str = "UTC") -> TimeSpec:
    """Converte propriedade temporal para TimeSpec.

    Valores DATE (all-day) NAO carregam TZID — RFC 5545 §3.3.4 os define como
    flutuantes. A regra R-A2 exige o fuso do CALENDARIO de origem, por isso ele
    entra por parametro: e propriedade do provedor, nao do evento.
    """
    value = prop.dt
    tzid = prop.params.get("TZID")
    if isinstance(value, datetime):
        if value.tzinfo is None:  # hora flutuante: interpretada como UTC, declarado
            value = value.replace(tzinfo=UTC)
        return TimeSpec(value.astimezone(UTC), tzid, is_date=False)
    if isinstance(value, date):
        zone_id = tzid or calendar_tz
        zone = _zone(zone_id)
        return TimeSpec(
            datetime(value.year, value.month, value.day, tzinfo=zone).astimezone(UTC),
            zone_id,
            is_date=True,
        )
    raise ConformanceError(f"valor temporal nao suportado: {value!r}")


def _zone(tzid: str) -> ZoneInfo:
    try:
        return ZoneInfo(tzid)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        # MEC-02: TZID desconhecido falha RUIDOSAMENTE. Cair para UTC em silencio
        # deslocaria o evento sem que ninguem percebesse.
        raise ConformanceError(f"TZID desconhecido na base tz local: {tzid}") from exc


def _text(comp, name: str) -> str:
    value = comp.get(name)
    return "" if value is None else str(value)


def _datetimes(comp, name: str) -> tuple[datetime, ...]:
    prop = comp.get(name)
    if prop is None:
        return ()
    props = prop if isinstance(prop, list) else [prop]
    out: list[datetime] = []
    for p in props:
        for item in getattr(p, "dts", []):
            value = item.dt
            if isinstance(value, datetime):
                out.append(value.astimezone(UTC) if value.tzinfo else value.replace(tzinfo=UTC))
            else:
                out.append(datetime(value.year, value.month, value.day, tzinfo=UTC))
    return tuple(sorted(out))


def to_canonical(ics_text: str, dialect: str = "alpha", calendar_tz: str = "UTC") -> Event:
    """ics de UM recurso -> Event canonico."""
    if dialect not in DIALECTS:
        raise ValueError(f"dialeto desconhecido: {dialect}")
    cal = Calendar.from_ical(ics_text)
    vevents = list(cal.walk("VEVENT"))
    if not vevents:
        raise ConformanceError("recurso sem VEVENT")
    return vevent_to_canonical(vevents[0], calendar_tz)


def vevent_to_canonical(comp, calendar_tz: str = "UTC") -> Event:
    uid = _text(comp, "UID")
    if not uid:
        # ASS-03: UID e obrigatorio (RFC 5545 §3.8.4.7). Sem ele nao ha identidade
        # possivel; derivar um seria inventar chave que o outro lado nao conhece.
        raise ConformanceError("VEVENT sem UID: identidade indeterminavel")
    if "DTSTART" not in comp:
        raise ConformanceError("VEVENT sem DTSTART")
    start = _as_timespec(comp["DTSTART"], calendar_tz)

    if "DTEND" in comp:
        end = _as_timespec(comp["DTEND"], calendar_tz)
    elif "DURATION" in comp:  # ASS-04: RFC 5545 permite DURATION no lugar de DTEND
        end = TimeSpec(start.instant_utc + comp["DURATION"].dt, start.tzid, start.is_date)
    elif start.is_date:
        end = TimeSpec(start.instant_utc + timedelta(days=1), start.tzid, True)
    else:
        end = start

    rid_prop = comp.get("RECURRENCE-ID")
    recurrence_id = _as_timespec(rid_prop, calendar_tz).instant_utc if rid_prop is not None else None
    dtstamp = comp["DTSTAMP"].dt.astimezone(UTC) if "DTSTAMP" in comp else None
    last_mod = comp["LAST-MODIFIED"].dt.astimezone(UTC) if "LAST-MODIFIED" in comp else None

    rrule = comp.get("RRULE")
    attendees = comp.get("ATTENDEE")
    if attendees is None:
        attendee_list: tuple[str, ...] = ()
    else:
        items = attendees if isinstance(attendees, list) else [attendees]
        attendee_list = tuple(sorted(str(a) for a in items))

    return Event(
        uid=uid,
        start=start,
        end=end,
        recurrence_id=recurrence_id,
        sequence=int(comp.get("SEQUENCE", 0)),
        dtstamp=dtstamp,
        last_modified=last_mod,
        summary=_text(comp, "SUMMARY"),
        location=_text(comp, "LOCATION"),
        description=_text(comp, "DESCRIPTION"),
        status=_text(comp, "STATUS") or "CONFIRMED",
        transparency=_text(comp, "TRANSP") or "OPAQUE",
        rrule=rrule.to_ical().decode() if rrule is not None else None,
        exdate=_datetimes(comp, "EXDATE"),
        rdate=_datetimes(comp, "RDATE"),
        attendees=attendee_list,
    )


def _to_vevent(event: Event, dialect: str) -> IcsEvent:
    cfg = DIALECTS[dialect]
    comp = IcsEvent()
    comp.add("UID", event.uid)
    comp.add("DTSTAMP", event.dtstamp or datetime(2026, 1, 1, tzinfo=UTC))
    comp.add("SEQUENCE", event.sequence)
    description = event.description
    limit = cfg["truncate_description"]
    if isinstance(limit, int) and len(description) > limit:
        description = description[:limit]  # normalizacao do provedor (CTL-04)

    def _value(spec: TimeSpec):
        if spec.is_date:
            return spec.as_utc().date()
        if spec.tzid:
            return spec.as_utc().astimezone(_zone(spec.tzid))
        return spec.as_utc()

    comp.add("DTSTART", _value(event.start))
    comp.add("DTEND", _value(event.end))
    if event.summary:
        comp.add("SUMMARY", event.summary)
    if event.location:
        comp.add("LOCATION", event.location)
    if description:
        comp.add("DESCRIPTION", description)
    comp.add("STATUS", event.status)
    comp.add("TRANSP", event.transparency)
    if event.last_modified:
        comp.add("LAST-MODIFIED", event.last_modified)
    if event.recurrence_id:
        comp.add("RECURRENCE-ID", event.recurrence_id)
    if event.rrule:
        comp.add("RRULE", _parse_rrule(event.rrule))
    for exd in event.exdate:
        comp.add("EXDATE", exd)
    for rd in event.rdate:
        comp.add("RDATE", rd)
    for att in event.attendees:
        comp.add("ATTENDEE", att)
    return comp


def _parse_rrule(text: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for part in text.replace("RRULE:", "").split(";"):
        if "=" in part:
            name, _, value = part.partition("=")
            out[name.strip().upper()] = value.split(",")
    return out


def to_ics(event: Event, dialect: str = "alpha") -> str:
    """Event canonico -> ics de um recurso, conforme RFC 5545.

    REG-02: TZID nao-UTC exige o bloco VTIMEZONE embutido, senao a saida nao e
    interoperavel. Gerado por icalendar.Timezone.from_tzinfo (verificado).
    """
    cal = Calendar()
    cal.add("PRODID", "-//T28-agenda//PT-BR//")
    cal.add("VERSION", "2.0")
    for tzid in {s.tzid for s in (event.start, event.end) if s and s.tzid}:
        anchor = event.start.as_utc()
        cal.add_component(
            Timezone.from_tzinfo(
                _zone(tzid),
                first_date=(anchor - timedelta(days=400)).replace(tzinfo=None),
                last_date=(anchor + timedelta(days=400)).replace(tzinfo=None),
            )
        )
    cal.add_component(_to_vevent(event, dialect))
    return cal.to_ical().decode()


# --- Fingerprint ------------------------------------------------------------
# Regras declaradas (achado IMP-06): colecoes ordenadas por chave natural;
# CRLF -> LF; trim das bordas; caixa preservada; EXCLUIDOS sequence, dtstamp,
# last_modified, PRODID, ids de provedor e ordem das propriedades.


def _norm_text(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n").strip()


def fingerprint(event: Event) -> str:
    parts = [
        f"v{FINGERPRINT_VERSION}",
        event.uid,
        event.recurrence_id.isoformat() if event.recurrence_id else "",
        event.start.as_utc().isoformat(),
        event.end.as_utc().isoformat(),
        "date" if event.all_day else "datetime",
        _norm_text(event.summary),
        _norm_text(event.location),
        _norm_text(event.description),
        event.status.upper(),
        event.transparency.upper(),
        _norm_text(event.rrule or ""),
        ",".join(sorted(d.isoformat() for d in event.exdate)),
        ",".join(sorted(d.isoformat() for d in event.rdate)),
        ",".join(sorted(_norm_text(a) for a in event.attendees)),
    ]
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()[:32]
