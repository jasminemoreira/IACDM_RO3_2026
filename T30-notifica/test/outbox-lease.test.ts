/**
 * EDGE-9, EDGE-10 e EDGE-11 — as três travas que fecham RES-05 e RES-06, os dois
 * críticos que a segunda iteração da crítica encontrou NA CORREÇÃO da primeira.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { makeHarness } from './helpers.ts';
import { PAR_19_MAX_IN_FLIGHT, PAR_20_LEASE_MS } from '../src/outbox/index.ts';

const payload = { subject: 'Assunto', body: 'Corpo' };

test('RES-06 / EDGE-9: `attempts` é incrementado NA REIVINDICAÇÃO, não no resultado', async (t) => {
  const h = await makeHarness();
  t.after(() => h.stop());

  const r = h.app.ingestion.ingest({ recipientId: 'carla', category: 'billing', payload }, 'x');
  const now = h.app.store.now();

  const [claimed] = h.app.outbox.claim(now);
  assert.equal(claimed.delivery.attempts, 1, 'a tentativa já conta no momento em que a entrega é tomada');

  // Simula o processo morrendo aqui: nada de recordResult.
  const antes = h.app.store.deliveries.get(claimed.delivery.id)!;
  assert.equal(antes.status, 'pending');
  assert.equal(antes.attempts, 1, 'o incremento está PERSISTIDO, não só no objeto em memória');
  assert.ok(antes.leaseUntil! > now, 'lease em vigor');

  // Enquanto o lease vale, ninguém mais a reivindica.
  assert.equal(h.app.outbox.claim(now).length, 0, 'lease impede reivindicação concorrente');

  // Expirado o lease, ela volta — e a tentativa seguinte é a 2ª, não a 1ª.
  const depois = h.app.outbox.claim(now + PAR_20_LEASE_MS + 1);
  assert.equal(depois.length, 1, 'a entrega não ficou presa para sempre');
  assert.equal(depois[0].delivery.attempts, 2, 'caminha para PAR-04 em vez de reprocessar eternamente');
  assert.ok(r.notificationId);
});

test('RES-06 (negativo): entrega envenenada alcança dead_letter em vez de girar para sempre', async (t) => {
  const h = await makeHarness();
  t.after(() => h.stop());

  const r = h.app.ingestion.ingest({ recipientId: 'carla', category: 'billing', payload }, 'x');
  let now = h.app.store.now();

  // Cinco reivindicações sem NENHUM resultado registrado — o cenário exato de um
  // processo que morre no meio, repetidamente.
  for (let i = 0; i < 5; i++) {
    const c = h.app.outbox.claim(now);
    assert.equal(c.length, 1);
    now += PAR_20_LEASE_MS + 1;
  }

  const d = h.app.outbox.history(r.notificationId)[0];
  assert.equal(d.attempts, 5, 'as cinco tentativas foram contadas');

  // Na próxima passada do worker, a política manda para dead-letter.
  const c = h.app.outbox.claim(now);
  const decisao = h.app.policy.nextAttempt(c[0].delivery.attempts, now);
  assert.ok('deadLetter' in decisao, 'PAR-04 esgotado — a entrega para de girar');
});

test('RES-05 / EDGE-11 (negativo): escrita com fencing token vencido é REJEITADA', async (t) => {
  const h = await makeHarness();
  t.after(() => h.stop());

  const r = h.app.ingestion.ingest({ recipientId: 'carla', category: 'billing', payload }, 'x');
  const now = h.app.store.now();

  const [primeiro] = h.app.outbox.claim(now);
  const tokenAntigo = primeiro.token;

  // O lease expira e outro ciclo toma a entrega.
  const [segundo] = h.app.outbox.claim(now + PAR_20_LEASE_MS + 1);
  assert.notEqual(segundo.token, tokenAntigo, 'cada reivindicação tem seu próprio token');

  // O dono ANTIGO termina o envio e tenta gravar: precisa ser recusado.
  const aceitou = h.app.outbox.recordResult(primeiro.delivery.id, tokenAntigo, {
    status: 'delivered',
    attempt: { n: 1, at: now, outcome: 'ok', detail: 'chegou tarde' },
  });
  assert.equal(aceitou, false, 'o dono anterior não sobrescreve o estado do atual');

  const d = h.app.outbox.history(r.notificationId)[0];
  assert.equal(d.status, 'pending', 'o estado continua sendo o do dono vigente');

  // O dono ATUAL grava normalmente.
  const ok = h.app.outbox.recordResult(segundo.delivery.id, segundo.token, {
    status: 'delivered',
    attempt: { n: 2, at: now, outcome: 'ok', detail: 'HTTP 200' },
  });
  assert.equal(ok, true);
});

test('RES-05 / PERF-05: o lote de reivindicação nunca excede PAR-19', async (t) => {
  const h = await makeHarness();
  t.after(() => h.stop());

  // 20 notificações para carla (só webhook) = 20 entregas devidas.
  for (let i = 0; i < 20; i++) {
    h.app.ingestion.ingest({ recipientId: 'carla', category: 'billing', dedupKey: `k${i}`, payload }, 'x');
  }
  const now = h.app.store.now();

  const lote = h.app.outbox.claim(now, 50); // pede 50 de propósito
  assert.equal(lote.length, PAR_19_MAX_IN_FLIGHT, 'nenhuma entrega espera sua vez com o lease correndo');
});

test('OBS-01 / CTL-01: stats expõe profundidade, idade da mais velha e alarme de PAR-23', async (t) => {
  const h = await makeHarness();
  t.after(() => h.stop());

  h.app.ingestion.ingest({ recipientId: 'carla', category: 'billing', payload }, 'x');
  const now = h.app.store.now();

  const agora = h.app.outbox.stats(now);
  assert.equal(agora.pending, 1);
  assert.equal(agora.ageAlarm, false, 'recém-criada não dispara alarme');

  const daquiAMeiaHora = h.app.outbox.stats(now + 30 * 60_000);
  assert.ok(daquiAMeiaHora.oldestAgeMs >= 30 * 60_000);
  assert.equal(daquiAMeiaHora.ageAlarm, true, 'acima de PAR-23 = 15 min o alarme sobe');
});
