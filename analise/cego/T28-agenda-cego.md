# Reagrupamento cego de achados — T28-agenda

Você recebe 105 achados de uma crítica arquitetural. Cada um tem um id anônimo, o
módulo onde ocorre, a severidade e uma descrição de uma linha.

**Sua tarefa:** agrupar os achados que apontam o MESMO DEFEITO.

Atenção a defeitos **replicados**: quando dois módulos são implementações irmãs do
mesmo contrato, o mesmo defeito pode aparecer em ambos. Se uma única correção na
abstração compartilhada resolveria os dois, é o mesmo defeito.

**Critério, e é o único que vale:**

> Dois achados são o mesmo defeito quando apontam o mesmo problema no mesmo local,
> com a mesma causa raiz. Regra operacional: **se corrigir um resolveria
> automaticamente o outro, é o mesmo defeito.** Se cada um exige uma correção
> própria, são defeitos distintos — mesmo que estejam no mesmo módulo e sejam
> parecidos.

**Viés conservador, obrigatório:** na dúvida, **NÃO** agrupe. Agrupar a mais é o erro
mais caro aqui.

Não explique, não comente, não reordene. Responda **só** com este JSON:

```json
{"grupos": [["F-03", "F-07"], ["F-11", "F-02", "F-19"]]}
```

Cada lista interna é um grupo de achados que são o mesmo defeito. Achados que não
são duplicata de nenhum outro **não aparecem** — grupos de um só elemento são
implícitos. Se nenhum achado for duplicata de outro, responda `{"grupos": []}`.

## A arquitetura

Os módulos do sistema, para você saber o que cada nome significa e quais são irmãos
entre si:

| id | módulo | responsabilidade | interface | depende-de |
|---|---|---|---|---|
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

## Achados

