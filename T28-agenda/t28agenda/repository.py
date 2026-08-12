"""M-11 repository — armazenamento de cinco colecoes, com commit atomico.

V(3) Regra 3: armazenamento BURRO. Ele guarda o que recebe e nao decide nada —
a reconciliacao de journal aberto e do sync-engine, o estado do conflito e do
conflict-queue.

Colecoes: ancestral (snapshot por lado), mapa de identidade, tokens de estado,
fila de conflitos, journal de ciclo.

Ordem de chamada OBRIGATORIA (achado LIN-05):
    open_cycle(plan) -> mark_applied(action)* / cancel_action(action)* -> close_cycle(tokens)
`mark_applied` e IDEMPOTENTE (a retomada pode remarcar — achado IMP-07).
`close_cycle` RECUSA fechar com acao planejada nao marcada (achado LIN-08).

MEC-B: o journal grava a INTENCAO antes de qualquer escrita no provedor. E o que
torna recuperavel a janela entre a escrita externa e o commit local (PR-6), que
por definicao nao pode ser atomica.
"""

from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from .canonical_event import Event, EventKey
from .conflict_queue import ConflictRecord, OPEN, RESOLVED
from .normalizer import to_canonical, to_ics
from .reconciler import Ancestor, AncestorSide

SCHEMA_VERSION = 1
FINGERPRINT_ALGO_VERSION = 1

