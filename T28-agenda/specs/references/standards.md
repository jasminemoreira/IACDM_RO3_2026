# Referências normativas — calendários e sincronização

> Depositado na Fase 0 (pesquisa autorizada pelo operador). Toda regra de
> identidade, versionamento e reconciliação usada no design DEVE apontar para
> uma linha desta tabela. Regra AP7: não implementar algoritmo sem referência
> bibliográfica verificável.

## Tabela de referências

| id | Documento | Escopo | URL |
|----|-----------|--------|-----|
| REF-1 | RFC 5545 — Internet Calendaring and Scheduling Core Object Specification (iCalendar) | Modelo de dados do evento: VEVENT, UID, DTSTAMP, DTSTART/DTEND, SEQUENCE, RECURRENCE-ID, RRULE, EXDATE, VTIMEZONE, STATUS | https://datatracker.ietf.org/doc/html/rfc5545 |
| REF-2 | RFC 5546 — iCalendar Transport-Independent Interoperability Protocol (iTIP) | §2.1.5 Message Sequencing: regra normativa de qual revisão de um componente prevalece | https://datatracker.ietf.org/doc/html/rfc5546 |
| REF-3 | RFC 6578 — Collection Synchronization for WebDAV | Protocolo de sync incremental por token: `DAV:sync-collection` REPORT, `DAV:sync-token`, `DAV:sync-level`, remoções como `404`, precondição `DAV:valid-sync-token` | https://datatracker.ietf.org/doc/html/rfc6578 |
| REF-4 | RFC 4791 — Calendaring Extensions to WebDAV (CalDAV) | Coleção de calendário, recurso de evento por URL, ETag como versão opaca do recurso | https://datatracker.ietf.org/doc/html/rfc4791 |
| REF-5 | Google Calendar API — Synchronize resources efficiently | `syncToken` / `nextSyncToken` / `nextPageToken`, HTTP 410 → full sync, entradas deletadas sempre presentes no delta | https://developers.google.com/workspace/calendar/api/guides/sync |
| REF-6 | Microsoft Graph — Get incremental changes to events in a calendar view | `calendarView/delta`, `@odata.nextLink` (`$skiptoken`), `@odata.deltaLink` (`$deltatoken`), `@removed`, `Prefer: odata.maxpagesize` | https://learn.microsoft.com/en-us/graph/delta-query-events |
| REF-7 | Balasubramaniam, S.; Pierce, B. C. — "What is a File Synchronizer?" MobiCom '98, ACM/IEEE, pp. 98-108 | Modelo formal de sincronizador de duas réplicas: estado comum ancestral, detecção de conflito como atualização concorrente divergente, e o critério de "não perder informação sem consentimento" | https://www.researchgate.net/publication/2576101_What_is_a_File_Synchronizer |
| REF-8 | Syncpal: A Simple and Iterative Reconciliation Algorithm for File Synchronizers (Springer, 2019) | Reconciliação iterativa: resolve um conflito por vez garantindo que resolver um não invalida outro | https://link.springer.com/chapter/10.1007/978-3-030-22496-7_1 |
| REF-9 | python-dateutil `rrule` / rrule.js | Expansão de RRULE conforme RFC 5545 (rrule.js é port de dateutil.rrule) | https://dateutil.readthedocs.io/en/stable/rrule.html · https://github.com/jkbrzt/rrule |
| REF-10 | RFC 7986 — New Properties for iCalendar | Propriedades adicionais (COLOR, IMAGE, CONFERENCE) — relevante só para mapeamento de campos além do núcleo | https://datatracker.ietf.org/doc/html/rfc7986 |

## Citações literais que viram regra de design

**REF-2, RFC 5546 §2.1.5 — identidade e precedência (base normativa da detecção de conflito):**

> "The primary key for referencing a particular iCalendar component is the 'UID'
> property value. To reference an instance of a recurring component, the primary
> key is composed of the 'UID' and the 'RECURRENCE-ID' properties."

> "For components where the 'UID' and 'RECURRENCE-ID' property values are the
> same, the component with the highest numeric value for the 'SEQUENCE' property
> obsoletes all other revisions of the component with lower values."

> "In situations where the 'UID', 'RECURRENCE-ID', and 'SEQUENCE' property values
> match, the 'DTSTAMP' property is used as the tie-breaker. The component with the
> latest 'DTSTAMP' overrides all others."

Consequência: a chave de identidade do evento é `(UID, RECURRENCE-ID)` — **não**
o id do provedor. A ordem de precedência normativa é `SEQUENCE` desc, depois
`DTSTAMP` desc. LWW puro por "hora de modificação do provedor" contraria REF-2 e
só é aceitável como desempate de última instância, documentado como tal.

**REF-3, RFC 6578 §3.2 — token opaco e invalidação:**

> "The synchronization token itself MUST be treated as an 'opaque' string by the client."

Remoções são reportadas com `DAV:response` contendo `DAV:status` = `404 Not Found`
(§3.5.2). Token inválido dispara a precondição `DAV:valid-sync-token`, forçando
ressincronização com token vazio.

**REF-7 — critério de conflito (paráfrase da definição formal):**
duas réplicas com um ancestral comum; uma modificação é *não conflitante* quando
apenas uma réplica divergiu do ancestral desde a última reconciliação. Conflito é
divergência **concorrente** de ambas as réplicas em relação ao mesmo ancestral.
Isto exige que o sincronizador **persista o ancestral** (last-synced state) — sem
ele não existe detecção de conflito, apenas heurística de timestamp.
