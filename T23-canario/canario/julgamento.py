"""M-02 julgamento — dono de `Metrica`, `Direcao` e `Veredito`. FUNÇÃO PURA.

Recebe duas listas de números e devolve um veredito. Não toca relógio, rede nem
terminal — é o que torna os critérios VAL-3 e VAL-4 verificáveis por tabela de
entrada/saída, sem simulador.

Teste: Mann-Whitney U (R-02), não paramétrico porque distribuições de latência
são assimétricas com cauda longa e um teste paramétrico assumiria uma
normalidade que não existe.

UNICAUDAL, com a cauda escolhida pela DIREÇÃO da métrica, e alfa = 0,01 para
preservar a taxa por cauda dos 98% bicaudais de R-02 (achado SCI-08). Como
consequência, o veredito `Low` nunca é produzido e por isso não existe no enum
— manter um valor de domínio inalcançável seria código morto (achado MEC-04).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from scipy.stats import mannwhitneyu


class Direcao(str, Enum):
    MENOR_E_MELHOR = "menor_e_melhor"
    MAIOR_E_MELHOR = "maior_e_melhor"


@dataclass(frozen=True)
class Metrica:
    """A `direcao` mora AQUI e em nenhum outro lugar.

    Espalhada como condicional pelo código, ela inverteria o sinal do
    julgamento silenciosamente ao se acrescentar uma métrica maior-é-melhor.
    """

    nome: str
    direcao: Direcao = Direcao.MENOR_E_MELHOR


class Veredito(str, Enum):
    PASS = "Pass"
    """Nenhuma diferença significativa entre canário e baseline."""
    HIGH = "High"
    """O canário está significativamente PIOR que o baseline, na direção da métrica."""
    NODATA = "Nodata"
    """Amostra insuficiente. Excluído do denominador do score (R-02, R-04)."""


# As três métricas julgadas neste ciclo. Todas menor-é-melhor.
# Cobrem latência, erros e saturação, que é a recomendação explícita de R-05.
# 'Tráfego', o quarto sinal de ouro de R-01, NÃO é julgado como métrica: sua
# ausência é coberta por `janela.volumes_comparaveis` (achado REG-01), porque
# acrescentar métrica mudaria O QUE o sistema julga, e isso seria escopo.
LATENCIA_P99_SUCESSO = Metrica("latencia_p99_sucesso")
TAXA_DE_ERRO = Metrica("taxa_de_erro")
SATURACAO = Metrica("saturacao")

METRICAS: tuple[Metrica, ...] = (LATENCIA_P99_SUCESSO, TAXA_DE_ERRO, SATURACAO)


def julgar(
    serie_canario: list[float],
    serie_baseline: list[float],
    metrica: Metrica,
    alfa: float,
    amostra_minima: int,
) -> Veredito:
    """Compara canário contra BASELINE PAREADO — nunca contra a estável.

    R-05: 'Don't compare the canary to production instances. Many differences
    can skew the results of the analysis: cache warmup time, heap size,
    load-balancing algorithms.'
    """
    if len(serie_canario) < amostra_minima or len(serie_baseline) < amostra_minima:
        return Veredito.NODATA

    # A cauda testada é a que representa "o canário está pior".
    alternative = "greater" if metrica.direcao is Direcao.MENOR_E_MELHOR else "less"

    try:
        resultado = mannwhitneyu(
            serie_canario,
            serie_baseline,
            alternative=alternative,
            method="auto",
        )
    except ValueError:
        # scipy recusa entradas degeneradas (p.ex. ambas constantes e idênticas).
        # Sem variação não há diferença a detectar: não é falha do canário.
        return Veredito.NODATA

    return Veredito.HIGH if resultado.pvalue < alfa else Veredito.PASS
