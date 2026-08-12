/**
 * M-09 sqlite-adaptador — implementa as portas de M-08 em SQLite.
 * Schema de specs/models/modelo-de-dados.md; seed de specs/datasets/seed-e-cenarios.md.
 *
 * V(2)/R1: `semear()` só roda em banco vazio — a matriz não pode ser reescrita com despesas
 * pendentes, senão a cadeia delas mudaria retroativamente e INV-6 cairia (achado A-02).
 * V(2)/R5: todas as consultas usam prepared statements (achado SEC-05).
 * V(2)/RES-01: falha de abertura derruba o processo com mensagem, não sobe pela metade.
 */
import Database from "better-sqlite3";
import type { Despesa, Estado } from "../dominio/despesa.js";
import type { Delegacao, EstadoDelegacao } from "../dominio/delegacao.js";
import type { Papel } from "../dominio/matriz-doa.js";
import type { Evento, TipoEvento } from "../dominio/trilha.js";
import type { Repositorios, Usuario } from "../dominio/portas.js";

const SCHEMA = `
CREATE TABLE IF NOT EXISTS papel (
  id TEXT PRIMARY KEY, nome TEXT NOT NULL,
  nivel INTEGER NOT NULL UNIQUE, limite_centavos INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS usuario (
  id TEXT PRIMARY KEY, nome TEXT NOT NULL,
  papel_id TEXT NOT NULL REFERENCES papel(id)
);
CREATE TABLE IF NOT EXISTS despesa (
  id TEXT PRIMARY KEY,
  solicitante_id TEXT NOT NULL REFERENCES usuario(id),
  valor_centavos INTEGER NOT NULL CHECK (valor_centavos > 0),
  descricao TEXT NOT NULL,
  estado TEXT NOT NULL CHECK (estado IN ('PENDENTE','APROVADA','REJEITADA')),
  indice_cadeia INTEGER,
  criada_em TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS delegacao (
  id TEXT PRIMARY KEY,
  delegante_id TEXT NOT NULL REFERENCES usuario(id),
  delegado_id TEXT NOT NULL REFERENCES usuario(id),
  inicio TEXT NOT NULL, fim TEXT NOT NULL,
  estado TEXT NOT NULL CHECK (estado IN ('ATIVA','REVOGADA')),
  revogada_em TEXT, revogada_por TEXT REFERENCES usuario(id),
  criada_em TEXT NOT NULL,
  CHECK (fim > inicio), CHECK (delegante_id <> delegado_id)
);
CREATE TABLE IF NOT EXISTS evento_trilha (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  despesa_id TEXT NOT NULL REFERENCES despesa(id),
  tipo TEXT NOT NULL,
  estado_anterior TEXT, estado_novo TEXT NOT NULL,
  nivel INTEGER,
  ator_id TEXT REFERENCES usuario(id),
  em_nome_de_id TEXT REFERENCES usuario(id),
  delegacao_id TEXT REFERENCES delegacao(id),
  limite_exercido_centavos INTEGER,
  motivo TEXT,
  ocorrido_em TEXT NOT NULL
);
-- Achado PERF-02: sem este índice, ler a trilha de uma despesa varre a tabela que mais cresce.
CREATE INDEX IF NOT EXISTS idx_evento_despesa ON evento_trilha(despesa_id, id);
`;

export const SEED_PAPEIS: readonly Papel[] = [
  { id: "coordenador", nome: "Coordenador", nivel: 1, limiteCentavos: 500_000 },
  { id: "gerente", nome: "Gerente", nivel: 2, limiteCentavos: 5_000_000 },
  { id: "diretor", nome: "Diretor", nivel: 3, limiteCentavos: 50_000_000 },
];

export const SEED_USUARIOS: readonly Usuario[] = [
  { id: "ana", nome: "Ana Silva", papelId: "coordenador" },
  { id: "bruno", nome: "Bruno Costa", papelId: "coordenador" },
  { id: "carla", nome: "Carla Dias", papelId: "gerente" },
  { id: "dario", nome: "Dário Melo", papelId: "gerente" },
  { id: "elisa", nome: "Elisa Rocha", papelId: "diretor" },
  { id: "fabio", nome: "Fábio Nunes", papelId: "diretor" },
];

type LinhaDespesa = {
  id: string; solicitante_id: string; valor_centavos: number; descricao: string;
  estado: string; indice_cadeia: number | null; criada_em: string;
};
type LinhaDelegacao = {
  id: string; delegante_id: string; delegado_id: string; inicio: string; fim: string;
  estado: string; revogada_em: string | null; revogada_por: string | null; criada_em: string;
};
type LinhaEvento = {
  despesa_id: string; tipo: string; estado_anterior: string | null; estado_novo: string;
  nivel: number | null; ator_id: string | null; em_nome_de_id: string | null;
  delegacao_id: string | null; limite_exercido_centavos: number | null;
  motivo: string | null; ocorrido_em: string;
};

