# Arquitetura — T28-agenda

Sincronizador bidirecional entre dois calendários externos, com detecção e
resolução de conflito de **sincronização** (acepção A) e de **agenda** (acepção B).

Padrão: **Hexagonal (Ports & Adapters)** · Princípios: **KISS + YAGNI** ·
Concorrência: **single-threaded** · GoF: **nenhum nomeado** ·
Domínio: **Domain Model enxuto** (value objects imutáveis + funções puras) ·
Dados: **Repository como porta**.

Stack verificada empiricamente (`specs/technical/feasibility.md`): Python 3.12.1,
`icalendar` 7.2.2, `recurring-ical-events`, `python-dateutil` 2.9.0.post0,
`zoneinfo`, `sqlite3` 3.41.2, `pytest` 9.0.2.

---

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

## V(2) — resposta unificada à crítica da iteração 1

V(1) permanece acima, intacto. Esta é a versão corrente.

**Princípio da resposta (assimetria da Fase 3):** a iteração 1 atacou com 16
lentes e produziu 64 achados. A resposta é UNIFICADA — cinco mecanismos que
atravessam vários achados de lentes diferentes — e **nenhum módulo novo foi
criado**. Onde a crítica revelou fragilidade, a correção redistribuiu
responsabilidade para módulos que já existiam, em vez de acrescentar peças
(AP2).

### Os cinco mecanismos

**MEC-A — Fingerprint canônico de conteúdo (vive em `normalizer`).**
`fingerprint(event) -> str`: hash estável do conteúdo canônico — campos escalares
e estruturados normalizados, **excluindo** `SEQUENCE`, `DTSTAMP`, ids do provedor
e ordenação de coleções. O ancestral passa a guardar o fingerprint além das
versões de cada lado. O eco deixa de ser detectado por ETag (que o provedor pode
mudar ao normalizar o recurso na gravação) e passa a ser detectado por
**identidade de conteúdo**: fingerprint igual ao do ancestral ⇒ no-op, não
importa o que o provedor fez com os metadados. Fecha a realimentação que gerava
ping-pong permanente.
Invariante testável decorrente: `fingerprint(to_canonical(to_ics(e))) == fingerprint(e)`.

**MEC-B — Journal de ciclo (vive em `repository`, uma tabela e dois métodos).**
Antes de qualquer escrita, o plano é persistido como intenção; cada ação é
marcada como aplicada junto da versão e do fingerprint resultantes; o ciclo é
fechado no mesmo commit dos tokens. Ao iniciar um ciclo, um journal aberto é
reconciliado contra o provedor antes de planejar. O mesmo registro guarda o valor
descartado por política e serve de histórico inspecionável. Um mecanismo, cinco
achados de quatro lentes distintas.

**MEC-C — Presença observável no contrato (`canonical-event`, `reconciler`, porta `Provider`).**
O reconciliador deixa de receber `Event | None` e passa a receber
`Side = Present(event) | Absent | Unobservable`. `Absent` significa
comprovadamente inexistente; `Unobservable` significa fora da janela ou
indeterminado — e **nunca** produz deleção. `pull(None)` é definido no contrato
como full sync **do escopo declarado por `observability_window()`**, eliminando a
ambiguidade entre as duas implementações da porta. `suspended` ganha transição de
retorno: evento que reentra na janela reativa o mapeamento preservando o ancestral.

**MEC-D — Cenário declarativo dos simuladores (`provider-alpha`, `provider-beta`).**
Os comportamentos adversos deixam de ser arbitrários: um arquivo de cenário
declara quando o token é invalidado, em que página um item é repetido e o tamanho
de página. O simulador vira determinístico e o teste, reproduzível.
Parâmetros com valor declarado: **página = 100 itens**, **teto de 50 páginas por
round** (5× o normal de 10 páginas para 1.000 eventos), **teto de 10.000
instâncias por expansão de série**.

**MEC-E — Janela temporal explícita (`recurrence`, `overlap-detector`, `cli`).**
Toda expansão ocorre numa janela declarada — padrão `[hoje-30d, hoje+365d]`,
sobreponível na CLI. `expand()` recebe um VCALENDAR com mestre e exceções
agrupados por UID (unidade de entrada definida). Séries sem `UNTIL` deixam de ser
um custo indefinido.

