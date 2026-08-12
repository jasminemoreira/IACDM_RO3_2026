/**
 * Estágio de entrega — tabela-verdade D-1..D-5 e S-1..S-5.
 * UC-2, UC-5, UC-6, UC-7, REG-02, CTL-02, EDGE-3, EDGE-4, PAR-01, PAR-17.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { decodeQuotedPrintable, makeHarness, utcForLocalHour } from './helpers.ts';
import { fullJitterDelay, PAR_02_BACKOFF_BASE_MS, PAR_03_BACKOFF_CAP_MS } from '../src/delivery-policy/index.ts';
import { PAR_12_CAPACITY } from '../src/rate-limiter/index.ts';

const payload = { subject: 'Assunto', body: 'Corpo' };

/** Roda ticks até a fila devida esvaziar (o lote é limitado a PAR-19). */
async function drain(h: Awaited<ReturnType<typeof makeHarness>>, now: number, maxTicks = 10) {
  let total = { claimed: 0, sent: 0, suppressed: 0, deferred: 0, failed: 0, deadLettered: 0 };
  for (let i = 0; i < maxTicks; i++) {
    const r = await h.app.worker.tick(now);
    for (const k of Object.keys(total) as Array<keyof typeof total>) total[k] += r[k];
    if (r.claimed === 0) break;
  }
  return total;
}

test('D-1 / UC-1: entrega nos dois canais com estados terminais DISTINTOS', async (t) => {
  const h = await makeHarness();
  t.after(() => h.stop());

  const r = h.app.ingestion.ingest({ recipientId: 'fabio', category: 'billing', payload }, 'cobranca');
  await drain(h, h.app.store.now());

  const ds = h.app.outbox.history(r.notificationId);
  const email = ds.find((d) => d.channel === 'email')!;
  const webhook = ds.find((d) => d.channel === 'webhook')!;

  assert.equal(email.status, 'sent', 'e-mail: só sabemos que o provedor aceitou a submissão');
  assert.equal(webhook.status, 'delivered', 'webhook: 2xx é confirmação do destino');
  assert.equal(h.box.mailbox.length, 1);
  assert.equal(h.box.received.length, 1);
});

test('D-3 / UC-2: notificação na madrugada é ADIADA até a abertura, não descartada', async (t) => {
  const h = await makeHarness();
  t.after(() => h.stop());

  const r = h.app.ingestion.ingest({ recipientId: 'ana', category: 'billing', payload }, 'cobranca');
  const madrugada = utcForLocalHour('America/Sao_Paulo', 2, 0);

  const res = await h.app.worker.tick(madrugada);
  assert.equal(res.deferred, 2, 'as duas entregas foram adiadas');
  assert.equal(res.sent, 0);

  const ds = h.app.outbox.history(r.notificationId);
  for (const d of ds) {
    assert.equal(d.status, 'pending', 'adiar não é suprimir — a entrega continua viva');
    assert.ok(d.nextAttemptAt > madrugada, 'reprogramada para o futuro');
    // Abre às 08:00 + jitter de PAR-25 (limitado a 10% da janela de 10h = 5 min).
    const abertura = utcForLocalHour('America/Sao_Paulo', 8, 0);
    assert.ok(d.nextAttemptAt >= abertura, 'não sai antes da abertura');
    assert.ok(d.nextAttemptAt <= abertura + 5 * 60_000 + 1000, 'jitter de PAR-25 dentro do teto');
  }
});

test('D-5 / UC-7: transacional na madrugada, com opt-out e teto zerado, é ENTREGUE', async (t) => {
  const h = await makeHarness();
  t.after(() => h.stop());

  h.app.preferences.optOut('ana', { category: 'security', channel: 'email' }, 'ana');
  h.app.preferences.optOut('ana', { category: 'security', channel: 'webhook' }, 'ana');
  h.app.store.recipients.updateBucket('ana', 0, h.app.store.now()); // teto esgotado

  const r = h.app.ingestion.ingest({ recipientId: 'ana', category: 'security', payload }, 'seguranca');
  const madrugada = utcForLocalHour('America/Sao_Paulo', 3, 0);
  const res = await h.app.worker.tick(madrugada);

  assert.equal(res.sent, 2, 'ignora opt_out, quiet_hours e rate_limited');
  const ds = h.app.outbox.history(r.notificationId);
  assert.ok(ds.every((d) => d.status === 'sent' || d.status === 'delivered'));
});

