# Matriz de cobertura — crítica adversarial

Modo GERATIVO (AP1): cada linha é um cenário de falha produzido pela pergunta
central da lente aplicada ao módulo — não um juízo de qualidade.

Lentes universais: Assumptions, Architectural, Implementability, Scientific,
Security, Performance, Regulatory.
Lentes condicionais ativadas na iteração 1: Resilience, UI/UX,
Sustainability / Proportionality, Process / Workflow, Governance / Accountability,
Observability / Operability, Control Engineering, Linguistics / Grammar,
Mechanical Engineering.
Não ativadas: Migration / Coexistence, Ethical / Human Impact, Game Theory.

## Iteração 1 — V(1)

| id | module | lens | severity | description |
|------|--------|------|----------|-------------|
| ASS-01 | sync-engine | Assumptions | 🔴 | PR-6 admite que write() no provedor e commit() local não são atômicos, mas nada define o que ocorre se o processo morrer entre os dois: a escrita já está no provedor e o ancestral não tem a versão resultante → no ciclo seguinte o eco é lido como mudança externa concorrente e gera conflito falso, ou sobrescreve o outro lado. Falta journal de intenção (write-ahead) antes de escrever |
| ASS-02 | reconciler | Assumptions | 🔴 | `reconcile(a, b, ancestor)` assume que `a=None` significa "não existe". Em provider-beta, `None` também significa "fora da janela observável" — informação que a assinatura pura não carrega. A regra R-A3 vive no sync-engine, então a função pura pode decidir deleção com dado incompleto |
| ASS-03 | canonical-event | Assumptions | 🟡 | Assume que todo VEVENT traz `UID`. Arquivos reais e algumas exceções de série omitem; sem regra de fallback declarada, a chave de identidade fica indefinida |
| ASS-04 | normalizer | Assumptions | 🟡 | Assume que `DTEND` existe. RFC 5545 permite `DURATION` em lugar de `DTEND`, e all-day frequentemente vem sem fim. O modelo canônico não tem representação de duração |
| ASS-05 | policies | Assumptions | 🟡 | POL-1 assume `SEQUENCE` confiável, mas edições por UI raramente o incrementam. Com `SEQUENCE` igual e `DTSTAMP` igual (granularidade de segundo) a política não decide — não há regra de desempate final declarada |
| ASS-06 | repository | Assumptions | 🟡 | Assume relógios comparáveis: `DTSTAMP` vindo de dois provedores distintos é comparado sem tratar skew, e `synced_at` supõe relógio local monotônico |
| ARC-01 | conflict-queue | Architectural | 🟡 | É o único módulo de domínio que depende de I/O (M-11) — não testável isoladamente sem banco, quebrando a simetria de núcleo puro que M-06/M-07 estabelecem |
| ARC-02 | sync-engine | Architectural | 🟡 | Depende de 7 módulos e concentra orquestração, full-resync, neutralização de eco, R-A3, paginação e circuit breaker. Tende a god module; a granularidade E=I₀/C fica no limite de uma sessão |
| ARC-03 | normalizer | Architectural | 🟢 | A interface `to_canonical`/`to_ics` não parametriza dialeto, mas os dois provedores têm dialetos diferentes: ou o normalizer conhece ambos (viola SRP) ou cada provider ajusta depois (duplicação que a P1 quis evitar) |
| ARC-04 | overlap-detector | Architectural | 🟡 | Fronteira ambígua: o reconciler compara eventos e o overlap-detector compara ocorrências, mas nada define quem expande a série no fluxo do ciclo nem com qual janela |
| ARC-05 | cli | Architectural | 🟢 | Não há porta de apresentação: a formatação tabular fica dentro do CLI, acoplada à forma do `SyncReport` |
| IMP-01 | provider-beta | Implementability | 🔴 | O contrato pede janela obrigatória + paginação que repete item já entregue + invalidação de token + tombstones, sem nenhuma especificação determinística de QUANDO cada comportamento ocorre. Sem isso o simulador é arbitrário e os testes não reproduzem |
| IMP-02 | policies | Implementability | 🟡 | POL-4 precisa de comparação campo a campo, mas `TimeSpec` não tem regra: mudar `tzid` preservando `instant_utc` conta como mudança de campo ou não? |
| IMP-03 | recurrence | Implementability | 🟡 | `recurring-ical-events` opera sobre um VCALENDAR com mestre e exceções juntos; o modelo canônico é por evento. A unidade de entrada de `expand()` não está definida |
| IMP-04 | sync-engine | Implementability | 🟡 | O circuit breaker de paginação (A-3) é citado sem valor: "limite máximo de páginas" sem número é parâmetro inventado na hora de codar (AP7) |
| IMP-05 | repository | Implementability | 🟢 | A assinatura de `commit()` diverge entre architecture.md (writes, ancestors, tokens) e data-model.md (inclui conflicts) — contrato ambíguo na hora de implementar |
| SCI-01 | policies | Scientific | 🟡 | POL-2 (LWW) usa "timestamp de modificação mais recente", mas o modelo canônico não tem `LAST-MODIFIED` — a política está catalogada sem o dado de entrada que ela exige |
| SCI-02 | overlap-detector | Scientific | 🟢 | O claim "O(n log n)" vale para detectar existência de sobreposição; enumerar todos os pares é O(n log n + k). O snippet de referência reconstrói a lista de ativos a cada item — a referência não sustenta o claim como está escrito |
| SCI-03 | reconciler | Scientific | 🟡 | REF-7 formaliza sincronização de sistema de arquivos; a adaptação para merge por campo de evento é extrapolação legítima mas não referenciada — está apresentada como derivada da fonte |
| SCI-04 | normalizer | Scientific | 🟢 | R-A2 (all-day ocupa `[00:00,24:00)` e bloqueia) é convenção do projeto decidida pelo operador, não regra normativa; o texto a apresenta junto de regras de RFC, o que confunde a origem |
| SEC-01 | normalizer | Security | 🟡 | `.ics` de fonte externa com `RRULE` sem `UNTIL`/`COUNT` e `FREQ=SECONDLY` provoca expansão ilimitada → exaustão de memória/CPU. Nenhum limite de instâncias por expansão foi declarado |
| SEC-02 | repository | Security | 🟡 | Conteúdo de calendário (potencialmente sensível) é gravado em claro no SQLite, incluindo `value_a_ics`/`value_b_ics` dos conflitos; nenhuma permissão de arquivo nem política de retenção declarada |
| SEC-03 | cli | Security | 🟢 | `conflicts resolve` não exige confirmação: qualquer processo local com acesso ao `.db` altera o ancestral e força sobrescrita do calendário no ciclo seguinte |
| SEC-04 | provider-alpha | Security | 🟢 | `provider_id` vindo do "provedor" é usado para localizar o arquivo `.ics` no disco — id contendo `../` escapa do diretório do provedor |
| SEC-05 | provider-beta | Security | 🟢 | duplica: SEC-04 — mesmo defeito de path traversal na resolução de `provider_id` para caminho de arquivo |
| PER-01 | sync-engine | Performance | 🟡 | VAL-2 (<5 s) mede o ciclo incremental; o pior caso real é o full resync após invalidação de token, que reconstrói mapa de identidade e ancestral de 1.000 eventos por lado — sem limiar definido |
| PER-02 | recurrence | Performance | 🟡 | VAL-1 conta eventos, não ocorrências: 1.000 eventos com séries diárias expandidas numa janela ampla produzem dezenas de milhares de ocorrências. A janela de expansão não está definida em lugar nenhum |
| PER-03 | repository | Performance | 🟢 | `conflict` tem índice só em `state`; consultas por chave de evento (o caminho que o ciclo usa para saber se a chave está bloqueada) fazem varredura |
| PER-04 | normalizer | Performance | 🟢 | Parse e serialização de texto `.ics` por evento a cada ciclo (2.000 parses) tende a dominar o tempo; o ETag existe justamente para pular o inalterado, mas o design não o usa para evitar parse |
| REG-01 | canonical-event | Regulatory | 🟡 | RFC 5545 exige `UID` e `DTSTAMP` em todo VEVENT; nenhuma validação de conformidade está prevista na saída `to_ics`, então o sistema pode emitir `.ics` inválido |
| REG-02 | normalizer | Regulatory | 🟡 | `.ics` com `TZID` não-UTC exige `VTIMEZONE` correspondente embutido no calendário (RFC 5545); o design preserva `tzid` mas não menciona emitir `VTIMEZONE` — a saída não é interoperável |
| REG-03 | policies | Regulatory | 🟢 | RFC 5546 §2.1.5 normatiza precedência no contexto de mensagens iTIP; usá-la como regra geral de sync é extensão razoável, mas rotulá-la "normativa" aqui é forte demais para a traçabilidade |
| RES-01 | sync-engine | Resilience | 🔴 | Se `write()` falhar no meio da aplicação do plano, metade das ações está aplicada e o ancestral não reflete nenhuma. O ciclo seguinte pode interpretar as mudanças já aplicadas como edições externas e revertê-las — regressão de dados |
| RES-02 | provider-beta | Resilience | 🟡 | duplica: IMP-04 — paginação que repete item já entregue (A-2) sem limite de páginas nem detecção de ciclo faz o pull girar indefinidamente |
| RES-03 | sync-engine | Resilience | 🟡 | R-A3 exige `get(provider_id)` para distinguir saída-de-janela de deleção; o design não diz o que fazer se esse `get()` falhar. O fallback silencioso "tratar como deleção" é destrutivo |
| RES-04 | repository | Resilience | 🟢 | Nada impede duas execuções simultâneas do ciclo sobre o mesmo `.db`; o lock do SQLite falha a segunda no meio, deixando estado parcialmente aplicado |
| UX-01 | cli | UI/UX | 🟡 | `conflicts resolve --take a\|b\|merge` oferece `merge` mesmo quando o conflito é SAME_FIELD, onde mesclar não tem significado — opção inválida apresentada sem contexto |
| UX-02 | cli | UI/UX | 🟡 | Não há comando para VER o conflito (os três valores: A, B e ancestral) antes de decidir; `list` só enumera. O operador decide às cegas |
| UX-03 | cli | UI/UX | 🟡 | Um conflito aberto congela a chave indefinidamente e nada comunica ao operador que N eventos estão parados aguardando decisão — trabalho bloqueado invisível |
| UX-04 | cli | UI/UX | 🟢 | Exit codes não definidos: impossível usar em script ("saiu 0 com conflitos abertos" é sucesso ou não?) |
| UX-05 | cli | UI/UX | 🟢 | O `--dry-run` exibe um plano, mas não há como aplicar exatamente aquele plano: o estado pode mudar entre a inspeção e a execução |
| SUS-01 | repository | Sustainability / Proportionality | 🟡 | Ancestral e fila de conflitos crescem indefinidamente: nada remove ancestral de evento deletado nos dois lados nem arquiva conflito resolvido. A 10× escala o banco cresce sem limite e sem valor correspondente |
| SUS-02 | recurrence | Sustainability / Proportionality | 🟢 | Séries sem `UNTIL` são infinitas; expandir "todo o futuro" consome recurso proporcional a nada. A janela é o que torna o custo proporcional ao valor — e ela não está definida |
| SUS-03 | sync-engine | Sustainability / Proportionality | 🟢 | Invalidação de token dispara full resync completo mesmo com ancestral local íntegro; comparar contra o ancestral custaria muito menos que reescrever tudo |
| PRO-01 | conflict-queue | Process / Workflow | 🟡 | Estados OPEN e RESOLVED apenas. Um conflito cuja chave foi deletada nos dois lados enquanto estava aberto fica órfão: não pode ser aplicado nem tem estado que o descreva |
| PRO-02 | sync-engine | Process / Workflow | 🟡 | `suspended` (R-A3) não tem transição de saída declarada: quando o evento reentra na janela observável, nada define quem reativa o mapeamento — estado sem caminho de volta |
| PRO-03 | conflict-queue | Process / Workflow | 🟡 | Resolver um conflito não aplica nada; só o próximo `sync` aplica. O operador resolve, nada acontece, e o handoff entre M-08 e M-10 fica ambíguo |
| PRO-04 | policies | Process / Workflow | 🟢 | `ESCALATE` não define dono nem prazo: um conflito sem decisão bloqueia a chave para sempre, e o fluxo não prevê nenhuma reação a isso |
| GOV-01 | repository | Governance / Accountability | 🟡 | Não há trilha de auditoria: o ancestral guarda só o estado corrente, então quando uma política descarta o valor de um lado não fica registro de qual valor foi descartado. "Por que meu evento mudou?" é irrespondível |
| GOV-02 | sync-engine | Governance / Accountability | 🟡 | `SyncReport` é efêmero — devolvido ao CLI e perdido. Não existe histórico de ciclos, então nenhuma ação é atribuível depois do fato |
| GOV-03 | conflict-queue | Governance / Accountability | 🟢 | `resolution` grava a escolha, mas não sob qual política ativa nem em que momento do histórico — e a política é global e pode mudar entre ciclos |
| OBS-01 | sync-engine | Observability / Operability | 🟡 | Nenhum log estruturado previsto: descobrir por que um evento específico não propagou exige depurador, não inspeção |
| OBS-02 | cli | Observability / Operability | 🟢 | `status` não tem conteúdo definido (tokens? contagem de ancestral? conflitos abertos? último ciclo?) — comando sem contrato |
| OBS-03 | repository | Observability / Operability | 🟢 | Não há forma de inspecionar o ancestral pela CLI; diagnosticar exige abrir o SQLite à mão |
| CTL-01 | sync-engine | Control Engineering | 🔴 | A neutralização de eco compara versão/ETag, mas o provedor pode normalizar o recurso ao gravar (recalcular `DTSTAMP`, reescrever `SEQUENCE`, reordenar campos). A versão devolvida então não corresponde ao conteúdo que o sincronizador crê ter gravado, e o pull seguinte vê diferença real de conteúdo → propaga de volta → ping-pong permanente entre os dois lados a cada ciclo. Falta comparar conteúdo normalizado, não apenas versão |
| CTL-02 | sync-engine | Control Engineering | 🟡 | Não existe sinal de erro nem detecção de oscilação: a mesma chave alternando A→B→A em ciclos consecutivos roda para sempre sem que nada perceba |
| CTL-03 | normalizer | Control Engineering | 🟡 | Se o round-trip não for idempotente (`to_canonical(to_ics(e)) ≠ e` por campo não mapeado que se perde), cada ciclo reescreve o evento e o marca como mudado do outro lado — realimenta CTL-01 mesmo sem nenhuma edição humana |
| LIN-01 | provider-beta | Linguistics / Grammar | 🔴 | O contrato `Provider` não define o que `pull(None)` significa para um provedor com janela: full sync de todo o calendário ou apenas da janela? Duas implementações "corretas" divergem, e o sync-engine não tem como saber qual recebeu |
| LIN-02 | sync-engine | Linguistics / Grammar | 🟡 | `Delta.invalidated=True` e `next_state_token=None` codificam estados diferentes que o contrato não separa: token nulo significa "faça full sync no próximo" ou "erro"? |
| LIN-03 | repository | Linguistics / Grammar | 🟡 | `commit(writes, ...)`: `writes` são escritas já aplicadas no provedor ou a aplicar? Duas implementações corretas do mesmo contrato fariam coisas opostas |
| LIN-04 | canonical-event | Linguistics / Grammar | 🟢 | `recurrence_id` é `None` no domínio e `''` no SQLite; a fronteira não é declarada, e dois códigos corretos podem discordar sobre o que é a mesma chave |
| MEC-01 | recurrence | Mechanical Engineering | 🟡 | PR-7 assume que `recurring-ical-events` expande exceções corretamente, sem versão fixada e sem teste de contrato — uma mudança de comportamento entre versões da lib altera silenciosamente a detecção de sobreposição |
| MEC-02 | normalizer | Mechanical Engineering | 🟡 | Tolerância zero à variação: `.ics` com `DTSTAMP` ausente, `TZID` desconhecido pela base tz local ou campo fora do padrão não tem comportamento degradado definido — só o caminho feliz |
| MEC-03 | repository | Mechanical Engineering | 🟢 | Esquema SQLite sem versionamento nem migração: qualquer alteração de campo invalida o `.db` existente, e o sistema não tem como detectar que o banco é de outra versão |

