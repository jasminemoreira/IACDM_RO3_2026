/**
 * M-12 store — adaptador SQLite.
 *
 * Interface: withTransaction(fn), repositórios por agregado, purge(olderThan).
 * O núcleo (M-03..M-09) nunca vê SQL: fala com estes repositórios.
 *
 * PAR-22: WAL + busy_timeout de 5000 ms (achado RES-04). Achado MEC-04: WAL
 * pressupõe um sistema de arquivos com locking adequado — em caminho montado do
 * host sob WSL2 ou em rede, ele falha; por isso a ativação é tolerante e cai
 * para o journal padrão em vez de derrubar o processo.
 *
 * O TEMPO vem do banco (`unixepoch()`), não do processo: isso elimina a premissa
 * de relógios sincronizados que o lease introduziu (achado ASS-07).
 */
import { DatabaseSync } from 'node:sqlite';
import type {
  AttemptRecord,
  Category,
  Channel,
  Delivery,
  DeliveryStatus,
  Notification,
  Recipient,
  SuppressionReason,
} from '../types.ts';
import { SCHEMA } from './schema.ts';
import { createSecretBox, type SecretBox } from './crypto.ts';

/** PAR-22 — busy_timeout em milissegundos. */
export const PAR_22_BUSY_TIMEOUT_MS = 5000;
/** PAR-18 — retenção padrão, em dias. Sobreposta por categories.retention_days (ARC-08). */
export const PAR_18_RETENTION_DAYS = 90;

type Row = Record<string, any>;

export interface ApiKeyRecord {
  issuer: string;
  categories: string[];
  allowTransactional: boolean;
}

export interface Store {
  readonly db: DatabaseSync;
  /** Relógio do BANCO, em epoch ms — fonte única de tempo do sistema (ASS-07). */
  now(): number;
  withTransaction<T>(fn: () => T): T;
  recipients: RecipientRepo;
  categories: CategoryRepo;
  preferences: PreferenceRepo;
  notifications: NotificationRepo;
  deliveries: DeliveryRepo;
  apiKeys: ApiKeyRepo;
  /** Poda por retenção; devolve o que apagaria/apagou (dryRun = padrão da CLI). */
  purge(now: number, dryRun: boolean): { notifications: number; deliveries: number };
  close(): void;
}

export interface RecipientRepo {
  get(id: string): Recipient | null;
  put(r: Omit<Recipient, 'webhookSecret'> & { webhookSecret: string | null }, now: number): void;
  updateBucket(id: string, tokens: number, at: number): void;
}

export interface CategoryRepo {
  get(name: string): Category | null;
  list(): Category[];
  put(c: Omit<Category, 'changedAt'>, now: number): void;
}

export interface PreferenceRepo {
  get(recipientId: string, category: string, channel: string): boolean | null;
  put(recipientId: string, category: string, channel: string, enabled: boolean, actor: string, now: number): void;
  listFor(recipientId: string): Array<{ category: string; channel: string; enabled: boolean; changedBy: string }>;
}

export interface NotificationRepo {
  insert(n: Notification, idempotencyKey: string | null, requestHash: string | null): void;
  get(id: string): Notification | null;
  findByIdempotency(issuer: string, key: string): { notification: Notification; requestHash: string | null } | null;
  findDuplicate(recipientId: string, dedupKey: string, since: number): Notification | null;
  markSuppressed(id: string, reason: SuppressionReason): void;
  listByRecipient(recipientId: string, since: number): Notification[];
}

export interface DeliveryRepo {
  insert(d: Delivery): void;
  get(id: string): Delivery | null;
  listByNotification(notificationId: string): Delivery[];
  /** Reivindicação atômica com lease e fencing token — ver M-08. */
  claimDue(now: number, limit: number, leaseMs: number, token: string): Delivery[];
  /** Só grava se o fencing token ainda for o vigente (RES-05). */
  recordResult(
    id: string,
    token: string,
    patch: {
      status: DeliveryStatus;
      nextAttemptAt?: number;
      suppressedReason?: SuppressionReason | null;
      suppressedDetail?: string | null;
      attempt?: AttemptRecord;
    },
  ): boolean;
  reopen(id: string, now: number): boolean;
  stats(now: number): { pending: number; oldestAgeMs: number; deadLetter: number; sent: number; suppressed: number };
  listPending(now: number, limit: number): Delivery[];
}

