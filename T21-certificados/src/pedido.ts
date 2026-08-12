/**
 * M-03 pedido — dominio puro. Maquina de estados (GoF State), SEM estado orfao.
 *
 * V(2), PRO-01: `rejeitado` e `cancelado` existem porque recusar e um ato de
 * governanca tao legitimo quanto aprovar — um sistema que so registra aprovacoes
 * mede consentimento, nao decisao.
 *
 * ARC-02: recebe o PAPEL COMO VALOR. A entidade nao depende do modulo de identidade.
 */

import { ok, erro, type Resultado } from './tipos.ts';

export type Papel = 'solicitante' | 'aprovador' | 'auditor';

export type EstadoPedido =
  | 'pendente'
  | 'aprovado'
  | 'fechado'
  | 'rejeitado'
  | 'cancelado'
  | 'expirado-sem-emissao';

export const ESTADOS_TERMINAIS: readonly EstadoPedido[] = [
  'fechado',
  'rejeitado',
  'cancelado',
  'expirado-sem-emissao',
];

export type Pedido = {
  readonly id: string;
  readonly alvoId: string;
  readonly estado: EstadoPedido;
  readonly solicitanteId: string;
  readonly aprovadorId: string | null;
  readonly motivo: string | null;
  readonly evidenciaId: string | null;
  readonly abertoEm: Date;
  readonly decididoEm: Date | null;
  readonly fechadoEm: Date | null;
};

export type ErroTransicao =
  | { tipo: 'estado-invalido'; de: EstadoPedido; acao: string }
  | { tipo: 'papel-insuficiente'; papel: Papel; exigido: Papel }
  | { tipo: 'motivo-obrigatorio' };

/** ASS-09: o invariante e "no maximo um pedido nao-terminal por alvo".
 *  Quem o impoe e caso-governanca, no momento de abrir; aqui fica o predicado. */
export function estaAberto(p: Pedido): boolean {
  return !ESTADOS_TERMINAIS.includes(p.estado);
}

export function abrir(id: string, alvoId: string, solicitanteId: string, agora: Date): Pedido {
  return {
    id,
    alvoId,
    estado: 'pendente',
    solicitanteId,
    aprovadorId: null,
    motivo: null,
    evidenciaId: null,
    abertoEm: agora,
    decididoEm: null,
    fechadoEm: null,
  };
}

/** CA-2: nao sai de `pendente` sem um Aprovador, e o ator fica gravado. */
export function aprovar(
  p: Pedido,
  atorId: string,
  papel: Papel,
  agora: Date,
): Resultado<Pedido, ErroTransicao> {
  if (papel !== 'aprovador') {
    return erro({ tipo: 'papel-insuficiente', papel, exigido: 'aprovador' });
  }
  if (p.estado !== 'pendente') {
    return erro({ tipo: 'estado-invalido', de: p.estado, acao: 'aprovar' });
  }
  return ok({ ...p, estado: 'aprovado', aprovadorId: atorId, decididoEm: agora });
}

export function rejeitar(
  p: Pedido,
  atorId: string,
  papel: Papel,
  motivo: string,
  agora: Date,
): Resultado<Pedido, ErroTransicao> {
  if (papel !== 'aprovador') {
    return erro({ tipo: 'papel-insuficiente', papel, exigido: 'aprovador' });
  }
  if (p.estado !== 'pendente') {
    return erro({ tipo: 'estado-invalido', de: p.estado, acao: 'rejeitar' });
  }
  if (motivo.trim().length === 0) return erro({ tipo: 'motivo-obrigatorio' });
  return ok({ ...p, estado: 'rejeitado', aprovadorId: atorId, motivo, decididoEm: agora });
}

/** V(3), PRO-07: cancelar SO a partir de `pendente` — cancelar um pedido ja
 *  aprovado apagaria o efeito de uma aprovacao registrada. */
export function cancelar(p: Pedido, _atorId: string, agora: Date): Resultado<Pedido, ErroTransicao> {
  if (p.estado !== 'pendente') {
    return erro({ tipo: 'estado-invalido', de: p.estado, acao: 'cancelar' });
  }
  return ok({ ...p, estado: 'cancelado', decididoEm: agora });
}

/** CA-3: o fechamento e consequencia da varredura, nunca de declaracao humana. */
export function fechar(p: Pedido, evidenciaId: string, agora: Date): Resultado<Pedido, ErroTransicao> {
  if (p.estado !== 'aprovado') {
    return erro({ tipo: 'estado-invalido', de: p.estado, acao: 'fechar' });
  }
  return ok({ ...p, estado: 'fechado', evidenciaId, fechadoEm: agora });
}

/** PRO-02/PRO-06: chamada por caso-varredura quando o alvo vence com pedido aberto. */
export function expirarSemEmissao(p: Pedido, agora: Date): Resultado<Pedido, ErroTransicao> {
  if (!estaAberto(p)) {
    return erro({ tipo: 'estado-invalido', de: p.estado, acao: 'expirarSemEmissao' });
  }
  return ok({ ...p, estado: 'expirado-sem-emissao', fechadoEm: agora });
}