## Iteração 2 — V(2)

Mesmo conjunto de lentes re-declarado contra a nova arquitetura (9 condicionais
ativadas; Migration / Coexistence, Ethical / Human Impact e Game Theory seguem
não ativadas por sinal de projeto). Alvo desta rodada: o acoplamento criado pela
redistribuição de responsabilidade e os cinco mecanismos MEC-A..E, que na
iteração 1 não existiam e portanto nunca passaram por lente nenhuma.

| id | module | lens | severity | description |
|------|--------|------|----------|-------------|
| ASS-07 | normalizer | Assumptions | 🔴 | Colisão entre dois mecanismos de V(2): o fingerprint (MEC-A) exclui `SEQUENCE` e `DTSTAMP` justamente para ignorar renormalização do provedor — mas são esses os campos que POL-1 usa para decidir precedência. Uma revisão que muda só `SEQUENCE`/`DTSTAMP` (organizador reemite a mesma reunião) tem fingerprint idêntico, é tratada como no-op, e a nova revisão nunca propaga: os dois lados ficam com metadados divergentes que o sistema nunca mais reconcilia |
| ASS-08 | repository | Assumptions | 🟡 | A retomada de journal aberto assume que o provedor está consultável naquele momento. Provedor indisponível na retomada deixa o ciclo bloqueado sem caminho declarado de saída |
| ASS-09 | reconciler | Assumptions | 🟡 | `plan(deltas, ancestors)` assume que deltas e ancestrais dos dois lados cabem em memória ao mesmo tempo. Verdadeiro em 1.000 eventos/lado, mas o limite não está declarado — a premissa é tácita |
| ARC-06 | reconciler | Architectural | 🟡 | `plan()` precisa saber quais chaves estão bloqueadas por conflito aberto e qual política vige. Se receber isso por argumento continua puro, mas a fronteira reconciler ↔ conflict-queue passou a existir e não está declarada |
| ARC-07 | repository | Architectural | 🟡 | A desconcentração do sync-engine empurrou massa para cá: ancestral, mapa de identidade, tokens, fila, journal, retenção, lock e versão de esquema. O risco de god module migrou de módulo em vez de desaparecer |
| ARC-08 | conflict-queue | Architectural | 🟢 | A entidade conflito ficou partida em dois módulos — transição pura aqui, persistência no repository. Nada garante que o estado gravado é o que a transição produziu |
| IMP-06 | normalizer | Implementability | 🟡 | O fingerprint exige ordenação canônica de coleções (`ATTENDEE`, `EXDATE`) e normalização de texto (caixa, espaços, quebras de linha em `DESCRIPTION`). Sem regra escrita, duas execuções corretas divergem no hash |
| IMP-07 | repository | Implementability | 🟡 | A retomada pode remarcar uma ação já marcada; `mark_applied` precisa ser idempotente e isso não está declarado |
| SCI-05 | normalizer | Scientific | 🟡 | O fingerprint é mecanismo próprio sem referência: nenhuma fonte foi citada para o conjunto de campos excluídos. É decisão de projeto apresentada como solução técnica derivada |
| SEC-06 | repository | Security | 🟡 | O journal grava valores descartados (conteúdo de calendário) por tempo indefinido; a retenção declarada em V(2) cobre conflitos arquivados, não o journal — amplia a superfície de dado sensível em claro que SEC-02 abriu |
| PER-05 | normalizer | Performance | 🟡 | O fingerprint acrescenta serialização canônica e hash por evento a cada ciclo, somando-se ao parse já contabilizado: em 2.000 eventos o custo é parse + normalização + hash, e VAL-2 (<5 s) foi estimado sem esse terceiro termo |
| PER-06 | repository | Performance | 🟢 | O journal escreve o plano inteiro antes de aplicar qualquer coisa: em full resync de 1.000 eventos/lado é uma escrita grande antes de qualquer progresso observável |
| REG-04 | normalizer | Regulatory | 🟡 | Emitir `VTIMEZONE` (RFC 5545 §3.6.5) exige o bloco serializado da zona; `zoneinfo` fornece regras de transição, não blocos `VTIMEZONE` prontos. De onde vem o bloco não está definido — é Tier 3 escondido dentro de um requisito de conformidade |
| RES-05 | sync-engine | Resilience | 🔴 | MEC-C manda resolver `Unobservable` consultando `get()`. Num full resync do provider-beta, TODA chave do ancestral fora da janela vira `Unobservable` — 1.000 chamadas `get()` extras num único ciclo, e a falha de qualquer uma trava o ciclo. O mecanismo que protege contra deleção indevida vira um problema de escala e de disponibilidade |
| RES-06 | repository | Resilience | 🟡 | O lock de execução impede duas instâncias, mas nada libera lock órfão deixado por processo morto: o próximo ciclo recusa rodar indefinidamente |
| UX-06 | cli | UI/UX | 🟡 | `journal` entrou como comando sem definir o que exibe nem como se navega um histórico que cresce a cada ciclo |
| UX-07 | cli | UI/UX | 🟢 | Com `STALE` e `APPLIED`, o operador passa a ter quatro estados de conflito para entender; sem explicação na saída, viram jargão interno vazando para a superfície |
| SUS-04 | repository | Sustainability / Proportionality | 🟡 | duplica: SEC-06 — o journal cresce a cada ciclo e a política de retenção de V(2) não o menciona; a 10× uso o histórico domina o banco |
| PRO-05 | conflict-queue | Process / Workflow | 🟡 | Com quatro estados, a transição RESOLVED → STALE não está definida: o operador resolve, o evento some dos dois lados antes do próximo `sync`, e a decisão gravada não tem onde aterrissar |
| PRO-06 | sync-engine | Process / Workflow | 🟡 | O journal criou um novo estado de processo — "ciclo aberto" — cuja recuperação não tem passo declarado na CLI. O operador não sabe se precisa fazer algo |
| GOV-04 | repository | Governance / Accountability | 🟡 | O journal registra o que foi aplicado, mas não sob qual versão de código/esquema/política — auditar um ciclo antigo não revela qual regra de merge vigia na hora |
| OBS-04 | sync-engine | Observability / Operability | 🟡 | A detecção de oscilação prometida ao journal não tem critério: quantos ciclos alternando caracterizam oscilação? Parâmetro sem valor — a mesma classe de defeito que IMP-04 e que V(2) corrigiu em outro lugar |
| CTL-04 | normalizer | Control Engineering | 🔴 | O fingerprint fecha o eco quando o provedor renormaliza METADADOS, mas não quando a normalização é semanticamente visível (trunca `DESCRIPTION`, descarta campo que o canônico mapeia): o que volta tem fingerprint diferente do que foi enviado, o sistema conclui "mudança externa" e reescreve — a oscilação sobrevive, agora com fingerprint. Falta convergir gravando no ancestral o fingerprint do que o provedor DEVOLVE, não do que foi enviado |
| CTL-05 | sync-engine | Control Engineering | 🟡 | Sem histerese: uma chave detectada em oscilação é reportada mas continua sendo reescrita a cada ciclo — o sistema observa o erro e não age sobre ele |
| LIN-05 | repository | Linguistics / Grammar | 🟡 | O contrato mais crítico do sistema é o menos especificado: `open_cycle(plan)`, `mark_applied(action)` e `commit(...)` aparecem sem tipos, sem ordem de chamada obrigatória e sem o que acontece se forem chamados fora de ordem |
| LIN-06 | canonical-event | Linguistics / Grammar | 🟢 | `Side` tem três variantes, mas nada define `Present` com conteúdo PARCIAL — o caso do provedor que devolve item resumido durante a paginação |
| MEC-04 | normalizer | Mechanical Engineering | 🟡 | O fingerprint é acoplado à versão das regras de normalização: mudar qualquer regra invalida TODOS os ancestrais gravados de uma vez (todo evento parece modificado). Falta versão do algoritmo no ancestral e caminho de recálculo |

