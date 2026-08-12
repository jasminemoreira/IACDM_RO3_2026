"""M-04 store — persistência SQLite. Data Mapper, nada além disso.

O que este módulo deliberadamente NÃO faz, porque a Iteração 1 mostrou que
acumular esses eixos aqui foi o defeito de maior concentração (13 achados em 10
lentes): não decide identidade, não conhece a estratégia de blocking, não avalia
duplicidade. Recebe a chave de bloco JÁ CALCULADA pelo matcher e a guarda como
texto indexado (ARC-07).

Decisões materializadas:
  - UNIQUE sobre ChaveNatural, nunca sobre chave de evento (ASM-04, ASM-09).
    A idempotência (I8) é garantia do banco; a colisão legítima (I6) sobrevive
    porque o ordinal a distingue.
  - Unidade de trabalho explícita, para que o audit-log grave na MESMA transação
    (RES-06).
  - Proveniência em toda linha: arquivo e execução de origem (GOV-03).
  - Esquema versionado com migração, cópia de segurança ANTES de aplicar, e
    recusa de base mais nova que o binário (MEC-03, MIG-01, MIG-03, RES-07).
  - SQL sempre parametrizado (SEC-03); base criada com permissão 0600 (SEC-04).
  - Índice composto sobre a coluna de bloco (PRF-03).
"""

from __future__ import annotations

import os
import shutil
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Iterable, Iterator, Sequence

from t26.domain.model import (
    Casamento,
    ChaveNatural,
    Dinheiro,
    Instrumento,
    Lancamento,
    Resultado,
    Situacao,
    Transacao,
)

VERSAO_ESQUEMA = 1

#: RES-04 — SQLite devolve "database is locked" quando outro processo segura o
#: lock. Espera declarada em vez de falha imediata.
TIMEOUT_LOCK_S = 30.0

_DDL = [
    "CREATE TABLE IF NOT EXISTS esquema (versao INTEGER NOT NULL)",
    """CREATE TABLE IF NOT EXISTS execucao (
           id TEXT PRIMARY KEY, instante TEXT NOT NULL,
           parametros TEXT NOT NULL, arquivos TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS transacao (
           chave TEXT PRIMARY KEY, fonte TEXT NOT NULL, conta TEXT NOT NULL,
           data TEXT NOT NULL, valor TEXT NOT NULL, descricao TEXT NOT NULL,
           instrumento TEXT NOT NULL, fitid TEXT, bloco TEXT NOT NULL,
           arquivo TEXT NOT NULL, linha INTEGER NOT NULL, execucao TEXT NOT NULL,
           duplicata_de TEXT)""",
    """CREATE TABLE IF NOT EXISTS lancamento (
           chave TEXT PRIMARY KEY, fonte TEXT NOT NULL, conta TEXT NOT NULL,
           data TEXT NOT NULL, valor TEXT NOT NULL, descricao TEXT NOT NULL,
           documento TEXT, instrumento TEXT NOT NULL, bloco TEXT NOT NULL,
           arquivo TEXT NOT NULL, linha INTEGER NOT NULL, execucao TEXT NOT NULL)""",
    # I4 (1:1): UNIQUE nos DOIS lados. O invariante é do banco, não do código.
    """CREATE TABLE IF NOT EXISTS casamento (
           transacao TEXT NOT NULL UNIQUE, lancamento TEXT NOT NULL UNIQUE,
           resultado TEXT NOT NULL, situacao TEXT NOT NULL, score INTEGER NOT NULL,
           delta_valor TEXT NOT NULL, delta_dias INTEGER NOT NULL,
           execucao TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS pendencia (
           id TEXT PRIMARY KEY, familia TEXT NOT NULL, esquerda TEXT NOT NULL,
           candidatos TEXT NOT NULL, scores TEXT NOT NULL, motivo TEXT NOT NULL,
           aberta INTEGER NOT NULL DEFAULT 1, execucao TEXT NOT NULL)""",
    # Append-only: sem UPDATE nem DELETE. Desfazer grava uma nova linha (GOV-01).
    """CREATE TABLE IF NOT EXISTS resolucao (
           id TEXT PRIMARY KEY, pendencia_id TEXT NOT NULL, acao TEXT NOT NULL,
           autor TEXT NOT NULL, instante TEXT NOT NULL, alvo TEXT,
           motivo TEXT NOT NULL DEFAULT '', desfaz TEXT, execucao TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS auditoria (
           seq INTEGER PRIMARY KEY AUTOINCREMENT, execucao TEXT NOT NULL,
           tipo TEXT NOT NULL, chave TEXT, conteudo TEXT NOT NULL,
           instante TEXT NOT NULL)""",
    # PRF-03 — sem isto, cada busca de candidatos varre a tabela inteira, que
    # cresce a cada mês.
    "CREATE INDEX IF NOT EXISTS ix_transacao_bloco ON transacao (bloco)",
    "CREATE INDEX IF NOT EXISTS ix_lancamento_bloco ON lancamento (bloco)",
    "CREATE INDEX IF NOT EXISTS ix_transacao_conta_data ON transacao (conta, data)",
    "CREATE INDEX IF NOT EXISTS ix_auditoria_chave ON auditoria (chave)",
    "CREATE INDEX IF NOT EXISTS ix_resolucao_pendencia ON resolucao (pendencia_id)",
]


