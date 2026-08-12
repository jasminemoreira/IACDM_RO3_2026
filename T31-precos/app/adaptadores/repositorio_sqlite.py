"""M-07 `repositorio-sqlite` — Data Mapper das portas declaradas pelo núcleo.

Repository + Data Mapper (Fowler). O núcleo declara as portas; este módulo as
implementa (DIP) — e é o único lugar do sistema que sabe o que é SQL.

Decisões que vieram das quatro rodadas de crítica:
  * SEC-04 — parâmetros LIGADOS obrigatórios, sempre. Nenhuma concatenação.
  * I-5/PERF — dinheiro persistido em centavos INTEIROS, nunca REAL.
  * RES-01 — falha de I/O vira erro acionável, nunca stack trace cru.
  * I-4/A-07 — publicar é uma transação: insere a versão e TODAS as regras, ou
    nada.
  * A-21/CTL-05 — `vigente_desde` é atribuída pelo SISTEMA no ato da
    publicação. Nenhum ator escolhe data de vigência; vigência retroativa está
    no escopo negativo.
  * X2/CTL-04 — `vigente_em(D)` resolve pelo MAIOR NÚMERO entre as versões com
    `vigente_desde <= D`. O número é sequencial por construção, logo imune a
    ajuste de relógio para trás.
  * PERF-03 — índices em `decisao(data_pedido)` e `decisao(sku)`.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from ..dominio.dinheiro import Dinheiro
from ..dominio.modelo_dominio import (
    Decisao,
    DescontoPct,
    Faixa,
    Origem,
    PrecoUnitario,
    Produto,
    Regra,
    TipoEfeito,
    TipoOrigem,
    Trace,
    Veredito,
    VersaoDeRegras,
    Vigencia,
    MotivoCodigo,
    ResultadoTrace,
)

ESQUEMA = """
CREATE TABLE IF NOT EXISTS produto (
    sku TEXT PRIMARY KEY,
    descricao TEXT NOT NULL,
    preco_base_centavos INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS versao (
    numero INTEGER PRIMARY KEY,
    publicada_em TEXT NOT NULL,
    vigente_desde TEXT NOT NULL,
    autor TEXT NOT NULL,
    origem_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS regra (
    id TEXT NOT NULL,
    versao_numero INTEGER NOT NULL REFERENCES versao(numero),
    escopo TEXT NOT NULL,
    faixa_min INTEGER NOT NULL,
    faixa_max INTEGER,
    efeito_tipo TEXT NOT NULL,
    efeito_valor TEXT NOT NULL,
    prioridade INTEGER NOT NULL,
    vigencia_inicio TEXT NOT NULL,
    vigencia_fim TEXT,
    PRIMARY KEY (id, versao_numero)
);
CREATE TABLE IF NOT EXISTS rascunho_regra (
    id TEXT PRIMARY KEY,
    escopo TEXT NOT NULL,
    faixa_min INTEGER NOT NULL,
    faixa_max INTEGER,
    efeito_tipo TEXT NOT NULL,
    efeito_valor TEXT NOT NULL,
    prioridade INTEGER NOT NULL,
    vigencia_inicio TEXT NOT NULL,
    vigencia_fim TEXT
);
-- Tudo que BLOQUEIA a publicação precisa ter o mesmo tempo de vida do
-- rascunho que ele bloqueia. A evidência de preço base divergente vivia só em
-- memória, e um restart a apagava — derrotando V-04 em silêncio.
CREATE TABLE IF NOT EXISTS rascunho_meta (
    chave TEXT PRIMARY KEY,
    valor_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS decisao (
    id TEXT PRIMARY KEY,
    sku TEXT NOT NULL,
    quantidade INTEGER NOT NULL,
    data_pedido TEXT NOT NULL,
    versao_regras INTEGER NOT NULL,
    preco_unitario_centavos INTEGER NOT NULL,
    total_centavos INTEGER NOT NULL,
    trace_json TEXT NOT NULL,
    solicitante TEXT NOT NULL,
    registrada_em TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_decisao_data ON decisao(data_pedido);
CREATE INDEX IF NOT EXISTS ix_decisao_sku ON decisao(sku);
"""


class ErroDePersistencia(Exception):
    """RES-01: falha de I/O com mensagem acionável, não stack trace.

    O pior estado possível para I-4 é o analista sem saber se publicou.
    """


class RepositorioSQLite:
    def __init__(self, caminho: str | Path) -> None:
        self.caminho = str(caminho)
        # A-06 REVISADA (defeito encontrado no teste de fumaça da Fase 5): o
        # sistema é single-USER, mas NÃO single-threaded — o servidor ASGI
        # executa handlers síncronos num threadpool, então dois cliques em
        # sequência podem cair em threads diferentes. A premissa original
        # ("sem trava") descrevia um runtime que a plataforma não concede.
        # É o LOCK, não a ausência de concorrência, que garante I-4.
        self._lock = threading.RLock()
        try:
            self._con = sqlite3.connect(
                self.caminho, isolation_level=None, check_same_thread=False
            )
            self._con.row_factory = sqlite3.Row
            self._con.execute("PRAGMA foreign_keys = ON")
            self._con.executescript(ESQUEMA)
            # Toda leitura e escrita passa a ser serializada. O RLock é
            # reentrante, então uma leitura dentro de uma transação na mesma
            # thread não trava.
            self._con = _ConexaoSincronizada(self._con, self._lock)
        except sqlite3.Error as e:  # pragma: no cover - caminho de I/O
            raise ErroDePersistencia(
                f"não foi possível abrir o banco em {self.caminho}: {e}. "
                "Verifique permissão de escrita e espaço em disco."
            ) from e

    def fechar(self) -> None:
        self._con.close()

    # -- catálogo --------------------------------------------------------

    def salvar_produtos(self, produtos: list[Produto]) -> None:
        with _transacao(self._con, "salvar produtos"):
            self._con.executemany(
                "INSERT INTO produto (sku, descricao, preco_base_centavos) "
                "VALUES (?, ?, ?) ON CONFLICT(sku) DO UPDATE SET "
                "descricao = excluded.descricao, "
                "preco_base_centavos = excluded.preco_base_centavos",
                [(p.sku, p.descricao, p.preco_base.centavos) for p in produtos],
            )

    def produtos(self) -> dict[str, Produto]:
        linhas = self._con.execute(
            "SELECT sku, descricao, preco_base_centavos FROM produto"
        ).fetchall()
        return {
            r["sku"]: Produto(r["sku"], r["descricao"], Dinheiro(r["preco_base_centavos"]))
            for r in linhas
        }

    # -- rascunho --------------------------------------------------------

    def salvar_rascunho(self, regras: list[Regra]) -> None:
        with _transacao(self._con, "salvar rascunho"):
            self._con.execute("DELETE FROM rascunho_regra")
            self._con.executemany(
                "INSERT INTO rascunho_regra (id, escopo, faixa_min, faixa_max, "
                "efeito_tipo, efeito_valor, prioridade, vigencia_inicio, vigencia_fim) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [_regra_para_linha(r) for r in regras],
            )

    def rascunho_atual(self) -> list[Regra]:
        linhas = self._con.execute("SELECT * FROM rascunho_regra ORDER BY id").fetchall()
        return [_linha_para_regra(r) for r in linhas]

    def salvar_conflitos_base(self, conflitos: list) -> None:
        """Persiste a evidência que bloqueia a publicação (V-04)."""
        dados = [
            {"sku": c.sku, "valores": list(c.valores), "linhas": list(c.linhas)}
            for c in conflitos
        ]
        with _transacao(self._con, "salvar conflitos de preço base"):
            self._con.execute(
                "INSERT INTO rascunho_meta (chave, valor_json) VALUES ('conflitos_base', ?) "
                "ON CONFLICT(chave) DO UPDATE SET valor_json = excluded.valor_json",
                (json.dumps(dados, ensure_ascii=False),),
            )

    def conflitos_base(self) -> list:
        from .importador_csv import ConflitoBase

        r = self._con.execute(
            "SELECT valor_json FROM rascunho_meta WHERE chave = 'conflitos_base'"
        ).fetchone()
        if r is None:
            return []
        return [
            ConflitoBase(sku=d["sku"], valores=tuple(d["valores"]), linhas=tuple(d["linhas"]))
            for d in json.loads(r["valor_json"])
        ]

    # -- versões ---------------------------------------------------------

    def publicar(
        self, regras: list[Regra], autor: str, origem: Origem, agora: datetime
    ) -> VersaoDeRegras:
        """I-4 + A-07: uma transação. Insere versão e TODAS as regras, ou nada.

        `agora` é injetado pelo chamador — nem este módulo nem o núcleo leem o
        relógio (A-04 estendida à fronteira de persistência para manter os
        testes determinísticos).
        """
        proximo = (
            self._con.execute("SELECT COALESCE(MAX(numero), 0) + 1 AS n FROM versao")
            .fetchone()["n"]
        )
        vigente_desde = agora.date()  # A-21: atribuída pelo sistema
        with _transacao(self._con, "publicar versão"):
            self._con.execute(
                "INSERT INTO versao (numero, publicada_em, vigente_desde, autor, origem_json) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    proximo,
                    agora.isoformat(),
                    vigente_desde.isoformat(),
                    autor,
                    json.dumps(_origem_para_dict(origem), ensure_ascii=False),
                ),
            )
            self._con.executemany(
                "INSERT INTO regra (id, versao_numero, escopo, faixa_min, faixa_max, "
                "efeito_tipo, efeito_valor, prioridade, vigencia_inicio, vigencia_fim) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (linha[0], proximo, *linha[1:])
                    for linha in (_regra_para_linha(r) for r in regras)
                ],
            )
        return VersaoDeRegras(
            numero=proximo,
            publicada_em=agora,
            vigente_desde=vigente_desde,
            autor=autor,
            origem=origem,
            regras=tuple(regras),
        )

    def indice_vigencia(self) -> list[tuple[date, int]]:
        """Pares `(vigente_desde, numero)` ordenados por NÚMERO (X2/CTL-04).

        Carregado sob demanda por `servico-aplicacao` (Y1/PERF-07).
        """
        linhas = self._con.execute(
            "SELECT numero, vigente_desde FROM versao ORDER BY numero"
        ).fetchall()
        return [(date.fromisoformat(r["vigente_desde"]), r["numero"]) for r in linhas]

    def versao(self, numero: int) -> VersaoDeRegras | None:
        v = self._con.execute(
            "SELECT * FROM versao WHERE numero = ?", (numero,)
        ).fetchone()
        if v is None:
            return None
        regras = self._con.execute(
            "SELECT * FROM regra WHERE versao_numero = ? ORDER BY id", (numero,)
        ).fetchall()
        return VersaoDeRegras(
            numero=v["numero"],
            publicada_em=datetime.fromisoformat(v["publicada_em"]),
            vigente_desde=date.fromisoformat(v["vigente_desde"]),
            autor=v["autor"],
            origem=_dict_para_origem(json.loads(v["origem_json"])),
            regras=tuple(_linha_para_regra(r) for r in regras),
        )

    def ultima_versao(self) -> int | None:
        r = self._con.execute("SELECT MAX(numero) AS n FROM versao").fetchone()
        return r["n"]

    # -- log de decisões -------------------------------------------------

    def registrar(self, d: Decisao) -> None:
        with _transacao(self._con, "registrar decisão"):
            self._con.execute(
                "INSERT INTO decisao (id, sku, quantidade, data_pedido, versao_regras, "
                "preco_unitario_centavos, total_centavos, trace_json, solicitante, "
                "registrada_em) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    d.id,
                    d.sku,
                    d.quantidade,
                    d.data_pedido.isoformat(),
                    d.versao_regras,
                    d.preco_unitario.centavos,
                    d.total.centavos,
                    json.dumps(_trace_para_dict(d.trace), ensure_ascii=False),
                    d.solicitante,
                    d.registrada_em.isoformat(),
                ),
            )

    def listar(
        self, sku: str | None = None, limite: int = 100
    ) -> list[Decisao]:
        if sku:
            linhas = self._con.execute(
                "SELECT * FROM decisao WHERE sku = ? "
                "ORDER BY registrada_em DESC LIMIT ?",
                (sku, limite),
            ).fetchall()
        else:
            linhas = self._con.execute(
                "SELECT * FROM decisao ORDER BY registrada_em DESC LIMIT ?",
                (limite,),
            ).fetchall()
        return [_linha_para_decisao(r) for r in linhas]

    def obter(self, decisao_id: str) -> Decisao | None:
        r = self._con.execute(
            "SELECT * FROM decisao WHERE id = ?", (decisao_id,)
        ).fetchone()
        return _linha_para_decisao(r) if r else None


class _Resultado:
    """Linhas já materializadas — nada é lido fora da seção crítica."""

    __slots__ = ("_linhas",)

    def __init__(self, linhas: list) -> None:
        self._linhas = linhas

    def fetchall(self) -> list:
        return self._linhas

    def fetchone(self):
        return self._linhas[0] if self._linhas else None


class _ConexaoSincronizada:
    """A-06 revisada: serializa o acesso ao SQLite entre threads do ASGI."""

    __slots__ = ("_con", "_lock")

    def __init__(self, con: sqlite3.Connection, lock) -> None:
        self._con = con
        self._lock = lock

    def execute(self, sql: str, params: tuple = ()) -> _Resultado:
        with self._lock:
            return _Resultado(self._con.execute(sql, params).fetchall())

    def executemany(self, sql: str, seq) -> _Resultado:
        with self._lock:
            return _Resultado(self._con.executemany(sql, seq).fetchall())

    def close(self) -> None:
        with self._lock:
            self._con.close()


class _transacao:
    """Contexto que traduz falha de I/O em `ErroDePersistencia` (RES-01).

    Segura o RLock do BEGIN ao COMMIT: é isto que garante I-4 (publicação
    atômica) agora que sabemos que o runtime é multi-thread.
    """

    def __init__(self, con: "_ConexaoSincronizada", operacao: str) -> None:
        self._con = con
        self._operacao = operacao

    def __enter__(self) -> None:
        self._con._lock.acquire()
        try:
            self._con.execute("BEGIN")
        except BaseException:
            self._con._lock.release()
            raise

    def __exit__(self, exc_type, exc, tb) -> bool:
        try:
            return self._concluir(exc_type, exc)
        finally:
            self._con._lock.release()

    def _concluir(self, exc_type, exc) -> bool:
        if exc_type is None:
            try:
                self._con.execute("COMMIT")
            except sqlite3.Error as e:
                raise ErroDePersistencia(
                    f"falha ao concluir '{self._operacao}': {e}. "
                    "Nada foi gravado — verifique espaço em disco e se o "
                    "arquivo do banco não está bloqueado por outro processo."
                ) from e
            return False
        self._con.execute("ROLLBACK")
        if issubclass(exc_type, sqlite3.Error):
            raise ErroDePersistencia(
                f"falha em '{self._operacao}': {exc}. Nada foi gravado."
            ) from exc
        return False


# -- mapeamento ---------------------------------------------------------------


def _regra_para_linha(r: Regra) -> tuple:
    valor = (
        str(r.efeito.valor.centavos)
        if r.efeito.tipo is TipoEfeito.PRECO_UNITARIO
        else str(r.efeito.pct)
    )
    return (
        r.id,
        r.escopo,
        r.faixa.minimo,
        r.faixa.maximo,
        r.efeito.tipo.value,
        valor,
        r.prioridade,
        r.vigencia.inicio.isoformat(),
        r.vigencia.fim.isoformat() if r.vigencia.fim else None,
    )


def _linha_para_regra(r: sqlite3.Row) -> Regra:
    tipo = TipoEfeito(r["efeito_tipo"])
    efeito = (
        PrecoUnitario(Dinheiro(int(r["efeito_valor"])))
        if tipo is TipoEfeito.PRECO_UNITARIO
        else DescontoPct(Decimal(r["efeito_valor"]))
    )
    return Regra(
        id=r["id"],
        escopo=r["escopo"],
        faixa=Faixa(r["faixa_min"], r["faixa_max"]),
        efeito=efeito,
        prioridade=r["prioridade"],
        vigencia=Vigencia(
            date.fromisoformat(r["vigencia_inicio"]),
            date.fromisoformat(r["vigencia_fim"]) if r["vigencia_fim"] else None,
        ),
    )


def _origem_para_dict(o: Origem) -> dict:
    return {
        "tipo": o.tipo.value,
        "justificativa": o.justificativa,
        "arquivo": o.arquivo,
        "sha256": o.sha256,
        "revertida_de": o.revertida_de,
        "relatorio": o.relatorio,
    }


def _dict_para_origem(d: dict) -> Origem:
    return Origem(
        tipo=TipoOrigem(d["tipo"]),
        justificativa=d["justificativa"],
        arquivo=d.get("arquivo"),
        sha256=d.get("sha256"),
        revertida_de=d.get("revertida_de"),
        relatorio=d.get("relatorio"),
    )


def _trace_para_dict(t: Trace) -> dict:
    return {
        "resultado": t.resultado.value,
        "vencedora": t.vencedora,
        "calculo": t.calculo,
        "vereditos": [
            {"regra_id": v.regra_id, "codigo": v.codigo.value, "detalhe": v.detalhe}
            for v in t.vereditos
        ],
    }


def _dict_para_trace(d: dict) -> Trace:
    return Trace(
        resultado=ResultadoTrace(d["resultado"]),
        vereditos=tuple(
            Veredito(v["regra_id"], MotivoCodigo(v["codigo"]), v.get("detalhe", {}))
            for v in d["vereditos"]
        ),
        calculo=d["calculo"],
        vencedora=d.get("vencedora"),
    )


def _linha_para_decisao(r: sqlite3.Row) -> Decisao:
    return Decisao(
        id=r["id"],
        sku=r["sku"],
        quantidade=r["quantidade"],
        data_pedido=date.fromisoformat(r["data_pedido"]),
        versao_regras=r["versao_regras"],
        preco_unitario=Dinheiro(r["preco_unitario_centavos"]),
        total=Dinheiro(r["total_centavos"]),
        trace=_dict_para_trace(json.loads(r["trace_json"])),
        solicitante=r["solicitante"],
        registrada_em=datetime.fromisoformat(r["registrada_em"]),
    )
