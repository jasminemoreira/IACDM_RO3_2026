/**
 * Integracao ponta a ponta — servidor TLS real, banco SQLite real, sem dubles.
 *
 * Cobre os criterios que so existem na costura entre modulos: CA-3 (a varredura
 * fecha o pedido), CA-6 (troca sem aprovacao e detectada) e SEC-09 (a justificativa
 * nao apaga o registro nem zera o contador).
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import tls from 'node:tls';
import { readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { randomUUID } from 'node:crypto';

import { criarRepositorio } from '../src/repositorio.ts';
import { criarSonda } from '../src/sonda-tls.ts';
import { criarRelogio } from '../src/relogio.ts';
import { varrer, estadoDoAlvo } from '../src/caso-varredura.ts';
import * as gov from '../src/caso-governanca.ts';
import { LIMIARES_PADRAO } from '../src/politica-limiar.ts';

const fx = (n: string) => readFileSync(new URL(`../specs/datasets/${n}`, import.meta.url));
const CURTO = { key: fx('key-45d.pem'), cert: fx('cert-45d.pem') };
const LONGO = { key: fx('key-200d.pem'), cert: fx('cert-200d.pem') };

async function comAmbiente(
  fn: (ctx: {
    deps: { repo: ReturnType<typeof criarRepositorio>; sonda: ReturnType<typeof criarSonda>; relogio: ReturnType<typeof criarRelogio> };
    govDeps: gov.Deps;
    porta: number;
    servirLongo: () => void;
    servirCurto: () => void;
  }) => Promise<void>,
) {
  const banco = join(tmpdir(), `t21-${randomUUID()}.db`);
  const servidor = tls.createServer(CURTO, (s) => s.end());
  await new Promise<void>((r) => servidor.listen(0, '127.0.0.1', r));
  const porta = (servidor.address() as { port: number }).port;

  const repo = criarRepositorio(banco);
  const relogio = criarRelogio();
  const deps = { repo, sonda: criarSonda(), relogio };
  try {
    await fn({
      deps,
      govDeps: { repo, relogio },
      porta,
      servirLongo: () => servidor.setSecureContext(LONGO),
      servirCurto: () => servidor.setSecureContext(CURTO),
    });
  } finally {
    repo.fechar();
    servidor.close();
    rmSync(banco, { force: true });
  }
}

function montarCenario(govDeps: gov.Deps, porta: number) {
  const ana = gov.criarPrimeiroAprovador(govDeps, 'ana', 'senha-forte-123');
  assert.ok(ana.ok);
  const alvo = gov.cadastrarAlvo(govDeps, ana.valor.id, '127.0.0.1', porta, ana.valor.id, LIMIARES_PADRAO);
  assert.ok(alvo.ok, 'cadastro do alvo deve funcionar');
  return { ana: ana.valor, alvo: alvo.valor };
}

test('UC-1: cadastrar alvo e varrer produz observacao verificada (nunca declarada)', async () => {
  await comAmbiente(async ({ deps, govDeps, porta }) => {
    const { alvo } = montarCenario(govDeps, porta);
    const rel = await varrer(deps);
    assert.equal(rel.total, 1);
    assert.equal(rel.ok, 1);
    assert.equal(rel.falha, 0);
    assert.equal(rel.resultados[0]?.decisao, 'primeira-observacao');

    const obs = deps.repo.alvos.ultimaObservacao(alvo.id);
    assert.ok(obs, 'a varredura precisa ter gravado a observacao');
    assert.ok(obs.subject.includes('curto.exemplo'));
  });
});

test('CA-5 na integracao: limiar 90 sobre certificado de 45 dias aparece como config invalida', async () => {
  await comAmbiente(async ({ deps, govDeps, porta }) => {
    const { alvo } = montarCenario(govDeps, porta);
    await varrer(deps);
    const e = estadoDoAlvo(deps.repo, alvo, deps.relogio.agora());
    assert.ok(e.configInvalida, 'CA-5 precisa acusar limiar maior que a vida do certificado');
    assert.equal(e.configInvalida.tipo, 'limiar-maior-que-vida');
  });
});

test('CA-3: pedido aprovado + certificado trocado => varredura FECHA o pedido com evidencia', async () => {
  await comAmbiente(async ({ deps, govDeps, porta, servirLongo }) => {
    const { ana, alvo } = montarCenario(govDeps, porta);
    await varrer(deps);

    const pedido = gov.abrirPedido(govDeps, ana, alvo.id);
    assert.ok(pedido.ok);
    const aprovado = gov.aprovarPedido(govDeps, ana, pedido.valor.id);
    assert.ok(aprovado.ok);
    assert.equal(aprovado.valor.aprovadorId, ana.id); // CA-2

    servirLongo(); // o operador instalou o certificado novo no host
    const rel = await varrer(deps);
    assert.equal(rel.resultados[0]?.decisao, 'emissao-aprovada');

    const fechado = deps.repo.pedidos.buscarPorId(pedido.valor.id);
    assert.equal(fechado?.estado, 'fechado');
    assert.ok(fechado?.evidenciaId, 'o certificado novo tem de ficar anexado como evidencia');

    const evento = deps.repo.trilha.listar(alvo.id).find((e) => e.tipo === 'pedido-fechado');
    assert.ok(evento, 'o fechamento tem de estar na trilha');
    assert.equal(gov.verificarIntegridade(govDeps).valida, true); // CA-4 apos movimentacao real
  });
});

test('CA-6: certificado trocado SEM pedido aprovado vira troca nao autorizada', async () => {
  await comAmbiente(async ({ deps, govDeps, porta, servirLongo }) => {
    const { alvo } = montarCenario(govDeps, porta);
    await varrer(deps);

    servirLongo(); // ninguem pediu, ninguem aprovou
    const rel = await varrer(deps);
    assert.equal(rel.resultados[0]?.decisao, 'troca-nao-autorizada');

    const eventos = deps.repo.trilha.listar(alvo.id).filter((e) => e.tipo === 'troca-nao-autorizada');
    assert.equal(eventos.length, 1);
    assert.equal(gov.destaqueAtivo(deps.repo, alvo.id), true);
  });
});

test('SEC-09 (negativo): justificar NAO apaga o registro nem zera o contador permanente', async () => {
  await comAmbiente(async ({ deps, govDeps, porta, servirLongo }) => {
    const { ana, alvo } = montarCenario(govDeps, porta);
    await varrer(deps);
    servirLongo();
    await varrer(deps);

    const antes = deps.repo.trilha.contarPorTipo(alvo.id, 'troca-nao-autorizada');
    assert.equal(antes, 1);

    const j = gov.justificarTroca(govDeps, ana, alvo.id, 'incidente fora do horario, troca emergencial');
    assert.ok(j.ok);
    assert.ok(j.valor.refIndice, 'a justificativa tem de referenciar a entrada da troca');

    // O destaque operacional sai...
    assert.equal(gov.destaqueAtivo(deps.repo, alvo.id), false);
    // ...mas o registro e o contador permanecem. E isso que muda o payoff de burlar.
    assert.equal(deps.repo.trilha.contarPorTipo(alvo.id, 'troca-nao-autorizada'), antes);
    assert.equal(gov.verificarIntegridade(govDeps).valida, true);
  });
});

test('SEC-09 (negativo): quem nao e Aprovador nao consegue justificar', async () => {
  await comAmbiente(async ({ deps, govDeps, porta, servirLongo }) => {
    const { ana, alvo } = montarCenario(govDeps, porta);
    await varrer(deps);
    servirLongo();
    await varrer(deps);

    const bruno = gov.novoAtor(govDeps, ana.id, 'bruno', 'senha-bruno-123', 'solicitante');
    assert.ok(bruno.ok);
    const j = gov.justificarTroca(govDeps, bruno.valor, alvo.id, 'deixa comigo');
    assert.equal(j.ok, false);
    assert.equal(j.ok === false && j.erro.tipo, 'papel-insuficiente');
  });
});

test('ASS-09 (negativo): nao e possivel abrir dois pedidos nao-terminais para o mesmo alvo', async () => {
  await comAmbiente(async ({ govDeps, porta }) => {
    const { ana, alvo } = montarCenario(govDeps, porta);
    assert.ok(gov.abrirPedido(govDeps, ana, alvo.id).ok);
    const segundo = gov.abrirPedido(govDeps, ana, alvo.id);
    assert.equal(segundo.ok, false);
    assert.equal(segundo.ok === false && segundo.erro.tipo, 'ja-existe-pedido-aberto');
  });
});

test('RES-01/RES-02: host inalcancavel vira falha registrada e NAO aborta os demais alvos', async () => {
  await comAmbiente(async ({ deps, govDeps, porta }) => {
    const { ana } = montarCenario(govDeps, porta);
    // porta 1 em 127.0.0.1: recusa conexao de imediato
    const morto = gov.cadastrarAlvo(govDeps, ana.id, '127.0.0.1', 1, ana.id, LIMIARES_PADRAO);
    assert.ok(morto.ok);

    const rel = await varrer(deps);
    assert.equal(rel.total, 2);
    assert.equal(rel.ok, 1, 'o alvo saudavel tem de ser varrido mesmo com o outro caindo');
    assert.equal(rel.falha, 1);

    const e = estadoDoAlvo(deps.repo, morto.valor, deps.relogio.agora());
    assert.equal(e.urgencia, 'indisponivel', 'sem observacao o alvo e indisponivel, nunca "ok"');
  });
});

test('GOV-01: cadastrar alvo e alterar limiar ficam na trilha, com autor', async () => {
  await comAmbiente(async ({ deps, govDeps, porta }) => {
    const { ana, alvo } = montarCenario(govDeps, porta);
    await varrer(deps);
    const r = gov.alterarLimiares(govDeps, ana.id, alvo.id, { aviso: 30, atencao: 20, critico: 10 });
    assert.ok(r.ok, 'limiares menores que a vida de 45 dias sao validos');

    const tipos = deps.repo.trilha.listar(alvo.id).map((e) => e.tipo);
    assert.ok(tipos.includes('alvo-cadastrado'));
    assert.ok(tipos.includes('limiar-alterado'));
    const alterado = deps.repo.trilha.listar(alvo.id).find((e) => e.tipo === 'limiar-alterado');
    assert.equal(alterado?.atorId, ana.id, 'mudar a politica tem de ter autor');
  });
});

test('CA-5 (negativo) na governanca: alterar limiar para valor >= vida do certificado e recusado', async () => {
  await comAmbiente(async ({ deps, govDeps, porta }) => {
    const { ana, alvo } = montarCenario(govDeps, porta);
    await varrer(deps); // certificado de 45 dias observado
    const r = gov.alterarLimiares(govDeps, ana.id, alvo.id, { aviso: 90, atencao: 60, critico: 30 });
    assert.equal(r.ok, false);
    assert.equal(r.ok === false && r.erro.tipo, 'config-invalida');
  });
});

test('REG-05: remover alvo e logico — a trilha e as observacoes sobrevivem', async () => {
  await comAmbiente(async ({ deps, govDeps, porta }) => {
    const { ana, alvo } = montarCenario(govDeps, porta);
    await varrer(deps);
    assert.ok(gov.removerAlvo(govDeps, ana.id, alvo.id).ok);

    assert.equal(deps.repo.alvos.listar().length, 0, 'some do inventario ativo');
    assert.ok(deps.repo.alvos.buscarPorId(alvo.id), 'mas o registro continua existindo');
    assert.ok(deps.repo.alvos.ultimaObservacao(alvo.id), 'e o historico observado tambem');
    assert.ok(deps.repo.trilha.listar(alvo.id).some((e) => e.tipo === 'alvo-removido'));
  });
});

test('PER-04/SUS-02: varrer duas vezes sem mudanca NAO duplica a observacao', async () => {
  await comAmbiente(async ({ deps, govDeps, porta }) => {
    const { alvo } = montarCenario(govDeps, porta);
    await varrer(deps);
    const primeira = deps.repo.alvos.ultimaObservacao(alvo.id);
    await varrer(deps);
    const segunda = deps.repo.alvos.ultimaObservacao(alvo.id);
    assert.equal(primeira?.id, segunda?.id, 'a mesma observacao e revisitada, nao reescrita');
    assert.ok(segunda!.vistoUltimaVez >= primeira!.vistoUltimaVez);
  });
});

/** PRO-05/GAM-02: segregacao de funcoes esta fora de escopo, entao auto-aprovacao e
 *  permitida — mas o auditor precisa conseguir FILTRAR. Registrar != proibir. */
