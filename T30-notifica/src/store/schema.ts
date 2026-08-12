/**
 * M-12 store — schema.
 *
 * 6 tabelas. V(1) tinha 9: `attempts`, `idempotency_keys`, `quiet_windows` e
 * `rate_buckets` viraram colunas (achados ARC-05 / IMP-01), e a coluna de estado
 * agregado da notificação foi REMOVIDA — o estado é derivado das entregas
 * (achado PRO-01).
 *
 * A tabela `deliveries` É o outbox (R-06): notificação e entregas são gravadas
 * na mesma transação, e M-08 dá a ela semântica de fila.
 */
export const SCHEMA = `
CREATE TABLE IF NOT EXISTS recipients (
  id                  TEXT PRIMARY KEY,
  timezone            TEXT    NOT NULL,             -- IANA, obrigatório (PRE-2)
  email               TEXT,
  webhook_url         TEXT,
  webhook_secret_enc  TEXT,                         -- ciphertext versionado (SEC-04/SEC-09)
  quiet_start         INTEGER NOT NULL,             -- minutos desde 00:00 local (PAR-14)
  quiet_end           INTEGER NOT NULL,
  tokens              REAL    NOT NULL,             -- token bucket (PAR-11/12)
  last_refill_at      INTEGER NOT NULL,
  created_at          INTEGER NOT NULL
);

-- Catálogo do OPERADOR. Tira do emissor o poder de declarar transacional (GAM-01).
CREATE TABLE IF NOT EXISTS categories (
  name            TEXT PRIMARY KEY,
  default_enabled INTEGER NOT NULL,
  transactional   INTEGER NOT NULL,
  retention_days  INTEGER,                          -- sobrepõe PAR-18 (ARC-08)
  changed_by      TEXT    NOT NULL,                 -- auditoria (GOV-04)
  changed_at      INTEGER NOT NULL
);

-- Ausência de linha ≠ opt-out: resolve pelo padrão da categoria (invariante 3).
CREATE TABLE IF NOT EXISTS preferences (
  recipient_id TEXT    NOT NULL REFERENCES recipients(id),
  category     TEXT    NOT NULL,
  channel      TEXT    NOT NULL,                    -- 'email' | 'webhook' | '*'
  enabled      INTEGER NOT NULL,
  changed_by   TEXT    NOT NULL,                    -- autoria da alteração (GOV-03)
  changed_at   INTEGER NOT NULL,
  PRIMARY KEY (recipient_id, category, channel)
);

CREATE TABLE IF NOT EXISTS notifications (
  id                TEXT PRIMARY KEY,
  recipient_id      TEXT    NOT NULL REFERENCES recipients(id),
  category          TEXT    NOT NULL,
  transactional     INTEGER NOT NULL,               -- copiado do catálogo no ingresso
  dedup_key         TEXT,                           -- fornecida pelo emissor (PRE-3)
  payload_json      TEXT    NOT NULL,
  issuer            TEXT    NOT NULL,               -- quem mandou isto (GOV-01)
  idempotency_key   TEXT,
  request_hash      TEXT,
  suppressed_reason TEXT,                           -- opt_out | duplicate (estágio ingresso)
  created_at        INTEGER NOT NULL
);

-- Idempotência ESCOPADA POR EMISSOR: dois emissores com a mesma chave não
-- colidem (achado SEC-08).
CREATE UNIQUE INDEX IF NOT EXISTS idx_idem
  ON notifications(issuer, idempotency_key)
  WHERE idempotency_key IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_dedup
  ON notifications(recipient_id, dedup_key, created_at);

CREATE TABLE IF NOT EXISTS deliveries (
  id                TEXT PRIMARY KEY,
  notification_id   TEXT    NOT NULL REFERENCES notifications(id),
  channel           TEXT    NOT NULL,
  status            TEXT    NOT NULL,
  attempts          INTEGER NOT NULL DEFAULT 0,
  next_attempt_at   INTEGER NOT NULL,
  lease_until       INTEGER,
  lease_token       TEXT,                           -- fencing token (RES-05)
  suppressed_reason TEXT,
  suppressed_detail TEXT,                           -- valor vigente do parâmetro (GOV-02)
  attempt_log_json  TEXT    NOT NULL DEFAULT '[]'
);

CREATE INDEX IF NOT EXISTS idx_due ON deliveries(status, next_attempt_at);

CREATE TABLE IF NOT EXISTS api_keys (
  key_hash            TEXT PRIMARY KEY,             -- nunca a chave em claro
  issuer              TEXT    NOT NULL,
  categories_json     TEXT    NOT NULL,             -- escopo por categoria (SEC-01)
  allow_transactional INTEGER NOT NULL,             -- separado de "pode emitir" (SEC-07)
  created_at          INTEGER NOT NULL
);
`;
