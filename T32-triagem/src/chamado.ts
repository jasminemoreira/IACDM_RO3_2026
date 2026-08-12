/**
 * M-05 chamado — entidade Chamado e ÚNICO DONO do recálculo de prioridade e
 * prazos em todo o sistema (MOV-8).
 *
 * O chamado guarda os EIXOS (impacto, urgência) e os instantes. Prioridade e
 * prazos são DERIVADOS na leitura, nunca campos gravados — não existe valor
 * armazenado que possa divergir do que a política vigente produz (CTL-01), e a
 * trilha registra qual versão de política produziu cada decisão.
 *
 * Toda operação devolve `{entidade, eventos}` (MOV-2): não há caminho que mude
 * a classificação sem produzir o evento correspondente. CA-3 vira propriedade
 * do tipo, como o CA-negativo já era.
 *
 * depends-on: prioridade, sla
 */

import { derivar, type Prioridade } from './prioridade.js'
import { prazoTriagem, prazos as calcularPrazos, violado } from './sla.js'
import { versao } from './configuracao.js'
import type {
  Categoria,
  Evento,
  Impacto,
  Instante,
  MudancaEixo,
  Origem,
  Prazos,
  Saida,
  Urgencia,
  EstadoChamado,
} from './tipos.js'

export type Chamado = {
  readonly id: string
  readonly solicitanteId: string
  readonly titulo: string
  readonly descricao: string
  readonly urgencia: Urgencia
  readonly categoria: Categoria | null
  readonly impacto: Impacto | null
  readonly estado: EstadoChamado
  readonly abertoEm: Instante
  readonly triadoEm: Instante | null
  /** Base da prescrição do recurso (MOV-12): o prazo conta da ÚLTIMA mudança
   *  de classificação, não da triagem, para que uma reclassificação tardia da
   *  urgência não deixe o solicitante sem instrumento (SEG-05). */
  readonly ultimaMudancaClassificacao: Instante | null
  readonly reconhecidoEm: Instante | null
  readonly encerradoEm: Instante | null
}

export type MotivoChamado =
  | 'JA_TRIADO'
  | 'NAO_TRIADO'
  | 'CHAMADO_ENCERRADO'
  | 'RECURSO_ABERTO_PENDENTE'
  | 'SEM_ALTERACAO'
  | 'MOTIVO_OBRIGATORIO'
  | 'CAMPO_OBRIGATORIO'
  | 'JA_RECONHECIDO'

export type MudancaClassificacao = {
  readonly categoria?: Categoria
  readonly impacto?: Impacto
  readonly urgencia?: Urgencia
}

// --- Derivações (nunca campos gravados) -------------------------------------

/** Prioridade do chamado, ou null enquanto não triado. A ausência de
 *  prioridade NÃO é "prioridade baixa" — é ausência, e a fila as separa. */
export function prioridadeDe(c: Chamado): Prioridade | null {
  if (c.impacto === null) return null
  return derivar(c.impacto, c.urgencia)
}

export function prazosDe(c: Chamado): Prazos | null {
  const p = prioridadeDe(c)
  if (p === null) return null
  return calcularPrazos(p, c.abertoEm)
}

/** O prazo que governa o chamado agora: o de triagem enquanto não triado, o de
 *  resolução depois. As duas grandezas nunca são comparadas entre si (PER-04). */
export function prazoVigente(c: Chamado): Instante {
  const p = prazosDe(c)
  return p === null ? prazoTriagem(c.abertoEm) : p.resolucao
}

export function estaVioladoAgora(c: Chamado, agora: Instante): boolean {
  if (c.estado === 'ENCERRADO') return false
  return violado(prazoVigente(c), agora)
}

// --- Operações ---------------------------------------------------------------

function evento(
  c: Chamado,
  tipo: Evento['tipo'],
  atorId: string,
  instante: Instante,
  origem: Origem,
  mudancas: readonly MudancaEixo[],
  motivo: string | null,
): Evento {
  return {
    chamadoId: c.id,
    tipo,
    atorId,
    instante,
    origem,
    versaoPolitica: mudancas.length > 0 ? versao() : null,
    mudancas,
    motivo,
  }
}

export function abrir(entrada: {
  id: string
  solicitanteId: string
  titulo: string
  descricao: string
  urgencia: Urgencia
  agora: Instante
}): Saida<Chamado, MotivoChamado> {
  if (entrada.titulo.trim() === '' || entrada.descricao.trim() === '') {
    return { ok: false, motivo: 'CAMPO_OBRIGATORIO' }
  }
  const c: Chamado = {
    id: entrada.id,
    solicitanteId: entrada.solicitanteId,
    titulo: entrada.titulo.trim(),
    descricao: entrada.descricao.trim(),
    urgencia: entrada.urgencia,
    categoria: null,
    impacto: null,
    estado: 'NAO_TRIADO',
    abertoEm: entrada.agora,
    triadoEm: null,
    ultimaMudancaClassificacao: null,
    reconhecidoEm: null,
    encerradoEm: null,
  }
  return {
    ok: true,
    entidade: c,
    eventos: [
      evento(c, 'ABERTURA', entrada.solicitanteId, entrada.agora, 'SOLICITANTE', [
        { campo: 'urgencia', de: null, para: entrada.urgencia },
      ], null),
    ],
  }
}

