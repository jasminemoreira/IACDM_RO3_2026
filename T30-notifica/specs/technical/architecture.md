# Arquitetura — T30

Padrão: **Hexagonal (Ports & Adapters)** · Princípios: **KISS+YAGNI, SOLID** ·
Concorrência: **worker único sobre o outbox** · GoF: **Adapter, Chain of
Responsibility** · Fowler: **Transaction Script** (domínio) + **Repository/Data
Mapper** (dados).

Ids `PAR-xx` → `specs/technical/parameters.md`. `R-xx` →
`specs/references/notification-references.md`. `UC-x`/`EDGE-x`/`AC-x` →
`specs/validation/acceptance-criteria.md`.

---

## V(1)

### Tabela de módulos

| id | module | responsibility | interface | depends-on |
|------|--------|----------------|-----------|------------|
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

**Contagem: 12 módulos** — dentro da faixa 8–12 do `ENUNCIADO.md`.

### Princípio de fronteira aplicado

Uma regra de supressão vira **módulo próprio quando carrega algoritmo
não-trivial**: `quiet-hours` (conversão de fuso + cruzamento de meia-noite) e
`rate-limiter` (token bucket com recarga) viram. `opt_out` (consulta de
preferência) e `duplicate` (índice + janela temporal) ficam dentro da cadeia
M-04, porque extrair um predicado de 5 linhas para um módulo é cerimônia sem
ganho de testabilidade — e KISS foi escolhido explicitamente.

### Porta de saída de canal (ChannelPort)

```
ChannelPort.send(msg: OutboundMessage) -> { ok: boolean, permanent: boolean }
```

O campo **`permanent`** é o ponto sensível do contrato: separa falha definitiva
(URL inválida, 4xx do destino, endereço inexistente ⇒ NÃO retentar) de falha
transitória (timeout, 5xx, conexão recusada ⇒ retentar com PAR-01). Sem ele,
EDGE-3 vira 5 tentativas inúteis contra um host que nunca existiu.
Implementada por M-10 e M-11, consumida somente por M-09.

### Pipeline de supressão (2 estágios — decisão da Fase 0)

```
estágio ingest   (em M-03):  opt_out  ->  duplicate
estágio deliver  (em M-09):  quiet_hours  ->  rate_limited
```

O teto é consumido na ENTREGA, não no POST, porque o teto protege a pessoa de
interrupção e quem interrompe é a entrega. Consequência aceita: 20 notificações
adiadas pela madrugada não viram 20 entregas às 08:00 — as excedentes são
suprimidas como `rate_limited` na abertura da janela.

Notificação **transacional** pula `opt_out`, `quiet_hours` e `rate_limited`;
**nunca** pula `duplicate` (invariante 2 do glossário / EDGE-7).

### Fluxo principal

```
POST /notifications (API key)
  -> M-01 valida
  -> M-03 idempotência (R-03) -> supressão[ingest] -> TRANSAÇÃO { notificação + entregas } (R-06)
  -> M-09 claimDue -> supressão[deliver] -> ChannelPort.send
       ok            -> delivered
       !ok & permanent -> dead_letter (sem retry)
       !ok & transitório -> nextAttemptAt = random(0, min(PAR-03, PAR-02 * 2^n)); n > PAR-04 -> dead_letter
```

Estado da Notificação **agrega** o estado das Entregas: `delivered` /
`partially_delivered` / `failed` / `suppressed(motivo)` / `deferred`.

### Premissas (Leveson — o que o sistema assume verdadeiro)

| id | Premissa | Por que é arriscada |
|----|----------|---------------------|
| PRE-1 | Worker único; SQLite não oferece `SELECT … FOR UPDATE SKIP LOCKED` (RSK-02) | Throughput limitado; um `tick` travado para todas as entregas |
| PRE-2 | Fuso é campo OBRIGATÓRIO da Pessoa, validado como IANA no cadastro (422 se ausente/inválido) — resolve EDGE-2 | Empurra o problema para a fronteira; cadastros antigos/importados não têm essa garantia |
| PRE-3 | A chave de dedup é fornecida pelo emissor; o serviço não a infere do conteúdo | Emissor que não manda chave perde dedup silenciosamente |
| PRE-4 | O relógio do servidor é confiável e não retrocede | PAR-06 (tolerância de 300 s) e o cálculo de janela dependem disso |
| PRE-5 | `node:sqlite` é experimental; isolado atrás de M-12 (RSK-01) | Mudança de API do runtime quebra M-12 |
| PRE-6 | API e worker no MESMO processo; todo estado de entrega vive no banco, nunca em memória | É o que AC-4 (durabilidade) exige provar |
| PRE-7 | O destino do webhook é idempotente do lado dele; nossa garantia é *at-least-once* | R-01 recomenda `webhook-id` como chave de idempotência no consumidor — mas nós não podemos garantir que ele faça isso |
| PRE-8 | A API key identifica um emissor confiável; não há autorização por recurso (qualquer emissor autenticado pode notificar qualquer pessoa) | Emissor comprometido = notificação em nome de qualquer um |

### Escopo negativo (o que o sistema deliberadamente NÃO faz)

