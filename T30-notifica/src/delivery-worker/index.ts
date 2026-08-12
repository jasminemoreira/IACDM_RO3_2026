/**
 * M-09 delivery-worker — MECANISMO PURO. Nenhuma regra de negócio.
 *
 * Em V(1) este módulo acumulava laço, backoff, dead-letter e reavaliação de
 * regras, e foi atingido por 10 das 18 lentes da Fase 2. A resposta foi separar
 * política de mecanismo: toda decisão vive em M-04. Aqui só há: reivindicar,
 * montar contexto, perguntar, enviar, reportar.
 *
 * PAR-19: até 8 envios EM VOO no laço único. Node faz I/O concorrente sem
 * thread nem processo extra — mata o head-of-line blocking (achado PERF-01) sem
 * violar a premissa de um só laço.
 * PAR-10: o envio é abortado em 10 s. É essa trava que mantém a posse da entrega
 * muito abaixo do lease de 60 s e fecha RES-05.
 * PAR-24: intervalo do laço.
 */
import type { Channel, ChannelPort, DecisionContext, Delivery } from '../types.ts';
import type { Store } from '../store/index.ts';
import type { Outbox } from '../outbox/index.ts';
import type { DeliveryPolicy } from '../delivery-policy/index.ts';
import type { Preferences } from '../preferences/index.ts';
import { PAR_10_REQUEST_TIMEOUT_MS } from '../channel-webhook/index.ts';

/** PAR-24 — intervalo do laço. */
export const PAR_24_TICK_INTERVAL_MS = 1_000;

export interface TickResult {
  claimed: number;
  sent: number;
  suppressed: number;
  deferred: number;
  failed: number;
  deadLettered: number;
}

export interface WorkerDeps {
  store: Store;
  outbox: Outbox;
  policy: DeliveryPolicy;
  preferences: Preferences;
  channels: Record<Channel, ChannelPort>;
  /** OBS-04: o dono do alarme de PAR-23 é o worker — declarado, não implícito. */
  onAlarm?: (stats: { pending: number; oldestAgeMs: number }) => void;
  log?: (line: string) => void;
}

export interface DeliveryWorker {
  tick(now?: number): Promise<TickResult>;
  start(): void;
  stop(): void;
  running(): boolean;
}

