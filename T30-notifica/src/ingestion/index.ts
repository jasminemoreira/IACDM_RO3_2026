/**
 * M-03 ingestion — transaction script do ingresso.
 *
 * Faz três coisas, nesta ordem:
 *  1. idempotência da REQUISIÇÃO, escopada por emissor (R-03 / achado SEC-08);
 *  2. regras do estágio de ingresso: `opt_out` -> `duplicate`;
 *  3. persiste a notificação e enfileira as entregas na MESMA transação (R-06).
 *
 * Idempotência ≠ deduplicação. Idempotência é sobre a requisição HTTP;
 * deduplicação é sobre o conteúdo lógico (glossário). São mecanismos distintos e
 * a confusão entre eles é o erro que o glossário existe para evitar.
 *
 * Transacional (declarado pelo CATÁLOGO, não pelo emissor — achado GAM-01) pula
 * `opt_out`; NUNCA pula `duplicate` (invariante 2 / EDGE-7).
 */
import { createHash, randomUUID } from 'node:crypto';
import type { Channel, Notification, NotificationPayload, SuppressionReason } from '../types.ts';
import type { Store } from '../store/index.ts';
import type { Preferences } from '../preferences/index.ts';
import type { Outbox } from '../outbox/index.ts';

/** PAR-05 — janela de deduplicação. */
export const PAR_05_DEDUP_WINDOW_MS = 5 * 60_000;
/** PAR-26 — tamanho máximo do payload (achado SEC-06). */
export const PAR_26_MAX_PAYLOAD_BYTES = 64 * 1024;

export interface IngestCommand {
  recipientId: string;
  category: string;
  dedupKey?: string | null;
  payload: NotificationPayload;
}

export interface IngestResult {
  notificationId: string;
  status: 'accepted' | 'suppressed';
  /** UX-03: o emissor não precisa adivinhar se a notificação foi descartada. */
  reason?: SuppressionReason;
  detail?: string;
  channels: Channel[];
  /** true quando a resposta veio da chave de idempotência, sem criar nada novo. */
  replayed?: boolean;
}

export type IngestErrorCode =
  | 'unknown_recipient'
  | 'unknown_category'
  | 'payload_too_large'
  | 'idempotency_conflict'
  | 'no_channel';

export class IngestError extends Error {
  code: IngestErrorCode;

  constructor(message: string, code: IngestErrorCode) {
    super(message);
    this.code = code;
  }
}

export interface Ingestion {
  ingest(cmd: IngestCommand, issuer: string, idempotencyKey?: string | null): IngestResult;
}

export function createIngestion(store: Store, preferences: Preferences, outbox: Outbox): Ingestion {
  return {
    ingest(cmd, issuer, idempotencyKey) {
      const now = store.now();
      const payloadJson = JSON.stringify(cmd.payload);

      if (Buffer.byteLength(payloadJson, 'utf8') > PAR_26_MAX_PAYLOAD_BYTES) {
        throw new IngestError(`payload excede PAR-26 (${PAR_26_MAX_PAYLOAD_BYTES} bytes)`, 'payload_too_large');
      }

      const recipient = preferences.recipient(cmd.recipientId);
      if (!recipient) throw new IngestError(`destinatário desconhecido: ${cmd.recipientId}`, 'unknown_recipient');

      // Categoria fora do catálogo é erro do emissor, não permissão implícita.
      const category = preferences.category(cmd.category);
      if (!category) throw new IngestError(`categoria fora do catálogo: ${cmd.category}`, 'unknown_category');

      // (1) Idempotência da requisição — escopada por emissor.
      const requestHash = createHash('sha256')
        .update(`${cmd.recipientId}|${cmd.category}|${cmd.dedupKey ?? ''}|${payloadJson}`)
        .digest('hex');

      if (idempotencyKey) {
        const prior = store.notifications.findByIdempotency(issuer, idempotencyKey);
        if (prior) {
          if (prior.requestHash !== requestHash) {
            // Mesma chave, corpo diferente: erro do cliente, não silêncio.
            throw new IngestError('mesma Idempotency-Key com corpo diferente', 'idempotency_conflict');
          }
          const existing = store.deliveries.listByNotification(prior.notification.id);
          return {
            notificationId: prior.notification.id,
            status: prior.notification.suppressedReason ? 'suppressed' : 'accepted',
            reason: prior.notification.suppressedReason ?? undefined,
            channels: existing.map((d) => d.channel),
            replayed: true,
          };
        }
      }

      // Canais fisicamente possíveis para esta pessoa.
      const available: Channel[] = [];
      if (recipient.email) available.push('email');
      if (recipient.webhookUrl) available.push('webhook');
      if (available.length === 0) {
        throw new IngestError(`destinatário ${recipient.id} não tem nenhum endereço de canal`, 'no_channel');
      }

      const notification: Notification = {
        id: randomUUID(),
        recipientId: recipient.id,
        category: category.name,
        transactional: category.transactional,
        dedupKey: cmd.dedupKey ?? null,
        payload: cmd.payload,
        issuer, // GOV-01: quem mandou isto
        suppressedReason: null,
        createdAt: now,
      };

      // (2a) opt_out — transacional pula.
      let enabled: Channel[] = available;
      if (!category.transactional) {
        enabled = available.filter((ch) => preferences.resolve(recipient.id, category.name, ch).enabled);
        if (enabled.length === 0) {
          return store.withTransaction(() => {
            notification.suppressedReason = 'opt_out';
            store.notifications.insert(notification, idempotencyKey ?? null, requestHash);
            return {
              notificationId: notification.id,
              status: 'suppressed' as const,
              reason: 'opt_out' as const,
              detail: 'nenhum canal habilitado para a categoria',
              channels: [],
            };
          });
        }
      }

      // (2b) duplicate — vale INCLUSIVE para transacional (invariante 2 / EDGE-7).
      if (cmd.dedupKey) {
        const since = now - PAR_05_DEDUP_WINDOW_MS;
        const twin = store.notifications.findDuplicate(recipient.id, cmd.dedupKey, since);
        if (twin) {
          return store.withTransaction(() => {
            notification.suppressedReason = 'duplicate';
            store.notifications.insert(notification, idempotencyKey ?? null, requestHash);
            return {
              notificationId: notification.id,
              status: 'suppressed' as const,
              reason: 'duplicate' as const,
              detail: `janela=${PAR_05_DEDUP_WINDOW_MS / 60000}min, original=${twin.id}`,
              channels: [],
            };
          });
        }
      }

      // (3) Notificação e entregas na MESMA transação — o ponto do padrão R-06.
      return store.withTransaction(() => {
        store.notifications.insert(notification, idempotencyKey ?? null, requestHash);
        outbox.enqueue(notification.id, enabled, now);
        return {
          notificationId: notification.id,
          status: 'accepted' as const,
          channels: enabled,
        };
      });
    },
  };
}
