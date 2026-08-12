# Tabela-verdade da supressão — ground truth dos testes

Prometida no Production Capacity Check da Fase 0. É contra ESTA tabela que os
testes verificam, não contra o comportamento observado da implementação.

Legenda: `—` = regra não se aplica · `✔` = a regra deixa passar · `✘` = a regra
suprime ou adia.

## Estágio de INGRESSO (M-03 ingestion)

| # | transacional? | canal habilitado? | dedup na janela? | resultado esperado | motivo |
|---|---|---|---|---|---|
| I-1 | não | sim | não | `accepted`, entregas materializadas | — |
| I-2 | não | **nenhum** | não | `suppressed` | `opt_out` |
| I-3 | não | sim | **sim** | `suppressed` | `duplicate` |
| I-4 | **sim** | **nenhum** | não | `accepted` — transacional ignora opt-out | — |
| I-5 | **sim** | qualquer | **sim** | `suppressed` — transacional **nunca** ignora dedup | `duplicate` (EDGE-7) |
| I-6 | não | sim | não, mas mesma `Idempotency-Key` e mesmo corpo | mesma notificação, `replayed` | — |
| I-7 | não | sim | mesma `Idempotency-Key`, corpo **diferente** | erro 422 | `idempotency_conflict` |
| I-8 | não | sim | mesma chave de idempotência, **emissor diferente** | duas notificações distintas | — (EDGE-13) |

## Estágio de ENTREGA (M-04 delivery-policy)

| # | transacional? | opt-out desde o ingresso? | em janela de silêncio? | tokens ≥ 1? | resultado | motivo |
|---|---|---|---|---|---|---|
| D-1 | não | não | não | sim | `send` | — |
| D-2 | não | **sim** | — | — | `suppress` | `opt_out` (REG-02) |
| D-3 | não | não | **sim** | — | `defer` até a abertura + jitter | `quiet_hours` |
| D-4 | não | não | não | **não** | `suppress` | `rate_limited(cap=10/1h)` |
| D-5 | **sim** | sim | sim | não | `send` — ignora as três | — |

## Resultado do envio (M-09 delivery-worker)

| # | resposta do canal | próximo estado | reprograma? |
|---|---|---|---|
| S-1 | aceito | `sent` (e-mail) / `delivered` (webhook) | não |
| S-2 | falha **permanente** (URL inválida, 4xx, 3xx) | `dead_letter` | não — EDGE-3 |
| S-3 | falha **transitória** (timeout, 5xx, conexão recusada) e `attempts` < 5 | `pending` | sim, Full Jitter |
| S-4 | falha transitória e `attempts` ≥ 5 | `dead_letter` | não |
| S-5 | exceção não capturada / processo morto | volta a `pending` ao expirar o lease, com `attempts` **já incrementado** | sim — EDGE-9 |

## Janela de silêncio (M-06 quiet-hours) — casos de fronteira

| # | janela | hora local | em janela? |
|---|---|---|---|
| Q-1 | 1320→480 (22:00–08:00, cruza) | 23:30 | ✘ sim |
| Q-2 | 1320→480 | 03:00 | ✘ sim |
| Q-3 | 1320→480 | 12:00 | ✔ não |
| Q-4 | 1320→480 | 08:00 exato | ✔ não — fim é exclusivo |
| Q-5 | 1320→480 | 22:00 exato | ✘ sim — início é inclusivo |
| Q-6 | 60→300 (01:00–05:00, normal) | 02:00 | ✘ sim |
| Q-7 | 60→300 | 23:00 | ✔ não |
| Q-8 | 0→0 (desligada) | qualquer | ✔ não |