class ErroStore(Exception):
    pass


class EsquemaIncompativel(ErroStore):
    """Base gravada por um binário mais novo. Recusar é melhor que ler errado (MIG-03)."""


@dataclass
class ResultadoImport:
    """Forma declarada do resultado (IMP-04), com a distinção que o UC-1 exige.

    LIN-07: "já presente" tem duas causas distintas e o analista precisa das duas
    separadas — a mesma linha reimportada não é a mesma coisa que o mesmo evento
    chegando por outra fonte.
    """

    novas: int = 0
    ja_presentes_por_chave: int = 0
    ja_presentes_por_dedup: int = 0
    rejeitadas: int = 0
    chaves_novas: list[ChaveNatural] = field(default_factory=list)

    def total(self) -> int:
        return (
            self.novas
            + self.ja_presentes_por_chave
            + self.ja_presentes_por_dedup
            + self.rejeitadas
        )


class UoW:
    """Unidade de trabalho: uma transação SQLite compartilhável (RES-06).

    O audit-log recebe esta mesma instância e grava dentro dela, de modo que a
    trilha e o estado nunca divergem: ou as duas coisas persistem, ou nenhuma.
    """

    def __init__(self, conexao: sqlite3.Connection, execucao_id: str) -> None:
        self.conexao = conexao
        self.execucao_id = execucao_id

    def executar(self, sql: str, parametros: Sequence = ()) -> sqlite3.Cursor:
        return self.conexao.execute(sql, tuple(parametros))

    def executar_muitos(self, sql: str, linhas: Iterable[Sequence]) -> None:
        self.conexao.executemany(sql, [tuple(l) for l in linhas])


