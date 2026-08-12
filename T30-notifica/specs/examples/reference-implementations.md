# Implementações de referência (S6 Tier 2 — portar, não inventar)

Cada bloco abaixo é o algoritmo **como a fonte o define**. Na Fase 5 o código
deve seguir esta estrutura e estes nomes, e citar o `PAR-xx` correspondente.
Divergir da fonte é permitido — desde que registrado, como em PAR-04.

---

## 1. Backoff Full Jitter — PAR-01/02/03 (fonte: R-05)

Fórmula literal do artigo:

```
sleep = random(0, min(cap, base * 2 ** attempt))
```

Alternativas descartadas, também do artigo (para não serem re-descobertas):

```
Equal Jitter:        sleep = base/2 + random(0, base/2 * 2 ** attempt)
Decorrelated Jitter: sleep = min(cap, random(base, sleep * 3))
```

Escolha: **Full Jitter** — menor trabalho total e menor carga no destino.
`base` = 5 s (PAR-02), `cap` = 24 h (PAR-03), máx. 5 tentativas (PAR-04, desvio
consciente do cronograma de ~9 de R-01).

> Cuidado de implementação: `attempt` começa em 0 na primeira retentativa. Com
> `attempt` já incrementado, a primeira espera vira 10 s em vez de 5 s.

---

## 2. Assinatura de webhook — PAR-07/08 (fonte: R-01, Standard Webhooks)

Headers obrigatórios na requisição de saída:

```
webhook-id:        <identificador único da mensagem>
webhook-timestamp: <unix timestamp INTEIRO, em SEGUNDOS>
webhook-signature: v1,<base64>
```

Conteúdo assinado — concatenação com ponto, **nesta ordem**:

```
{webhook-id}.{webhook-timestamp}.{payload}
```

Exemplo literal da spec:

```
msg_2KWPBgLlAfxdpx2AI54pPJ85f4W.1674087231.{"type":"contact.created"...}
```

Algoritmo: HMAC-SHA256 com o segredo do destinatário, saída em Base64, prefixada
por `v1,`. O header aceita **lista separada por espaço** (rotação de segredo).

Do lado do recebimento (nosso receptor local de teste faz isso, e é o que
esperamos do destino real):
- rejeitar se `|now - webhook-timestamp| > 300 s` (PAR-06) — proteção contra replay;
- usar `webhook-id` como chave de idempotência, retido ~5 min (PAR-05);
- **a cada retentativa o timestamp é NOVO**; o id da mensagem permanece o mesmo.

Sucesso = HTTP 2xx (200–299). Qualquer outra coisa é falha (PAR-09).

---

## 3. Token bucket — PAR-11/12 (fonte: R-07)

Recarga preguiçosa (não há timer; calcula-se no acesso):

```
elapsed  = now - last_refill_at
tokens   = min(capacity, tokens + elapsed * (capacity / window))
if tokens >= 1:  tokens -= 1        -> permitido
else:            retryAfter = (1 - tokens) * (window / capacity)  -> negado
last_refill_at = now
```

`capacity` = 10, `window` = 1 h (PAR-12), escopo **global por pessoa**.

Descartado: GCRA. Motivo registrado — em GCRA "quantos tokens restam?" não é
pergunta direta (deriva-se do TAT), e a CLI do UC-8 precisa responder isso.

---

## 4. Janela de silêncio com cruzamento de meia-noite — PAR-14 / EDGE-1

O erro clássico é escrever `start <= m && m < end`, que é **sempre falso** quando
a janela cruza a meia-noite (22:00 → 08:00, ou seja `1320 → 480`).

```
minuteOfDay = hora_local * 60 + minuto_local        // via Intl, no fuso da PESSOA
inWindow = (start <= end)
             ? (minuteOfDay >= start && minuteOfDay < end)   // janela normal
             : (minuteOfDay >= start || minuteOfDay < end)   // cruza a meia-noite
```

Obtenção da hora local sem biblioteca de datas (verificado funcionando no
ambiente, ver `specs/technical/feasibility.md`):

```js
const p = new Intl.DateTimeFormat('en-GB', {
  timeZone: tz, hour: '2-digit', minute: '2-digit', hour12: false
}).formatToParts(now);
```

`opensAt` = o próximo instante em que `minuteOfDay === end` no fuso da pessoa —
atenção a dias com transição de horário de verão, em que o dia local não tem
1440 minutos.

---

## 5. Transactional Outbox — (fonte: R-06)

O ponto do padrão, e a única coisa que precisa estar certa:

```
BEGIN
  INSERT INTO notifications (...)
  INSERT INTO deliveries    (...)   -- uma por canal habilitado
COMMIT
-- só então o worker enxerga as entregas
```

Nunca gravar a notificação e enfileirar a entrega em transações distintas: é
exatamente a falha que o padrão existe para evitar. A garantia resultante é
*at-least-once*; `duplicate` (PAR-05) e a chave de idempotência (R-03) é que
tornam o efeito observável *exactly-once*.
