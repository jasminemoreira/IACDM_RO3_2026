/**
 * M-05 preferences — pessoas, preferências e o CATÁLOGO DE CATEGORIAS.
 *
 * O catálogo é do OPERADOR, não do emissor (achado GAM-01): é ele que decide o
 * que é transacional. Toda alteração de categoria é auditada (achado GOV-04),
 * porque marcar uma categoria como transacional anula o opt-out das pessoas —
 * poder que fica visível em vez de silencioso (achado ETH-03, mitigado).
 *
 * ARC-07 (risco aceito): este módulo tem duas razões para mudar — dado da pessoa
 * e política do operador. Separar exigiria um 13º módulo, fora da faixa 8–12 do
 * enunciado. A coesão que justifica: o catálogo é a CAMADA DE PADRÃO da mesma
 * política — "quem recebe o quê".
 *
 * Invariante 3: ausência de preferência ≠ opt-out. Resolve pelo padrão da categoria.
 */
import type { Category, Channel, Recipient } from '../types.ts';
import type { Store } from '../store/index.ts';

/** PAR-14 — janela de silêncio padrão: 22:00 (1320) às 08:00 (480). */
export const PAR_14_DEFAULT_QUIET_START = 22 * 60;
export const PAR_14_DEFAULT_QUIET_END = 8 * 60;

export interface Resolution {
  enabled: boolean;
  /** true quando veio do padrão da categoria, não de uma preferência explícita. */
  defaulted: boolean;
}

export interface RecipientInput {
  id: string;
  timezone: string;
  email?: string | null;
  webhookUrl?: string | null;
  webhookSecret?: string | null;
  quietStart?: number;
  quietEnd?: number;
}

export class ValidationError extends Error {
  // Sem parameter properties: o strip-only do Node não as transforma, só remove
  // tipos. Atribuição explícita é o preço de não ter passo de build.
  field: string;

  constructor(message: string, field: string) {
    super(message);
    this.field = field;
  }
}

/** PRE-2 / EDGE-2: fuso é obrigatório e precisa ser IANA válido. */
export function isValidTimezone(tz: string): boolean {
  try {
    new Intl.DateTimeFormat('en', { timeZone: tz });
    return true;
  } catch {
    return false;
  }
}

export interface Preferences {
  recipient(id: string): Recipient | null;
  putRecipient(input: RecipientInput): Recipient;
  category(name: string): Category | null;
  listCategories(): Category[];
  setCategory(c: { name: string; defaultEnabled: boolean; transactional: boolean; retentionDays?: number | null }, actor: string): Category;
  resolve(recipientId: string, category: string, channel: Channel): Resolution;
  optOut(recipientId: string, target: { category?: string; channel?: Channel }, actor: string): void;
  optIn(recipientId: string, target: { category?: string; channel?: Channel }, actor: string): void;
  list(recipientId: string): Array<{ category: string; channel: string; enabled: boolean; changedBy: string }>;
}

export function createPreferences(store: Store): Preferences {
  return {
    recipient: (id) => store.recipients.get(id),

    putRecipient(input) {
      if (!input.id) throw new ValidationError('id é obrigatório', 'id');
      if (!input.timezone || !isValidTimezone(input.timezone)) {
        // A ausência de fuso não vira "UTC por conveniência": o motor de janela
        // nunca pode receber fuso ausente (PRE-2).
        throw new ValidationError(`fuso horário IANA inválido ou ausente: ${input.timezone}`, 'timezone');
      }
      const now = store.now();
      const existing = store.recipients.get(input.id);
      const rec: Recipient = {
        id: input.id,
        timezone: input.timezone,
        email: input.email ?? null,
        webhookUrl: input.webhookUrl ?? null,
        webhookSecret: input.webhookSecret ?? existing?.webhookSecret ?? null,
        quietStart: input.quietStart ?? existing?.quietStart ?? PAR_14_DEFAULT_QUIET_START,
        quietEnd: input.quietEnd ?? existing?.quietEnd ?? PAR_14_DEFAULT_QUIET_END,
        tokens: existing?.tokens ?? 10,
        lastRefillAt: existing?.lastRefillAt ?? now,
      };
      store.recipients.put(rec, now);
      return rec;
    },

    category: (name) => store.categories.get(name),
    listCategories: () => store.categories.list(),

    setCategory(c, actor) {
      if (!actor) throw new ValidationError('actor é obrigatório: alteração de categoria é auditada', 'actor');
      const now = store.now();
      store.categories.put(
        {
          name: c.name,
          defaultEnabled: c.defaultEnabled,
          transactional: c.transactional,
          retentionDays: c.retentionDays ?? null,
          changedBy: actor,
        },
        now,
      );
      return store.categories.get(c.name)!;
    },

    /**
     * Precedência: preferência específica do canal > preferência do canal '*' >
     * padrão da categoria. Categoria desconhecida resolve como desabilitada —
     * emitir numa categoria fora do catálogo é erro do emissor, não permissão.
     */
    resolve(recipientId, category, channel) {
      const specific = store.preferences.get(recipientId, category, channel);
      if (specific !== null) return { enabled: specific, defaulted: false };

      const anyChannel = store.preferences.get(recipientId, category, '*');
      if (anyChannel !== null) return { enabled: anyChannel, defaulted: false };

      const cat = store.categories.get(category);
      return { enabled: cat?.defaultEnabled ?? false, defaulted: true };
    },

    optOut(recipientId, target, actor) {
      const now = store.now();
      const category = target.category ?? '*';
      const channel = target.channel ?? '*';
      if (category === '*') {
        // Desligar TODAS as categorias conhecidas naquele canal.
        for (const c of store.categories.list()) {
          store.preferences.put(recipientId, c.name, channel, false, actor, now);
        }
        return;
      }
      store.preferences.put(recipientId, category, channel, false, actor, now);
    },

    /** PRO-04: o glossário diz "válido até reativação explícita" — eis o caminho de volta. */
    optIn(recipientId, target, actor) {
      const now = store.now();
      const category = target.category ?? '*';
      const channel = target.channel ?? '*';
      if (category === '*') {
        for (const c of store.categories.list()) {
          store.preferences.put(recipientId, c.name, channel, true, actor, now);
        }
        return;
      }
      store.preferences.put(recipientId, category, channel, true, actor, now);
    },

    list: (recipientId) => store.preferences.listFor(recipientId),
  };
}
