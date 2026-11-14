"""X.05 Sagnaskemma adapter (roadmap section 40).

Roadmap section 40 (Part VII workstream 5 of 15) names the
Sagnaskemma engine: Volmarr's private tabletop engine in the
private repo hrabanazviking/Sagnaskemma-Volmarrs-D-and-D-Lore-
Treasure-Trove (engine/ tree). The X.05 audit (docs/
modernization/X05_SAGNASKEMMA_WORKSTREAM.md, 2026-11-14)
staged that tree sparsely (engine + tests + scripts + docs
interfaces only; the repo's campaign/canon/lore trees were
never checked out) directly under $HOME at ~/sagnaskemma-x05,
HEAD a1f474f4b880, and proved the real engine contract there:
package sagnaskemma-engine 0.2.0, engine.api discover() /
execute() at protocol 1.0 (243 commands at the audited HEAD),
transports python / cli-json / ndjson-stdio, state root via
the SAGNASKEMMA_STATE_DIR environment variable, sole runtime
dependency Avrae d20. There is NO LICENSE file at the audited
HEAD: the repo is the owner's private creation and its
THIRD_PARTY_NOTICES records the license as to-be-decided
while the code stays non-public. No engine source and no
private canon, scenario, character or lore content is
incorporated into this fork -- this module is original
volmarr-core code written against the audited interface,
plugin-side only. The pre-existing volmarr-rpg SRD adapter
is a separate plugin and is untouched.

What this slice builds, honestly scoped to section 40:

- a private adapter plan surface (this module's status /
  capability records) based on the engine's current API,
  version and license scope (item 1);
- mechanics capabilities (dice, checks, combat, inventory,
  initiative, tables, encounter state) kept SEPARATE from
  narrative capabilities (session descriptions, NPC /
  character state, approved lore retrieval) (item 2);
- ONE canonical dice owner per session: every roll in a
  session flows through that session's seeded DiceOwner;
  seeds and outcomes are recorded in the session ledger for
  audit and replay (item 3);
- game-state persistence in an adapter-side durable store
  (SQLite, WAL, synchronous FULL): the audited engine
  contract is explicit that its request ids are correlation
  ids only (not persisted idempotency keys) and that its
  atomicity is per save file with no cross-file rollback,
  so transaction ids, idempotent application, savepoint /
  undo and crash recovery live here, in the adapter, and
  say so (item 4);
- a versioned private local tool-service record
  (runeforge.sagnaskemma.service.v1): users without source
  access see "not configured" and NO hidden content -- when
  no engine root is configured, every engine-facing surface
  reports not_configured and no capability is dressed up
  (item 5);
- an optional Samtal link record: distinct room / session
  ids, per-seat permissions, privacy boundaries (item 6);
- a WYRD translation that lands ONLY in a separate fictional
  campaign namespace (sagnaskemma-<session>), reality tagged
  fictional -- roleplay events never mix with real-world
  observations (item 7; the consumer seam X.04 built);
- copyrighted rule text, homebrew and campaign material stay
  in approved private stores only: lore retrieval is DENIED
  by default (canon_denied) and needs an explicit approved-
  store configuration this slice does not provide (item 8);
- frontend handoff by session export / import: the dice
  owner state and the transaction ledger travel with the
  session, so a handoff never duplicates a dice roll or a
  state change (item 9);
- production readiness is NEVER claimed: every status record
  carries production_ready False with its reason (item 10).
"""
from __future__ import annotations

import hashlib
import json
import random
import re
import sqlite3
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

SOURCE_REPO = "hrabanazviking/Sagnaskemma-Volmarrs-D-and-D-Lore-Treasure-Trove"
SOURCE_BRANCH = "main"
SOURCE_HEAD_AUDITED = "a1f474f4b8803b7003b35b09f486a53145545685"
ENGINE_PACKAGE = "sagnaskemma-engine"
ENGINE_VERSION_AUDITED = "0.2.0"
ENGINE_PROTOCOL_VERSION = "1.0"
ENGINE_COMMANDS_AUDITED = 243
ENGINE_TRANSPORTS = ("python", "cli-json", "ndjson-stdio")
ENGINE_STATE_ENV = "SAGNASKEMMA_STATE_DIR"
ENGINE_DEPENDENCY = "d20>=1.1.2,<2 (Avrae d20, sole runtime dependency)"
SOURCE_LICENSE = ("private - no LICENSE file at the audited HEAD; "
                  "owner's private repo, license to-be-decided while "
                  "non-public (THIRD_PARTY_NOTICES section 3, read "
                  "at the staged tree in X.05); no source incorporated")
SERVICE_SCHEMA = "runeforge.sagnaskemma.service.v1"
SESSION_SCHEMA = "runeforge.sagnaskemma.session.v1"
ADAPTER_PLAN_SCHEMA = "runeforge.sagnaskemma.adapter-plan.v1"
NOT_CONFIGURED = "not configured"
MECHANICS_CAPABILITIES = ("dice", "checks", "combat", "inventory",
                          "initiative", "tables", "encounter_state")
NARRATIVE_CAPABILITIES = ("session_description", "npc_state",
                          "character_state", "lore_retrieval")
