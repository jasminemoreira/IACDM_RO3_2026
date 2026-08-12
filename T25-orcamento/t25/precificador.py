"""M-04 precificador — custo real e reserva de pior caso.

Formula de custo: specs/examples/referencias-de-implementacao.md §2 (portada
literalmente). Aritmetica INTEIRA em nano; nenhuma divisao intermediaria.

Reserva de pior caso, V(3):

    pior_caso = bytes_do_corpo x preco_entrada + max_tokens x preco_saida

O termo de entrada usa o limite superior LOCAL `tokens_entrada <= bytes_do_corpo`:
num tokenizador BPE sobre UTF-8 todo token consome ao menos 1 byte. Isso devolve
o custo de entrada a reserva (achado A-05) sem chamar `count_tokens` (arbitragem
do operador, achados SUS-01/CIE-03).

PREMISSA A8 — NAO VERIFICADA. A desigualdade e raciocinio derivado, nao fonte
citada. Validar empiricamente na Fase 6 comparando count_tokens com bytes numa
amostra. Se falhar, o invariante do criterio de acerto cai junto.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .rate_card import RateCard


@dataclass(frozen=True)
class Uso:
    """Adapter do objeto `usage` da API — as QUATRO categorias, separadas.

    Agrega-las perderia a informacao de preco: cada categoria tem preco proprio
    (specs/technical/token-accounting.md §1).
    """

    tokens_entrada: int
    tokens_cache_leitura: int
    tokens_cache_escrita: int
    tokens_saida: int
    cache_escrita_1h: bool = False

    @property
    def total_entrada(self) -> int:
        return (
            self.tokens_entrada + self.tokens_cache_leitura + self.tokens_cache_escrita
        )


class Precificador:
    def __init__(self, rate_card: RateCard) -> None:
        self._rc = rate_card

    def custo(self, uso: Uso, modelo: str, instante: datetime) -> int:
        cat_escrita = "cache_escrita_1h" if uso.cache_escrita_1h else "cache_escrita_5m"
        p = self._rc.preco
        return (
            uso.tokens_entrada * p(modelo, "entrada", instante)
            + uso.tokens_cache_leitura * p(modelo, "cache_leitura", instante)
            + uso.tokens_cache_escrita * p(modelo, cat_escrita, instante)
            + uso.tokens_saida * p(modelo, "saida", instante)
        )

    def pior_caso(
        self, modelo: str, bytes_corpo: int, max_tokens: int, instante: datetime
    ) -> int:
        """Limite superior do custo desta requisicao, em nano."""
        if max_tokens <= 0:
            raise ValueError("max_tokens deve ser positivo")
        p = self._rc.preco
        return bytes_corpo * p(modelo, "entrada", instante) + max_tokens * p(
            modelo, "saida", instante
        )


def nano_para_texto(nano: int) -> str:
    """Apresentacao com 2 casas. Arredondamento SO na apresentacao (V(1) §1)."""
    sinal = "-" if nano < 0 else ""
    centavos = (abs(nano) + 5_000_000) // 10_000_000  # nano -> centavos, meio p/ cima
    return f"{sinal}{centavos // 100}.{centavos % 100:02d}"