| id | módulo | severidade | descrição |
|---|---|---|---|
| F-01 | sync-engine | 🟡 | VAL-2 (<5 s) mede o ciclo incremental; o pior caso real é o full resync após invalidação de token, que reconstrói mapa de identidade e ancestral de 1.000 eventos por lado — sem limiar definido |
| F-02 | policies | 🟡 | POL-4 precisa de comparação campo a campo, mas `TimeSpec` não tem regra: mudar `tzid` preservando `instant_utc` conta como mudança de campo ou não? |
| F-03 | cli | 🟢 | Com `STALE` e `APPLIED`, o operador passa a ter quatro estados de conflito para entender; sem explicação na saída, viram jargão interno vazando para a superfície |
| F-04 | canonical-event | 🟢 | `Side` tem três variantes, mas nada define `Present` com conteúdo PARCIAL — o caso do provedor que devolve item resumido durante a paginação |
| F-05 | sync-engine | 🟡 | Sem histerese: uma chave detectada em oscilação é reportada mas continua sendo reescrita a cada ciclo — o sistema observa o erro e não age sobre ele |
| F-06 | repository | 🟡 | Não há trilha de auditoria: o ancestral guarda só o estado corrente, então quando uma política descarta o valor de um lado não fica registro de qual valor foi descartado. "Por que meu evento mudou?" é irrespondível |
| F-07 | recurrence | 🟡 | PR-7 assume que `recurring-ical-events` expande exceções corretamente, sem versão fixada e sem teste de contrato — uma mudança de comportamento entre versões da lib altera silenciosamente a detecção de sobreposição |
| F-08 | normalizer | 🟡 | O recálculo de fingerprint por mudança de versão do algoritmo depende do snapshot ancestral (portanto de ASS-10) e nenhum comando o expõe: a migração existe no papel e não tem caminho de execução |
| F-09 | repository | 🟡 | Assume relógios comparáveis: `DTSTAMP` vindo de dois provedores distintos é comparado sem tratar skew, e `synced_at` supõe relógio local monotônico |
| F-10 | policies | 🟢 | RFC 5546 §2.1.5 normatiza precedência no contexto de mensagens iTIP; usá-la como regra geral de sync é extensão razoável, mas rotulá-la "normativa" aqui é forte demais para a traçabilidade |
| F-11 | repository | 🟡 | O journal registra o que foi aplicado, mas não sob qual versão de código/esquema/política — auditar um ciclo antigo não revela qual regra de merge vigia na hora |
| F-12 | provider-beta | 🟡 | paginação que repete item já entregue (A-2) sem limite de páginas nem detecção de ciclo faz o pull girar indefinidamente |
| F-13 | sync-engine | 🟡 | R-A3 exige `get(provider_id)` para distinguir saída-de-janela de deleção; o design não diz o que fazer se esse `get()` falhar. O fallback silencioso "tratar como deleção" é destrutivo |
| F-14 | sync-engine | 🟡 | Depende de 7 módulos e concentra orquestração, full-resync, neutralização de eco, R-A3, paginação e circuit breaker. Tende a god module; a granularidade E=I₀/C fica no limite de uma sessão |
| F-15 | normalizer | 🟢 | Parse e serialização de texto `.ics` por evento a cada ciclo (2.000 parses) tende a dominar o tempo; o ETag existe justamente para pular o inalterado, mas o design não o usa para evitar parse |
| F-16 | repository | 🟡 | O contrato mais crítico do sistema é o menos especificado: `open_cycle(plan)`, `mark_applied(action)` e `commit(...)` aparecem sem tipos, sem ordem de chamada obrigatória e sem o que acontece se forem chamados fora de ordem |
| F-17 | sync-engine | 🟡 | `SyncReport` é efêmero — devolvido ao CLI e perdido. Não existe histórico de ciclos, então nenhuma ação é atribuível depois do fato |
| F-18 | provider-beta | 🔴 | O contrato pede janela obrigatória + paginação que repete item já entregue + invalidação de token + tombstones, sem nenhuma especificação determinística de QUANDO cada comportamento ocorre. Sem isso o simulador é arbitrário e os testes não reproduzem |
| F-19 | sync-engine | 🔴 | MEC-C manda resolver `Unobservable` consultando `get()`. Num full resync do provider-beta, TODA chave do ancestral fora da janela vira `Unobservable` — 1.000 chamadas `get()` extras num único ciclo, e a falha de qualquer uma trava o ciclo. O mecanismo que protege contra deleção indevida vira um problema de escala e de disponibilidade |
| F-20 | sync-engine | 🔴 | V(3) usa "janela declarada" para duas coisas diferentes: a janela de EXPANSÃO de recorrência (MEC-E, hoje-30d a hoje+365d) e a janela de OBSERVABILIDADE do provedor (`observability_window()`). A decisão de presença da Regra 2 depende da segunda; se o código usar a primeira, um evento que o provedor não observa mas que cai na janela de expansão vira `Absent` e a deleção é propagada — perda de dados por conflação de nomes |
| F-21 | sync-engine | 🔴 | Contradição entre contrato e regra: a porta `Provider` declara `write(op) -> Version`, mas a Regra 1 exige gravar no ancestral o RECURSO devolvido pelo provedor. Uma implementação que honra o contrato literalmente devolve só a versão, e a Regra 1 fica inaplicável sem ninguém violar contrato nenhum |
| F-22 | reconciler | 🟡 | `plan()` precisa saber quais chaves estão bloqueadas por conflito aberto e qual política vige. Se receber isso por argumento continua puro, mas a fronteira reconciler ↔ conflict-queue passou a existir e não está declarada |
| F-23 | cli | 🟢 | Não há porta de apresentação: a formatação tabular fica dentro do CLI, acoplada à forma do `SyncReport` |
| F-24 | cli | 🟡 | `journal` entrou como comando sem definir o que exibe nem como se navega um histórico que cresce a cada ciclo |
| F-25 | sync-engine | 🟡 | A detecção de oscilação prometida ao journal não tem critério: quantos ciclos alternando caracterizam oscilação? Parâmetro sem valor — a mesma classe de defeito que IMP-04 e que V(2) corrigiu em outro lugar |
| F-26 | conflict-queue | 🟡 | Com quatro estados, a transição RESOLVED → STALE não está definida: o operador resolve, o evento some dos dois lados antes do próximo `sync`, e a decisão gravada não tem onde aterrissar |
| F-27 | sync-engine | 🟡 | `Present(partial=True)` obriga leitura completa antes de reconciliar; um provedor que pagina com itens resumidos reintroduz N chamadas extras — a mitigação de RES-05 não cobre este caminho |
| F-28 | conflict-queue | 🟢 | `resolution` grava a escolha, mas não sob qual política ativa nem em que momento do histórico — e a política é global e pode mudar entre ciclos |
| F-29 | provider-beta | 🟢 | mesmo defeito de path traversal na resolução de `provider_id` para caminho de arquivo |
| F-30 | sync-engine | 🟡 | A reconciliação de journal aberto exige um passe de leitura contra o provedor no início do ciclo — a dependência de disponibilidade que a Regra 2 tirou da porta da frente volta pela dos fundos, em caminho distinto de RES-05 |
| F-31 | recurrence | 🟡 | VAL-1 conta eventos, não ocorrências: 1.000 eventos com séries diárias expandidas numa janela ampla produzem dezenas de milhares de ocorrências. A janela de expansão não está definida em lugar nenhum |
| F-32 | cli | 🟢 | `status` não tem conteúdo definido (tokens? contagem de ancestral? conflitos abertos? último ciclo?) — comando sem contrato |
| F-33 | canonical-event | 🟡 | RFC 5545 exige `UID` e `DTSTAMP` em todo VEVENT; nenhuma validação de conformidade está prevista na saída `to_ics`, então o sistema pode emitir `.ics` inválido |
| F-34 | sync-engine | 🟡 | Nenhum log estruturado previsto: descobrir por que um evento específico não propagou exige depurador, não inspeção |
| F-35 | conflict-queue | 🟡 | É o único módulo de domínio que depende de I/O (M-11) — não testável isoladamente sem banco, quebrando a simetria de núcleo puro que M-06/M-07 estabelecem |
| F-36 | reconciler | 🔴 | `reconcile(a, b, ancestor)` assume que `a=None` significa "não existe". Em provider-beta, `None` também significa "fora da janela observável" — informação que a assinatura pura não carrega. A regra R-A3 vive no sync-engine, então a função pura pode decidir deleção com dado incompleto |
| F-37 | sync-engine | 🟢 | Invalidação de token dispara full resync completo mesmo com ancestral local íntegro; comparar contra o ancestral custaria muito menos que reescrever tudo |
| F-38 | sync-engine | 🟡 | `suspended` (R-A3) não tem transição de saída declarada: quando o evento reentra na janela observável, nada define quem reativa o mapeamento — estado sem caminho de volta |
| F-39 | repository | 🟢 | O journal escreve o plano inteiro antes de aplicar qualquer coisa: em full resync de 1.000 eventos/lado é uma escrita grande antes de qualquer progresso observável |
| F-40 | sync-engine | 🟡 | O journal criou um novo estado de processo — "ciclo aberto" — cuja recuperação não tem passo declarado na CLI. O operador não sabe se precisa fazer algo |
| F-41 | sync-engine | 🟢 | `SyncReport` não tem campo para chaves suspensas por oscilação — o dado existe internamente e não sai |
| F-42 | repository | 🟡 | o journal cresce a cada ciclo e a política de retenção de V(2) não o menciona; a 10× uso o histórico domina o banco |
| F-43 | reconciler | 🟡 | `plan(deltas, ancestors)` assume que deltas e ancestrais dos dois lados cabem em memória ao mesmo tempo. Verdadeiro em 1.000 eventos/lado, mas o limite não está declarado — a premissa é tácita |
| F-44 | normalizer | 🟡 | Tolerância zero à variação: `.ics` com `DTSTAMP` ausente, `TZID` desconhecido pela base tz local ou campo fora do padrão não tem comportamento degradado definido — só o caminho feliz |
| F-45 | repository | 🟢 | `conflict` tem índice só em `state`; consultas por chave de evento (o caminho que o ciclo usa para saber se a chave está bloqueada) fazem varredura |
| F-46 | normalizer | 🟡 | Emitir `VTIMEZONE` (RFC 5545 §3.6.5) exige o bloco serializado da zona; `zoneinfo` fornece regras de transição, não blocos `VTIMEZONE` prontos. De onde vem o bloco não está definido — é Tier 3 escondido dentro de um requisito de conformidade |
| F-47 | cli | 🟡 | Um conflito aberto congela a chave indefinidamente e nada comunica ao operador que N eventos estão parados aguardando decisão — trabalho bloqueado invisível |
| F-48 | repository | 🟢 | A assinatura de `commit()` diverge entre architecture.md (writes, ancestors, tokens) e data-model.md (inclui conflicts) — contrato ambíguo na hora de implementar |
| F-49 | repository | 🟢 | Nada impede duas execuções simultâneas do ciclo sobre o mesmo `.db`; o lock do SQLite falha a segunda no meio, deixando estado parcialmente aplicado |
| F-50 | normalizer | 🟢 | A interface `to_canonical`/`to_ics` não parametriza dialeto, mas os dois provedores têm dialetos diferentes: ou o normalizer conhece ambos (viola SRP) ou cada provider ajusta depois (duplicação que a P1 quis evitar) |
| F-51 | normalizer | 🟢 | R-A2 (all-day ocupa `[00:00,24:00)` e bloqueia) é convenção do projeto decidida pelo operador, não regra normativa; o texto a apresenta junto de regras de RFC, o que confunde a origem |
| F-52 | repository | 🟡 | A retomada pode remarcar uma ação já marcada; `mark_applied` precisa ser idempotente e isso não está declarado |
| F-53 | policies | 🟡 | POL-2 (LWW) usa "timestamp de modificação mais recente", mas o modelo canônico não tem `LAST-MODIFIED` — a política está catalogada sem o dado de entrada que ela exige |
| F-54 | normalizer | 🟡 | O fingerprint é mecanismo próprio sem referência: nenhuma fonte foi citada para o conjunto de campos excluídos. É decisão de projeto apresentada como solução técnica derivada |
| F-55 | sync-engine | 🔴 | A neutralização de eco compara versão/ETag, mas o provedor pode normalizar o recurso ao gravar (recalcular `DTSTAMP`, reescrever `SEQUENCE`, reordenar campos). A versão devolvida então não corresponde ao conteúdo que o sincronizador crê ter gravado, e o pull seguinte vê diferença real de conteúdo → propaga de volta → ping-pong permanente entre os dois lados a cada ciclo. Falta comparar conteúdo normalizado, não apenas versão |
| F-56 | canonical-event | 🟢 | `recurrence_id` é `None` no domínio e `''` no SQLite; a fronteira não é declarada, e dois códigos corretos podem discordar sobre o que é a mesma chave |
| F-57 | normalizer | 🟡 | Se o round-trip não for idempotente (`to_canonical(to_ics(e)) ≠ e` por campo não mapeado que se perde), cada ciclo reescreve o evento e o marca como mudado do outro lado — realimenta CTL-01 mesmo sem nenhuma edição humana |
| F-58 | cli | 🟢 | `conflicts resolve` não exige confirmação: qualquer processo local com acesso ao `.db` altera o ancestral e força sobrescrita do calendário no ciclo seguinte |
| F-59 | overlap-detector | 🟡 | Fronteira ambígua: o reconciler compara eventos e o overlap-detector compara ocorrências, mas nada define quem expande a série no fluxo do ciclo nem com qual janela |
| F-60 | repository | 🟢 | `close_cycle(tokens)` não define o destino das ações planejadas e não marcadas: somem, viram pendência, ou impedem o fechamento? |
| F-61 | repository | 🟡 | Ancestral e fila de conflitos crescem indefinidamente: nada remove ancestral de evento deletado nos dois lados nem arquiva conflito resolvido. A 10× escala o banco cresce sem limite e sem valor correspondente |
| F-62 | cli | 🟡 | `conflicts resolve --take a\ | b\ | merge` oferece `merge` mesmo quando o conflito é SAME_FIELD, onde mesclar não tem significado — opção inválida apresentada sem contexto |
| F-63 | cli | 🟢 | O `--dry-run` exibe um plano, mas não há como aplicar exatamente aquele plano: o estado pode mudar entre a inspeção e a execução |
| F-64 | sync-engine | 🟡 | O circuit breaker de paginação (A-3) é citado sem valor: "limite máximo de páginas" sem número é parâmetro inventado na hora de codar (AP7) |
| F-65 | provider-beta | 🟡 | `write()` de evento cujo `DTSTART` cai fora da janela do provedor não tem semântica definida: aceita e some do delta seguinte, ou rejeita? A Regra 1 depende justamente do que ele devolve nesse caso |
| F-66 | recurrence | 🟡 | `recurring-ical-events` opera sobre um VCALENDAR com mestre e exceções juntos; o modelo canônico é por evento. A unidade de entrada de `expand()` não está definida |
| F-67 | policies | 🟡 | A precedência por delta relativo ao ancestral do próprio lado é indefinida quando NÃO há ancestral — criação concorrente com o mesmo UID (IDENTITY_COLLISION). POL-1 fica sem regra exatamente no caso que mais precisa dela |
| F-68 | sync-engine | 🔴 | PR-6 admite que write() no provedor e commit() local não são atômicos, mas nada define o que ocorre se o processo morrer entre os dois: a escrita já está no provedor e o ancestral não tem a versão resultante → no ciclo seguinte o eco é lido como mudança externa concorrente e gera conflito falso, ou sobrescreve o outro lado. Falta journal de intenção (write-ahead) antes de escrever |
| F-69 | normalizer | 🟡 | `.ics` de fonte externa com `RRULE` sem `UNTIL`/`COUNT` e `FREQ=SECONDLY` provoca expansão ilimitada → exaustão de memória/CPU. Nenhum limite de instâncias por expansão foi declarado |
| F-70 | policies | 🟢 | `ESCALATE` não define dono nem prazo: um conflito sem decisão bloqueia a chave para sempre, e o fluxo não prevê nenhuma reação a isso |
| F-71 | conflict-queue | 🟢 | A entidade conflito ficou partida em dois módulos — transição pura aqui, persistência no repository. Nada garante que o estado gravado é o que a transição produziu |
| F-72 | cli | 🟡 | Com a histerese, uma chave suspensa por oscilação passa a ser mais um motivo para "nada acontece" naquele evento; a saída precisa distinguir bloqueio por conflito de bloqueio por oscilação, ou o operador conclui que o sync está quebrado |
| F-73 | conflict-queue | 🟡 | Resolver um conflito não aplica nada; só o próximo `sync` aplica. O operador resolve, nada acontece, e o handoff entre M-08 e M-10 fica ambíguo |
| F-74 | repository | 🟡 | O lock de execução impede duas instâncias, mas nada libera lock órfão deixado por processo morto: o próximo ciclo recusa rodar indefinidamente |
| F-75 | recurrence | 🟢 | Séries sem `UNTIL` são infinitas; expandir "todo o futuro" consome recurso proporcional a nada. A janela é o que torna o custo proporcional ao valor — e ela não está definida |
| F-76 | repository | 🟢 | Esquema SQLite sem versionamento nem migração: qualquer alteração de campo invalida o `.db` existente, e o sistema não tem como detectar que o banco é de outra versão |
| F-77 | sync-engine | 🟡 | `Delta.invalidated=True` e `next_state_token=None` codificam estados diferentes que o contrato não separa: token nulo significa "faça full sync no próximo" ou "erro"? |
| F-78 | conflict-queue | 🟡 | Estados OPEN e RESOLVED apenas. Um conflito cuja chave foi deletada nos dois lados enquanto estava aberto fica órfão: não pode ser aplicado nem tem estado que o descreva |
| F-79 | reconciler | 🟡 | REF-7 formaliza sincronização de sistema de arquivos; a adaptação para merge por campo de evento é extrapolação legítima mas não referenciada — está apresentada como derivada da fonte |
| F-80 | normalizer | 🟡 | O fingerprint acrescenta serialização canônica e hash por evento a cada ciclo, somando-se ao parse já contabilizado: em 2.000 eventos o custo é parse + normalização + hash, e VAL-2 (<5 s) foi estimado sem esse terceiro termo |
| F-81 | repository | 🟢 | Não há forma de inspecionar o ancestral pela CLI; diagnosticar exige abrir o SQLite à mão |
| F-82 | repository | 🟡 | A desconcentração do sync-engine empurrou massa para cá: ancestral, mapa de identidade, tokens, fila, journal, retenção, lock e versão de esquema. O risco de god module migrou de módulo em vez de desaparecer |
| F-83 | conflict-queue | 🟡 | A detecção de oscilação exige histórico de direção por chave, que vive no journal; a retenção do journal (20 ciclos) e o critério de oscilação (3 ciclos) funcionam juntos hoje, mas a dependência entre os dois parâmetros não está declarada e uma mudança de retenção quebra o detector em silêncio |
| F-84 | normalizer | 🟡 | O fingerprint é acoplado à versão das regras de normalização: mudar qualquer regra invalida TODOS os ancestrais gravados de uma vez (todo evento parece modificado). Falta versão do algoritmo no ancestral e caminho de recálculo |
| F-85 | repository | 🟡 | Conteúdo de calendário (potencialmente sensível) é gravado em claro no SQLite, incluindo `value_a_ics`/`value_b_ics` dos conflitos; nenhuma permissão de arquivo nem política de retenção declarada |
| F-86 | repository | 🔴 | A Regra 1 redefiniu o ancestral como `AncestorSide = fingerprint, versão, sequence, dtstamp` — e ao fazer isso removeu o CONTEÚDO ancestral sem perceber quem dependia dele: POL-4, o merge 3-vias por campo, precisa dos VALORES ancestrais campo a campo para decidir o que mesclar. Com só o hash, o merge por campo é impossível e todo conflito escala para a fila, revertendo a decisão de P0 |
| F-87 | normalizer | 🟡 | `.ics` com `TZID` não-UTC exige `VTIMEZONE` correspondente embutido no calendário (RFC 5545); o design preserva `tzid` mas não menciona emitir `VTIMEZONE` — a saída não é interoperável |
| F-88 | sync-engine | 🟡 | Não existe sinal de erro nem detecção de oscilação: a mesma chave alternando A→B→A em ciclos consecutivos roda para sempre sem que nada perceba |
| F-89 | repository | 🟡 | O journal grava valores descartados (conteúdo de calendário) por tempo indefinido; a retenção declarada em V(2) cobre conflitos arquivados, não o journal — amplia a superfície de dado sensível em claro que SEC-02 abriu |
| F-90 | normalizer | 🔴 | O fingerprint fecha o eco quando o provedor renormaliza METADADOS, mas não quando a normalização é semanticamente visível (trunca `DESCRIPTION`, descarta campo que o canônico mapeia): o que volta tem fingerprint diferente do que foi enviado, o sistema conclui "mudança externa" e reescreve — a oscilação sobrevive, agora com fingerprint. Falta convergir gravando no ancestral o fingerprint do que o provedor DEVOLVE, não do que foi enviado |
| F-91 | provider-alpha | 🟢 | `provider_id` vindo do "provedor" é usado para localizar o arquivo `.ics` no disco — id contendo `../` escapa do diretório do provedor |
| F-92 | canonical-event | 🟡 | Assume que todo VEVENT traz `UID`. Arquivos reais e algumas exceções de série omitem; sem regra de fallback declarada, a chave de identidade fica indefinida |
| F-93 | repository | 🟡 | A retomada de journal aberto assume que o provedor está consultável naquele momento. Provedor indisponível na retomada deixa o ciclo bloqueado sem caminho declarado de saída |
| F-94 | normalizer | 🟡 | Assume que `DTEND` existe. RFC 5545 permite `DURATION` em lugar de `DTEND`, e all-day frequentemente vem sem fim. O modelo canônico não tem representação de duração |
| F-95 | normalizer | 🟡 | O fingerprint exige ordenação canônica de coleções (`ATTENDEE`, `EXDATE`) e normalização de texto (caixa, espaços, quebras de linha em `DESCRIPTION`). Sem regra escrita, duas execuções corretas divergem no hash |
| F-96 | cli | 🟢 | Exit codes não definidos: impossível usar em script ("saiu 0 com conflitos abertos" é sucesso ou não?) |
| F-97 | provider-beta | 🔴 | O contrato `Provider` não define o que `pull(None)` significa para um provedor com janela: full sync de todo o calendário ou apenas da janela? Duas implementações "corretas" divergem, e o sync-engine não tem como saber qual recebeu |
| F-98 | cli | 🟡 | Não há comando para VER o conflito (os três valores: A, B e ancestral) antes de decidir; `list` só enumera. O operador decide às cegas |
| F-99 | overlap-detector | 🟢 | O claim "O(n log n)" vale para detectar existência de sobreposição; enumerar todos os pares é O(n log n + k). O snippet de referência reconstrói a lista de ativos a cada item — a referência não sustenta o claim como está escrito |
| F-100 | cli | 🟢 | O comando `journal` imprime valores descartados no terminal — mesma classe de exposição de SEC-02, agora na superfície visível |
| F-101 | repository | 🟡 | `commit(writes, ...)`: `writes` são escritas já aplicadas no provedor ou a aplicar? Duas implementações corretas do mesmo contrato fariam coisas opostas |
| F-102 | normalizer | 🔴 | Colisão entre dois mecanismos de V(2): o fingerprint (MEC-A) exclui `SEQUENCE` e `DTSTAMP` justamente para ignorar renormalização do provedor — mas são esses os campos que POL-1 usa para decidir precedência. Uma revisão que muda só `SEQUENCE`/`DTSTAMP` (organizador reemite a mesma reunião) tem fingerprint idêntico, é tratada como no-op, e a nova revisão nunca propaga: os dois lados ficam com metadados divergentes que o sistema nunca mais reconcilia |
| F-103 | policies | 🟡 | POL-1 assume `SEQUENCE` confiável, mas edições por UI raramente o incrementam. Com `SEQUENCE` igual e `DTSTAMP` igual (granularidade de segundo) a política não decide — não há regra de desempate final declarada |
| F-104 | repository | 🟡 | Sendo armazenamento burro com retenção automática, nada impede que a poda apague journal que uma auditoria em curso está usando — a regra de retenção não tem exceção declarada |
| F-105 | sync-engine | 🔴 | Se `write()` falhar no meio da aplicação do plano, metade das ações está aplicada e o ancestral não reflete nenhuma. O ciclo seguinte pode interpretar as mudanças já aplicadas como edições externas e revertê-las — regressão de dados |
