/**
 * M-06 recurso — o rito, conforme specs/technical/rito-recurso.md.
 *
 * Único componente Tier 3 do projeto: não existe biblioteca, é lógica de
 * domínio própria — e por isso foi DEPOSITADA POR ESCRITO antes de virar
 * código (obrigação registrada na Fase 0, antídoto AP7). Fundamento normativo:
 * ISO 10002:2018 (fonte F6).
 *
 * MOV-8: este módulo NÃO modifica o chamado. Devolve a INTENÇÃO (`novosEixos`)
 * e quem aplica é `chamado.reclassificar`, único dono do recálculo. Por isso
 * `recurso` não depende de `chamado`.
 *
 * depends-on: configuracao
 */

import { prazosRito, versao } from './configuracao.js'
import { somarMinutos } from './sla.js'
import type {
  Categoria,
  Eixo,
  Evento,
  EstadoRecurso,
  Impacto,
  Instante,
  Saida,
  Urgencia,
} from './tipos.js'

export type Recurso = {
  readonly id: string
  readonly chamadoId: string
  readonly autorId: string
  readonly eixosContestados: readonly Eixo[]
  readonly justificativa: string
  readonly abertoEm: Instante
  readonly estado: EstadoRecurso
  readonly julgadorId: string | null
  readonly julgadoEm: Instante | null
  readonly fundamentacao: string | null
}

/** Motivos de recusa — enumerados porque B-3 (prescrição) tem de ser
 *  distinguível de B-5 (legitimidade) na tela e no teste (LIN-03). */
export type MotivoRecurso =
  | 'NAO_TRIADO'
  | 'CHAMADO_ENCERRADO'
  | 'SEM_LEGITIMIDADE'
  | 'RECURSO_JA_EXISTE'
  | 'PRESCRITO'
  | 'EIXOS_OBRIGATORIOS'
  | 'JUSTIFICATIVA_OBRIGATORIA'
  | 'SEM_AUTORIDADE'
  | 'JA_JULGADO'
  | 'FUNDAMENTACAO_OBRIGATORIA'
  | 'SEM_ALTERACAO'
  | 'PARCIAL_EXIGE_DOIS_EIXOS'
  | 'AINDA_NO_PRAZO'

export type Desfecho = 'PROVIDO' | 'PARCIALMENTE_PROVIDO' | 'IMPROVIDO'

export type NovosEixos = {
  readonly impacto?: Impacto
  readonly urgencia?: Urgencia
  readonly categoria?: Categoria
}

/** Contexto do chamado necessário às guardas — passado pelo caso de uso, e não
 *  obtido por dependência, para que `recurso` não conheça `chamado` (MOV-8). */
export type ContextoChamado = {
  readonly id: string
  readonly solicitanteId: string
  readonly estado: 'NAO_TRIADO' | 'TRIADO' | 'RECONHECIDO' | 'ENCERRADO'
  readonly ultimaMudancaClassificacao: Instante | null
}

export type SaidaJulgamento = Saida<Recurso, MotivoRecurso> & {
  readonly novosEixos?: NovosEixos
}

function evento(
  chamadoId: string,
  tipo: Evento['tipo'],
  atorId: string,
  instante: Instante,
  motivo: string | null,
): Evento {
  return {
    chamadoId,
    tipo,
    atorId,
    instante,
    origem: 'RECURSO',
    versaoPolitica: versao(),
    mudancas: [],
    motivo,
  }
}

/** Instante em que o recurso prescreve, contado da última mudança de
 *  classificação (MOV-12). Comparação é `>=`: exatamente no prazo, prescreveu. */
export function prescreveEm(ctx: ContextoChamado): Instante | null {
  if (ctx.ultimaMudancaClassificacao === null) return null
  return somarMinutos(ctx.ultimaMudancaClassificacao, prazosRito().recorrerMin)
}

/**
 * As 5 guardas de admissibilidade, NESTA ORDEM — o motivo devolvido é o da
 * primeira que falha, e os testes B-1..B-5 dependem de motivos distinguíveis.
 */
