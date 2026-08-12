/**
 * M-09 repositorio — portas, Data Mapper SQLite, esquema, migração e transação.
 *
 * MOV-9: NÃO existe "salvar entidade". Só existe `salvar({entidade, eventos})`.
 * O que MOV-2 prometia e não entregava — "impossível violar a trilha" — passa a
 * valer por tipo aqui: é impossível gravar o estado sem gravar os eventos,
 * porque não há função que aceite só o estado (IMP-04).
 *
 * O domínio ignora que existe SQLite: o mapeamento entre entidades e linhas
 * mora inteiramente neste módulo (Repository + Data Mapper).
 *
 * ⚠️ RES-01, aceito: sob SQLITE_BUSY, corrupção ou disco cheio, a transação
 * falha e o erro sobe explícito até a UI. Não há repetição silenciosa —
 * repetir uma escrita de classificação sem o operador saber seria pior.
 *
 * depends-on: chamado, recurso, trilha (tipos)
 */

import Database from 'better-sqlite3'
import { readFileSync } from 'node:fs'
import type { Chamado } from './chamado.js'
import type { Recurso } from './recurso.js'
import type { Evento, Instante, Resultado, Usuario } from './tipos.js'

const ESQUEMA = `
CREATE TABLE IF NOT EXISTS usuarios (
  id    TEXT PRIMARY KEY,
  nome  TEXT NOT NULL,
  papel TEXT NOT NULL CHECK (papel IN ('SOLICITANTE','AGENTE','GESTOR'))
);

-- Chamado guarda os EIXOS e os instantes. Prioridade e prazos NAO sao colunas:
-- sao derivados na leitura por chamado.prioridadeDe/prazosDe, de modo que nao
-- existe valor gravado que possa divergir da politica vigente (CTL-01).
CREATE TABLE IF NOT EXISTS chamados (
  id                          TEXT PRIMARY KEY,
  solicitante_id              TEXT NOT NULL REFERENCES usuarios(id),
  titulo                      TEXT NOT NULL,
  descricao                   TEXT NOT NULL,
  urgencia                    TEXT NOT NULL CHECK (urgencia IN ('ALTA','MEDIA','BAIXA')),
  categoria                   TEXT,
  impacto                     TEXT CHECK (impacto IS NULL OR impacto IN ('ALTO','MEDIO','BAIXO')),
  estado                      TEXT NOT NULL CHECK (estado IN ('NAO_TRIADO','TRIADO','RECONHECIDO','ENCERRADO')),
  aberto_em                   INTEGER NOT NULL,
  triado_em                   INTEGER,
  ultima_mudanca_classificacao INTEGER,
  reconhecido_em              INTEGER,
  encerrado_em                INTEGER
);

CREATE TABLE IF NOT EXISTS recursos (
  id                TEXT PRIMARY KEY,
  chamado_id        TEXT NOT NULL UNIQUE REFERENCES chamados(id),
  autor_id          TEXT NOT NULL REFERENCES usuarios(id),
  eixos_contestados TEXT NOT NULL,
  justificativa     TEXT NOT NULL,
  aberto_em         INTEGER NOT NULL,
  estado            TEXT NOT NULL,
  julgador_id       TEXT,
  julgado_em        INTEGER,
  fundamentacao     TEXT
);

-- Somente-insercao (premissa A4). Nenhum UPDATE, nenhum DELETE em lugar algum
-- deste modulo.
CREATE TABLE IF NOT EXISTS eventos (
  seq             INTEGER PRIMARY KEY AUTOINCREMENT,
  chamado_id      TEXT NOT NULL REFERENCES chamados(id),
  tipo            TEXT NOT NULL,
  ator_id         TEXT NOT NULL,
  instante        INTEGER NOT NULL,
  origem          TEXT NOT NULL,
  versao_politica TEXT,
  mudancas        TEXT NOT NULL,
  motivo          TEXT
);

CREATE INDEX IF NOT EXISTS idx_eventos_chamado ON eventos(chamado_id, seq);
CREATE INDEX IF NOT EXISTS idx_chamados_estado ON chamados(estado, aberto_em);
`

type LinhaChamado = {
  id: string
  solicitante_id: string
  titulo: string
  descricao: string
  urgencia: string
  categoria: string | null
  impacto: string | null
  estado: string
  aberto_em: number
  triado_em: number | null
  ultima_mudanca_classificacao: number | null
  reconhecido_em: number | null
  encerrado_em: number | null
}

type LinhaRecurso = {
  id: string
  chamado_id: string
  autor_id: string
  eixos_contestados: string
  justificativa: string
  aberto_em: number
  estado: string
  julgador_id: string | null
  julgado_em: number | null
  fundamentacao: string | null
}

