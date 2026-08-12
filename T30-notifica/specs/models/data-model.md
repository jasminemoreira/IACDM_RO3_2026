# Modelo de dados — T30 (V1)

Adaptador: SQLite (M-12). O núcleo nunca vê estas tabelas — fala com repositórios
(Repository + Data Mapper). Ids `PAR-xx` em `specs/technical/parameters.md`.

## Decisão de simplificação (KISS)

**A tabela `deliveries` É o outbox.** O padrão de R-06 exige que a mensagem a
enviar seja gravada na mesma transação que o estado de negócio; uma tabela
`outbox` separada, além de `deliveries`, duplicaria a mesma linha com o mesmo
ciclo de vida. `M-08 outbox` é o módulo que dá semântica de fila a essa tabela
(`claimDue`, `recordResult`), não uma tabela a mais.

## Tabelas

```sql
recipients(
  id            TEXT PRIMARY KEY,
  timezone      TEXT NOT NULL,          -- IANA, obrigatório (PRE-2 / EDGE-2)
  email         TEXT,
  webhook_url   TEXT,
  webhook_secret TEXT,                  -- segredo HMAC por destinatário (PAR-07)
  created_at    INTEGER NOT NULL
)

preferences(
  recipient_id  TEXT NOT NULL REFERENCES recipients(id),
  category      TEXT NOT NULL,          -- 'security' | 'billing' | 'marketing' | ...
  channel       TEXT NOT NULL,          -- 'email' | 'webhook' | '*' (canal todo)
  enabled       INTEGER NOT NULL,       -- 0 = opt-out explícito
  PRIMARY KEY (recipient_id, category, channel)
)                                        -- ausência ≠ opt-out (invariante 3)

quiet_windows(
  recipient_id  TEXT PRIMARY KEY REFERENCES recipients(id),
  start_minute  INTEGER NOT NULL,       -- minutos desde 00:00 local; padrão 1320 (22:00)
  end_minute    INTEGER NOT NULL        -- padrão 480 (08:00) — start > end = cruza meia-noite
)                                        -- PAR-14 / EDGE-1

notifications(
  id                TEXT PRIMARY KEY,
  recipient_id      TEXT NOT NULL REFERENCES recipients(id),
  category          TEXT NOT NULL,
  transactional     INTEGER NOT NULL DEFAULT 0,
  dedup_key         TEXT,               -- fornecida pelo emissor (PRE-3)
  payload_json      TEXT NOT NULL,
  status            TEXT NOT NULL,      -- accepted|deferred|delivered|partially_delivered|failed|suppressed
  suppressed_reason TEXT,               -- opt_out|quiet_hours|rate_limited|duplicate (enum fechado)
  created_at        INTEGER NOT NULL
)
CREATE INDEX idx_dedup ON notifications(recipient_id, dedup_key, created_at);
                                         -- janela de PAR-05 é consultada, não fixada no índice

deliveries(                              -- ESTA TABELA É O OUTBOX (R-06)
  id              TEXT PRIMARY KEY,
  notification_id TEXT NOT NULL REFERENCES notifications(id),
  channel         TEXT NOT NULL,        -- 'email' | 'webhook'
  status          TEXT NOT NULL,        -- pending|delivered|dead_letter|suppressed
  attempts        INTEGER NOT NULL DEFAULT 0,
  next_attempt_at INTEGER NOT NULL,     -- devida quando <= now; adiamento por quiet_hours grava aqui
  suppressed_reason TEXT,
  last_error      TEXT
)
CREATE INDEX idx_due ON deliveries(status, next_attempt_at);

attempts(                                -- histórico para UC-8
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  delivery_id TEXT NOT NULL REFERENCES deliveries(id),
  n           INTEGER NOT NULL,
  at          INTEGER NOT NULL,
  outcome     TEXT NOT NULL,            -- ok|transient|permanent
  detail      TEXT
)

idempotency_keys(                        -- R-03
  key             TEXT PRIMARY KEY,
  request_hash    TEXT NOT NULL,         -- mesma chave + corpo diferente = 422, não silêncio
  notification_id TEXT NOT NULL REFERENCES notifications(id),
  created_at      INTEGER NOT NULL
)

rate_buckets(                            -- token bucket, PAR-11/12
  recipient_id   TEXT PRIMARY KEY REFERENCES recipients(id),
  tokens         REAL NOT NULL,
  last_refill_at INTEGER NOT NULL
)

api_keys(
  key_hash   TEXT PRIMARY KEY,           -- nunca a chave em claro
  issuer     TEXT NOT NULL,
  created_at INTEGER NOT NULL
)
```

## V2 — 9 tabelas → 6 (Fase 3)

Resposta a ARC-05 🟡 e IMP-01 🟡 (`store` grande demais para uma interação) e a
PRO-01 🔴 (estado agregado sem dono).

| Antes (V1) | Agora (V2) | Motivo |
|---|---|---|
| `attempts` (tabela) | coluna `attempts_json` em `deliveries` | O histórico é sempre lido junto com a entrega; tabela separada só agregava junção |
| `idempotency_keys` (tabela) | colunas `idempotency_key` + `request_hash` em `notifications`, com índice único | Relação 1:1 com a notificação |
| `quiet_windows` (tabela) | colunas `quiet_start` / `quiet_end` em `recipients` | Relação 1:1 com a pessoa |
| `rate_buckets` (tabela) | colunas `tokens` / `last_refill_at` em `recipients` | Relação 1:1 com a pessoa |
| — | **nova** `categories` | Catálogo do OPERADOR: `name`, `default_enabled`, `transactional`, `retention_days`. Dá dono a ASS-05 e tira a auto-declaração do emissor (GAM-01) |
| `notifications.status` | **removida** | O estado passa a ser DERIVADO das entregas — sem coluna, não há dono a definir (PRO-01) |

**Tabelas em V2:** `recipients`, `categories`, `preferences`, `notifications`,
`deliveries`, `api_keys`.

Colunas acrescentadas por achado: `notifications.issuer` (GOV-01);
`deliveries.lease_until` (RES-01/ASS-01); `deliveries.suppressed_detail` com o
valor do parâmetro aplicado, ex. `rate_limited(cap=10/1h)` (GOV-02);
`recipients.webhook_secret` passa a guardar ciphertext AES-GCM (SEC-04);
`api_keys.categories` com o escopo da chave (SEC-01);
`preferences.changed_by` com o ator da alteração (GOV-03).

## Notas de modelagem

1. **`suppressed_reason` existe em dois níveis** — na notificação (suprimida no
   ingresso: `opt_out`, `duplicate`) e na entrega (suprimida na entrega:
   `quiet_hours` não suprime, adia; `rate_limited` suprime). É o que permite ao
   `explain` da CLI responder por canal (UC-8 / ambiguidade 3).
2. **Adiamento não é um estado novo:** janela de silêncio grava
   `next_attempt_at = opensAt` na entrega. O worker não precisa de agendador
   separado — a mesma consulta `idx_due` serve retry e adiamento.
3. **Tempo em INTEGER (epoch ms).** Fuso é propriedade da pessoa, nunca do
   armazenamento — a conversão acontece só em M-06.
4. `request_hash` em `idempotency_keys` distingue "reenvio idêntico" (devolve a
   mesma notificação) de "mesma chave, corpo diferente" (erro do cliente).
