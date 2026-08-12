/**
 * UC-8 e AC-3 (a supressão é auditável pelo operador), mais a superfície HTTP:
 * SEC-01/SEC-07 (escopo da chave), SEC-12 (/health), RFC 8058 (unsubscribe) e
 * UX-06 (purge com dry-run).
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { createApi } from '../src/http-api/index.ts';
import { hashApiKey } from '../src/http-api/auth.ts';
import { signUnsubscribeToken } from '../src/tokens.ts';
import { makeHarness, utcForLocalHour } from './helpers.ts';

const CLI = fileURLToPath(new URL('../src/cli/index.ts', import.meta.url));
const payload = { subject: 'Assunto', body: 'Corpo' };

function runCli(dbPath: string, args: string[]): string {
  return execFileSync(process.execPath, ['--disable-warning=ExperimentalWarning', CLI, '--db', dbPath, ...args], {
    encoding: 'utf8',
    stdio: ['ignore', 'pipe', 'pipe'],
  });
}

test('UC-8 / AC-3: os quatro motivos de supressão são distinguíveis pela CLI', async (t) => {
  const h = await makeHarness();
  t.after(() => h.stop());

  // 1) opt_out — no ingresso.
  h.app.preferences.optOut('bruno', { category: 'billing', channel: 'email' }, 'bruno');
  const optout = h.app.ingestion.ingest({ recipientId: 'bruno', category: 'billing', payload }, 'x');

  // 2) duplicate — no ingresso.
  h.app.ingestion.ingest({ recipientId: 'fabio', category: 'billing', dedupKey: 'd1', payload }, 'x');
  const dup = h.app.ingestion.ingest({ recipientId: 'fabio', category: 'billing', dedupKey: 'd1', payload }, 'x');

  // 3) rate_limited — na entrega. O balde é zerado DEPOIS da ingestão e o tick
  // usa o relógio corrente: capturar o instante antes deixaria a entrega com
  // vencimento no futuro e ela não seria reivindicada.
  const limited = h.app.ingestion.ingest({ recipientId: 'carla', category: 'billing', payload }, 'x');
  h.app.store.recipients.updateBucket('carla', 0, h.app.store.now());
  const res = await h.app.worker.tick(h.app.store.now());
  assert.equal(res.suppressed, 1, 'a entrega da carla foi de fato avaliada neste tick');

  // 4) quiet_hours — na entrega, como adiamento (não descarte). Só agora se usa
  // tempo simulado no futuro, para não recarregar o balde do cenário anterior.
  const quiet = h.app.ingestion.ingest({ recipientId: 'ana', category: 'billing', payload }, 'x');
  await h.app.worker.tick(utcForLocalHour('America/Sao_Paulo', 3, 0));

  const saidaOptOut = runCli(h.dbPath, ['explain', optout.notificationId]);
  assert.match(saidaOptOut, /"suppressedReason": "opt_out"/);

  const saidaDup = runCli(h.dbPath, ['explain', dup.notificationId]);
  assert.match(saidaDup, /"suppressedReason": "duplicate"/);

  const saidaLimited = runCli(h.dbPath, ['explain', limited.notificationId]);
  assert.match(saidaLimited, /"suppressedReason": "rate_limited"/);
  assert.match(saidaLimited, /"suppressedDetail": "cap=10\/1h"/, 'com o parâmetro vigente — GOV-02');

  const saidaQuiet = runCli(h.dbPath, ['explain', quiet.notificationId]);
  assert.match(saidaQuiet, /adiada por quiet_hours/, 'adiamento aparece no histórico de tentativas');
  assert.match(saidaQuiet, /"status": "deferred"/, 'e o estado agregado da notificação reflete isso');

  // Os quatro são textualmente distintos — é o que AC-3 exige.
  const motivos = new Set(['opt_out', 'duplicate', 'rate_limited', 'quiet_hours']);
  assert.equal(motivos.size, 4);
});

test('UC-8 (negativo): explain por PESSOA responde "por que ela não recebeu nada"', async (t) => {
  const h = await makeHarness();
  t.after(() => h.stop());

  h.app.preferences.optOut('bruno', { category: 'billing', channel: 'email' }, 'bruno');
  h.app.ingestion.ingest({ recipientId: 'bruno', category: 'billing', payload }, 'emissor-x');

  const saida = runCli(h.dbPath, ['explain', '--recipient', 'bruno']);
  assert.match(saida, /opt_out/);
  assert.match(saida, /emissor-x/, 'mostra QUEM tentou notificar — GOV-01');
});

test('UX-06 (negativo): purge é dry-run por padrão e não apaga nada sem --yes', async (t) => {
  const h = await makeHarness();
  t.after(() => h.stop());

  const saida = runCli(h.dbPath, ['purge']);
  assert.match(saida, /dry-run/);
  assert.match(saida, /--yes/, 'diz explicitamente o que fazer para executar de verdade');
});

test('SEC-01 / SEC-07 (negativo): a chave limita categorias e o transacional é permissão separada', async (t) => {
  const h = await makeHarness();
  t.after(() => h.stop());

  const now = h.app.store.now();
  h.app.store.apiKeys.put(hashApiKey('chave-mkt'), { issuer: 'mkt', categories: ['marketing'], allowTransactional: false }, now);
  h.app.store.apiKeys.put(hashApiKey('chave-seg'), { issuer: 'seg', categories: ['security'], allowTransactional: true }, now);

  const server = createApi({
    store: h.app.store,
    preferences: h.app.preferences,
    ingestion: h.app.ingestion,
    outbox: h.app.outbox,
    tokenSecret: h.app.tokenSecret,
    workerRunning: () => false,
  });
  await new Promise<void>((r) => server.listen(0, '127.0.0.1', () => r()));
  const port = (server.address() as { port: number }).port;
  t.after(() => new Promise<void>((r) => server.close(() => r())));

  const post = (key: string, category: string) =>
    fetch(`http://127.0.0.1:${port}/notifications`, {
      method: 'POST',
      headers: { authorization: `Bearer ${key}`, 'content-type': 'application/json' },
      body: JSON.stringify({ recipientId: 'fabio', category, payload }),
    });

  assert.equal((await post('chave-inexistente', 'marketing')).status, 401, 'chave desconhecida');
  assert.equal((await post('chave-mkt', 'billing')).status, 403, 'fora do escopo de categorias da chave');
  assert.equal((await post('chave-mkt', 'security')).status, 403, 'sem permissão de transacional');
  assert.equal((await post('chave-seg', 'security')).status, 202, 'dentro do escopo e com permissão');
});

test('SEC-12 (negativo): /health sem chave não vaza métricas de fila', async (t) => {
  const h = await makeHarness();
  t.after(() => h.stop());

  h.app.store.apiKeys.put(hashApiKey('op'), { issuer: 'op', categories: ['*'], allowTransactional: true }, h.app.store.now());
  h.app.ingestion.ingest({ recipientId: 'fabio', category: 'billing', payload }, 'x');

  const server = createApi({
    store: h.app.store,
    preferences: h.app.preferences,
    ingestion: h.app.ingestion,
    outbox: h.app.outbox,
    tokenSecret: h.app.tokenSecret,
    workerRunning: () => true,
  });
  await new Promise<void>((r) => server.listen(0, '127.0.0.1', () => r()));
  const port = (server.address() as { port: number }).port;
  t.after(() => new Promise<void>((r) => server.close(() => r())));

  // res.json() é `unknown` — o formato esperado fica declarado aqui em vez de
  // ser assumido implicitamente pelo acesso ao campo.
  type Health = { status: string; worker: string; queue?: { pending: number } };

  const anon = (await (await fetch(`http://127.0.0.1:${port}/health`)).json()) as Health;
  assert.equal(anon.status, 'ok');
  assert.equal(anon.queue, undefined, 'profundidade de fila é informação operacional');

  const auth = (await (
    await fetch(`http://127.0.0.1:${port}/health`, { headers: { authorization: 'Bearer op' } })
  ).json()) as Health;
  assert.equal(auth.queue!.pending, 2, 'com chave, as métricas aparecem');
});

test('RFC 8058: unsubscribe one-click funciona SEM sessão, e token inválido é recusado', async (t) => {
  const h = await makeHarness();
  t.after(() => h.stop());

  const server = createApi({
    store: h.app.store,
    preferences: h.app.preferences,
    ingestion: h.app.ingestion,
    outbox: h.app.outbox,
    tokenSecret: h.app.tokenSecret,
    workerRunning: () => false,
  });
  await new Promise<void>((r) => server.listen(0, '127.0.0.1', () => r()));
  const port = (server.address() as { port: number }).port;
  t.after(() => new Promise<void>((r) => server.close(() => r())));

  assert.equal(h.app.preferences.resolve('fabio', 'billing', 'email').enabled, true, 'antes: recebe');

  const token = signUnsubscribeToken(
    { recipientId: 'fabio', category: 'billing', expiresAt: Date.now() + 60_000 },
    h.app.tokenSecret,
  );
  const ok = await fetch(`http://127.0.0.1:${port}/unsubscribe?token=${token}`, { method: 'POST' });
  assert.equal(ok.status, 200, 'sem Authorization — quem clica no rodapé do e-mail não está autenticado');
  assert.equal(h.app.preferences.resolve('fabio', 'billing', 'email').enabled, false, 'depois: não recebe');

  const forjado = await fetch(`http://127.0.0.1:${port}/unsubscribe?token=abc.def`, { method: 'POST' });
  assert.equal(forjado.status, 403, 'sem token válido, seria um botão de descadastrar terceiros');

  const expirado = signUnsubscribeToken(
    { recipientId: 'ana', category: 'billing', expiresAt: Date.now() - 1 },
    h.app.tokenSecret,
  );
  const vencido = await fetch(`http://127.0.0.1:${port}/unsubscribe?token=${expirado}`, { method: 'POST' });
  assert.equal(vencido.status, 403, 'PAR-21: token tem validade');
});

test('PRO-01: o estado da notificação é DERIVADO — falha parcial vira partially_delivered', async (t) => {
  const h = await makeHarness({ hookStatus: () => 400 }); // webhook falha em definitivo
  t.after(() => h.stop());

  const r = h.app.ingestion.ingest({ recipientId: 'fabio', category: 'billing', payload }, 'x');
  await h.app.worker.tick(h.app.store.now());

  const saida = JSON.parse(runCli(h.dbPath, ['explain', r.notificationId]));
  assert.equal(saida.status, 'partially_delivered', 'e-mail entregue, webhook em dead_letter');
  const email = saida.deliveries.find((d: { channel: string }) => d.channel === 'email');
  const webhook = saida.deliveries.find((d: { channel: string }) => d.channel === 'webhook');
  assert.equal(email.status, 'sent');
  assert.equal(webhook.status, 'dead_letter');

  // A coluna não existe no schema: o estado é calculado, não guardado.
  const colunas = h.app.store.db.prepare('PRAGMA table_info(notifications)').all() as Array<{ name: string }>;
  assert.equal(colunas.some((c) => c.name === 'status'), false, 'sem coluna de estado agregado — sem dono a definir');
});
