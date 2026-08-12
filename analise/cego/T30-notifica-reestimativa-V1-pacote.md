# Tarefa — dizer quais lentes de crítica esta arquitetura aciona

Você recebe a decomposição arquitetural de um sistema. Diga **quais lentes de crítica
aquela arquitetura aciona**, e por qual sinal dela.

Não escreva código, não faça perguntas, não busque nada fora deste texto.

---

## O problema

> Serviço de notificação com preferências por pessoa, supressão e canais externos

## A arquitetura

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
| Resilience | What happens when an external dependency fails, responds slowly, or returns unexpected data? | External dependencies (APIs, DBs, queues, third-party services) |
| UI/UX | Can the user complete their task without frustration, confusion, or error? | Any surface a PERSON operates — including a CLI or operational tooling, not only graphical end-user interfaces |
| Migration / Coexistence | What breaks during the transition from old to new? Is there a rollback path? | Replacing or modifying existing production system |
| Sustainability / Proportionality | Is resource consumption proportionate to value delivered? Cost at 10\xD7 scale? | The system decides, allocates, or consumes a resource whose cost grows with use — e.g. (but NOT only) AI/ML, high-volume data processing, elastic infrastructure. Apply the central question, do not just match the examples |
| Ethical / Human Impact | Who is potentially harmed? Are there audit, correction, and transparency mechanisms? | Automated decisions about people (scoring, classification, moderation) |
| Process / Workflow | Are processes, state transitions, actor responsibilities, and exception paths complete? | Multi-actor flows, state machines, or business processes |
| Governance / Accountability | Is every action attributable? Does every data entity have a defined owner? | The system records or decides something someone will later need to audit, attribute, or answer for — data with distinct owners, actions that need authorship, or an obligation to account. This is a SYSTEM property: a single-operator project activates it when the system has it (not only multi-team / compliance contexts) |
| Observability / Operability | Can degradation be detected and incidents diagnosed in production without code changes? | Production systems with operational requirements |
| Control Engineering | Where does the system generate an error signal and correct it? Risk of oscillation or state drift? | State synchronization, runtime configuration affecting behavior, self-correcting or feedback-driven systems |
| Game Theory | Do system actors have aligned incentives? Where does the design assume cooperation and may encounter strategic defection? | Multiple independent actors, public API, external integrations, marketplace or platform design |
| Linguistics / Grammar | Is the interface contract unambiguous? Can two correct implementations of the same contract produce incompatible behaviors? | Inter-component communication, protocol definitions, message formats, interface contracts between independent teams |
| Mechanical Engineering | Where are the tolerances? Does the system tolerate variation or only work at exact specification? | Module maintenance, system evolution, long-lived systems with technical debt accumulation |

---

## O que responder

Para **cada uma das 12**: `ativa` (true/false) e `sinal` — uma frase curta dizendo **o
que na arquitetura** aciona, ou não aciona, a lente. Preencha o `sinal` também nas
`false`. E `modulos_estimados`: quantos módulos a arquitetura tem.

As 12 têm que aparecer, com o nome exato da tabela. Só o JSON, sem preâmbulo:

```json
{
  "projeto": "T30-notifica",
  "modulos_estimados": 0,
  "lentes": [{"lente": "Resilience", "ativa": true, "sinal": "..."}]
}
```