ALL_CAPABILITIES = MECHANICS_CAPABILITIES + NARRATIVE_CAPABILITIES
SEAT_ROLES = {
    "gm": ("read", "roll", "check", "combat", "inventory",
           "initiative", "encounter", "narrate", "npc_state",
           "character_state", "undo", "link", "export"),
    "player": ("read", "roll", "check", "inventory", "narrate"),
    "spectator": ("read",),
}
_ACTION_CAPABILITY = {
    "roll": "dice", "check": "checks", "combat": "combat",
    "inventory": "inventory", "initiative": "initiative",
    "encounter": "encounter_state",
    "describe": "session_description", "npc_state": "npc_state",
    "character_state": "character_state",
}
_ACTION_PERMISSION = {
    "roll": "roll", "check": "check", "combat": "combat",
    "inventory": "inventory", "initiative": "initiative",
    "encounter": "encounter", "describe": "narrate",
    "npc_state": "npc_state", "character_state": "character_state",
}
_ID_RE = re.compile(r"^[a-z0-9](?:[a-z0-9_-]{0,63})$")
_DICE_RE = re.compile(r"^(\d{1,3})d(\d{1,4})([+-]\d{1,6})?$")
_VERSION_RE = re.compile(r"__version__\s*=\s*\"([^\"]+)\"")


class SagnaskemmaError(Exception):
    """Named refusal in the X.05 adapter layer."""

    def __init__(self, name: str, detail: str) -> None:
        super().__init__(f"{name}: {detail}")
        self.name = name
        self.detail = detail


def _valid_id(value: Any) -> bool:
    return isinstance(value, str) and bool(_ID_RE.fullmatch(value))


# ------------------------------------------------------------ engine probe

def probe_engine(root: Any) -> dict:
    """File-level probe of one staged engine root.

    Interface facts only: the probe reads the engine package's
    own version line and the presence of its public modules.
    It never reads the repo's data, campaign, canon or lore
    content, and it imports nothing."""
    record = {"configured": False, "root": str(root or ""),
              "engine_version": None, "protocol_version": None,
              "reason": NOT_CONFIGURED}
    if not root:
        return record
    base = Path(str(root))
    api = base / "engine" / "api.py"
    init = base / "engine" / "__init__.py"
    dice = base / "engine" / "dice.py"
    if not (api.is_file() and init.is_file() and dice.is_file()):
        record["reason"] = ("engine root does not hold the audited "
                            "engine/ tree (api.py, __init__.py, "
                            "dice.py) -- reported as " + NOT_CONFIGURED)
        return record
    try:
        text = init.read_text(encoding="utf-8", errors="strict")[:4096]
    except OSError as exc:
        record["reason"] = f"engine version unreadable: {exc}"
        return record
    match = _VERSION_RE.search(text)
    record["configured"] = True
    record["engine_version"] = match.group(1) if match else None
    record["protocol_version"] = ENGINE_PROTOCOL_VERSION
    record["reason"] = "staged engine tree present (interface probe only)"
    return record


def engine_root_from_ctx(ctx) -> str:
    return str(ctx.get_config("sagnaskemma_engine_root", "") or "")


def capability_catalog() -> dict:
    """The section 40 item 2 split, as data (plan surface)."""
    return {
        "schema": ADAPTER_PLAN_SCHEMA,
        "service": "volmarr-sagnaskemma",
        "mechanics": list(MECHANICS_CAPABILITIES),
        "narrative": list(NARRATIVE_CAPABILITIES),
        "narrative_gates": {
            "session_description": "seat permission narrate",
            "npc_state": "seat permission npc_state (gm)",
            "character_state": "seat permission character_state (gm)",
            "lore_retrieval": ("DENIED by default (canon_denied): "
                                "approved private store only, item 8"),
        },
        "dice_owner": ("one canonical seeded DiceOwner per session; "
                       "seeds and outcomes recorded in the session "
                       "ledger for audit/replay (item 3)"),
        "persistence": ("adapter-side durable store: transaction "
                        "ids, idempotent application, savepoint/undo, "
                        "crash recovery (item 4)"),
    }


def authorize_capability(ctx, capability: Any, *,
                         engine: dict | None = None) -> dict:
    """Gate one capability (items 5 and 8).

    Without a configured engine every capability answers
    not_configured -- users without source access see that and
    no hidden content. Lore retrieval is separately denied by
    default even with an engine: canon lives in approved
    private stores only."""
    if capability not in ALL_CAPABILITIES:
        raise SagnaskemmaError(
            "unknown_capability",
            f"capability {capability!r} is not a Sagnaskemma "
            f"capability; known: {list(ALL_CAPABILITIES)}")
    probe = engine if engine is not None else probe_engine(
        engine_root_from_ctx(ctx))
    if capability == "lore_retrieval":
        if not ctx.get_config("sagnaskemma_canon_access", False):
            raise SagnaskemmaError(
                "canon_denied",
                "lore retrieval is denied by default: copyrighted "
                "rule text, homebrew and campaign material stay in "
                "approved private stores only (section 40 item 8)")
        raise SagnaskemmaError(
            "canon_store_not_configured",
            "canon access is flagged on but no approved private "
            "canon store is configured in this slice; no content "
            "is served (section 40 item 8)")
    if not probe["configured"]:
        raise SagnaskemmaError(
            "not_configured",
            "Sagnaskemma engine is " + NOT_CONFIGURED + ": "
            + probe["reason"])
    return {"capability": capability, "allowed": True,
            "kind": ("mechanics" if capability in MECHANICS_CAPABILITIES
                     else "narrative"),
            "engine_version": probe["engine_version"]}