test('D-4 / UC-5: 15 notificações em 1 h — 10 entregues, 5 suprimidas por rate_limited', async (t) => {
  const h = await makeHarness();
  t.after(() => h.stop());

  // bruno só tem e-mail: 15 notificações = 15 entregas, direto contra o teto de 10.
  const ids: string[] = [];
  for (let i = 0; i < 15; i++) {
    ids.push(h.app.ingestion.ingest({ recipientId: 'bruno', category: 'billing', dedupKey: `k-${i}`, payload }, 'cobranca').notificationId);
  }
  const now = h.app.store.now();
  const res = await drain(h, now, 20);

  assert.equal(res.sent, PAR_12_CAPACITY, 'exatamente a capacidade do balde');
  assert.equal(res.suppressed, 15 - PAR_12_CAPACITY, 'o excedente é SUPRIMIDO, nunca agrupado');

  const suprimidas = ids
    .flatMap((id) => h.app.outbox.history(id))
    .filter((d) => d.status === 'suppressed');
  assert.equal(suprimidas.length, 5);
  assert.ok(suprimidas.every((d) => d.suppressedReason === 'rate_limited'));
  // GOV-02: o motivo carrega o valor do parâmetro vigente na decisão.
  assert.ok(suprimidas.every((d) => d.suppressedDetail === 'cap=10/1h'), 'o histórico registra a regra vigente');
});

test('D-2 / REG-02 (negativo): opt-out DEPOIS do enfileiramento impede a entrega', async (t) => {
  const h = await makeHarness();
  t.after(() => h.stop());

  const r = h.app.ingestion.ingest({ recipientId: 'fabio', category: 'billing', payload }, 'cobranca');
  // A pessoa se descadastra enquanto a entrega já está na fila.
  h.app.preferences.optOut('fabio', { category: 'billing', channel: 'email' }, 'fabio');
  h.app.preferences.optOut('fabio', { category: 'billing', channel: 'webhook' }, 'fabio');

  await drain(h, h.app.store.now());
  const ds = h.app.outbox.history(r.notificationId);
  assert.ok(ds.every((d) => d.status === 'suppressed'), 'a entrega já materializada não sai');
  assert.ok(ds.every((d) => d.suppressedReason === 'opt_out'));
  assert.equal(h.box.mailbox.length, 0, 'nenhum e-mail chegou a ser submetido');
});

test('S-3 / UC-6: 500 do destino reprograma com backoff dentro do teto de PAR-01', async (t) => {
  const h = await makeHarness({ hookStatus: () => 500 });
  t.after(() => h.stop());

  const r = h.app.ingestion.ingest({ recipientId: 'carla', category: 'billing', payload }, 'cobranca');
  const now = h.app.store.now();
  const res = await h.app.worker.tick(now);

  assert.equal(res.failed, 1);
  const [d] = h.app.outbox.history(r.notificationId);
  assert.equal(d.status, 'pending', 'falha transitória volta para a fila');
  assert.equal(d.attempts, 1, 'attempts foi incrementado na reivindicação');
  assert.ok(d.nextAttemptAt >= now, 'reprogramada');
  assert.ok(d.nextAttemptAt <= now + PAR_02_BACKOFF_BASE_MS, 'primeira espera no máximo base=5s (Full Jitter)');
  assert.match(d.attemptLog[0].detail, /HTTP 500/);
});

test('S-4 / UC-6: esgotar PAR-04 leva a dead_letter e para de tentar', async (t) => {
  const h = await makeHarness({ hookStatus: () => 503 });
  t.after(() => h.stop());

  const r = h.app.ingestion.ingest({ recipientId: 'carla', category: 'billing', payload }, 'cobranca');
  let now = h.app.store.now();
  for (let i = 0; i < 6; i++) {
    await h.app.worker.tick(now);
    now += PAR_03_BACKOFF_CAP_MS; // avança além de qualquer backoff possível
  }

  const [d] = h.app.outbox.history(r.notificationId);
  assert.equal(d.status, 'dead_letter');
  assert.equal(d.attempts, 5, 'exatamente PAR-04 tentativas');

  const antes = h.box.received.length;
  await h.app.worker.tick(now);
  assert.equal(h.box.received.length, antes, 'dead_letter não é reivindicada de novo');
});