export function createDeliveryWorker(deps: WorkerDeps): DeliveryWorker {
  const { store, outbox, policy, preferences, channels } = deps;
  let timer: NodeJS.Timeout | null = null;
  let ticking = false;

  async function processOne(delivery: Delivery, token: string, now: number): Promise<Partial<TickResult>> {
    // Contexto materializado AQUI — a política não faz I/O (achado ARC-06).
    const notification = store.notifications.get(delivery.notificationId);
    if (!notification) {
      outbox.recordResult(delivery.id, token, {
        status: 'dead_letter',
        attempt: { n: delivery.attempts, at: now, outcome: 'permanent', detail: 'notificação inexistente' },
      });
      return { deadLettered: 1, failed: 1 };
    }
    const recipient = preferences.recipient(notification.recipientId);
    const category = preferences.category(notification.category);
    if (!recipient || !category) {
      outbox.recordResult(delivery.id, token, {
        status: 'dead_letter',
        attempt: { n: delivery.attempts, at: now, outcome: 'permanent', detail: 'destinatário ou categoria removidos' },
      });
      return { deadLettered: 1, failed: 1 };
    }

    const ctx: DecisionContext = {
      delivery,
      notification,
      recipient,
      category,
      channelEnabled: preferences.resolve(recipient.id, category.name, delivery.channel).enabled,
      now,
    };

    const verdict = policy.decide(ctx);

    if (verdict.decision === 'suppress') {
      outbox.recordResult(delivery.id, token, {
        status: 'suppressed',
        suppressedReason: verdict.reason,
        suppressedDetail: verdict.detail,
        attempt: { n: delivery.attempts, at: now, outcome: 'permanent', detail: `suprimida: ${verdict.reason}` },
      });
      return { suppressed: 1 };
    }

    if (verdict.decision === 'defer') {
      // PRO-05: precedência declarada entre adiamento e reprogramação por falha.
      const nextAt = Math.max(verdict.until, delivery.nextAttemptAt);
      outbox.recordResult(delivery.id, token, {
        status: 'pending',
        nextAttemptAt: nextAt,
        attempt: { n: delivery.attempts, at: now, outcome: 'transient', detail: `adiada por quiet_hours até ${nextAt}` },
      });
      return { deferred: 1 };
    }

    const port = channels[delivery.channel];
    const controller = new AbortController();
    const abortTimer = setTimeout(() => controller.abort(), PAR_10_REQUEST_TIMEOUT_MS);
    let result;
    try {
      result = await port.send(
        {
          deliveryId: delivery.id,
          notificationId: notification.id,
          recipient,
          category: category.name,
          transactional: category.transactional,
          payload: notification.payload,
          now,
        },
        controller.signal,
      );
    } finally {
      clearTimeout(abortTimer);
    }

    if (result.accepted) {
      outbox.recordResult(delivery.id, token, {
        status: port.terminalStatus, // 'sent' (e-mail) ou 'delivered' (webhook)
        attempt: { n: delivery.attempts, at: now, outcome: 'ok', detail: result.detail },
      });
      return { sent: 1 };
    }

    if (result.permanent) {
      // EDGE-3: falha definitiva não retenta. Sem essa distinção, uma URL
      // inválida consumiria 5 tentativas contra um host que nunca existiu.
      outbox.recordResult(delivery.id, token, {
        status: 'dead_letter',
        attempt: { n: delivery.attempts, at: now, outcome: 'permanent', detail: result.detail },
      });
      return { failed: 1, deadLettered: 1 };
    }

    const next = policy.nextAttempt(delivery.attempts, now);
    if ('deadLetter' in next) {
      outbox.recordResult(delivery.id, token, {
        status: 'dead_letter',
        attempt: { n: delivery.attempts, at: now, outcome: 'transient', detail: `${result.detail} (esgotou PAR-04)` },
      });
      return { failed: 1, deadLettered: 1 };
    }
    outbox.recordResult(delivery.id, token, {
      status: 'pending',
      nextAttemptAt: next.at,
      attempt: { n: delivery.attempts, at: now, outcome: 'transient', detail: result.detail },
    });
    return { failed: 1 };
  }

  async function tick(nowArg?: number): Promise<TickResult> {
    const now = nowArg ?? store.now();
    const totals: TickResult = { claimed: 0, sent: 0, suppressed: 0, deferred: 0, failed: 0, deadLettered: 0 };

    const claimed = outbox.claim(now);
    totals.claimed = claimed.length;

    // O lote já vem limitado a PAR-19 pelo outbox, então isto é exatamente
    // "no máximo 8 em voo" — nenhuma entrega espera com o lease correndo.
    const results = await Promise.allSettled(claimed.map((c) => processOne(c.delivery, c.token, now)));

    for (const r of results) {
      if (r.status === 'fulfilled') {
        for (const [k, v] of Object.entries(r.value)) {
          totals[k as keyof TickResult] += v as number;
        }
      } else {
        // RES-06: exceção não capturada NÃO trava a entrega. O lease expira e
        // ela volta à fila — e `attempts` já foi incrementado na reivindicação,
        // então ela caminha para dead-letter em vez de reprocessar para sempre.
        totals.failed += 1;
        deps.log?.(`falha não capturada no processamento: ${(r.reason as Error)?.message}`);
      }
    }

    const stats = outbox.stats(now);
    if (stats.ageAlarm) {
      deps.onAlarm?.({ pending: stats.pending, oldestAgeMs: stats.oldestAgeMs });
      deps.log?.(
        `ALARME PAR-23: entrega mais velha com ${Math.round(stats.oldestAgeMs / 60000)} min, ${stats.pending} pendentes`,
      );
    }
    return totals;
  }

  return {
    tick,
    start() {
      if (timer) return;
      timer = setInterval(() => {
        if (ticking) return; // um laço só — sem sobreposição de ticks
        ticking = true;
        void tick()
          .catch((err) => deps.log?.(`tick falhou: ${(err as Error).message}`))
          .finally(() => {
            ticking = false;
          });
      }, PAR_24_TICK_INTERVAL_MS);
      timer.unref?.();
    },
    stop() {
      if (timer) clearInterval(timer);
      timer = null;
    },
    running: () => timer !== null,
  };
}
