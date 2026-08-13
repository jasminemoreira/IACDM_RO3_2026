# Tarefa — dizer quais lentes de crítica esta arquitetura aciona

Você recebe a decomposição arquitetural de um sistema. Diga **quais lentes de crítica
aquela arquitetura aciona**, e por qual sinal dela.

Não escreva código, não faça perguntas, não busque nada fora deste texto.

---

## O problema

> Sincronizador entre dois calendários externos, com detecção e resolução de conflito

## A arquitetura

## V(1) — Decomposição

| id | module | responsibility | interface | depends-on |
|------|--------|----------------|-----------|------------|
| M-01 | canonical-event | Modelo canônico imutável do evento e chave de identidade UID + RECURRENCE-ID | Event, Occurrence, EventKey; key(event) -> EventKey; scalar_fields(event) -> dict | nenhuma |
| M-02 | recurrence | Expandir série em ocorrências numa janela aplicando EXDATE, RDATE e exceções RECURRENCE-ID | expand(calendar, window) -> lista de Occurrence | canonical-event |
| M-03 | normalizer | Traduzir ics do provedor para o modelo canônico e de volta: mapa de campos, TZID para UTC, DATE versus DATE-TIME | to_canonical(ics_text) -> Event; to_ics(event) -> ics_text | canonical-event |
| M-04 | provider-alpha | Provedor simulado estilo Google: token de estado opaco, tombstone por STATUS CANCELLED, token de paginação distinto, invalidação de token, sem janela temporal | porta Provider, contrato abaixo | normalizer |
| M-05 | provider-beta | Provedor simulado estilo Microsoft Graph: deltaLink e skiptoken, remoção por removed, janela temporal obrigatória, paginação capaz de repetir item | porta Provider, mesmo contrato | normalizer |
| M-06 | reconciler | Matriz 3-vias pura: classifica cada chave em propagação, no-op ou conflito com sua classe | reconcile(a, b, ancestor) -> Decision | canonical-event |
| M-07 | policies | Catálogo POL-1 a POL-4 e a regra R-A1 de campos estruturados | resolve(conflict, policy) -> Resolution ou ESCALATE | canonical-event |
| M-08 | conflict-queue | Conflitos como entidades persistidas, ciclo de vida aberto para resolvido, nada aplicado sem decisão | enqueue(conflict); list(state); resolve(id, choice) | canonical-event, repository |
| M-09 | overlap-detector | Sobreposição temporal por varredura ordenada sobre ocorrências em UTC, com a regra R-A2 de all-day | find_overlaps(occurrences) -> lista de Overlap | canonical-event, recurrence |
| M-10 | sync-engine | Orquestra o ciclo pull, normalizar, reconciliar, planejar, aplicar, persistir; trata full resync, neutralização de eco, limite de páginas e a regra R-A3 | run_cycle(policy, dry_run) -> SyncReport | provider-alpha, provider-beta, reconciler, policies, conflict-queue, repository |
| M-11 | repository | Porta de persistência e implementação SQLite do ancestral, mapa de identidade, tokens e fila, com commit atômico | load_ancestor(key); resolve_identity; load_tokens; commit(...) | nenhuma |
| M-12 | cli | Superfície que a pessoa opera: sync, status, conflicts list, conflicts resolve, overlaps, dry-run | comandos, exit codes, saída tabular em stdout | conflict-queue, overlap-detector, sync-engine |

Detalhamento das linhas acima (o que a tabela resume em prosa mínima):
`M-04` reproduz a semântica REF-5 (`syncToken`, `STATUS:CANCELLED`, `nextPageToken`,
410) e **não** tem janela; `M-05` reproduz REF-6 (`deltaLink`/`$skiptoken`,
`@removed`, `startDateTime`/`endDateTime` obrigatórios) e **pode repetir item já
entregue** (armadilha A-2). `M-07` devolve `Resolution` ou `ESCALATE`. `M-09`
opera em O(n log n). `M-12` expõe `conflicts resolve <id> --take a|b|merge`.

Granularidade (E = I₀/C): cada módulo é implementável numa sessão isolada tendo
em contexto apenas este documento e a interface dos módulos de que depende.
M-06 e M-07 são **puros** — sem I/O, sem banco, sem provedor — e é isso que
permite testar a matriz 3-vias como tabela de entradas/saídas.

---

## Contratos das portas (Design by Contract)

### Porta `Provider` (implementada por M-04 e M-05)

