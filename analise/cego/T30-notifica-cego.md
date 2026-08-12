# Reagrupamento cego de achados — T30-notifica

Você recebe 96 achados de uma crítica arquitetural. Cada um tem um id anônimo, o
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
| M-01 | http-api | Adaptador de entrada HTTP: rotas, validação de payload, autenticação por API key, tradução erro→status | `POST /notifications`, `GET /notifications/:id`, `GET\|PUT /recipients/:id/preferences`, `POST /unsubscribe` | ingestion, preferences |
| M-02 | cli | Superfície do operador (UC-8): explicar supressão, listar pendentes, reprocessar, subir o serviço | `explain <id>`, `pending`, `retry <id>`, `serve` | outbox, preferences, store |
| M-03 | ingestion | Transaction script de ingestão: idempotência de requisição (R-03), avalia supressão de estágio `ingest`, persiste notificação e enfileira entregas na MESMA transação (R-06) | `ingest(cmd, idempotencyKey) -> {notificationId, status, reason?}` | suppression, outbox, store |
| M-04 | suppression | Chain of Responsibility das 4 regras em 2 estágios; produz decisão nomeada com motivo do enum fechado | `evaluate(stage, ctx) -> {decision: allow\|suppress\|defer, reason?, until?}` | preferences, quiet-hours, rate-limiter, store |
| M-05 | preferences | Pessoas e preferências; resolve o padrão da categoria (invariante 3); opt-out por categoria e por canal | `recipient(id)`, `resolve(id, category, channel)`, `optOut(id, target)`, `put(id, prefs)` | store |
| M-06 | quiet-hours | Função PURA: a janela está aberta no fuso da pessoa? Quando abre? Trata cruzamento de meia-noite (EDGE-1) | `check(window, tz, now) -> {inWindow, opensAt?}` | — |
| M-07 | rate-limiter | Token bucket global por pessoa (PAR-11/12), consumido no momento da ENTREGA | `tryConsume(recipientId, now) -> {ok, retryAfter?}` | store |
| M-08 | outbox | Fila durável de entregas (R-06): enfileirar na transação de ingestão, reivindicar as devidas, registrar resultado e próxima tentativa | `enqueue(tx, deliveries)`, `claimDue(now, n)`, `recordResult(id, outcome, nextAt?)`, `deadLetter(id)` | store |
| M-09 | delivery-worker | Laço único: reivindica devidas, reavalia supressão de estágio `deliver`, chama o canal, aplica Full Jitter (PAR-01), dead-letter após PAR-04 tentativas | `tick(now) -> {claimed, delivered, failed}`, `start()` | outbox, suppression, ChannelPort |
| M-10 | channel-email | Adaptador SMTP (nodemailer): template, assunto/corpo, headers `List-Unsubscribe` + `List-Unsubscribe-Post` one-click (PAR-17) | `send(msg) -> {ok, permanent}` — implementa ChannelPort | — |
| M-11 | channel-webhook | Adaptador HTTP: assinatura HMAC-SHA256 sobre `id.timestamp.payload` (PAR-07/08), timeout PAR-10, 2xx = sucesso (PAR-09) | `send(msg) -> {ok, permanent}` — implementa ChannelPort | — |
| M-12 | store | Adaptador SQLite: schema, migração, transação, implementações concretas dos repositórios | `withTransaction(fn)`, repositórios por agregado | — |
| M-01 | http-api | Adaptador HTTP: rotas, validação, API key com **escopo de categorias**, token assinado de unsubscribe, saúde/métricas | `POST /notifications`, `GET /notifications/:id`, `GET\|PUT /recipients/:id/preferences`, `POST /unsubscribe`, `GET /health` | ingestion, preferences, outbox |
| M-02 | cli | Superfície do operador: explicar por notificação **ou por pessoa/período**, listar pendentes, reprocessar, podar | `explain <id>`, `explain --recipient <id> --since <t>`, `pending`, `retry <id>`, `purge`, `serve` | outbox, preferences |
| M-03 | ingestion | Transaction script: idempotência (R-03), **regras de ingresso** (`opt_out`, `duplicate`), registra o emissor, persiste notificação + entregas na MESMA transação (R-06) | `ingest(cmd, issuer, idempotencyKey) -> {notificationId, status, reason?}` | preferences, outbox, store |
| M-04 | delivery-policy | **Toda decisão da entrega**, como funções puras sobre estado: opt-out reavaliado, janela, teto, próxima tentativa e dead-letter | `decide(delivery, recipient, now) -> {send\|suppress(reason)\|defer(until)}`, `nextAttempt(attempts, now) -> at \| deadLetter` | preferences, quiet-hours, rate-limiter |
| M-05 | preferences | Pessoas, preferências **e o catálogo de categorias** (padrão, se é transacional, retenção) — o catálogo é do OPERADOR, não do emissor | `recipient(id)`, `category(name)`, `resolve(id, category, channel)`, `optOut(id, target, actor)`, `optIn(id, target, actor)` | store |
| M-06 | quiet-hours | Função pura: janela no fuso da pessoa, cruzamento de meia-noite (EDGE-1) e comportamento declarado em transição de horário de verão | `check(window, tz, now) -> {inWindow, opensAt?}` — `opensAt` é epoch ms | — |
| M-07 | rate-limiter | Token bucket global por pessoa, recarga contínua preguiçosa, saturada em zero se o relógio retroceder | `tryConsume(recipientId, now) -> {ok, retryAfter?, capApplied}` | store |
| M-08 | outbox | Fila durável **com lease**: reivindicação atômica com expiração, resultado, histórico e métricas | `enqueue(tx, deliveries)`, `claim(now, n, lease)`, `recordResult(id, outcome, nextAt?)`, `history(notificationId)`, `byRecipient(id, since)`, `stats()` | store |
| M-09 | delivery-worker | **Mecanismo puro**: reivindica lote, pergunta à política, envia com até N em voo, reporta resultado. Nenhuma regra de negócio | `tick(now) -> {claimed, sent, suppressed, deferred, failed}`, `start()` | outbox, delivery-policy, ChannelPort |
| M-10 | channel-email | Adaptador SMTP: template, URL base configurável, headers de unsubscribe one-click (PAR-17) | `send(msg) -> {accepted, permanent}` | — |
| M-11 | channel-webhook | Adaptador HTTP: assinatura HMAC (PAR-07/08, timestamp em **segundos**), guarda anti-SSRF, timeout PAR-10 | `send(msg) -> {accepted, permanent}` | — |
| M-12 | store | Adaptador SQLite: 6 tabelas, WAL + busy_timeout, transação, cifra dos segredos em repouso, poda por retenção | `withTransaction(fn)`, repositórios, `purge(olderThan)` | — |
| M-01 | http-api | Adaptador HTTP; decomposição interna declarada: rotas, autenticação, tradução de erros. Escopo da chave é `{categoria, permite_transacional}`; `/health` sem auth expõe só liveness, métricas exigem chave | `POST /notifications`, `GET /notifications/:id`, `GET\|PUT /recipients/:id/preferences`, `POST /unsubscribe`, `GET /health` | ingestion, preferences, outbox |
| M-02 | cli | Operador; `purge` é **dry-run por padrão**, exige `--yes` para executar | `explain <id>`, `explain --recipient <id> --since <t>`, `pending`, `retry <id>`, `purge [--yes]`, `serve` | outbox, preferences |
| M-03 | ingestion | Transaction script; idempotência **escopada por emissor** (índice único em `issuer + idempotency_key`) | `ingest(cmd, issuer, idempotencyKey) -> {notificationId, status, reason?}` | preferences, outbox, store |
| M-04 | delivery-policy | Decisão da entrega sobre um **contexto já materializado** — não faz I/O de preferências. A janela é função pura; o teto tem estado | `decide(ctx) -> {send\|suppress(reason)\|defer(until)}`, `nextAttempt(attempts, now) -> at \| deadLetter` | quiet-hours, rate-limiter |
| M-05 | preferences | Pessoas, preferências e catálogo de categorias. Alteração de categoria é **auditada** (`changed_by`) | `recipient(id)`, `category(name)`, `resolve(...)`, `optOut(...)`, `optIn(...)`, `setCategory(..., actor)` | store |
| M-06 | quiet-hours | Função pura; DST: hora inexistente abre no próximo instante válido, hora repetida usa a **primeira** ocorrência | `check(window, tz, now) -> {inWindow, opensAt?}` | — |
| M-07 | rate-limiter | Token bucket, recarga contínua, saturado em zero | `tryConsume(recipientId, now) -> {ok, retryAfter?, capApplied}` | store |
| M-08 | outbox | Fila durável com lease: **`claim` incrementa `attempts` no ato e devolve um fencing token**; lote limitado a PAR-19; `recordResult` exige o token e rejeita escrita tardia. Tempo vem do banco, não do processo | `enqueue(tx, deliveries)`, `claim(n<=PAR-19) -> [{delivery, token}]`, `recordResult(id, token, outcome, nextAt?)`, `history(...)`, `byRecipient(...)`, `stats()` | store |
| M-09 | delivery-worker | Mecanismo: monta o contexto (pessoa + categoria), pergunta à política, envia com **abort duro em PAR-10**, reporta. Dono do alarme de PAR-23 | `tick(now) -> {claimed, sent, suppressed, deferred, failed}`, `start()` | outbox, delivery-policy, preferences, ChannelPort |
| M-10 | channel-email | Adaptador SMTP; terminal é `sent` (submetido ao provedor) | `send(msg, signal) -> {accepted, permanent}` | — |
| M-11 | channel-webhook | Adaptador HTTP; **resolve o DNS uma vez, valida o IP e conecta naquele IP**; `redirect: manual` (3xx = falha permanente); terminal é `delivered` (2xx) | `send(msg, signal) -> {accepted, permanent}` | — |
| M-12 | store | SQLite; ciphertext **versionado** (`v1:nonce:ct`) com leitura pela chave anterior durante rotação; precedência de retenção declarada | `withTransaction(fn)`, repositórios, `purge(olderThan)` | — |

