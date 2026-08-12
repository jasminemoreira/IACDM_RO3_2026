"""M-05 provider-beta — provedor simulado de semantica estilo Microsoft Graph.

Fonte da semantica: specs/technical/provider-sync-protocols.md (REF-6).
  * `@odata.deltaLink` (token de estado) vs `@odata.nextLink` (`$skiptoken`);
  * remocao sinalizada como `@removed` — o recurso SOME do armazenamento;
  * JANELA TEMPORAL OBRIGATORIA: `calendarView/delta` so observa
    [startDateTime, endDateTime]; eventos fora dela nao existem para o delta;
  * paginacao capaz de repetir item ja entregue (armadilha A-2, declarada no
    cenario).

Semantica de escrita fora da janela (achado RES-07, correcao V(4)): a escrita e
ACEITA, o recurso e devolvido, e o evento simplesmente nao aparece nos deltas
seguintes — ou seja, vira `Unobservable` por construcao, jamais `Absent`.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from ..canonical_event import UTC
from .base import ObservabilityWindow, Scenario
from ._store import FileBackedProvider


class ProviderBeta(FileBackedProvider):
    name = "beta"
    dialect = "beta"
    keeps_cancelled_resource = False  # o recurso removido some (@removed)

    def __init__(
        self,
        root: Path,
        scenario: Scenario | None = None,
        window: ObservabilityWindow | None = None,
    ) -> None:
        super().__init__(root, scenario)
        self._window = window or self._load_window()

    def _load_window(self) -> ObservabilityWindow:
        path = self.root / "scenario.json"
        if path.exists():
            data = json.loads(path.read_text()).get("observability_window")
            if data:
                return ObservabilityWindow(
                    datetime.fromisoformat(data["start"]).astimezone(UTC),
                    datetime.fromisoformat(data["end"]).astimezone(UTC),
                )
        return ObservabilityWindow()

    def observability_window(self) -> ObservabilityWindow:
        return self._window
