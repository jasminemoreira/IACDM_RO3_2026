"""Porta `Provider` — contrato unico para os dois provedores heterogeneos.

Forma abstrata comum aos tres protocolos reais (Google syncToken, Microsoft
Graph deltaLink, CalDAV RFC 6578) — ver specs/technical/provider-sync-protocols.md.

Invariantes do contrato (achado LIN-02, correcao em V(3)):
  * exatamente UM de `next_page_token` / `next_state_token` e nao-nulo;
  * `state_token` e OPACO: proibido parsear, ordenar ou derivar tempo dele
    (RFC 6578 §3.2);
  * remocoes vem em `tombstones`; ausencia de item NAO significa remocao;
  * `invalidated=True` obriga o chamador a descartar o token e refazer full sync;
  * `write()` devolve o RECURSO GRAVADO, nao so a versao (correcao C-2 / LIN-07)
    — sem isso a Regra 1 (ancestral = o que o provedor devolveu) e inaplicavel.
"""

from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

# MEC-D: parametros com valor declarado, nunca inventados na hora de codar.
DEFAULT_PAGE_SIZE = 100
MAX_PAGES_PER_ROUND = 50  # 5x o normal de 10 paginas para 1.000 eventos

_SAFE_ID = re.compile(r"[^A-Za-z0-9._-]")


def sanitize_id(provider_id: str) -> str:
    """SEC-04/05: o id vem do 'provedor' e vira nome de arquivo. Sem isso, um id
    contendo `../` escapa do diretorio do provedor."""
    cleaned = _SAFE_ID.sub("_", provider_id)
    if not cleaned or cleaned in (".", ".."):
        raise ValueError(f"provider_id invalido: {provider_id!r}")
    return cleaned[:120]


@dataclass(frozen=True, slots=True)
class ObservabilityWindow:
    """O que ESTE provedor consegue observar. Governa a decisao de PRESENCA
    (V(3) Regra 2). Nao confundir com ExpansionWindow — correcao C-3."""

    start: datetime | None = None
    end: datetime | None = None

    @property
    def unbounded(self) -> bool:
        return self.start is None and self.end is None

    def contains(self, moment: datetime) -> bool:
        if self.start is not None and moment < self.start:
            return False
        if self.end is not None and moment >= self.end:
            return False
        return True


@dataclass(frozen=True, slots=True)
class WriteOp:
    kind: str  # "create" | "update" | "delete"
    ics: str | None = None
    provider_id: str | None = None


@dataclass(frozen=True, slots=True)
class WriteResult:
    """C-2: o recurso gravado, como o provedor o guardou (ja renormalizado)."""

    provider_id: str
    version: str
    stored_ics: str | None


@dataclass(slots=True)
class Delta:
    items: list[tuple[str, str, str]] = field(default_factory=list)  # (id, version, ics)
    tombstones: list[str] = field(default_factory=list)
    next_page_token: str | None = None
    next_state_token: str | None = None
    invalidated: bool = False


@dataclass(frozen=True, slots=True)
class Scenario:
    """Comportamento adverso DECLARATIVO (MEC-D, achado IMP-01).

    Sem isto o simulador e arbitrario: 'quando duplica uma pagina' e 'quando
    invalida o token' viravam decisao do momento, e o teste nao reproduzia.
    """

    page_size: int = DEFAULT_PAGE_SIZE
    invalidate_token_at_cycle: int | None = None
    duplicate_item_at_page: int | None = None
    calendar_tz: str = "UTC"

    @staticmethod
    def from_dict(data: dict) -> Scenario:
        return Scenario(
            page_size=int(data.get("page_size", DEFAULT_PAGE_SIZE)),
            invalidate_token_at_cycle=data.get("invalidate_token_at_cycle"),
            duplicate_item_at_page=data.get("duplicate_item_at_page"),
            calendar_tz=data.get("calendar_tz", "UTC"),
        )


def encode_token(payload: dict) -> str:
    """Token OPACO para o chamador. A opacidade e do contrato, nao do formato."""
    return base64.urlsafe_b64encode(json.dumps(payload, sort_keys=True).encode()).decode()


def decode_token(token: str) -> dict:
    return json.loads(base64.urlsafe_b64decode(token.encode()).decode())


class Provider(Protocol):
    name: str
    dialect: str

    def pull(self, state_token: str | None) -> Delta: ...

    def write(self, op: WriteOp) -> WriteResult: ...

    def get(self, provider_id: str) -> str | None: ...

    def observability_window(self) -> ObservabilityWindow: ...