export function abrir(entrada: {
  id: string
  ctx: ContextoChamado
  autorId: string
  eixosContestados: readonly Eixo[]
  justificativa: string
  recursoExistente: boolean
  agora: Instante
}): Saida<Recurso, MotivoRecurso> {
  const { ctx } = entrada

  // G1 — há classificação a contestar?
  if (ctx.estado === 'NAO_TRIADO') return { ok: false, motivo: 'NAO_TRIADO' }
  // G2 — chamado ainda vivo?
  if (ctx.estado === 'ENCERRADO') return { ok: false, motivo: 'CHAMADO_ENCERRADO' }
  // G3 — legitimidade: só o solicitante DESTE chamado
  if (entrada.autorId !== ctx.solicitanteId) return { ok: false, motivo: 'SEM_LEGITIMIDADE' }
  // G4 — no máximo um recurso por chamado
  if (entrada.recursoExistente) return { ok: false, motivo: 'RECURSO_JA_EXISTE' }
  // G5 — prescrição
  const limite = prescreveEm(ctx)
  if (limite === null || entrada.agora >= limite) return { ok: false, motivo: 'PRESCRITO' }

  if (entrada.eixosContestados.length === 0) return { ok: false, motivo: 'EIXOS_OBRIGATORIOS' }
  if (entrada.justificativa.trim() === '') return { ok: false, motivo: 'JUSTIFICATIVA_OBRIGATORIA' }

  const r: Recurso = {
    id: entrada.id,
    chamadoId: ctx.id,
    autorId: entrada.autorId,
    eixosContestados: [...entrada.eixosContestados],
    justificativa: entrada.justificativa.trim(),
    abertoEm: entrada.agora,
    estado: 'ABERTO',
    julgadorId: null,
    julgadoEm: null,
    fundamentacao: null,
  }
  return {
    ok: true,
    entidade: r,
    eventos: [evento(ctx.id, 'RECURSO_ABERTO', entrada.autorId, entrada.agora, r.justificativa)],
  }
}

/**
 * Julgamento. Devolve `novosEixos` quando o desfecho altera a classificação —
 * quem aplica é `chamado.reclassificar` (MOV-8).
 *
 * O prazo de julgamento (24 h) NÃO é guarda aqui: julgar com atraso continua
 * válido, porque invalidar a decisão puniria o solicitante pelo atraso do
 * gestor. O prazo age pelo outro lado, em `prescrever`.
 */
export function julgar(entrada: {
  recurso: Recurso
  julgadorEhGestor: boolean
  julgadorId: string
  desfecho: Desfecho
  fundamentacao: string
  novosEixos: NovosEixos
  agora: Instante
}): SaidaJulgamento {
  const { recurso: r } = entrada

  // J1 — só o GESTOR julga
  if (!entrada.julgadorEhGestor) return { ok: false, motivo: 'SEM_AUTORIDADE' }
  // J2 — recurso ainda aberto
  if (r.estado !== 'ABERTO') return { ok: false, motivo: 'JA_JULGADO' }
  // J3 — fundamentação obrigatória, inclusive no improvimento
  if (entrada.fundamentacao.trim() === '') return { ok: false, motivo: 'FUNDAMENTACAO_OBRIGATORIA' }

  const alterou = Object.values(entrada.novosEixos).some((v) => v !== undefined)
  // J4 — provimento sem alteração é contradição
  if (entrada.desfecho !== 'IMPROVIDO' && !alterou) return { ok: false, motivo: 'SEM_ALTERACAO' }
  // LIN-04 — "parcialmente provido" só faz sentido com dois eixos contestados
  if (entrada.desfecho === 'PARCIALMENTE_PROVIDO' && r.eixosContestados.length < 2) {
    return { ok: false, motivo: 'PARCIAL_EXIGE_DOIS_EIXOS' }
  }

  const julgado: Recurso = {
    ...r,
    estado: entrada.desfecho,
    julgadorId: entrada.julgadorId,
    julgadoEm: entrada.agora,
    fundamentacao: entrada.fundamentacao.trim(),
  }
  const saida: SaidaJulgamento = {
    ok: true,
    entidade: julgado,
    eventos: [
      evento(r.chamadoId, 'RECURSO_JULGADO', entrada.julgadorId, entrada.agora, `${entrada.desfecho}: ${julgado.fundamentacao}`),
    ],
  }
  // IMPROVIDO também grava trilha (VAL-11): registrar o que NÃO mudou, e por
  // quê, é metade do valor de auditoria do rito.
  if (entrada.desfecho === 'IMPROVIDO') return saida
  return { ...saida, novosEixos: entrada.novosEixos }
}

/**
 * MOV-11 — prescrição sem julgamento. Existe porque a guarda "não se encerra
 * chamado com recurso ABERTO" transformaria um recurso esquecido num bloqueio
 * permanente do chamado (PRO-06). A trilha registra que NINGUÉM JULGOU, que é
 * informação diferente de "foi improvido": reusar IMPROVIDO aqui seria mentir
 * e destruiria o valor de auditoria do rito.
 */
export function prescrever(r: Recurso, agora: Instante): Saida<Recurso, MotivoRecurso> {
  if (r.estado !== 'ABERTO') return { ok: false, motivo: 'JA_JULGADO' }
  const limite = somarMinutos(r.abertoEm, prazosRito().julgarMin)
  if (agora < limite) return { ok: false, motivo: 'AINDA_NO_PRAZO' }

  const prescrito: Recurso = { ...r, estado: 'PRESCRITO_SEM_JULGAMENTO' }
  return {
    ok: true,
    entidade: prescrito,
    eventos: [
      evento(r.chamadoId, 'RECURSO_PRESCRITO', 'sistema', agora, 'prazo de julgamento esgotado sem decisão do gestor'),
    ],
  }
}

export function expirouParaJulgamento(r: Recurso, agora: Instante): boolean {
  return r.estado === 'ABERTO' && agora >= somarMinutos(r.abertoEm, prazosRito().julgarMin)
}
