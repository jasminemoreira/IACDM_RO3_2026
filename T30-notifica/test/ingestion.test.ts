/**
 * Estágio de ingresso — tabela-verdade I-1..I-8.
 * UC-3 (opt-out), UC-4 (dedup), UC-7/EDGE-7 (transacional × dedup),
 * EDGE-6 e EDGE-13 (idempotência).
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { makeHarness } from './helpers.ts';
import { IngestError } from '../src/ingestion/index.ts';

const payload = { subject: 'Assunto', body: 'Corpo' };

test('I-1 / UC-1: notificação normal materializa uma entrega por canal habilitado', async (t) => {
  const h = await makeHarness();
  t.after(() => h.stop());

  const r = h.app.ingestion.ingest({ recipientId: 'ana', category: 'billing', payload }, 'cobranca');
  assert.equal(r.status, 'accepted');
  assert.deepEqual(r.channels.sort(), ['email', 'webhook'], 'ana tem os dois endereços');
});

test('I-2 / UC-3: opt-out em todos os canais suprime no ingresso com motivo nomeado', async (t) => {
  const h = await makeHarness();
  t.after(() => h.stop());

  h.app.preferences.optOut('ana', { category: 'billing', channel: 'email' }, 'ana');
  h.app.preferences.optOut('ana', { category: 'billing', channel: 'webhook' }, 'ana');

  const r = h.app.ingestion.ingest({ recipientId: 'ana', category: 'billing', payload }, 'cobranca');
  assert.equal(r.status, 'suppressed');
  assert.equal(r.reason, 'opt_out');
  assert.deepEqual(r.channels, [], 'nenhuma entrega materializada');
});

test('UC-3 (negativo): opt-out numa categoria não afeta as outras', async (t) => {
  const h = await makeHarness();
  t.after(() => h.stop());

  h.app.preferences.optOut('ana', { category: 'marketing' }, 'ana');
  const marketing = h.app.ingestion.ingest({ recipientId: 'ana', category: 'marketing', payload }, 'mkt');
  const billing = h.app.ingestion.ingest({ recipientId: 'ana', category: 'billing', payload }, 'cobranca');

  assert.equal(marketing.status, 'suppressed');
  assert.equal(billing.status, 'accepted', 'billing continua fluindo');
});

test('EDGE-5: preferência ausente resolve pelo PADRÃO da categoria, não como opt-out', async (t) => {
  const h = await makeHarness();
  t.after(() => h.stop());

  // fabio nunca declarou preferência alguma.
  const billing = h.app.ingestion.ingest({ recipientId: 'fabio', category: 'billing', payload }, 'cobranca');
  assert.equal(billing.status, 'accepted', 'billing tem defaultEnabled=true');

  const marketing = h.app.ingestion.ingest({ recipientId: 'fabio', category: 'marketing', payload }, 'mkt');
  assert.equal(marketing.status, 'suppressed', 'marketing tem defaultEnabled=false');
  assert.equal(marketing.reason, 'opt_out');
});

test('I-3 / UC-4: mesma chave lógica dentro de PAR-05 é deduplicada', async (t) => {
  const h = await makeHarness();
  t.after(() => h.stop());

  const first = h.app.ingestion.ingest({ recipientId: 'ana', category: 'billing', dedupKey: 'f-1', payload }, 'cobranca');
  const second = h.app.ingestion.ingest({ recipientId: 'ana', category: 'billing', dedupKey: 'f-1', payload }, 'cobranca');

  assert.equal(first.status, 'accepted');
  assert.equal(second.status, 'suppressed');
  assert.equal(second.reason, 'duplicate');
  assert.match(second.detail!, /original=/, 'o motivo aponta qual notificação era a original');
});

test('UC-4 (negativo): chaves de dedup diferentes não colapsam', async (t) => {
  const h = await makeHarness();
  t.after(() => h.stop());

  const a = h.app.ingestion.ingest({ recipientId: 'ana', category: 'billing', dedupKey: 'f-1', payload }, 'cobranca');
  const b = h.app.ingestion.ingest({ recipientId: 'ana', category: 'billing', dedupKey: 'f-2', payload }, 'cobranca');
  assert.equal(a.status, 'accepted');
  assert.equal(b.status, 'accepted');
});

test('I-4 / UC-7: transacional ignora o opt-out no ingresso', async (t) => {
  const h = await makeHarness();
  t.after(() => h.stop());

  h.app.preferences.optOut('ana', { category: 'security', channel: 'email' }, 'ana');
  h.app.preferences.optOut('ana', { category: 'security', channel: 'webhook' }, 'ana');

  const r = h.app.ingestion.ingest({ recipientId: 'ana', category: 'security', payload }, 'seguranca');
  assert.equal(r.status, 'accepted', 'security é transacional no catálogo');
  assert.equal(r.channels.length, 2, 'entrega materializada mesmo com opt-out');
});

test('I-5 / EDGE-7 (negativo): transacional NÃO ignora deduplicação', async (t) => {
  const h = await makeHarness();
  t.after(() => h.stop());

  const first = h.app.ingestion.ingest({ recipientId: 'ana', category: 'security', dedupKey: '2fa-1', payload }, 'seg');
  const second = h.app.ingestion.ingest({ recipientId: 'ana', category: 'security', dedupKey: '2fa-1', payload }, 'seg');

  assert.equal(first.status, 'accepted');
  assert.equal(second.status, 'suppressed', 'a única regra que transacional não pula');
  assert.equal(second.reason, 'duplicate');
});

test('I-6 / EDGE-6: mesma Idempotency-Key com o MESMO corpo devolve a mesma notificação', async (t) => {
  const h = await makeHarness();
  t.after(() => h.stop());

  const a = h.app.ingestion.ingest({ recipientId: 'ana', category: 'billing', payload }, 'cobranca', 'k-1');
  const b = h.app.ingestion.ingest({ recipientId: 'ana', category: 'billing', payload }, 'cobranca', 'k-1');

  assert.equal(b.notificationId, a.notificationId);
  assert.equal(b.replayed, true);
  assert.notEqual(a.replayed, true, 'a primeira não é replay');
});

test('I-7 / EDGE-6 (negativo): mesma Idempotency-Key com corpo diferente é erro, não silêncio', async (t) => {
  const h = await makeHarness();
  t.after(() => h.stop());

  h.app.ingestion.ingest({ recipientId: 'ana', category: 'billing', payload }, 'cobranca', 'k-2');
  assert.throws(
    () => h.app.ingestion.ingest({ recipientId: 'ana', category: 'billing', payload: { subject: 'Outro', body: 'x' } }, 'cobranca', 'k-2'),
    (err: unknown) => err instanceof IngestError && err.code === 'idempotency_conflict',
  );
});

test('I-8 / EDGE-13 (negativo): a chave de idempotência é escopada por EMISSOR', async (t) => {
  const h = await makeHarness();
  t.after(() => h.stop());

  const a = h.app.ingestion.ingest({ recipientId: 'ana', category: 'billing', payload }, 'emissor-A', 'mesma-chave');
  const b = h.app.ingestion.ingest({ recipientId: 'ana', category: 'billing', payload }, 'emissor-B', 'mesma-chave');

  assert.notEqual(a.notificationId, b.notificationId, 'dois emissores não colidem');
  assert.notEqual(b.replayed, true, 'o emissor B não recebe a resposta do A');
});

test('UC-1 (negativo): destinatário sem nenhum endereço de canal é recusado', async (t) => {
  const h = await makeHarness();
  t.after(() => h.stop());

  h.app.preferences.putRecipient({ id: 'sem-canal', timezone: 'UTC', email: null, webhookUrl: null });
  assert.throws(
    () => h.app.ingestion.ingest({ recipientId: 'sem-canal', category: 'billing', payload }, 'x'),
    (err: unknown) => err instanceof IngestError && err.code === 'no_channel',
  );
});

test('SEC-06 (negativo): payload acima de PAR-26 é recusado', async (t) => {
  const h = await makeHarness();
  t.after(() => h.stop());

  assert.throws(
    () => h.app.ingestion.ingest({ recipientId: 'ana', category: 'billing', payload: { subject: 's', body: 'x'.repeat(70 * 1024) } }, 'x'),
    (err: unknown) => err instanceof IngestError && err.code === 'payload_too_large',
  );
});

test('GOV-01: a notificação registra QUAL emissor a criou', async (t) => {
  const h = await makeHarness();
  t.after(() => h.stop());

  const r = h.app.ingestion.ingest({ recipientId: 'ana', category: 'billing', payload }, 'sistema-de-cobranca');
  const n = h.app.store.notifications.get(r.notificationId)!;
  assert.equal(n.issuer, 'sistema-de-cobranca');
});

test('R-06: notificação e entregas são gravadas na MESMA transação', async (t) => {
  const h = await makeHarness();
  t.after(() => h.stop());

  const r = h.app.ingestion.ingest({ recipientId: 'ana', category: 'billing', payload }, 'cobranca');
  const deliveries = h.app.outbox.history(r.notificationId);
  assert.equal(deliveries.length, 2, 'as entregas já existem assim que a notificação existe');
  assert.ok(deliveries.every((d) => d.status === 'pending'));
});
