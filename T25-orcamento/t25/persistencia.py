"""M-08 persistencia — conexao, schema, transacao e repositorios.

Padrao: Repository sobre SQL direto (Fowler). A interface fala a linguagem do
dominio; a transacao e EXPLICITA e VISIVEL, porque a transacao e a garantia do
invariante.

`sqlite3` da biblioteca padrao, SINCRONO e intencionalmente bloqueante (decisao
de V(2), achado A-01): e o que torna a secao critica atomica sem lock. A chamada
ao provedor acontece SEMPRE fora dela.

V(3):
- `recuperar_no_arranque()` — num processo recem-iniciado nenhuma requisicao pode
  estar em voo, logo toda reserva 'aberta' e lixo de crash e e liberada.
  Substitui o TTL inteiro (achados RES-04, RES-05, PRO-03, GOV-03, OBS-03, CTL-03).
- retencao aplicada NO ARRANQUE, nunca durante o trafego (achado PERF-05).
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterator

GLOBAL = "global"
ENTIDADE = "entidade"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS entidade (
    id          TEXT PRIMARY KEY,
    nome        TEXT NOT NULL,
    max_tokens  INTEGER NOT NULL,      -- teto de max_tokens por requisicao (GAM-01)
    max_reservas INTEGER NOT NULL,     -- reservas simultaneas permitidas (GAM-03)
    criada_em   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chave_virtual (
    hash        TEXT PRIMARY KEY,      -- hash da chave; NUNCA a chave em claro
    entidade_id TEXT NOT NULL REFERENCES entidade(id),
    revogada_em TEXT
);

CREATE TABLE IF NOT EXISTS teto (
    escopo       TEXT NOT NULL,
    entidade_id  TEXT NOT NULL,        -- '' quando escopo = 'global'
    valor_nano   INTEGER NOT NULL,
    atualizado_em TEXT NOT NULL,
    atualizado_por TEXT NOT NULL,      -- trilha de auditoria (SEG-04/GOV-01)
    PRIMARY KEY (escopo, entidade_id)
);

CREATE TABLE IF NOT EXISTS contador (
    escopo          TEXT NOT NULL,
    entidade_id     TEXT NOT NULL,
    janela_inicio   TEXT NOT NULL,     -- a janela faz parte da chave: virada preguicosa
    confirmado_nano INTEGER NOT NULL DEFAULT 0,
    reservado_nano  INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (escopo, entidade_id, janela_inicio)
);

CREATE TABLE IF NOT EXISTS reserva (
    id            TEXT PRIMARY KEY,    -- torna reconciliar idempotente
    entidade_id   TEXT NOT NULL,
    janela_inicio TEXT NOT NULL,       -- a reserva grava SUA janela (achado PRO-01)
    valor_nano    INTEGER NOT NULL,
    estado        TEXT NOT NULL,       -- 'aberta' | 'reconciliada' | 'liberada'
    criada_em     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_reserva_abertas ON reserva(entidade_id, estado);

CREATE TABLE IF NOT EXISTS evento_uso (
    id                   TEXT PRIMARY KEY,
    entidade_id          TEXT NOT NULL,
    modelo               TEXT NOT NULL,
    tokens_entrada       INTEGER NOT NULL,
    tokens_cache_leitura INTEGER NOT NULL,
    tokens_cache_escrita INTEGER NOT NULL,
    tokens_saida         INTEGER NOT NULL,
    custo_nano           INTEGER NOT NULL,
    stop_reason          TEXT,
    ocorrido_em          TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_evento_entidade ON evento_uso(entidade_id, ocorrido_em);

CREATE TABLE IF NOT EXISTS auditoria_teto (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    escopo      TEXT NOT NULL,
    entidade_id TEXT NOT NULL,
    de_nano     INTEGER,
    para_nano   INTEGER NOT NULL,
    ator        TEXT NOT NULL,
    em          TEXT NOT NULL
);
"""


@dataclass
class Contador:
    confirmado_nano: int
    reservado_nano: int

    @property
    def comprometido_nano(self) -> int:
        """O que a decisao de admissao le. Ler so `confirmado` e o bug que faz
        N requisicoes concorrentes passarem juntas."""
        return self.confirmado_nano + self.reservado_nano


