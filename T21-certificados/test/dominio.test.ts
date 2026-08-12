/**
 * Testes de dominio — escritos contra specs/validation (CA-1 a CA-6) e contra os
 * achados nomeados da matriz de cobertura, NAO contra a implementacao.
 *
 * Fixtures reais em specs/datasets, geradas por openssl. O relogio e fixado em
 * `notAfter - N dias` para cair em cada faixa: o teste vale hoje e daqui a um ano.
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

import { deCadeia, vidaTotalDias, restanteDias, semExpiracao, cadeiaExpiraAntes,
         SENTINELA_SEM_EXPIRACAO, type Observacao } from '../src/certificado.ts';
import { classificar, validarLimiares, validarContraObservacao, deveEscalar,
         LIMIARES_PADRAO } from '../src/politica-limiar.ts';
import { abrir, aprovar, rejeitar, cancelar, fechar } from '../src/pedido.ts';
import { anexar, verificar, canonicalizar, GENESIS, type Entrada, type Evento } from '../src/trilha.ts';
import { criarAtor, autenticar, desativar } from '../src/autorizacao.ts';
import { reconciliar } from '../src/reconciliacao.ts';
import { relogioFixo, criarRelogio } from '../src/relogio.ts';

const DIA = 86_400_000;
const fixture = (n: string) => readFileSync(new URL(`../specs/datasets/${n}`, import.meta.url));
const separar = (pem: Buffer): Buffer[] =>
  pem.toString().split(/(?<=-----END CERTIFICATE-----\n?)/).filter((b) => b.includes('BEGIN'))
    .map((b) => Buffer.from(b));

const obs200 = (() => {
  const r = deCadeia([fixture('cert-200d.pem')]);
  assert.ok(r.ok, 'fixture cert-200d deve parsear');
  return r.valor;
})();
const obs45 = (() => {
  const r = deCadeia([fixture('cert-45d.pem')]);
  assert.ok(r.ok);
  return r.valor;
})();
/** agora = notAfter - N dias */
const emT = (o: Observacao, diasAntes: number) => new Date(o.notAfterFolha.getTime() - diasAntes * DIA);

// ---------------------------------------------------------------- certificado

test('deCadeia recusa cadeia vazia (pre-condicao declarada)', () => {
  const r = deCadeia([]);
  assert.equal(r.ok, false);
  assert.equal(r.ok === false && r.erro.tipo, 'cadeia-vazia');
});

test('deCadeia recusa DER ilegivel informando o indice', () => {
  const r = deCadeia([Buffer.from('nao sou um certificado')]);
  assert.equal(r.ok, false);
  assert.equal(r.ok === false && r.erro.tipo, 'der-ilegivel');
});

test('vidaTotalDias mede a vida real da fixture (200 dias)', () => {
  assert.equal(Math.round(vidaTotalDias(obs200)), 200);
  assert.equal(Math.round(vidaTotalDias(obs45)), 45);
});

test('SAN e extraido; subject e issuer preenchidos', () => {
  assert.ok(obs45.san.some((s) => s.includes('curto.exemplo')));
  assert.ok(obs45.subject.includes('curto.exemplo'));
});

test('ASS-01: notAfterEfetivo vem do intermediario que expira antes da folha', () => {
  const r = deCadeia(separar(fixture('cadeia-folha200-ca30.pem')));
  assert.ok(r.ok);
  assert.equal(r.valor.profundidade, 2);
  assert.ok(r.valor.notAfterEfetivo < r.valor.notAfterFolha,
    'a cadeia expira antes da folha — e a falha que o produto existe para prever');
  assert.equal(cadeiaExpiraAntes(r.valor), true);
});

test('RFC 5280: sentinela 99991231235959Z e "nao expira", nao ano 9999', () => {
  const sentinela: Observacao = { ...obs200, notAfterFolha: new Date(SENTINELA_SEM_EXPIRACAO) };
  assert.equal(semExpiracao(sentinela), true);
  assert.equal(semExpiracao(obs200), false);
});

// ---------------------------------------------------------------- CA-1