### Tabela de módulos V(2)

| id | module | responsibility | interface | depends-on |
|------|--------|----------------|-----------|------------|
| M-01 | canonical-event | Modelo canônico imutável, chave UID + RECURRENCE-ID, campo LAST-MODIFIED, e o tipo Side com Present, Absent e Unobservable | Event, Occurrence, EventKey, Side; key(event) -> EventKey; scalar_fields(event) -> dict | nenhuma |
| M-02 | recurrence | Expandir VCALENDAR agrupado por UID em ocorrências dentro da janela declarada, com teto de instâncias por série | expand(vcalendar, window) -> lista de Occurrence | canonical-event |
| M-03 | normalizer | Traduzir ics para canônico e de volta por dialeto declarado, emitir VTIMEZONE, validar conformidade, e produzir o fingerprint canônico de conteúdo | to_canonical(ics_text, dialect) -> Event; to_ics(event) -> ics_text; fingerprint(event) -> str | canonical-event |
| M-04 | provider-alpha | Provedor simulado estilo Google dirigido por cenário declarativo, com id sanitizado antes de virar caminho de arquivo | porta Provider incluindo observability_window e get | normalizer |
| M-05 | provider-beta | Provedor simulado estilo Microsoft Graph dirigido por cenário declarativo, com janela obrigatória e id sanitizado | porta Provider, mesmo contrato | normalizer |
| M-06 | reconciler | Matriz 3-vias pura sobre Side, e o planejamento puro do ciclo inteiro a partir dos deltas e dos ancestrais | reconcile(a, b, ancestor) -> Decision; plan(deltas, ancestors) -> Plan | canonical-event |
| M-07 | policies | Catálogo POL-1 a POL-4 com desempate determinístico em cascata e a regra R-A1 de campos estruturados | resolve(conflict, policy) -> Resolution ou ESCALATE | canonical-event |
| M-08 | conflict-queue | Transições puras do conflito entre OPEN, RESOLVED, APPLIED e STALE, sem tocar em I/O | transition(conflict, event) -> Conflict; is_blocking(conflict) -> bool | canonical-event |
| M-09 | overlap-detector | Sobreposição temporal por varredura ordenada sobre ocorrências em UTC, com a regra R-A2 de all-day | find_overlaps(occurrences) -> lista de Overlap | canonical-event, recurrence |
| M-10 | sync-engine | Executa o plano produzido pelo reconciliador: resolve Unobservable consultando o provedor, aplica pelo journal, trata full resync e o teto de páginas | run_cycle(policy, window, dry_run) -> SyncReport | provider-alpha, provider-beta, reconciler, policies, conflict-queue, repository |
| M-11 | repository | Persistência SQLite com esquema versionado: ancestral com fingerprint, mapa de identidade, tokens, fila e journal de ciclo, com commit atômico, retenção e lock de execução | load_ancestor(key); open_cycle(plan); mark_applied(action); commit(...) | nenhuma |
| M-12 | cli | Superfície humana: sync, status, conflicts list, conflicts show, conflicts resolve, overlaps, journal, com exit codes definidos | comandos, exit codes, saída tabular em stdout | conflict-queue, overlap-detector, sync-engine, repository |

### O que mudou de V(1) para V(2)

| module | mudança | natureza |
|---|---|---|
| sync-engine | **perdeu** o planejamento (foi para reconciler), a atomicidade e o histórico (foram para repository) e a detecção de eco (foi para normalizer); ficou com execução do plano e resolução de presença | reestruturação — desconcentração |
| reconciler | **ganhou** `plan()` e passou a operar sobre `Side` em vez de `Event\|None` | reestruturação |
| repository | **ganhou** journal, esquema versionado, retenção e lock | reestruturação |
| conflict-queue | passou a ser **puro**: transições sem I/O, persistência delegada ao repository | reestruturação |
| normalizer | ganhou fingerprint, dialeto, VTIMEZONE e validação | extensão de responsabilidade |
| canonical-event | ganhou `LAST-MODIFIED` e o tipo `Side` | extensão |
| policies | ganhou cascata de desempate determinística | extensão |
| recurrence | ganhou janela obrigatória, unidade VCALENDAR e teto | extensão |
| provider-alpha, provider-beta | ganharam cenário declarativo e sanitização de id | extensão |
| overlap-detector, cli | inalterados na estrutura; cli ganhou comandos `show` e `journal` | extensão |

