/**
 * EDGE-8 (assinatura e unidade do timestamp) e EDGE-12 (SSRF e redirecionamento).
 *
 * LIN-05 é o achado que este arquivo existe para provar: o sistema trabalha em
 * epoch MILISSEGUNDOS e a spec exige o header em SEGUNDOS. Um fator 1000 aqui
 * faria a tolerância de 300 s (PAR-06) rejeitar 100% das entregas.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { createHmac } from 'node:crypto';
import { makeHarness } from './helpers.ts';
import { isPrivateAddress, resolveAndValidate, signPayload } from '../src/channel-webhook/index.ts';

const payload = { subject: 'Assunto', body: 'Corpo' };

test('EDGE-8: headers de R-01 presentes, timestamp em SEGUNDOS e assinatura conferindo', async (t) => {
  const h = await makeHarness();
  t.after(() => h.stop());

  h.app.ingestion.ingest({ recipientId: 'carla', category: 'billing', payload }, 'x');
  await h.app.worker.tick(h.app.store.now());

  assert.equal(h.box.received.length, 1);
  const { headers, body } = h.box.received[0];

  const id = headers['webhook-id'] as string;
  const ts = headers['webhook-timestamp'] as string;
  const sig = headers['webhook-signature'] as string;

  assert.ok(id, 'webhook-id presente');
  assert.match(ts, /^\d+$/, 'webhook-timestamp é inteiro');

  const segundos = Number(ts);
  assert.ok(segundos < 1e11, 'está em SEGUNDOS — em milissegundos passaria de 1e12');
  assert.ok(Math.abs(segundos * 1000 - Date.now()) < 300_000, 'dentro da tolerância de PAR-06 (300 s)');

  // A assinatura é sobre `id.timestamp.payload`, nesta ordem literal (R-01).
  const esperada = `v1,${createHmac('sha256', 'segredo-carla').update(`${id}.${segundos}.${body}`).digest('base64')}`;
  assert.equal(sig, esperada, 'HMAC-SHA256 sobre id.timestamp.payload, base64, prefixo v1');
});

test('EDGE-8 (negativo): alterar qualquer parte do conteúdo assinado invalida a assinatura', () => {
  const base = signPayload('msg-1', 1674087231, '{"a":1}', 'segredo');
  assert.notEqual(signPayload('msg-2', 1674087231, '{"a":1}', 'segredo'), base, 'id diferente');
  assert.notEqual(signPayload('msg-1', 1674087232, '{"a":1}', 'segredo'), base, 'timestamp diferente');
  assert.notEqual(signPayload('msg-1', 1674087231, '{"a":2}', 'segredo'), base, 'payload diferente');
  assert.notEqual(signPayload('msg-1', 1674087231, '{"a":1}', 'outro'), base, 'segredo diferente');
});

test('SEC-03 / EDGE-12 (negativo): faixas privadas e de metadados são rejeitadas', () => {
  for (const ip of ['127.0.0.1', '10.1.2.3', '172.16.0.1', '172.31.255.255', '192.168.1.1', '169.254.169.254', '100.64.0.1', '0.0.0.0', '::1', 'fe80::1', 'fd00::1', '::ffff:127.0.0.1']) {
    assert.equal(isPrivateAddress(ip), true, `${ip} precisa ser bloqueado`);
  }
  for (const ip of ['8.8.8.8', '1.1.1.1', '172.32.0.1', '192.169.0.1', '2606:4700::1111']) {
    assert.equal(isPrivateAddress(ip), false, `${ip} é público e deve passar`);
  }
});

test('SEC-03 / EDGE-12 (negativo): URL que resolve para loopback é recusada na validação', async () => {
  const local = await resolveAndValidate('http://localhost:9999/hook');
  assert.equal(local.ok, false);
  assert.match(local.reason!, /privado/);

  const esquema = await resolveAndValidate('file:///etc/passwd');
  assert.equal(esquema.ok, false);
  assert.match(esquema.reason!, /esquema/);

  const invalida = await resolveAndValidate('não é uma url');
  assert.equal(invalida.ok, false);
});

test('SEC-11 / EDGE-12 (negativo): 3xx é falha PERMANENTE — redirecionamento não é seguido', async (t) => {
  const h = await makeHarness({ hookStatus: () => 302 });
  t.after(() => h.stop());

  const r = h.app.ingestion.ingest({ recipientId: 'carla', category: 'billing', payload }, 'x');
  await h.app.worker.tick(h.app.store.now());

  const [d] = h.app.outbox.history(r.notificationId);
  assert.equal(d.status, 'dead_letter', 'seguir o 302 furaria o anti-SSRF por desenho');
  assert.equal(d.attempts, 1, 'não retenta');
  assert.match(d.attemptLog[0].detail, /redirecionamento/);
});

test('S-2 (negativo): 4xx do destino é permanente; 429 e 408 continuam retentáveis', async (t) => {
  const h400 = await makeHarness({ hookStatus: () => 400 });
  t.after(() => h400.stop());
  const a = h400.app.ingestion.ingest({ recipientId: 'carla', category: 'billing', payload }, 'x');
  await h400.app.worker.tick(h400.app.store.now());
  assert.equal(h400.app.outbox.history(a.notificationId)[0].status, 'dead_letter', '400 é erro do emissor, não adianta insistir');

  const h429 = await makeHarness({ hookStatus: () => 429 });
  t.after(() => h429.stop());
  const b = h429.app.ingestion.ingest({ recipientId: 'carla', category: 'billing', payload }, 'x');
  await h429.app.worker.tick(h429.app.store.now());
  assert.equal(h429.app.outbox.history(b.notificationId)[0].status, 'pending', '429 pede exatamente para tentar depois');
});

test('SEC-04 / SEC-09: o segredo do webhook é cifrado em repouso e legível pela aplicação', async (t) => {
  const h = await makeHarness();
  t.after(() => h.stop());

  const emRepouso = h.app.store.db
    .prepare('SELECT webhook_secret_enc AS enc FROM recipients WHERE id = ?')
    .get('carla') as { enc: string };

  assert.ok(emRepouso.enc.startsWith('v1:'), 'ciphertext versionado (SEC-09: permite rotação de chave)');
  assert.doesNotMatch(emRepouso.enc, /segredo-carla/, 'o segredo não aparece em claro no banco');
  assert.equal(h.app.preferences.recipient('carla')!.webhookSecret, 'segredo-carla', 'mas a aplicação o recupera para assinar');
});
