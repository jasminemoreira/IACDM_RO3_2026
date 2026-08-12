/**
 * M-10 caso-varredura — camada de aplicacao. Fluxo de observacao.
 *
 * Sondar -> reconciliar -> decidir -> persistir, com UMA transacao por alvo
 * (RES-03: fato e trilha commitam juntos, ou nenhum dos dois).
 *
 * RES-02: falha de um alvo NAO aborta os demais — o monitor precisa continuar
 * monitorando o resto quando um host cai.
 */

import { randomUUID } from 'node:crypto';
import { deCadeia, type Observacao } from './certificado.ts';
import { classificar, deveEscalar, validarContraObservacao, type ErroConfig } from './politica-limiar.ts';
import { expirarSemEmissao, fechar, estaAberto } from './pedido.ts';
import { reconciliar, rollbackTambemNaoAutorizado, type Decisao } from './reconciliacao.ts';
import type { Relogio } from './relogio.ts';
import type { Sonda } from './sonda-tls.ts';
import type { Repositorio, ObservacaoPersistida, Alvo } from './repositorio.ts';

export type Deps = { repo: Repositorio; sonda: Sonda; relogio: Relogio };

export type ResultadoAlvo = {
  readonly alvo: string;
  readonly decisao: Decisao | 'falha-de-sonda';
  readonly detalhe?: string;
};

export type RelatorioVarredura = {
  readonly varreduraId: string;
  readonly total: number;
  readonly ok: number;
  readonly falha: number;
  readonly resultados: readonly ResultadoAlvo[];
};

/** RES-06: chamado na abertura da aplicacao. Varredura sem `concluida_em` ficou orfa
 *  porque o processo morreu no meio — sem isto ela contamina a contagem para sempre. */
export function reconciliarVarredurasOrfas({ repo }: Deps): number {
  return repo.emTransacao((tx) => repo.varreduras.marcarOrfas(tx));
}

export async function varrer(deps: Deps): Promise<RelatorioVarredura> {
  const { repo, sonda, relogio } = deps;
  const alvos = repo.alvos.listar();
  const varreduraId = randomUUID();
  const iniciadaEm = relogio.agora();

  // OBS-01: o registro da varredura vive em transacao PROPRIA, no inicio e no fim.
  repo.emTransacao((tx) => {
    repo.varreduras.salvar(tx, {
      id: varreduraId, iniciadaEm, concluidaEm: null, interrompida: false,
      total: alvos.length, ok: 0, falha: 0,
    });
    repo.trilha.registrar(
      tx,
      { tipo: 'varredura-iniciada', atorId: null, alvoId: null, pedidoId: null, refIndice: null,
        dados: { varreduraId, alvos: alvos.length } },
      iniciadaEm,
    );
  });

  const resultados: ResultadoAlvo[] = [];
  let ok = 0;
  let falha = 0;

  for (const alvo of alvos) {
    const rotulo = `${alvo.host}:${alvo.porta}`;
    const sondagem = await sonda.sondar(alvo.host, alvo.porta);

    if (!sondagem.ok) {
      falha++;
      const agora = relogio.agora();
      repo.emTransacao((tx) =>
        repo.varreduras.registrarFalha(tx, alvo.id, sondagem.erro.tipo, sondagem.erro.detalhe, agora),
      );
      resultados.push({ alvo: rotulo, decisao: 'falha-de-sonda', detalhe: sondagem.erro.tipo });
      continue;
    }

    const parsed = deCadeia(sondagem.valor);
    if (!parsed.ok) {
      falha++;
      const agora = relogio.agora();
      repo.emTransacao((tx) =>
        repo.varreduras.registrarFalha(tx, alvo.id, 'tls', `parsing: ${parsed.erro.tipo}`, agora),
      );
      resultados.push({ alvo: rotulo, decisao: 'falha-de-sonda', detalhe: parsed.erro.tipo });
      continue;
    }

    ok++;
    resultados.push({ alvo: rotulo, ...processarAlvo(deps, alvo, parsed.valor) });
  }

  const concluidaEm = relogio.agora();
  repo.emTransacao((tx) => {
    repo.varreduras.salvar(tx, {
      id: varreduraId, iniciadaEm, concluidaEm, interrompida: false,
      total: alvos.length, ok, falha,
    });
    repo.trilha.registrar(
      tx,
      { tipo: 'varredura-concluida', atorId: null, alvoId: null, pedidoId: null, refIndice: null,
        dados: { varreduraId, ok, falha } },
      concluidaEm,
    );
  });

  return { varreduraId, total: alvos.length, ok, falha, resultados };
}