Módulos adicionados: **0**. Removidos: **0**. Reestruturados: **4**.

### Premissas revisadas

PR-6 deixa de ser risco aceito e passa a ser **tratada** por MEC-B: a
impossibilidade de atomicidade entre provedor externo e banco local continua
verdadeira, mas o journal torna a janela recuperável em vez de silenciosa.
PR-7 (confiança na lib de expansão) ganha pin de versão e teste de contrato.
Nova premissa **PR-9**: o fingerprint é estável entre round-trips — se falhar, o
sistema oscila; por isso vira invariante testada, não premissa tácita.

---

## V(3) — resposta unificada à crítica da iteração 2

V(1) e V(2) permanecem acima, intactos. Esta é a versão corrente.

A iteração 2 produziu 27 achados e **os 3 críticos eram todos efeitos colaterais
dos mecanismos de V(2)** — nenhum era resíduo de V(1). A resposta de V(3) é
deliberadamente do tipo oposto à de V(2): **nenhum mecanismo novo**. Três regras
que *simplificam* mecanismos existentes, e o resto é especificação do que já
existia mas estava vago.

### Regra 1 — O ancestral guarda o que o provedor DEVOLVEU, por lado

`AncestorSide = { fingerprint, provider_version, sequence, dtstamp }`, gravado a
partir do estado **observado após a escrita**, não do estado enviado.

- **CTL-04 morre:** qualquer normalização do provedor (inclusive semanticamente
  visível, como truncar `DESCRIPTION`) é absorvida no ancestral no momento da
  escrita. O pull seguinte encontra fingerprint igual → no-op. A oscilação não
  tem de onde nascer.
- **ASS-07 morre por declaração, não por maquinaria:** `SEQUENCE`/`DTSTAMP` são
  **metadados locais de cada provedor e não são sincronizados** — é um não-objetivo
  declarado, porque uma revisão que não muda nada observável não é uma mudança.
  E POL-1 deixa de comparar `SEQUENCE` absoluto entre provedores (que diverge por
  construção): compara **Δ relativo ao ancestral do próprio lado**
  (`seq_lado − seq_ancestral_do_lado`), dado que já está armazenado.
- **MEC-04 tratado:** o ancestral guarda a versão do algoritmo de fingerprint;
  mudança de regra dispara recálculo, não invalidação em massa.

### Regra 2 — Presença é decidida pela janela, não por consulta

Inverte a resolução de `Unobservable`: uma chave cujo ancestral está **fora da
janela declarada** por `observability_window()` é `Unobservable` **por
construção, sem nenhuma chamada de rede**. Só chaves *dentro* da janela e ausentes
do delta são `Absent`. O `get()` fica reservado à fronteira — chave dentro da
janela que sumiu, que pode ter sido movida para fora — e essas são poucas.

- **RES-05 morre:** o full resync deixa de custar ~1.000 `get()`; o caso normal
  custa zero.
- A garantia de R-A3 (saída-de-janela nunca vira deleção) fica **mais forte**,
  porque passa a depender de dado local em vez de disponibilidade do provedor.

### Regra 3 — `repository` é armazenamento burro; decisão é de quem orquestra

`repository` guarda cinco coleções com commit atômico, retenção declarada e
versão de esquema — e **não decide nada**. A reconciliação de journal aberto (o
que fazer com um ciclo interrompido) volta para `sync-engine`, que já é o dono da
orquestração. `conflict-queue` produz o valor do conflito; `repository` grava o
que recebe, verbatim, sem nunca mutar estado de conflito.

- **ARC-07 tratado:** o que tinha migrado para `repository` era *lógica de
  decisão*; ela sai, e o que fica é dado.
