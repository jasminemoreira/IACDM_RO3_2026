# Protocolos de sync incremental dos provedores externos

> Fonte: REF-3, REF-5, REF-6 em `specs/references/standards.md`.
> Todo parâmetro abaixo é citado, nenhum é inferido.

## Padrão comum aos três protocolos

Os três (Google, Microsoft Graph, CalDAV/RFC 6578) implementam a **mesma forma
abstrata**, o que permite uma interface única de adaptador:

1. **Full sync inicial** → devolve todos os itens + um token de estado.
2. **Paginação** → um token de "há mais páginas" que NÃO é o token de estado final.
3. **Delta incremental** → passa o token de estado, recebe só o que mudou, incluindo remoções.
4. **Invalidação do token** → erro específico ⇒ descartar estado local e refazer full sync.

| Conceito abstrato | Google Calendar (REF-5) | Microsoft Graph (REF-6) | CalDAV / RFC 6578 (REF-3) |
|---|---|---|---|
| Token de estado | `nextSyncToken` (enviado como `syncToken`) | `@odata.deltaLink` contendo `$deltatoken` | `DAV:sync-token` |
| Token de paginação | `nextPageToken` (enviado como `pageToken`) | `@odata.nextLink` contendo `$skiptoken` | (paginação via `DAV:limit` / múltiplos REPORTs) |
| Remoção no delta | entrada com `status = "cancelled"` — "the result will always contain deleted entries" | objeto com `"@removed": {"reason": "deleted"}` | `DAV:response` com `DAV:status` = `404 Not Found` (§3.5.2) |
| Token inválido | HTTP **410 GONE** ⇒ limpar store local e refazer full sync | ressincronizar a partir de request inicial | precondição `DAV:valid-sync-token` ⇒ REPORT com token vazio |
| Versão do item | `etag` do recurso | `@odata.etag` | `ETag` (REF-4) |
| Tamanho de página | parâmetro `maxResults` | header `Prefer: odata.maxpagesize={x}` | `DAV:limit`/`DAV:nresults` |
| Escopo da consulta | mesmos query params em TODAS as páginas de um round (params divergentes ⇒ HTTP 400) | `startDateTime`/`endDateTime` obrigatórios e codificados dentro do token; `$select` NÃO é suportado | `DAV:sync-level` = `1` (filhos imediatos) ou `infinite` |

## Regras operacionais citadas (não inferidas)

- **Google (REF-5):** "Each list request should use the same set of query
  parameters, including the initial request." Parâmetros não permitidos devolvem
  HTTP 400. Tokens expiram por inatividade ou "changes in related ACLs". Ao
  paginar, novas entradas criadas durante a paginação não são perdidas.
- **Google (REF-5):** o delta **sempre** contém as entradas deletadas, "so that
  the clients get the chance to remove them from storage" — o sincronizador não
  precisa inferir deleção por ausência.
- **Microsoft (REF-6):** os state tokens são **opacos** e já codificam
  `startDateTime`/`endDateTime` e demais query params do request inicial; não
  reenviar esses params nos requests subsequentes. Um round termina quando a
  resposta traz `@odata.deltaLink` em vez de `@odata.nextLink`.
- **Microsoft (REF-6):** `calendarView/delta` é **ligado a uma janela temporal
  fixa** (start/end). Sincronizar múltiplos calendários exige rastrear cada um
  individualmente. Delta de calendário **sem** janela fixa só existe em `/beta`.
- **RFC 6578 (REF-3):** o token "MUST be treated as an 'opaque' string by the
  client" — proibido parsear, comparar ordinalmente ou derivar timestamp dele.

## Armadilhas documentadas (entram como premissas de risco na Fase 2)

| # | Armadilha | Fonte |
|---|-----------|-------|
| A-1 | Token de sync pode ser invalidado a qualquer momento pelo servidor (semanas de inatividade, mudança de ACL) ⇒ o caminho de full-resync não é excepcional, é rotina | REF-5 |
| A-2 | `calendarView/delta` do Graph pode devolver mais itens que `maxpagesize` quando um mestre recorrente é expandido, e há relatos de `@odata.nextLink` reapresentando itens já recebidos (loop infinito de paginação) | REF-6 + issue msgraph-sdk-dotnet #3070 |
| A-3 | Duplicatas na paginação exigem idempotência por `(UID, RECURRENCE-ID)` no aplicador de mudanças, e um limite máximo de páginas por round como circuit breaker | REF-6, A-2 |
| A-4 | Janela temporal do Graph é obrigatória: eventos fora de `[startDateTime, endDateTime]` **não existem** para o sincronizador. Um evento movido para fora da janela aparece como remoção, não como update | REF-6 |
| A-5 | Eco de sincronização: uma escrita feita pelo sincronizador no provedor B retorna no próximo delta de B como "mudança externa". Sem marcação de origem, gera loop infinito de sync | REF-7 (necessidade de ancestral) |

## Semântica de identidade e recorrência (REF-1, REF-2)

- Chave primária do evento: `UID`. Instância de série: `(UID, RECURRENCE-ID)`.
- `SEQUENCE`: inteiro monotônico incrementado pelo organizador a cada revisão
  significativa. Maior `SEQUENCE` **obsoleta** revisões menores (REF-2 §2.1.5).
- `DTSTAMP`: desempate quando `UID`+`RECURRENCE-ID`+`SEQUENCE` são iguais — o
  `DTSTAMP` mais recente prevalece (REF-2 §2.1.5).
- `RRULE` define a série; `RECURRENCE-ID` identifica uma **exceção** (instância
  destacada); `EXDATE` remove instâncias. Expansão de RRULE conforme REF-9 —
  **não** escrever expansor próprio (S6 Tier 1).
- `DTSTART`/`DTEND` com `TZID` referenciam um `VTIMEZONE`; comparação temporal
  entre dois provedores DEVE ser feita em instante absoluto (UTC), preservando o
  `TZID` original para gravação (evento all-day é DATE, não DATE-TIME — comparar
  all-day com timed exige regra explícita).
