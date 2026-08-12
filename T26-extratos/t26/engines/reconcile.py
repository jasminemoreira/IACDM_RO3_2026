"""M-08 reconcile-engine — casamento 1:1 extrato × livro interno.

Algoritmo DETERMINÍSTICO e declarado (IMP-01: sem essa decisão o módulo não é
implementável de forma reproduzível, e VAL-5 exige reprodutibilidade):

  guloso estável por score decrescente
  desempate 1: menor distância de data
  desempate 2: ChaveNatural (lexicográfica) — NUNCA id gerado em execução

O desempate por id gerado por execução foi rejeitado por IMP-09: com uuid ou
autoincremento de base recriada, o desempate vira arbitrário e VAL-5 quebra
exatamente no caso em que o desempate existe para agir.

O ótimo global (atribuição húngara) foi rejeitado por PRF-04: O(n³) inviabiliza
VAL-4 mesmo com blocking, e o ganho de qualidade não compensa — o guloso estável
com desempate declarado é reproduzível e explicável ao analista, que é o que a
auditoria contábil pede.

ASM-06 / I4 — o caso 1:N é DETECTADO antes de escolher. Casar 1:N
automaticamente está fora de escopo por decisão da Fase 0; esses casos viram
pendência em vez de serem ignorados ou resolvidos em silêncio.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Sequence

from t26.domain.model import (
    Casamento,
    ChaveNatural,
    Lancamento,
    PendenciaConciliacao,
    Resultado,
    ResultadoConciliacao,
    Situacao,
    Transacao,
)
from t26.matching import matcher as M


@dataclass
class ConfigConciliacao:
    """P2 — tolerância de valor com DEFAULT ZERO.

    Casar valores diferentes por padrão esconderia erro contábil; a tolerância só
    entra quando o operador a liga explicitamente, e o par resultante recebe
    `casado-com-divergencia` com o delta registrado.
    """

    tolerancia_valor: Decimal = Decimal("0")
    #: Quantos candidatos acima do corte de revisão bastam para o caso virar 1:N
    max_candidatos_automatico: int = 1


def _id_pendencia(transacao: ChaveNatural, candidatos: Sequence[ChaveNatural]) -> str:
    material = transacao.texto() + "||" + "|".join(sorted(c.texto() for c in candidatos))
    return "C" + hashlib.sha256(material.encode()).hexdigest()[:16]


class ReconcileEngine:
    def __init__(self, store, audit_log) -> None:
        self._store = store
        self._log = audit_log

    def conciliar(
        self,
        uow,
        transacoes: Sequence[Transacao],
        lancamentos: Sequence[Lancamento],
        config: ConfigConciliacao | None = None,
    ) -> ResultadoConciliacao:
        config = config or ConfigConciliacao()
        resultado = ResultadoConciliacao()

        # Candidatos por bloco, com o mesmo teto e a mesma regra de excedente.
        pares, excedentes, _ = M.candidatos(transacoes, lancamentos)

        pontuados: list[tuple[int, int, str, Transacao, Lancamento]] = []
        candidatos_por_transacao: dict[str, list[tuple[int, Lancamento]]] = {}

        for par in pares:
            transacao, lancamento = par.esquerda, par.direita
            pontos = M.score_conciliacao(transacao, lancamento, config.tolerancia_valor)
            if pontos < M.CORTE_REVISAO:
                continue
            dias = abs((transacao.data - lancamento.data).days)
            pontuados.append(
                (pontos, -dias, transacao.chave.texto(), transacao, lancamento)
            )
            candidatos_por_transacao.setdefault(transacao.chave.texto(), []).append(
                (pontos, lancamento)
            )

        # ASM-06 / I4 — 1:N detectado ANTES de escolher.
        ambiguas: set[str] = {
            chave
            for chave, cands in candidatos_por_transacao.items()
            if len([c for c in cands if c[0] >= M.CORTE_FUSAO])
            > config.max_candidatos_automatico
        }

        # Ordenação total e determinística: score desc, distância de data asc,
        # ChaveNatural asc. Nada aqui depende de id gerado nem de ordem de hash.
        pontuados.sort(key=lambda p: (-p[0], -p[1], p[2]))

        usadas_t: set[str] = set()
        usados_l: set[str] = set()

        for pontos, neg_dias, _, transacao, lancamento in pontuados:
            kt, kl = transacao.chave.texto(), lancamento.chave.texto()
            if kt in usadas_t or kl in usados_l:
                continue
            if kt in ambiguas:
                continue
            dias = -neg_dias
            delta = transacao.valor.valor - lancamento.valor.valor

            if pontos >= M.CORTE_FUSAO and delta == 0 and dias == 0:
                res, sit = Resultado.CASADO, Situacao.AUTOMATICA
            elif pontos >= M.CORTE_FUSAO:
                res, sit = Resultado.CASADO_COM_DIVERGENCIA, Situacao.AUTOMATICA
            else:
                continue  # entre os cortes: vira pendência abaixo, não casa aqui

            resultado.casamentos.append(
                Casamento(
                    transacao=transacao.chave,
                    lancamento=lancamento.chave,
                    resultado=res,
                    situacao=sit,
                    score=pontos,
                    delta_valor=delta,
                    delta_dias=dias,
                )
            )
            usadas_t.add(kt)
            usados_l.add(kl)

        # Pendências: ambíguas (1:N) e faixa de revisão.
        for chave, cands in candidatos_por_transacao.items():
            if chave in usadas_t:
                continue
            transacao = next(t for t in transacoes if t.chave.texto() == chave)
            candidatas = tuple(l.chave for _, l in sorted(cands, key=lambda c: -c[0]))
            scores = tuple(sorted((p for p, _ in cands), reverse=True))
            motivo = (
                f"{len(cands)} candidatos acima do corte de revisão — caso 1:N, "
                "casamento automático fora de escopo por decisão da Fase 0"
                if chave in ambiguas
                else f"melhor score {scores[0]} entre {M.CORTE_REVISAO} e {M.CORTE_FUSAO}"
            )
            pend = PendenciaConciliacao(
                id=_id_pendencia(transacao.chave, candidatas),
                transacao=transacao.chave,
                candidatos=candidatas,
                scores=scores,
                motivo=motivo,
            )
            resultado.pendencias.append(pend)
            usadas_t.add(chave)

        # PRF-06 — excedente de bloco vira pendência, nunca órfão silencioso.
        for exc in excedentes:
            chave = exc.item.chave
            if chave.texto() in usadas_t:
                continue
            pend = PendenciaConciliacao(
                id=_id_pendencia(chave, []),
                transacao=chave,
                candidatos=(),
                scores=(),
                motivo=(
                    f"bloco {exc.bloco} com {exc.tamanho_bloco} itens excede o teto "
                    f"{M.TETO_BLOCO}; escalado para revisão em vez de descartado"
                ),
            )
            resultado.pendencias.append(pend)
            usadas_t.add(chave.texto())

        # I3 — todo item termina em exatamente um estado.
        for transacao in transacoes:
            if transacao.chave.texto() not in usadas_t:
                resultado.orfaos_extrato.append(transacao.chave)
        for lancamento in lancamentos:
            if lancamento.chave.texto() not in usados_l:
                resultado.orfaos_livro.append(lancamento.chave)

        self._store.salvar_casamentos(uow, resultado.casamentos)
        for pend in resultado.pendencias:
            uow.executar(
                """INSERT OR IGNORE INTO pendencia
                       (id, familia, esquerda, candidatos, scores, motivo, aberta, execucao)
                   VALUES (?,?,?,?,?,?,1,?)""",
                (
                    pend.id,
                    "conciliacao",
                    pend.transacao.texto(),
                    json.dumps([c.texto() for c in pend.candidatos]),
                    json.dumps(list(pend.scores)),
                    pend.motivo,
                    uow.execucao_id,
                ),
            )
        return resultado
