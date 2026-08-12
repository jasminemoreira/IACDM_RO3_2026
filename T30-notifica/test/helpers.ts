/**
 * Apoio dos testes. Constrói o app com provedores locais e carrega os fixtures
 * de specs/datasets — o ground truth vem de lá, não de valores inventados aqui.
 */
import { mkdtempSync } from 'node:fs';
import { readFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createApp, type App } from '../src/app.ts';
import { startDevbox, type Devbox } from '../src/cli/devbox.ts';

export interface Fixtures {
  categories: Array<{ name: string; defaultEnabled: boolean; transactional: boolean; retentionDays?: number }>;
  recipients: Array<{
    id: string;
    timezone: string;
    email: string | null;
    webhook: boolean;
    quietStart: number;
    quietEnd: number;
  }>;
  payloads: Array<{ id: string; category: string; subject: string; body: string }>;
}

export async function loadFixtures(): Promise<Fixtures> {
  const raw = await readFile(new URL('../specs/datasets/fixtures.json', import.meta.url), 'utf8');
  return JSON.parse(raw) as Fixtures;
}

export interface Harness {
  app: App;
  box: Devbox;
  dbPath: string;
  stop(): Promise<void>;
}

export interface HarnessOptions {
  hookStatus?: () => number;
  hookDelayMs?: () => number;
  /** Não carrega fixtures — para testes que montam o próprio cenário. */
  bare?: boolean;
}

export async function makeHarness(opts: HarnessOptions = {}): Promise<Harness> {
  const dir = mkdtempSync(join(tmpdir(), 't30-test-'));
  const dbPath = join(dir, 'test.db');
  const box = await startDevbox({ hookStatus: opts.hookStatus, hookDelayMs: opts.hookDelayMs });
  const app = createApp({
    dbPath,
    smtpHost: '127.0.0.1',
    smtpPort: box.smtpPort,
    allowPrivateWebhooks: true,
    baseUrl: 'http://localhost:3000',
  });

  if (!opts.bare) {
    const fx = await loadFixtures();
    for (const c of fx.categories) {
      app.preferences.setCategory(
        { name: c.name, defaultEnabled: c.defaultEnabled, transactional: c.transactional, retentionDays: c.retentionDays ?? null },
        'fixtures',
      );
    }
    for (const r of fx.recipients) {
      app.preferences.putRecipient({
        id: r.id,
        timezone: r.timezone,
        email: r.email,
        webhookUrl: r.webhook ? `http://127.0.0.1:${box.hookPort}/hook` : null,
        webhookSecret: r.webhook ? `segredo-${r.id}` : null,
        quietStart: r.quietStart,
        quietEnd: r.quietEnd,
      });
    }
  }

  return {
    app,
    box,
    dbPath,
    async stop() {
      app.close();
      await box.stop();
    },
  };
}

/**
 * Decodifica quoted-printable. Sem isto, um teste sobre o CONTEÚDO da mensagem
 * acabaria testando o encoding do transporte: "não" vira "n=C3=A3o" e pode ser
 * partido ao meio por uma quebra suave.
 */
export function decodeQuotedPrintable(raw: string): string {
  const unfolded = raw.replace(/=\r?\n/g, ''); // quebras suaves
  const bytes: number[] = [];
  for (let i = 0; i < unfolded.length; i++) {
    if (unfolded[i] === '=' && /^[0-9A-F]{2}$/i.test(unfolded.slice(i + 1, i + 3))) {
      bytes.push(parseInt(unfolded.slice(i + 1, i + 3), 16));
      i += 2;
    } else {
      bytes.push(unfolded.charCodeAt(i));
    }
  }
  // Os bytes escapados são UTF-8: decodificar byte a byte com fromCharCode daria
  // "Ã£" em vez de "ã". Passar pelo Buffer é o que restitui o caractere.
  return Buffer.from(bytes).toString('utf8');
}

/** Instante UTC correspondente a uma hora local num fuso — para testar janelas. */
export function utcForLocalHour(tz: string, hour: number, minute = 0, dayOffset = 0): number {
  const base = new Date(Date.UTC(2026, 7, 15 + dayOffset, 12, 0, 0));
  // Descobre o deslocamento do fuso naquele dia e corrige.
  const local = new Intl.DateTimeFormat('en-GB', {
    timeZone: tz,
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).formatToParts(base);
  const lh = Number(local.find((p) => p.type === 'hour')!.value) % 24;
  const lm = Number(local.find((p) => p.type === 'minute')!.value);
  const deltaMinutes = hour * 60 + minute - (lh * 60 + lm);
  return base.getTime() + deltaMinutes * 60_000;
}