export interface ApiKeyRepo {
  find(keyHash: string): ApiKeyRecord | null;
  put(keyHash: string, rec: ApiKeyRecord, now: number): void;
}

function toRecipient(row: Row, box: SecretBox): Recipient {
  return {
    id: row.id,
    timezone: row.timezone,
    email: row.email,
    webhookUrl: row.webhook_url,
    webhookSecret: row.webhook_secret_enc ? box.decrypt(row.webhook_secret_enc) : null,
    quietStart: row.quiet_start,
    quietEnd: row.quiet_end,
    tokens: row.tokens,
    lastRefillAt: row.last_refill_at,
  };
}

function toCategory(row: Row): Category {
  return {
    name: row.name,
    defaultEnabled: row.default_enabled === 1,
    transactional: row.transactional === 1,
    retentionDays: row.retention_days,
    changedBy: row.changed_by,
    changedAt: row.changed_at,
  };
}

function toNotification(row: Row): Notification {
  return {
    id: row.id,
    recipientId: row.recipient_id,
    category: row.category,
    transactional: row.transactional === 1,
    dedupKey: row.dedup_key,
    payload: JSON.parse(row.payload_json),
    issuer: row.issuer,
    suppressedReason: row.suppressed_reason,
    createdAt: row.created_at,
  };
}

function toDelivery(row: Row): Delivery {
  return {
    id: row.id,
    notificationId: row.notification_id,
    channel: row.channel as Channel,
    status: row.status as DeliveryStatus,
    attempts: row.attempts,
    nextAttemptAt: row.next_attempt_at,
    leaseUntil: row.lease_until,
    leaseToken: row.lease_token,
    suppressedReason: row.suppressed_reason,
    suppressedDetail: row.suppressed_detail,
    attemptLog: JSON.parse(row.attempt_log_json),
  };
}