- **ARC-08 tratado:** a entidade deixa de estar partida em duas metades com
  autoridade dividida — a autoridade é de `conflict-queue`, a gravação é do
  `repository`.

### Especificações que faltavam (o resto dos achados)

| tema | o que passa a estar declarado |
|---|---|
| Contrato do `repository` (LIN-05, IMP-07) | Ordem obrigatória `open_cycle(plan) → mark_applied(action)* → close_cycle(tokens)`; `mark_applied` **idempotente** (retomada pode remarcar); chamada fora de ordem é erro explícito, não comportamento indefinido |
| Contrato do `reconciler` (ARC-06, ASS-09) | `plan(deltas, ancestors, blocked_keys, policy) -> Plan` — argumentos explícitos, pureza preservada, fronteira com `conflict-queue` declarada; limite de memória declarado em ~5.000 eventos por lado |
| Regras do fingerprint (IMP-06) | Coleções ordenadas por chave natural; `CRLF`→`LF`; trim de bordas; caixa preservada; excluídos `SEQUENCE`, `DTSTAMP`, `PRODID`, ids de provedor e ordem de propriedades |
| Origem do fingerprint (SCI-05) | Declarado como **convenção do projeto**, análoga à semântica de ETag (REF-4), não como regra derivada de norma |
| `VTIMEZONE` (REG-04) | `icalendar.Timezone.from_tzinfo(ZoneInfo(tzid), first_date, last_date)` — **verificado por execução** na 7.2.2. Tier 1, não Tier 3 |
| Oscilação (OBS-04, CTL-05) | Critério com valor: chave que alterna de direção em **3 ciclos consecutivos** é marcada oscilante; ação (histerese): propagação suspensa e conflito aberto na fila para decisão humana — usa maquinaria que já existe |
| Retenção e auditoria (SEC-06, SUS-04, GOV-04) | Journal retido por **20 ciclos ou 30 dias, o que for maior**; cada entrada registra versão de esquema, política vigente e versão do algoritmo de fingerprint |
| Estados do conflito (PRO-05) | `RESOLVED → STALE` definido: decisão gravada cuja chave desapareceu dos dois lados antes da aplicação vira `STALE` com o motivo registrado |
| Ciclo aberto (PRO-06, ASS-08) | `sync` detecta e recupera automaticamente, sem passo manual; provedor indisponível na retomada **falha com mensagem e exit code próprios**, nunca trava em silêncio |
| CLI (UX-06, UX-07) | `journal` mostra os últimos N ciclos com filtro por chave; a saída de `conflicts` explica os quatro estados em uma linha cada |
| `Side.Present` parcial (LIN-06) | Item resumido vindo de paginação é `Present(partial=True)` e **nunca** participa de reconciliação: obriga leitura completa antes de decidir |
| Custo do fingerprint (PER-05) | Calculado **uma vez, durante a normalização do pull** (o parse já está acontecendo) — não é passe adicional |

### Tabela de módulos V(3)