def sagnaskemma_status(ctx, *, recorded_at: str = "") -> dict:
    """Truthful status for the live caller (items 1, 5, 10)."""
    probe = probe_engine(engine_root_from_ctx(ctx))
    enabled = bool(ctx.get_config("sagnaskemma_enabled", False))
    return {
        "schema": SERVICE_SCHEMA,
        "service": "volmarr-sagnaskemma",
        "availability": ("contract-implemented" if probe["configured"]
                         else NOT_CONFIGURED),
        "enabled": enabled,
        "configured": probe["configured"],
        "engine": probe,
        "source_repo": SOURCE_REPO,
        "source_branch": SOURCE_BRANCH,
        "source_head_audited": SOURCE_HEAD_AUDITED,
        "engine_package": ENGINE_PACKAGE,
        "engine_version_audited": ENGINE_VERSION_AUDITED,
        "protocol_version": ENGINE_PROTOCOL_VERSION,
        "transports": list(ENGINE_TRANSPORTS),
        "source_license": SOURCE_LICENSE,
        "pin_taken_in_x05": True,
        "capabilities": capability_catalog(),
        "production_ready": False,
        "production_ready_reason": ("an interface existing is not "
                                    "production readiness (section 40 "
                                    "item 10): the live engine service "
                                    "and multi-frontend play are unproven"),
        "recorded_at": recorded_at,
    }


# ------------------------------------------------------------ dice owner

def _rng_state_to_json(state) -> list:
    version, internal, gauss = state
    return [version, list(internal), gauss]


def _rng_state_from_json(data: list):
    return (int(data[0]), tuple(int(x) for x in data[1]), data[2])


class DiceOwner:
    """The ONE canonical random/dice owner for a session (item 3).

    All rolls in a session flow through this object. It is
    seeded once at session creation; the seed and every outcome
    (expression, faces, modifier, total, roller, purpose) are
    recorded in order, so a session's rolls can be audited and
    replayed exactly: a fresh DiceOwner with the same seed
    reproduces the identical sequence. The full owner state
    (including the RNG state) serializes with the session, so a
    frontend handoff continues the sequence instead of
    re-rolling it (item 9)."""

    def __init__(self, seed: int) -> None:
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise SagnaskemmaError(
                "seed_malformed", "a session seed must be an integer")
        self._seed = seed
        self._rng = random.Random(seed)
        self._rolls: list[dict] = []

    @property
    def seed(self) -> int:
        return self._seed

    @property
    def rolls(self) -> list[dict]:
        return deepcopy(self._rolls)

    def roll(self, expression: Any, *, roller: str | None = None,
             purpose: str | None = None) -> dict:
        if not isinstance(expression, str):
            raise SagnaskemmaError(
                "dice_malformed", "a dice expression must be text")
        match = _DICE_RE.fullmatch(expression.strip())
        if not match:
            raise SagnaskemmaError(
                "dice_malformed",
                f"dice expression {expression!r} is not NdM[+-K]")
        count, sides = int(match.group(1)), int(match.group(2))
        modifier = int(match.group(3)) if match.group(3) else 0
        if count < 1 or sides < 2:
            raise SagnaskemmaError(
                "dice_malformed",
                "a roll needs at least one die with at least two sides")
        faces = [self._rng.randint(1, sides) for _ in range(count)]
        record = {"index": len(self._rolls), "expression": expression.strip(),
                  "faces": faces, "modifier": modifier,
                  "total": sum(faces) + modifier,
                  "roller": roller, "purpose": purpose}
        self._rolls.append(record)
        return deepcopy(record)

    def to_state(self) -> dict:
        return {"seed": self._seed,
                "rng_state": _rng_state_to_json(self._rng.getstate()),
                "rolls": deepcopy(self._rolls)}

    @classmethod
    def from_state(cls, state: dict) -> "DiceOwner":
        owner = cls(int(state["seed"]))
        owner._rng.setstate(_rng_state_from_json(state["rng_state"]))
        owner._rolls = deepcopy(state.get("rolls") or [])
        return owner


def _initial_state(seed: int) -> dict:
    return {"dice": DiceOwner(seed).to_state(), "combatants": {},
            "initiative": [], "inventory": {}, "encounter": {},
            "description": "", "npc_state": {}, "character_state": {}}


