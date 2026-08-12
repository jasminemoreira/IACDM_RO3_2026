"""M-08 relogio — PORTA de tempo + adaptador virtual.

Nenhum outro módulo do sistema lê o relógio do sistema operacional. O tempo é
sempre injetado, e em teste avança programaticamente: uma implantação de horas
simuladas executa em milissegundos, de forma determinística e sem `sleep`.

A9 (premissa explícita): o DONO ÚNICO do avanço é o `coordenador`. Nenhum outro
módulo chama `avancar` — achado LIN-02.
"""

from __future__ import annotations

from typing import Protocol


class Relogio(Protocol):
    """Porta de tempo. Unidades são inteiras e adimensionais ('tiques')."""

    def agora(self) -> int: ...

    def avancar(self, delta: int) -> None: ...


class RelogioVirtual:
    """Adaptador determinístico. Único implementador neste ciclo."""

    def __init__(self, inicio: int = 0) -> None:
        self._t = inicio

    def agora(self) -> int:
        return self._t

    def avancar(self, delta: int) -> None:
        if delta <= 0:
            raise ValueError("o tempo virtual só avança")
        self._t += delta