Digest/batching (o excedente do teto é **suprimido**, nunca agrupado) · SMS e
push · página web de preferências · editor visual de fluxos/templates · feed
in-app · entrega paralela / múltiplos workers · autorização por recurso (só
autenticação de emissor, ver PRE-8) · e não reinventa algoritmo: backoff, token
bucket, outbox e assinatura são portes literais de fonte citada (Tier 2).

---

## V(2) — resposta unificada à Iteração 1 da crítica

Eixo da revisão: **política separada de mecanismo**. A Fase 2 mostrou
`delivery-worker` atingido por 10 das 18 lentes — sinal de módulo mal concebido.
Ele acumulava laço, backoff, dead-letter e reavaliação de regras. Em V(2) ele é
só mecanismo; toda decisão vive em `delivery-policy`.

### Tabela de módulos

| id | module | responsibility | interface | depends-on |
|------|--------|----------------|-----------|------------|
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

**12 módulos** (faixa 8–12 mantida). Removido: `suppression`. Adicionado:
`delivery-policy`.

### O que mudou e por quê (por id de achado)

| Mudança | Resolve |
|---|---|
| `suppression` deixa de existir: regras de ingresso vão para `ingestion`, regras de entrega para `delivery-policy` | ARC-01 🔴, PRO-03 🟡, LIN-02 🟡 |
| `outbox.claim` com **lease expirável** (reivindicação atômica; entrega volta à fila se o lease vencer) | RES-01 🔴, ASS-01 🔴 — o worker único deixa de ser premissa e passa a ser consequência do mecanismo |
| `delivery-worker` vira mecanismo; política sai para M-04, incluindo `nextAttempt` | ARC-02 🟡, LIN-03 🟡, PRO-02 🟡 |
| Até **PAR-19 = 8 envios em voo** num único laço (I/O concorrente, sem processo extra) | PERF-01 🔴 |
| `transactional` passa a vir do **catálogo de categorias** (operador), não do emissor; API key com escopo de categorias | GAM-01 🔴, SEC-01 🔴 (reduzido), ETH-02 🟡, ASS-05 🟡 |
| Motivo de supressão devolvido ao emissor; supressão consultável e reenviável pelo operador | ETH-01 🔴, UX-03 🟡 |
| Estado da notificação passa a ser **derivado** das entregas — a coluna some | PRO-01 🔴 (não há dono a definir porque não há estado duplicado) |
| `delivery-policy` reavalia **opt-out também na entrega** | REG-02 🟡 |
| 9 → **6 tabelas**: `attempts` vira JSON na entrega; idempotência, janela e bucket viram colunas | ARC-05 🟡, IMP-01 🟡 |
| Segredos cifrados em repouso (AES-GCM, chave de ambiente) | SEC-04 🟡 |
| Guarda anti-SSRF na URL de webhook (cadastro e envio) | SEC-03 🟡 |
| Token de unsubscribe: assinado, com escopo pessoa+categoria e validade (PAR-21). "Uso único" **abandonado** — descadastrar é idempotente, então o requisito era desnecessário | SEC-02 🟡 |
| `ChannelPort` devolve `{accepted, permanent}`; estado terminal é `sent` (e-mail, submetido) ou `delivered` (webhook, 2xx confirmado) | RES-02 🟡, LIN-01 🟡 |
| Poda por retenção com dono declarado (`store.purge`, `cli purge`, PAR-18) | SUS-01 🟡, PERF-02 🟡, REG-03 🟢 |
| `outbox.stats()` + `GET /health` + alarme de idade da fila (PAR-23) | OBS-01 🟡, OBS-02 🟢, CTL-01 🟡 |
| `outbox.history` e `byRecipient` — a CLI não fala mais com `store` | ARC-03 🟡, UX-01 🟡 |
| Supressão grava o **valor do parâmetro aplicado** (`rate_limited(cap=10/1h)`) e a notificação grava o `issuer` | GOV-02 🟡, GOV-01 🟡 |
| WAL + `busy_timeout` (PAR-22) | RES-04 🟡 |
| Unidades declaradas no contrato: `webhook-timestamp` em segundos, tudo mais em epoch ms | LIN-05 🟢 |
| Jitter na reabertura da janela (PAR-25), saturação em zero no bucket (CTL-02), intervalo do tick (PAR-24), teto de payload (PAR-26), DST declarado, `optIn` na interface | CTL-03 🟢, CTL-02 🟢, MEC-03 🟢, SEC-06 🟢, ASS-03 🟡, PRO-04 🟢 |

### Riscos aceitos com justificativa (não resolvidos por decisão)