def _payload_hash(kind: str, payload: dict) -> str:
    blob = json.dumps({"kind": kind, "payload": payload},
                      sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


# ------------------------------------------------------------ session store

class TableSessionStore:
    """Durable adapter-side game-state store (item 4).

    SQLite with WAL and synchronous FULL. Every applied action
    is a transaction with a caller-supplied transaction id:
    re-applying the same id with the same payload returns the
    recorded result WITHOUT re-executing (no duplicated dice
    roll, no duplicated state change -- the handoff guarantee,
    item 9); the same id with a different payload is refused
    by name. Each committed transaction records the full prior
    state, so undo is a savepoint restore (latest committed
    transaction first). State lands in the sessions row in the
    same database transaction as the ledger row, so a crash
    mid-action leaves either the whole action or none of it:
    reopening the store IS the crash recovery, and the state
    read back is exactly the last committed state."""

    def __init__(self, path: Any) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        conn = self._connect()
        try:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS sagna_sessions ("
                "session_id TEXT PRIMARY KEY, owner_seat TEXT, "
                "seed INTEGER, state_json TEXT, "
                "wyrd_namespace TEXT, samtal_room_id TEXT, "
                "revision INTEGER, created_at TEXT)")
            conn.execute(
                "CREATE TABLE IF NOT EXISTS sagna_seats ("
                "session_id TEXT, seat_id TEXT, role TEXT, "
                "PRIMARY KEY (session_id, seat_id))")
            conn.execute(
                "CREATE TABLE IF NOT EXISTS sagna_transactions ("
                "txn_id TEXT PRIMARY KEY, session_id TEXT, "
                "seat_id TEXT, kind TEXT, payload_hash TEXT, "
                "payload_json TEXT, result_json TEXT, "
                "prior_state_json TEXT, status TEXT, "
                "created_at TEXT)")
            conn.commit()
        finally:
            conn.close()

    @property
    def path(self) -> Path:
        return self._path

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._path))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=FULL")
        return conn

    # -- sessions and seats ------------------------------------

    def create_session(self, session_id: str, owner_seat: str,
                       seed: int, *, created_at: str = "") -> dict:
        if not _valid_id(session_id):
            raise SagnaskemmaError(
                "session_malformed",
                f"session_id {session_id!r} is not a valid table id")
        if not _valid_id(owner_seat):
            raise SagnaskemmaError(
                "seat_malformed",
                f"owner seat {owner_seat!r} is not a valid seat id")
        state = _initial_state(seed)
        namespace = f"sagnaskemma-{session_id}"
        conn = self._connect()
        try:
            if conn.execute(
                    "SELECT 1 FROM sagna_sessions WHERE session_id=?",
                    (session_id,)).fetchone():
                raise SagnaskemmaError(
                    "session_exists",
                    f"session {session_id!r} already exists; import "
                    "its handoff export instead of recreating it")
            conn.execute(
                "INSERT INTO sagna_sessions VALUES (?,?,?,?,?,?,?,?)",
                (session_id, owner_seat, seed,
                 json.dumps(state, sort_keys=True), namespace, None,
                 0, created_at))
            conn.execute(
                "INSERT INTO sagna_seats VALUES (?,?,?)",
                (session_id, owner_seat, "gm"))
            conn.commit()
        finally:
            conn.close()
        return self.get_session(session_id)

    def get_session(self, session_id: str) -> dict:
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT session_id, owner_seat, seed, wyrd_namespace, "
                "samtal_room_id, revision, created_at FROM "
                "sagna_sessions WHERE session_id=?",
                (session_id,)).fetchone()
        finally:
            conn.close()
        if row is None:
            raise SagnaskemmaError(
                "session_not_found", f"no session {session_id!r}")
        return {"schema": SESSION_SCHEMA, "session_id": row[0],
                "owner_seat": row[1], "seed": row[2],
                "wyrd_namespace": row[3], "samtal_room_id": row[4],
                "revision": row[5], "created_at": row[6],
                "seats": self.seats(session_id)}

    def _state(self, conn, session_id: str) -> dict:
        row = conn.execute(
            "SELECT state_json FROM sagna_sessions WHERE session_id=?",
            (session_id,)).fetchone()
        if row is None:
            raise SagnaskemmaError(
                "session_not_found", f"no session {session_id!r}")
        return json.loads(row[0])

    def state(self, session_id: str) -> dict:
        conn = self._connect()
        try:
            return self._state(conn, session_id)
        finally:
            conn.close()

    def seats(self, session_id: str) -> list[dict]:
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT seat_id, role FROM sagna_seats WHERE "
                "session_id=? ORDER BY seat_id", (session_id,)).fetchall()
        finally:
            conn.close()
        return [{"seat_id": r[0], "role": r[1],
                 "permissions": list(SEAT_ROLES[r[1]])} for r in rows]

    def add_seat(self, session_id: str, seat_id: str,
                 role: str) -> dict:
        if role not in SEAT_ROLES:
            raise SagnaskemmaError(
                "seat_malformed",
                f"role {role!r} is not one of {sorted(SEAT_ROLES)}")
        if not _valid_id(seat_id):
            raise SagnaskemmaError(
                "seat_malformed",
                f"seat_id {seat_id!r} is not a valid seat id")
        conn = self._connect()
        try:
            self._state(conn, session_id)
            conn.execute(
                "INSERT OR REPLACE INTO sagna_seats VALUES (?,?,?)",
                (session_id, seat_id, role))
            conn.commit()
        finally:
            conn.close()
        return {"seat_id": seat_id, "role": role,
                "permissions": list(SEAT_ROLES[role])}

    def _seat_role(self, conn, session_id: str, seat_id: str) -> str:
        row = conn.execute(
            "SELECT role FROM sagna_seats WHERE session_id=? AND "
            "seat_id=?", (session_id, seat_id)).fetchone()
        if row is None:
            raise SagnaskemmaError(
                "seat_not_found",
                f"seat {seat_id!r} holds no seat in session "
                f"{session_id!r}; seats are isolated per session")
        return row[0]

    # -- transactional application ------------------------------

    def apply(self, session_id: str, seat_id: str, txn_id: str,
              kind: str, payload: dict | None = None, *,
              created_at: str = "") -> dict:
        """Apply one action as one transaction (item 4).

        Turn/session ownership is explicit: the acting seat must
        hold a seat in THIS session with the permission the
        action needs. An interrupted action (the mutator raises)
        rolls back whole: no ledger row, no state change, no
        revision bump, and no dice spent -- the session dice
        owner is rebuilt from the untouched prior state."""
        if kind not in _ACTION_CAPABILITY:
            raise SagnaskemmaError(
                "action_unknown",
                f"action {kind!r} is not a table action; known: "
                f"{sorted(_ACTION_CAPABILITY)}")
        if not _valid_id(txn_id):
            raise SagnaskemmaError(
                "txn_malformed",
                f"transaction id {txn_id!r} is not a valid id")
        payload = dict(payload or {})
        digest = _payload_hash(kind, payload)
        conn = self._connect()
        try:
            prior_row = conn.execute(
                "SELECT payload_hash, result_json, status FROM "
                "sagna_transactions WHERE txn_id=?",
                (txn_id,)).fetchone()
            if prior_row is not None:
                if prior_row[0] != digest:
                    raise SagnaskemmaError(
                        "idempotency_conflict",
                        f"transaction {txn_id!r} was already applied "
                        "with a different payload; refusing to "
                        "reinterpret it")
                recorded = json.loads(prior_row[1])
                recorded["duplicate"] = True
                recorded["status"] = prior_row[2]
                return recorded
            role = self._seat_role(conn, session_id, seat_id)
            needed = _ACTION_PERMISSION[kind]
            if needed not in SEAT_ROLES[role]:
                raise SagnaskemmaError(
                    "seat_permission_refused",
                    f"seat {seat_id!r} with role {role!r} may not "
                    f"perform {kind!r} (needs permission {needed!r}); "
                    "per-seat permissions are enforced per session")
            prior_state = self._state(conn, session_id)
            new_state, result = _mutate(kind, deepcopy(prior_state),
                                        payload, seat_id)
            revision_row = conn.execute(
                "SELECT revision FROM sagna_sessions WHERE "
                "session_id=?", (session_id,)).fetchone()
            revision = int(revision_row[0]) + 1
            result = {**result, "schema": SESSION_SCHEMA,
                      "txn_id": txn_id, "session_id": session_id,
                      "seat_id": seat_id, "kind": kind,
                      "revision": revision, "duplicate": False,
                      "status": "committed"}
            conn.execute(
                "UPDATE sagna_sessions SET state_json=?, revision=? "
                "WHERE session_id=?",
                (json.dumps(new_state, sort_keys=True), revision,
                 session_id))
            conn.execute(
                "INSERT INTO sagna_transactions VALUES "
                "(?,?,?,?,?,?,?,?,?,?)",
                (txn_id, session_id, seat_id, kind, digest,
                 json.dumps(payload, sort_keys=True),
                 json.dumps(result, sort_keys=True),
                 json.dumps(prior_state, sort_keys=True),
                 "committed", created_at))
            conn.commit()
            return result
        finally:
            conn.close()

    def undo(self, session_id: str, seat_id: str,
             txn_id: str) -> dict:
        """Savepoint undo: restore the state before one txn.

        Stack discipline: only the latest committed transaction
        can be undone, so an undo can never silently rewrite
        history underneath later actions."""
        conn = self._connect()
        try:
            role = self._seat_role(conn, session_id, seat_id)
            if "undo" not in SEAT_ROLES[role]:
                raise SagnaskemmaError(
                    "seat_permission_refused",
                    f"seat {seat_id!r} with role {role!r} may not undo")
            row = conn.execute(
                "SELECT prior_state_json, status FROM "
                "sagna_transactions WHERE txn_id=? AND session_id=?",
                (txn_id, session_id)).fetchone()
            if row is None:
                raise SagnaskemmaError(
                    "txn_not_found",
                    f"no transaction {txn_id!r} in session {session_id!r}")
            if row[1] != "committed":
                raise SagnaskemmaError(
                    "txn_not_committed",
                    f"transaction {txn_id!r} is {row[1]}, not committed")
            latest = conn.execute(
                "SELECT txn_id FROM sagna_transactions WHERE "
                "session_id=? AND status='committed' ORDER BY "
                "rowid DESC LIMIT 1", (session_id,)).fetchone()
            if latest is None or latest[0] != txn_id:
                raise SagnaskemmaError(
                    "undo_not_latest",
                    "only the latest committed transaction can be "
                    "undone (savepoint stack discipline)")
            conn.execute(
                "UPDATE sagna_sessions SET state_json=?, "
                "revision=revision-1 WHERE session_id=?",
                (row[0], session_id))
            conn.execute(
                "UPDATE sagna_transactions SET status='undone' "
                "WHERE txn_id=?", (txn_id,))
            conn.commit()
        finally:
            conn.close()
        return {"schema": SESSION_SCHEMA, "txn_id": txn_id,
                "session_id": session_id, "status": "undone"}

    def transactions(self, session_id: str) -> list[dict]:
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT txn_id, seat_id, kind, status FROM "
                "sagna_transactions WHERE session_id=? ORDER BY rowid",
                (session_id,)).fetchall()
        finally:
            conn.close()
        return [{"txn_id": r[0], "seat_id": r[1], "kind": r[2],
                 "status": r[3]} for r in rows]

    # -- Samtal link + WYRD translation --------------------------

    def link_samtal(self, session_id: str, seat_id: str,
                    room_id: str) -> dict:
        """Optional Samtal link record (item 6).

        Distinct ids are required: the Samtal room id must not
        equal the table session id, so a chat room and a game
        session can never be conflated. The record carries the
        per-seat permission map; the privacy boundary is stated
        in the record itself."""
        if not _valid_id(room_id):
            raise SagnaskemmaError(
                "room_malformed",
                f"Samtal room id {room_id!r} is not a valid id")
        if room_id == session_id:
            raise SagnaskemmaError(
                "room_session_conflated",
                "the Samtal room id must be distinct from the table "
                "session id (section 40 item 6)")
        conn = self._connect()
        try:
            role = self._seat_role(conn, session_id, seat_id)
            if "link" not in SEAT_ROLES[role]:
                raise SagnaskemmaError(
                    "seat_permission_refused",
                    f"seat {seat_id!r} with role {role!r} may not "
                    "link a Samtal room")
            self._state(conn, session_id)
            conn.execute(
                "UPDATE sagna_sessions SET samtal_room_id=? WHERE "
                "session_id=?", (room_id, session_id))
            conn.commit()
        finally:
            conn.close()
        return {"schema": "runeforge.sagnaskemma.samtal-link.v1",
                "session_id": session_id, "samtal_room_id": room_id,
                "seats": self.seats(session_id),
                "privacy": ("table state stays in the adapter store; "
                            "the room carries seat-filtered views "
                            "only, never the session ledger")}

    def wyrd_campaign_record(self, session_id: str) -> dict:
        """Translate table state into the WYRD campaign namespace.

        Item 7: the namespace is ALWAYS the fictional campaign
        namespace minted at session creation, and the record is
        tagged fictional -- roleplay state is never presented as
        a real-world observation."""
        session = self.get_session(session_id)
        state = self.state(session_id)
        return {"schema": "runeforge.sagnaskemma.wyrd-campaign.v1",
                "namespace": session["wyrd_namespace"],
                "reality": "fictional", "truth_class": "fictional_state",
                "session_id": session_id,
                "combatants": sorted(state["combatants"]),
                "initiative_order": [e["name"] for e in state["initiative"]],
                "encounter": state["encounter"],
                "rolls_recorded": len(state["dice"]["rolls"])}

    # -- handoff export / import (item 9) -------------------------

    def export_session(self, session_id: str) -> dict:
        session = self.get_session(session_id)
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT txn_id, seat_id, kind, payload_hash, "
                "payload_json, result_json, prior_state_json, status "
                "FROM sagna_transactions WHERE session_id=? ORDER BY "
                "rowid", (session_id,)).fetchall()
        finally:
            conn.close()
        return {"schema": SESSION_SCHEMA, "session": session,
                "state": self.state(session_id),
                "transactions": [
                    {"txn_id": r[0], "seat_id": r[1], "kind": r[2],
                     "payload_hash": r[3], "payload": json.loads(r[4]),
                     "result": json.loads(r[5]),
                     "prior_state": json.loads(r[6]), "status": r[7]}
                    for r in rows]}

    def import_session(self, data: dict) -> dict:
        """Import one handoff export; idempotent by session id.

        Re-importing the same session returns the existing
        session untouched -- a handoff can never duplicate dice
        rolls or state, because the dice owner state and the
        whole transaction ledger travel with the export."""
        if not isinstance(data, dict) or \
                data.get("schema") != SESSION_SCHEMA:
            raise SagnaskemmaError(
                "handoff_malformed",
                "handoff data does not carry the session schema "
                + SESSION_SCHEMA)
        session = data["session"]
        session_id = session["session_id"]
        conn = self._connect()
        try:
            exists = conn.execute(
                "SELECT 1 FROM sagna_sessions WHERE session_id=?",
                (session_id,)).fetchone()
            if exists:
                return {**self.get_session(session_id),
                        "handoff": "already_present"}
            conn.execute(
                "INSERT INTO sagna_sessions VALUES (?,?,?,?,?,?,?,?)",
                (session_id, session["owner_seat"], session["seed"],
                 json.dumps(data["state"], sort_keys=True),
                 session["wyrd_namespace"], session["samtal_room_id"],
                 session["revision"], session["created_at"]))
            for seat in session["seats"]:
                conn.execute(
                    "INSERT INTO sagna_seats VALUES (?,?,?)",
                    (session_id, seat["seat_id"], seat["role"]))
            for txn in data["transactions"]:
                conn.execute(
                    "INSERT INTO sagna_transactions VALUES "
                    "(?,?,?,?,?,?,?,?,?,?)",
                    (txn["txn_id"], session_id, txn["seat_id"],
                     txn["kind"], txn["payload_hash"],
                     json.dumps(txn["payload"], sort_keys=True),
                     json.dumps(txn["result"], sort_keys=True),
                     json.dumps(txn["prior_state"], sort_keys=True),
                     txn["status"], ""))
            conn.commit()
        finally:
            conn.close()
        return {**self.get_session(session_id), "handoff": "imported"}


