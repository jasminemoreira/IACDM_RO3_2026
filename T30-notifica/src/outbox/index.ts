/**
 * M-08 outbox — fila durável de entregas, com lease.
 *
 * A tabela `deliveries` É o outbox (R-06): notificação e entregas são gravadas na
 * MESMA transação, e este módulo dá a ela semântica de fila. Nunca gravar a
 * notificação e enfileirar a entrega em transações distintas — é exatamente a
 * falha que o padrão existe para evitar.
 *
 * O lease é a resposta a RES-01/ASS-01 da iteração 1 — e os dois críticos da
 * iteração 2 são justamente as janelas que ele abriu:
 *
 *  RES-05 (duplicação): três travas combinadas — o lote de `claim` é limitado a
 *    PAR-19 (nada espera com o lease correndo), o envio é abortado em PAR-10 pelo
 *    worker (posse ~10 s contra lease de 60 s), e `recordResult` exige o fencing
 *    token, rejeitando a escrita de um dono anterior que chegou tarde.
 *
 *  RES-06 (poison message): `attempts` é incrementado NA REIVINDICAÇÃO, não no
 *    resultado. Falha não capturada consome tentativa, a entrega alcança PAR-04 e
 *    vai a dead-letter em vez de reprocessar para sempre. Trade-off declarado:
 *    um crash "gasta" uma tentativa.
 */
import { randomUUID } from 'node:crypto';
import type {
  AttemptRecord,
  Channel,
  Delivery,
  DeliveryStatus,
  Notification,
  NotificationStatus,
  SuppressionReason,
} from '../types.ts';
import type { Store } from '../store/index.ts';

/**
 * Estado da notificação é DERIVADO das entregas, nunca armazenado (achado
 * PRO-01: em V(1) a coluna existia e nenhum módulo era dono de mantê-la).
 * O dono da derivação é este módulo, que é o dono das entregas.
 */
export function deriveStatus(
  notification: Notification,
  deliveries: Delivery[],
  now: number,
): NotificationStatus {
  if (notification.suppressedReason) return 'suppressed';
  if (deliveries.length === 0) return 'suppressed';

  const succeeded = deliveries.filter((d) => d.status === 'sent' || d.status === 'delivered').length;
  const terminalBad = deliveries.filter((d) => d.status === 'dead_letter' || d.status === 'suppressed').length;
  const pending = deliveries.filter((d) => d.status === 'pending');

  if (pending.length > 0) {
    if (succeeded > 0) return 'partially_delivered';
    return pending.some((d) => d.nextAttemptAt > now) ? 'deferred' : 'accepted';
  }
  if (succeeded === deliveries.length) return 'delivered';
  if (succeeded > 0 && terminalBad > 0) return 'partially_delivered';
  return 'failed';
}

/** PAR-19 — envios em voo simultâneos, e também o teto do lote de reivindicação. */
export const PAR_19_MAX_IN_FLIGHT = 8;
/** PAR-20 — duração do lease de reivindicação. */
export const PAR_20_LEASE_MS = 60_000;
/** PAR-23 — limiar de alarme para a idade da entrega mais velha. */
export const PAR_23_QUEUE_AGE_ALARM_MS = 15 * 60_000;

export interface ClaimedDelivery {
  delivery: Delivery;
  /** Fencing token: sem ele, `recordResult` não escreve. */
  token: string;
}

export interface OutboxStats {
  pending: number;
  oldestAgeMs: number;
  deadLetter: number;
  sent: number;
  suppressed: number;
  /** Sinal de PAR-23. Quem reage a ele é o worker (achado OBS-04: dono declarado). */
  ageAlarm: boolean;
}

export interface Outbox {
  enqueue(notificationId: string, channels: Channel[], dueAt: number): Delivery[];
  claim(now: number, limit?: number): ClaimedDelivery[];
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
  history(notificationId: string): Delivery[];
  byRecipient(recipientId: string, since: number): Array<{ notificationId: string; deliveries: Delivery[] }>;
  reopen(deliveryId: string, now: number): boolean;
  stats(now: number): OutboxStats;
  pending(now: number, limit?: number): Delivery[];
}

export function createOutbox(store: Store): Outbox {
  return {
    /**
     * Chamado DENTRO da transação de ingestão (R-06). Não abre transação própria
     * de propósito: quem garante a atomicidade é o chamador.
     */
    enqueue(notificationId, channels, dueAt) {
      const created: Delivery[] = [];
      for (const channel of channels) {
        const d: Delivery = {
          id: randomUUID(),
          notificationId,
          channel,
          status: 'pending',
          attempts: 0,
          nextAttemptAt: dueAt,
          leaseUntil: null,
          leaseToken: null,
          suppressedReason: null,
          suppressedDetail: null,
          attemptLog: [],
        };
        store.deliveries.insert(d);
        created.push(d);
      }
      return created;
    },

    claim(now, limit = PAR_19_MAX_IN_FLIGHT) {
      // PERF-05: o lote nunca excede a concorrência em voo. Se excedesse, as
      // entregas sobrando esperariam sua vez com o lease correndo — e poderiam
      // perdê-lo antes de sequer serem tentadas.
      const effective = Math.min(limit, PAR_19_MAX_IN_FLIGHT);
      const token = randomUUID();
      const claimed = store.withTransaction(() =>
        store.deliveries.claimDue(now, effective, PAR_20_LEASE_MS, token),
      );
      return claimed.map((delivery) => ({ delivery, token }));
    },

    recordResult: (id, token, patch) => store.deliveries.recordResult(id, token, patch),

    history: (notificationId) => store.deliveries.listByNotification(notificationId),

    byRecipient(recipientId, since) {
      // UX-01: a pergunta real do operador é "por que ESTA PESSOA não recebeu
      // nada hoje?", não "o que houve com a notificação X".
      return store.notifications
        .listByRecipient(recipientId, since)
        .map((n) => ({ notificationId: n.id, deliveries: store.deliveries.listByNotification(n.id) }));
    },

    /** PRO-02: transição explícita de terminal de volta para pendente. */
    reopen: (deliveryId, now) => store.deliveries.reopen(deliveryId, now),

    stats(now) {
      const s = store.deliveries.stats(now);
      return { ...s, ageAlarm: s.oldestAgeMs > PAR_23_QUEUE_AGE_ALARM_MS };
    },

    pending: (now, limit = 50) => store.deliveries.listPending(now, limit),
  };
}