# Retencao do journal. A dependencia com o criterio de oscilacao e DECLARADA e
# verificada em tempo de execucao (achado IMP-08): mudar um sem o outro quebraria
# o detector em silencio.
JOURNAL_RETENTION_CYCLES = 20
JOURNAL_RETENTION_DAYS = 30
OSCILLATION_CYCLES = 3
assert JOURNAL_RETENTION_CYCLES >= 3 * OSCILLATION_CYCLES, (
    "retencao do journal precisa ser >= 3x o criterio de oscilacao"
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS ancestor (
  uid TEXT NOT NULL, recurrence_id TEXT NOT NULL DEFAULT '',
  snapshot_a TEXT, fingerprint_a TEXT, version_a TEXT, sequence_a INTEGER DEFAULT 0,
  snapshot_b TEXT, fingerprint_b TEXT, version_b TEXT, sequence_b INTEGER DEFAULT 0,
  suspended INTEGER NOT NULL DEFAULT 0, synced_at TEXT,
  PRIMARY KEY (uid, recurrence_id));
CREATE TABLE IF NOT EXISTS identity_map (
  provider TEXT NOT NULL, provider_id TEXT NOT NULL,
  uid TEXT NOT NULL, recurrence_id TEXT NOT NULL DEFAULT '',
  PRIMARY KEY (provider, provider_id));
CREATE UNIQUE INDEX IF NOT EXISTS ix_identity_key
  ON identity_map(provider, uid, recurrence_id);
CREATE TABLE IF NOT EXISTS sync_state (provider TEXT PRIMARY KEY, state_token TEXT);
CREATE TABLE IF NOT EXISTS conflict (
  id TEXT PRIMARY KEY, uid TEXT NOT NULL, recurrence_id TEXT NOT NULL DEFAULT '',
  klass TEXT NOT NULL, fields TEXT NOT NULL, state TEXT NOT NULL,
  resolution TEXT, reason TEXT DEFAULT '', policy TEXT DEFAULT '',
  value_a TEXT, value_b TEXT, value_anc_a TEXT, value_anc_b TEXT,
  detected_at TEXT, resolved_at TEXT);
CREATE INDEX IF NOT EXISTS ix_conflict_state ON conflict(state);
CREATE INDEX IF NOT EXISTS ix_conflict_key ON conflict(uid, recurrence_id);
CREATE TABLE IF NOT EXISTS cycle (
  id INTEGER PRIMARY KEY AUTOINCREMENT, opened_at TEXT NOT NULL, closed_at TEXT,
  schema_version INTEGER NOT NULL, policy TEXT NOT NULL,
  fingerprint_algo INTEGER NOT NULL, dry_run INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS journal (
  id INTEGER PRIMARY KEY AUTOINCREMENT, cycle_id INTEGER NOT NULL,
  uid TEXT NOT NULL, recurrence_id TEXT NOT NULL DEFAULT '',
  direction TEXT NOT NULL, kind TEXT NOT NULL, state TEXT NOT NULL,
  provider_id TEXT, version TEXT, fingerprint TEXT,
  discarded_value TEXT, note TEXT DEFAULT '');
CREATE INDEX IF NOT EXISTS ix_journal_cycle ON journal(cycle_id);
CREATE INDEX IF NOT EXISTS ix_journal_key ON journal(uid, recurrence_id);
"""

PLANNED = "PLANNED"
DONE = "DONE"
CANCELLED = "CANCELLED"


@dataclass(frozen=True, slots=True)
class JournalEntry:
    id: int
    cycle_id: int
    key: EventKey
    direction: str
    kind: str
    state: str
    provider_id: str | None = None
    version: str | None = None
    fingerprint: str | None = None
    note: str = ""


class CycleStateError(RuntimeError):
    """Chamada fora da ordem obrigatoria do contrato."""


class Repository:
    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        new = not self.path.exists()
        self.conn = sqlite3.connect(self.path, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        # WAL + synchronous=NORMAL: durabilidade contra MORTE DE PROCESSO, que e
        # exatamente a garantia de que MEC-B precisa (o journal tem de sobreviver
        # ao processo morrer entre a escrita no provedor e o commit local).
        # Durabilidade contra queda de energia nunca esteve em escopo. Com
        # synchronous=FULL cada commit custava ~37 ms de fsync, e um ciclo de
        # 1.000 eventos violava VAL-2 por 8x.
        self.conn.execute("PRAGMA journal_mode = WAL")
        self.conn.execute("PRAGMA synchronous = NORMAL")
        self.conn.executescript(SCHEMA)
        if new:
            # SEC-02: conteudo de calendario e dado sensivel; o arquivo nao deve
            # ser legivel por outros usuarios da maquina.
            os.chmod(self.path, 0o600)
        self._set_meta_default("schema_version", str(SCHEMA_VERSION))
        self._set_meta_default("fingerprint_algo", str(FINGERPRINT_ALGO_VERSION))
        self._check_schema_version()
        self._open_cycle_id: int | None = None

    # --- meta e esquema -----------------------------------------------------
    def _set_meta_default(self, key: str, value: str) -> None:
        self.conn.execute("INSERT OR IGNORE INTO meta(k, v) VALUES (?, ?)", (key, value))

    def meta(self, key: str) -> str | None:
        row = self.conn.execute("SELECT v FROM meta WHERE k = ?", (key,)).fetchone()
        return row["v"] if row else None

    def _check_schema_version(self) -> None:
        found = int(self.meta("schema_version") or 0)
        if found != SCHEMA_VERSION:  # MEC-03: banco de outra versao e detectado
            raise RuntimeError(
                f"banco na versao de esquema {found}, esperada {SCHEMA_VERSION}. "
                "Este ciclo nao implementa migracao entre versoes de esquema "
                "(escopo negativo declarado): recrie o workspace ou migre o .db manualmente."
            )

    # --- lock de execucao ---------------------------------------------------
    def acquire_lock(self, stale_after_seconds: int = 900) -> None:
        """RES-04. RES-06: lock orfao de processo morto expira por tempo, senao o
        proximo ciclo recusaria rodar para sempre."""
        row = self.conn.execute("SELECT v FROM meta WHERE k = 'lock'").fetchone()
        if row and row["v"]:
            owner, taken_at = json.loads(row["v"])
            age = (datetime.now().timestamp() - taken_at)
            if age < stale_after_seconds and owner != os.getpid():
                raise RuntimeError(
                    f"outro ciclo em execucao (pid {owner}, ha {int(age)}s). "
                    "Se o processo morreu, o lock expira sozinho."
                )
        payload = json.dumps([os.getpid(), datetime.now().timestamp()])
        self.conn.execute(
            "INSERT INTO meta(k, v) VALUES ('lock', ?) ON CONFLICT(k) DO UPDATE SET v = ?",
            (payload, payload),
        )

    def release_lock(self) -> None:
        self.conn.execute("DELETE FROM meta WHERE k = 'lock'")

    # --- ancestral ----------------------------------------------------------
    def load_ancestor(self, key: EventKey) -> Ancestor | None:
        uid, rid = key.as_row()
        row = self.conn.execute(
            "SELECT * FROM ancestor WHERE uid = ? AND recurrence_id = ?", (uid, rid)
        ).fetchone()
        return self._row_to_ancestor(row) if row else None

    def load_all_ancestors(self) -> dict[EventKey, Ancestor]:
        out: dict[EventKey, Ancestor] = {}
        for row in self.conn.execute("SELECT * FROM ancestor"):
            ancestor = self._row_to_ancestor(row)
            out[ancestor.key] = ancestor
        return out

    def _row_to_ancestor(self, row: sqlite3.Row) -> Ancestor:
        key = EventKey.from_row(row["uid"], row["recurrence_id"])
        return Ancestor(
            key=key,
            side_a=AncestorSide(
                snapshot=to_canonical(row["snapshot_a"], "alpha") if row["snapshot_a"] else None,
                fingerprint=row["fingerprint_a"] or "",
                provider_version=row["version_a"] or "",
                sequence=row["sequence_a"] or 0,
            ),
            side_b=AncestorSide(
                snapshot=to_canonical(row["snapshot_b"], "beta") if row["snapshot_b"] else None,
                fingerprint=row["fingerprint_b"] or "",
                provider_version=row["version_b"] or "",
                sequence=row["sequence_b"] or 0,
            ),
            suspended=bool(row["suspended"]),
        )

    def save_ancestor(self, ancestor: Ancestor, moment: datetime) -> None:
        uid, rid = ancestor.key.as_row()
        self.conn.execute(
            """INSERT INTO ancestor
               (uid, recurrence_id, snapshot_a, fingerprint_a, version_a, sequence_a,
                snapshot_b, fingerprint_b, version_b, sequence_b, suspended, synced_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(uid, recurrence_id) DO UPDATE SET
                 snapshot_a=excluded.snapshot_a, fingerprint_a=excluded.fingerprint_a,
                 version_a=excluded.version_a, sequence_a=excluded.sequence_a,
                 snapshot_b=excluded.snapshot_b, fingerprint_b=excluded.fingerprint_b,
                 version_b=excluded.version_b, sequence_b=excluded.sequence_b,
                 suspended=excluded.suspended, synced_at=excluded.synced_at""",
            (
                uid, rid,
                to_ics(ancestor.side_a.snapshot, "alpha") if ancestor.side_a.snapshot else None,
                ancestor.side_a.fingerprint, ancestor.side_a.provider_version,
                ancestor.side_a.sequence,
                to_ics(ancestor.side_b.snapshot, "beta") if ancestor.side_b.snapshot else None,
                ancestor.side_b.fingerprint, ancestor.side_b.provider_version,
                ancestor.side_b.sequence,
                int(ancestor.suspended), moment.isoformat(),
            ),
        )

    def delete_ancestor(self, key: EventKey) -> None:
        uid, rid = key.as_row()
        self.conn.execute("DELETE FROM ancestor WHERE uid = ? AND recurrence_id = ?", (uid, rid))

    # --- mapa de identidade -------------------------------------------------
    def map_identity(self, provider: str, provider_id: str, key: EventKey) -> None:
        uid, rid = key.as_row()
        self.conn.execute(
            """INSERT INTO identity_map(provider, provider_id, uid, recurrence_id)
               VALUES (?,?,?,?)
               ON CONFLICT(provider, provider_id) DO UPDATE SET
                 uid=excluded.uid, recurrence_id=excluded.recurrence_id""",
            (provider, provider_id, uid, rid),
        )

    def resolve_identity(self, provider: str, provider_id: str) -> EventKey | None:
        row = self.conn.execute(
            "SELECT uid, recurrence_id FROM identity_map WHERE provider = ? AND provider_id = ?",
            (provider, provider_id),
        ).fetchone()
        return EventKey.from_row(row["uid"], row["recurrence_id"]) if row else None

    def provider_id_for(self, provider: str, key: EventKey) -> str | None:
        uid, rid = key.as_row()
        row = self.conn.execute(
            """SELECT provider_id FROM identity_map
               WHERE provider = ? AND uid = ? AND recurrence_id = ?""",
            (provider, uid, rid),
        ).fetchone()
        return row["provider_id"] if row else None

    def forget_identity(self, provider: str, key: EventKey) -> None:
        uid, rid = key.as_row()
        self.conn.execute(
            "DELETE FROM identity_map WHERE provider = ? AND uid = ? AND recurrence_id = ?",
            (provider, uid, rid),
        )

    # --- tokens -------------------------------------------------------------
    def load_tokens(self) -> dict[str, str | None]:
        return {r["provider"]: r["state_token"] for r in self.conn.execute("SELECT * FROM sync_state")}

    def save_token(self, provider: str, token: str | None) -> None:
        self.conn.execute(
            """INSERT INTO sync_state(provider, state_token) VALUES (?,?)
               ON CONFLICT(provider) DO UPDATE SET state_token = excluded.state_token""",
            (provider, token),
        )

    # --- fila de conflitos --------------------------------------------------
    def save_conflict(self, conflict: ConflictRecord) -> None:
        """Grava VERBATIM o que o conflict-queue produziu. Este modulo nunca
        altera estado de conflito (achado ARC-08)."""
        uid, rid = conflict.key.as_row()
        self.conn.execute(
            """INSERT INTO conflict(id, uid, recurrence_id, klass, fields, state, resolution,
                                    reason, policy, value_a, value_b, value_anc_a, value_anc_b,
                                    detected_at, resolved_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(id) DO UPDATE SET
                 state=excluded.state, resolution=excluded.resolution,
                 reason=excluded.reason, resolved_at=excluded.resolved_at""",
            (
                conflict.id, uid, rid, conflict.klass, json.dumps(list(conflict.fields)),
                conflict.state, conflict.resolution, conflict.reason,
                conflict.policy_at_detection,
                to_ics(conflict.value_a, "alpha") if conflict.value_a else None,
                to_ics(conflict.value_b, "beta") if conflict.value_b else None,
                to_ics(conflict.value_ancestor_a, "alpha") if conflict.value_ancestor_a else None,
                to_ics(conflict.value_ancestor_b, "beta") if conflict.value_ancestor_b else None,
                conflict.detected_at.isoformat() if conflict.detected_at else None,
                conflict.resolved_at.isoformat() if conflict.resolved_at else None,
            ),
        )

    def list_conflicts(self, state: str | None = None) -> list[ConflictRecord]:
        if state:
            rows = self.conn.execute("SELECT * FROM conflict WHERE state = ? ORDER BY id", (state,))
        else:
            rows = self.conn.execute("SELECT * FROM conflict ORDER BY id")
        return [self._row_to_conflict(r) for r in rows]

    def get_conflict(self, conflict_id: str) -> ConflictRecord | None:
        row = self.conn.execute("SELECT * FROM conflict WHERE id = ?", (conflict_id,)).fetchone()
        return self._row_to_conflict(row) if row else None

    def blocked_keys(self) -> set[EventKey]:
        rows = self.conn.execute(
            "SELECT uid, recurrence_id FROM conflict WHERE state IN (?, ?)", (OPEN, RESOLVED)
        )
        return {EventKey.from_row(r["uid"], r["recurrence_id"]) for r in rows}

    def _row_to_conflict(self, row: sqlite3.Row) -> ConflictRecord:
        def load(text: str | None, dialect: str) -> Event | None:
            return to_canonical(text, dialect) if text else None

        return ConflictRecord(
            id=row["id"],
            key=EventKey.from_row(row["uid"], row["recurrence_id"]),
            klass=row["klass"],
            fields=tuple(json.loads(row["fields"])),
            state=row["state"],
            resolution=row["resolution"],
            detected_at=datetime.fromisoformat(row["detected_at"]) if row["detected_at"] else None,
            resolved_at=datetime.fromisoformat(row["resolved_at"]) if row["resolved_at"] else None,
            reason=row["reason"] or "",
            value_a=load(row["value_a"], "alpha"),
            value_b=load(row["value_b"], "beta"),
            value_ancestor_a=load(row["value_anc_a"], "alpha"),
            value_ancestor_b=load(row["value_anc_b"], "beta"),
            policy_at_detection=row["policy"] or "",
        )

    # --- journal de ciclo (MEC-B) -------------------------------------------
    def open_cycle(self, planned: list[tuple[EventKey, str, str]], policy: str, dry_run: bool,
                   moment: datetime) -> int:
        """Grava a INTENCAO antes de qualquer escrita no provedor."""
        if self._open_cycle_id is not None:
            raise CycleStateError("ja existe um ciclo aberto nesta sessao")
        cursor = self.conn.execute(
            """INSERT INTO cycle(opened_at, schema_version, policy, fingerprint_algo, dry_run)
               VALUES (?,?,?,?,?)""",
            (moment.isoformat(), SCHEMA_VERSION, policy, FINGERPRINT_ALGO_VERSION, int(dry_run)),
        )
        cycle_id = int(cursor.lastrowid)
        for key, direction, kind in planned:
            uid, rid = key.as_row()
            self.conn.execute(
                """INSERT INTO journal(cycle_id, uid, recurrence_id, direction, kind, state)
                   VALUES (?,?,?,?,?,?)""",
                (cycle_id, uid, rid, direction, kind, PLANNED),
            )
        self._open_cycle_id = cycle_id
        return cycle_id

    def open_cycles(self) -> list[int]:
        rows = self.conn.execute("SELECT id FROM cycle WHERE closed_at IS NULL ORDER BY id")
        return [r["id"] for r in rows]

    def journal_of(self, cycle_id: int) -> list[JournalEntry]:
        rows = self.conn.execute(
            "SELECT * FROM journal WHERE cycle_id = ? ORDER BY id", (cycle_id,)
        )
        return [
            JournalEntry(
                id=r["id"], cycle_id=r["cycle_id"],
                key=EventKey.from_row(r["uid"], r["recurrence_id"]),
                direction=r["direction"], kind=r["kind"], state=r["state"],
                provider_id=r["provider_id"], version=r["version"],
                fingerprint=r["fingerprint"], note=r["note"] or "",
            )
            for r in rows
        ]

    def discarded_value(self, entry_id: int) -> str | None:
        row = self.conn.execute(
            "SELECT discarded_value FROM journal WHERE id = ?", (entry_id,)
        ).fetchone()
        return row["discarded_value"] if row else None

    def mark_applied(self, entry_id: int, provider_id: str | None, version: str | None,
                     fingerprint: str | None, discarded: str | None = None) -> None:
        """IDEMPOTENTE (achado IMP-07): a retomada pode remarcar a mesma acao."""
        self.conn.execute(
            """UPDATE journal SET state = ?, provider_id = ?, version = ?, fingerprint = ?,
                                  discarded_value = COALESCE(?, discarded_value)
               WHERE id = ?""",
            (DONE, provider_id, version, fingerprint, discarded, entry_id),
        )

    def cancel_action(self, entry_id: int, note: str) -> None:
        self.conn.execute(
            "UPDATE journal SET state = ?, note = ? WHERE id = ?", (CANCELLED, note, entry_id)
        )

    def close_cycle(self, cycle_id: int, tokens: dict[str, str | None], moment: datetime) -> None:
        """LIN-08: recusa fechar com acao planejada nao marcada. O estado nunca
        fica ambiguo — cancelar e explicito."""
        pending = self.conn.execute(
            "SELECT COUNT(*) AS n FROM journal WHERE cycle_id = ? AND state = ?",
            (cycle_id, PLANNED),
        ).fetchone()["n"]
        if pending:
            raise CycleStateError(
                f"ciclo {cycle_id} tem {pending} acao(oes) planejada(s) nao marcada(s); "
                "use mark_applied ou cancel_action antes de fechar"
            )
        for provider, token in tokens.items():
            self.save_token(provider, token)
        self.conn.execute("UPDATE cycle SET closed_at = ? WHERE id = ?", (moment.isoformat(), cycle_id))
        self._open_cycle_id = None

    def recent_cycles(self, limit: int = 10) -> list[sqlite3.Row]:
        return list(self.conn.execute("SELECT * FROM cycle ORDER BY id DESC LIMIT ?", (limit,)))

    def direction_history(self, key: EventKey, cycles: int = OSCILLATION_CYCLES) -> list[str]:
        """Historico de direcao por chave — base do detector de oscilacao."""
        uid, rid = key.as_row()
        rows = self.conn.execute(
            """SELECT direction FROM journal
               WHERE uid = ? AND recurrence_id = ? AND state = ?
               ORDER BY id DESC LIMIT ?""",
            (uid, rid, DONE, cycles),
        )
        return [r["direction"] for r in rows]

    # --- transacao e retencao -----------------------------------------------
    def begin(self) -> None:
        self.conn.execute("BEGIN IMMEDIATE")

    def commit(self) -> None:
        self.conn.execute("COMMIT")

    def rollback(self) -> None:
        self.conn.execute("ROLLBACK")

    def prune(self, moment: datetime) -> int:
        """Retencao do journal. GOV-05: NUNCA remove ciclo referenciado por
        conflito ainda aberto nem por chave suspensa."""
        cutoff = (moment - timedelta(days=JOURNAL_RETENTION_DAYS)).isoformat()
        keep_ids = [r["id"] for r in self.conn.execute(
            "SELECT id FROM cycle ORDER BY id DESC LIMIT ?", (JOURNAL_RETENTION_CYCLES,)
        )]
        protected_keys = {c.key.as_row() for c in self.list_conflicts() if is_open_like(c)}
        protected_keys |= {
            EventKey.from_row(r["uid"], r["recurrence_id"]).as_row()
            for r in self.conn.execute("SELECT uid, recurrence_id FROM ancestor WHERE suspended = 1")
        }
        removed = 0
        for row in self.conn.execute(
            "SELECT id FROM cycle WHERE closed_at IS NOT NULL AND closed_at < ?", (cutoff,)
        ).fetchall():
            cycle_id = row["id"]
            if cycle_id in keep_ids:
                continue
            entries = self.journal_of(cycle_id)
            if any(e.key.as_row() in protected_keys for e in entries):
                continue
            self.conn.execute("DELETE FROM journal WHERE cycle_id = ?", (cycle_id,))
            self.conn.execute("DELETE FROM cycle WHERE id = ?", (cycle_id,))
            removed += 1
        return removed


def is_open_like(conflict: ConflictRecord) -> bool:
    return conflict.state in (OPEN, RESOLVED)
