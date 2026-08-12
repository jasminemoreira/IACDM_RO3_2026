/**
 * M-09 repositorio — portas nomeadas (Repository) + Data Mapper sobre node:sqlite.
 * Unico modulo que conhece SQL. Statements SEMPRE parametrizados (SEC-07).
 *
 * V(3), SEC-11: as operacoes de ESCRITA exigem um token `Transacao` como parametro.
 * Escrever fora de `emTransacao` deixa de ser proibido por convencao e passa a ser
 * impossivel pelo tipo — o handle do banco nunca sai daqui.
 *
 * V(3), MEC-05: WAL REMOVIDO. Ele existe para permitir leitores concorrentes com um
 * escritor, e a trava exclusiva (A6, ASS-07) anula o motivo de usa-lo.
 *
 * V(3), REG-05: remocao de alvo e LOGICA (`removido_em`), nunca fisica — auditoria
 * exige que observacoes e pedidos historicos sobrevivam.
 *
 * DDL: specs/models/schema.md.
 */

import { DatabaseSync } from 'node:sqlite';
import type { Ator } from './autorizacao.ts';
import type { Observacao } from './certificado.ts';
import type { Pedido, EstadoPedido, Papel } from './pedido.ts';
import { anexar as encadear, GENESIS, type Entrada, type Evento, type TipoEvento } from './trilha.ts';
import type { Transacao } from './tipos.ts';
import type { Limiares } from './politica-limiar.ts';
import type { TipoErroSonda } from './sonda-tls.ts';

export type Alvo = {
  readonly id: string;
  readonly host: string;
  readonly porta: number;
  /** GOV-05: referencia a ator(id), nao texto livre. */
  readonly donoId: string;
  readonly limiares: Limiares;
  readonly criadoEm: Date;
  readonly removidoEm: Date | null;
};

export type ObservacaoPersistida = Observacao & {
  readonly id: string;
  readonly alvoId: string;
  readonly vistoPrimeiroEm: Date;
  readonly vistoUltimaVez: Date;
};

export type Varredura = {
  readonly id: string;
  readonly iniciadaEm: Date;
  readonly concluidaEm: Date | null;
  readonly interrompida: boolean;
  readonly total: number;
  readonly ok: number;
  readonly falha: number;
};

const DDL = `
PRAGMA foreign_keys = ON;
PRAGMA locking_mode = EXCLUSIVE;

CREATE TABLE IF NOT EXISTS ator (
  id TEXT PRIMARY KEY, nome TEXT NOT NULL UNIQUE,
  papel TEXT NOT NULL CHECK (papel IN ('solicitante','aprovador','auditor')),
  senha_hash TEXT NOT NULL, senha_salt TEXT NOT NULL,
  ativo INTEGER NOT NULL DEFAULT 1, criado_em TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS alvo (
  id TEXT PRIMARY KEY, host TEXT NOT NULL, porta INTEGER NOT NULL,
  dono_id TEXT NOT NULL REFERENCES ator(id),
  limiar_aviso INTEGER NOT NULL, limiar_atencao INTEGER NOT NULL, limiar_critico INTEGER NOT NULL,
  criado_em TEXT NOT NULL, removido_em TEXT,
  UNIQUE (host, porta)
);

CREATE TABLE IF NOT EXISTS observacao (
  id TEXT PRIMARY KEY, alvo_id TEXT NOT NULL REFERENCES alvo(id),
  fingerprint256 TEXT NOT NULL, issuer TEXT NOT NULL, subject TEXT NOT NULL,
  serial TEXT NOT NULL, san TEXT NOT NULL,
  not_before TEXT NOT NULL, not_after_folha TEXT NOT NULL, not_after_efetivo TEXT NOT NULL,
  profundidade INTEGER NOT NULL,
  visto_primeiro_em TEXT NOT NULL, visto_ultima_vez TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_obs_alvo ON observacao (alvo_id, visto_ultima_vez DESC);

CREATE TABLE IF NOT EXISTS varredura (
  id TEXT PRIMARY KEY, iniciada_em TEXT NOT NULL, concluida_em TEXT,
  interrompida INTEGER NOT NULL DEFAULT 0,
  alvos_total INTEGER NOT NULL, alvos_ok INTEGER NOT NULL, alvos_falha INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS falha_sonda (
  alvo_id TEXT NOT NULL REFERENCES alvo(id),
  tipo TEXT NOT NULL CHECK (tipo IN ('timeout','recusado','dns','tls','cadeia-grande')),
  detalhe TEXT NOT NULL, ocorrencias INTEGER NOT NULL DEFAULT 1,
  primeira_ocorrencia TEXT NOT NULL, ultima_ocorrencia TEXT NOT NULL,
  PRIMARY KEY (alvo_id, tipo)
);

CREATE TABLE IF NOT EXISTS pedido (
  id TEXT PRIMARY KEY, alvo_id TEXT NOT NULL REFERENCES alvo(id),
  estado TEXT NOT NULL CHECK (estado IN
    ('pendente','aprovado','fechado','rejeitado','cancelado','expirado-sem-emissao')),
  solicitante_id TEXT NOT NULL REFERENCES ator(id),
  aprovador_id TEXT REFERENCES ator(id),
  motivo TEXT, evidencia_id TEXT REFERENCES observacao(id),
  aberto_em TEXT NOT NULL, decidido_em TEXT, fechado_em TEXT
);
CREATE INDEX IF NOT EXISTS idx_pedido_alvo_estado ON pedido (alvo_id, estado);

CREATE TABLE IF NOT EXISTS trilha (
  i INTEGER PRIMARY KEY, tipo TEXT NOT NULL,
  ator_id TEXT REFERENCES ator(id), alvo_id TEXT REFERENCES alvo(id),
  pedido_id TEXT REFERENCES pedido(id), ref_indice INTEGER,
  dados TEXT NOT NULL, registrado_em TEXT NOT NULL,
  hash_anterior TEXT NOT NULL, hash TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_trilha_alvo ON trilha (alvo_id, i);
`;

