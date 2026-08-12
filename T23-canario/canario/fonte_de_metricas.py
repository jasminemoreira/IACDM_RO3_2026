"""M-09 fonte-de-metricas — PORTA de coleta.

QUATRO desfechos, não dois (achado RES-01). Distinguir "não consegui medir" de
"medi e está ruim" é o que impede que a queda do coletor derrube um canário
saudável — R-06: 'unlike failures, errors tend to happen ephemerally and may
recover on its own'.

A8 (premissa explícita): UMA chamada a `coletar` devolve UMA amostra. A
cardinalidade está fixada aqui porque duas implementações corretas do contrato
divergiriam sobre ela — achado LIN-01.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Union


@dataclass(frozen=True)
class Amostra:
    """Medição bem-sucedida."""

    valor: float
    instante: int


@dataclass(frozen=True)
class Indisponivel:
    """O coletor não respondeu. Conta como ERRO em sucessão, nunca como falha."""

    motivo: str = "coletor indisponível"


@dataclass(frozen=True)
class Lenta:
    """Respondeu além do prazo aceitável.

    Semântica declarada (achado LIN-04): é tratada como ERRO, não como amostra
    tardia. Um valor que chegou fora da janela a que pertence contaminaria a
    série com dado de outro regime — o mesmo defeito que a janela deslizante
    existe para evitar.
    """

    motivo: str = "coleta lenta"


@dataclass(frozen=True)
class Invalida:
    """Respondeu com valor não utilizável (NaN, negativo, infinito).

    Também tratada como ERRO: o coletor está quebrado, não a versão.
    """

    valor_bruto: float
    motivo: str = "valor inválido"


Resultado = Union[Amostra, Indisponivel, Lenta, Invalida]

FALHAS_DE_COLETA = (Indisponivel, Lenta, Invalida)
"""Os três desfechos que alimentam o contador de ERRO. Nenhum deles é falha do
canário."""


class FonteDeMetricas(Protocol):
    """Porta de coleta. Uma chamada, uma amostra (A8)."""

    def coletar(self, papel: str, metrica: str) -> Resultado: ...