export function openStore(path: string, opts: { secretKey?: string; previousSecretKey?: string } = {}): Store {
  const db = new DatabaseSync(path);
  const box = createSecretBox(
    opts.secretKey ?? process.env.T30_SECRET_KEY ?? 'chave-de-desenvolvimento-t30',
    opts.previousSecretKey ?? process.env.T30_SECRET_KEY_PREVIOUS,
  );

  db.exec(`PRAGMA busy_timeout = ${PAR_22_BUSY_TIMEOUT_MS}`);
  try {
    db.exec('PRAGMA journal_mode = WAL'); // PAR-22
  } catch {
    // MEC-04: sistema de arquivos sem locking adequado (WSL2 em caminho montado,
    // rede). Segue no journal padrão — degrada concorrência, não corretude.
  }
  db.exec('PRAGMA foreign_keys = ON');
  db.exec(SCHEMA);

  const nowStmt = db.prepare(`SELECT CAST(unixepoch('subsec') * 1000 AS INTEGER) AS ms`);
  const now = () => (nowStmt.get() as Row).ms as number;

  let depth = 0;
  function withTransaction<T>(fn: () => T): T {
    if (depth > 0) return fn(); // transações aninhadas participam da externa
    db.exec('BEGIN IMMEDIATE');
    depth++;
    try {
      const out = fn();
      db.exec('COMMIT');
      return out;
    } catch (err) {
      db.exec('ROLLBACK');
      throw err;
    } finally {
      depth--;
    }
  }

  const recipients: RecipientRepo = {
    get(id) {
      const row = db.prepare('SELECT * FROM recipients WHERE id = ?').get(id) as Row | undefined;
      return row ? toRecipient(row, box) : null;
    },
    put(r, at) {
      db.prepare(
        `INSERT INTO recipients (id, timezone, email, webhook_url, webhook_secret_enc,
                                 quiet_start, quiet_end, tokens, last_refill_at, created_at)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
         ON CONFLICT(id) DO UPDATE SET
           timezone = excluded.timezone, email = excluded.email,
           webhook_url = excluded.webhook_url, webhook_secret_enc = excluded.webhook_secret_enc,
           quiet_start = excluded.quiet_start, quiet_end = excluded.quiet_end`,
      ).run(
        r.id,
        r.timezone,
        r.email,
        r.webhookUrl,
        r.webhookSecret ? box.encrypt(r.webhookSecret) : null,
        r.quietStart,
        r.quietEnd,
        r.tokens,
        r.lastRefillAt,
        at,
      );
    },
    updateBucket(id, tokens, at) {
      db.prepare('UPDATE recipients SET tokens = ?, last_refill_at = ? WHERE id = ?').run(tokens, at, id);
    },
  };

  const categories: CategoryRepo = {
    get(name) {
      const row = db.prepare('SELECT * FROM categories WHERE name = ?').get(name) as Row | undefined;
      return row ? toCategory(row) : null;
    },
    list() {
      return (db.prepare('SELECT * FROM categories ORDER BY name').all() as Row[]).map(toCategory);
    },
    put(c, at) {
      db.prepare(
        `INSERT INTO categories (name, default_enabled, transactional, retention_days, changed_by, changed_at)
         VALUES (?, ?, ?, ?, ?, ?)
         ON CONFLICT(name) DO UPDATE SET
           default_enabled = excluded.default_enabled, transactional = excluded.transactional,
           retention_days = excluded.retention_days, changed_by = excluded.changed_by,
           changed_at = excluded.changed_at`,
      ).run(c.name, c.defaultEnabled ? 1 : 0, c.transactional ? 1 : 0, c.retentionDays, c.changedBy, at);
    },
  };

  const preferences: PreferenceRepo = {
    get(recipientId, category, channel) {
      const row = db
        .prepare('SELECT enabled FROM preferences WHERE recipient_id = ? AND category = ? AND channel = ?')
        .get(recipientId, category, channel) as Row | undefined;
      return row ? row.enabled === 1 : null;
    },
    put(recipientId, category, channel, enabled, actor, at) {
      db.prepare(
        `INSERT INTO preferences (recipient_id, category, channel, enabled, changed_by, changed_at)
         VALUES (?, ?, ?, ?, ?, ?)
         ON CONFLICT(recipient_id, category, channel) DO UPDATE SET
           enabled = excluded.enabled, changed_by = excluded.changed_by, changed_at = excluded.changed_at`,
      ).run(recipientId, category, channel, enabled ? 1 : 0, actor, at);
    },
    listFor(recipientId) {
      return (db.prepare('SELECT * FROM preferences WHERE recipient_id = ?').all(recipientId) as Row[]).map((r) => ({
        category: r.category,
        channel: r.channel,
        enabled: r.enabled === 1,
        changedBy: r.changed_by,
      }));
    },
  };

  const notifications: NotificationRepo = {
    insert(n, idempotencyKey, requestHash) {
      db.prepare(
        `INSERT INTO notifications (id, recipient_id, category, transactional, dedup_key, payload_json,
                                    issuer, idempotency_key, request_hash, suppressed_reason, created_at)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      ).run(
        n.id,
        n.recipientId,
        n.category,
        n.transactional ? 1 : 0,
        n.dedupKey,
        JSON.stringify(n.payload),
        n.issuer,
        idempotencyKey,
        requestHash,
        n.suppressedReason,
        n.createdAt,
      );
    },
    get(id) {
      const row = db.prepare('SELECT * FROM notifications WHERE id = ?').get(id) as Row | undefined;
      return row ? toNotification(row) : null;
    },
    findByIdempotency(issuer, key) {
      const row = db
        .prepare('SELECT * FROM notifications WHERE issuer = ? AND idempotency_key = ?')
        .get(issuer, key) as Row | undefined;
      return row ? { notification: toNotification(row), requestHash: row.request_hash } : null;
    },
    findDuplicate(recipientId, dedupKey, since) {
      const row = db
        .prepare(
          `SELECT * FROM notifications
           WHERE recipient_id = ? AND dedup_key = ? AND created_at >= ? AND suppressed_reason IS NULL
           ORDER BY created_at DESC LIMIT 1`,
        )
        .get(recipientId, dedupKey, since) as Row | undefined;
      return row ? toNotification(row) : null;
    },
    markSuppressed(id, reason) {
      db.prepare('UPDATE notifications SET suppressed_reason = ? WHERE id = ?').run(reason, id);
    },
    listByRecipient(recipientId, since) {
      return (
        db
          .prepare('SELECT * FROM notifications WHERE recipient_id = ? AND created_at >= ? ORDER BY created_at DESC')
          .all(recipientId, since) as Row[]
      ).map(toNotification);
    },
  };

  const deliveries: DeliveryRepo = {
    insert(d) {
      db.prepare(
        `INSERT INTO deliveries (id, notification_id, channel, status, attempts, next_attempt_at,
                                 lease_until, lease_token, suppressed_reason, suppressed_detail, attempt_log_json)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      ).run(
        d.id,
        d.notificationId,
        d.channel,
        d.status,
        d.attempts,
        d.nextAttemptAt,
        d.leaseUntil,
        d.leaseToken,
        d.suppressedReason,
        d.suppressedDetail,
        JSON.stringify(d.attemptLog),
      );
    },
    get(id) {
      const row = db.prepare('SELECT * FROM deliveries WHERE id = ?').get(id) as Row | undefined;
      return row ? toDelivery(row) : null;
    },
    listByNotification(notificationId) {
      return (
        db.prepare('SELECT * FROM deliveries WHERE notification_id = ? ORDER BY channel').all(notificationId) as Row[]
      ).map(toDelivery);
    },

    /**
     * Reivindicação ATÔMICA. Três coisas acontecem juntas, e as três importam:
     *  - o lease é gravado (RES-01: morrer aqui não prende a entrega para sempre);
     *  - o fencing token é gravado (RES-05: escrita tardia de um dono anterior é rejeitada);
     *  - `attempts` é incrementado JÁ (RES-06: falha não capturada consome tentativa,
     *    então a entrega alcança PAR-04 e vai a dead-letter em vez de reprocessar
     *    para sempre). Trade-off declarado: um crash "gasta" uma tentativa.
     */
    claimDue(atNow, limit, leaseMs, token) {
      const rows = db
        .prepare(
          `UPDATE deliveries
              SET lease_until = ? + ?, lease_token = ?, attempts = attempts + 1
            WHERE id IN (
              SELECT id FROM deliveries
               WHERE status = 'pending'
                 AND next_attempt_at <= ?
                 AND (lease_until IS NULL OR lease_until <= ?)
               ORDER BY next_attempt_at
               LIMIT ?
            )
            RETURNING *`,
        )
        .all(atNow, leaseMs, token, atNow, atNow, limit) as Row[];
      return rows.map(toDelivery);
    },

    recordResult(id, token, patch) {
      const current = this.get(id);
      if (!current) return false;
      if (current.leaseToken !== token) return false; // fencing: dono anterior chegou tarde
      const log = patch.attempt ? [...current.attemptLog, patch.attempt].slice(-5) : current.attemptLog;
      const changed = db
        .prepare(
          `UPDATE deliveries
              SET status = ?, next_attempt_at = ?, suppressed_reason = ?, suppressed_detail = ?,
                  attempt_log_json = ?, lease_until = NULL, lease_token = NULL
            WHERE id = ? AND lease_token = ?`,
        )
        .run(
          patch.status,
          patch.nextAttemptAt ?? current.nextAttemptAt,
          patch.suppressedReason ?? null,
          patch.suppressedDetail ?? null,
          JSON.stringify(log),
          id,
          token,
        );
      return changed.changes > 0;
    },

    reopen(id, at) {
      const res = db
        .prepare(
          `UPDATE deliveries
              SET status = 'pending', next_attempt_at = ?, attempts = 0,
                  lease_until = NULL, lease_token = NULL,
                  suppressed_reason = NULL, suppressed_detail = NULL
            WHERE id = ? AND status IN ('dead_letter', 'suppressed')`,
        )
        .run(at, id);
      return res.changes > 0;
    },

    stats(atNow) {
      const row = db
        .prepare(
          `SELECT
             SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END)     AS pending,
             SUM(CASE WHEN status = 'dead_letter' THEN 1 ELSE 0 END) AS dead_letter,
             SUM(CASE WHEN status IN ('sent','delivered') THEN 1 ELSE 0 END) AS sent,
             SUM(CASE WHEN status = 'suppressed' THEN 1 ELSE 0 END)  AS suppressed,
             MIN(CASE WHEN status = 'pending' THEN next_attempt_at END) AS oldest
           FROM deliveries`,
        )
        .get() as Row;
      return {
        pending: row.pending ?? 0,
        deadLetter: row.dead_letter ?? 0,
        sent: row.sent ?? 0,
        suppressed: row.suppressed ?? 0,
        oldestAgeMs: row.oldest == null ? 0 : Math.max(0, atNow - row.oldest),
      };
    },

    listPending(atNow, limit) {
      return (
        db
          .prepare(`SELECT * FROM deliveries WHERE status = 'pending' ORDER BY next_attempt_at LIMIT ?`)
          .all(limit) as Row[]
      ).map(toDelivery);
    },
  };

  const apiKeys: ApiKeyRepo = {
    find(keyHash) {
      const row = db.prepare('SELECT * FROM api_keys WHERE key_hash = ?').get(keyHash) as Row | undefined;
      if (!row) return null;
      return {
        issuer: row.issuer,
        categories: JSON.parse(row.categories_json),
        allowTransactional: row.allow_transactional === 1,
      };
    },
    put(keyHash, rec, at) {
      db.prepare(
        `INSERT INTO api_keys (key_hash, issuer, categories_json, allow_transactional, created_at)
         VALUES (?, ?, ?, ?, ?)
         ON CONFLICT(key_hash) DO UPDATE SET
           issuer = excluded.issuer, categories_json = excluded.categories_json,
           allow_transactional = excluded.allow_transactional`,
      ).run(keyHash, rec.issuer, JSON.stringify(rec.categories), rec.allowTransactional ? 1 : 0, at);
    },
  };

  /**
   * Poda por retenção. Precedência declarada (achado ARC-08):
   * categories.retention_days sobrepõe PAR-18, que é o padrão.
   * Só apaga o que já é terminal — entrega pendente nunca é podada.
   */
  function purge(atNow: number, dryRun: boolean) {
    const cats = categories.list();
    const perCategory = new Map(cats.map((c) => [c.name, c.retentionDays ?? PAR_18_RETENTION_DAYS]));
    const day = 86_400_000;

    const doomed = (
      db
        .prepare(
          `SELECT n.id AS id, n.category AS category, n.created_at AS created_at
             FROM notifications n
            WHERE NOT EXISTS (
              SELECT 1 FROM deliveries d WHERE d.notification_id = n.id AND d.status = 'pending'
            )`,
        )
        .all() as Row[]
    ).filter((r) => atNow - r.created_at > (perCategory.get(r.category) ?? PAR_18_RETENTION_DAYS) * day);

    let deliveriesRemoved = 0;
    if (!dryRun) {
      const delStmt = db.prepare('DELETE FROM deliveries WHERE notification_id = ?');
      const notStmt = db.prepare('DELETE FROM notifications WHERE id = ?');
      withTransaction(() => {
        for (const r of doomed) {
          deliveriesRemoved += delStmt.run(r.id).changes as number;
          notStmt.run(r.id);
        }
      });
    } else {
      for (const r of doomed) {
        deliveriesRemoved += (
          db.prepare('SELECT COUNT(*) AS c FROM deliveries WHERE notification_id = ?').get(r.id) as Row
        ).c;
      }
    }
    return { notifications: doomed.length, deliveries: deliveriesRemoved };
  }

  return {
    db,
    now,
    withTransaction,
    recipients,
    categories,
    preferences,
    notifications,
    deliveries,
    apiKeys,
    purge,
    close: () => db.close(),
  };
}