type Linha = Record<string, string | number | bigint | null | Uint8Array>;

const iso = (d: Date) => d.toISOString();
const data = (v: unknown) => new Date(String(v));
const dataOuNulo = (v: unknown) => (v === null || v === undefined ? null : new Date(String(v)));

export type PortaAlvos = {
  salvar(tx: Transacao, a: Alvo): void;
  listar(): Alvo[];
  buscarPorId(id: string): Alvo | null;
  remover(tx: Transacao, id: string, agora: Date): void;
  salvarObservacao(tx: Transacao, o: ObservacaoPersistida): void;
  tocarObservacao(tx: Transacao, id: string, agora: Date): void;
  ultimaObservacao(alvoId: string): ObservacaoPersistida | null;
};

export type PortaPedidos = {
  salvar(tx: Transacao, p: Pedido): void;
  buscarPorId(id: string): Pedido | null;
  abertoDe(alvoId: string): Pedido | null;
  aprovadoDe(alvoId: string): Pedido | null;
  listar(): Pedido[];
};

export type PortaTrilha = {
  anexar(tx: Transacao, e: Entrada): void;
  /** Encadeia e persiste em um passo. Existe para que a logica da cadeia viva em UM
   *  lugar: duplica-la nos dois casos de uso seria duas chances de errar o hash. */
  registrar(tx: Transacao, e: Evento, agora: Date): Entrada;
  ponta(): { hash: string; i: number; registradoEm: Date | null };
  listar(alvoId?: string): Entrada[];
  contarPorTipo(alvoId: string, tipo: TipoEvento): number;
};

export type PortaAtores = {
  salvar(tx: Transacao, a: Ator): void;
  buscarPorId(id: string): Ator | null;
  buscarPorNome(nome: string): Ator | null;
  listar(): Ator[];
};

/** 5a porta: V(2) criou as tabelas `varredura` e `falha_sonda` mas a lista de portas
 *  do documento ficou com as 4 originais. Divergencia corrigida aqui — mesmo modulo,
 *  mesmo adaptador. Registrada como decisao da Fase 5. */
export type PortaVarreduras = {
  salvar(tx: Transacao, v: Varredura): void;
  registrarFalha(tx: Transacao, alvoId: string, tipo: TipoErroSonda, detalhe: string, agora: Date): void;
  ultima(): Varredura | null;
  marcarOrfas(tx: Transacao): number;
};

export type Repositorio = {
  alvos: PortaAlvos;
  pedidos: PortaPedidos;
  trilha: PortaTrilha;
  atores: PortaAtores;
  varreduras: PortaVarreduras;
  /** Unica forma de escrita. RES-03: fato e trilha commitam juntos, ou nenhum dos dois. */
  emTransacao<T>(fn: (tx: Transacao) => T): T;
  fechar(): void;
};