export type Adaptador = Repositorios & {
  /** Só semeia banco vazio; devolve false se já havia dados. */
  semear(papeis?: readonly Papel[], usuarios?: readonly Usuario[]): boolean;
};

export function abrir(caminho: string): Adaptador {
  let db: Database.Database;
  try {
    db = new Database(caminho);
    db.pragma("journal_mode = WAL");
    db.pragma("foreign_keys = ON");
    db.exec(SCHEMA);
  } catch (e) {
    // RES-01: sem banco não há sistema. Falhar aqui, com mensagem, em vez de subir quebrado.
    throw new Error(
      `Não foi possível abrir o banco em "${caminho}": ${String(e)}. ` +
        `Verifique permissão de escrita e espaço em disco.`,
    );
  }

  const st = {
    salvarDespesa: db.prepare(
      `INSERT INTO despesa (id, solicitante_id, valor_centavos, descricao, estado, indice_cadeia, criada_em)
       VALUES (@id, @solicitante_id, @valor_centavos, @descricao, @estado, @indice_cadeia, @criada_em)
       ON CONFLICT(id) DO UPDATE SET estado = excluded.estado, indice_cadeia = excluded.indice_cadeia`,
    ),
    despesaPorId: db.prepare(`SELECT * FROM despesa WHERE id = ?`),
    despesasPendentes: db.prepare(`SELECT * FROM despesa WHERE estado = 'PENDENTE' ORDER BY criada_em, id`),
    despesasTodas: db.prepare(`SELECT * FROM despesa ORDER BY criada_em, id`),
    salvarDelegacao: db.prepare(
      `INSERT INTO delegacao (id, delegante_id, delegado_id, inicio, fim, estado, revogada_em, revogada_por, criada_em)
       VALUES (@id, @delegante_id, @delegado_id, @inicio, @fim, @estado, @revogada_em, @revogada_por, @criada_em)
       ON CONFLICT(id) DO UPDATE SET estado = excluded.estado, revogada_em = excluded.revogada_em,
                                     revogada_por = excluded.revogada_por`,
    ),
    delegacaoPorId: db.prepare(`SELECT * FROM delegacao WHERE id = ?`),
    delegacoesTodas: db.prepare(`SELECT * FROM delegacao ORDER BY criada_em, id`),
    delegacoesPorDelegante: db.prepare(`SELECT * FROM delegacao WHERE delegante_id = ? ORDER BY criada_em, id`),
    usuarioPorId: db.prepare(`SELECT * FROM usuario WHERE id = ?`),
    usuariosTodos: db.prepare(`SELECT u.* FROM usuario u JOIN papel p ON p.id = u.papel_id ORDER BY p.nivel, u.nome`),
    papeisTodos: db.prepare(`SELECT * FROM papel ORDER BY nivel`),
    anexarEvento: db.prepare(
      `INSERT INTO evento_trilha (despesa_id, tipo, estado_anterior, estado_novo, nivel, ator_id,
                                  em_nome_de_id, delegacao_id, limite_exercido_centavos, motivo, ocorrido_em)
       VALUES (@despesa_id, @tipo, @estado_anterior, @estado_novo, @nivel, @ator_id,
               @em_nome_de_id, @delegacao_id, @limite_exercido_centavos, @motivo, @ocorrido_em)`,
    ),
    eventosPorDespesa: db.prepare(`SELECT * FROM evento_trilha WHERE despesa_id = ? ORDER BY id`),
    contarPapeis: db.prepare(`SELECT COUNT(*) AS n FROM papel`),
    inserirPapel: db.prepare(`INSERT INTO papel (id, nome, nivel, limite_centavos) VALUES (?, ?, ?, ?)`),
    inserirUsuario: db.prepare(`INSERT INTO usuario (id, nome, papel_id) VALUES (?, ?, ?)`),
  };

  const paraDespesa = (l: LinhaDespesa): Despesa => ({
    id: l.id,
    solicitanteId: l.solicitante_id,
    valorCentavos: l.valor_centavos,
    descricao: l.descricao,
    estado: l.estado as Estado,
    indiceCadeia: l.indice_cadeia,
    criadaEm: l.criada_em,
  });
  const paraDelegacao = (l: LinhaDelegacao): Delegacao => ({
    id: l.id,
    deleganteId: l.delegante_id,
    delegadoId: l.delegado_id,
    inicio: l.inicio,
    fim: l.fim,
    estado: l.estado as EstadoDelegacao,
    revogadaEm: l.revogada_em,
    revogadaPor: l.revogada_por,
    criadaEm: l.criada_em,
  });
  const paraEvento = (l: LinhaEvento): Evento => ({
    despesaId: l.despesa_id,
    tipo: l.tipo as TipoEvento,
    estadoAnterior: l.estado_anterior,
    estadoNovo: l.estado_novo,
    nivel: l.nivel,
    atorId: l.ator_id,
    emNomeDeId: l.em_nome_de_id,
    delegacaoId: l.delegacao_id,
    limiteExercidoCentavos: l.limite_exercido_centavos,
    motivo: l.motivo,
    ocorridoEm: l.ocorrido_em,
  });

  const repos: Repositorios = {
    despesas: {
      salvar: (d) =>
        void st.salvarDespesa.run({
          id: d.id, solicitante_id: d.solicitanteId, valor_centavos: d.valorCentavos,
          descricao: d.descricao, estado: d.estado, indice_cadeia: d.indiceCadeia, criada_em: d.criadaEm,
        }),
      porId: (id) => {
        const l = st.despesaPorId.get(id) as LinhaDespesa | undefined;
        return l ? paraDespesa(l) : undefined;
      },
      pendentes: () => (st.despesasPendentes.all() as LinhaDespesa[]).map(paraDespesa),
      todas: () => (st.despesasTodas.all() as LinhaDespesa[]).map(paraDespesa),
    },
    delegacoes: {
      salvar: (d) =>
        void st.salvarDelegacao.run({
          id: d.id, delegante_id: d.deleganteId, delegado_id: d.delegadoId, inicio: d.inicio,
          fim: d.fim, estado: d.estado, revogada_em: d.revogadaEm, revogada_por: d.revogadaPor,
          criada_em: d.criadaEm,
        }),
      porId: (id) => {
        const l = st.delegacaoPorId.get(id) as LinhaDelegacao | undefined;
        return l ? paraDelegacao(l) : undefined;
      },
      todas: () => (st.delegacoesTodas.all() as LinhaDelegacao[]).map(paraDelegacao),
      porDelegante: (id) => (st.delegacoesPorDelegante.all(id) as LinhaDelegacao[]).map(paraDelegacao),
    },
    usuarios: {
      // Mapeamento explícito, como em todos os outros agregados: a linha do SQLite usa
      // `papel_id` e o tipo de domínio usa `papelId`. Um `as Usuario` direto compila e
      // devolve `papelId: undefined` em silêncio.
      porId: (id) => {
        const l = st.usuarioPorId.get(id) as { id: string; nome: string; papel_id: string } | undefined;
        return l ? { id: l.id, nome: l.nome, papelId: l.papel_id } : undefined;
      },
      todos: () =>
        (st.usuariosTodos.all() as { id: string; nome: string; papel_id: string }[]).map((u) => ({
          id: u.id, nome: u.nome, papelId: u.papel_id,
        })),
    },
    papeis: {
      todos: () =>
        (st.papeisTodos.all() as { id: string; nome: string; nivel: number; limite_centavos: number }[]).map(
          (p) => ({ id: p.id, nome: p.nome, nivel: p.nivel, limiteCentavos: p.limite_centavos }),
        ),
    },
    trilha: {
      anexar: (e) =>
        void st.anexarEvento.run({
          despesa_id: e.despesaId, tipo: e.tipo, estado_anterior: e.estadoAnterior,
          estado_novo: e.estadoNovo, nivel: e.nivel, ator_id: e.atorId, em_nome_de_id: e.emNomeDeId,
          delegacao_id: e.delegacaoId, limite_exercido_centavos: e.limiteExercidoCentavos,
          motivo: e.motivo, ocorrido_em: e.ocorridoEm,
        }),
      porDespesa: (id) => (st.eventosPorDespesa.all(id) as LinhaEvento[]).map(paraEvento),
    },
    emTransacao: <T,>(fn: () => T): T => db.transaction(fn)(),
    fechar: () => db.close(),
  };

  /**
   * O seed é a ÚNICA escrita em `papel`/`usuario` do sistema (matriz não editável em runtime
   * — escopo negativo), por isso M-08 não expõe repositório de escrita para eles: o seed é
   * um closure do adaptador, não um contrato de domínio.
   * Idempotente por construção (achado IMP-05): só semeia banco vazio.
   */
  const semear = (
    papeis: readonly Papel[] = SEED_PAPEIS,
    usuarios: readonly Usuario[] = SEED_USUARIOS,
  ): boolean => {
    if (repos.papeis.todos().length > 0) return false;
    repos.emTransacao(() => {
      for (const p of papeis) st.inserirPapel.run(p.id, p.nome, p.nivel, p.limiteCentavos);
      for (const u of usuarios) st.inserirUsuario.run(u.id, u.nome, u.papelId);
    });
    return true;
  };

  return { ...repos, semear };
}
