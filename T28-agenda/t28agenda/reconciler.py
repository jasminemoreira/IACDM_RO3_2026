"""M-06 reconciler — matriz 3-vias PURA e planejamento do ciclo.

Fundamento formal: Balasubramaniam & Pierce, "What is a File Synchronizer?"
(MobiCom '98) — REF-7. Ha conflito quando AMBAS as replicas divergiram do
ancestral comum desde a ultima reconciliacao; se apenas uma divergiu, e
propagacao simples.

Nota de honestidade (achado SCI-03): REF-7 formaliza sincronizacao de sistema de
arquivos. A adaptacao para merge por campo de evento e EXTRAPOLACAO deste
projeto, nao derivacao da fonte.

Modulo PURO: nenhuma funcao aqui faz I/O, toca banco ou fala com provedor.
`Unobservable` NUNCA produz delecao — regra R-A3, correcao MEC-C.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .canonical_event import (
    Absent,
    Event,
    EventKey,
    Present,
    STRUCTURED_FIELDS,
    Side,
    Unobservable,
)

# Classes de conflito. Cada uma existe porque o desfecho correto e diferente:
# colapsa-las em "conflito" faria delete-vs-update ser tratado como update.
SAME_FIELD = "SAME_FIELD"
DELETE_VS_UPDATE = "DELETE_VS_UPDATE"
UPDATE_VS_DELETE = "UPDATE_VS_DELETE"
STRUCTURED_FIELD = "STRUCTURED_FIELD"
IDENTITY_COLLISION = "IDENTITY_COLLISION"

A = "a"
B = "b"


@dataclass(frozen=True, slots=True)
class NoOp:
    reason: str = ""


@dataclass(frozen=True, slots=True)
class Propagate:
    direction: str  # "a->b" ou "b->a"
    event: Event
    delete: bool = False


@dataclass(frozen=True, slots=True)
class Conflict:
    key: EventKey
    klass: str
    fields: tuple[str, ...]
    a: Event | None
    b: Event | None
    ancestor_a: Event | None
    ancestor_b: Event | None


Decision = NoOp | Propagate | Conflict


@dataclass(frozen=True, slots=True)
class AncestorSide:
    """C-1: o ancestral guarda o CONTEUDO por lado, nao so o hash.

    O snapshot e o que AQUELE lado devolveu por ultimo (V(3) Regra 1), o que
    torna o diff de cada lado uma comparacao contra o que ele proprio mostrou —
    e e o dado sem o qual POL-4 (merge por campo) e impossivel.
    """

    snapshot: Event | None = None
    fingerprint: str = ""
    provider_version: str = ""
    sequence: int = 0


@dataclass(frozen=True, slots=True)
class Ancestor:
    key: EventKey
    side_a: AncestorSide = field(default_factory=AncestorSide)
    side_b: AncestorSide = field(default_factory=AncestorSide)
    suspended: bool = False


@dataclass(slots=True)
class Plan:
    actions: list[tuple[EventKey, Propagate]] = field(default_factory=list)
    conflicts: list[Conflict] = field(default_factory=list)
    noops: int = 0
    skipped_blocked: list[EventKey] = field(default_factory=list)
    suspended_keys: list[EventKey] = field(default_factory=list)


def changed_fields(current: Event, base: Event | None) -> tuple[str, ...]:
    """Campos cujo valor divergiu do ancestral daquele lado."""
    if base is None:
        return ()
    out = [name for name, value in current.scalar_fields().items() if value != getattr(base, name)]
    out += [name for name in STRUCTURED_FIELDS if getattr(current, name) != getattr(base, name)]
    return tuple(sorted(out))


def reconcile(a: Side, b: Side, ancestor: Ancestor | None) -> Decision:
    """Matriz 3-vias. Ver a tabela completa em specs/technical/conflict-model.md."""
    key = _key_of(a, b, ancestor)

    # Unobservable nunca decide: nao ha informacao suficiente para agir sobre
    # aquele lado, e agir seria destrutivo (R-A3).
    if isinstance(a, Unobservable) and isinstance(b, Unobservable):
        return NoOp("ambos fora do escopo observavel")
    if isinstance(a, Unobservable):
        return _one_sided(b, ancestor.side_b if ancestor else None, "b->a", observable_peer=False)
    if isinstance(b, Unobservable):
        return _one_sided(a, ancestor.side_a if ancestor else None, "a->b", observable_peer=False)

    anc_a = ancestor.side_a if ancestor else None
    anc_b = ancestor.side_b if ancestor else None

    if isinstance(a, Absent) and isinstance(b, Absent):
        return NoOp("removido dos dois lados")

    # Criacao unilateral
    if isinstance(a, Present) and isinstance(b, Absent):
        if anc_b is None or anc_b.snapshot is None:
            if anc_a is not None and anc_a.snapshot is not None:
                # existia dos dois lados e sumiu de B: delecao real de B
                if changed_fields(a.event, anc_a.snapshot):
                    return Conflict(key, UPDATE_VS_DELETE, (), a.event, None, anc_a.snapshot, None)
                return Propagate("b->a", a.event, delete=True)
            return Propagate("a->b", a.event)
        if changed_fields(a.event, anc_a.snapshot if anc_a else None):
            return Conflict(key, UPDATE_VS_DELETE, (), a.event, None, _snap(anc_a), _snap(anc_b))
        return Propagate("b->a", a.event, delete=True)

    if isinstance(b, Present) and isinstance(a, Absent):
        if anc_a is None or anc_a.snapshot is None:
            if anc_b is not None and anc_b.snapshot is not None:
                if changed_fields(b.event, anc_b.snapshot):
                    return Conflict(key, DELETE_VS_UPDATE, (), None, b.event, None, anc_b.snapshot)
                return Propagate("a->b", b.event, delete=True)
            return Propagate("b->a", b.event)
        if changed_fields(b.event, anc_b.snapshot if anc_b else None):
            return Conflict(key, DELETE_VS_UPDATE, (), None, b.event, _snap(anc_a), _snap(anc_b))
        return Propagate("a->b", b.event, delete=True)

    assert isinstance(a, Present) and isinstance(b, Present)
    if a.partial or b.partial:
        # PER-07: item resumido de paginacao nunca reconcilia — exige leitura
        # completa antes de decidir.
        return NoOp("lado parcial: exige leitura completa antes de reconciliar")

    # Criacao concorrente com o mesmo UID e sem ancestral: nao ha base para
    # calcular delta, entao escala direto (achado ASS-12).
    if anc_a is None or anc_a.snapshot is None or anc_b is None or anc_b.snapshot is None:
        if _same_content(a.event, b.event):
            return NoOp("criacao concorrente convergente")
        return Conflict(key, IDENTITY_COLLISION, (), a.event, b.event, _snap(anc_a), _snap(anc_b))

    diff_a = changed_fields(a.event, anc_a.snapshot)
    diff_b = changed_fields(b.event, anc_b.snapshot)

    if not diff_a and not diff_b:
        return NoOp("nada mudou dos dois lados")
    if diff_a and not diff_b:
        return Propagate("a->b", a.event)
    if diff_b and not diff_a:
        return Propagate("b->a", b.event)

    colliding = tuple(sorted(set(diff_a) & set(diff_b)))
    if not colliding:
        # Campos disjuntos: POL-4 mescla no resolvedor, sem conflito real.
        return Conflict(key, SAME_FIELD, (), a.event, b.event, anc_a.snapshot, anc_b.snapshot)
    if set(colliding) & set(STRUCTURED_FIELDS):
        # R-A1: campo estruturado nunca mescla.
        return Conflict(key, STRUCTURED_FIELD, colliding, a.event, b.event, anc_a.snapshot, anc_b.snapshot)
    if all(getattr(a.event, f) == getattr(b.event, f) for f in colliding):
        return NoOp("convergencia acidental: os dois lados mudaram para o mesmo valor")
    return Conflict(key, SAME_FIELD, colliding, a.event, b.event, anc_a.snapshot, anc_b.snapshot)


def plan(
    sides: dict[EventKey, tuple[Side, Side]],
    ancestors: dict[EventKey, Ancestor],
    blocked_keys: set[EventKey],
    policy: str,
) -> Plan:
    """Planejamento PURO do ciclo inteiro (argumentos explicitos — achado ARC-06)."""
    result = Plan()
    for key in sorted(sides, key=str):
        side_a, side_b = sides[key]
        ancestor = ancestors.get(key)
        if key in blocked_keys:
            result.skipped_blocked.append(key)
            continue
        decision = reconcile(side_a, side_b, ancestor)
        if isinstance(decision, NoOp):
            result.noops += 1
        elif isinstance(decision, Propagate):
            result.actions.append((key, decision))
        else:
            result.conflicts.append(decision)
    return result


def _snap(side: AncestorSide | None) -> Event | None:
    return side.snapshot if side else None


def _same_content(x: Event, y: Event) -> bool:
    return x.scalar_fields() == y.scalar_fields() and x.structured_fields() == y.structured_fields()


def _one_sided(
    observable: Side, ancestor_side: AncestorSide | None, direction: str, observable_peer: bool
) -> Decision:
    """Um lado nao e observavel: so propagamos o que o lado visivel criou ou
    alterou, e NUNCA interpretamos a invisibilidade como delecao."""
    if isinstance(observable, Absent):
        return NoOp("lado visivel ausente e o outro nao observavel: nada a decidir com seguranca")
    assert isinstance(observable, Present)
    base = ancestor_side.snapshot if ancestor_side else None
    if base is None:
        return Propagate(direction, observable.event)
    if changed_fields(observable.event, base):
        return Propagate(direction, observable.event)
    return NoOp("sem mudanca no lado observavel")


def _key_of(a: Side, b: Side, ancestor: Ancestor | None) -> EventKey:
    if isinstance(a, Present):
        return a.event.key
    if isinstance(b, Present):
        return b.event.key
    if ancestor is not None:
        return ancestor.key
    raise ValueError("nao ha chave: os dois lados ausentes e sem ancestral")
