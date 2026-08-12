"""M-09 review-queue — fila de pendências e resoluções humanas.

Duas FAMÍLIAS de pendência com conjuntos de ação distintos (PRC-02). Um único
tipo `Pendencia` com um único `resolver` cobria dois processos diferentes:
"casar-manual" não faz sentido para dedup e "é a mesma transação" não faz sentido
para conciliação. Aqui o contrato recusa a ação errada para a família errada.

UX-01 — a fila é ORDENADA POR IMPACTO FINANCEIRO e agrupável por padrão
recorrente. Com dezenas de milhares de transações, uma lista sem ordem e sem
lote torna a tarefa central do operador inexecutável em tempo humano: o desenho
escalava o volume e não a revisão.

UX-06 — resolução em lote EXIGE confirmação explícita do tamanho do grupo. Tornar
a fila operável barateia o erro humano na mesma medida; sob VAL-2 (zero falso
positivo) um agrupamento errado propagaria a decisão errada para todo o grupo.

GOV-01 / I7 — desfazer é APPEND de um novo registro apontando para o anterior,
nunca apagamento. A trilha continua sendo trilha (MIG-02).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Sequence

from t26.domain.model import (
    AcaoConciliacao,
    AcaoDedup,
    ChaveNatural,
    PendenciaConciliacao,
    PendenciaDedup,
    Resolucao,
)
from t26.persistence.auditoria import agora
from t26.persistence.store import _chave_de_texto


class ErroRevisao(Exception):
    pass


class ConfirmacaoAusente(ErroRevisao):
    """UX-06 — lote sem confirmação do tamanho não é executado."""


ACOES_POR_FAMILIA = {
    "dedup": {a.value: a for a in AcaoDedup},
    "conciliacao": {a.value: a for a in AcaoConciliacao},
}


@dataclass(frozen=True)
class ItemFila:
    id: str
    familia: str
    esquerda: ChaveNatural
    candidatos: tuple[ChaveNatural, ...]
    scores: tuple[int, ...]
    motivo: str
    impacto: Decimal
    grupo: str

    def melhor_score(self) -> int:
        return max(self.scores) if self.scores else 0


class ReviewQueue:
    def __init__(self, store, audit_log) -> None:
        self._store = store
        self._log = audit_log

    # ---------------------------------------------------------------- leitura

    def listar(
        self,
        familia: str | None = None,
        ordem: str = "impacto",
        agrupar: bool = False,
    ) -> list[ItemFila]:
        """Ordens: `impacto` (default), `score`, `id`.

        O default é impacto financeiro decrescente porque é a ordem em que o
        analista recupera mais valor por decisão tomada — se ele parar no meio da
        fila, parou tendo resolvido o que mais importa.
        """
        sql = "SELECT * FROM pendencia WHERE aberta = 1"
        params: list = []
        if familia:
            sql += " AND familia = ?"
            params.append(familia)
        linhas = [dict(l) for l in self._store.conexao.execute(sql, tuple(params))]
        itens = [self._para_item(l) for l in linhas]

        if ordem == "impacto":
            itens.sort(key=lambda i: (-i.impacto, i.id))
        elif ordem == "score":
            itens.sort(key=lambda i: (-i.melhor_score(), i.id))
        else:
            itens.sort(key=lambda i: i.id)

        if agrupar:
            itens.sort(key=lambda i: (i.grupo, -i.impacto, i.id))
        return itens

    def grupos(self, familia: str | None = None) -> dict[str, list[ItemFila]]:
        """Agrupa por padrão recorrente — mesmo motivo e mesma faixa de score.

        É o que permite ao analista resolver "todas as tarifas de R$ 30,00 do
        bloco degenerado" numa decisão em vez de trezentas.
        """
        saida: dict[str, list[ItemFila]] = {}
        for item in self.listar(familia):
            saida.setdefault(item.grupo, []).append(item)
        return saida

    # --------------------------------------------------------------- escritas

    def resolver(
        self, uow, pendencia_id: str, acao: str, autor: str,
        alvo: ChaveNatural | None = None, motivo: str = "",
    ) -> Resolucao:
        familia = self._familia(pendencia_id)
        acao_tipada = self._validar_acao(familia, acao)
        if acao_tipada in (AcaoDedup.E_A_MESMA, AcaoConciliacao.CASAR_COM) and alvo is None:
            raise ErroRevisao(f"ação '{acao}' exige um alvo — qual é a contraparte?")

        resolucao = Resolucao(
            id=_id_resolucao(pendencia_id, acao, autor),
            pendencia_id=pendencia_id,
            acao=acao_tipada,
            autor=autor,
            instante=agora(),
            alvo=alvo,
            motivo=motivo,
        )
        self._log.registrar_resolucao(uow, resolucao)
        uow.executar("UPDATE pendencia SET aberta = 0 WHERE id = ?", (pendencia_id,))
        return resolucao

    def resolver_lote(
        self, uow, ids: Sequence[str], acao: str, autor: str,
        confirmacao: int | None = None, motivo: str = "",
    ) -> list[Resolucao]:
        """UX-06 — `confirmacao` deve ser o tamanho exato do lote.

        Não é cerimônia: é o único ponto em que o operador vê quantos itens sua
        decisão vai atingir antes de ela ser irreversível na prática.
        """
        if confirmacao != len(ids):
            raise ConfirmacaoAusente(
                f"resolução em lote de {len(ids)} itens exige confirmacao={len(ids)}; "
                f"recebido {confirmacao!r}"
            )
        return [self.resolver(uow, i, acao, autor, motivo=motivo) for i in ids]

    def desfazer(self, uow, resolucao_id: str, motivo: str, autor: str) -> Resolucao:
        """UX-03 / GOV-01 — corrige por APPEND, jamais por apagamento.

        I7 diz que a decisão humana é soberana e não sobrescrita por heurística;
        sem desfazer, um erro de digitação do analista viraria permanente por
        desenho, que não é o que o invariante quer dizer.
        """
        original = self._store.conexao.execute(
            "SELECT * FROM resolucao WHERE id = ?", (resolucao_id,)
        ).fetchone()
        if original is None:
            raise ErroRevisao(f"resolução {resolucao_id} não existe")
        original = dict(original)
        familia = self._familia(original["pendencia_id"])
        inversa = (
            AcaoDedup.SAO_DISTINTAS
            if familia == "dedup"
            else AcaoConciliacao.NAO_CASA
        )
        resolucao = Resolucao(
            id=_id_resolucao(original["pendencia_id"], "desfaz:" + resolucao_id, autor),
            pendencia_id=original["pendencia_id"],
            acao=inversa,
            autor=autor,
            instante=agora(),
            motivo=motivo,
            desfaz=resolucao_id,
        )
        self._log.registrar_resolucao(uow, resolucao)
        uow.executar(
            "UPDATE pendencia SET aberta = 1 WHERE id = ?", (original["pendencia_id"],)
        )
        return resolucao

    # -------------------------------------------------------------- internos

    def _familia(self, pendencia_id: str) -> str:
        linha = self._store.conexao.execute(
            "SELECT familia FROM pendencia WHERE id = ?", (pendencia_id,)
        ).fetchone()
        if linha is None:
            raise ErroRevisao(f"pendência {pendencia_id} não existe")
        return linha["familia"]

    @staticmethod
    def _validar_acao(familia: str, acao: str):
        permitidas = ACOES_POR_FAMILIA[familia]
        if acao not in permitidas:
            raise ErroRevisao(
                f"ação '{acao}' não existe na família '{familia}'. "
                f"Permitidas: {', '.join(sorted(permitidas))}"
            )
        return permitidas[acao]

    def _para_item(self, linha: dict) -> ItemFila:
        esquerda = _chave_de_texto(linha["esquerda"])
        candidatos = tuple(_chave_de_texto(t) for t in json.loads(linha["candidatos"]))
        scores = tuple(int(s) for s in json.loads(linha["scores"]))
        impacto = self._impacto(esquerda)
        # Grupo = padrão recorrente: mesmo motivo estrutural e mesma faixa de score.
        faixa = (max(scores) // 10 * 10) if scores else 0
        raiz = linha["motivo"].split(";")[0].split(" com ")[0]
        return ItemFila(
            id=linha["id"],
            familia=linha["familia"],
            esquerda=esquerda,
            candidatos=candidatos,
            scores=scores,
            motivo=linha["motivo"],
            impacto=impacto,
            grupo=f"{linha['familia']}|{raiz[:40]}|{faixa}",
        )

    def _impacto(self, chave: ChaveNatural) -> Decimal:
        for tabela in ("transacao", "lancamento"):
            linha = self._store.conexao.execute(
                f"SELECT valor FROM {tabela} WHERE chave = ?", (chave.texto(),)
            ).fetchone()
            if linha:
                return abs(Decimal(linha["valor"]))
        if chave.valor_texto:
            return abs(Decimal(chave.valor_texto))
        return Decimal("0")


def _id_resolucao(pendencia_id: str, acao: str, autor: str) -> str:
    material = f"{pendencia_id}|{acao}|{autor}|{agora()}"
    return "R" + hashlib.sha256(material.encode()).hexdigest()[:16]
