/**
 * M-11 caso-governanca — camada de aplicacao. Fluxo humano.
 *
 * TODA operacao exige ator autenticado e anexa entrada na trilha. GOV-01: cadastrar
 * alvo e alterar limiar sao atos mais poderosos que aprovar um pedido — afrouxar o
 * limiar de 30 para 5 dias apaga o alerta de todo o inventario. Eram, em V(1), os
 * unicos atos sem autor.
 *
 * Divida de granularidade conhecida e aceita (ARC-06): auditoria (leitura pura) vive
 * aqui junto da governanca (escrita transacional) porque separa-la criaria um 13o
 * modulo, acima do limite de 12 do enunciado congelado.
 */

import { randomUUID } from 'node:crypto';
import { criarAtor, desativar, autenticar, type Ator } from './autorizacao.ts';
import { validarContraObservacao, validarLimiares, type Limiares, type ErroConfig } from './politica-limiar.ts';
import { abrir, aprovar, rejeitar, cancelar, type Pedido, type Papel, type EstadoPedido } from './pedido.ts';
import { verificar, type Entrada, type ResultadoVerificacao } from './trilha.ts';
import type { Relogio } from './relogio.ts';
import type { Repositorio, Alvo } from './repositorio.ts';
import { ok, erro, type Resultado } from './tipos.ts';

export type Deps = { repo: Repositorio; relogio: Relogio };

export type ErroGovernanca =
  | { tipo: 'ator-desconhecido' }
  | { tipo: 'papel-insuficiente'; exigido: Papel }
  | { tipo: 'alvo-desconhecido' }
  | { tipo: 'pedido-desconhecido' }
  | { tipo: 'ja-existe-pedido-aberto'; pedidoId: string }
  | { tipo: 'alvo-duplicado' }
  | { tipo: 'config-invalida'; causa: ErroConfig }
  /** O dominio sabe POR QUE recusou. Colapsar tudo em 'transicao-invalida' fazia a
   *  UI dizer jargao a quem so precisava preencher um campo — descoberto no teste
   *  exploratorio da Fase 6, e e perda de informacao, nao problema de texto. */
  | { tipo: 'motivo-obrigatorio' }
  | { tipo: 'estado-invalido'; de: EstadoPedido; acao: string }
  | { tipo: 'sem-troca-para-justificar' }
  | { tipo: 'relogio-retrocedeu'; deltaMs: number };

/** RES-07: nenhuma escrita acontece com o relogio andando para tras. */
function guardaDeRelogio({ repo, relogio }: Deps): Resultado<void, ErroGovernanca> {
  const m = relogio.verificarMonotonia(repo.trilha.ponta().registradoEm);
  return m.ok ? ok(undefined) : erro({ tipo: 'relogio-retrocedeu', deltaMs: m.erro.deltaMs });
}

// ---------------------------------------------------------------- atores

/** ASS-06: sem isto o sistema nasce travado — nenhum Aprovador, nenhum pedido aprovavel. */
export function criarPrimeiroAprovador(
  deps: Deps,
  nome: string,
  senha: string,
): Resultado<Ator, ErroGovernanca> {
  return novoAtor(deps, null, nome, senha, 'aprovador');
}

export function novoAtor(
  deps: Deps,
  autorId: string | null,
  nome: string,
  senha: string,
  papel: Papel,
): Resultado<Ator, ErroGovernanca> {
  const { repo, relogio } = deps;
  const agora = relogio.agora();
  const ator = criarAtor(nome, senha, papel, agora);
  repo.emTransacao((tx) => {
    repo.atores.salvar(tx, ator);
    repo.trilha.registrar( // GOV-03: quem criou o Aprovador fica registrado
      tx,
      { tipo: 'ator-criado', atorId: autorId, alvoId: null, pedidoId: null, refIndice: null,
        dados: { criado: ator.id, nome, papel } },
      agora,
    );
  });
  return ok(ator);
}

export function desativarAtor(deps: Deps, autorId: string, alvoAtorId: string): Resultado<void, ErroGovernanca> {
  const { repo, relogio } = deps;
  const a = repo.atores.buscarPorId(alvoAtorId);
  if (a === null) return erro({ tipo: 'ator-desconhecido' });
  const agora = relogio.agora();
  repo.emTransacao((tx) => {
    repo.atores.salvar(tx, desativar(a));
    repo.trilha.registrar(
      tx,
      { tipo: 'ator-criado', atorId: autorId, alvoId: null, pedidoId: null, refIndice: null,
        dados: { desativado: a.id, nome: a.nome } },
      agora,
    );
  });
  return ok(undefined);
}

export function autenticarAtor(deps: Deps, nome: string, senha: string): Ator | null {
  const a = deps.repo.atores.buscarPorNome(nome);
  if (a === null) return null;
  return autenticar(a, senha) ? a : null;
}

// ---------------------------------------------------------------- inventario

