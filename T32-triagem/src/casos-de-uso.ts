/**
 * M-10 casos-de-uso — orquestração fina: autoriza, chama o domínio, persiste.
 *
 * MOV-2/MOV-9 esvaziaram este módulo de regra. Ele não decide prioridade, não
 * calcula prazo e não constrói evento — o domínio devolve estado e eventos
 * juntos, e `repositorio.salvar` os grava juntos. O que sobrou aqui é
 * composição, que é o que um caso de uso deve ser.
 *
 * A única composição com substância é `julgarRecurso`: MOV-8 fez `recurso`
 * devolver a INTENÇÃO e `chamado.reclassificar` aplicá-la, de modo que o
 * recálculo de prioridade e prazos continue tendo um único dono.
 *
 * depends-on: M-01..M-09
 */

import { pode, type Acao, type MotivoNegado } from './autorizacao.js'
import * as chamado from './chamado.js'
import type { Chamado, MotivoChamado } from './chamado.js'
import { prioridadeDe, prazosDe, estaVioladoAgora, prazoVigente } from './chamado.js'
import { severidade } from './prioridade.js'
import * as recurso from './recurso.js'
import type { Desfecho, MotivoRecurso, Recurso } from './recurso.js'
import { prescreveEm } from './recurso.js'
import type { Relogio } from './relogio.js'
import type { Repositorio } from './repositorio.js'
import { mudancasDePrioridade } from './trilha.js'
import type { Categoria, Eixo, Evento, Impacto, Instante, Urgencia, Usuario } from './tipos.js'

export type Falha = { ok: false; motivo: MotivoNegado | MotivoChamado | MotivoRecurso | 'CHAMADO_INEXISTENTE' | 'RECURSO_INEXISTENTE' | 'USUARIO_INEXISTENTE' }
export type Sucesso<T> = { ok: true; valor: T }
export type Resposta<T> = Sucesso<T> | Falha

const falha = (motivo: Falha['motivo']): Falha => ({ ok: false, motivo })
const ok = <T>(valor: T): Sucesso<T> => ({ ok: true, valor })

const DIAS_30_MS = 30 * 24 * 60 * 60 * 1000

export type VistaChamado = {
  chamado: Chamado
  prioridade: string | null
  prazos: { reconhecimento: Instante; resolucao: Instante } | null
  prazoVigente: Instante
  violado: boolean
  recurso: Recurso | null
  podeRecorrer: boolean
  motivoNaoPodeRecorrer: MotivoRecurso | MotivoNegado | null
  prescreveEm: Instante | null
  eventos: readonly Evento[]
}