## Iteração 3 — V(3)

Mesmo conjunto de lentes re-declarado contra V(3). Alvo: as três regras novas
(ancestral observado, presença por janela, repository burro) e o que `repository`
e `sync-engine` trocaram entre si.

| id | module | lens | severity | description |
|------|--------|------|----------|-------------|
| ASS-10 | repository | Assumptions | 🔴 | A Regra 1 redefiniu o ancestral como `AncestorSide = fingerprint, versão, sequence, dtstamp` — e ao fazer isso removeu o CONTEÚDO ancestral sem perceber quem dependia dele: POL-4, o merge 3-vias por campo, precisa dos VALORES ancestrais campo a campo para decidir o que mesclar. Com só o hash, o merge por campo é impossível e todo conflito escala para a fila, revertendo a decisão de P0 |
| LIN-07 | sync-engine | Linguistics / Grammar | 🔴 | Contradição entre contrato e regra: a porta `Provider` declara `write(op) -> Version`, mas a Regra 1 exige gravar no ancestral o RECURSO devolvido pelo provedor. Uma implementação que honra o contrato literalmente devolve só a versão, e a Regra 1 fica inaplicável sem ninguém violar contrato nenhum |
| ASS-11 | sync-engine | Assumptions | 🔴 | V(3) usa "janela declarada" para duas coisas diferentes: a janela de EXPANSÃO de recorrência (MEC-E, hoje-30d a hoje+365d) e a janela de OBSERVABILIDADE do provedor (`observability_window()`). A decisão de presença da Regra 2 depende da segunda; se o código usar a primeira, um evento que o provedor não observa mas que cai na janela de expansão vira `Absent` e a deleção é propagada — perda de dados por conflação de nomes |
| RES-07 | provider-beta | Resilience | 🟡 | `write()` de evento cujo `DTSTART` cai fora da janela do provedor não tem semântica definida: aceita e some do delta seguinte, ou rejeita? A Regra 1 depende justamente do que ele devolve nesse caso |
| ARC-09 | sync-engine | Architectural | 🟡 | A reconciliação de journal aberto exige um passe de leitura contra o provedor no início do ciclo — a dependência de disponibilidade que a Regra 2 tirou da porta da frente volta pela dos fundos, em caminho distinto de RES-05 |
| ASS-12 | policies | Assumptions | 🟡 | A precedência por delta relativo ao ancestral do próprio lado é indefinida quando NÃO há ancestral — criação concorrente com o mesmo UID (IDENTITY_COLLISION). POL-1 fica sem regra exatamente no caso que mais precisa dela |
| PER-07 | sync-engine | Performance | 🟡 | `Present(partial=True)` obriga leitura completa antes de reconciliar; um provedor que pagina com itens resumidos reintroduz N chamadas extras — a mitigação de RES-05 não cobre este caminho |
| IMP-08 | conflict-queue | Implementability | 🟡 | A detecção de oscilação exige histórico de direção por chave, que vive no journal; a retenção do journal (20 ciclos) e o critério de oscilação (3 ciclos) funcionam juntos hoje, mas a dependência entre os dois parâmetros não está declarada e uma mudança de retenção quebra o detector em silêncio |
| GOV-05 | repository | Governance / Accountability | 🟡 | Sendo armazenamento burro com retenção automática, nada impede que a poda apague journal que uma auditoria em curso está usando — a regra de retenção não tem exceção declarada |
| MEC-05 | normalizer | Mechanical Engineering | 🟡 | O recálculo de fingerprint por mudança de versão do algoritmo depende do snapshot ancestral (portanto de ASS-10) e nenhum comando o expõe: a migração existe no papel e não tem caminho de execução |
| UX-08 | cli | UI/UX | 🟡 | Com a histerese, uma chave suspensa por oscilação passa a ser mais um motivo para "nada acontece" naquele evento; a saída precisa distinguir bloqueio por conflito de bloqueio por oscilação, ou o operador conclui que o sync está quebrado |
| OBS-05 | sync-engine | Observability / Operability | 🟢 | `SyncReport` não tem campo para chaves suspensas por oscilação — o dado existe internamente e não sai |
| LIN-08 | repository | Linguistics / Grammar | 🟢 | `close_cycle(tokens)` não define o destino das ações planejadas e não marcadas: somem, viram pendência, ou impedem o fechamento? |
| SEC-07 | cli | Security | 🟢 | O comando `journal` imprime valores descartados no terminal — mesma classe de exposição de SEC-02, agora na superfície visível |