export function cadastrarAlvo(
  deps: Deps,
  autorId: string,
  host: string,
  porta: number,
  donoId: string,
  limiares: Limiares,
): Resultado<Alvo, ErroGovernanca> {
  const { repo, relogio } = deps;
  const guarda = guardaDeRelogio(deps);
  if (!guarda.ok) return guarda;
  if (repo.atores.buscarPorId(donoId) === null) return erro({ tipo: 'ator-desconhecido' });
  if (repo.alvos.listar().some((a) => a.host === host && a.porta === porta)) {
    return erro({ tipo: 'alvo-duplicado' });
  }
  // CA-5 na configuracao inicial: sem observacao ainda, valida ordem e positividade.
  const v = validarLimiares(limiares, Number.POSITIVE_INFINITY);
  if (!v.ok) return erro({ tipo: 'config-invalida', causa: v.erro });

  const agora = relogio.agora();
  const alvo: Alvo = { id: randomUUID(), host, porta, donoId, limiares, criadoEm: agora, removidoEm: null };
  repo.emTransacao((tx) => {
    repo.alvos.salvar(tx, alvo);
    repo.trilha.registrar(
      tx,
      { tipo: 'alvo-cadastrado', atorId: autorId, alvoId: alvo.id, pedidoId: null, refIndice: null,
        dados: { host, porta, donoId, limiares } },
      agora,
    );
  });
  return ok(alvo);
}

/** REG-05: remocao LOGICA — observacoes e pedidos historicos sobrevivem a auditoria. */
export function removerAlvo(deps: Deps, autorId: string, alvoId: string): Resultado<void, ErroGovernanca> {
  const { repo, relogio } = deps;
  const alvo = repo.alvos.buscarPorId(alvoId);
  if (alvo === null) return erro({ tipo: 'alvo-desconhecido' });
  const agora = relogio.agora();
  repo.emTransacao((tx) => {
    repo.alvos.remover(tx, alvoId, agora);
    repo.trilha.registrar(
      tx,
      { tipo: 'alvo-removido', atorId: autorId, alvoId, pedidoId: null, refIndice: null,
        dados: { host: alvo.host, porta: alvo.porta } },
      agora,
    );
  });
  return ok(undefined);
}

/** CA-5: limiar >= vida total do certificado observado e configuracao INVALIDA. */
export function alterarLimiares(
  deps: Deps,
  autorId: string,
  alvoId: string,
  limiares: Limiares,
): Resultado<void, ErroGovernanca> {
  const { repo, relogio } = deps;
  const alvo = repo.alvos.buscarPorId(alvoId);
  if (alvo === null) return erro({ tipo: 'alvo-desconhecido' });

  const obs = repo.alvos.ultimaObservacao(alvoId);
  const v = obs === null
    ? validarLimiares(limiares, Number.POSITIVE_INFINITY)
    : validarContraObservacao(limiares, obs);
  if (!v.ok) return erro({ tipo: 'config-invalida', causa: v.erro });

  const agora = relogio.agora();
  repo.emTransacao((tx) => {
    repo.alvos.salvar(tx, { ...alvo, limiares });
    repo.trilha.registrar( // GOV-01 + CTL-02: mudar a politica tem autor e fica no historico
      tx,
      { tipo: 'limiar-alterado', atorId: autorId, alvoId, pedidoId: null, refIndice: null,
        dados: { de: alvo.limiares, para: limiares } },
      agora,
    );
  });
  return ok(undefined);
}

// ---------------------------------------------------------------- pedidos

/** ASS-09: invariante — no maximo UM pedido nao-terminal por alvo. */
export function abrirPedido(deps: Deps, ator: Ator, alvoId: string): Resultado<Pedido, ErroGovernanca> {
  const { repo, relogio } = deps;
  const guarda = guardaDeRelogio(deps);
  if (!guarda.ok) return guarda;
  if (repo.alvos.buscarPorId(alvoId) === null) return erro({ tipo: 'alvo-desconhecido' });
  const jaAberto = repo.pedidos.abertoDe(alvoId);
  if (jaAberto !== null) return erro({ tipo: 'ja-existe-pedido-aberto', pedidoId: jaAberto.id });

  const agora = relogio.agora();
  const pedido = abrir(randomUUID(), alvoId, ator.id, agora);
  repo.emTransacao((tx) => {
    repo.pedidos.salvar(tx, pedido);
    repo.trilha.registrar(
      tx,
      { tipo: 'pedido-aberto', atorId: ator.id, alvoId, pedidoId: pedido.id, refIndice: null, dados: {} },
      agora,
    );
  });
  return ok(pedido);
}

/** CA-2: nao sai de pendente sem Aprovador autenticado, e o ator fica gravado. */
export function aprovarPedido(deps: Deps, ator: Ator, pedidoId: string): Resultado<Pedido, ErroGovernanca> {
  return decidirPedido(deps, ator, pedidoId, 'aprovar', null);
}

export function rejeitarPedido(
  deps: Deps,
  ator: Ator,
  pedidoId: string,
  motivo: string,
): Resultado<Pedido, ErroGovernanca> {
  return decidirPedido(deps, ator, pedidoId, 'rejeitar', motivo);
}