class Store:
    def __init__(self, caminho: str | Path) -> None:
        self.caminho = Path(caminho)
        nova = not self.caminho.exists()
        self.conexao = sqlite3.connect(
            self.caminho, timeout=TIMEOUT_LOCK_S, isolation_level=None
        )
        self.conexao.row_factory = sqlite3.Row
        self.conexao.execute("PRAGMA foreign_keys = ON")
        self.conexao.execute("PRAGMA journal_mode = WAL")
        if nova:
            # SEC-04 — extrato bancário não deve nascer legível por outros
            # usuários da máquina.
            os.chmod(self.caminho, 0o600)
            self._criar()
        self._conferir_versao()

    # ---------------------------------------------------------------- esquema

    def _criar(self) -> None:
        with self.transacao_bruta():
            for ddl in _DDL:
                self.conexao.execute(ddl)
            self.conexao.execute("DELETE FROM esquema")
            self.conexao.execute("INSERT INTO esquema (versao) VALUES (?)", (VERSAO_ESQUEMA,))

    def versao_esquema(self) -> int:
        linha = self.conexao.execute("SELECT versao FROM esquema").fetchone()
        return int(linha["versao"]) if linha else 0

    def _conferir_versao(self) -> None:
        atual = self.versao_esquema()
        if atual > VERSAO_ESQUEMA:
            raise EsquemaIncompativel(
                f"{self.caminho}: base no esquema v{atual}, binário conhece até "
                f"v{VERSAO_ESQUEMA}. Recusando para não ler errado — atualize o software."
            )

    def migrar(self) -> Path | None:
        """Aplica migrações pendentes. Devolve o caminho da cópia de segurança.

        MIG-01 e RES-07: a base é o registro contábil acumulado, não cache. A
        cópia é feita ANTES de qualquer DDL, e o DDL roda numa transação; falha
        no meio não deixa esquema intermediário.
        """
        atual = self.versao_esquema()
        if atual == VERSAO_ESQUEMA:
            return None
        backup = self.caminho.with_suffix(f".v{atual}.bak")
        self.conexao.commit() if self.conexao.in_transaction else None
        shutil.copy2(self.caminho, backup)
        os.chmod(backup, 0o600)
        try:
            with self.transacao_bruta():
                for ddl in _DDL:
                    self.conexao.execute(ddl)
                self.conexao.execute("UPDATE esquema SET versao = ?", (VERSAO_ESQUEMA,))
        except Exception as erro:
            raise ErroStore(
                f"migração falhou e foi revertida; cópia de segurança em {backup}: {erro}"
            ) from erro
        return backup

    # ------------------------------------------------------- unidade trabalho

    @contextmanager
    def transacao_bruta(self) -> Iterator[sqlite3.Connection]:
        self.conexao.execute("BEGIN")
        try:
            yield self.conexao
        except Exception:
            self.conexao.execute("ROLLBACK")
            raise
        else:
            self.conexao.execute("COMMIT")

    @contextmanager
    def unidade_de_trabalho(self, execucao_id: str) -> Iterator[UoW]:
        with self.transacao_bruta():
            yield UoW(self.conexao, execucao_id)

    # -------------------------------------------------------------- escritas

    def gravar_lote(
        self,
        uow: UoW,
        transacoes: Sequence[tuple[Transacao, str]],
    ) -> ResultadoImport:
        """Grava transações com sua chave de bloco. Idempotente por ChaveNatural.

        `transacoes` é uma sequência de (Transacao, bloco) — o bloco vem pronto
        do matcher; o store não sabe como ele foi calculado (ARC-07).
        """
        resultado = ResultadoImport()
        # PRF-02 — existência verificada EM LOTE. Um SELECT por item era o padrão
        # N+1 que a Iteração 1 mandou eliminar do dedup e que reapareceu aqui.
        presentes = self._chaves_presentes(
            "transacao", [t.chave.texto() for t, _ in transacoes]
        )
        linhas = []
        for transacao, bloco in transacoes:
            chave = transacao.chave.texto()
            if chave in presentes:
                resultado.ja_presentes_por_chave += 1
                continue
            presentes.add(chave)  # duplicata dentro do próprio lote
            linhas.append(
                (
                    chave,
                    transacao.fonte,
                    transacao.conta,
                    transacao.data.isoformat(),
                    transacao.valor.texto(),
                    transacao.descricao_bruta,
                    transacao.instrumento.value,
                    transacao.fitid,
                    bloco,
                    transacao.arquivo,
                    transacao.linha,
                    uow.execucao_id,
                )
            )
            resultado.novas += 1
            resultado.chaves_novas.append(transacao.chave)
        if linhas:
            uow.executar_muitos(
                """INSERT INTO transacao (chave, fonte, conta, data, valor, descricao,
                       instrumento, fitid, bloco, arquivo, linha, execucao)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                linhas,
            )
        return resultado

    def _chaves_presentes(self, tabela: str, chaves: Sequence[str]) -> set[str]:
        """Uma consulta por fatia de parâmetros, não uma por chave.

        O limite de variáveis de host do SQLite (999 por padrão em builds
        antigos) obriga a fatiar; 500 é folgado e mantém o número de consultas em
        n/500 em vez de n.
        """
        if tabela not in ("transacao", "lancamento"):
            raise ErroStore(f"tabela desconhecida: {tabela}")
        presentes: set[str] = set()
        for i in range(0, len(chaves), 500):
            fatia = chaves[i : i + 500]
            marcas = ",".join("?" * len(fatia))
            cur = self.conexao.execute(
                f"SELECT chave FROM {tabela} WHERE chave IN ({marcas})", tuple(fatia)
            )
            presentes.update(l["chave"] for l in cur.fetchall())
        return presentes

    def carregar_blocos(self, blocos: Sequence[str], tabela: str = "transacao") -> list[dict]:
        """Carrega vários blocos numa consulta por fatia — não uma por bloco."""
        if tabela not in ("transacao", "lancamento"):
            raise ErroStore(f"tabela desconhecida: {tabela}")
        saida: list[dict] = []
        unicos = sorted(set(blocos))
        for i in range(0, len(unicos), 500):
            fatia = unicos[i : i + 500]
            marcas = ",".join("?" * len(fatia))
            cur = self.conexao.execute(
                f"SELECT * FROM {tabela} WHERE bloco IN ({marcas}) ORDER BY chave",
                tuple(fatia),
            )
            saida.extend(dict(l) for l in cur.fetchall())
        return saida

    def gravar_lancamentos(
        self, uow: UoW, lancamentos: Sequence[tuple[Lancamento, str]]
    ) -> ResultadoImport:
        resultado = ResultadoImport()
        presentes = self._chaves_presentes(
            "lancamento", [l.chave.texto() for l, _ in lancamentos]
        )
        linhas = []
        for lancamento, bloco in lancamentos:
            chave = lancamento.chave.texto()
            if chave in presentes:
                resultado.ja_presentes_por_chave += 1
                continue
            presentes.add(chave)
            linhas.append(
                (
                    chave,
                    lancamento.fonte,
                    lancamento.conta,
                    lancamento.data.isoformat(),
                    lancamento.valor.texto(),
                    lancamento.descricao_bruta,
                    lancamento.documento,
                    lancamento.instrumento.value,
                    bloco,
                    lancamento.arquivo,
                    lancamento.linha,
                    uow.execucao_id,
                )
            )
            resultado.novas += 1
            resultado.chaves_novas.append(lancamento.chave)
        if linhas:
            uow.executar_muitos(
                """INSERT INTO lancamento (chave, fonte, conta, data, valor, descricao,
                       documento, instrumento, bloco, arquivo, linha, execucao)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                linhas,
            )
        return resultado

    def marcar_duplicata(self, uow: UoW, chave: ChaveNatural, de: ChaveNatural) -> None:
        uow.executar(
            "UPDATE transacao SET duplicata_de = ? WHERE chave = ?",
            (de.texto(), chave.texto()),
        )

    def desmarcar_duplicata(self, uow: UoW, chave: ChaveNatural) -> None:
        """CTL-03 — malha de correção: existe caminho de volta."""
        uow.executar(
            "UPDATE transacao SET duplicata_de = NULL WHERE chave = ?", (chave.texto(),)
        )

    def salvar_casamentos(self, uow: UoW, casamentos: Sequence[Casamento]) -> None:
        uow.executar_muitos(
            """INSERT INTO casamento (transacao, lancamento, resultado, situacao,
                   score, delta_valor, delta_dias, execucao)
               VALUES (?,?,?,?,?,?,?,?)""",
            [
                (
                    c.transacao.texto(),
                    c.lancamento.texto(),
                    c.resultado.value,
                    c.situacao.value,
                    c.score,
                    str(c.delta_valor),
                    c.delta_dias,
                    uow.execucao_id,
                )
                for c in casamentos
            ],
        )

    def registrar_execucao(
        self, uow: UoW, instante: str, parametros: str, arquivos: str
    ) -> None:
        uow.executar(
            "INSERT INTO execucao (id, instante, parametros, arquivos) VALUES (?,?,?,?)",
            (uow.execucao_id, instante, parametros, arquivos),
        )

    # --------------------------------------------------------------- leituras

    def carregar_bloco(self, bloco: str, tabela: str = "transacao") -> list[dict]:
        """Devolve as linhas de um bloco. A chave vem pronta — o store só indexa."""
        if tabela not in ("transacao", "lancamento"):
            raise ErroStore(f"tabela desconhecida: {tabela}")
        cur = self.conexao.execute(
            f"SELECT * FROM {tabela} WHERE bloco = ? ORDER BY chave", (bloco,)
        )
        return [dict(l) for l in cur.fetchall()]

    def buscar_transacao(self, chave: ChaveNatural) -> dict | None:
        linha = self.conexao.execute(
            "SELECT * FROM transacao WHERE chave = ?", (chave.texto(),)
        ).fetchone()
        return dict(linha) if linha else None

    def contar(self, tabela: str) -> int:
        if tabela not in ("transacao", "lancamento", "casamento", "pendencia", "resolucao", "auditoria"):
            raise ErroStore(f"tabela desconhecida: {tabela}")
        return int(self.conexao.execute(f"SELECT COUNT(*) c FROM {tabela}").fetchone()["c"])

    def digest_estado(self) -> str:
        """Digest do conteúdo das tabelas — como VAL-5 exige ser verificado.

        Contagem de linhas não serve: valores podem ter sido sobrescritos sem
        mudar a contagem (a falsa cobertura que specs/validation proíbe).
        """
        import hashlib

        h = hashlib.sha256()
        for tabela in ("transacao", "lancamento", "casamento", "pendencia", "resolucao"):
            for linha in self.conexao.execute(f"SELECT * FROM {tabela} ORDER BY 1"):
                # a coluna de execução muda a cada rodada por construção e não
                # faz parte do ESTADO conciliado
                itens = {k: v for k, v in dict(linha).items() if k != "execucao"}
                h.update(repr(sorted(itens.items())).encode())
        return h.hexdigest()

    def fechar(self) -> None:
        self.conexao.close()