export function triar(
  c: Chamado,
  agenteId: string,
  categoria: Categoria,
  impacto: Impacto,
  agora: Instante,
): Saida<Chamado, MotivoChamado> {
  if (c.estado === 'ENCERRADO') return { ok: false, motivo: 'CHAMADO_ENCERRADO' }
  if (c.estado !== 'NAO_TRIADO') return { ok: false, motivo: 'JA_TRIADO' }

  const novo: Chamado = {
    ...c,
    categoria,
    impacto,
    estado: 'TRIADO',
    triadoEm: agora,
    ultimaMudancaClassificacao: agora,
  }
  const mudancas: MudancaEixo[] = [
    { campo: 'categoria', de: null, para: categoria },
    { campo: 'impacto', de: null, para: impacto },
    { campo: 'prioridade', de: null, para: prioridadeDe(novo) },
  ]
  return { ok: true, entidade: novo, eventos: [evento(novo, 'TRIAGEM', agenteId, agora, 'AGENTE', mudancas, null)] }
}

/**
 * Única porta de mudança de classificação após a triagem — usada tanto pelo
 * agente quanto pelo provimento de recurso (MOV-8: `recurso` devolve a
 * intenção, quem aplica é aqui). Registra evento MESMO quando a prioridade
 * resultante não muda (VAL-4 / B-9): o que mudou foram os eixos.
 */
export function reclassificar(
  c: Chamado,
  atorId: string,
  mudanca: MudancaClassificacao,
  motivo: string,
  origem: Origem,
  agora: Instante,
): Saida<Chamado, MotivoChamado> {
  if (c.estado === 'ENCERRADO') return { ok: false, motivo: 'CHAMADO_ENCERRADO' }
  if (c.estado === 'NAO_TRIADO') return { ok: false, motivo: 'NAO_TRIADO' }
  if (motivo.trim() === '') return { ok: false, motivo: 'MOTIVO_OBRIGATORIO' }

  const alvo = {
    categoria: mudanca.categoria ?? c.categoria,
    impacto: mudanca.impacto ?? c.impacto,
    urgencia: mudanca.urgencia ?? c.urgencia,
  }
  const mudancas: MudancaEixo[] = []
  if (alvo.categoria !== c.categoria) mudancas.push({ campo: 'categoria', de: c.categoria, para: alvo.categoria })
  if (alvo.impacto !== c.impacto) mudancas.push({ campo: 'impacto', de: c.impacto, para: alvo.impacto })
  if (alvo.urgencia !== c.urgencia) mudancas.push({ campo: 'urgencia', de: c.urgencia, para: alvo.urgencia })
  if (mudancas.length === 0) return { ok: false, motivo: 'SEM_ALTERACAO' }

  const novo: Chamado = { ...c, ...alvo, ultimaMudancaClassificacao: agora }
  const antes = prioridadeDe(c)
  const depois = prioridadeDe(novo)
  if (antes !== depois) mudancas.push({ campo: 'prioridade', de: antes, para: depois })

  return {
    ok: true,
    entidade: novo,
    eventos: [evento(novo, 'RECLASSIFICACAO', atorId, agora, origem, mudancas, motivo.trim())],
  }
}

export function reconhecer(c: Chamado, atorId: string, agora: Instante): Saida<Chamado, MotivoChamado> {
  if (c.estado === 'ENCERRADO') return { ok: false, motivo: 'CHAMADO_ENCERRADO' }
  if (c.estado === 'NAO_TRIADO') return { ok: false, motivo: 'NAO_TRIADO' }
  if (c.estado === 'RECONHECIDO') return { ok: false, motivo: 'JA_RECONHECIDO' }

  const novo: Chamado = { ...c, estado: 'RECONHECIDO', reconhecidoEm: agora }
  return { ok: true, entidade: novo, eventos: [evento(novo, 'RECONHECIMENTO', atorId, agora, 'AGENTE', [], null)] }
}

/**
 * Guarda PRO-04: não se encerra chamado com recurso ABERTO — o recurso ficaria
 * órfão, sem julgamento com efeito e sem estado terminal. O bloqueio não é
 * permanente: passado o prazo de julgamento o recurso prescreve (MOV-11) e o
 * encerramento libera.
 */
export function encerrar(
  c: Chamado,
  atorId: string,
  agora: Instante,
  temRecursoAberto: boolean,
): Saida<Chamado, MotivoChamado> {
  if (c.estado === 'ENCERRADO') return { ok: false, motivo: 'CHAMADO_ENCERRADO' }
  if (c.estado === 'NAO_TRIADO') return { ok: false, motivo: 'NAO_TRIADO' }
  if (temRecursoAberto) return { ok: false, motivo: 'RECURSO_ABERTO_PENDENTE' }

  const novo: Chamado = { ...c, estado: 'ENCERRADO', encerradoEm: agora }
  return { ok: true, entidade: novo, eventos: [evento(novo, 'ENCERRAMENTO', atorId, agora, 'AGENTE', [], null)] }
}
