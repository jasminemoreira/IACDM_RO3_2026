"""M-03 score — agregação dos vereditos. FUNÇÃO PURA.

    score = (quantidade de Pass / quantidade de vereditos != Nodata) × 100

`Nodata` sai do DENOMINADOR, não entra como reprovação (R-02, R-04).

Sem faixa `Marginal`: com 3 métricas o score só assume {0; 33,3; 66,7; 100} e
nenhum valor alcançável cai em [75, 95), a faixa marginal de R-03. Implementá-la
seria implementar um ramo que nenhum teste consegue exercitar.
"""

from __future__ import annotations

from dataclasses import dataclass

from .julgamento import Metrica, Veredito


@dataclass(frozen=True)
class Score:
    valor: float | None
    """None quando TODAS as métricas deram Nodata — ver `indefinido`."""
    vereditos: dict[str, Veredito]

    @property
    def indefinido(self) -> bool:
        """Denominador zero.

        Nenhuma fonte cobre este caso. Tratamento adotado: NÃO é aprovação nem
        reprovação — é ausência de julgamento. Reprovar por falta de dado
        transformaria coletor lento em rollback; aprovar promoveria um canário
        que ninguém observou.
        """
        return self.valor is None

    @property
    def reprovadas(self) -> list[str]:
        return [n for n, v in self.vereditos.items() if v is Veredito.HIGH]


def pontuar(vereditos: dict[Metrica, Veredito]) -> Score:
    considerados = {m.nome: v for m, v in vereditos.items() if v is not Veredito.NODATA}
    todos = {m.nome: v for m, v in vereditos.items()}
    if not considerados:
        return Score(valor=None, vereditos=todos)
    passes = sum(1 for v in considerados.values() if v is Veredito.PASS)
    return Score(valor=passes / len(considerados) * 100.0, vereditos=todos)


def aprova(score: Score, limiar: float) -> bool:
    """Comparação INCLUSIVA (>=).

    R-02/R-03: 'A score of exactly 95 with a pass threshold of 95 results in a
    pass.' Um score indefinido nunca aprova — e também não reprova; quem trata
    isso é o coordenador, que mantém o passo aguardando amostra.
    """
    if score.indefinido:
        return False
    return score.valor >= limiar
