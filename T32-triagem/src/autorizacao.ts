/**
 * M-08 autorizacao — RBAC mais legitimidade sobre o ALVO.
 *
 * Devolve permissão COM MOTIVO enumerado, nunca um booleano (LIN-03): a tela e
 * o teste precisam distinguir "não é o seu chamado" de "seu papel não faz
 * isso", e um `false` não distingue nada.
 *
 * A matriz de autorização vem de specs/models/modelo-de-dominio.md. A única
 * linha com condição sobre o ALVO — e não só sobre o papel — é "abrir recurso":
 * apenas o solicitante DAQUELE chamado.
 *
 * ⚠️ Risco aceito e registrado (SEG-01 / premissa A8): não há prova de
 * identidade. O cookie de sessão assinado impede a forja trivial do papel a
 * cada requisição, mas quem escolhe ser GESTOR na tela de entrada, é.
 * A autorização é real e testada; a AUTENTICAÇÃO está no escopo negativo.
 *
 * depends-on: —
 */

import type { Papel, Usuario } from './tipos.js'

export type Acao =
  | 'ABRIR_CHAMADO'
  | 'TRIAR'
  | 'RECLASSIFICAR'
  | 'RECONHECER'
  | 'ENCERRAR'
  | 'ABRIR_RECURSO'
  | 'JULGAR_RECURSO'
  | 'VER_FILA'
  | 'VER_CHAMADO'

export type MotivoNegado = 'PAPEL_INSUFICIENTE' | 'SEM_LEGITIMIDADE'

export type Permissao = { readonly ok: true } | { readonly ok: false; readonly motivo: MotivoNegado }

const PERMITIDO: Permissao = { ok: true }
const negado = (motivo: MotivoNegado): Permissao => ({ ok: false, motivo })

/** Alvo da ação, quando ela recai sobre um chamado específico. */
export type Alvo = { readonly solicitanteId: string } | null

const PAPEIS_POR_ACAO: Record<Acao, readonly Papel[]> = {
  ABRIR_CHAMADO: ['SOLICITANTE', 'AGENTE', 'GESTOR'],
  TRIAR: ['AGENTE', 'GESTOR'],
  RECLASSIFICAR: ['AGENTE', 'GESTOR'],
  RECONHECER: ['AGENTE', 'GESTOR'],
  ENCERRAR: ['AGENTE', 'GESTOR'],
  ABRIR_RECURSO: ['SOLICITANTE'],
  JULGAR_RECURSO: ['GESTOR'],
  VER_FILA: ['AGENTE', 'GESTOR'],
  VER_CHAMADO: ['SOLICITANTE', 'AGENTE', 'GESTOR'],
}

export function pode(usuario: Usuario, acao: Acao, alvo: Alvo = null): Permissao {
  if (!PAPEIS_POR_ACAO[acao].includes(usuario.papel)) return negado('PAPEL_INSUFICIENTE')

  // Legitimidade sobre o alvo: só o solicitante do próprio chamado recorre (B-5),
  // e um solicitante só lê os chamados que são dele (SEG-04 — sem isso, ids
  // sequenciais expõem chamados alheios por enumeração).
  if (usuario.papel === 'SOLICITANTE' && alvo !== null) {
    if ((acao === 'ABRIR_RECURSO' || acao === 'VER_CHAMADO') && alvo.solicitanteId !== usuario.id) {
      return negado('SEM_LEGITIMIDADE')
    }
  }
  return PERMITIDO
}