# ------------------------------------------------------------ action mutators

def _mutate(kind: str, state: dict, payload: dict,
            seat_id: str) -> tuple[dict, dict]:
    """Apply one action to a working copy of the session state.

    Pure with respect to the store: raising here aborts the
    transaction and the working copy (including any dice the
    action spent) is discarded whole -- that is the interrupted-
    action rollback. Synthetic payloads only in tests; real
    session content stays in the private store."""
    owner = DiceOwner.from_state(state["dice"])
    result: dict[str, Any] = {}
    if kind == "roll":
        record = owner.roll(payload.get("expression"),
                            roller=seat_id,
                            purpose=payload.get("purpose"))
        result = {"roll": record}
    elif kind == "check":
        record = owner.roll("1d20", roller=seat_id,
                            purpose=payload.get("purpose") or "check")
        modifier = payload.get("modifier", 0)
        if isinstance(modifier, bool) or not isinstance(modifier, int):
            raise SagnaskemmaError(
                "check_malformed", "a check modifier must be an integer")
        total = record["total"] + modifier
        result = {"roll": record, "modifier": modifier, "total": total,
                  "dc": payload.get("dc"),
                  "success": (None if payload.get("dc") is None
                              else total >= payload["dc"])}
    elif kind == "combat":
        name = payload.get("name")
        if not isinstance(name, str) or not name.strip():
            raise SagnaskemmaError(
                "combat_malformed", "a combatant needs a name")
        combatants = state["combatants"]
        if "hp" in payload:
            hp = payload["hp"]
            if isinstance(hp, bool) or not isinstance(hp, int) or hp < 0:
                raise SagnaskemmaError(
                    "combat_malformed", "combatant hp must be a "
                    "non-negative integer")
            combatants[name] = {"hp": hp, "max_hp": hp}
        elif "damage" in payload:
            if name not in combatants:
                raise SagnaskemmaError(
                    "combatant_not_found",
                    f"no combatant {name!r} in this encounter")
            damage = payload["damage"]
            if isinstance(damage, bool) or not isinstance(damage, int) \
                    or damage < 0:
                raise SagnaskemmaError(
                    "combat_malformed", "damage must be a non-negative "
                    "integer")
            combatants[name]["hp"] = max(
                0, combatants[name]["hp"] - damage)
        else:
            raise SagnaskemmaError(
                "combat_malformed",
                "a combat action carries hp (add) or damage (apply)")
        result = {"combatant": name,
                  "state": deepcopy(combatants[name])}
    elif kind == "initiative":
        entries = payload.get("entries")
        if not isinstance(entries, list) or not entries:
            raise SagnaskemmaError(
                "initiative_malformed",
                "initiative needs a non-empty entries list")
        cleaned = []
        for entry in entries:
            if not isinstance(entry, dict) or \
                    not isinstance(entry.get("name"), str) or \
                    isinstance(entry.get("initiative"), bool) or \
                    not isinstance(entry.get("initiative"), int):
                raise SagnaskemmaError(
                    "initiative_malformed",
                    "each initiative entry is {name, initiative: int}")
            cleaned.append({"name": entry["name"],
                            "initiative": entry["initiative"]})
        state["initiative"] = sorted(
            cleaned, key=lambda e: (-e["initiative"], e["name"]))
        result = {"initiative": deepcopy(state["initiative"])}
    elif kind == "inventory":
        holder = payload.get("holder")
        item = payload.get("item")
        count = payload.get("count", 1)
        if not isinstance(holder, str) or not holder.strip() or \
                not isinstance(item, str) or not item.strip() or \
                isinstance(count, bool) or not isinstance(count, int) \
                or count == 0:
            raise SagnaskemmaError(
                "inventory_malformed",
                "inventory needs holder, item and a non-zero int count")
        held = state["inventory"].setdefault(holder, {})
        new_count = held.get(item, 0) + count
        if new_count < 0:
            raise SagnaskemmaError(
                "inventory_insufficient",
                f"{holder!r} does not hold {abs(count)} of {item!r}")
        if new_count == 0:
            held.pop(item, None)
        else:
            held[item] = new_count
        result = {"holder": holder, "item": item, "count": new_count}
    elif kind == "encounter":
        update = payload.get("encounter")
        if not isinstance(update, dict) or not update:
            raise SagnaskemmaError(
                "encounter_malformed",
                "an encounter action carries a non-empty encounter dict")
        state["encounter"].update(update)
        result = {"encounter": deepcopy(state["encounter"])}
    elif kind == "describe":
        text = payload.get("text")
        if not isinstance(text, str) or not text.strip():
            raise SagnaskemmaError(
                "narrative_malformed",
                "a session description needs text")
        state["description"] = text
        result = {"description": text}
    elif kind in {"npc_state", "character_state"}:
        name = payload.get("name")
        fields = payload.get("fields")
        if not isinstance(name, str) or not name.strip() or \
                not isinstance(fields, dict) or not fields:
            raise SagnaskemmaError(
                "narrative_malformed",
                f"a {kind} action carries a name and a fields dict")
        state[kind][name] = deepcopy(fields)
        result = {kind: {name: deepcopy(fields)}}
    else:  # pragma: no cover - apply() gates kinds first
        raise SagnaskemmaError("action_unknown", f"unknown action {kind!r}")
    state["dice"] = owner.to_state()
    return state, result