export function criarRepositorio(caminho: string): Repositorio {
  const db = new DatabaseSync(caminho);
  db.exec(DDL);
  const tx = {} as Transacao; // token opaco; nunca carrega o handle

  const paraAlvo = (l: Linha): Alvo => ({
    id: String(l['id']),
    host: String(l['host']),
    porta: Number(l['porta']),
    donoId: String(l['dono_id']),
    limiares: {
      aviso: Number(l['limiar_aviso']),
      atencao: Number(l['limiar_atencao']),
      critico: Number(l['limiar_critico']),
    },
    criadoEm: data(l['criado_em']),
    removidoEm: dataOuNulo(l['removido_em']),
  });

  const paraObservacao = (l: Linha): ObservacaoPersistida => ({
    id: String(l['id']),
    alvoId: String(l['alvo_id']),
    fingerprint256: String(l['fingerprint256']),
    issuer: String(l['issuer']),
    subject: String(l['subject']),
    serial: String(l['serial']),
    san: JSON.parse(String(l['san'])) as string[],
    notBefore: data(l['not_before']),
    notAfterFolha: data(l['not_after_folha']),
    notAfterEfetivo: data(l['not_after_efetivo']),
    profundidade: Number(l['profundidade']),
    vistoPrimeiroEm: data(l['visto_primeiro_em']),
    vistoUltimaVez: data(l['visto_ultima_vez']),
  });

  const paraPedido = (l: Linha): Pedido => ({
    id: String(l['id']),
    alvoId: String(l['alvo_id']),
    estado: String(l['estado']) as EstadoPedido,
    solicitanteId: String(l['solicitante_id']),
    aprovadorId: l['aprovador_id'] === null ? null : String(l['aprovador_id']),
    motivo: l['motivo'] === null ? null : String(l['motivo']),
    evidenciaId: l['evidencia_id'] === null ? null : String(l['evidencia_id']),
    abertoEm: data(l['aberto_em']),
    decididoEm: dataOuNulo(l['decidido_em']),
    fechadoEm: dataOuNulo(l['fechado_em']),
  });

  const paraAtor = (l: Linha): Ator => ({
    id: String(l['id']),
    nome: String(l['nome']),
    papel: String(l['papel']) as Papel,
    senhaHash: String(l['senha_hash']),
    senhaSalt: String(l['senha_salt']),
    ativo: Number(l['ativo']) === 1,
    criadoEm: data(l['criado_em']),
  });

  const paraEntrada = (l: Linha): Entrada => ({
    i: Number(l['i']),
    tipo: String(l['tipo']) as TipoEvento,
    atorId: l['ator_id'] === null ? null : String(l['ator_id']),
    alvoId: l['alvo_id'] === null ? null : String(l['alvo_id']),
    pedidoId: l['pedido_id'] === null ? null : String(l['pedido_id']),
    refIndice: l['ref_indice'] === null ? null : Number(l['ref_indice']),
    dados: JSON.parse(String(l['dados'])) as Record<string, unknown>,
    registradoEm: data(l['registrado_em']),
    hashAnterior: String(l['hash_anterior']),
    hash: String(l['hash']),
  });

  const paraVarredura = (l: Linha): Varredura => ({
    id: String(l['id']),
    iniciadaEm: data(l['iniciada_em']),
    concluidaEm: dataOuNulo(l['concluida_em']),
    interrompida: Number(l['interrompida']) === 1,
    total: Number(l['alvos_total']),
    ok: Number(l['alvos_ok']),
    falha: Number(l['alvos_falha']),
  });

  return {
    alvos: {
      salvar(_tx, a) {
        db.prepare(
          `INSERT INTO alvo (id,host,porta,dono_id,limiar_aviso,limiar_atencao,limiar_critico,criado_em,removido_em)
           VALUES (?,?,?,?,?,?,?,?,?)
           ON CONFLICT(id) DO UPDATE SET dono_id=excluded.dono_id,
             limiar_aviso=excluded.limiar_aviso, limiar_atencao=excluded.limiar_atencao,
             limiar_critico=excluded.limiar_critico, removido_em=excluded.removido_em`,
        ).run(
          a.id, a.host, a.porta, a.donoId,
          a.limiares.aviso, a.limiares.atencao, a.limiares.critico,
          iso(a.criadoEm), a.removidoEm ? iso(a.removidoEm) : null,
        );
      },
      listar() {
        return (db.prepare('SELECT * FROM alvo WHERE removido_em IS NULL ORDER BY host, porta').all() as Linha[])
          .map(paraAlvo);
      },
      buscarPorId(id) {
        const l = db.prepare('SELECT * FROM alvo WHERE id = ?').get(id) as Linha | undefined;
        return l ? paraAlvo(l) : null;
      },
      remover(_tx, id, agora) {
        db.prepare('UPDATE alvo SET removido_em = ? WHERE id = ?').run(iso(agora), id);
      },
      salvarObservacao(_tx, o) {
        db.prepare(
          `INSERT INTO observacao (id,alvo_id,fingerprint256,issuer,subject,serial,san,
             not_before,not_after_folha,not_after_efetivo,profundidade,visto_primeiro_em,visto_ultima_vez)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)`,
        ).run(
          o.id, o.alvoId, o.fingerprint256, o.issuer, o.subject, o.serial, JSON.stringify(o.san),
          iso(o.notBefore), iso(o.notAfterFolha), iso(o.notAfterEfetivo), o.profundidade,
          iso(o.vistoPrimeiroEm), iso(o.vistoUltimaVez),
        );
      },
      /** PER-04/SUS-02: observacao identica nao vira linha nova — so a revisita e marcada. */
      tocarObservacao(_tx, id, agora) {
        db.prepare('UPDATE observacao SET visto_ultima_vez = ? WHERE id = ?').run(iso(agora), id);
      },
      ultimaObservacao(alvoId) {
        const l = db
          .prepare('SELECT * FROM observacao WHERE alvo_id = ? ORDER BY visto_ultima_vez DESC, rowid DESC LIMIT 1')
          .get(alvoId) as Linha | undefined;
        return l ? paraObservacao(l) : null;
      },
    },

    pedidos: {
      salvar(_tx, p) {
        db.prepare(
          `INSERT INTO pedido (id,alvo_id,estado,solicitante_id,aprovador_id,motivo,evidencia_id,aberto_em,decidido_em,fechado_em)
           VALUES (?,?,?,?,?,?,?,?,?,?)
           ON CONFLICT(id) DO UPDATE SET estado=excluded.estado, aprovador_id=excluded.aprovador_id,
             motivo=excluded.motivo, evidencia_id=excluded.evidencia_id,
             decidido_em=excluded.decidido_em, fechado_em=excluded.fechado_em`,
        ).run(
          p.id, p.alvoId, p.estado, p.solicitanteId, p.aprovadorId, p.motivo, p.evidenciaId,
          iso(p.abertoEm), p.decididoEm ? iso(p.decididoEm) : null, p.fechadoEm ? iso(p.fechadoEm) : null,
        );
      },
      buscarPorId(id) {
        const l = db.prepare('SELECT * FROM pedido WHERE id = ?').get(id) as Linha | undefined;
        return l ? paraPedido(l) : null;
      },
      abertoDe(alvoId) {
        const l = db
          .prepare(`SELECT * FROM pedido WHERE alvo_id = ? AND estado IN ('pendente','aprovado') LIMIT 1`)
          .get(alvoId) as Linha | undefined;
        return l ? paraPedido(l) : null;
      },
      aprovadoDe(alvoId) {
        const l = db
          .prepare(`SELECT * FROM pedido WHERE alvo_id = ? AND estado = 'aprovado' ORDER BY decidido_em LIMIT 1`)
          .get(alvoId) as Linha | undefined;
        return l ? paraPedido(l) : null;
      },
      listar() {
        return (db.prepare('SELECT * FROM pedido ORDER BY aberto_em DESC').all() as Linha[]).map(paraPedido);
      },
    },

    trilha: {
      anexar(_tx, e) {
        db.prepare(
          `INSERT INTO trilha (i,tipo,ator_id,alvo_id,pedido_id,ref_indice,dados,registrado_em,hash_anterior,hash)
           VALUES (?,?,?,?,?,?,?,?,?,?)`,
        ).run(
          e.i, e.tipo, e.atorId, e.alvoId, e.pedidoId, e.refIndice,
          JSON.stringify(e.dados), iso(e.registradoEm), e.hashAnterior, e.hash,
        );
      },
      registrar(tx, e, agora) {
        const p = this.ponta();
        const entrada = encadear(p.hash, e, agora, p.i + 1);
        this.anexar(tx, entrada);
        return entrada;
      },
      ponta() {
        const l = db.prepare('SELECT i, hash, registrado_em FROM trilha ORDER BY i DESC LIMIT 1').get() as
          | Linha
          | undefined;
        return l
          ? { hash: String(l['hash']), i: Number(l['i']), registradoEm: data(l['registrado_em']) }
          : { hash: GENESIS, i: 0, registradoEm: null };
      },
      listar(alvoId) {
        const linhas = alvoId
          ? (db.prepare('SELECT * FROM trilha WHERE alvo_id = ? ORDER BY i').all(alvoId) as Linha[])
          : (db.prepare('SELECT * FROM trilha ORDER BY i').all() as Linha[]);
        return linhas.map(paraEntrada);
      },
      /** SEC-09/GAM-04: o contador permanente de trocas nao autorizadas. Nada o zera. */
      contarPorTipo(alvoId, tipo) {
        const l = db
          .prepare('SELECT COUNT(*) AS n FROM trilha WHERE alvo_id = ? AND tipo = ?')
          .get(alvoId, tipo) as Linha | undefined;
        return l ? Number(l['n']) : 0;
      },
    },

    atores: {
      salvar(_tx, a) {
        db.prepare(
          `INSERT INTO ator (id,nome,papel,senha_hash,senha_salt,ativo,criado_em) VALUES (?,?,?,?,?,?,?)
           ON CONFLICT(id) DO UPDATE SET ativo=excluded.ativo, senha_hash=excluded.senha_hash,
             senha_salt=excluded.senha_salt, papel=excluded.papel`,
        ).run(a.id, a.nome, a.papel, a.senhaHash, a.senhaSalt, a.ativo ? 1 : 0, iso(a.criadoEm));
      },
      buscarPorId(id) {
        const l = db.prepare('SELECT * FROM ator WHERE id = ?').get(id) as Linha | undefined;
        return l ? paraAtor(l) : null;
      },
      buscarPorNome(nome) {
        const l = db.prepare('SELECT * FROM ator WHERE nome = ?').get(nome) as Linha | undefined;
        return l ? paraAtor(l) : null;
      },
      listar() {
        return (db.prepare('SELECT * FROM ator ORDER BY nome').all() as Linha[]).map(paraAtor);
      },
    },

    varreduras: {
      salvar(_tx, v) {
        db.prepare(
          `INSERT INTO varredura (id,iniciada_em,concluida_em,interrompida,alvos_total,alvos_ok,alvos_falha)
           VALUES (?,?,?,?,?,?,?)
           ON CONFLICT(id) DO UPDATE SET concluida_em=excluded.concluida_em,
             interrompida=excluded.interrompida, alvos_total=excluded.alvos_total,
             alvos_ok=excluded.alvos_ok, alvos_falha=excluded.alvos_falha`,
        ).run(
          v.id, iso(v.iniciadaEm), v.concluidaEm ? iso(v.concluidaEm) : null,
          v.interrompida ? 1 : 0, v.total, v.ok, v.falha,
        );
      },
      /** SUS-03: deduplicada por (alvo, tipo) com contador — host permanentemente
       *  fora nao gera uma linha nova a cada varredura. */
      registrarFalha(_tx, alvoId, tipo, detalhe, agora) {
        db.prepare(
          `INSERT INTO falha_sonda (alvo_id,tipo,detalhe,ocorrencias,primeira_ocorrencia,ultima_ocorrencia)
           VALUES (?,?,?,1,?,?)
           ON CONFLICT(alvo_id,tipo) DO UPDATE SET ocorrencias = ocorrencias + 1,
             detalhe = excluded.detalhe, ultima_ocorrencia = excluded.ultima_ocorrencia`,
        ).run(alvoId, tipo, detalhe, iso(agora), iso(agora));
      },
      ultima() {
        const l = db.prepare('SELECT * FROM varredura ORDER BY iniciada_em DESC LIMIT 1').get() as
          | Linha
          | undefined;
        return l ? paraVarredura(l) : null;
      },
      /** RES-06: varredura com concluida_em NULL na abertura da aplicacao ficou orfa. */
      marcarOrfas(_tx) {
        const r = db
          .prepare('UPDATE varredura SET interrompida = 1 WHERE concluida_em IS NULL AND interrompida = 0')
          .run();
        return Number(r.changes);
      },
    },

    emTransacao<T>(fn: (t: Transacao) => T): T {
      db.exec('BEGIN IMMEDIATE');
      try {
        const r = fn(tx);
        db.exec('COMMIT');
        return r;
      } catch (e) {
        db.exec('ROLLBACK');
        throw e;
      }
    },

    fechar() {
      db.close();
    },
  };
}