def linha_para_transacao(linha: dict) -> Transacao:
    """Data Mapper: linha do banco -> objeto de domínio."""
    chave = _chave_de_texto(linha["chave"])
    return Transacao(
        chave=chave,
        conta=linha["conta"],
        data=date.fromisoformat(linha["data"]),
        valor=Dinheiro(Decimal(linha["valor"])),
        descricao_bruta=linha["descricao"],
        fonte=linha["fonte"],
        arquivo=linha["arquivo"],
        linha=int(linha["linha"]),
        instrumento=Instrumento(linha["instrumento"]),
        fitid=linha["fitid"],
    )


def linha_para_lancamento(linha: dict) -> Lancamento:
    return Lancamento(
        chave=_chave_de_texto(linha["chave"]),
        conta=linha["conta"],
        data=date.fromisoformat(linha["data"]),
        valor=Dinheiro(Decimal(linha["valor"])),
        descricao_bruta=linha["descricao"],
        fonte=linha["fonte"],
        arquivo=linha["arquivo"],
        linha=int(linha["linha"]),
        documento=linha["documento"],
        instrumento=Instrumento(linha["instrumento"]),
    )


def _chave_de_texto(texto: str) -> ChaveNatural:
    partes = texto.split("|")
    fonte, conta, resto = partes[0], partes[1], partes[2]
    if resto.startswith("fitid:"):
        return ChaveNatural(fonte=fonte, conta=conta, fitid=resto[len("fitid:") :])
    return ChaveNatural(
        fonte=fonte,
        conta=conta,
        data=date.fromisoformat(resto[len("nat:") :]),
        valor_texto=partes[3],
        descricao_bruta=partes[4],
        ordinal=int(partes[5]),
    )


def linha_para_casamento(linha: dict) -> Casamento:
    return Casamento(
        transacao=_chave_de_texto(linha["transacao"]),
        lancamento=_chave_de_texto(linha["lancamento"]),
        resultado=Resultado(linha["resultado"]),
        situacao=Situacao(linha["situacao"]),
        score=int(linha["score"]),
        delta_valor=Decimal(linha["delta_valor"]),
        delta_dias=int(linha["delta_dias"]),
    )
