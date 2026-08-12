"""M-04 provider-alpha — provedor simulado de semantica estilo Google.

Fonte da semantica: specs/technical/provider-sync-protocols.md (REF-5).
  * token de estado (`nextSyncToken`) OPACO, distinto do token de paginacao
    (`nextPageToken`);
  * remocao permanece observavel como recurso com STATUS:CANCELLED — "the result
    will always contain deleted entries";
  * invalidacao de token equivalente ao HTTP 410 fullSyncRequired;
  * SEM janela temporal: observability_window ilimitada.
"""

from __future__ import annotations

from .base import ObservabilityWindow
from ._store import FileBackedProvider


class ProviderAlpha(FileBackedProvider):
    name = "alpha"
    dialect = "alpha"
    keeps_cancelled_resource = True  # o recurso cancelado continua existindo

    def observability_window(self) -> ObservabilityWindow:
        return ObservabilityWindow()  # ilimitada
