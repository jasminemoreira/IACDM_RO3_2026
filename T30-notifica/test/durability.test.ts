/**
 * AC-4 — PROVA DE DURABILIDADE.
 *
 * É o critério que justifica a escolha de SQLite + transactional outbox: sem
 * ele, a durabilidade fica AFIRMADA e não demonstrada, e a lente Resiliência da
 * Fase 2 teria razão em atacar.
 *
 * O teste mata um processo de verdade, com SIGKILL, no pior instante: depois de
 * reivindicar a entrega e antes de registrar o resultado.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { makeHarness } from './helpers.ts';
import { PAR_20_LEASE_MS } from '../src/outbox/index.ts';

const CHILD = fileURLToPath(new URL('../tools/worker-child.ts', import.meta.url));
const payload = { subject: 'Fatura', body: 'Vence hoje' };

test('AC-4: matar o processo (SIGKILL) com entrega pendente — a entrega retoma e conclui', async (t) => {
  const h = await makeHarness();
  t.after(() => h.stop());

  const r = h.app.ingestion.ingest({ recipientId: 'carla', category: 'billing', payload }, 'cobranca');
  const antes = h.app.outbox.history(r.notificationId)[0];
  assert.equal(antes.status, 'pending');
  assert.equal(antes.attempts, 0);

  // --- um processo SEPARADO toma a entrega e morre ---------------------------
  const child = spawn(
    process.execPath,
    ['--disable-warning=ExperimentalWarning', CHILD, h.dbPath, String(h.box.smtpPort), String(h.box.hookPort)],
    { stdio: ['ignore', 'pipe', 'inherit'] },
  );

  const claimed = await new Promise<number>((resolve, reject) => {
    let buf = '';
    const timer = setTimeout(() => reject(new Error('filho não reivindicou a tempo')), 20_000);
    child.stdout.on('data', (chunk) => {
      buf += String(chunk);
      const m = buf.match(/CLAIMED (\d+)/);
      if (m) {
        clearTimeout(timer);
        resolve(Number(m[1]));
      }
    });
    child.on('exit', (code) => {
      clearTimeout(timer);
      reject(new Error(`filho saiu antes de reivindicar (código ${code})`));
    });
  });
  assert.equal(claimed, 1, 'o outro processo reivindicou a entrega');

  child.kill('SIGKILL'); // sem finally, sem cleanup, sem gravar resultado
  // Um listener de 'exit' registrado DEPOIS da saída nunca dispara — daí a checagem.
  if (child.exitCode === null && child.signalCode === null) {
    await new Promise((resolve) => child.on('exit', resolve));
  }

  // --- o que sobrou no disco ------------------------------------------------
  const orfa = h.app.store.deliveries.get(antes.id)!;
  assert.equal(orfa.status, 'pending', 'não foi perdida');
  assert.equal(orfa.attempts, 1, 'a tentativa do processo morto está contabilizada — é o que a leva a PAR-04');
  assert.ok(orfa.leaseUntil !== null, 'ficou com lease de um dono que não existe mais');
  assert.equal(h.box.received.length, 0, 'nada foi entregue antes da morte');

  // Enquanto o lease vale, o novo worker respeita o dono anterior.
  const durante = await h.app.worker.tick(h.app.store.now());
  assert.equal(durante.claimed, 0, 'sem roubo de entrega dentro do lease');

  // --- expirado o lease, a entrega volta e conclui ---------------------------
  const depoisDoLease = h.app.store.now() + PAR_20_LEASE_MS + 1;
  const retomada = await h.app.worker.tick(depoisDoLease);

  assert.equal(retomada.claimed, 1, 'a entrega retomou sozinha após a expiração do lease');
  assert.equal(retomada.sent, 1);

  const final = h.app.store.deliveries.get(antes.id)!;
  assert.equal(final.status, 'delivered', 'concluída apesar da morte do processo anterior');
  assert.equal(final.attempts, 2, 'a tentativa perdida foi contada, a segunda venceu');
  assert.equal(h.box.received.length, 1, 'o destino recebeu exatamente uma vez');
});

test('AC-4 (negativo): o estado sobrevive ao fechamento e reabertura do banco', async (t) => {
  const h = await makeHarness();
  t.after(() => h.stop());

  const r = h.app.ingestion.ingest({ recipientId: 'carla', category: 'billing', payload }, 'cobranca');

  // Abre o MESMO arquivo com uma instância independente — o WAL permite, e é o
  // que prova que o estado está no disco e não na memória do processo. Fechar o
  // store do harness aqui causaria duplo close do mesmo handle no hook after.
  const { openStore } = await import('../src/store/index.ts');
  const store2 = openStore(h.dbPath);
  const d = store2.deliveries.listByNotification(r.notificationId);
  assert.equal(d.length, 1, 'a entrega existe para quem abre o arquivo do zero');
  assert.equal(d[0].status, 'pending');
  assert.equal(store2.notifications.get(r.notificationId)!.issuer, 'cobranca', 'a notificação também');
  store2.close();
});