```
pull(state_token | None) -> Delta
    Delta = { items: [RawEvent], tombstones: [ProviderId],
              next_page_token: str|None, next_state_token: str|None,
              invalidated: bool }
    - Exatamente um de next_page_token / next_state_token é não-nulo.
    - state_token é OPACO: proibido parsear, ordenar ou derivar tempo dele.
    - invalidated=True  =>  o chamador DEVE descartar o token e refazer full sync.
    - Remoções vêm em tombstones; ausência de um item NÃO significa remoção.

write(op: Create|Update|Delete) -> Version
    - Devolve a versão/ETag resultante da escrita. O chamador DEVE gravá-la no
      ancestral no mesmo commit (neutralização de eco, A-5).

get(provider_id) -> RawEvent | NOT_FOUND
    - Usado por M-10 para distinguir saída-de-janela de deleção real (R-A3).

observability_window() -> Window | UNBOUNDED
    - Declara se o provedor só observa um intervalo. Governa a aplicação de R-A3.
```

### Porta `Repository` (implementada por M-11)

```
load_ancestor(key: EventKey) -> Ancestor | None
resolve_identity(provider, provider_id) -> EventKey | None
load_tokens() -> {provider: state_token}
commit(writes: [AppliedWrite], ancestors: [Ancestor], tokens: {...},
       conflicts: [Conflict]) -> None
    - Uma única transação. Ou tudo entra, ou nada entra.
```

### Núcleo puro

```
reconcile(a: Event|None, b: Event|None, ancestor: Ancestor|None) -> Decision
    Decision = NoOp | Propagate(direction, event) | Conflict(class, fields)
    - Função pura. Mesma entrada, mesma saída, sempre.

resolve(conflict: Conflict, policy: Policy) -> Resolution | ESCALATE
    - ESCALATE significa: vai para a fila humana; NADA é aplicado.
```

---

## Premissas (AP4 — o que o sistema assume como verdadeiro)

| id | Premissa | Se for falsa… |
|----|----------|---------------|
| PR-1 | O ancestral cabe em SQLite local e o commit de estado é atômico | estado inconsistente após interrupção; ancestral e token divergem |
| PR-2 | Os provedores simulados são fiéis o bastante para que os bugs encontrados sejam os bugs reais | o sistema passa nos testes e falha contra um provedor real |
| PR-3 | `UID` é preservado pelos dois provedores nas escritas | o mapa de identidade quebra e eventos duplicam a cada ciclo |
| PR-4 | Merge por campo é seguro para campos escalares; estruturados escalam (R-A1) | merge produz evento semanticamente inválido |
| PR-5 | Comparar em UTC não perde informação relevante para gravação (o `TZID` original é preservado à parte) | evento gravado no fuso errado após um round-trip |
| PR-6 | A escrita no provedor e o commit local não podem ser atômicos entre si (o provedor é externo) — a janela entre os dois é uma falha possível | escrita aplicada no provedor sem ancestral gravado ⇒ o eco é lido como mudança externa |
| PR-7 | `recurring-ical-events` expande exceções e `EXDATE` corretamente conforme RFC 5545 | sobreposições falsas/ausentes; UC-8 falha silenciosamente |
| PR-8 | Um ciclo cabe em < 5 s com ~1.000 eventos por lado sem paralelismo | VAL-2 falha; exigiria repensar single-threaded |

## Escopo negativo (o que o sistema deliberadamente NÃO faz)

1. Não fala com API real nem faz OAuth2 — a porta `Provider` existe pronta, o adaptador real não é escrito neste ciclo.
2. Não roda como daemon, não faz polling, não recebe webhook, não agenda nada.
3. Não tem Web UI, TUI, servidor HTTP nem notificação — só a CLI.
4. Não implementa iTIP como protocolo: sem convite, RSVP, status de participante, free/busy.
5. **Não reagenda eventos**: sobreposição de agenda é detectada e reportada, nunca resolvida movendo evento.
6. Não mescla campos estruturados (`attendees`, `RRULE`) — escala para conflito (R-A1).
7. Não escreve expansor de recorrência próprio (S6 Tier 1).
8. Não propaga remoção vinda do provedor com janela sem antes verificar existência fora dela (R-A3).

## Decisões tecnológicas com alternativa considerada

| Decisão | Escolhida | Alternativa descartada | Motivo |
|---|---|---|---|
| Payload dos provedores | `.ics` real via `icalendar` | JSON próprio | exercita parsing real; fortalece PR-2, que é a premissa mais fraca do projeto |
| Expansão de recorrência | `recurring-ical-events` | `dateutil.rrule` manual | trata `EXDATE`/`RDATE`/`RECURRENCE-ID` de fábrica — é onde nasce o bug caro |
| Estado | SQLite único do sincronizador; provedores guardam dados fora dele | banco único cobrindo os provedores | manter os provedores externos preserva o problema que o projeto estuda |
| Concorrência | single-threaded | async nos pulls | determinismo; sem rede não há ganho |

---

---

## Como funcionam as lentes

Um processo de crítica arquitetural aplica lentes: cada uma faz uma pergunta central
a cada módulo, e detecta uma classe de falha que as outras não detectam.