type LinhaEvento = {
  chamado_id: string
  tipo: string
  ator_id: string
  instante: number
  origem: string
  versao_politica: string | null
  mudancas: string
  motivo: string | null
}

const paraChamado = (l: LinhaChamado): Chamado => ({
  id: l.id,
  solicitanteId: l.solicitante_id,
  titulo: l.titulo,
  descricao: l.descricao,
  urgencia: l.urgencia as Chamado['urgencia'],
  categoria: l.categoria as Chamado['categoria'],
  impacto: l.impacto as Chamado['impacto'],
  estado: l.estado as Chamado['estado'],
  abertoEm: l.aberto_em,
  triadoEm: l.triado_em,
  ultimaMudancaClassificacao: l.ultima_mudanca_classificacao,
  reconhecidoEm: l.reconhecido_em,
  encerradoEm: l.encerrado_em,
})

const paraRecurso = (l: LinhaRecurso): Recurso => ({
  id: l.id,
  chamadoId: l.chamado_id,
  autorId: l.autor_id,
  eixosContestados: JSON.parse(l.eixos_contestados),
  justificativa: l.justificativa,
  abertoEm: l.aberto_em,
  estado: l.estado as Recurso['estado'],
  julgadorId: l.julgador_id,
  julgadoEm: l.julgado_em,
  fundamentacao: l.fundamentacao,
})

const paraEvento = (l: LinhaEvento): Evento => ({
  chamadoId: l.chamado_id,
  tipo: l.tipo as Evento['tipo'],
  atorId: l.ator_id,
  instante: l.instante,
  origem: l.origem as Evento['origem'],
  versaoPolitica: l.versao_politica,
  mudancas: JSON.parse(l.mudancas),
  motivo: l.motivo,
})

export interface Repositorio {
  emTransacao<T>(fn: () => T): T
  /** Grava estado E eventos. Não há sobrecarga que aceite só o estado (MOV-9). */
  salvarChamado(r: Resultado<Chamado>): void
  salvarRecurso(r: Resultado<Recurso>): void
  chamado(id: string): Chamado | null
  chamadosAbertos(): readonly Chamado[]
  chamadosDe(solicitanteId: string): readonly Chamado[]
  recursoDoChamado(chamadoId: string): Recurso | null
  recursosAbertos(): readonly Recurso[]
  eventos(chamadoId: string): readonly Evento[]
  usuario(id: string): Usuario | null
  usuarios(): readonly Usuario[]
  /** Contexto de decisão do gestor no julgamento (MOV-14). Só isto — não há
   *  consulta agregada por solicitante em nenhuma outra tela. */
  recursosDoSolicitanteDesde(solicitanteId: string, desde: Instante): number
  fechar(): void
}

