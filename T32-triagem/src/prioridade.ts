/**
 * M-03 prioridade — a ÚNICA origem de uma Prioridade em todo o sistema.
 *
 * Tier 2 (S6): algoritmo documentado com referência. Portado literalmente de
 * specs/examples/derivacao-prioridade.md, que por sua vez vem de
 * specs/technical/matriz-prioridade.md (fonte F1).
 *
 * O tipo `Prioridade` tem marca e este módulo NÃO exporta construtor nem
 * conversão. Nenhum outro módulo consegue fabricar uma Prioridade — é assim
 * que o CA-negativo ("prioridade gravada por escrita direta = falha, mesmo com
 * testes verdes") deixa de depender de disciplina e passa a depender do tsc.
 *
 * depends-on: configuracao
 */

import { matriz } from './configuracao.js'
import type { Impacto, RotuloPrioridade, Urgencia } from './tipos.js'

declare const marcaPrioridade: unique symbol

export type Prioridade = RotuloPrioridade & { readonly [marcaPrioridade]: true }

/**
 * Consulta TOTAL: sem default, sem fallback. A totalidade da matriz é
 * garantida na inicialização por configuracao.carregar (PRE-01) — se uma
 * célula faltasse, o processo não teria subido.
 *
 * NÃO implementar como `P = impacto + urgencia - 1`: a identidade aritmética
 * existe, mas acopla o resultado a uma matriz simétrica 3×3, e a matriz é
 * configurável (F2, F4). Trocar uma célula na política deve mudar o resultado;
 * com a fórmula, não mudaria.
 */
export function derivar(impacto: Impacto, urgencia: Urgencia): Prioridade {
  return matriz()[impacto][urgencia] as Prioridade
}

/**
 * Reconstrói a Prioridade a partir de impacto e urgência persistidos.
 * Existe porque o banco guarda os EIXOS, e a prioridade é sempre rederivada
 * na leitura — nunca lida como valor gravado independente (PRE-07).
 */
export const rederivar = derivar

/** Severidade numérica: 1 = P1 (mais severa) … 5 = P5. Usada na ordenação da fila. */
export function severidade(p: Prioridade): number {
  return Number(p.slice(1))
}