test('S-2 / EDGE-3 (negativo): falha PERMANENTE não consome 5 tentativas', async (t) => {
  const h = await makeHarness();
  t.after(() => h.stop());

  h.app.preferences.putRecipient({
    id: 'carla',
    timezone: 'Europe/Lisbon',
    email: null,
    webhookUrl: 'http://host-que-nao-existe.invalid/hook',
    webhookSecret: 'x',
    quietStart: 0,
    quietEnd: 0,
  });

  const r = h.app.ingestion.ingest({ recipientId: 'carla', category: 'billing', payload }, 'cobranca');
  await h.app.worker.tick(h.app.store.now());

  const [d] = h.app.outbox.history(r.notificationId);
  assert.equal(d.status, 'dead_letter', 'host inexistente é definitivo');
  assert.equal(d.attempts, 1, 'uma tentativa só — não adianta insistir contra o que nunca existiu');
});

test('EDGE-4 (negativo): abort do worker é falha TRANSITÓRIA, não permanente', async (t) => {
  const h = await makeHarness({ hookDelayMs: () => 5_000 });
  t.after(() => h.stop());

  const recipient = h.app.preferences.recipient('carla')!;
  const controller = new AbortController();
  setTimeout(() => controller.abort(), 150).unref?.();

  const res = await h.app.channels.webhook.send(
    {
      deliveryId: 'd1',
      notificationId: 'n1',
      recipient,
      category: 'billing',
      transactional: false,
      payload,
      now: Date.now(),
    },
    controller.signal,
  );

  assert.equal(res.accepted, false);
  assert.equal(res.permanent, false, 'timeout/abort precisa ser retentável');
});

test('CTL-02 (negativo): relógio retrocedendo NÃO reduz os tokens do balde', async (t) => {
  const h = await makeHarness();
  t.after(() => h.stop());

  const now = h.app.store.now();
  h.app.store.recipients.updateBucket('fabio', 5, now);

  const antes = h.app.preferences.recipient('fabio')!.tokens;
  // Consulta com relógio 1 h no passado: `elapsed` seria negativo.
  const r = h.app.ingestion.ingest({ recipientId: 'fabio', category: 'billing', payload }, 'x');
  await h.app.worker.tick(now - 3_600_000);

  const depois = h.app.preferences.recipient('fabio')!.tokens;
  assert.ok(depois <= antes, 'consumo normal reduz');
  assert.ok(depois >= antes - 2, 'mas o retrocesso do relógio não subtrai tempo negativo do balde');
  assert.ok(r.notificationId);
});

test('PAR-01: Full Jitter respeita 0 <= sleep < min(cap, base * 2^n)', () => {
  for (let attempts = 1; attempts <= 6; attempts++) {
    const teto = Math.min(PAR_03_BACKOFF_CAP_MS, PAR_02_BACKOFF_BASE_MS * 2 ** (attempts - 1));
    for (let i = 0; i < 200; i++) {
      const s = fullJitterDelay(attempts);
      assert.ok(s >= 0, 'nunca negativo');
      assert.ok(s < teto || teto === 0, `sleep ${s} abaixo do teto ${teto}`);
    }
  }
  // Sempre 0 na borda inferior do gerador, sempre abaixo do teto na superior.
  assert.equal(fullJitterDelay(1, () => 0), 0);
  assert.equal(fullJitterDelay(1, () => 0.999999), Math.floor(0.999999 * PAR_02_BACKOFF_BASE_MS));
});

test('PAR-17: headers do RFC 8058 na mensagem normal, AUSENTES na transacional', async (t) => {
  const h = await makeHarness();
  t.after(() => h.stop());

  h.app.ingestion.ingest({ recipientId: 'bruno', category: 'billing', payload }, 'cobranca');
  await drain(h, h.app.store.now());
  const normal = h.box.mailbox.at(-1)!.raw;
  // \s* porque o RFC 5322 permite dobrar headers longos, e o nodemailer dobra.
  // O critério do RFC 8058 é o campo existir com um URI, não caber numa linha.
  assert.match(normal, /List-Unsubscribe:\s*<https?:/i);
  assert.match(normal, /List-Unsubscribe-Post: List-Unsubscribe=One-Click/i, 'valor literal, sem variação');

  h.app.ingestion.ingest({ recipientId: 'bruno', category: 'security', payload }, 'seguranca');
  await drain(h, h.app.store.now());
  const transacional = h.box.mailbox.at(-1)!.raw;
  assert.doesNotMatch(transacional, /List-Unsubscribe:/i, 'oferecer descadastro que não desliga nada seria promessa falsa');
  assert.match(
    decodeQuotedPrintable(transacional),
    /não pode ser desativada/i,
    'em vez disso, explica por que ela recebe',
  );
});