export function abrirRepositorio(caminhoBanco: string, caminhoSeed?: string): Repositorio {
  const db = new Database(caminhoBanco)
  db.pragma('journal_mode = WAL')
  db.pragma('foreign_keys = ON')
  db.exec(ESQUEMA)

  if (caminhoSeed) {
    const seed = JSON.parse(readFileSync(caminhoSeed, 'utf8')) as { usuarios: Usuario[] }
    const ins = db.prepare('INSERT OR IGNORE INTO usuarios (id, nome, papel) VALUES (?, ?, ?)')
    const carregar = db.transaction((us: Usuario[]) => {
      for (const u of us) ins.run(u.id, u.nome, u.papel)
    })
    carregar(seed.usuarios)
  }

  const insEvento = db.prepare(
    `INSERT INTO eventos (chamado_id, tipo, ator_id, instante, origem, versao_politica, mudancas, motivo)
     VALUES (@chamado_id, @tipo, @ator_id, @instante, @origem, @versao_politica, @mudancas, @motivo)`,
  )
  const gravarEventos = (eventos: readonly Evento[]) => {
    for (const e of eventos) {
      insEvento.run({
        chamado_id: e.chamadoId,
        tipo: e.tipo,
        ator_id: e.atorId,
        instante: e.instante,
        origem: e.origem,
        versao_politica: e.versaoPolitica,
        mudancas: JSON.stringify(e.mudancas),
        motivo: e.motivo,
      })
    }
  }

  const upsertChamado = db.prepare(
    `INSERT INTO chamados (id, solicitante_id, titulo, descricao, urgencia, categoria, impacto, estado,
                           aberto_em, triado_em, ultima_mudanca_classificacao, reconhecido_em, encerrado_em)
     VALUES (@id, @solicitante_id, @titulo, @descricao, @urgencia, @categoria, @impacto, @estado,
             @aberto_em, @triado_em, @ultima_mudanca_classificacao, @reconhecido_em, @encerrado_em)
     ON CONFLICT(id) DO UPDATE SET
       urgencia = excluded.urgencia, categoria = excluded.categoria, impacto = excluded.impacto,
       estado = excluded.estado, triado_em = excluded.triado_em,
       ultima_mudanca_classificacao = excluded.ultima_mudanca_classificacao,
       reconhecido_em = excluded.reconhecido_em, encerrado_em = excluded.encerrado_em`,
  )

  const upsertRecurso = db.prepare(
    `INSERT INTO recursos (id, chamado_id, autor_id, eixos_contestados, justificativa, aberto_em,
                           estado, julgador_id, julgado_em, fundamentacao)
     VALUES (@id, @chamado_id, @autor_id, @eixos_contestados, @justificativa, @aberto_em,
             @estado, @julgador_id, @julgado_em, @fundamentacao)
     ON CONFLICT(id) DO UPDATE SET
       estado = excluded.estado, julgador_id = excluded.julgador_id,
       julgado_em = excluded.julgado_em, fundamentacao = excluded.fundamentacao`,
  )

  return {
    emTransacao<T>(fn: () => T): T {
      return db.transaction(fn)()
    },

    salvarChamado({ entidade: c, eventos }) {
      upsertChamado.run({
        id: c.id,
        solicitante_id: c.solicitanteId,
        titulo: c.titulo,
        descricao: c.descricao,
        urgencia: c.urgencia,
        categoria: c.categoria,
        impacto: c.impacto,
        estado: c.estado,
        aberto_em: c.abertoEm,
        triado_em: c.triadoEm,
        ultima_mudanca_classificacao: c.ultimaMudancaClassificacao,
        reconhecido_em: c.reconhecidoEm,
        encerrado_em: c.encerradoEm,
      })
      gravarEventos(eventos)
    },

    salvarRecurso({ entidade: r, eventos }) {
      upsertRecurso.run({
        id: r.id,
        chamado_id: r.chamadoId,
        autor_id: r.autorId,
        eixos_contestados: JSON.stringify(r.eixosContestados),
        justificativa: r.justificativa,
        aberto_em: r.abertoEm,
        estado: r.estado,
        julgador_id: r.julgadorId,
        julgado_em: r.julgadoEm,
        fundamentacao: r.fundamentacao,
      })
      gravarEventos(eventos)
    },

    chamado(id) {
      const l = db.prepare('SELECT * FROM chamados WHERE id = ?').get(id) as LinhaChamado | undefined
      return l ? paraChamado(l) : null
    },

    chamadosAbertos() {
      const ls = db
        .prepare(`SELECT * FROM chamados WHERE estado <> 'ENCERRADO' ORDER BY aberto_em ASC`)
        .all() as LinhaChamado[]
      return ls.map(paraChamado)
    },

    chamadosDe(solicitanteId) {
      const ls = db
        .prepare('SELECT * FROM chamados WHERE solicitante_id = ? ORDER BY aberto_em DESC')
        .all(solicitanteId) as LinhaChamado[]
      return ls.map(paraChamado)
    },

    recursoDoChamado(chamadoId) {
      const l = db.prepare('SELECT * FROM recursos WHERE chamado_id = ?').get(chamadoId) as LinhaRecurso | undefined
      return l ? paraRecurso(l) : null
    },

    recursosAbertos() {
      const ls = db.prepare(`SELECT * FROM recursos WHERE estado = 'ABERTO'`).all() as LinhaRecurso[]
      return ls.map(paraRecurso)
    },

    eventos(chamadoId) {
      const ls = db
        .prepare('SELECT * FROM eventos WHERE chamado_id = ? ORDER BY seq ASC')
        .all(chamadoId) as LinhaEvento[]
      return ls.map(paraEvento)
    },

    usuario(id) {
      const l = db.prepare('SELECT * FROM usuarios WHERE id = ?').get(id) as Usuario | undefined
      return l ?? null
    },

    usuarios() {
      return db.prepare('SELECT * FROM usuarios ORDER BY papel, nome').all() as Usuario[]
    },

    recursosDoSolicitanteDesde(solicitanteId, desde) {
      const r = db
        .prepare('SELECT COUNT(*) AS n FROM recursos WHERE autor_id = ? AND aberto_em >= ?')
        .get(solicitanteId, desde) as { n: number }
      return r.n
    },

    fechar() {
      db.close()
    },
  }
}