# ------------------------------------------------------------ engine client

_DISCOVER_CODE = (
    "import json,sys; sys.path.insert(0, '.'); "
    "from engine import api; d = api.discover(); "
    "print(json.dumps({'protocol_version': d['protocol_version'], "
    "'name': d['name'], 'command_count': len(d['commands']), "
    "'transports': d['transports'], 'state_env': d['state_env']}))")
_EXECUTE_CODE = (
    "import json,sys; sys.path.insert(0, '.'); "
    "from engine import api; req = json.loads(sys.argv[1]); "
    "print(json.dumps(api.execute(req['argv'], "
    "request_id=req.get('request_id'))))")


class EngineClient:
    """Versioned private local tool-service client (item 5).

    The engine is called ONLY through its audited public
    contract -- engine.api discover()/execute() at protocol
    1.0 -- in a bounded subprocess rooted at the staged tree,
    with the engine state root pointed at a caller-named
    private directory. The Hermes process never imports the
    private engine. A runner can be injected for contract
    proofs; the default runner is the subprocess above."""

    def __init__(self, root: Any, *, python: str = "",
                 state_dir: str = "", runner=None,
                 timeout: float = 30.0) -> None:
        self._root = str(root or "")
        self._python = python or sys.executable
        self._state_dir = state_dir
        self._runner = runner
        self._timeout = timeout

    def _run(self, code: str, argv: list[str]) -> dict:
        if self._runner is not None:
            return self._runner(code, argv)
        probe = probe_engine(self._root)
        if not probe["configured"]:
            raise SagnaskemmaError(
                "not_configured",
                "Sagnaskemma engine is " + NOT_CONFIGURED + ": "
                + probe["reason"])
        import os
        env = dict(os.environ)
        if self._state_dir:
            env[ENGINE_STATE_ENV] = self._state_dir
        try:
            proc = subprocess.run(
                [self._python, "-c", code, *argv], cwd=self._root,
                env=env, capture_output=True, text=True,
                timeout=self._timeout)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise SagnaskemmaError(
                "engine_unavailable",
                f"the staged engine could not be run: {exc}") from exc
        if proc.returncode != 0:
            raise SagnaskemmaError(
                "engine_unavailable",
                "the staged engine exited "
                f"{proc.returncode}: {proc.stderr.strip()[:200]}")
        try:
            return json.loads(proc.stdout.strip().splitlines()[-1])
        except (ValueError, IndexError) as exc:
            raise SagnaskemmaError(
                "engine_protocol_error",
                "the staged engine did not answer with one JSON "
                "envelope") from exc

    def discover(self) -> dict:
        record = self._run(_DISCOVER_CODE, [])
        if record.get("protocol_version") != ENGINE_PROTOCOL_VERSION:
            raise SagnaskemmaError(
                "version_mismatch",
                f"engine protocol {record.get('protocol_version')!r} "
                f"is not the audited protocol "
                f"{ENGINE_PROTOCOL_VERSION}; no silent adaptation")
        return {"schema": SERVICE_SCHEMA, "service": "volmarr-sagnaskemma",
                **record}

    def execute(self, argv: list[str], *, request_id: str) -> dict:
        """Execute one engine command under one transaction id.

        The engine's own contract is honest that its request id
        is a correlation id, not an idempotency key -- callers
        that need no-duplicate guarantees route through the
        session store's transaction ledger, which never calls
        execute twice for one transaction id."""
        payload = json.dumps({"argv": list(argv),
                              "request_id": request_id})
        return self._run(_EXECUTE_CODE, [payload])


def session_db_path(ctx) -> Path:
    """Resolve the session store path (profile-relative default)."""
    from hermes_constants import get_hermes_home
    raw = str(ctx.get_config("sagnaskemma_session_db",
                             "state/sagnaskemma_sessions.db"))
    path = Path(raw)
    if not path.is_absolute():
        path = get_hermes_home() / path
    return path


def service_record(ctx, *, recorded_at: str = "") -> dict:
    """The versioned private local tool-service record (item 5)."""
    status = sagnaskemma_status(ctx, recorded_at=recorded_at)
    status["session_store"] = ("adapter-side durable store at the "
                                "configured sagnaskemma_session_db path")
    status["hidden_content_served"] = False
    return status
