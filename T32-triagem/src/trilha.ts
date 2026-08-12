/**
 * M-07 trilha — guarda e devolve eventos. NÃO os constrói (MOV-2).
 *
 * Quem constrói o evento é o domínio, junto com a mudança de estado. Este
 * módulo é a porta de leitura e as regras de leitura da trilha — e nada mais.
 *
 * Somente-inserção: nunca atualizada, nunca apagada (premissa A4). CA-3 depende
 * disso: a sequência de eventos precisa reconstruir toda mudança de prioridade
 * com ator, instante, valor antes/depois e motivo.
 *
 * Premissa A15: não há arquivamento nesta entrega, e o crescimento é ilimitado
 * e CONHECIDO — a formulação anterior ("a trilha vive enquanto o chamado vive")
 * era enganosa, porque nenhum chamado morre (SUS-03).
 *
 * depends-on: —
 */

import type { Evento, MudancaEixo } from './tipos.js'

export interface PortaTrilha {
  /** Só leitura: a escrita acontece dentro de `repositorio.salvar`, que grava
   *  estado e eventos juntos e não tem versão que grave só o estado (MOV-9). */
  doChamado(chamadoId: string): readonly Evento[]
}

/** Só as mudanças de PRIORIDADE — é a projeção que CA-3 exige verificar. */
export function mudancasDePrioridade(eventos: readonly Evento[]): readonly (MudancaEixo & { instante: number; atorId: string; motivo: string | null })[] {
  const saida: (MudancaEixo & { instante: number; atorId: string; motivo: string | null })[] = []
  for (const e of eventos) {
    for (const m of e.mudancas) {
      if (m.campo === 'prioridade') {
        saida.push({ ...m, instante: e.instante, atorId: e.atorId, motivo: e.motivo })
      }
    }
  }
  return saida
}

/**
 * A prioridade que a trilha diz estar vigente após todos os eventos.
 * Devolve o RÓTULO como string, nunca uma `Prioridade` — o tipo com marca só
 * existe no domínio, e ler da trilha jamais pode produzir uma prioridade que
 * não passou por `derivar` (PRE-07).
 */
export function prioridadeSegundoTrilha(eventos: readonly Evento[]): string | null {
  const mudancas = mudancasDePrioridade(eventos)
  const ultima = mudancas[mudancas.length - 1]
  return ultima ? ultima.para : null
}

/** Quantas vezes a prioridade mudou — usado por CA-3 para conferir que a
 *  contagem de eventos bate com a contagem de mudanças efetivas. */
export function contarMudancasDePrioridade(eventos: readonly Evento[]): number {
  return mudancasDePrioridade(eventos).length
}