| id | module | responsibility | interface | depends-on |
|------|--------|----------------|-----------|------------|
| M-01 | canonical-event | Modelo canônico imutável, chave UID + RECURRENCE-ID, LAST-MODIFIED, e Side com Present incluindo marca de parcial, Absent e Unobservable | Event, Occurrence, EventKey, Side; key(event) -> EventKey | nenhuma |
| M-02 | recurrence | Expandir VCALENDAR agrupado por UID em ocorrências dentro da janela declarada, com teto de instâncias por série | expand(vcalendar, window) -> lista de Occurrence | canonical-event |
| M-03 | normalizer | Traduzir ics por dialeto, emitir VTIMEZONE via icalendar, validar conformidade e produzir o fingerprint canônico versionado | to_canonical(ics_text, dialect) -> Event; to_ics(event) -> ics_text; fingerprint(event) -> str | canonical-event |
| M-04 | provider-alpha | Provedor simulado estilo Google dirigido por cenário declarativo, id sanitizado, devolve o recurso gravado | porta Provider incluindo observability_window e get | normalizer |
| M-05 | provider-beta | Provedor simulado estilo Microsoft Graph dirigido por cenário, janela obrigatória, id sanitizado, devolve o recurso gravado | porta Provider, mesmo contrato | normalizer |
| M-06 | reconciler | Matriz 3-vias pura sobre Side e planejamento puro do ciclo com argumentos explícitos de bloqueio e política | reconcile(a, b, ancestor) -> Decision; plan(deltas, ancestors, blocked_keys, policy) -> Plan | canonical-event |
| M-07 | policies | Catálogo POL-1 a POL-4 com precedência por delta relativo ao ancestral de cada lado e cascata determinística | resolve(conflict, policy) -> Resolution ou ESCALATE | canonical-event |
| M-08 | conflict-queue | Autoridade sobre o conflito: transições puras entre OPEN, RESOLVED, APPLIED e STALE, incluindo oscilação | transition(conflict, event) -> Conflict; is_blocking(conflict) -> bool | canonical-event |
| M-09 | overlap-detector | Sobreposição temporal por varredura ordenada sobre ocorrências em UTC, com a regra R-A2 de all-day | find_overlaps(occurrences) -> lista de Overlap | canonical-event, recurrence |
| M-10 | sync-engine | Orquestra o ciclo, decide presença pela janela sem consultar o provedor, reconcilia journal aberto, detecta oscilação e aplica histerese | run_cycle(policy, window, dry_run) -> SyncReport | provider-alpha, provider-beta, reconciler, policies, conflict-queue, repository |
| M-11 | repository | Armazenamento burro de cinco coleções com commit atômico, ordem de chamada obrigatória, retenção declarada e esquema versionado; não decide nada | open_cycle(plan); mark_applied(action); close_cycle(tokens); load_ancestor(key) | nenhuma |
| M-12 | cli | Superfície humana com estados explicados e exit codes definidos: sync, status, conflicts, overlaps, journal | comandos, exit codes, saída tabular em stdout | conflict-queue, overlap-detector, sync-engine, repository |

### O que mudou de V(2) para V(3)

| module | mudança | natureza |
|---|---|---|
| repository | **perdeu** toda lógica de decisão (reconciliação de journal foi para sync-engine); ganhou ordem de chamada obrigatória e retenção declarada | reestruturação |
| sync-engine | **ganhou** a reconciliação de journal e a decisão de presença por janela; **perdeu** a consulta em massa ao provedor | reestruturação |
| normalizer | fingerprint versionado, regras de normalização declaradas, VTIMEZONE via lib verificada | extensão |
| policies | precedência por delta relativo em vez de SEQUENCE absoluto | extensão |
| conflict-queue, canonical-event, reconciler, cli | contratos e estados especificados; nenhuma mudança de forma | especificação |
| recurrence, overlap-detector, provider-alpha, provider-beta | inalterados | — |

Módulos adicionados: **0**. Removidos: **0**. Reestruturados: **2**.
Mecanismos novos: **0** — três regras que simplificam mecanismos de V(2).

---

## V(4) — resposta à iteração 3 (costura)

V(1), V(2) e V(3) permanecem acima. Esta é a versão corrente e a que a Fase 5
implementa.

A iteração 3 não encontrou falha interna em nenhuma regra de V(3): os três
críticos são **defeitos de costura** entre as regras novas e decisões tomadas em
P0/P1. A resposta é proporcional — nenhum mecanismo novo, nenhuma
responsabilidade movida de módulo. São correções de contrato, de esquema e de
nome.

### As três correções de costura

**C-1 — O ancestral volta a guardar conteúdo, agora por lado (ASS-10).**
```
Ancestor = { key, side_a: AncestorSide, side_b: AncestorSide, suspended, synced_at }
AncestorSide = { snapshot: Event, fingerprint, provider_version, sequence, dtstamp }
```
A Regra 1 de V(3) removeu o conteúdo sem ver que POL-4 (merge 3-vias por campo,
decisão de P0) depende dele. Guardar o snapshot **por lado** não é regressão a
V(2): é mais correto, porque "o que mudou em A" passa a ser
`A_atual vs snapshot_a` — o diff de cada lado contra o que aquele lado mostrou
por último, que é exatamente o que a Regra 1 estabeleceu.
Custo declarado: dois snapshots por evento em vez de um. É armazenamento local,
proporcional ao valor (o merge por campo é requisito de P0).