**Sete são universais** — rodam sempre e não estão em questão: Premissas, Arquitetura,
Implementabilidade, Rigor científico, Segurança, Desempenho, Conformidade regulatória.
**Não as inclua na resposta.**

**Doze são condicionais**, e são essas que você vai avaliar.

**A ativação é por SINAL DO PROJETO, e só.** Que outra lente pareça cobrir a mesma
classe de falha **não** é motivo para deixar uma de fora: não achar nada já é um
resultado válido, e decidir de antemão que duas lentes se sobrepõem é conclusão, não
premissa. Nunca marque `false` por redundância com outra lente — o motivo tem que ser
um sinal do projeto ("não há dependência externa", "não há superfície de usuário"),
nunca "já coberta pela lente X".


| lente | pergunta central | ativa quando |
|---|---|---|
| Resilience | What happens when an external dependency fails, responds slowly, or returns unexpected data? | The system depends on anything outside its own process that can fail, stall, or return unexpected data — a network service, a database, a queue, a file, a subprocess. Apply the central question wherever such a boundary exists; the list is illustrative, not the requirement. |
| UI/UX | Can the user complete their task without frustration, confusion, or error? | Any surface a PERSON operates — including a CLI or operational tooling, not only graphical end-user interfaces |
| Migration / Coexistence | What breaks during the transition from old to new? Is there a rollback path? | The work must carry an existing, relied-upon state or contract across a change — a populated store, a format other code already reads, a live interface consumers depend on — that has to survive or roll back. Greenfield work, and a store only this version ever reads, do not activate. |
| Sustainability / Proportionality | Is resource consumption proportionate to value delivered? Cost at 10\xD7 scale? | The system decides, allocates, or consumes a resource whose cost grows with use — e.g. (but NOT only) AI/ML, high-volume data processing, elastic infrastructure. Apply the central question, do not just match the examples |
| Ethical / Human Impact | Who is potentially harmed? Are there audit, correction, and transparency mechanisms? | The system makes or automates a consequential decision whose effect falls on people — directly, or through an entity they depend on (a budget cut borne by those it funds, an access denial, a flag acted on). Apply the central question — who can be harmed? — without requiring the decision be nominally "about people". A system that decides nothing consequential about anyone stays out. |
| Process / Workflow | Are processes, state transitions, actor responsibilities, and exception paths complete? | The system has a process with states, handoffs, or exception paths — one actor or many. Apply the central question wherever a flow can be left incomplete; "multi-actor" is one case, not the requirement. |
| Governance / Accountability | Is every action attributable? Does every data entity have a defined owner? | The system records or decides something someone will later need to audit, attribute, or answer for — data with distinct owners, actions that need authorship, or an obligation to account. This is a SYSTEM property: a single-operator project activates it when the system has it (not only multi-team / compliance contexts) |
| Observability / Operability | Can degradation be detected and incidents diagnosed in production without code changes? | The system runs somewhere it can degrade or fail after it ships, and someone would need to tell WHY without changing code. Apply the central question wherever a running system can fail silently; it does not require a formal "production" or "ops" label. |
| Control Engineering | Where does the system generate an error signal and correct it? Risk of oscillation or state drift? | The system regulates state over time rather than only reacting — state synchronization, a runtime setting that changes behavior, a retry/backoff, a self-correcting or feedback-driven loop that can oscillate or drift. Apply the central question wherever such regulation exists; the list is illustrative. |
| Game Theory | Do system actors have aligned incentives? Where does the design assume cooperation and may encounter strategic defection? | The design assumes some actor — a user, a client, an integrator, an operator — behaves as intended, and a self-interested one could deviate to its own benefit. Apply the central question wherever cooperation is assumed rather than enforced; a public API or marketplace is one case, not the requirement. |
| Linguistics / Grammar | Is the interface contract unambiguous? Can two correct implementations of the same contract produce incompatible behaviors? | Any contract two parties must agree on — a function signature, a message format, a protocol, a file schema — where two correct readings could diverge. Apply the central question wherever a contract can be read two ways; it does not require separate teams. |
| Mechanical Engineering | Where are the tolerances? Does the system tolerate variation or only work at exact specification? | The system depends on something that can vary — a dependency version, an environment, an input range, a load — and could fail on small deviations. Apply the central question wherever variation is possible, not only in long-lived or maintenance-heavy systems. |

---

## O que responder

Para **cada uma das 12**: `ativa` (true/false) e `sinal` — uma frase curta dizendo **o
que na arquitetura** aciona, ou não aciona, a lente. Preencha o `sinal` também nas
`false`. E `modulos_estimados`: quantos módulos a arquitetura tem.

As 12 têm que aparecer, com o nome exato da tabela. Só o JSON, sem preâmbulo:

```json
{
  "projeto": "T28-agenda",
  "modulos_estimados": 0,
  "lentes": [{"lente": "Resilience", "ativa": true, "sinal": "..."}]
}
```
