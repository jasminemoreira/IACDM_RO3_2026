"""M-06 configuracao — objeto congelado da configuração de DECISÃO.

Folha do grafo de dependências: não importa nenhum outro módulo do domínio.

Guarda APENAS parâmetros de decisão. Semente e cenário moram em
`simulador_de_cenario` (separação decidida em V(3), achado IMP-05): é o que
torna o critério de acerto CA-0 verificável de forma estrutural — mesma
`Configuracao`, `Cenario` diferente.

Toda constante numérica aqui tem fonte em specs/technical/canary-decision-parameters.md.
A ÚNICA exceção é a guarda absoluta, que por isso não tem valor padrão.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# --- Padrões com fonte bibliográfica -----------------------------------------

AMOSTRA_MINIMA = 50
"""R-03/R-05: 'at least 50 pieces of time series data per metric for the
statistical analysis to produce accurate results'."""

ALFA = 0.01
"""R-02 exige 98% de confiança no teste BICAUDAL do Kayenta, isto é 0,02
repartidos em 0,01 por cauda. Como julgamos com teste UNICAUDAL (a direção da
métrica define a cauda de interesse), 0,01 é o valor que preserva a taxa por
cauda da fonte. Manter 0,02 aqui dobraria o falso positivo — achado SCI-08."""

LIMITE_ERROS_CONSECUTIVOS = 4
"""R-06, comentário do código-fonte do Argo Rollouts: 'ConsecutiveErrorLimit is
the maximum number of times the measurement is allowed to error in succession,
before the metric is considered error (default: 4)'."""

LIMITE_FALHAS = 3
"""R-07 (Flagger `threshold`): número de verificações falhas toleradas antes do
rollback. A doc exemplifica 10 com intervalo de 1min; 3 é o análogo para os
poucos julgamentos que cabem numa execução comprimida, preservando a razão."""

HISTERESE_K = 2
"""R-06 (`consecutiveSuccessLimit`): 'the number of consecutive times the
measurement must succeed'. É o que impede a oscilação pausado<->progredindo."""

PISO_ESTAVEL = 50
"""R-04, modelo de três clusters da Netflix: o cluster de produção recebe a
MAIORIA das requisições enquanto baseline e canário ficam pequenos e iguais.
O piso é o que impede a rampa de zerar a estável — achado SUS-03."""

RAZAO_VOLUME_MINIMA = 0.8
"""R-03 exige que baseline e canário recebam 'same type and amount of traffic'.
Como V(2) passou a DERIVAR peso(baseline) == peso(canario), qualquer divergência
de volume é anomalia, não configuração. O piso de 0,8 é a tolerância a ruído de
amostragem; abaixo dele o julgamento é recusado — achado REG-01."""


class ConfiguracaoInvalida(ValueError):
    """Uma das quatro validações de construção falhou."""


@dataclass(frozen=True)
class Configuracao:
    """Configuração de decisão. Imutável e validada na construção.

    `guarda_taxa_erro` e `guarda_latencia_p99` NÃO têm valor padrão de
    propósito: são o único parâmetro do sistema sem fonte bibliográfica
    (achado SCI-01, risco aceito e registrado). Exigi-los do operador não
    melhora a fundamentação — melhora a atribuição, e é o que temos.
    """

    # --- Guarda absoluta: obrigatórios, sem fonte, decisão do operador -------
    guarda_taxa_erro: float
    guarda_latencia_p99: float

    # --- Parâmetros com fonte ------------------------------------------------
    amostra_minima: int = AMOSTRA_MINIMA
    tamanho_janela: int = AMOSTRA_MINIMA
    alfa: float = ALFA
    limiar_score: float = 100.0
    piso_estavel: int = PISO_ESTAVEL
    razao_volume_minima: float = RAZAO_VOLUME_MINIMA
    limite_falhas: int = LIMITE_FALHAS
    limite_erros_consecutivos: int = LIMITE_ERROS_CONSECUTIVOS
    histerese_k: int = HISTERESE_K

    # --- Temporização (unidades de tempo virtual) ----------------------------
    intervalo: int = 10
    taxa_de_amostragem: int = 5
    duracao_maxima: int = 400

    pesos: tuple[int, ...] = field(default=(2, 5, 10, 15))

    def __post_init__(self) -> None:
        self._validar()

    def _validar(self) -> None:
        """As quatro validações enumeradas em V(3) — achado MEC-03.

        'Validado na construção' sem a lista é promessa, não tolerância.
        """
        # 1. Teto de exposição (SUS-03): a estável nunca perde a maioria.
        if not self.pesos:
            raise ConfiguracaoInvalida("sequência de pesos vazia")
        exposicao = 2 * max(self.pesos)
        teto = 100 - self.piso_estavel
        if exposicao > teto:
            raise ConfiguracaoInvalida(
                f"teto de exposição violado: 2×{max(self.pesos)}% = {exposicao}% "
                f"excede {teto}% (piso da estável = {self.piso_estavel}%). "
                "Com espelhamento baseline==canário, a estável ficaria abaixo do piso."
            )

        # 2. Independência entre julgamentos (CTL-03): janelas disjuntas.
        novas_por_intervalo = self.intervalo * self.taxa_de_amostragem
        if novas_por_intervalo < self.tamanho_janela:
            raise ConfiguracaoInvalida(
                f"julgamentos não independentes: intervalo×taxa = {novas_por_intervalo} "
                f"amostras novas < janela de {self.tamanho_janela}. Julgamentos "
                "consecutivos compartilhariam amostras, e o limite de falhas "
                "pressupõe independência."
            )

        # 3. Sequência de pesos estritamente crescente.
        if any(b <= a for a, b in zip(self.pesos, self.pesos[1:])):
            raise ConfiguracaoInvalida(f"pesos não estritamente crescentes: {self.pesos}")
        if self.pesos[0] <= 0:
            raise ConfiguracaoInvalida("o primeiro peso deve ser positivo")

        # 4. Limites mínimos.
        if self.histerese_k < 1:
            raise ConfiguracaoInvalida("histerese_k deve ser >= 1")
        if self.limite_falhas < 1:
            raise ConfiguracaoInvalida("limite_falhas deve ser >= 1")
        if self.limite_erros_consecutivos < 1:
            raise ConfiguracaoInvalida("limite_erros_consecutivos deve ser >= 1")
        if self.tamanho_janela < self.amostra_minima:
            raise ConfiguracaoInvalida(
                f"janela de {self.tamanho_janela} < amostra mínima de {self.amostra_minima}"
            )
        if not 0.0 < self.razao_volume_minima <= 1.0:
            raise ConfiguracaoInvalida("razao_volume_minima deve estar em (0, 1]")
        if self.guarda_taxa_erro <= 0 or self.guarda_latencia_p99 <= 0:
            raise ConfiguracaoInvalida("limiares da guarda absoluta devem ser positivos")

    def proximo_peso(self, atual: int | None) -> int | None:
        """Próximo degrau da progressão, ou None se `atual` é o último."""
        if atual is None:
            return self.pesos[0]
        try:
            i = self.pesos.index(atual)
        except ValueError:
            raise ConfiguracaoInvalida(f"{atual} não é um passo da sequência {self.pesos}")
        return self.pesos[i + 1] if i + 1 < len(self.pesos) else None

    def ultimo(self, peso: int) -> bool:
        return peso == self.pesos[-1]