**C-2 — O contrato devolve o recurso, não só a versão (LIN-07).**
```
write(op: Create|Update|Delete) -> WriteResult { stored: RawEvent, version: str }
```
A Regra 1 exige gravar no ancestral o que o provedor devolveu; o contrato de V(1)
prometia só a versão. Uma implementação fiel ao contrato tornava a regra
inaplicável sem violar nada. Corrigido na porta, herdado pelas duas
implementações.

**C-3 — Duas janelas, dois nomes (ASS-11).**
| nome | quem declara | para que serve | pode ser usada para |
|---|---|---|---|
| `observability_window` | o provedor, via porta | o que aquele provedor consegue ver | **decisão de presença** (Regra 2) |
| `expansion_window` | o operador, via CLI, padrão hoje-30d a hoje+365d | até onde expandir séries | **detecção de sobreposição** (MEC-E) |

Usar uma pela outra é o caminho para propagar deleção de evento que só está fora
do alcance do provedor. Os dois nomes são distintos no código, no glossário e nos
testes; nenhuma função recebe "window" sem qualificador.

### As demais correções

| id | correção |
|---|---|
| RES-07 | `write()` de evento fora da `observability_window` do provider-beta: **aceita, devolve o recurso gravado, e o evento não aparece nos deltas seguintes** — ou seja, vira `Unobservable` por construção. Determinístico e declarado no cenário |
| ARC-09 | A reconciliação de journal aberto usa **apenas dados locais** para ações já marcadas (têm fingerprint gravado); só a ação aberta exige verificação — e como o ciclo é single-threaded, há no máximo **uma**. A leitura contra o provedor cai de "um passe" para "≤1 chave" |
| ASS-12 | Sem ancestral não há delta: criação concorrente com mesmo UID (`IDENTITY_COLLISION`) **escala direto para a fila**, sem tentar precedência. Declarado como regra, não como caso omisso |
| PER-07 | Os dois provedores simulados **nunca** devolvem item parcial (declarado no cenário); `Present(partial=True)` existe para o adaptador real futuro, e quando ocorrer a leitura completa se limita às chaves parciais da página |
| IMP-08 | Dependência entre parâmetros declarada e **verificada em tempo de execução**: retenção do journal ≥ 3 × o critério de oscilação. Mudar um sem o outro falha ruidosamente em vez de quebrar o detector em silêncio |
| GOV-05 | A poda **nunca** remove entrada de ciclo referenciada por conflito ainda aberto ou por chave suspensa por oscilação |
| MEC-05 | Caminho de execução existe: `maintenance recompute-fingerprints` recalcula a partir dos snapshots por lado (viável porque C-1 os trouxe de volta) |
| UX-08, OBS-05 | `SyncReport` ganha `suspended_oscillating`; `status` e `sync` distinguem BLOQUEADA-POR-CONFLITO de SUSPENSA-POR-OSCILAÇÃO na saída |
| LIN-08 | `close_cycle` **recusa** fechar com ação planejada não marcada; cancelar é explícito (`cancel_action`). O estado nunca fica ambíguo |
| SEC-07 | `journal` omite valores por padrão; exibi-los exige `--show-values` |

### Tabela de módulos V(4)

Idêntica à de V(3) em nomes, responsabilidades e dependências — **nenhum módulo
foi adicionado, removido ou reestruturado**. Mudam apenas o esquema de
`repository` (snapshot por lado) e a assinatura de `write` na porta `Provider`.