function processarAlvo(
  { repo, relogio }: Deps,
  alvo: Alvo,
  atual: Observacao,
): { decisao: Decisao; detalhe?: string } {
  const anterior = repo.alvos.ultimaObservacao(alvo.id);
  const pedidoAprovado = repo.pedidos.aprovadoDe(alvo.id);
  const decisao = reconciliar({ anterior, atual, pedidoAprovado });
  const agora = relogio.agora();

  // RES-07: relogio retrocedeu -> a operacao e RECUSADA. O evento e registrado com o
  // ultimo carimbo valido, para nao produzir uma cadeia com tempo andando para tras.
  const monotonia = relogio.verificarMonotonia(repo.trilha.ponta().registradoEm);
  if (!monotonia.ok) {
    const carimbo = repo.trilha.ponta().registradoEm ?? agora;
    repo.emTransacao((tx) =>
      repo.trilha.registrar(
        tx,
        { tipo: 'relogio-retrocedeu', atorId: null, alvoId: alvo.id, pedidoId: null, refIndice: null,
          dados: { deltaMs: monotonia.erro.deltaMs } },
        carimbo,
      ),
    );
    return { decisao, detalhe: 'operacao recusada: relogio retrocedeu' };
  }

  repo.emTransacao((tx) => {
    // PER-04/SUS-02: linha nova SO quando o fingerprint muda.
    let evidenciaId: string;
    if (anterior !== null && anterior.fingerprint256 === atual.fingerprint256) {
      repo.alvos.tocarObservacao(tx, anterior.id, agora);
      evidenciaId = anterior.id;
    } else {
      const nova: ObservacaoPersistida = {
        ...atual, id: randomUUID(), alvoId: alvo.id, vistoPrimeiroEm: agora, vistoUltimaVez: agora,
      };
      repo.alvos.salvarObservacao(tx, nova);
      evidenciaId = nova.id;
    }

    if (decisao === 'emissao-aprovada' && pedidoAprovado !== null) {
      const fechado = fechar(pedidoAprovado, evidenciaId, agora); // CA-3
      if (fechado.ok) {
        repo.pedidos.salvar(tx, fechado.valor);
        repo.trilha.registrar(
          tx,
          { tipo: 'pedido-fechado', atorId: null, alvoId: alvo.id, pedidoId: pedidoAprovado.id,
            refIndice: null,
            dados: { fingerprint: atual.fingerprint256, notAfter: atual.notAfterFolha.toISOString() } },
          agora,
        );
      }
    }

    if (decisao === 'troca-nao-autorizada') {
      repo.trilha.registrar( // CA-6
        tx,
        { tipo: 'troca-nao-autorizada', atorId: null, alvoId: alvo.id, pedidoId: null, refIndice: null,
          dados: { fingerprint: atual.fingerprint256, anterior: anterior?.fingerprint256 ?? null } },
        agora,
      );
    }

    if (decisao === 'rollback-detectado') {
      repo.trilha.registrar(
        tx,
        { tipo: 'rollback-detectado', atorId: null, alvoId: alvo.id, pedidoId: null, refIndice: null,
          dados: { fingerprint: atual.fingerprint256, notAfter: atual.notAfterFolha.toISOString() } },
        agora,
      );
      if (rollbackTambemNaoAutorizado(decisao, pedidoAprovado)) {
        repo.trilha.registrar(
          tx,
          { tipo: 'troca-nao-autorizada', atorId: null, alvoId: alvo.id, pedidoId: null, refIndice: null,
            dados: { fingerprint: atual.fingerprint256, motivo: 'rollback sem pedido aprovado' } },
          agora,
        );
      }
    }

    // PRO-02/PRO-06: alvo venceu com pedido aberto -> a transicao existe e alguem a chama.
    const urgencia = classificar(atual, alvo.limiares, agora).urgencia;
    const aberto = repo.pedidos.abertoDe(alvo.id);
    if (urgencia === 'expirado' && aberto !== null && estaAberto(aberto)) {
      const expirado = expirarSemEmissao(aberto, agora);
      if (expirado.ok) {
        repo.pedidos.salvar(tx, expirado.valor);
        repo.trilha.registrar(
          tx,
          { tipo: 'pedido-expirado-sem-emissao', atorId: null, alvoId: alvo.id, pedidoId: aberto.id,
            refIndice: null, dados: {} },
          agora,
        );
      }
    }
  });

  return { decisao };
}

/** Estado derivado na leitura (ASS-11/CTL-04): nunca persistido, sempre calculado a
 *  partir da observacao e do limiar VIGENTE. Mudar a politica reclassifica tudo. */
export function estadoDoAlvo(repo: Repositorio, alvo: Alvo, agora: Date) {
  const obs = repo.alvos.ultimaObservacao(alvo.id);
  const pedido = repo.pedidos.abertoDe(alvo.id);
  if (obs === null) {
    return { obs: null, urgencia: 'indisponivel' as const, escalado: false, semExpiracao: false,
             configInvalida: null as ErroConfig | null, pedido,
             trocasNaoAutorizadas: repo.trilha.contarPorTipo(alvo.id, 'troca-nao-autorizada') };
  }
  const c = classificar(obs, alvo.limiares, agora);
  /**
   * CA-5 no ponto onde o dado existe. No cadastro do alvo ainda nao ha certificado, e
   * validar contra Infinity deixa passar limiar de 90 dias sobre certificado de 45 —
   * alerta permanente desde a emissao, que e o ruido que treina o operador a ignorar
   * o alerta. A validacao real so e possivel DEPOIS da primeira observacao, e por isso
   * mora aqui, no estado derivado, e nao apenas em alterarLimiares.
   */
  const v = validarContraObservacao(alvo.limiares, obs);
  return {
    obs,
    urgencia: c.urgencia,
    semExpiracao: c.semExpiracao,
    escalado: deveEscalar(c.urgencia, pedido !== null),
    configInvalida: v.ok ? null : v.erro,
    pedido,
    trocasNaoAutorizadas: repo.trilha.contarPorTipo(alvo.id, 'troca-nao-autorizada'),
  };
}
