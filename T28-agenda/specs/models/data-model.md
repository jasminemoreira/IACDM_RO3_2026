# Modelo de dados — T28-agenda

Value objects **imutáveis** (Domain Model enxuto). Nenhum objeto de domínio
conhece SQLite ou provedor.

## Evento canônico (M-01)

| campo | tipo | origem iCalendar | participa do merge? |
|---|---|---|---|
| `uid` | str | `UID` | não (é identidade) |
| `recurrence_id` | datetime\|None | `RECURRENCE-ID` | não (é identidade) |
| `sequence` | int | `SEQUENCE` | não (é versão, REF-2) |
| `dtstamp` | datetime (UTC) | `DTSTAMP` | não (é desempate, REF-2) |
| `start` / `end` | `TimeSpec` | `DTSTART`/`DTEND` | **escalar** |
| `all_day` | bool | valor `DATE` vs `DATE-TIME` | **escalar** |
| `summary` | str | `SUMMARY` | **escalar** |
| `location` | str | `LOCATION` | **escalar** |
| `description` | str | `DESCRIPTION` | **escalar** |
| `status` | enum | `STATUS` | **escalar** |
| `transparency` | enum | `TRANSP` | **escalar** |
| `rrule` / `exdate` / `rdate` | estrutura | `RRULE`/`EXDATE`/`RDATE` | **estruturado → escala (R-A1)** |
| `attendees` | lista | `ATTENDEE` | **estruturado → escala (R-A1)** |

`TimeSpec` = `{ instant_utc: datetime, tzid: str|None, is_date: bool }` —
comparação sempre por `instant_utc`; `tzid` preservado para gravação (PR-5).

`EventKey` = `(uid, recurrence_id)`. **Nunca** o id do provedor.

## Ancestral (M-11)

```
Ancestor = {
  key: EventKey,
  snapshot: Event,              # estado na última sync bem-sucedida
  version_a: str|None,          # ETag/versão resultante da última escrita em A
  version_b: str|None,          # idem em B
  suspended: bool,              # R-A3: saiu da janela observável, não foi deletado
  synced_at: datetime
}
```
`version_a`/`version_b` são o mecanismo de neutralização de eco (A-5): a versão
devolvida por `write()` é gravada aqui **no mesmo commit**.

## Mapa de identidade (M-11)

`(provider, provider_id) -> EventKey`, com unicidade nos dois sentidos.
Existe porque o mesmo evento tem ids locais diferentes em cada provedor e o
`UID` é o único elo estável.

## Conflito (M-08)

```
Conflict = {
  id: str, key: EventKey,
  klass: SAME_FIELD | DELETE_VS_UPDATE | UPDATE_VS_DELETE
       | STRUCTURED_FIELD | IDENTITY_COLLISION,
  fields: [str],                 # campos em colisão
  value_a, value_b, value_ancestor,
  state: OPEN | RESOLVED,
  resolution: TAKE_A | TAKE_B | MERGE | None,
  detected_at, resolved_at
}
```
Enquanto `state = OPEN`, **nada daquela chave é aplicado em nenhum dos lados.**

## Estado de sincronização (M-11)

`(provider) -> state_token: str|None` — opaco (RFC 6578 §3.2). `None` significa
"full sync no próximo ciclo".

## Esquema SQLite (M-11)

```sql
CREATE TABLE ancestor (
  uid TEXT NOT NULL, recurrence_id TEXT NOT NULL DEFAULT '',
  snapshot_ics TEXT NOT NULL,
  version_a TEXT, version_b TEXT,
  suspended INTEGER NOT NULL DEFAULT 0,
  synced_at TEXT NOT NULL,
  PRIMARY KEY (uid, recurrence_id)
);
CREATE TABLE identity_map (
  provider TEXT NOT NULL, provider_id TEXT NOT NULL,
  uid TEXT NOT NULL, recurrence_id TEXT NOT NULL DEFAULT '',
  PRIMARY KEY (provider, provider_id)
);
CREATE UNIQUE INDEX ix_identity_key ON identity_map(provider, uid, recurrence_id);
CREATE TABLE sync_state (provider TEXT PRIMARY KEY, state_token TEXT);
CREATE TABLE conflict (
  id TEXT PRIMARY KEY, uid TEXT NOT NULL, recurrence_id TEXT NOT NULL DEFAULT '',
  klass TEXT NOT NULL, fields_json TEXT NOT NULL,
  value_a_ics TEXT, value_b_ics TEXT, value_ancestor_ics TEXT,
  state TEXT NOT NULL, resolution TEXT,
  detected_at TEXT NOT NULL, resolved_at TEXT
);
CREATE INDEX ix_conflict_open ON conflict(state);
```
`recurrence_id` usa `''` em vez de `NULL` porque `NULL` não compara em chave
primária no SQLite — evento simples e instância destacada precisam coexistir.

## Relatório do ciclo (M-10 → M-12)

```
SyncReport = { pulled: {a: n, b: n}, applied: [Action], skipped_noop: n,
               conflicts_opened: [id], suspended: [EventKey],
               full_resync: [provider], duration_s: float, dry_run: bool }
```
`applied` vazio com `skipped_noop > 0` num segundo ciclo é a evidência de VAL-4.
