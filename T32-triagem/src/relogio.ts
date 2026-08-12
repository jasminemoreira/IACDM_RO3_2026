/**
 * M-01 relogio — fonte de tempo abstrata.
 *
 * Decisão da Fase 0: NENHUM módulo lê o relógio do sistema diretamente.
 * Prescrição de recurso (2880 min) e violação de SLA (240 a 14400 min) são
 * fenômenos de horas e dias; sem relógio controlável os requisitos temporais
 * — que são o núcleo deste sistema — ficariam não testáveis.
 *
 * Premissa A14: o relógio é monotônico e não retrocede. Se retrocedesse, um
 * recurso prescrito voltaria a ser admissível e um chamado violado voltaria a
 * não-violado (PRE-03).
 *
 * depends-on: —
 */

import type { Instante } from './tipos.js'

export interface Relogio {
  agora(): Instante
}

export const relogioDoSistema: Relogio = {
  agora: () => Date.now(),
}

export interface RelogioControlado extends Relogio {
  /** Só existe na implementação de teste. Avança o tempo sob comando —
   *  é o que permite testar 48 h de prescrição em microssegundos. */
  avancarMinutos(minutos: number): void
}

export function criarRelogioControlado(inicio: Instante): RelogioControlado {
  let atual = inicio
  return {
    agora: () => atual,
    avancarMinutos(minutos: number) {
      if (!Number.isFinite(minutos)) throw new Error('avancarMinutos: valor não finito')
      if (minutos < 0) throw new Error('avancarMinutos: o relógio não retrocede (premissa A14)')
      atual += Math.round(minutos * 60_000)
    },
  }
}
