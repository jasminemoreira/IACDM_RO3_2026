"""M-07 policies — catalogo de politicas de resolucao de conflito.

POL-1 normativa   : precedencia por SEQUENCE, desempate por DTSTAMP.
                    RFC 5546 §2.1.5 (REF-2), citado literalmente em
                    specs/references/standards.md.
POL-2 LWW         : ultima modificacao vence (usa LAST-MODIFIED, RFC 5545).
POL-3 prioridade  : um lado configurado sempre vence.
POL-4 merge campo : campos disjuntos mesclam; so colisao real escala.

Correcao de V(3): POL-1 NAO compara SEQUENCE absoluto entre provedores — eles
divergem por construcao, ja que cada provedor incrementa a seu criterio. Compara
o DELTA relativo ao ancestral daquele lado (`seq_lado - seq_ancestral_do_lado`).

Regra R-A1: campo estruturado (attendees, RRULE, EXDATE, RDATE) nunca mescla.
Achado ASS-12: sem ancestral nao ha delta, entao IDENTITY_COLLISION escala
direto para a fila em qualquer politica.

Modulo PURO. Sem GoF nomeado: uma politica e uma funcao com assinatura comum.
"""

from __future__ import annotations

from dataclasses import dataclass

from .canonical_event import Event
from .reconciler import (
    A,
    B,
    Ancestor,
    Conflict,
    IDENTITY_COLLISION,
    STRUCTURED_FIELD,
    changed_fields,
)

ESCALATE = "ESCALATE"
POLICIES = ("pol1", "pol2", "pol3", "pol4", "manual")


@dataclass(frozen=True, slots=True)
class Resolution:
    winner: str  # "a" | "b" | "merge"
    event: Event
    rationale: str


def resolve(
    conflict: Conflict,
    policy: str,
    ancestor: Ancestor | None = None,
    priority_side: str = A,
) -> Resolution | str:
    """Devolve a resolucao ou ESCALATE. ESCALATE significa: vai para a fila
    humana e NADA e aplicado naquela chave ate haver decisao (POL-5)."""
    if policy not in POLICIES:
        raise ValueError(f"politica desconhecida: {policy}")
    if policy == "manual":
        return ESCALATE
    if conflict.klass == IDENTITY_COLLISION:
        return ESCALATE  # sem ancestral nao ha delta: nada a comparar
    if conflict.klass in ("DELETE_VS_UPDATE", "UPDATE_VS_DELETE"):
        return ESCALATE  # perder um lado sem consentimento seria perda silenciosa
    if conflict.klass == STRUCTURED_FIELD:
        return ESCALATE  # R-A1

    if policy == "pol4":
        merged = _merge_by_field(conflict)
        if merged is not None:
            return merged
        return ESCALATE  # colisao real no mesmo campo escalar

    if policy == "pol3":
        winner = priority_side
        event = conflict.a if winner == A else conflict.b
        if event is None:
            return ESCALATE
        return Resolution(winner, event, f"POL-3: lado {winner} tem prioridade configurada")

    if policy == "pol2":
        return _by_last_modified(conflict)

    return _by_sequence_delta(conflict, ancestor)


def _merge_by_field(conflict: Conflict) -> Resolution | None:
    """POL-4: campos disjuntos mesclam sobre o ancestral; colisao real -> None."""
    a, b = conflict.a, conflict.b
    if a is None or b is None or conflict.ancestor_a is None or conflict.ancestor_b is None:
        return None
    diff_a = set(changed_fields(a, conflict.ancestor_a))
    diff_b = set(changed_fields(b, conflict.ancestor_b))
    colliding = {f for f in diff_a & diff_b if getattr(a, f) != getattr(b, f)}
    if colliding:
        return None
    merged = a
    for field_name in diff_b:
        merged = merged.with_fields(**{field_name: getattr(b, field_name)})
    changed = sorted(diff_a | diff_b)
    return Resolution("merge", merged, f"POL-4: campos disjuntos mesclados ({', '.join(changed)})")


def _by_last_modified(conflict: Conflict) -> Resolution | str:
    a, b = conflict.a, conflict.b
    if a is None or b is None:
        return ESCALATE
    la, lb = a.last_modified, b.last_modified
    if la is None or lb is None or la == lb:
        return ESCALATE  # sem o dado de entrada a politica nao decide (SCI-01)
    winner, event = (A, a) if la > lb else (B, b)
    return Resolution(winner, event, f"POL-2 (LWW): LAST-MODIFIED mais recente em {winner}")


def _by_sequence_delta(conflict: Conflict, ancestor: Ancestor | None) -> Resolution | str:
    """POL-1 com a correcao de V(3): delta relativo ao ancestral de cada lado."""
    a, b = conflict.a, conflict.b
    if a is None or b is None:
        return ESCALATE
    base_a = ancestor.side_a.sequence if ancestor else 0
    base_b = ancestor.side_b.sequence if ancestor else 0
    delta_a, delta_b = a.sequence - base_a, b.sequence - base_b
    if delta_a != delta_b:
        winner, event = (A, a) if delta_a > delta_b else (B, b)
        return Resolution(
            winner, event, f"POL-1 (RFC 5546 §2.1.5): maior delta de SEQUENCE em {winner}"
        )
    # Cascata deterministica: SEQUENCE -> DTSTAMP -> LAST-MODIFIED -> ESCALATE.
    # Nunca ha estado "indefinido" (achado ASS-05).
    if a.dtstamp and b.dtstamp and a.dtstamp != b.dtstamp:
        winner, event = (A, a) if a.dtstamp > b.dtstamp else (B, b)
        return Resolution(winner, event, f"POL-1: desempate por DTSTAMP em {winner}")
    if a.last_modified and b.last_modified and a.last_modified != b.last_modified:
        winner, event = (A, a) if a.last_modified > b.last_modified else (B, b)
        return Resolution(winner, event, f"POL-1: desempate por LAST-MODIFIED em {winner}")
    return ESCALATE
