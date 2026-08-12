"""Base de armazenamento em arquivo compartilhada pelos dois simuladores.

Os dois provedores sao HETEROGENEOS na superficie (tokens, tombstones, janela),
mas o mecanismo de armazenamento e o mesmo: um `.ics` real por recurso mais um
`state.json` com contador monotonico de sequencia. A heterogeneidade que importa
esta nas subclasses, nao aqui.

Nenhum destes provedores devolve item PARCIAL — declarado no cenario (achado
PER-07): `Present(partial=True)` existe para o adaptador real futuro.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ..normalizer import to_canonical, to_ics
from .base import (
    MAX_PAGES_PER_ROUND,
    Delta,
    ObservabilityWindow,
    Scenario,
    WriteOp,
    WriteResult,
    decode_token,
    encode_token,
    sanitize_id,
)


@dataclass
class _Resource:
    provider_id: str
    seq: int
    version: str
    deleted: bool = False


class FileBackedProvider:
    name = "base"
    dialect = "alpha"
    keeps_cancelled_resource = True  # alpha guarda o recurso cancelado; beta apaga

    def __init__(self, root: Path, scenario: Scenario | None = None) -> None:
        self.root = Path(root)
        self.events_dir = self.root / "events"
        self.events_dir.mkdir(parents=True, exist_ok=True)
        self.scenario = scenario or self._load_scenario()
        self._state = self._load_state()

    # --- estado interno do simulador ---------------------------------------
    def _load_scenario(self) -> Scenario:
        path = self.root / "scenario.json"
        if path.exists():
            return Scenario.from_dict(json.loads(path.read_text()))
        return Scenario()

    def _load_state(self) -> dict:
        path = self.root / "state.json"
        if path.exists():
            return json.loads(path.read_text())
        return {"seq": 0, "pulls": 0, "resources": {}}

    def _save_state(self) -> None:
        (self.root / "state.json").write_text(json.dumps(self._state, indent=1, sort_keys=True))

    def _path(self, provider_id: str) -> Path:
        return self.events_dir / f"{sanitize_id(provider_id)}.ics"

    def _resources(self) -> dict[str, _Resource]:
        return {
            pid: _Resource(pid, data["seq"], data["version"], data.get("deleted", False))
            for pid, data in self._state["resources"].items()
        }

    # --- porta Provider -----------------------------------------------------
    def observability_window(self) -> ObservabilityWindow:
        return ObservabilityWindow()

    def get(self, provider_id: str) -> str | None:
        """Le o recurso INDEPENDENTE da janela — e exatamente para isso que existe:
        distinguir saida-de-janela de delecao real (regra R-A3)."""
        entry = self._state["resources"].get(provider_id)
        if entry is None or entry.get("deleted"):
            return None
        path = self._path(provider_id)
        return path.read_text() if path.exists() else None

    def _observable(self, ics_text: str) -> bool:
        window = self.observability_window()
        if window.unbounded:
            return True
        event = to_canonical(ics_text, self.dialect, self.scenario.calendar_tz)
        return window.contains(event.start.as_utc())

    def pull(self, state_token: str | None) -> Delta:
        if state_token is None:
            self._state["pulls"] = self._state.get("pulls", 0) + 1
            self._save_state()
            since, page = 0, 0
        else:
            payload = decode_token(state_token)
            if payload.get("kind") == "page":
                since, page = payload["since"], payload["page"]
            else:
                self._state["pulls"] = self._state.get("pulls", 0) + 1
                self._save_state()
                invalidate_at = self.scenario.invalidate_token_at_cycle
                if invalidate_at is not None and self._state["pulls"] >= invalidate_at:
                    # REF-5: HTTP 410 / RFC 6578: valid-sync-token. Caminho de
                    # ROTINA, nao excecao (armadilha A-1).
                    return Delta(invalidated=True)
                since, page = payload["since"], 0

        if page >= MAX_PAGES_PER_ROUND:
            raise RuntimeError(f"round excedeu {MAX_PAGES_PER_ROUND} paginas (circuit breaker)")

        changed = sorted(
            (r for r in self._resources().values() if r.seq > since),
            key=lambda r: (r.seq, r.provider_id),
        )
        size = self.scenario.page_size
        window = changed[page * size : (page + 1) * size]

        delta = Delta()
        for resource in window:
            if resource.deleted:
                delta.tombstones.append(resource.provider_id)
                continue
            path = self._path(resource.provider_id)
            if not path.exists():
                continue
            text = path.read_text()
            if not self._observable(text):
                continue  # fora da observability_window: o provedor nao o ve
            delta.items.append((resource.provider_id, resource.version, text))

        if self.scenario.duplicate_item_at_page == page and delta.items:
            delta.items.append(delta.items[0])  # armadilha A-2: item repetido

        if (page + 1) * size < len(changed):
            delta.next_page_token = encode_token({"kind": "page", "since": since, "page": page + 1})
        else:
            top = max((r.seq for r in self._resources().values()), default=since)
            delta.next_state_token = encode_token({"kind": "state", "since": max(since, top)})
        return delta

    def write(self, op: WriteOp) -> WriteResult:
        self._state["seq"] += 1
        seq = self._state["seq"]

        if op.kind == "delete":
            provider_id = op.provider_id or ""
            entry = self._state["resources"].get(provider_id)
            if entry is None:
                raise KeyError(f"recurso inexistente: {provider_id}")
            entry.update({"seq": seq, "version": f"v{seq}", "deleted": True})
            if self.keeps_cancelled_resource:
                path = self._path(provider_id)
                if path.exists():
                    event = to_canonical(path.read_text(), self.dialect, self.scenario.calendar_tz)
                    path.write_text(to_ics(event.with_fields(status="CANCELLED"), self.dialect))
            else:
                self._path(provider_id).unlink(missing_ok=True)
            self._save_state()
            return WriteResult(provider_id, f"v{seq}", None)

        if op.ics is None:
            raise ValueError("create/update exige ics")
        # O provedor RENORMALIZA o recurso ao gravar (o dialeto beta trunca a
        # descricao). E a origem do achado CTL-04, e a razao de o ancestral
        # guardar o que o provedor DEVOLVEU (V(3) Regra 1).
        event = to_canonical(op.ics, self.dialect, self.scenario.calendar_tz)
        stored = to_ics(event, self.dialect)
        provider_id = op.provider_id or self._new_id(event.uid, seq)
        self._path(provider_id).write_text(stored)
        self._state["resources"][provider_id] = {
            "seq": seq,
            "version": f"v{seq}",
            "deleted": False,
        }
        self._save_state()
        return WriteResult(provider_id, f"v{seq}", stored)

    def _new_id(self, uid: str, seq: int) -> str:
        return sanitize_id(f"{self.name}-{uid}-{seq}")

    # --- apoio a fixtures e testes -----------------------------------------
    def seed(self, ics_text: str, provider_id: str | None = None) -> str:
        """Injeta um recurso como se ja existisse no provedor (sem passar pelo
        sincronizador). Usado pelas fixtures e pelo teste de mudanca externa."""
        result = self.write(WriteOp("create", ics=ics_text, provider_id=provider_id))
        return result.provider_id

    def all_resources(self) -> dict[str, str]:
        return {
            pid: self._path(pid).read_text()
            for pid, data in self._state["resources"].items()
            if not data.get("deleted") and self._path(pid).exists()
        }

    def write_count(self) -> int:
        return self._state["seq"]