| id | Por que fica |
|---|---|
| SEC-01 🟡 (residual) | Emissor autorizado ainda pode notificar qualquer pessoa. Autorização por recurso continua fora de escopo (Fase 0); o vetor de bypass de supressão foi fechado |
| REG-01 🟡 | DKIM é responsabilidade do provedor de e-mail, não do serviço. `channel-email` emite os headers exigidos por R-02; a assinatura é configuração do provedor real |
| RES-03 🟡 | Circuit breaker por destino: com PAR-19 envios em voo e Full Jitter, um destino morto não bloqueia mais a fila. Adicionar estado de breaker seria complexidade sem ganho no porte alvo (AP2) |
| GAM-02 🟡 | Teto global por pessoa foi decisão explícita da Fase 0; mudá-lo para por-emissor alteraria semântica acordada com o operador |
| ASS-02 🟡 | Materializar entregas no POST é a semântica oficial e agora está declarada: habilitar um canal depois não alcança notificação já aceita |
| SEC-05, SUS-02, MEC-02, GAM-03, UX-04 🟢 | Adiados para v2.0 com registro |

### Premissas revisadas

PRE-1 **reescrita**: não se assume worker único — o lease torna a reivindicação
segura mesmo com mais de um processo, e o paralelismo em voo é intra-laço e
limitado por PAR-19. PRE-4 (relógio) permanece, mas o bucket agora satura em
zero e a assinatura declara a unidade. PRE-8 **reduzida**: a API key tem escopo
de categorias; a ausência de autorização por recurso permanece declarada.
PRE-2, PRE-3, PRE-5, PRE-6, PRE-7 inalteradas.

---

## V(3) — resposta à Iteração 2 da crítica

**Nenhum módulo adicionado ou removido.** Os 12 de V(2) permanecem com os mesmos
nomes. As correções são de contrato e de semântica — os dois críticos vinham da
própria correção anterior, e a resposta é fechar as duas janelas que o lease
abriu, não trocar o mecanismo.

### Tabela de módulos

| id | module | responsibility | interface | depends-on |
|------|--------|----------------|-----------|------------|
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

### O que mudou (por id de achado)

| Mudança | Resolve |
|---|---|
| `claim` limita o lote a PAR-19 (nada espera com lease correndo) + envio abortado em PAR-10 (posse ≈ 10 s ≪ lease de 60 s) + fencing token rejeita escrita tardia | RES-05 🔴, PERF-05 🟡 |
| `claim` **incrementa `attempts` no ato da reivindicação**, não no resultado: falha não capturada consome tentativa e a entrega alcança PAR-04 → dead-letter. Trade-off declarado: um crash "gasta" uma tentativa | RES-06 🔴 |
| O worker monta o contexto; `delivery-policy` não depende mais de `preferences`, e a alegação de "funções puras" é corrigida (janela é pura, teto tem estado) | ARC-06 🟡 |
| Tempo do lease vem de `unixepoch()` **do banco**, não do processo — a premissa de relógios sincronizados desaparece | ASS-07 🟡 |
| `decide()` devolve o veredito; `nextAttempt()` é chamado pelo worker **somente** quando o envio falha | LIN-06 🟡 |
| Precedência declarada: `next_attempt_at = max(nextAttempt, deferUntil)` | PRO-05 🟡 |
| Precedência declarada: `categories.retention_days` sobrepõe PAR-18, que é o padrão | ARC-08 🟡 |
| Escopo da chave passa a ser `{categoria, permite_transacional}` | SEC-07 🟡 |
| Idempotência escopada por emissor | SEC-08 🟡 |
| Ciphertext versionado + leitura pela chave anterior | SEC-09 🟡 |
| DNS resolvido uma vez, IP validado e fixado na conexão | SEC-10 🟡 |
| `redirect: manual` — 3xx é falha permanente | SEC-11 🟡 |
| `/health` sem auth só responde liveness; métricas exigem chave | SEC-12 🟢 |
| `categories.changed_by` + histórico; CLI lista categorias que ignoram consentimento | GOV-04 🟡, ETH-03 🟡 (mitigado) |
| `specs/validation/acceptance-criteria.md` atualizado para os estados por canal | PRO-07 🟡 |
| Decomposição interna de `http-api` declarada (rotas / auth / erros) | IMP-05 🟡 |
| `purge` dry-run por padrão | UX-06 🟡 |
| DST na hora repetida; jitter limitado a `min(PAR-25, 10% da janela)`; dono do alarme = worker; `attempts_json` guarda no máximo PAR-04 entradas com detalhe truncado; WAL com fallback declarado se o sistema de arquivos não suportar | ASS-08, SCI-05, OBS-04, SUS-03, MEC-04 🟢 |

### Riscos aceitos nesta rodada

| id | Por que fica |
|---|---|
| ARC-07 🟡 | `preferences` continua dona das preferências da pessoa **e** do catálogo. Separar exigiria um 13º módulo (fora da faixa 8–12 do enunciado) ou absorver `quiet-hours` só para abrir vaga — churn estrutural maior que o defeito. Justificativa de coesão: o catálogo é a **camada de padrão** da mesma política ("quem recebe o quê"), e o poder que ele confere agora é auditado (GOV-04) e visível na CLI |
| ETH-03 🟡 (residual) | O operador pode, por desenho, marcar uma categoria como transacional e com isso anular opt-out. É ele quem responde pelo sistema; a lente exige auditoria, correção e transparência — os três foram adicionados. Remover o poder mudaria UC-7, que é escopo do operador, não meu |
| GAM-04 🟢, REG-04 🟡 | duplicatas de ETH-03 |
