"""M-07 dedup-engine — cadeia de precedência L0→L5, em lote.

Chain of Responsibility: a cadeia para no primeiro elo que decide, e a decisão
carrega SEMPRE qual elo decidiu e a evidência (sem isso, VAL-2 — zero falso
positivo — seria inverificável, porque não haveria como investigar um).

Camadas em specs/technical/parametros-matching.md, revisadas em V(3):
  L0 resolução humana gravada  · L1 ChaveNatural idêntica (garantida pelo UNIQUE
  do store) · L2 mesma origem com chaves distintas → veto (I6) · L3 score ≥ 95 →
  duplicata · L4 70 ≤ score < 95 OU excedente de bloco → pendência · L5 → distintas

PRF-02: contrato EM LOTE. A versão anterior consultava o repositório uma vez por
transação — 50.000 idas ao banco para um lote de 50.000, o padrão N+1 que fazia
VAL-4 falhar antes de qualquer discussão de algoritmo.

CTL-01: L0 é chaveado pela ChaveNatural do PAR. A resolução sobrevive à troca de
FITID entre downloads porque a chave natural não depende dele quando ele muda —
sem isso a mesma pendência reaparecia a cada importação, indefinidamente.

CTL-03: existe malha de correção. `desfazer_duplicata` devolve o item como
PENDENTE — não como não classificado (a execução seguinte poderia refundi-lo) nem
como resolvido (contradiria o motivo do desfazer). Ver PRC-07.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Sequence

from t26.domain.model import (
    Camada,
    ChaveNatural,
    DecisaoDedup,
    PendenciaDedup,
    Transacao,
    Veredito,
)
from t26.matching import matcher as M


@dataclass
class Escopo:
    """ASM-03 — o escopo de comparação é DECLARADO, nunca implícito.

    A versão anterior recebia "existentes" sem dizer o que era: restrito à conta,
    a duplicata cross-source entre contas nunca seria detectada (requisito da
    Fase 0); irrestrito, o custo explodiria.

    SUS-02: a janela existe porque o custo não pode crescer com a HISTÓRIA. Uma
    duplicata de reimportação de três anos atrás é implausível, e pagar
    similaridade sobre ela é trabalho sem valor entregue.
    """

    mesma_conta: bool = True
    cross_source: bool = True
    janela_dias: int = 90


@dataclass
class ResultadoDedup:
    decisoes: list[DecisaoDedup] = field(default_factory=list)
    duplicatas: list[tuple[ChaveNatural, ChaveNatural]] = field(default_factory=list)
    pendencias: list[PendenciaDedup] = field(default_factory=list)
    metricas: M.MetricasBloco = field(default_factory=M.MetricasBloco)


def _id_pendencia(esquerda: ChaveNatural, candidatas: Sequence[ChaveNatural]) -> str:
    """Id determinístico: a mesma pendência recebe o mesmo id entre execuções.

    IMP-09/VAL-5: id gerado por execução (uuid, autoincremento) tornaria o
    desempate e a fila não reproduzíveis. Derivar do conteúdo é o que mantém o
    determinismo exigido.
    """
    material = esquerda.texto() + "||" + "|".join(sorted(c.texto() for c in candidatas))
    return "P" + hashlib.sha256(material.encode()).hexdigest()[:16]


class DedupEngine:
    def __init__(self, store, audit_log) -> None:
        self._store = store
        self._log = audit_log

    def classificar_lote(
        self,
        uow,
        novas: Sequence[Transacao],
        existentes: Sequence[Transacao],
        escopo: Escopo | None = None,
    ) -> ResultadoDedup:
        escopo = escopo or Escopo()
        resultado = ResultadoDedup()

        candidatas_por_escopo = self._filtrar(novas, existentes, escopo)
        pares, excedentes, metricas = M.candidatos(novas, candidatas_por_escopo)
        resultado.metricas = metricas

        resolucoes = self._resolucoes_gravadas()
        melhores: dict[str, tuple[int, Transacao]] = {}

        for par in pares:
            nova: Transacao = par.esquerda
            outra: Transacao = par.direita

            # L0 — resolução humana. I7: soberana, nunca reavaliada.
            gravada = resolucoes.get(_chave_par(nova.chave, outra.chave))
            if gravada is not None:
                veredito = (
                    Veredito.DUPLICATA if gravada == "e-a-mesma" else Veredito.DISTINTA
                )
                resultado.decisoes.append(
                    DecisaoDedup(
                        nova.chave, veredito, Camada.L0_RESOLUCAO_HUMANA,
                        f"resolução humana registrada: {gravada}", outra.chave,
                    )
                )
                if veredito is Veredito.DUPLICATA:
                    resultado.duplicatas.append((nova.chave, outra.chave))
                continue

            # L2 — mesma origem, chaves distintas: colisão legítima (I6).
            if M.mesma_origem(nova, outra):
                resultado.decisoes.append(
                    DecisaoDedup(
                        nova.chave, Veredito.DISTINTA, Camada.L2_CHAVE_NATURAL,
                        f"mesma origem {nova.fonte}/{nova.arquivo}: a fonte reportou "
                        "duas linhas, logo dois eventos", outra.chave,
                    )
                )
                continue

            pontos = M.score(M.Par(nova, outra, par.bloco), M.PERFIL_DEDUP)
            anterior = melhores.get(nova.chave.texto())
            if anterior is None or pontos > anterior[0]:
                melhores[nova.chave.texto()] = (pontos, outra)

        for nova in novas:
            melhor = melhores.get(nova.chave.texto())
            if melhor is None:
                continue
            pontos, outra = melhor

            if pontos >= M.CORTE_FUSAO:  # L3
                resultado.decisoes.append(
                    DecisaoDedup(
                        nova.chave, Veredito.DUPLICATA, Camada.L3_SCORE_ALTO,
                        f"score {pontos} >= corte de fusão {M.CORTE_FUSAO}", outra.chave, pontos,
                    )
                )
                resultado.duplicatas.append((nova.chave, outra.chave))
            elif pontos >= M.CORTE_REVISAO:  # L4
                pend = PendenciaDedup(
                    id=_id_pendencia(nova.chave, [outra.chave]),
                    esquerda=nova.chave,
                    candidatas=(outra.chave,),
                    scores=(pontos,),
                    motivo=f"score {pontos} entre {M.CORTE_REVISAO} e {M.CORTE_FUSAO}",
                )
                resultado.pendencias.append(pend)
                resultado.decisoes.append(
                    DecisaoDedup(
                        nova.chave, Veredito.PENDENCIA, Camada.L4_PENDENCIA,
                        pend.motivo, outra.chave, pontos,
                    )
                )
            else:  # L5
                resultado.decisoes.append(
                    DecisaoDedup(
                        nova.chave, Veredito.DISTINTA, Camada.L5_DISTINTAS,
                        f"score {pontos} < corte de revisão {M.CORTE_REVISAO}",
                        outra.chave, pontos,
                    )
                )

        # PRF-06 — excedente de bloco NUNCA vira "distinta". Vira pendência.
        for exc in excedentes:
            item = exc.item
            pend = PendenciaDedup(
                id=_id_pendencia(item.chave, []),
                esquerda=item.chave,
                candidatas=(),
                scores=(),
                motivo=(
                    f"bloco {exc.bloco} com {exc.tamanho_bloco} itens excede o teto "
                    f"{M.TETO_BLOCO}; não comparado exaustivamente para preservar VAL-4, "
                    "e escalado para revisão para preservar VAL-1"
                ),
            )
            resultado.pendencias.append(pend)
            resultado.decisoes.append(
                DecisaoDedup(
                    item.chave, Veredito.PENDENCIA, Camada.L4_PENDENCIA, pend.motivo
                )
            )

        self._persistir(uow, resultado)
        return resultado

    def desfazer_duplicata(self, uow, chave: ChaveNatural, motivo: str, autor: str) -> None:
        """CTL-03 / PRC-07 — devolve o item ao estado PENDENTE, não a 'sem estado'."""
        self._store.desmarcar_duplicata(uow, chave)
        self._log.registrar_lote(
            uow,
            [
                DecisaoDedup(
                    chave, Veredito.PENDENCIA, Camada.L4_PENDENCIA,
                    f"des-duplicação por {autor}: {motivo}",
                )
            ],
        )

    # -------------------------------------------------------------- internos

    def _filtrar(
        self, novas: Sequence[Transacao], existentes: Sequence[Transacao], escopo: Escopo
    ) -> list[Transacao]:
        if not novas:
            return []
        datas = [t.data for t in novas]
        inicio, fim = min(datas), max(datas)
        # PRF-02 — o conjunto de contas é pré-computado UMA vez. Testá-lo com um
        # `any` dentro do laço sobre `existentes` custa len(novas) por item, o que
        # é O(n²) e foi exatamente o que fez VAL-4 estourar na primeira medição.
        contas_novas = {n.conta for n in novas}
        saida = []
        for e in existentes:
            if inicio <= e.data <= fim:
                delta = 0
            else:
                delta = min(abs((e.data - inicio).days), abs((e.data - fim).days))
            if delta > escopo.janela_dias:
                continue
            mesma = e.conta in contas_novas
            if mesma and not escopo.mesma_conta:
                continue
            if not mesma and not escopo.cross_source:
                continue
            saida.append(e)
        return saida

    def _resolucoes_gravadas(self) -> dict[str, str]:
        """Resoluções vigentes por par. Um desfazer posterior anula o anterior.

        A trilha é append-only: a leitura reconstrói o estado vigente aplicando os
        registros em ordem, em vez de o banco guardar um estado mutável.
        """
        vigentes: dict[str, str] = {}
        anuladas: set[str] = set()
        # O JOIN recupera o lado ESQUERDO do par, que vive na pendência e não na
        # resolução. Sem ele a chave do dicionário não é a mesma que a da
        # consulta, L0 nunca dispara e a mesma pendência reaparece a cada
        # execução — o defeito que CTL-01 mandou corrigir.
        cur = self._store.conexao.execute(
            """SELECT r.*, p.esquerda AS esquerda
                 FROM resolucao r JOIN pendencia p ON p.id = r.pendencia_id
             ORDER BY r.instante, r.id"""
        )
        por_id: dict[str, dict] = {}
        for linha in cur.fetchall():
            d = dict(linha)
            por_id[d["id"]] = d
            if d["desfaz"]:
                anuladas.add(d["desfaz"])
        for ident, d in por_id.items():
            if ident in anuladas or d["alvo"] is None or d["esquerda"] is None:
                continue
            chave = "||".join(sorted([d["esquerda"], d["alvo"]]))
            vigentes[chave] = d["acao"]
        return vigentes

    def _persistir(self, uow, resultado: ResultadoDedup) -> None:
        for chave, de in resultado.duplicatas:
            self._store.marcar_duplicata(uow, chave, de)
        for pend in resultado.pendencias:
            uow.executar(
                """INSERT OR IGNORE INTO pendencia
                       (id, familia, esquerda, candidatos, scores, motivo, aberta, execucao)
                   VALUES (?,?,?,?,?,?,1,?)""",
                (
                    pend.id,
                    "dedup",
                    pend.esquerda.texto(),
                    json.dumps([c.texto() for c in pend.candidatas]),
                    json.dumps(list(pend.scores)),
                    pend.motivo,
                    uow.execucao_id,
                ),
            )
        # PRF-07 — um append por lote, não um por decisão.
        self._log.registrar_lote(uow, resultado.decisoes)


def _chave_par(a: ChaveNatural, b: ChaveNatural) -> str:
    return "||".join(sorted([a.texto(), b.texto()]))
