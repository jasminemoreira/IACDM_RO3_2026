# Implementações de referência (S6 Tier 1/2) — consultar ANTES de codar

Cada trecho vem da documentação oficial da lib/protocolo. Portar a forma, não
improvisar.

## Expansão de recorrência com `recurring-ical-events` (M-02)

Trata `RRULE`, `EXDATE`, `RDATE` e instâncias destacadas por `RECURRENCE-ID` de
fábrica — é a razão de ser Tier 1 (REF-9 e doc da lib).

```python
import icalendar, recurring_ical_events
from datetime import datetime
from zoneinfo import ZoneInfo

cal = icalendar.Calendar.from_ical(ics_text)
start = datetime(2026, 8, 1, tzinfo=ZoneInfo("UTC"))
end   = datetime(2026, 9, 1, tzinfo=ZoneInfo("UTC"))

for occ in recurring_ical_events.of(cal).between(start, end):
    occ["DTSTART"].dt   # instância materializada, já com exceções aplicadas
    occ["UID"]
    occ.get("RECURRENCE-ID")
```

Cuidado: `DTSTART` de evento all-day vem como `date`, não `datetime` — é onde
R-A2 se aplica (converter para `[00:00, 24:00)` no `tzid` do calendário antes de
comparar).

## Leitura de `.ics` e round-trip (M-03)

```python
from icalendar import Calendar, Event as IcsEvent
cal = Calendar.from_ical(text)
for comp in cal.walk("VEVENT"):
    comp.get("UID"); comp.get("SEQUENCE"); comp.get("DTSTAMP").dt
    dtstart = comp["DTSTART"]
    tzid = dtstart.params.get("TZID")          # None em UTC/flutuante
    is_all_day = not hasattr(dtstart.dt, "hour")
out = cal.to_ical()                            # serialização
```

## Precedência normativa (M-07, POL-1) — RFC 5546 §2.1.5

Portar **literalmente**, citando a seção no código:

```
def newer(x, y):                 # x obsoleta y?
    if x.sequence != y.sequence: return x.sequence > y.sequence
    return x.dtstamp > y.dtstamp          # desempate normativo
```

## Forma do delta dos provedores (M-04, M-05)

Estilo Google (REF-5) — tombstone dentro do próprio delta:
```json
{"items": [{"id": "abc", "status": "cancelled"}, {"id": "def", "...": "..."}],
 "nextPageToken": null, "nextSyncToken": "CPjJ..."}
```
HTTP 410 ⇒ descartar token e refazer full sync.

Estilo Graph (REF-6) — remoção como `@removed`, janela codificada no token:
```json
{"@odata.deltaLink": "…/calendarView/delta?$deltatoken=R0us…",
 "value": [{"id": "AAM…", "@removed": {"reason": "deleted"}}, {"id": "…"}]}
```
Um round termina quando vem `@odata.deltaLink` em vez de `@odata.nextLink`.

## Varredura ordenada para sobreposição (M-09)

Algoritmo clássico; O(n log n) exigido por VAL-3. Predicado semiaberto — eventos
encostados **não** sobrepõem:

```python
def find_overlaps(occs):                 # occs: [(start_utc, end_utc, ref)]
    occs = sorted(occs, key=lambda o: o[0])
    active, out = [], []
    for s, e, ref in occs:
        active = [a for a in active if a[1] > s]     # expira encerrados
        out += [(a[2], ref) for a in active]          # a.start < e e s < a.end
        active.append((s, e, ref))
    return out
```

## Commit atômico (M-11)

```python
with sqlite3.connect(db) as conn:        # commit/rollback automático
    conn.execute("BEGIN IMMEDIATE")
    ...  # ancestor + identity_map + sync_state + conflict juntos
```
A escrita no provedor acontece **fora** desta transação (PR-6) — a ordem correta
é: escrever no provedor → obter a versão resultante → commit local incluindo essa
versão. Falha entre os dois passos é cenário para a Fase 2 atacar.