test('PRO-05: auto-aprovacao e permitida, porem fica MARCADA na trilha', async () => {
  await comAmbiente(async ({ deps, govDeps, porta }) => {
    const { ana, alvo } = montarCenario(govDeps, porta);
    await varrer(deps);
    const p = gov.abrirPedido(govDeps, ana, alvo.id);
    assert.ok(p.ok);
    assert.ok(gov.aprovarPedido(govDeps, ana, p.valor.id).ok, 'aprovar o proprio pedido continua permitido');

    const ev = deps.repo.trilha.listar(alvo.id).find((e) => e.tipo === 'pedido-aprovado');
    assert.equal(ev?.dados['autoAprovacao'], true, 'o auditor tem de conseguir filtrar por isto');
  });
});

test('PRO-05: aprovacao por outra pessoa NAO e marcada como auto-aprovacao', async () => {
  await comAmbiente(async ({ deps, govDeps, porta }) => {
    const { ana, alvo } = montarCenario(govDeps, porta);
    await varrer(deps);
    const bruno = gov.novoAtor(govDeps, ana.id, 'bruno', 'senha-bruno-123', 'solicitante');
    assert.ok(bruno.ok);

    const p = gov.abrirPedido(govDeps, bruno.valor, alvo.id);
    assert.ok(p.ok);
    assert.ok(gov.aprovarPedido(govDeps, ana, p.valor.id).ok);

    const ev = deps.repo.trilha.listar(alvo.id).find((e) => e.tipo === 'pedido-aprovado');
    assert.equal(ev?.dados['autoAprovacao'], false);
  });
});

test('UX-05: rejeitar sem motivo devolve a causa REAL, nao "transicao-invalida"', async () => {
  await comAmbiente(async ({ govDeps, porta }) => {
    const { ana, alvo } = montarCenario(govDeps, porta);
    const p = gov.abrirPedido(govDeps, ana, alvo.id);
    assert.ok(p.ok);
    const r = gov.rejeitarPedido(govDeps, ana, p.valor.id, '   ');
    assert.equal(r.ok, false);
    assert.equal(r.ok === false && r.erro.tipo, 'motivo-obrigatorio');
  });
});

test('OBS-01: a varredura fica registrada e o operador sabe quando ela rodou', async () => {
  await comAmbiente(async ({ deps, govDeps, porta }) => {
    montarCenario(govDeps, porta);
    const rel = await varrer(deps);
    const v = deps.repo.varreduras.ultima();
    assert.equal(v?.id, rel.varreduraId);
    assert.ok(v?.concluidaEm, 'varredura concluida tem carimbo de fim');
    assert.equal(v?.interrompida, false);
  });
});
