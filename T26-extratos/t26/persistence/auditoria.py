"""M-05 audit-log — trilha append-only de decisões, resoluções e parâmetros.

Por que este módulo existe: VAL-2 exige ZERO falso positivo, e um critério de
zero-defeito só é verificável se for possível INVESTIGAR um. Sem trilha, um
falso positivo descoberto no fechamento seguinte é inauditável (GOV-01, GOV-02).

Contrato de falha declarado (RES-06 — o defeito da Iteração 2): este módulo NÃO
abre transação própria. Recebe a `UoW` do store e grava dentro dela. Ou o estado
e a trilha persistem juntos, ou nenhum dos dois persiste. Compartilhar a
transação foi a escolha porque a alternativa — trilha em transação separada —
produz divergência silenciosa exatamente após a falha, que é quando a trilha
importa.

PRF-07: gravação em LOTE por importação, não uma escrita por decisão. 50.000
appends individuais colocariam a trilha no caminho crítico do orçamento de 60 s.

REG-04 / SEC-07 — conflito normativo real, arbitrado aqui: a guarda contábil
exige reter, a LGPD exige poder eliminar dado pessoal. A regra é anonimizar a
contraparte após o prazo, por APPEND de um registro de anonimização, nunca por
edição do registro original (MIG-02: a trilha não pode ser corrigida por UPDATE
sem deixar de ser trilha).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Sequence

from t26.domain.model import ChaveNatural, DecisaoDedup, Resolucao
from t26.persistence.store import UoW

#: Prazo de retenção do dado pessoal de contraparte na TRILHA, em dias.
#: Não é prazo contábil (que é maior e se aplica ao dado, não à trilha): é o
#: ponto a partir do qual a contraparte deixa de ser necessária para auditar a
#: DECISÃO. Parâmetro configurável com default documentado, como toda constante
#: deste projeto (specs/technical/parametros-matching.md).
RETENCAO_CONTRAPARTE_DIAS = 365 * 5


class Tipo:
    EXECUCAO = "execucao"
    DECISAO_DEDUP = "decisao-dedup"
    RESOLUCAO = "resolucao"
    DESFAZER = "desfazer"
    ANONIMIZACAO = "anonimizacao"


@dataclass(frozen=True)
class Evento:
    seq: int
    execucao: str
    tipo: str
    chave: str | None
    conteudo: dict
    instante: str


def agora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class AuditLog:
    def __init__(self, store) -> None:
        self._store = store

    # ------------------------------------------------------------- escritas

    def registrar_execucao(
        self, uow: UoW, parametros: dict, hashes_entrada: dict[str, str]
    ) -> str:
        """Registra os parâmetros EFETIVOS e o hash dos arquivos de entrada.

        Os parâmetros fecham CTL-02 e REG-03: sem eles, mudar um limiar
        reclassifica o histórico em silêncio e o relatório não é reexecutável.
        Os hashes fecham GOV-06: reprodutível quanto aos parâmetros E quanto aos
        dados, não só quanto aos parâmetros.
        """
        instante = agora()
        self._store.registrar_execucao(
            uow, instante, json.dumps(parametros, sort_keys=True, default=str),
            json.dumps(hashes_entrada, sort_keys=True),
        )
        self._append(
            uow,
            [(Tipo.EXECUCAO, None, {"parametros": parametros, "arquivos": hashes_entrada})],
            instante,
        )
        return uow.execucao_id

    def registrar_lote(self, uow: UoW, decisoes: Sequence[DecisaoDedup]) -> None:
        """Um append por lote (PRF-07), com uma linha por decisão dentro dele."""
        instante = agora()
        self._append(
            uow,
            [
                (
                    Tipo.DECISAO_DEDUP,
                    d.chave.texto(),
                    {
                        "veredito": d.veredito.value,
                        "camada": d.camada.value,
                        "evidencia": d.evidencia,
                        "contraparte": d.contraparte.texto() if d.contraparte else None,
                        "score": d.score,
                    },
                )
                for d in decisoes
            ],
            instante,
        )

    def registrar_resolucao(self, uow: UoW, resolucao: Resolucao) -> None:
        """Grava a resolução humana. GOV-05: marca ausência de segunda instância.

        Quando quem desfaz é o mesmo autor da resolução original, o fato fica
        registrado. Atribuível não é o mesmo que responsabilizável, e a trilha
        não deve fingir que é.
        """
        tipo = Tipo.DESFAZER if resolucao.desfaz else Tipo.RESOLUCAO
        conteudo = {
            "pendencia": resolucao.pendencia_id,
            "acao": resolucao.acao.value,
            "autor": resolucao.autor,
            "alvo": resolucao.alvo.texto() if resolucao.alvo else None,
            "motivo": resolucao.motivo,
            "desfaz": resolucao.desfaz,
        }
        if resolucao.desfaz:
            original = self._buscar_resolucao(resolucao.desfaz)
            if original is not None and original["autor"] == resolucao.autor:
                conteudo["sem_segunda_instancia"] = True
        uow.executar(
            """INSERT INTO resolucao (id, pendencia_id, acao, autor, instante, alvo,
                   motivo, desfaz, execucao) VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                resolucao.id,
                resolucao.pendencia_id,
                resolucao.acao.value,
                resolucao.autor,
                resolucao.instante,
                resolucao.alvo.texto() if resolucao.alvo else None,
                resolucao.motivo,
                resolucao.desfaz,
                uow.execucao_id,
            ),
        )
        self._append(uow, [(tipo, resolucao.pendencia_id, conteudo)], resolucao.instante)

    def anonimizar_contraparte(self, uow: UoW, chave: ChaveNatural, motivo: str) -> None:
        """REG-04: elimina o dado pessoal por APPEND, preservando a auditabilidade.

        A decisão (camada, veredito, score) permanece íntegra; só a contraparte é
        substituída na leitura. A trilha continua sendo trilha.
        """
        self._append(
            uow,
            [(Tipo.ANONIMIZACAO, chave.texto(), {"motivo": motivo})],
            agora(),
        )

    # -------------------------------------------------------------- leituras

    def historico(self, chave: ChaveNatural | str) -> list[Evento]:
        """IMP-08: `chave` é a ChaveNatural — a identidade da OBSERVAÇÃO.

        Foi a escolha explícita entre as três leituras possíveis (observação,
        evento, par), porque é sobre a linha concreta que o auditor pergunta:
        "de onde veio esta transação e o que o sistema decidiu sobre ela?".
        """
        texto = chave if isinstance(chave, str) else chave.texto()
        cur = self._store.conexao.execute(
            "SELECT * FROM auditoria WHERE chave = ? ORDER BY seq", (texto,)
        )
        eventos = [self._para_evento(l) for l in cur.fetchall()]
        return self._aplicar_anonimizacao(eventos)

    def eventos_da_execucao(self, execucao_id: str) -> list[Evento]:
        cur = self._store.conexao.execute(
            "SELECT * FROM auditoria WHERE execucao = ? ORDER BY seq", (execucao_id,)
        )
        return [self._para_evento(l) for l in cur.fetchall()]

    # -------------------------------------------------------------- internos

    def _append(
        self, uow: UoW, linhas: Sequence[tuple[str, str | None, dict]], instante: str
    ) -> None:
        uow.executar_muitos(
            """INSERT INTO auditoria (execucao, tipo, chave, conteudo, instante)
               VALUES (?,?,?,?,?)""",
            [
                (uow.execucao_id, tipo, chave, json.dumps(conteudo, sort_keys=True, default=str), instante)
                for tipo, chave, conteudo in linhas
            ],
        )

    def _buscar_resolucao(self, resolucao_id: str) -> dict | None:
        linha = self._store.conexao.execute(
            "SELECT * FROM resolucao WHERE id = ?", (resolucao_id,)
        ).fetchone()
        return dict(linha) if linha else None

    @staticmethod
    def _para_evento(linha) -> Evento:
        d = dict(linha)
        return Evento(
            seq=int(d["seq"]),
            execucao=d["execucao"],
            tipo=d["tipo"],
            chave=d["chave"],
            conteudo=json.loads(d["conteudo"]),
            instante=d["instante"],
        )

    @staticmethod
    def _aplicar_anonimizacao(eventos: list[Evento]) -> list[Evento]:
        """Se houve anonimização, a contraparte some da LEITURA sem sumir o registro."""
        if not any(e.tipo == Tipo.ANONIMIZACAO for e in eventos):
            return eventos
        saida = []
        for e in eventos:
            if e.tipo == Tipo.DECISAO_DEDUP and e.conteudo.get("contraparte"):
                conteudo = dict(e.conteudo)
                conteudo["contraparte"] = "[anonimizado]"
                e = Evento(e.seq, e.execucao, e.tipo, e.chave, conteudo, e.instante)
            saida.append(e)
        return saida
