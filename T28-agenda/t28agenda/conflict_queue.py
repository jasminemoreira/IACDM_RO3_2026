"""M-08 conflict-queue — autoridade sobre o conflito (transicoes PURAS).

V(3) Regra 3: este modulo DECIDE o estado; `repository` apenas grava o que
recebe, verbatim, e nunca muta estado de conflito (achado ARC-08).

Maquina de estados (achados PRO-01, PRO-05):
    OPEN     --resolve-->  RESOLVED  --aplicado no proximo sync-->  APPLIED
    OPEN     --chave sumiu dos dois lados-->  STALE
    RESOLVED --chave sumiu antes de aplicar-->  STALE

Enquanto OPEN ou RESOLVED, a chave esta BLOQUEADA: nada daquela chave e aplicado
em nenhum dos lados (POL-5 — nada e aplicado sem decisao).
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime

from .canonical_event import Event, EventKey

OPEN = "OPEN"
RESOLVED = "RESOLVED"
APPLIED = "APPLIED"
STALE = "STALE"

TAKE_A = "a"
TAKE_B = "b"
MERGE = "merge"
RESUME = "resume"

OSCILLATION = "OSCILLATION"

# Classes em que "merge" NAO tem significado: os dois lados mudaram o MESMO
# campo, ou nao ha o que mesclar (achado UX-01).
MERGE_NOT_APPLICABLE = ("DELETE_VS_UPDATE", "UPDATE_VS_DELETE", "IDENTITY_COLLISION")


@dataclass(frozen=True, slots=True)
class ConflictRecord:
    id: str
    key: EventKey
    klass: str
    fields: tuple[str, ...]
    state: str = OPEN
    resolution: str | None = None
    detected_at: datetime | None = None
    resolved_at: datetime | None = None
    reason: str = ""
    value_a: Event | None = None
    value_b: Event | None = None
    value_ancestor_a: Event | None = None
    value_ancestor_b: Event | None = None
    policy_at_detection: str = ""

    def choices(self) -> tuple[str, ...]:
        if self.klass == OSCILLATION:
            # A suspensao por oscilacao nao guarda dois valores em disputa: o que
            # o operador decide e RETOMAR a propagacao daquela chave.
            return (RESUME,)
        if self.klass in MERGE_NOT_APPLICABLE:
            return (TAKE_A, TAKE_B)
        return (TAKE_A, TAKE_B, MERGE)


def is_blocking(conflict: ConflictRecord) -> bool:
    """OPEN e RESOLVED bloqueiam; APPLIED e STALE nao."""
    return conflict.state in (OPEN, RESOLVED)


def transition_resolve(conflict: ConflictRecord, choice: str, moment: datetime) -> ConflictRecord:
    if conflict.state != OPEN:
        raise ValueError(f"conflito {conflict.id} nao esta OPEN (esta {conflict.state})")
    if choice not in conflict.choices():
        raise ValueError(
            f"escolha '{choice}' invalida para a classe {conflict.klass}; "
            f"validas: {', '.join(conflict.choices())}"
        )
    return replace(conflict, state=RESOLVED, resolution=choice, resolved_at=moment)


def transition_applied(conflict: ConflictRecord) -> ConflictRecord:
    if conflict.state != RESOLVED:
        raise ValueError(f"conflito {conflict.id} nao esta RESOLVED")
    return replace(conflict, state=APPLIED)


def transition_stale(conflict: ConflictRecord, reason: str) -> ConflictRecord:
    """A chave desapareceu dos dois lados antes de a decisao aterrissar."""
    if conflict.state not in (OPEN, RESOLVED):
        raise ValueError(f"conflito {conflict.id} nao pode virar STALE de {conflict.state}")
    return replace(conflict, state=STALE, reason=reason)


def explain_states() -> list[tuple[str, str]]:
    """Achado UX-07: os quatro estados precisam sair explicados, ou viram jargao."""
    return [
        (OPEN, "aguardando sua decisao; a chave nao sincroniza ate voce decidir"),
        (RESOLVED, "voce decidiu; o proximo `sync` aplica"),
        (APPLIED, "decisao ja aplicada nos dois lados"),
        (STALE, "o evento sumiu dos dois lados antes de a decisao ser aplicada"),
    ]
