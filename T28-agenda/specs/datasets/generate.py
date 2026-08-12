"""Gerador de datasets sinteticos determinísticos.

Produzido conforme o Production Capacity Check da Fase 0: o unico ativo de
producao do projeto sao fixtures de teste, geradas pela IA e depositadas aqui.

Determinístico por construcao: nenhuma data "agora", nenhum aleatorio sem
semente. A saida esperada de cada cenario esta em expected.md.

Uso:  python specs/datasets/generate.py <destino>
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

UTC = ZoneInfo("UTC")
SP = "America/Sao_Paulo"

# Ancora fixa do dataset. Escolhida em novembro para que a serie semanal
# atravesse a transicao de horario de verao de fusos do hemisferio norte.
ANCHOR = datetime(2026, 11, 2, 12, 0, tzinfo=UTC)


def vevent(uid: str, start: datetime, minutes: int = 60, summary: str = "", *,
           tzid: str | None = None, rrule: str | None = None, description: str = "",
           location: str = "", sequence: int = 0, recurrence_id: datetime | None = None,
           all_day: bool = False, exdate: datetime | None = None) -> str:
    end = start + timedelta(minutes=minutes)
    if all_day:
        dt_start = f"DTSTART;VALUE=DATE:{start.strftime('%Y%m%d')}"
        dt_end = f"DTEND;VALUE=DATE:{(start + timedelta(days=1)).strftime('%Y%m%d')}"
    elif tzid:
        local_start = start.astimezone(ZoneInfo(tzid))
        local_end = end.astimezone(ZoneInfo(tzid))
        dt_start = f"DTSTART;TZID={tzid}:{local_start.strftime('%Y%m%dT%H%M%S')}"
        dt_end = f"DTEND;TZID={tzid}:{local_end.strftime('%Y%m%dT%H%M%S')}"
    else:
        dt_start = f"DTSTART:{start.strftime('%Y%m%dT%H%M%SZ')}"
        dt_end = f"DTEND:{end.strftime('%Y%m%dT%H%M%SZ')}"

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//T28-agenda//fixtures//",
    ]
    if tzid and not all_day:
        lines += [
            "BEGIN:VTIMEZONE",
            f"TZID:{tzid}",
            "BEGIN:STANDARD",
            "DTSTART:20260101T000000",
            "TZNAME:-03",
            "TZOFFSETFROM:-0300",
            "TZOFFSETTO:-0300",
            "END:STANDARD",
            "END:VTIMEZONE",
        ]
    lines += [
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{ANCHOR.strftime('%Y%m%dT%H%M%SZ')}",
        f"SEQUENCE:{sequence}",
        dt_start,
        dt_end,
        f"SUMMARY:{summary or uid}",
    ]
    if description:
        lines.append(f"DESCRIPTION:{description}")
    if location:
        lines.append(f"LOCATION:{location}")
    if rrule:
        lines.append(f"RRULE:{rrule}")
    if exdate:
        lines.append(f"EXDATE:{exdate.strftime('%Y%m%dT%H%M%SZ')}")
    if recurrence_id:
        lines.append(f"RECURRENCE-ID:{recurrence_id.strftime('%Y%m%dT%H%M%SZ')}")
    lines += [f"LAST-MODIFIED:{ANCHOR.strftime('%Y%m%dT%H%M%SZ')}", "STATUS:CONFIRMED",
              "TRANSP:OPAQUE", "END:VEVENT", "END:VCALENDAR"]
    return "\r\n".join(lines) + "\r\n"


def basic_pair() -> dict[str, str]:
    """Cenario base: um evento em cada lado + um que existe nos dois."""
    return {
        "so-em-a.ics": vevent("so-em-a@t28", ANCHOR + timedelta(days=1), 60, "Revisao de arquitetura"),
        "so-em-b.ics": vevent("so-em-b@t28", ANCHOR + timedelta(days=2), 30, "1:1 com a lider"),
        "compartilhado.ics": vevent(
            "compartilhado@t28", ANCHOR + timedelta(days=3), 90, "Planejamento trimestral",
            location="Sala 4", description="Pauta inicial"
        ),
    }


def recurring() -> dict[str, str]:
    """Serie semanal com EXDATE e uma excecao destacada por RECURRENCE-ID."""
    master_start = ANCHOR + timedelta(days=4)
    skipped = master_start + timedelta(days=14)
    moved = master_start + timedelta(days=7)
    return {
        "serie.ics": vevent(
            "serie@t28", master_start, 30, "Daily do time",
            rrule="FREQ=WEEKLY;COUNT=8", exdate=skipped
        ),
        "serie-excecao.ics": vevent(
            "serie@t28", moved + timedelta(hours=2), 30, "Daily do time (adiado)",
            recurrence_id=moved
        ),
    }


def timezone_and_allday() -> dict[str, str]:
    """all-day em fuso de origem + evento com horario no mesmo dia: e onde a
    regra R-A2 e o erro de fuso aparecem (VAL-7/VAL-8)."""
    day = ANCHOR + timedelta(days=6)
    return {
        "feriado.ics": vevent("feriado@t28", day.replace(hour=0), summary="Feriado local", all_day=True),
        "reuniao-sp.ics": vevent(
            "reuniao-sp@t28", day.replace(hour=14), 60, "Reuniao em Sao Paulo", tzid=SP
        ),
    }


def overlapping() -> dict[str, str]:
    """Um par que se sobrepoe e um par apenas ENCOSTADO (nao e sobreposicao)."""
    base = ANCHOR + timedelta(days=8)
    return {
        "sobrepoe-1.ics": vevent("ov1@t28", base.replace(hour=14), 60, "Dentista"),
        "sobrepoe-2.ics": vevent("ov2@t28", base.replace(hour=14, minute=30), 60, "Retro"),
        "encostado-1.ics": vevent("ed1@t28", base.replace(hour=9), 60, "Cafe"),
        "encostado-2.ics": vevent("ed2@t28", base.replace(hour=10), 60, "Standup"),
    }


def scale(count: int = 1000) -> dict[str, str]:
    """VAL-1: ~1.000 eventos por lado, para medir VAL-2 (< 5 s) de verdade."""
    out: dict[str, str] = {}
    for i in range(count):
        start = ANCHOR + timedelta(days=i % 300, hours=(i % 9) + 8)
        out[f"escala-{i:04d}.ics"] = vevent(f"escala-{i:04d}@t28", start, 30, f"Evento {i}")
    return out


SCENARIOS = {
    "basic": basic_pair,
    "recurring": recurring,
    "timezone": timezone_and_allday,
    "overlapping": overlapping,
}


def main(destination: str, scale_count: int = 0) -> None:
    root = Path(destination)
    for name, builder in SCENARIOS.items():
        folder = root / name
        folder.mkdir(parents=True, exist_ok=True)
        for filename, text in builder().items():
            (folder / filename).write_text(text)
    if scale_count:
        folder = root / "scale"
        folder.mkdir(parents=True, exist_ok=True)
        for filename, text in scale(scale_count).items():
            (folder / filename).write_text(text)
    print(f"fixtures escritas em {root}")


if __name__ == "__main__":
    dest = sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).parent / "fixtures")
    count = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    main(dest, count)
