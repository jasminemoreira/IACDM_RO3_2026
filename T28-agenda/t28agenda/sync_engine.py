"""M-10 sync-engine — orquestracao do ciclo.

Fluxo: pull -> normalizar -> decidir presenca -> reconciliar -> planejar ->
gravar intencao no journal -> aplicar -> gravar ancestral -> fechar ciclo.

Tres regras de V(3)/V(4) vivem aqui:
  Regra 1  o ancestral guarda o que o provedor DEVOLVEU (write -> WriteResult),
           por lado. E o que fecha o eco mesmo quando o provedor renormaliza o
           recurso ao gravar (achado CTL-04).
  Regra 2  presenca decidida pela `observability_window` do provedor, SEM
           consultar: chave fora da janela e `Unobservable` por construcao
           (achado RES-05). `get()` fica so para a fronteira.
  Regra 3  a reconciliacao de journal aberto e AQUI, nao no repository.

C-3: `observability_window` (presenca) e `expansion_window` (sobreposicao) sao
coisas distintas e nunca se substituem.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, replace
from datetime import datetime

from .canonical_event import ABSENT, Event, EventKey, Present, Side, Unobservable
from .conflict_queue import (
    ConflictRecord, MERGE, OPEN, OSCILLATION, RESOLVED, TAKE_A, TAKE_B,
    transition_applied, transition_stale,
)
from .normalizer import fingerprint, to_canonical, to_ics
from .policies import Resolution, resolve
from .providers.base import MAX_PAGES_PER_ROUND, Delta, Provider, WriteOp
from .reconciler import Ancestor, AncestorSide, Propagate, plan
from .repository import OSCILLATION_CYCLES, PLANNED, Repository


@dataclass
class SyncReport:
    pulled: dict[str, int] = field(default_factory=dict)
    applied: list[str] = field(default_factory=list)
    skipped_noop: int = 0
    conflicts_opened: list[str] = field(default_factory=list)
    conflicts_applied: list[str] = field(default_factory=list)
    conflicts_stale: list[str] = field(default_factory=list)
    suspended_unobservable: list[str] = field(default_factory=list)
    suspended_oscillating: list[str] = field(default_factory=list)  # achado OBS-05
    blocked_keys: list[str] = field(default_factory=list)
    full_resync: list[str] = field(default_factory=list)
    recovered_cycle: int | None = None
    duration_s: float = 0.0
    dry_run: bool = False

    @property
    def writes(self) -> int:
        return len(self.applied)


class SyncEngine:
    def __init__(self, repo: Repository, provider_a: Provider, provider_b: Provider) -> None:
        self.repo = repo
        self.a = provider_a
        self.b = provider_b

    # --- pull ---------------------------------------------------------------
    def _pull_all(self, provider: Provider, token: str | None, report: SyncReport) -> tuple[Delta, str | None]:
        """Percorre as paginas de um round. Idempotente por (provider_id): a
        armadilha A-2 (item repetido) e absorvida por dicionario, e o teto de
        paginas e o circuit breaker de A-3."""
        items: dict[str, tuple[str, str]] = {}
        tombstones: list[str] = []
        state_token: str | None = None
        request = token
        pages = 0
        while True:
            delta = provider.pull(request)
            if delta.invalidated:
                report.full_resync.append(provider.name)
                self._forget_provider_state(provider)
                items, tombstones, request, pages = {}, [], None, 0
                delta = provider.pull(None)
            for pid, version, ics in delta.items:
                items[pid] = (version, ics)  # idempotente: absorve item repetido (A-2)
            tombstones.extend(delta.tombstones)
            if delta.next_state_token is not None:
                state_token = delta.next_state_token
                break
            request = delta.next_page_token
            pages += 1
            if pages > MAX_PAGES_PER_ROUND:  # circuit breaker de A-3
                raise RuntimeError(f"{provider.name}: round excedeu {MAX_PAGES_PER_ROUND} paginas")
        report.pulled[provider.name] = len(items)
        merged = Delta(items=[(pid, v, i) for pid, (v, i) in items.items()], tombstones=tombstones)
        return merged, state_token

    def _forget_provider_state(self, provider: Provider) -> None:
        """Token invalidado (A-1): descarta o token, PRESERVA o ancestral e o mapa
        de identidade — refazer full sync nao pode duplicar nem perder (UC-6)."""
        self.repo.save_token(provider.name, None)

    # --- presenca (Regra 2) -------------------------------------------------
    def _sides(self, delta: Delta, provider: Provider, ancestors: dict[EventKey, Ancestor],
               report: SyncReport) -> dict[EventKey, Side]:
        window = provider.observability_window()
        dialect = provider.dialect
        cal_tz = getattr(provider, "scenario", None)
        cal_tz = cal_tz.calendar_tz if cal_tz else "UTC"
        seen: dict[EventKey, Side] = {}

        # Uma unica transacao para todo o mapeamento de identidade: em
        # autocommit cada linha custaria um fsync, e o eco das proprias escritas
        # traz o lote inteiro de volta no ciclo seguinte.
        self.repo.begin()
        try:
            for pid, _version, ics in delta.items:
                event = to_canonical(ics, dialect, cal_tz)
                self.repo.map_identity(provider.name, pid, event.key)
                seen[event.key] = Present(event)
            self.repo.commit()
        except Exception:
            self.repo.rollback()
            raise

        for pid in delta.tombstones:
            key = self.repo.resolve_identity(provider.name, pid)
            if key is None:
                continue
            # R-A3: remocao vinda de provedor COM janela pode ser apenas saida de
            # escopo observavel. Verificar antes de tratar como delecao real.
            if not window.unbounded and provider.get(pid) is not None:
                seen[key] = Unobservable("saiu da janela observavel, ainda existe no provedor")
            else:
                seen[key] = ABSENT

        # Chaves conhecidas que nao vieram no delta: decidir por JANELA, sem
        # consultar o provedor (Regra 2 — custo zero, achado RES-05).
        for key, ancestor in ancestors.items():
            if key in seen:
                continue
            side_state = ancestor.side_a if provider is self.a else ancestor.side_b
            snapshot = side_state.snapshot
            if snapshot is None:
                continue
            if window.unbounded or window.contains(snapshot.start.as_utc()):
                seen[key] = Present(snapshot)  # inalterado desde a ultima sync
            else:
                seen[key] = Unobservable("ancestral fora da observability_window")
                report.suspended_unobservable.append(str(key))
        return seen

    # --- ciclo --------------------------------------------------------------
    def run_cycle(self, policy: str = "pol4", dry_run: bool = False,
                  moment: datetime | None = None, priority_side: str = "a") -> SyncReport:
        moment = moment or datetime.now().astimezone()
        started = moment.timestamp()
        report = SyncReport(dry_run=dry_run)
        self.repo.acquire_lock()
        try:
            report.recovered_cycle = self._recover_open_cycle()

            tokens = self.repo.load_tokens()
            ancestors = self.repo.load_all_ancestors()
            delta_a, token_a = self._pull_all(self.a, tokens.get(self.a.name), report)
            delta_b, token_b = self._pull_all(self.b, tokens.get(self.b.name), report)

            sides_a = self._sides(delta_a, self.a, ancestors, report)
            sides_b = self._sides(delta_b, self.b, ancestors, report)

            keys = sorted(set(sides_a) | set(sides_b) | set(ancestors), key=str)
            sides = {k: (sides_a.get(k, ABSENT), sides_b.get(k, ABSENT)) for k in keys}
            blocked = self.repo.blocked_keys()
            result = plan(sides, ancestors, blocked, policy)
            report.skipped_noop = result.noops
            report.blocked_keys = [str(k) for k in result.skipped_blocked]

            # Conflitos: politica decide, ou escala para a fila humana.
            pending: list[tuple[EventKey, Propagate]] = list(result.actions)
            new_conflicts: list[ConflictRecord] = []
            for conflict in result.conflicts:
                outcome = resolve(conflict, policy, ancestors.get(conflict.key), priority_side)
                if isinstance(outcome, Resolution):
                    direction = "a->b" if outcome.winner in ("a", "merge") else "b->a"
                    if outcome.winner == "merge":
                        pending.append((conflict.key, Propagate("a->b", outcome.event)))
                        pending.append((conflict.key, Propagate("b->a", outcome.event)))
                    else:
                        pending.append((conflict.key, Propagate(direction, outcome.event)))
                else:
                    record = ConflictRecord(
                        id=f"C-{uuid.uuid4().hex[:8]}",
                        key=conflict.key, klass=conflict.klass, fields=conflict.fields,
                        state=OPEN, detected_at=moment,
                        value_a=conflict.a, value_b=conflict.b,
                        value_ancestor_a=conflict.ancestor_a, value_ancestor_b=conflict.ancestor_b,
                        policy_at_detection=policy,
                    )
                    new_conflicts.append(record)
                    report.conflicts_opened.append(record.id)

            # Conflitos ja resolvidos pelo operador entram no plano deste ciclo.
            resolved_actions = self._actions_from_resolved(sides, report)
            pending.extend(resolved_actions)

            # Histerese (achados CTL-05/OBS-05): chave que alterna de direcao em
            # OSCILLATION_CYCLES ciclos seguidos e suspensa e vai para a fila.
            pending, oscillating = self._filter_oscillating(pending, moment, report)
            new_conflicts.extend(oscillating)

            if dry_run:
                report.applied = [f"{k} {p.direction}{' (delete)' if p.delete else ''}"
                                  for k, p in pending]
                return report

            self.repo.begin()
            cycle_id = self.repo.open_cycle(
                [(k, p.direction, "delete" if p.delete else "upsert") for k, p in pending],
                policy, dry_run, moment,
            )
            for record in new_conflicts:
                self.repo.save_conflict(record)
            self.repo.commit()

            entries = {e.id: e for e in self.repo.journal_of(cycle_id) if e.state == PLANNED}
            for entry, (key, action) in zip(sorted(entries), pending):
                self._apply(entry, key, action, ancestors, moment, report)

            self.repo.begin()
            self._close_resolved_conflicts(pending, report)
            self.repo.close_cycle(cycle_id, {self.a.name: token_a, self.b.name: token_b}, moment)
            self.repo.prune(moment)
            self.repo.commit()
        finally:
            self.repo.release_lock()
        report.duration_s = datetime.now().astimezone().timestamp() - started
        return report

    # --- aplicacao ----------------------------------------------------------
    def _apply(self, entry_id: int, key: EventKey, action: Propagate,
               ancestors: dict[EventKey, Ancestor], moment: datetime, report: SyncReport) -> None:
        target = self.b if action.direction == "a->b" else self.a
        source_is_a = action.direction == "a->b"
        provider_id = self.repo.provider_id_for(target.name, key)

        if action.delete:
            if provider_id is None:
                self.repo.begin()
                self.repo.cancel_action(entry_id, "sem mapeamento no destino")
                self.repo.commit()
                return
            result = target.write(WriteOp("delete", provider_id=provider_id))
            self.repo.begin()
            self.repo.mark_applied(entry_id, result.provider_id, result.version, None)
            self.repo.forget_identity(target.name, key)
            self.repo.delete_ancestor(key)
            self.repo.commit()
            report.applied.append(f"{key} delete {action.direction}")
            return

        ics = to_ics(action.event, target.dialect)
        op = WriteOp("update" if provider_id else "create", ics=ics, provider_id=provider_id)
        result = target.write(op)

        # Regra 1: o ancestral do lado ALVO recebe o que o provedor DEVOLVEU,
        # nao o que enviamos. E isto que impede o ping-pong quando o provedor
        # renormaliza o recurso ao gravar (CTL-04).
        stored = to_canonical(result.stored_ics, target.dialect) if result.stored_ics else action.event
        stored_fp = fingerprint(stored)

        ancestor = ancestors.get(key) or Ancestor(key=key)
        target_side = AncestorSide(stored, stored_fp, result.version, stored.sequence)
        source_event = action.event
        source_side = AncestorSide(
            source_event, fingerprint(source_event),
            (ancestor.side_a if source_is_a else ancestor.side_b).provider_version,
            source_event.sequence,
        )
        updated = (
            replace(ancestor, side_a=source_side, side_b=target_side)
            if source_is_a
            else replace(ancestor, side_a=target_side, side_b=source_side)
        )
        ancestors[key] = updated

        self.repo.begin()
        self.repo.mark_applied(entry_id, result.provider_id, result.version, stored_fp)
        self.repo.map_identity(target.name, result.provider_id, key)
        self.repo.save_ancestor(updated, moment)
        self.repo.commit()
        report.applied.append(f"{key} {action.direction}")

    # --- conflitos resolvidos pelo operador ---------------------------------
    def _actions_from_resolved(self, sides: dict[EventKey, tuple[Side, Side]],
                               report: SyncReport) -> list[tuple[EventKey, Propagate]]:
        """PRO-03: resolver grava a decisao; o proximo `sync` e que aplica."""
        out: list[tuple[EventKey, Propagate]] = []
        for conflict in self.repo.list_conflicts(RESOLVED):
            if conflict.klass == OSCILLATION:
                # Nada a aplicar: a decisao foi retomar a propagacao. O conflito
                # sai do estado bloqueante e o proximo ciclo reconcilia normal.
                self.repo.begin()
                self.repo.save_conflict(transition_applied(conflict))
                self.repo.commit()
                report.conflicts_applied.append(conflict.id)
                continue
            side_a, side_b = sides.get(conflict.key, (ABSENT, ABSENT))
            if not isinstance(side_a, Present) and not isinstance(side_b, Present):
                stale = transition_stale(conflict, "chave sumiu dos dois lados antes de aplicar")
                self.repo.begin()
                self.repo.save_conflict(stale)
                self.repo.commit()
                report.conflicts_stale.append(conflict.id)
                continue
            if conflict.resolution == TAKE_A and conflict.value_a is not None:
                out.append((conflict.key, Propagate("a->b", conflict.value_a)))
            elif conflict.resolution == TAKE_B and conflict.value_b is not None:
                out.append((conflict.key, Propagate("b->a", conflict.value_b)))
            elif conflict.resolution == MERGE and conflict.value_a and conflict.value_b:
                merged = self._merge(conflict)
                out.append((conflict.key, Propagate("a->b", merged)))
                out.append((conflict.key, Propagate("b->a", merged)))
        return out

    def _merge(self, conflict: ConflictRecord) -> Event:
        merged = conflict.value_a
        base = conflict.value_ancestor_b
        if base is not None and conflict.value_b is not None:
            for name, value in conflict.value_b.scalar_fields().items():
                if value != getattr(base, name):
                    merged = merged.with_fields(**{name: value})
        return merged

    def _close_resolved_conflicts(self, pending: list[tuple[EventKey, Propagate]],
                                  report: SyncReport) -> None:
        applied_keys = {key for key, _ in pending}
        for conflict in self.repo.list_conflicts(RESOLVED):
            if conflict.key in applied_keys:
                self.repo.save_conflict(transition_applied(conflict))
                report.conflicts_applied.append(conflict.id)

    # --- oscilacao ----------------------------------------------------------
    def _filter_oscillating(self, pending: list[tuple[EventKey, Propagate]], moment: datetime,
                            report: SyncReport) -> tuple[list[tuple[EventKey, Propagate]], list[ConflictRecord]]:
        kept: list[tuple[EventKey, Propagate]] = []
        conflicts: list[ConflictRecord] = []
        for key, action in pending:
            history = self.repo.direction_history(key, OSCILLATION_CYCLES)
            alternating = (
                len(history) >= OSCILLATION_CYCLES
                and all(history[i] != history[i + 1] for i in range(len(history) - 1))
                and history[0] != action.direction
            )
            if alternating:
                report.suspended_oscillating.append(str(key))
                conflicts.append(ConflictRecord(
                    id=f"C-{uuid.uuid4().hex[:8]}", key=key, klass=OSCILLATION,
                    fields=(), state=OPEN, detected_at=moment,
                    reason=f"direcao alternou em {OSCILLATION_CYCLES} ciclos seguidos",
                ))
            else:
                kept.append((key, action))
        return kept, conflicts

    # --- retomada de ciclo aberto (Regra 3, achados ARC-09/PRO-06) ----------
    def _recover_open_cycle(self) -> int | None:
        """Usa APENAS dados locais para as acoes ja marcadas; so a acao aberta
        exige verificacao, e como o ciclo e single-threaded ha no maximo uma."""
        open_cycles = self.repo.open_cycles()
        if not open_cycles:
            return None
        cycle_id = open_cycles[0]
        for entry in self.repo.journal_of(cycle_id):
            if entry.state == PLANNED:
                self.repo.begin()
                self.repo.cancel_action(entry.id, "cancelada na retomada: intencao nao confirmada")
                self.repo.commit()
        self.repo.begin()
        self.repo.close_cycle(cycle_id, {}, datetime.now().astimezone())
        self.repo.commit()
        return cycle_id
