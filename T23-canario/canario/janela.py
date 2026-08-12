"""M-01 janela — janela DESLIZANTE de amostras por participante×métrica.

Deslizante, não cumulativa. A versão cumulativa de V(1) acumulava cinco defeitos
de cinco lentes distintas de uma vez só: misturava regimes de carga (ASM-03),
custava O(n log n) crescente por julgamento (PERF-01), ficava progressivamente
mais lenta para reagir justo quando o canário tinha mais tráfego (CTL-02),
retinha sem teto (SUS-02) e importava os 50 pontos de R-03 para um conceito que
a fonte não governa (SCI-04).

Também é aqui que mora a defesa contra o achado mais perverso da Fase 2:
um canário que PAROU de receber requisições apresenta latência e taxa de erro
melhores e saturação menor, e seria promovido justamente por estar quebrado
(REG-01). `volumes_comparaveis` recusa o julgamento nesse caso.
"""

from __future__ import annotations

from collections import deque

from .alvo_de_implantacao import Papel
from .configuracao import Configuracao


class Janela:
    def __init__(self, cfg: Configuracao) -> None:
        self._cfg = cfg
        self._series: dict[tuple[Papel, str], deque[float]] = {}

    def adicionar(self, papel: Papel, metrica: str, valor: float) -> None:
        chave = (papel, metrica)
        serie = self._series.get(chave)
        if serie is None:
            # maxlen faz o descarte do mais antigo ser O(1) — achado PERF-03.
            serie = deque(maxlen=self._cfg.tamanho_janela)
            self._series[chave] = serie
        serie.append(valor)

    def series(self, papel: Papel, metrica: str) -> list[float]:
        return list(self._series.get((papel, metrica), ()))

    def contagem(self, papel: Papel, metrica: str) -> int:
        return len(self._series.get((papel, metrica), ()))

    def pronta(self, metrica: str) -> bool:
        """Canário e baseline têm amostra suficiente para um teste válido.

        R-03/R-05: 'at least 50 pieces of time series data per metric for the
        statistical analysis to produce accurate results'. Abaixo disso o
        veredito é Nodata — não é aprovação nem reprovação.
        """
        minimo = self._cfg.amostra_minima
        return (
            self.contagem(Papel.CANARIO, metrica) >= minimo
            and self.contagem(Papel.BASELINE, metrica) >= minimo
        )

    def volumes_comparaveis(self, metrica: str) -> bool:
        """Os volumes de canário e baseline estão próximos o bastante?

        Como `alvo-de-implantacao` DERIVA peso(baseline) == peso(canario), os
        dois deveriam receber o mesmo volume por construção. Uma divergência
        real significa que um dos lados parou de produzir dados — e é isso que
        não pode ser lido como 'está tudo bem'.
        """
        c = self.contagem(Papel.CANARIO, metrica)
        b = self.contagem(Papel.BASELINE, metrica)
        if c == 0 or b == 0:
            return False
        return min(c, b) / max(c, b) >= self._cfg.razao_volume_minima

    def limpar(self) -> None:
        """Descarta tudo. Usado ao mudar de passo, para que o julgamento do
        passo N+1 não herde amostras do regime de carga do passo N."""
        self._series.clear()