test('CA-1: classifica ok / aviso / atencao / critico com fixture real de 200 dias', () => {
  const l = LIMIARES_PADRAO; // 90/60/30 — validos contra vida de 200 dias
  assert.equal(classificar(obs200, l, emT(obs200, 120)).urgencia, 'ok');
  assert.equal(classificar(obs200, l, emT(obs200, 75)).urgencia, 'aviso');
  assert.equal(classificar(obs200, l, emT(obs200, 45)).urgencia, 'atencao');
  assert.equal(classificar(obs200, l, emT(obs200, 15)).urgencia, 'critico');
});

test('CA-1: certificado vencido e "expirado"', () => {
  const depois = new Date(obs200.notAfterFolha.getTime() + DIA);
  assert.equal(classificar(obs200, LIMIARES_PADRAO, depois).urgencia, 'expirado');
});

test('CA-1 (negativo): certificado vencido NUNCA cai em ok', () => {
  for (const dias of [1, 30, 400]) {
    const depois = new Date(obs200.notAfterFolha.getTime() + dias * DIA);
    assert.notEqual(classificar(obs200, LIMIARES_PADRAO, depois).urgencia, 'ok');
  }
});

test('ASS-04: certificado ainda nao valido tem estado proprio, nao "ok"', () => {
  const antes = new Date(obs200.notBefore.getTime() - DIA);
  assert.equal(classificar(obs200, LIMIARES_PADRAO, antes).urgencia, 'ainda-nao-valido');
});

test('MEC-03: dias por truncamento — 29,9 dias restantes e critico, nao atencao', () => {
  const agora = new Date(obs200.notAfterFolha.getTime() - 29.9 * DIA);
  assert.equal(restanteDias(obs200, agora), 29);
  assert.equal(classificar(obs200, LIMIARES_PADRAO, agora).urgencia, 'critico');
});

test('LIN-03: semExpiracao e dimensao separada da urgencia', () => {
  const sentinela: Observacao = { ...obs200, notAfterFolha: new Date(SENTINELA_SEM_EXPIRACAO) };
  const c = classificar(sentinela, LIMIARES_PADRAO, new Date());
  assert.equal(c.semExpiracao, true);
  assert.equal(c.urgencia, 'ok');
});

// ---------------------------------------------------------------- CA-5

test('CA-5: limiar >= vida total do certificado e configuracao INVALIDA', () => {
  const r = validarContraObservacao(LIMIARES_PADRAO, obs45); // 90 dias sobre cert de 45
  assert.equal(r.ok, false);
  assert.equal(r.ok === false && r.erro.tipo, 'limiar-maior-que-vida');
});

test('CA-5 (negativo): limiares fora de ordem sao recusados', () => {
  const r = validarLimiares({ aviso: 10, atencao: 60, critico: 90 }, 200);
  assert.equal(r.ok, false);
  assert.equal(r.ok === false && r.erro.tipo, 'limiares-fora-de-ordem');
});

test('CA-5 (negativo): limiar zero ou negativo e recusado', () => {
  assert.equal(validarLimiares({ aviso: 90, atencao: 60, critico: 0 }, 200).ok, false);
});

test('CA-5: limiares validos contra certificado de 200 dias sao aceitos', () => {
  assert.equal(validarContraObservacao(LIMIARES_PADRAO, obs200).ok, true);
});

test('NIST inacao: critico sem pedido escala; com pedido aberto nao', () => {
  assert.equal(deveEscalar('critico', false), true);
  assert.equal(deveEscalar('expirado', false), true);
  assert.equal(deveEscalar('critico', true), false);
  assert.equal(deveEscalar('aviso', false), false);
});

// ---------------------------------------------------------------- CA-2

const agoraFixo = new Date('2026-08-09T12:00:00Z');
const novoPedido = () => abrir('p1', 'a1', 'solicitante-1', agoraFixo);

test('CA-2 (negativo): auditor nao aprova', () => {
  const r = aprovar(novoPedido(), 'x', 'auditor', agoraFixo);
  assert.equal(r.ok, false);
  assert.equal(r.ok === false && r.erro.tipo, 'papel-insuficiente');
});