## Achados

| id | módulo | severidade | descrição |
|---|---|---|---|
| F-01 | rate-limiter | 🟡 | Teto global por pessoa compartilhado entre TODOS os emissores: um emissor barulhento consome a cota e cala os outros. Quem é prejudicado não é quem causou. |
| F-02 | channel-email | 🟡 | Os estados terminais passaram a diferir por canal (`sent` para e-mail submetido, `delivered` para webhook com 2xx), mas `specs/validation/acceptance-criteria.md` ainda descreve o comportamento de V(1): UC-1 fala em "2 entregas" sem distinguir. O artefato de aceitação ficou desatualizado em relação ao desenho. |
| F-03 | rate-limiter | 🟢 | A recarga usa `now - last_refill_at`; se o relógio retroceder (PRE-4 assume que não), `elapsed` negativo REDUZ tokens — a fórmula não satura em zero. |
| F-04 | ingestion | 🟢 | `payload_json` sem limite de tamanho declarado: emissor autenticado pode inflar o banco. |
| F-05 | cli | 🟢 | `explain` expõe o payload da notificação e não há noção de autorização — quem tem o arquivo SQLite lê tudo. |
| F-06 | delivery-policy | 🟡 | Não está definido se, após um envio falho, o worker chama `nextAttempt()` ou se `decide()` já devolve o próximo instante. Duas implementações corretas do contrato reprogramam de formas diferentes. |
| F-07 | delivery-worker | 🟡 | Nenhum contrato expõe métricas do laço (profundidade da fila, idade da entrega mais velha, taxa de dead-letter); `tick()` devolve contadores por chamada que ninguém agrega. |
| F-08 | delivery-worker | 🟡 | A relação entre o tamanho do lote de `claim(now, n, lease)` e PAR-19 = 8 em voo não está declarada. Se `n` > 8, as entregas excedentes esperam sua vez **com o lease correndo** — e podem perdê-lo antes de sequer serem tentadas (agrava RES-05). |
| F-09 | preferences | 🟡 | uma categoria marcada transacional que ignora opt-out conflita com a obrigação de honrar o descadastro (R-02, PAR-16). |
| F-10 | http-api | 🟡 | O POST devolve sucesso tanto para "aceitei e vou entregar" quanto para "aceitei e descartei por opt_out" — a distinção depende de o emissor ler um campo com atenção. |
| F-11 | preferences | 🟢 | A mesma tabela é escrita por três caminhos (pessoa via unsubscribe, operador, emissor via API) e nada registra a autoria da alteração. |
| F-12 | delivery-policy | 🟡 | V(2) ganhou sensor (stats + alarme) mas não ganhou atuador: detectada a fila crescente, nada no desenho reage — sem throttle de ingestão, sem priorização, sem degradação controlada. A malha continua aberta, agora instrumentada. |
| F-13 | outbox | 🟡 | O lease torna o multiprocesso seguro e, com isso, passa a assumir relógios sincronizados entre processos — premissa nova que PRE-4 (relógio não retrocede) não cobre. |
| F-14 | http-api | 🟢 | `GET /health` expõe profundidade de fila e idade da entrega mais velha sem autenticação declarada. |
| F-15 | channel-webhook | 🟢 | Assume `webhook_secret` presente sempre que há `webhook_url`; o modelo permite URL sem segredo (colunas nullable independentes). |
| F-16 | store | 🟡 | Retenção infinita em `notifications`, `deliveries`, `attempts` e `idempotency_keys`. Nenhum módulo é dono da poda; em 10× de escala o gargalo é o banco, não a CPU. |
| F-17 | store | 🟡 | M-12 implementa TODOS os repositórios (6 clientes) sem fronteira interna — candidato natural ao "arquivo de 800 linhas" na Fase 5. |
| F-18 | channel-webhook | 🟡 | Não está declarado se o adaptador segue redirecionamentos. Se seguir, um destino público responde 302 para `169.254.169.254` e o anti-SSRF de SEC-10 é contornado por desenho. |
| F-19 | outbox | 🟡 | `recordResult(id, outcome, nextAt?)` não define quem calcula `nextAt` (worker ou outbox). Se ambos assumirem que é o outro, entregas ficam sem reprogramação. |
| F-20 | store | 🟡 | Retenção é declarada em dois lugares: PAR-18 global (90 dias) e `categories.retention_days` por categoria. Nenhuma regra de precedência foi definida. |
| F-21 | channel-email | 🟢 | O link de unsubscribe exige URL base configurável que não aparece em nenhum contrato nem no modelo de dados. |
| F-22 | ingestion | 🟢 | A chave de dedup é escolhida pelo emissor (PRE-3): quem quiser burlar a dedup basta variá-la. A regra depende de cooperação. |
| F-23 | quiet-hours | 🟡 | Assume que todo dia local tem 1440 minutos. Em dias de transição de horário de verão o minuto de abertura (480) pode não existir ou existir duas vezes. |
| F-24 | store | 🟡 | `webhook_secret` armazenado em claro; `api_keys` guarda hash, o segredo HMAC não. |
| F-25 | delivery-worker | 🟡 | `suppressed` e `dead_letter` são terminais, mas `retry <id>` promete reprocessar: não há transição declarada de terminal de volta para `pending`. |
| F-26 | delivery-worker | 🟡 | O laço não gera sinal de erro nem realimenta: se a taxa de chegada exceder a de entrega (worker único), a fila cresce monotonamente sem que nada perceba ou reaja — sem throttle de ingestão, sem alarme. |
| F-27 | http-api | 🟡 | Token de unsubscribe declarado "de uso único", mas nem o modelo nem o contrato dizem onde o consumo é registrado — sem armazenamento, "uso único" é só assinatura, portanto reutilizável. |
| F-28 | http-api | 🔴 | PRE-8: qualquer emissor autenticado notifica QUALQUER pessoa em QUALQUER categoria, inclusive com `transactional: true`. Uma chave vazada é canal de spam com bypass de todas as supressões. |
| F-29 | delivery-worker | 🟢 | PAR-04 (5 tentativas) é desvio documentado de R-01 (~9 em 75 h), mas muda o resultado observável: destino fora do ar por 12 h que R-01 recuperaria vira dead-letter aqui. |
| F-30 | http-api | 🟢 | `status` reusa os nomes do estado de domínio; `accepted` no HTTP (202) e `accepted` no domínio (persistida) não coincidem necessariamente. |
| F-31 | channel-webhook | 🟡 | Sem circuit breaker por destino: um destino que devolve 500 para todos consome tentativas de todas as notificações dele, e o worker único paga o custo. |
| F-32 | rate-limiter | 🟢 | o incentivo de classificar como transacional para escapar do teto migrou do emissor para o operador. |
| F-33 | suppression | 🔴 | M-04 recebe `stage` e ramifica entre regras de ingest e de deliver: duas razões para mudar (SRP), e M-03/M-09 dependem de um módulo do qual usam metades disjuntas. Testar a cadeia de entrega exige montar o contexto de ingresso. |
| F-34 | delivery-policy | 🟡 | O módulo é descrito como "funções puras sobre estado", mas depende de `preferences` para reavaliar opt-out. Ou faz I/O (e não é puro), ou recebe o contexto montado — e aí não está declarado quem o monta. A contradição está no próprio contrato. |
| F-35 | channel-email | 🟡 | Falha de e-mail é assíncrona (bounce chega depois, por outro canal), mas `{ok, permanent}` só modela o resultado síncrono da submissão: um e-mail marcado `delivered` pode ter bouncado. |
| F-36 | channel-email | 🟡 | `{ok, permanent}` não define se `ok` é "submetido" ou "entregue"; duas implementações corretas do ChannelPort produzem semânticas incompatíveis de `delivered`. |
| F-37 | rate-limiter | 🟡 | Assume leitura-e-escrita atômica do bucket. Vale com M-12 + worker único, mas o contrato `tryConsume` não declara a exigência — trocar o repositório quebraria silenciosamente. |
| F-38 | suppression | 🟡 | `defer` devolve `until` sem definir se significa "não avaliar antes de" ou "entregar exatamente em" — implementações divergem na abertura da janela. |
| F-39 | quiet-hours | 🟢 | Todas as entregas adiadas de um mesmo fuso acordam no mesmo minuto (08:00): pico sincronizado, efeito manada. O retry tem jitter; a reprogramação por janela não tem. |
| F-40 | preferences | 🟡 | O catálogo tirou do emissor o poder de anular o consentimento da pessoa — e o entregou ao OPERADOR, sem trava. Marcar `marketing` como transacional faz o opt-out de todas as pessoas deixar de valer, silenciosamente. O poder foi movido, não removido. |
| F-41 | preferences | 🟡 | `preferences.changed_by` registra o ator da alteração de preferência, mas o catálogo de categorias — que agora decide o que ignora consentimento — não registra quem o alterou. A lacuna corrigida em GOV-03 reabriu ao lado. |
| F-42 | ingestion | 🔴 | `transactional` é auto-declarado pelo emissor e ignora opt-out, janela e teto. O incentivo de todo emissor é marcar tudo como transacional, e nada no design cria custo para isso: funciona apenas sob cooperação. |
| F-43 | store | 🟡 | RSK-01: a arquitetura confia que trocar `node:sqlite` por `better-sqlite3` é "troca de adaptador", mas as APIs diferem e não existe teste de contrato de repositório que garanta a equivalência. |
| F-44 | suppression | 🟢 | A regra `duplicate` consulta `notifications` por (recipient_id, dedup_key, created_at) a cada ingestão, sobre histórico que só cresce. |
| F-45 | suppression | 🟡 | `defer` é produzido por quiet_hours no estágio deliver, mas o contrato admite `defer` também no ingest e a arquitetura não diz o que M-03 faz com ele. |
| F-46 | preferences | 🟢 | O one-click unsubscribe (POST sem página) não dá retorno visual: a pessoa não sabe se funcionou. |
| F-47 | delivery-worker | 🟢 | O intervalo do laço `tick` não está especificado em nenhum PAR-xx: a precisão temporal de todo o sistema depende de um valor que não existe na spec. |
| F-48 | http-api | 🟡 | IMP-02 já duvidava dos "~40 LOC" de auth; V(2) acrescentou escopo por categoria, `/health`, métricas e token com validade. M-01 é agora o maior módulo da borda e continua sem decomposição interna declarada. |
| F-49 | channel-email | 🟢 | Nenhuma tolerância declarada a variação de servidor SMTP (auth, STARTTLS, limite de tamanho): funciona com o provider local, não necessariamente com um real. |
| F-50 | channel-webhook | 🟡 | A guarda anti-SSRF valida a URL no cadastro e antes do envio, mas o DNS pode reresolver entre a validação e a conexão — DNS rebinding contorna a guarda. |
| F-51 | preferences | 🟡 | PAR-16 exige efetivar opt-out em 48 h, mas o opt-out só é avaliado no estágio ingest: entregas já materializadas e adiadas pela madrugada são enviadas depois do descadastro. |
| F-52 | quiet-hours | 🟢 | O comportamento em DST foi declarado para a hora inexistente (abre no próximo instante válido), mas não para a hora REPETIDA no fim do horário de verão: a janela abre duas vezes? |
| F-53 | preferences | 🟡 | Invariante 3 ("ausência ≠ opt-out, resolve pelo padrão da categoria") assume um catálogo de categorias com padrão declarado. Nenhum módulo é dono desse catálogo; a tabela `preferences` não o modela. |
| F-54 | store | 🟢 | PAR-22 (WAL) pressupõe sistema de arquivos com locking adequado. O ambiente medido é WSL2 — em caminho montado do host ou em rede, WAL degrada ou falha. Tolerância não declarada. |
| F-55 | ingestion | 🔴 | O estado `deferred` da notificação não tem transição de saída com dono: a entrega volta a ser devida por `next_attempt_at`, mas nenhum módulo é declarado responsável por agregar o estado da notificação a partir das entregas. A coluna existe, o dono não. |
| F-56 | store | 🟢 | Sem id de correlação entre a requisição de ingestão e as tentativas de entrega — o log de um erro não aponta para o POST que o originou. |
| F-57 | http-api | 🟢 | As rotas de preferências são CRUD puro e não passam por script de domínio: validação de invariante tende a ficar no adaptador. |
| F-58 | outbox | 🟢 | O alarme de PAR-23 (idade da fila) não tem dono declarado: `outbox.stats()` produz o número, e não está dito se quem compara com o limiar é o worker, a API ou a CLI. |
| F-59 | outbox | 🔴 | **Poison message:** se o processamento lançar exceção ANTES de `recordResult`, o lease expira e a entrega volta a ser devida com `attempts` **inalterado** — ela nunca chega a PAR-04 e reprocessa para sempre. O caminho de dead-letter só é alcançado por falha reportada, não por falha não capturada. |
| F-60 | store | 🟢 | Dados pessoais (e-mail, fuso, histórico) sem política de retenção nem mecanismo de apagamento — nenhum módulo é dono de "esquecer uma pessoa". |
| F-61 | channel-webhook | 🟢 | PAR-08 exige `webhook-timestamp` em SEGUNDOS; o modelo de dados guarda tempo em epoch MILISSEGUNDOS, e `send(msg)` não declara a unidade. É o erro de fator 1000 que a tolerância de 300 s (PAR-06) transforma em rejeição de 100% das entregas. |
| F-62 | channel-webhook | 🟢 | PAR-10 (timeout 10 s) é POLÍTICA e interage com PAR-01 sem análise: 5 tentativas × 10 s = 50 s de bloqueio do worker único. |
| F-63 | cli | 🟡 | `purge` é comando destrutivo e foi acrescentado sem `--dry-run` nem confirmação declarada: o operador apaga histórico por engano e não há desfazer. |
| F-64 | channel-email | 🟡 | R-02 (RFC 8058) exige assinatura DKIM cobrindo `List-Unsubscribe` e `List-Unsubscribe-Post`. Nenhum módulo é dono de DKIM e o provider local não assina: requisito normativo sem rastreabilidade para módulo. |
| F-65 | channel-webhook | 🟡 | SSRF: a URL é fornecida pelo destinatário e o worker faz POST nela. Nada restringe destino a IPs públicos (169.254.169.254, localhost, rede interna). |
| F-66 | suppression | 🔴 | Uma notificação não-transacional que importa (ex.: aviso de vencimento) pode ser suprimida por `rate_limited` e desaparecer: sem recurso, sem aviso à pessoa, sem mecanismo de correção. Decisão automática de não informar alguém, sem reparação. |
| F-67 | store | 🟢 | `attempts_json` embutido na entrega retém o detalhe de erro de cada tentativa por PAR-18 = 90 dias: o volume por entrega cresce com o número de tentativas, não só com o número de entregas. |
| F-68 | store | 🟡 | A cifra AES-GCM não tem versionamento nem rotação de chave: trocar a chave de ambiente torna todos os `webhook_secret` ilegíveis, sem caminho de migração. |
| F-69 | rate-limiter | 🟢 | `tryConsume` é O(1), mas roda dentro do laço serial e é uma escrita no SQLite por entrega — amplia o custo por entrega. |
| F-70 | http-api | 🟡 | 5 rotas + API key + token assinado de unsubscribe + tradução erro→status. A estimativa de "~40 LOC" para auth foi feita na Fase 1 e não verificada. |
| F-71 | rate-limiter | 🟡 | PAR-12 (10/h) marcado POLÍTICA, sem fonte — honesto, mas alimenta um algoritmo cuja fonte (R-07) parametriza capacidade e refil, e não se declara se a janela é contínua ou hora fechada. |
| F-72 | preferences | 🟢 | O glossário diz que opt-out vale "até reativação explícita", mas a interface tem `optOut` e não tem o caminho de volta. |
| F-73 | preferences | 🟡 | M-05 passou a ter duas razões para mudar: preferências da PESSOA (dado do usuário) e catálogo de categorias (política do OPERADOR). É exatamente a violação de SRP que ARC-01 apontou em `suppression` — a correção reproduziu o padrão em outro módulo. |
| F-74 | suppression | 🟡 | quem sofre a consequência de classificar mal `transactional` é a pessoa, não o emissor que classificou. |
| F-75 | delivery-worker | 🔴 | Head-of-line blocking: worker único + timeout de 10 s por tentativa ⇒ drenagem O(N × 10 s). Notificação urgente de uma pessoa espera atrás de destinos lentos de outras. Nada na arquitetura mitiga. |
| F-76 | suppression | 🟡 | Registra-se o motivo da supressão, não a regra/valor vigente (teto era 10? janela era 22–08?). Mudou a política, o histórico fica ininterpretável. |
| F-77 | store | 🟡 | `SQLITE_BUSY` entre a thread da API e o laço do worker no mesmo processo não é tratado em nenhum contrato. |
| F-78 | ingestion | 🟡 | Assume que o conjunto de canais habilitados é conhecido no POST (entregas materializadas na transação). Se a pessoa habilitar webhook depois, a notificação já aceita nunca ganha essa entrega — comportamento não declarado. |
| F-79 | outbox | 🟡 | Entregas `delivered`/`dead_letter` permanecem na tabela para sempre (sem retenção), degradando `idx_due` indefinidamente. |
| F-80 | delivery-worker | 🔴 | PRE-6 assume "worker único" mas nada o IMPÕE: subir `serve` duas vezes faz `claimDue` reivindicar a mesma entrega nos dois processos → entrega duplicada. A premissa é assumida, não garantida. |
| F-81 | ingestion | 🟡 | Nenhuma coluna registra QUAL emissor criou a notificação. Com PRE-8, um post-mortem não consegue responder "quem mandou isto". |
| F-82 | http-api | 🟡 | O escopo da API key é por categoria, mas não distingue "pode emitir nesta categoria" de "pode emitir como transacional". Um emissor autorizado numa categoria transacional herda o bypass de supressão. |
| F-83 | delivery-worker | 🟢 | Destino permanentemente morto consome 5 tentativas com backoff até 24 h POR NOTIFICAÇÃO — custo cresce com o volume, não com o número de destinos mortos. |
| F-84 | quiet-hours | 🟡 | PAR-14 (22:00–08:00) é POLÍTICA; R-09 só afirma "modele no fuso da pessoa" e não fixa janela. |
| F-85 | http-api | 🟢 | Sem endpoint de saúde/prontidão: saber se o worker está vivo exige inspecionar o banco. |
| F-86 | quiet-hours | 🟢 | `opensAt` exige aritmética de calendário no fuso da pessoa e é sensível a DST; a assinatura não declara se `opensAt` é epoch ou hora local. |
| F-87 | ingestion | 🟡 | A chave de idempotência é global, não escopada por emissor: dois emissores usando a mesma `Idempotency-Key` colidem, e um recebe a resposta referente à notificação do outro. |
| F-88 | delivery-policy | 🟢 | PAR-25 (dispersão de 0–5 min na reabertura) é POLÍTICA e interage com a janela: numa janela curta, o jitter pode empurrar a entrega para fora dela. |
| F-89 | delivery-worker | 🔴 | Não há lease nem timeout de reivindicação: se `send` lançar exceção ou o processo morrer entre `claimDue` e `recordResult`, a entrega fica presa em estado reivindicado para sempre. É exatamente o cenário que AC-4 (matar o processo) exercita. |
| F-90 | delivery-policy | 🟡 | `defer(until)` e `nextAttempt()` escrevem o mesmo campo `next_attempt_at`. Para uma entrega que já falhou E entrou em janela de silêncio, qual valor prevalece não está declarado. |
| F-91 | cli | 🟢 | Não está declarado se `retry` ignora supressões; se não ignorar, o operador re-suprime e não entende por quê. |
| F-92 | cli | 🟡 | M-02 depende de `store` diretamente — fura o hexágono, porque `explain` precisa do histórico de `attempts`, que nenhum repositório de domínio expõe. |
| F-93 | store | 🟡 | 9 tabelas + schema + migração + transação + 6 repositórios num módulo: é o único que provavelmente NÃO cabe em uma interação (viola E = I₀/C). |
| F-94 | cli | 🟡 | `explain <id>` responde por notificação, mas a pergunta real do operador é "por que ESTA PESSOA não recebeu nada hoje?" — não há consulta por destinatário nem por período. |
| F-95 | delivery-worker | 🟡 | M-09 acumula laço + política de backoff + política de dead-letter. Não há costura para testar a política de retry sem rodar o laço. |
| F-96 | outbox | 🔴 | O lease dura PAR-20 = 60 s, mas nada garante que o envio termine dentro dele: um SMTP lento com PAR-10 = 10 s de timeout, mais fila interna de 8 em voo, pode ultrapassar 60 s. O lease expira, outro ciclo reivindica a MESMA entrega e o primeiro envio ainda está em voo → **entrega duplicada**. O lease curou a perda e criou a duplicação. |
