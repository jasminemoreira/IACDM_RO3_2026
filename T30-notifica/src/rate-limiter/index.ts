/**
 * M-07 rate-limiter — token bucket global por pessoa.
 *
 * Portado de specs/examples/reference-implementations.md §3 (Tier 2, fonte R-07).
 * PAR-11 token bucket (escolhido sobre GCRA porque "quantos tokens restam?" é
 * pergunta direta — a CLI do UC-8 precisa responder isso).
 * PAR-12: capacidade 10, janela 1 h, escopo GLOBAL por pessoa (decisão da Fase 0).
 * Recarga CONTÍNUA e preguiçosa, não por hora fechada (achado SCI-01).
 *
 * O teto é consumido NA ENTREGA, não no POST: ele protege a pessoa de
 * interrupção, e quem interrompe é a entrega (decisão da Fase 0).
 */
import type { Store } from '../store/index.ts';

/** PAR-12 — capacidade do balde. */
export const PAR_12_CAPACITY = 10;
/** PAR-12 — janela de recarga completa, em ms. */
export const PAR_12_WINDOW_MS = 3_600_000;

export interface ConsumeResult {
  ok: boolean;
  retryAfterMs?: number;
  /** Parâmetro vigente na decisão, para o registro de auditoria (GOV-02). */
  capApplied: string;
}

export interface RateLimiter {
  tryConsume(recipientId: string, now: number): ConsumeResult;
  peek(recipientId: string, now: number): number;
}

function refill(tokens: number, lastRefillAt: number, now: number): number {
  // CTL-02: relógio retrocedendo daria `elapsed` negativo e REDUZIRIA tokens.
  // Satura em zero — nunca punir por causa do relógio.
  const elapsed = Math.max(0, now - lastRefillAt);
  const gained = elapsed * (PAR_12_CAPACITY / PAR_12_WINDOW_MS);
  return Math.min(PAR_12_CAPACITY, tokens + gained);
}

export function createRateLimiter(store: Store): RateLimiter {
  const capApplied = `cap=${PAR_12_CAPACITY}/1h`;

  return {
    tryConsume(recipientId, now) {
      // ASS-04: a leitura-modificação-escrita precisa ser atômica. Com o worker
      // único e a transação do store isso vale; a exigência fica DECLARADA aqui
      // em vez de implícita, porque trocar o repositório a quebraria em silêncio.
      return store.withTransaction(() => {
        const r = store.recipients.get(recipientId);
        if (!r) return { ok: false, capApplied };

        const tokens = refill(r.tokens, r.lastRefillAt, now);
        if (tokens >= 1) {
          store.recipients.updateBucket(recipientId, tokens - 1, now);
          return { ok: true, capApplied };
        }
        store.recipients.updateBucket(recipientId, tokens, now);
        const deficit = 1 - tokens;
        return {
          ok: false,
          retryAfterMs: Math.ceil(deficit * (PAR_12_WINDOW_MS / PAR_12_CAPACITY)),
          capApplied,
        };
      });
    },

    peek(recipientId, now) {
      const r = store.recipients.get(recipientId);
      return r ? refill(r.tokens, r.lastRefillAt, now) : 0;
    },
  };
}