test('CA-2 (negativo): solicitante nao aprova', () => {
  const r = aprovar(novoPedido(), 'x', 'solicitante', agoraFixo);
  assert.equal(r.ok, false);
});

test('CA-2: aprovador aprova e o ator fica GRAVADO no pedido', () => {
  const r = aprovar(novoPedido(), 'ana-id', 'aprovador', agoraFixo);
  assert.ok(r.ok);
  assert.equal(r.valor.estado, 'aprovado');
  assert.equal(r.valor.aprovadorId, 'ana-id');
  assert.deepEqual(r.valor.decididoEm, agoraFixo);
});

test('CA-2 (negativo): aprovar duas vezes falha', () => {
  const um = aprovar(novoPedido(), 'ana', 'aprovador', agoraFixo);
  assert.ok(um.ok);
  const dois = aprovar(um.valor, 'ana', 'aprovador', agoraFixo);
  assert.equal(dois.ok, false);
  assert.equal(dois.ok === false && dois.erro.tipo, 'estado-invalido');
});

test('PRO-01 (negativo): rejeitar sem motivo e recusado', () => {
  const r = rejeitar(novoPedido(), 'ana', 'aprovador', '   ', agoraFixo);
  assert.equal(r.ok, false);
  assert.equal(r.ok === false && r.erro.tipo, 'motivo-obrigatorio');
});

test('PRO-01: rejeitar com motivo registra o motivo e o aprovador', () => {
  const r = rejeitar(novoPedido(), 'ana', 'aprovador', 'host sera desativado', agoraFixo);
  assert.ok(r.ok);
  assert.equal(r.valor.estado, 'rejeitado');
  assert.equal(r.valor.motivo, 'host sera desativado');
});

test('PRO-07 (negativo): cancelar pedido ja aprovado apagaria uma aprovacao registrada', () => {
  const ap = aprovar(novoPedido(), 'ana', 'aprovador', agoraFixo);
  assert.ok(ap.ok);
  assert.equal(cancelar(ap.valor, 'x', agoraFixo).ok, false);
});

test('CA-3 (negativo): fechar pedido que nao foi aprovado e recusado', () => {
  assert.equal(fechar(novoPedido(), 'obs-1', agoraFixo).ok, false);
});

// ---------------------------------------------------------------- CA-4

const evento = (tipo: Evento['tipo'], dados: Record<string, unknown> = {}): Evento =>
  ({ tipo, atorId: null, alvoId: 'a1', pedidoId: null, refIndice: null, dados });

function cadeiaDe(n: number): Entrada[] {
  const out: Entrada[] = [];
  let anterior = GENESIS;
  for (let i = 1; i <= n; i++) {
    const e = anexar(anterior, evento('pedido-aberto', { n: i }), new Date(agoraFixo.getTime() + i * 1000), i);
    out.push(e);
    anterior = e.hash;
  }
  return out;
}

test('CA-4: cadeia intacta verifica como VALIDA', () => {
  assert.deepEqual(verificar(cadeiaDe(5)), { valida: true });
});

test('CA-4 (negativo): adulterar UM registro torna a cadeia INVALIDA no indice certo', () => {
  const c = cadeiaDe(5);
  const adulterada = c.map((e, i) => (i === 2 ? { ...e, dados: { n: 'FORJADO' } } : e));
  const r = verificar(adulterada);
  assert.equal(r.valida, false);
  assert.equal(r.quebraNoIndice, 3);
});

test('CA-4 (negativo): remover um registro do meio quebra a cadeia', () => {
  const c = cadeiaDe(5);
  const r = verificar([...c.slice(0, 2), ...c.slice(3)]);
  assert.equal(r.valida, false);
});

test('CA-4 (negativo): trocar a ordem de duas entradas quebra a cadeia', () => {
  const c = cadeiaDe(5);
  const trocada = [...c];
  [trocada[1], trocada[2]] = [trocada[2]!, trocada[1]!];
  assert.equal(verificar(trocada).valida, false);
});

test('ASS-05: canonicalizacao — ordem das chaves nao altera o hash', () => {
  assert.equal(canonicalizar({ b: 1, a: 2 }), canonicalizar({ a: 2, b: 1 }));
  assert.equal(canonicalizar({ d: new Date('2026-01-01T00:00:00Z') }), '{"d":"2026-01-01T00:00:00.000Z"}');
});

