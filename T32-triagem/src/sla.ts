/**
 * M-04 sla — prazos contados DA ABERTURA, em minutos inteiros.
 *
 * A regra central da Fase 0 está na assinatura, não num comentário:
 * `prazos(p, abertoEm)` NÃO aceita "agora". É impossível implementar por
 * engano "reiniciar na reclassificação" — a opção explicitamente descartada —
 * porque a função não recebe o dado que isso exigiria.
 *
 * Metas em MINUTOS INTEIROS (MEC-03): horas fracionárias produziam
 * milissegundos quebrados e o prazo deslizava segundos em relação à meta
 * declarada. 0,167 h nunca foi 10 minutos.
 *
 * Fonte dos valores: specs/technical/matriz-prioridade.md (Tier C — defaults
 * configuráveis de projeto, NÃO norma ITIL).
 *
 * depends-on: configuracao
 */

import { metas, prazoTriagem as prazoTriagemConfig } from './configuracao.js'
import type { Prioridade } from './prioridade.js'
import type { Instante, Prazos, RotuloPrioridade } from './tipos.js'

const MS_POR_MINUTO = 60_000

export function somarMinutos(instante: Instante, minutos: number): Instante {
  return instante + minutos * MS_POR_MINUTO
}

/**
 * Prazos de um chamado triado. `abertoEm`, sempre — é o que faz um chamado
 * mal triado que sobe para P1 nascer já violado (CA-2, cenário GT-3), e é o
 * comportamento correto: a urgência sempre existiu, o erro foi não tê-la visto.
 */
export function prazos(p: Prioridade, abertoEm: Instante): Prazos {
  // A marca de `Prioridade` existe para controlar a ORIGEM do valor, não para
  // indexar: aqui só interessa o rótulo. O parâmetro continua exigindo uma
  // Prioridade de verdade, que só `prioridade.derivar` produz.
  const m = metas()[p as RotuloPrioridade]
  return {
    reconhecimento: somarMinutos(abertoEm, m.reconhecerMin),
    resolucao: somarMinutos(abertoEm, m.resolverMin),
  }
}

/**
 * Prazo para TRIAR (MOV-3). Independente de prioridade — não se pode depender
 * de uma prioridade que ainda não existe. Sem ele, o único estado sem governo
 * de tempo seria justamente a porta de entrada do sistema (PRO-01).
 */
export function prazoTriagem(abertoEm: Instante): Instante {
  return somarMinutos(abertoEm, prazoTriagemConfig())
}

export function violado(prazo: Instante, agora: Instante): boolean {
  return agora > prazo
}

export function violadoResolucao(p: Prazos, agora: Instante): boolean {
  return violado(p.resolucao, agora)
}