export function criarCasosDeUso(repo: Repositorio, relogio: Relogio, novoId: () => string) {
  const autorizar = (u: Usuario, acao: Acao, alvo: { solicitanteId: string } | null = null): Falha | null => {
    const p = pode(u, acao, alvo)
    return p.ok ? null : falha(p.motivo)
  }

  /** Prescreve recursos vencidos antes de qualquer leitura ou escrita que
   *  dependa deles (MOV-11). Sem isto, um recurso esquecido bloquearia o
   *  encerramento do chamado para sempre (PRO-06). */
  const prescreverVencidos = (agora: Instante): void => {
    for (const r of repo.recursosAbertos()) {
      if (!recurso.expirouParaJulgamento(r, agora)) continue
      const s = recurso.prescrever(r, agora)
      if (s.ok) repo.salvarRecurso(s)
    }
  }

  return {
    // ---- UC-1 ------------------------------------------------------------
    abrirChamado(u: Usuario, dados: { titulo: string; descricao: string; urgencia: Urgencia }): Resposta<Chamado> {
      const neg = autorizar(u, 'ABRIR_CHAMADO')
      if (neg) return neg
      return repo.emTransacao(() => {
        const s = chamado.abrir({ id: novoId(), solicitanteId: u.id, ...dados, agora: relogio.agora() })
        if (!s.ok) return falha(s.motivo)
        repo.salvarChamado(s)
        return ok(s.entidade)
      })
    },

    // ---- UC-2 ------------------------------------------------------------
    triar(u: Usuario, chamadoId: string, dados: { categoria: Categoria; impacto: Impacto }): Resposta<Chamado> {
      const neg = autorizar(u, 'TRIAR')
      if (neg) return neg
      return repo.emTransacao(() => {
        const c = repo.chamado(chamadoId)
        if (!c) return falha('CHAMADO_INEXISTENTE')
        const s = chamado.triar(c, u.id, dados.categoria, dados.impacto, relogio.agora())
        if (!s.ok) return falha(s.motivo)
        repo.salvarChamado(s)
        return ok(s.entidade)
      })
    },

    // ---- UC-3 ------------------------------------------------------------
    reclassificar(
      u: Usuario,
      chamadoId: string,
      dados: { categoria?: Categoria; impacto?: Impacto; urgencia?: Urgencia; motivo: string },
    ): Resposta<Chamado> {
      const neg = autorizar(u, 'RECLASSIFICAR')
      if (neg) return neg
      return repo.emTransacao(() => {
        const c = repo.chamado(chamadoId)
        if (!c) return falha('CHAMADO_INEXISTENTE')
        const s = chamado.reclassificar(
          c,
          u.id,
          { categoria: dados.categoria, impacto: dados.impacto, urgencia: dados.urgencia },
          dados.motivo,
          'AGENTE',
          relogio.agora(),
        )
        if (!s.ok) return falha(s.motivo)
        repo.salvarChamado(s)
        return ok(s.entidade)
      })
    },

    // ---- UC-5: reconhecer / encerrar --------------------------------------
    reconhecer(u: Usuario, chamadoId: string): Resposta<Chamado> {
      const neg = autorizar(u, 'RECONHECER')
      if (neg) return neg
      return repo.emTransacao(() => {
        const c = repo.chamado(chamadoId)
        if (!c) return falha('CHAMADO_INEXISTENTE')
        const s = chamado.reconhecer(c, u.id, relogio.agora())
        if (!s.ok) return falha(s.motivo)
        repo.salvarChamado(s)
        return ok(s.entidade)
      })
    },

    encerrar(u: Usuario, chamadoId: string): Resposta<Chamado> {
      const neg = autorizar(u, 'ENCERRAR')
      if (neg) return neg
      const agora = relogio.agora()
      return repo.emTransacao(() => {
        prescreverVencidos(agora)
        const c = repo.chamado(chamadoId)
        if (!c) return falha('CHAMADO_INEXISTENTE')
        const r = repo.recursoDoChamado(chamadoId)
        const s = chamado.encerrar(c, u.id, agora, r?.estado === 'ABERTO')
        if (!s.ok) return falha(s.motivo)
        repo.salvarChamado(s)
        return ok(s.entidade)
      })
    },

    // ---- UC-4a -----------------------------------------------------------
    abrirRecurso(
      u: Usuario,
      chamadoId: string,
      dados: { eixos: readonly Eixo[]; justificativa: string },
    ): Resposta<Recurso> {
      const agora = relogio.agora()
      return repo.emTransacao(() => {
        const c = repo.chamado(chamadoId)
        if (!c) return falha('CHAMADO_INEXISTENTE')
        const neg = autorizar(u, 'ABRIR_RECURSO', { solicitanteId: c.solicitanteId })
        if (neg) return neg
        const s = recurso.abrir({
          id: novoId(),
          ctx: {
            id: c.id,
            solicitanteId: c.solicitanteId,
            estado: c.estado,
            ultimaMudancaClassificacao: c.ultimaMudancaClassificacao,
          },
          autorId: u.id,
          eixosContestados: dados.eixos,
          justificativa: dados.justificativa,
          recursoExistente: repo.recursoDoChamado(chamadoId) !== null,
          agora,
        })
        if (!s.ok) return falha(s.motivo)
        repo.salvarRecurso(s)
        return ok(s.entidade)
      })
    },

    // ---- UC-4b: a única composição com substância -------------------------
    julgarRecurso(
      u: Usuario,
      chamadoId: string,
      dados: {
        desfecho: Desfecho
        fundamentacao: string
        novosEixos: { impacto?: Impacto; urgencia?: Urgencia }
      },
    ): Resposta<{ recurso: Recurso; chamado: Chamado }> {
      const neg = autorizar(u, 'JULGAR_RECURSO')
      if (neg) return neg
      const agora = relogio.agora()
      return repo.emTransacao(() => {
        const c = repo.chamado(chamadoId)
        if (!c) return falha('CHAMADO_INEXISTENTE')
        const r = repo.recursoDoChamado(chamadoId)
        if (!r) return falha('RECURSO_INEXISTENTE')

        const j = recurso.julgar({
          recurso: r,
          julgadorEhGestor: u.papel === 'GESTOR',
          julgadorId: u.id,
          desfecho: dados.desfecho,
          fundamentacao: dados.fundamentacao,
          novosEixos: dados.novosEixos,
          agora,
        })
        if (!j.ok) return falha(j.motivo)
        repo.salvarRecurso(j)

        // MOV-8: recurso devolveu a intenção; quem aplica — e portanto quem
        // recalcula prioridade e reconta prazos DESDE A ABERTURA — é chamado.
        let atual = c
        if (j.novosEixos) {
          const rc = chamado.reclassificar(
            c,
            u.id,
            j.novosEixos,
            `${dados.desfecho}: ${dados.fundamentacao}`,
            'RECURSO',
            agora,
          )
          if (!rc.ok) return falha(rc.motivo)
          repo.salvarChamado(rc)
          atual = rc.entidade
        }
        return ok({ recurso: j.entidade, chamado: atual })
      })
    },

    // ---- UC-5: fila ------------------------------------------------------
    /**
     * MOV-10 — DUAS seções, nunca uma coluna só. Misturar prazo de triagem com
     * prazo de resolução na mesma ordenação faria um não triado de 60 min
     * passar na frente de um P1 de 240 min (PER-04).
     */
    consultarFila(u: Usuario, filtroCategoria?: Categoria) {
      const neg = autorizar(u, 'VER_FILA')
      if (neg) return neg
      const agora = relogio.agora()
      const todos = repo
        .chamadosAbertos()
        .filter((c) => !filtroCategoria || c.categoria === filtroCategoria)

      const decorar = (c: Chamado) => ({
        chamado: c,
        prioridade: prioridadeDe(c),
        prazo: prazoVigente(c),
        violado: estaVioladoAgora(c, agora),
      })

      const triados = todos
        .filter((c) => c.estado !== 'NAO_TRIADO')
        .map(decorar)
        .sort((a, b) => {
          if (a.violado !== b.violado) return a.violado ? -1 : 1
          const sa = severidade(a.prioridade!)
          const sb = severidade(b.prioridade!)
          if (sa !== sb) return sa - sb
          return a.prazo - b.prazo
        })

      const naoTriados = todos
        .filter((c) => c.estado === 'NAO_TRIADO')
        .map(decorar)
        .sort((a, b) => a.prazo - b.prazo)

      return ok({ triados, naoTriados, agora })
    },

    // ---- UC-6 ------------------------------------------------------------
    consultarChamado(u: Usuario, chamadoId: string): Resposta<VistaChamado> {
      const agora = relogio.agora()
      return repo.emTransacao(() => {
        prescreverVencidos(agora)
        const c = repo.chamado(chamadoId)
        if (!c) return falha('CHAMADO_INEXISTENTE')
        const neg = autorizar(u, 'VER_CHAMADO', { solicitanteId: c.solicitanteId })
        if (neg) return neg

        const r = repo.recursoDoChamado(chamadoId)
        const ctx = {
          id: c.id,
          solicitanteId: c.solicitanteId,
          estado: c.estado,
          ultimaMudancaClassificacao: c.ultimaMudancaClassificacao,
        }

        // O botão "Recorrer" só aparece quando as guardas passam; caso
        // contrário, o MOTIVO aparece no lugar dele (UX-03). Um botão que
        // falha ao ser clicado é pior que um botão ausente com explicação.
        const ensaio = recurso.abrir({
          id: 'ensaio',
          ctx,
          autorId: u.id,
          eixosContestados: ['URGENCIA'],
          justificativa: 'ensaio',
          recursoExistente: r !== null,
          agora,
        })
        const permitido = pode(u, 'ABRIR_RECURSO', { solicitanteId: c.solicitanteId })

        return ok({
          chamado: c,
          prioridade: prioridadeDe(c),
          prazos: prazosDe(c),
          prazoVigente: prazoVigente(c),
          violado: estaVioladoAgora(c, agora),
          recurso: r,
          podeRecorrer: permitido.ok && ensaio.ok,
          motivoNaoPodeRecorrer: !permitido.ok ? permitido.motivo : ensaio.ok ? null : ensaio.motivo,
          prescreveEm: prescreveEm(ctx),
          eventos: repo.eventos(chamadoId),
        } satisfies VistaChamado)
      })
    },

    meusChamados(u: Usuario) {
      const agora = relogio.agora()
      return repo.chamadosDe(u.id).map((c) => ({
        chamado: c,
        prioridade: prioridadeDe(c),
        prazo: prazoVigente(c),
        violado: estaVioladoAgora(c, agora),
      }))
    },

    /** MOV-14 — contexto de decisão do gestor, só na tela de julgamento. */
    contextoJulgamento(solicitanteId: string): number {
      return repo.recursosDoSolicitanteDesde(solicitanteId, relogio.agora() - DIAS_30_MS)
    },

    /** Projeção que CA-3 verifica: toda mudança de prioridade com ator,
     *  instante, antes/depois e motivo. */
    historicoDePrioridade(chamadoId: string) {
      return mudancasDePrioridade(repo.eventos(chamadoId))
    },
  }
}

export type CasosDeUso = ReturnType<typeof criarCasosDeUso>