// ---------------------------------------------------------------- CA-3 / CA-6

const comFingerprint = (o: Observacao, fp: string, notAfter: Date): Observacao =>
  ({ ...o, fingerprint256: fp, notAfterFolha: notAfter });

const pedidoAprovado = (() => {
  const r = aprovar(novoPedido(), 'ana', 'aprovador', agoraFixo);
  assert.ok(r.ok);
  return r.valor;
})();

test('ASS-03 (negativo): primeira observacao NUNCA e troca nao autorizada', () => {
  assert.equal(reconciliar({ anterior: null, atual: obs200, pedidoAprovado: null }), 'primeira-observacao');
});

test('reconciliar: mesmo fingerprint e sem-mudanca', () => {
  assert.equal(reconciliar({ anterior: obs200, atual: obs200, pedidoAprovado: null }), 'sem-mudanca');
});

test('CA-3: fingerprint novo com notAfter avancado E pedido aprovado = emissao aprovada', () => {
  const novo = comFingerprint(obs200, 'FP-NOVO', new Date(obs200.notAfterFolha.getTime() + 100 * DIA));
  assert.equal(reconciliar({ anterior: obs200, atual: novo, pedidoAprovado }), 'emissao-aprovada');
});

test('CA-6: fingerprint novo com notAfter avancado e SEM pedido aprovado = troca nao autorizada', () => {
  const novo = comFingerprint(obs200, 'FP-NOVO', new Date(obs200.notAfterFolha.getTime() + 100 * DIA));
  assert.equal(reconciliar({ anterior: obs200, atual: novo, pedidoAprovado: null }), 'troca-nao-autorizada');
});

test('LIN-05 (negativo): fingerprint muda sem notAfter avancar NAO fecha pedido', () => {
  const antigo = comFingerprint(obs200, 'FP-ANTIGO', new Date(obs200.notAfterFolha.getTime() - 50 * DIA));
  assert.equal(reconciliar({ anterior: obs200, atual: antigo, pedidoAprovado }), 'rollback-detectado');
});

// ---------------------------------------------------------------- autorizacao

test('autenticar aceita a senha correta (scrypt OWASP N=2^17, r=8, p=1)', () => {
  const a = criarAtor('ana', 'senha-forte-123', 'aprovador', agoraFixo);
  assert.equal(autenticar(a, 'senha-forte-123'), true);
});

test('(negativo) autenticar recusa senha errada', () => {
  const a = criarAtor('ana', 'senha-forte-123', 'aprovador', agoraFixo);
  assert.equal(autenticar(a, 'senha-forte-124'), false);
});

test('ETH-03 (negativo): ator desativado nao autentica, mas o historico permanece', () => {
  const a = desativar(criarAtor('ana', 'senha-forte-123', 'aprovador', agoraFixo));
  assert.equal(autenticar(a, 'senha-forte-123'), false);
  assert.equal(a.nome, 'ana');
});

// ---------------------------------------------------------------- relogio

test('ASS-08 (negativo): relogio retrocedido e detectado', () => {
  const r = relogioFixo(new Date('2026-08-09T10:00:00Z'));
  const m = r.verificarMonotonia(new Date('2026-08-09T12:00:00Z'));
  assert.equal(m.ok, false);
  assert.equal(m.ok === false && m.erro.tipo, 'relogio-retrocedeu');
  assert.equal(m.ok === false && m.erro.deltaMs, 2 * 60 * 60 * 1000);
});

test('relogio monotonico passa, e a primeira entrada (sem carimbo anterior) tambem', () => {
  const r = relogioFixo(new Date('2026-08-09T12:00:00Z'));
  assert.equal(r.verificarMonotonia(new Date('2026-08-09T10:00:00Z')).ok, true);
  assert.equal(r.verificarMonotonia(null).ok, true);
});

test('relogio devolve UTC (MEC-04)', () => {
  const agora = criarRelogio().agora();
  assert.match(agora.toISOString(), /Z$/);
});