class Persistencia:
    def __init__(self, caminho: str) -> None:
        # isolation_level=None: controlamos BEGIN/COMMIT explicitamente.
        # check_same_thread=False: servidores ASGI constroem a app numa thread e
        # servem noutra. A seguranca NAO vem do guard do sqlite3 e sim do desenho:
        # processo unico, event loop unico e BEGIN IMMEDIATE em toda escrita.
        self._con = sqlite3.connect(caminho, isolation_level=None, check_same_thread=False)
        self._con.row_factory = sqlite3.Row
        self._con.execute("PRAGMA journal_mode=WAL")
        self._con.execute("PRAGMA foreign_keys=ON")
        self._con.executescript(_SCHEMA)

    def fechar(self) -> None:
        self._con.close()

    # ---------- transacao ----------

    @contextmanager
    def transacao(self) -> Iterator[sqlite3.Connection]:
        """BEGIN IMMEDIATE: adquire o lock de escrita na abertura, nao na primeira
        escrita. Sem isso, duas transacoes que leem e depois escrevem podem
        intercalar leitura-decisao-escrita (anomalia lost update, achado A7)."""
        self._con.execute("BEGIN IMMEDIATE")
        try:
            yield self._con
        except BaseException:
            self._con.execute("ROLLBACK")
            raise
        else:
            self._con.execute("COMMIT")

    # ---------- arranque ----------

    def recuperar_no_arranque(self) -> int:
        """Libera reservas 'aberta' remanescentes de uma queda de processo.

        Correto por construcao: num processo recem-iniciado nenhuma requisicao
        pode estar em voo. Substitui o TTL de V(2).
        """
        with self.transacao() as c:
            linhas = c.execute(
                "SELECT id, entidade_id, janela_inicio, valor_nano FROM reserva WHERE estado='aberta'"
            ).fetchall()
            for r in linhas:
                self._somar_reservado(c, GLOBAL, "", r["janela_inicio"], -r["valor_nano"])
                self._somar_reservado(
                    c, ENTIDADE, r["entidade_id"], r["janela_inicio"], -r["valor_nano"]
                )
                c.execute("UPDATE reserva SET estado='liberada' WHERE id=?", (r["id"],))
            return len(linhas)

    def aplicar_retencao(self, dias: int, agora: datetime) -> int:
        """Remove eventos de uso mais antigos que `dias`. So no arranque."""
        if dias <= 0:
            return 0
        corte = (agora - timedelta(days=dias)).isoformat()
        with self.transacao() as c:
            cur = c.execute("DELETE FROM evento_uso WHERE ocorrido_em < ?", (corte,))
            return cur.rowcount or 0

    # ---------- contadores ----------

    def ler_contador(
        self, c: sqlite3.Connection, escopo: str, entidade_id: str, janela: str
    ) -> Contador:
        """Criacao preguicosa: linha ausente = consumo zero. E o reset."""
        r = c.execute(
            "SELECT confirmado_nano, reservado_nano FROM contador"
            " WHERE escopo=? AND entidade_id=? AND janela_inicio=?",
            (escopo, entidade_id, janela),
        ).fetchone()
        if r is None:
            return Contador(0, 0)
        return Contador(r["confirmado_nano"], r["reservado_nano"])

    @staticmethod
    def _upsert_contador(c: sqlite3.Connection, escopo: str, ent: str, janela: str) -> None:
        c.execute(
            "INSERT OR IGNORE INTO contador(escopo, entidade_id, janela_inicio)"
            " VALUES (?,?,?)",
            (escopo, ent, janela),
        )

    def _somar_reservado(
        self, c: sqlite3.Connection, escopo: str, ent: str, janela: str, delta: int
    ) -> None:
        self._upsert_contador(c, escopo, ent, janela)
        c.execute(
            "UPDATE contador SET reservado_nano = MAX(0, reservado_nano + ?)"
            " WHERE escopo=? AND entidade_id=? AND janela_inicio=?",
            (delta, escopo, ent, janela),
        )

    def somar_reservado(
        self, c: sqlite3.Connection, escopo: str, ent: str, janela: str, delta: int
    ) -> None:
        self._somar_reservado(c, escopo, ent, janela, delta)

    def somar_confirmado(
        self, c: sqlite3.Connection, escopo: str, ent: str, janela: str, delta: int
    ) -> None:
        self._upsert_contador(c, escopo, ent, janela)
        c.execute(
            "UPDATE contador SET confirmado_nano = confirmado_nano + ?"
            " WHERE escopo=? AND entidade_id=? AND janela_inicio=?",
            (delta, escopo, ent, janela),
        )

    # ---------- tetos ----------

    def ler_teto(self, c: sqlite3.Connection, escopo: str, entidade_id: str) -> int | None:
        r = c.execute(
            "SELECT valor_nano FROM teto WHERE escopo=? AND entidade_id=?",
            (escopo, entidade_id),
        ).fetchone()
        return None if r is None else r["valor_nano"]

    def definir_teto(
        self, escopo: str, entidade_id: str, valor_nano: int, ator: str, agora: datetime
    ) -> None:
        with self.transacao() as c:
            anterior = self.ler_teto(c, escopo, entidade_id)
            c.execute(
                "INSERT INTO teto(escopo, entidade_id, valor_nano, atualizado_em, atualizado_por)"
                " VALUES (?,?,?,?,?)"
                " ON CONFLICT(escopo, entidade_id) DO UPDATE SET"
                " valor_nano=excluded.valor_nano, atualizado_em=excluded.atualizado_em,"
                " atualizado_por=excluded.atualizado_por",
                (escopo, entidade_id, valor_nano, agora.isoformat(), ator),
            )
            c.execute(
                "INSERT INTO auditoria_teto(escopo, entidade_id, de_nano, para_nano, ator, em)"
                " VALUES (?,?,?,?,?,?)",
                (escopo, entidade_id, anterior, valor_nano, ator, agora.isoformat()),
            )

    # ---------- eventos ----------

    def registrar_evento(self, c: sqlite3.Connection, **campos) -> None:
        c.execute(
            "INSERT INTO evento_uso(id, entidade_id, modelo, tokens_entrada,"
            " tokens_cache_leitura, tokens_cache_escrita, tokens_saida, custo_nano,"
            " stop_reason, ocorrido_em) VALUES"
            " (:id,:entidade_id,:modelo,:tokens_entrada,:tokens_cache_leitura,"
            " :tokens_cache_escrita,:tokens_saida,:custo_nano,:stop_reason,:ocorrido_em)",
            campos,
        )

    # ---------- consultas do painel ----------

    def consumo_por_entidade(self, janela: str) -> list[dict]:
        linhas = self._con.execute(
            "SELECT e.id, e.nome,"
            "       (SELECT valor_nano FROM teto t WHERE t.escopo='entidade' AND t.entidade_id=e.id) AS teto_nano,"
            "       c.confirmado_nano, c.reservado_nano"
            " FROM entidade e"
            " LEFT JOIN contador c"
            "   ON c.escopo='entidade' AND c.entidade_id=e.id AND c.janela_inicio=?"
            " ORDER BY e.id",
            (janela,),
        ).fetchall()
        return [dict(r) for r in linhas]

    def contador_global(self, janela: str) -> dict:
        c = self.ler_contador(self._con, GLOBAL, "", janela)
        teto = self.ler_teto(self._con, GLOBAL, "")
        return {
            "confirmado_nano": c.confirmado_nano,
            "reservado_nano": c.reservado_nano,
            "teto_nano": teto,
        }

    def verificar_invariantes(self, janela: str) -> dict:
        """Invariante I2: soma das reservas 'aberta' == reservado_nano do escopo.

        Exposto em /health (achado OBS-02): sem isso, corrupcao do contador seria
        silenciosa.
        """
        somas = {
            r["entidade_id"]: r["s"]
            for r in self._con.execute(
                "SELECT entidade_id, SUM(valor_nano) AS s FROM reserva"
                " WHERE estado='aberta' AND janela_inicio=? GROUP BY entidade_id",
                (janela,),
            ).fetchall()
        }
        divergencias = []
        for r in self._con.execute(
            "SELECT entidade_id, reservado_nano FROM contador"
            " WHERE escopo='entidade' AND janela_inicio=?",
            (janela,),
        ).fetchall():
            esperado = somas.get(r["entidade_id"], 0)
            if esperado != r["reservado_nano"]:
                divergencias.append(
                    {
                        "entidade_id": r["entidade_id"],
                        "reservado_nano": r["reservado_nano"],
                        "soma_reservas_abertas": esperado,
                    }
                )
        return {"i2_ok": not divergencias, "divergencias": divergencias}

    # ---------- administracao ----------

    def criar_entidade(
        self, id_: str, nome: str, max_tokens: int, max_reservas: int, agora: datetime
    ) -> None:
        with self.transacao() as c:
            c.execute(
                "INSERT OR REPLACE INTO entidade(id, nome, max_tokens, max_reservas, criada_em)"
                " VALUES (?,?,?,?,?)",
                (id_, nome, max_tokens, max_reservas, agora.isoformat()),
            )

    def conexao(self) -> sqlite3.Connection:
        return self._con
