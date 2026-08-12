/**
 * EDGE-1, EDGE-2 e a tabela Q-1..Q-8 de specs/datasets/suppression-truth-table.md.
 *
 * O erro que este arquivo existe para pegar: `start <= m && m < end`, que é
 * SEMPRE falso quando a janela cruza a meia-noite.
 */
import test from 'node:test';
import assert from 'node:assert/strict';
import { check, isInWindow, localMinuteOfDay } from '../src/quiet-hours/index.ts';
import { createPreferences, ValidationError } from '../src/preferences/index.ts';
import { openStore } from '../src/store/index.ts';
import { mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { utcForLocalHour } from './helpers.ts';

const CROSSING = { start: 22 * 60, end: 8 * 60 }; // 1320 -> 480
const NORMAL = { start: 60, end: 300 }; // 01:00 -> 05:00
const OFF = { start: 0, end: 0 };
const TZ = 'America/Sao_Paulo';

test('EDGE-1: janela cruzando a meia-noite — tabela-verdade Q-1..Q-8', () => {
  const at = (h: number, m = 0) => utcForLocalHour(TZ, h, m);

  assert.equal(isInWindow(CROSSING, TZ, at(23, 30)), true, 'Q-1: 23:30 está na janela');
  assert.equal(isInWindow(CROSSING, TZ, at(3, 0)), true, 'Q-2: 03:00 está na janela');
  assert.equal(isInWindow(CROSSING, TZ, at(12, 0)), false, 'Q-3: 12:00 está fora');
  assert.equal(isInWindow(CROSSING, TZ, at(8, 0)), false, 'Q-4: 08:00 exato está FORA (fim exclusivo)');
  assert.equal(isInWindow(CROSSING, TZ, at(22, 0)), true, 'Q-5: 22:00 exato está DENTRO (início inclusivo)');
  assert.equal(isInWindow(NORMAL, TZ, at(2, 0)), true, 'Q-6: janela normal, 02:00 dentro');
  assert.equal(isInWindow(NORMAL, TZ, at(23, 0)), false, 'Q-7: janela normal, 23:00 fora');
  assert.equal(isInWindow(OFF, TZ, at(3, 0)), false, 'Q-8: janela desligada nunca retém');
});

test('UC-2: a abertura é calculada no fuso da PESSOA, não no do servidor', () => {
  // Mesmo instante absoluto, três pessoas em fusos diferentes.
  const instant = utcForLocalHour('America/Sao_Paulo', 2, 0);

  const sp = check(CROSSING, 'America/Sao_Paulo', instant);
  assert.equal(sp.inWindow, true, 'em SP são 02:00 — dentro da janela');
  assert.equal(localMinuteOfDay('America/Sao_Paulo', sp.opensAt!), 8 * 60, 'abre exatamente às 08:00 locais');

  const tokyo = check(CROSSING, 'Asia/Tokyo', instant);
  assert.equal(tokyo.inWindow, false, 'no mesmo instante, em Tóquio é meio da tarde — fora da janela');

  // A prova de que o fuso importa: a abertura em NY é um instante ABSOLUTO diferente.
  const ny = check(CROSSING, 'America/New_York', instant);
  if (ny.inWindow) {
    assert.notEqual(ny.opensAt, sp.opensAt, 'abertura em NY não coincide com a de SP');
  }
});

test('UC-2 (negativo): fora da janela não há adiamento e não há opensAt', () => {
  const meioDia = utcForLocalHour(TZ, 12, 0);
  const r = check(CROSSING, TZ, meioDia);
  assert.equal(r.inWindow, false);
  assert.equal(r.opensAt, undefined, 'sem janela ativa, não faz sentido devolver instante de abertura');
});

test('ASS-03/ASS-08: transição de horário de verão não trava nem devolve instante passado', () => {
  // Em 2026, NY entra no horário de verão em 08/03 às 02:00 locais (hora inexistente).
  const durante = Date.UTC(2026, 2, 8, 6, 30); // 01:30 locais, dentro de 23:00-07:00
  const r = check({ start: 23 * 60, end: 7 * 60 }, 'America/New_York', durante);
  assert.equal(r.inWindow, true);
  assert.ok(r.opensAt! > durante, 'a abertura é no futuro, não no passado');
  assert.equal(isInWindow({ start: 23 * 60, end: 7 * 60 }, 'America/New_York', r.opensAt!), false,
    'o instante devolvido está de fato FORA da janela — é isso que o avanço por DST garante');
});

test('EDGE-2: fuso ausente ou inválido é rejeitado no cadastro, não silenciado como UTC', () => {
  const dir = mkdtempSync(join(tmpdir(), 't30-tz-'));
  const store = openStore(join(dir, 'tz.db'));
  const prefs = createPreferences(store);

  assert.throws(
    () => prefs.putRecipient({ id: 'x', timezone: '' }),
    (err: unknown) => err instanceof ValidationError && err.field === 'timezone',
    'fuso vazio precisa falhar',
  );
  assert.throws(
    () => prefs.putRecipient({ id: 'x', timezone: 'Marte/Olympus' }),
    (err: unknown) => err instanceof ValidationError,
    'fuso inexistente precisa falhar',
  );
  const ok = prefs.putRecipient({ id: 'x', timezone: 'Europe/Lisbon' });
  assert.equal(ok.timezone, 'Europe/Lisbon');
  store.close();
});