export function cancelarPedido(deps: Deps, ator: Ator, pedidoId: string): Resultado<Pedido, ErroGovernanca> {
  return decidirPedido(deps, ator, pedidoId, 'cancelar', null);
}

function decidirPedido(
  deps: Deps,
  ator: Ator,
  pedidoId: string,
  acao: 'aprovar' | 'rejeitar' | 'cancelar',
  motivo: string | null,
): Resultado<Pedido, ErroGovernanca> {
  const { repo, relogio } = deps;
  const guarda = guardaDeRelogio(deps);
  if (!guarda.ok) return guarda;
  const p = repo.pedidos.buscarPorId(pedidoId);
  if (p === null) return erro({ tipo: 'pedido-desconhecido' });

  const agora = relogio.agora();
  const r =
    acao === 'aprovar' ? aprovar(p, ator.id, ator.papel, agora)
    : acao === 'rejeitar' ? rejeitar(p, ator.id, ator.papel, motivo ?? '', agora)
    : cancelar(p, ator.id, agora);

  if (!r.ok) {
    switch (r.erro.tipo) {
      case 'papel-insuficiente':
        return erro({ tipo: 'papel-insuficiente', exigido: r.erro.exigido });
      case 'motivo-obrigatorio':
        return erro({ tipo: 'motivo-obrigatorio' });
      case 'estado-invalido':
        return erro({ tipo: 'estado-invalido', de: r.erro.de, acao: r.erro.acao });
    }
  }

  const tipo = acao === 'aprovar' ? 'pedido-aprovado' : acao === 'rejeitar' ? 'pedido-rejeitado' : 'pedido-cancelado';
  /** PRO-05/GAM-02: segregacao de funcoes esta fora de escopo por decisao do operador,
   *  entao auto-aprovacao e PERMITIDA — mas fica MARCADA, para o auditor poder filtrar.
   *  Registrar nao e o mesmo que proibir. */
  const autoAprovacao = acao === 'aprovar' && ator.id === p.solicitanteId;
  repo.emTransacao((tx) => {
    repo.pedidos.salvar(tx, r.valor);
    repo.trilha.registrar(
      tx,
      { tipo, atorId: ator.id, alvoId: p.alvoId, pedidoId: p.id, refIndice: null,
        dados: { ...(motivo === null ? {} : { motivo }), ...(acao === 'aprovar' ? { autoAprovacao } : {}) } },
      agora,
    );
  });
  return ok(r.valor);
}

// ---------------------------------------------------------------- justificativa

/**
 * SEC-09/GAM-04/ETH-01 — o limite admitido do produto.
 *
 * Um sistema sem poder sobre o host NAO impede a burla. O que ele faz:
 *  1. exige papel Aprovador (nao qualquer ator autenticado);
 *  2. NAO apaga nada — referencia o indice `i` da entrada `troca-nao-autorizada`
 *     e anexa uma entrada nova;
 *  3. o contador de trocas nao autorizadas do alvo e permanente e nada o zera.
 *
 * O burlador continua podendo justificar-se. O que ele nao consegue e fazer o
 * registro desaparecer, nem escreve-lo sem que fique atribuido ao seu nome.
 */
export function justificarTroca(
  deps: Deps,
  ator: Ator,
  alvoId: string,
  justificativa: string,
): Resultado<Entrada, ErroGovernanca> {
  const { repo, relogio } = deps;
  if (ator.papel !== 'aprovador') return erro({ tipo: 'papel-insuficiente', exigido: 'aprovador' });
  const guarda = guardaDeRelogio(deps);
  if (!guarda.ok) return guarda;

  const trocas = repo.trilha.listar(alvoId).filter((e) => e.tipo === 'troca-nao-autorizada');
  const ultima = trocas.at(-1);
  if (ultima === undefined) return erro({ tipo: 'sem-troca-para-justificar' });

  const agora = relogio.agora();
  const entrada = repo.emTransacao((tx) =>
    repo.trilha.registrar(
      tx,
      { tipo: 'troca-justificada', atorId: ator.id, alvoId, pedidoId: null,
        refIndice: ultima.i, dados: { justificativa } },
      agora,
    ),
  );
  return ok(entrada);
}

/** O destaque operacional some quando ha justificativa posterior a ultima troca.
 *  O CONTADOR nao some — e o que muda o payoff de burlar. */
export function destaqueAtivo(repo: Repositorio, alvoId: string): boolean {
  const entradas = repo.trilha.listar(alvoId);
  const ultimaTroca = entradas.filter((e) => e.tipo === 'troca-nao-autorizada').at(-1);
  if (ultimaTroca === undefined) return false;
  return !entradas.some((e) => e.tipo === 'troca-justificada' && e.refIndice === ultimaTroca.i);
}

// ---------------------------------------------------------------- auditoria

export function auditar(deps: Deps, alvoId?: string): Entrada[] {
  return deps.repo.trilha.listar(alvoId);
}

/** CA-4. */
export function verificarIntegridade(deps: Deps): ResultadoVerificacao {
  return verificar(deps.repo.trilha.listar());
}
