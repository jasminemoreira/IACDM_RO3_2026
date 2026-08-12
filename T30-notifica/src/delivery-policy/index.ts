/**
 * M-04 delivery-policy — TODA decisão da entrega, num lugar só.
 *
 * Substituiu o módulo `suppression` de V(1), que recebia um parâmetro `stage` e
 * servia a dois mestres (achado ARC-01). Aqui só existe o estágio de ENTREGA;
 * as regras de ingresso (`opt_out` inicial, `duplicate`) vivem em M-03 ingestion.
 *
 * Recebe um DecisionContext JÁ MATERIALIZADO — não consulta preferences nem faz
 * I/O (achado ARC-06). A janela é função pura; o teto tem estado, e isso está
 * declarado em vez de escondido atrás de uma alegação de pureza.
 *
 * Ordem das regras: opt_out -> quiet_hours -> rate_limited.
 * Transacional pula as três. NUNCA pula `duplicate` — que é do ingresso
 * (invariante 2 do glossário / EDGE-7).
 */
import type { DecisionContext, Verdict } from '../types.ts';
import { check as checkQuietHours } from '../quiet-hours/index.ts';
import type { RateLimiter } from '../rate-limiter/index.ts';

/** PAR-02 — base do backoff Full Jitter. */
export const PAR_02_BACKOFF_BASE_MS = 5_000;
/** PAR-03 — teto do backoff. */
export const PAR_03_BACKOFF_CAP_MS = 24 * 3_600_000;
/** PAR-04 — máximo de tentativas. Desvio consciente de R-01 (~9 em 75 h). */
export const PAR_04_MAX_ATTEMPTS = 5;
/** PAR-25 — dispersão na reabertura da janela, contra o efeito manada (CTL-03). */
export const PAR_25_REOPEN_JITTER_MS = 5 * 60_000;

export interface DeliveryPolicy {
  decide(ctx: DecisionContext): Verdict;
  nextAttempt(attempts: number, now: number): { at: number } | { deadLetter: true };
}

/**
 * Full Jitter, portado literalmente de specs/examples §1 (fonte R-05):
 *   sleep = random(0, min(cap, base * 2 ** attempt))
 * `attempt` começa em 0 na PRIMEIRA retentativa — como `attempts` já foi
 * incrementado na reivindicação (RES-06), o expoente é `attempts - 1`.
 */
export function fullJitterDelay(attempts: number, random: () => number = Math.random): number {
  const exponent = Math.max(0, attempts - 1);
  const ceiling = Math.min(PAR_03_BACKOFF_CAP_MS, PAR_02_BACKOFF_BASE_MS * 2 ** exponent);
  return Math.floor(random() * ceiling);
}

export function createDeliveryPolicy(rateLimiter: RateLimiter, random: () => number = Math.random): DeliveryPolicy {
  return {
    decide(ctx) {
      const { delivery, recipient, category, channelEnabled, now } = ctx;

      // Transacional (declarado pelo CATÁLOGO, não pelo emissor — achado GAM-01)
      // ignora as três regras de entrega.
      if (!category.transactional) {
        // REG-02: opt-out é reavaliado AQUI também. Sem isto, uma entrega
        // materializada e adiada pela madrugada sairia depois do descadastro.
        if (!channelEnabled) {
          return { decision: 'suppress', reason: 'opt_out', detail: `channel=${delivery.channel}` };
        }

        const quiet = checkQuietHours(
          { start: recipient.quietStart, end: recipient.quietEnd },
          recipient.timezone,
          now,
        );
        if (quiet.inWindow && quiet.opensAt !== undefined) {
          // CTL-03: sem dispersão, todas as entregas de um fuso acordam no mesmo
          // minuto. O jitter é limitado a 10% da janela para não empurrar a
          // entrega para fora dela numa janela curta (achado SCI-05).
          const windowMs = windowLengthMs(recipient.quietStart, recipient.quietEnd);
          const jitterCeiling = Math.min(PAR_25_REOPEN_JITTER_MS, Math.floor(windowMs * 0.1));
          const until = quiet.opensAt + Math.floor(random() * jitterCeiling);
          return { decision: 'defer', until, reason: 'quiet_hours' };
        }

        // O teto é consumido AQUI, na entrega — não no POST (decisão da Fase 0).
        const consumed = rateLimiter.tryConsume(recipient.id, now);
        if (!consumed.ok) {
          return { decision: 'suppress', reason: 'rate_limited', detail: consumed.capApplied };
        }
      }

      return { decision: 'send' };
    },

    /**
     * Chamado pelo worker SOMENTE quando o envio falha de forma transitória
     * (achado LIN-06: quem reprograma é este método, não `decide`).
     */
    nextAttempt(attempts, now) {
      if (attempts >= PAR_04_MAX_ATTEMPTS) return { deadLetter: true };
      return { at: now + fullJitterDelay(attempts, random) };
    },
  };
}

function windowLengthMs(start: number, end: number): number {
  const minutes = start <= end ? end - start : 1440 - start + end;
  return minutes * 60_000;
}