| id | module | responsibility | interface | depends-on |
|------|--------|----------------|-----------|------------|
| M-01 | canonical-event | Modelo canônico imutável, chave UID + RECURRENCE-ID, LAST-MODIFIED, e Side com Present, marca de parcial, Absent e Unobservable | Event, Occurrence, EventKey, Side | nenhuma |
| M-02 | recurrence | Expandir VCALENDAR agrupado por UID em ocorrências dentro da expansion_window, com teto de instâncias por série | expand(vcalendar, expansion_window) -> lista de Occurrence | canonical-event |
| M-03 | normalizer | Traduzir ics por dialeto, emitir VTIMEZONE via icalendar, validar conformidade, produzir fingerprint versionado e recalcular fingerprints sob demanda | to_canonical(ics_text, dialect) -> Event; to_ics(event) -> ics_text; fingerprint(event) -> str | canonical-event |
| M-04 | provider-alpha | Provedor simulado estilo Google dirigido por cenário, id sanitizado, write devolve o recurso gravado, observability_window ilimitada | pull(state_token) -> Delta; write(op) -> WriteResult; get(id); observability_window() | normalizer |
| M-05 | provider-beta | Provedor simulado estilo Graph dirigido por cenário, id sanitizado, write devolve o recurso gravado, observability_window limitada com semântica declarada de escrita fora da janela | mesma porta Provider | normalizer |
| M-06 | reconciler | Matriz 3-vias pura sobre Side e planejamento puro com argumentos explícitos de bloqueio e política | reconcile(a, b, ancestor_side) -> Decision; plan(deltas, ancestors, blocked_keys, policy) -> Plan | canonical-event |
| M-07 | policies | POL-1 a POL-4 com precedência por delta relativo ao ancestral do lado, cascata determinística, e escalonamento direto quando não há ancestral | resolve(conflict, policy) -> Resolution ou ESCALATE | canonical-event |
| M-08 | conflict-queue | Autoridade sobre o conflito: transições puras entre OPEN, RESOLVED, APPLIED e STALE, incluindo suspensão por oscilação | transition(conflict, event) -> Conflict; is_blocking(conflict) -> bool | canonical-event |
| M-09 | overlap-detector | Sobreposição por varredura ordenada sobre ocorrências em UTC, com a regra R-A2 de all-day | find_overlaps(occurrences) -> lista de Overlap | canonical-event, recurrence |
| M-10 | sync-engine | Orquestra o ciclo, decide presença pela observability_window sem consultar o provedor, reconcilia journal aberto por dados locais, detecta oscilação e aplica histerese | run_cycle(policy, expansion_window, dry_run) -> SyncReport | provider-alpha, provider-beta, reconciler, policies, conflict-queue, repository |
| M-11 | repository | Armazenamento de cinco coleções com snapshot por lado, commit atômico, ordem de chamada obrigatória, retenção com exceções declaradas e esquema versionado | open_cycle(plan); mark_applied(action); cancel_action(action); close_cycle(tokens); load_ancestor(key) | nenhuma |
| M-12 | cli | Superfície humana com estados explicados e exit codes definidos: sync, status, conflicts, overlaps, journal, maintenance | comandos, exit codes, saída tabular em stdout | conflict-queue, overlap-detector, sync-engine, repository |

### Premissas finais (as que a Fase 5 herda)

| id | premissa | estado |
|----|----------|--------|
| PR-1 | Ancestral em SQLite com commit atômico | tratada por MEC-B |
| PR-2 | Simuladores fiéis o bastante | **premissa viva** — o cenário declarativo (MEC-D) a reduz, não a elimina |
| PR-3 | UID preservado pelos provedores nas escritas | tratada por C-2: o recurso devolvido revela se não foi |
| PR-4 | Merge por campo seguro em escalares; estruturados escalam | R-A1, e C-1 devolveu o dado que ele exige |
| PR-5 | Comparar em UTC não perde informação de gravação | TZID preservado à parte; VTIMEZONE emitido |
| PR-6 | Atomicidade impossível entre provedor e banco local | tratada por MEC-B (recuperável, não silenciosa) |
| PR-7 | recurring-ical-events expande corretamente | versão fixada + teste de contrato |
| PR-8 | Ciclo < 5 s com 1.000 eventos/lado sem paralelismo | **premissa viva** — medida por VAL-2 na Fase 6 |
| PR-9 | Fingerprint estável entre round-trips | invariante testada, não premissa |
