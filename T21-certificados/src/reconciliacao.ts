/**
 * M-04 reconciliacao — dominio puro.
 *
 * Decide EXCLUSIVAMENTE o que aconteceu com o certificado entre duas observacoes.
 * Nao classifica urgencia e nao escala — isso e politica-limiar.
 *
 * V(2), LIN-01: contrato desambiguado. `pedidoAprovado` contem APENAS pedido em
 * estado `aprovado`; `anterior` pode ser null (=> primeira-observacao, nunca troca
 * nao autorizada); nao recebe `estado` e nao depende de politica-limiar.
 *
 * CA-3 e CA-6 moram aqui.
 */

import type { Observacao } from './certificado.ts';
import type { Pedido } from './pedido.ts';

export type Decisao =
  /** ASS-03: primeira varredura de um alvo. Nunca e burla. */
  | 'primeira-observacao'
  | 'sem-mudanca'
  /** CA-3: fingerprint novo com notAfter avancado E pedido aprovado aberto. */
  | 'emissao-aprovada'
  /** CA-6: fingerprint novo com notAfter avancado e NENHUM pedido aprovado. */
  | 'troca-nao-autorizada'
  /** LIN-05: fingerprint mudou mas notAfter nao avancou — certificado antigo
   *  reinstalado. Nunca fecha pedido, seja qual for o estado da governanca. */
  | 'rollback-detectado';

export type EntradaReconciliacao = {
  readonly anterior: Observacao | null;
  readonly atual: Observacao;
  readonly pedidoAprovado: Pedido | null;
};

export function reconciliar({ anterior, atual, pedidoAprovado }: EntradaReconciliacao): Decisao {
  if (anterior === null) return 'primeira-observacao';
  if (anterior.fingerprint256 === atual.fingerprint256) return 'sem-mudanca';

  const avancou = atual.notAfterFolha.getTime() > anterior.notAfterFolha.getTime();
  if (!avancou) return 'rollback-detectado';

  return pedidoAprovado !== null ? 'emissao-aprovada' : 'troca-nao-autorizada';
}

/**
 * Regra declarada em V(3) para o consumidor: um rollback sem pedido aprovado
 * tambem e uma troca sem autorizacao e deve ser registrado como tal.
 */
export function rollbackTambemNaoAutorizado(
  decisao: Decisao,
  pedidoAprovado: Pedido | null,
): boolean {
  return decisao === 'rollback-detectado' && pedidoAprovado === null;
}
