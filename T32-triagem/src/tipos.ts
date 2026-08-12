/**
 * Tipos compartilhados do domínio.
 *
 * NÃO é um 13º módulo: contém exclusivamente declarações de tipo, zero
 * comportamento e zero dependência. Existe para que `chamado` (M-05) e
 * `recurso` (M-06) possam PRODUZIR eventos sem depender de `trilha` (M-07),
 * que apenas os guarda — dependência que não existe na tabela de módulos de
 * specs/technical/architecture.md e que não deve ser criada.
 */

export type Papel = 'SOLICITANTE' | 'AGENTE' | 'GESTOR'

/** Atribuído pelo AGENTE após a triagem (fonte F4). */
export type Impacto = 'ALTO' | 'MEDIO' | 'BAIXO'

/** Declarado pelo SOLICITANTE na abertura (fonte F4). */
export type Urgencia = 'ALTA' | 'MEDIA' | 'BAIXA'

export type Categoria = 'HARDWARE' | 'SOFTWARE' | 'REDE' | 'ACESSO' | 'OUTRO'

/**
 * O RÓTULO da prioridade — não a Prioridade.
 * `Prioridade` é tipo com marca e só existe como retorno de
 * `prioridade.derivar` (M-03). Este alias é o que aparece em configuração,
 * em banco e em trilha: dado inerte, sem a garantia do domínio.
 */
export type RotuloPrioridade = 'P1' | 'P2' | 'P3' | 'P4' | 'P5'

/** Milissegundos desde a época, UTC. Só obtido via `relogio.agora()` (M-01). */
export type Instante = number

export type EstadoChamado = 'NAO_TRIADO' | 'TRIADO' | 'RECONHECIDO' | 'ENCERRADO'

export type EstadoRecurso =
  | 'ABERTO'
  | 'PROVIDO'
  | 'PARCIALMENTE_PROVIDO'
  | 'IMPROVIDO'
  | 'PRESCRITO_SEM_JULGAMENTO'

export type Eixo = 'URGENCIA' | 'IMPACTO'

export type Usuario = {
  readonly id: string
  readonly nome: string
  readonly papel: Papel
}

export type Prazos = {
  readonly reconhecimento: Instante
  readonly resolucao: Instante
}

// ---------------------------------------------------------------------------
// Trilha — união fechada (LIN-05). Os construtores estão enumerados aqui e em
// nenhum outro lugar; `antes`/`depois` como json livre foi o defeito LIN-02.
// ---------------------------------------------------------------------------

export type TipoEvento =
  | 'ABERTURA'
  | 'TRIAGEM'
  | 'RECLASSIFICACAO'
  | 'RECURSO_ABERTO'
  | 'RECURSO_JULGADO'
  | 'RECURSO_PRESCRITO'
  | 'RECONHECIMENTO'
  | 'ENCERRAMENTO'

/** Distingue uma mudança feita pelo agente de uma decorrente de recurso — é o
 *  que separa "violamos porque triamos errado" de "violamos porque demoramos"
 *  (JOG-02). */
export type Origem = 'SOLICITANTE' | 'AGENTE' | 'RECURSO' | 'SISTEMA'

export type CampoClassificacao = 'urgencia' | 'impacto' | 'categoria' | 'prioridade'

export type MudancaEixo = {
  readonly campo: CampoClassificacao
  readonly de: string | null
  readonly para: string | null
}

export type Evento = {
  readonly chamadoId: string
  readonly tipo: TipoEvento
  readonly atorId: string
  readonly instante: Instante
  readonly origem: Origem
  /** Hash da política vigente no instante da classificação (MOV-1/MOV-7).
   *  Responde "por que este chamado é P4?" de forma única e datada. */
  readonly versaoPolitica: string | null
  readonly mudancas: readonly MudancaEixo[]
  readonly motivo: string | null
}

/** Toda operação de domínio devolve estado E eventos juntos (MOV-2). */
export type Resultado<T> = {
  readonly entidade: T
  readonly eventos: readonly Evento[]
}

/**
 * Saída de operação de domínio: sucesso com estado+eventos, ou recusa com
 * MOTIVO tipado. O motivo é enumerado por módulo e não é string livre —
 * "inadmitido por prescrição" (B-3) precisa ser distinguível de "inadmitido
 * por falta de legitimidade" (B-5), e a UI mostra um texto diferente para cada.
 */
export type Saida<T, M extends string> =
  | ({ readonly ok: true } & Resultado<T>)
  | { readonly ok: false; readonly motivo: M }
