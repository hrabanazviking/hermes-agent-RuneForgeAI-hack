"""Persona canon vs runtime facts (Self-Aware Agency roadmap §16).

Persona canon and the runtime self-model solve different problems.
A persona file answers "what kind of being am I supposed to be?";
the self-model answers "what evidence says I currently am?" §16
lets a Caducea-style persona file seed exactly six things —
narrative self, ideal self, self-reflection vocabulary, values,
preferred practices, and philosophical interpretation — and §16 is
explicit that canon should not override deterministic runtime
facts: if canon says "I remember everything" while memory health
reports failure, the system recognises the discrepancy rather than
hallucinating continuity.

What stands here is that distinction, in code:

- a human-authored, read-only canon file
  (``entity/persona_canon.yaml``) whose assertions each carry one
  of the six §16 seed kinds (:data:`SEED_KINDS`), a bounded
  statement, and optionally one named deterministic runtime check
  (:data:`RUNTIME_CHECKS`). The runtime never writes, seeds, or
  edits this file; changes are human edits only, exactly like the
  Phase 5 autonomy policy;
- an explicit, deterministic evaluation
  (:meth:`PersonaCanonService.evaluate`): every assertion keeps
  the epistemic basis ``persona_canon`` forever — it can be
  *supported* by a named runtime check passing, *contradicted*
  by that check failing, or *unverifiable* (no check named, or
  the runtime fact is unknown) — and it is never promoted to a
  verified runtime fact. A contradicted assertion surfaces as a
  structured ``persona_vs_runtime`` discrepancy; the runtime fact
  stands and the layered self-model is never rewritten by canon
  (evaluation is read-only against every source store);
- the runtime facts themselves are the ones the plugin already
  owns: memory continuity is the continuity heartbeat probe,
  live goals and relationships come from the Slice 103 layered
  snapshot's objective layer when it is enabled, and a
  ``verified_capability`` check passes only for a capability the
  objective layer already verifies from strong evidence. A fact
  the snapshot cannot supply (layered model disabled) is
  *unknown*, which makes its check unverifiable — never
  contradicted and never supported;
- explicit evaluation receipts in this module's own bounded log
  (``entity/persona_canon_evaluations.jsonl``): counts only plus
  the contradicted assertion ids (slugs) — no statement text, so
  no receipt can smuggle canon prose into telemetry-shaped data.

Disabled by default. No hook, loop, scheduler, or turn-path
caller evaluates or records; both are explicit calls only.
"""

from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from hermes_constants import get_hermes_home, mkdir_under_hermes_home

from .context_packet import ContextItem
from .heartbeat import probe_heartbeat
from .identity import IdentityError, IdentityStore, _as_bool
from .self_model_layers import LayeredSelfModelError, LayeredSelfModelService

CANON_VERSION = 1
EVALUATION_VERSION = 1
DEFAULT_CANON_PATH = Path("entity") / "persona_canon.yaml"
DEFAULT_LOG_PATH = Path("entity") / "persona_canon_evaluations.jsonl"
DEFAULT_LOG_LIMIT = 200
MAX_CANON_BYTES = 256 * 1024
MAX_LOG_BYTES = 4 * 1024 * 1024
MAX_ASSERTIONS = 100
MAX_STATEMENT_CHARS = 500
EPISTEMIC_BASIS = "persona_canon"

# The six things §16 allows a persona file to seed, in roadmap order.
SEED_KINDS = (
    "narrative_self",
    "ideal_self",
    "reflection_vocabulary",
    "values",
    "preferred_practices",
    "philosophical_interpretation",
)

# The named deterministic runtime checks an assertion may declare.
RUNTIME_CHECKS = (
    "memory_continuity",
    "live_goals_present",
    "relationships_present",
    "verified_capability",
)

STATUSES = frozenset({"supported", "contradicted", "unverifiable"})
_SLUG = re.compile(r"[a-z0-9][a-z0-9_-]*")
_CANON_FIELDS = {"canon_version", "owner_entity_id", "assertions"}
_ASSERTION_FIELDS = {"assertion_id", "kind", "statement"}
_ASSERTION_OPTIONAL = {"runtime_check", "check_subject"}
_EVALUATION_FIELDS = {
    "evaluation_version", "kind", "record_id", "owner_entity_id",
    "recorded_at", "total", "supported", "contradicted",
    "unverifiable", "contradicted_ids",
}

try:
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None
try:
    import msvcrt
except ImportError:  # pragma: no cover
    msvcrt = None


class PersonaCanonError(RuntimeError):
    """Persona canon cannot be safely read, evaluated, or recorded."""


def _now_dt() -> datetime:
    return datetime.now(timezone.utc)


def _fmt(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _timestamp_ok(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _epoch(value: str) -> float:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except (ValueError, OverflowError, OSError):
        return 0.0


def _canonical_uuid(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        return str(uuid.UUID(value)) == value
    except ValueError:
        return False


def seed_kinds() -> list[str]:
    return list(SEED_KINDS)


def runtime_checks() -> list[str]:
    return list(RUNTIME_CHECKS)


class PersonaCanonStore:
    """Read the human-authored canon file; the runtime never writes it."""

    def __init__(self, ctx) -> None:
        self._ctx = ctx
        self._identity = IdentityStore(ctx)

    def path(self) -> Path:
        home = get_hermes_home().resolve()
        configured = Path(str(self._ctx.get_config(
            "persona_canon_path", str(DEFAULT_CANON_PATH))))
        if configured.is_absolute():
            configured = DEFAULT_CANON_PATH
        lexical = home / configured
        candidate = lexical.resolve()
        if not candidate.is_relative_to(home):
            lexical = home / DEFAULT_CANON_PATH
            candidate = lexical.resolve()
        if not candidate.is_relative_to(home):
            raise PersonaCanonError(
                "persona canon path resolves outside the profile")
        if lexical.is_symlink():
            return lexical
        return candidate

    def read(self) -> dict[str, Any] | None:
        """The validated canon document, or None when no file exists."""
        owner = self._identity.read().entity_id
        path = self.path()
        if path.is_symlink():
            raise PersonaCanonError(
                "persona canon file must not be a symbolic link")
        if not path.is_file():
            return None
        if path.stat().st_size > MAX_CANON_BYTES:
            raise PersonaCanonError("persona canon file exceeds its size limit")
        try:
            payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, yaml.YAMLError) as exc:
            raise PersonaCanonError(
                "persona canon file is unreadable or malformed") from exc
        return self._validate(payload, owner)

    def _validate(self, payload: Any, owner: str) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise PersonaCanonError("persona canon document must be a mapping")
        if set(payload) != _CANON_FIELDS:
            raise PersonaCanonError("persona canon fields are invalid")
        version = payload.get("canon_version")
        if isinstance(version, bool) or version != CANON_VERSION:
            raise PersonaCanonError("persona canon version is unsupported")
        if payload.get("owner_entity_id") != owner:
            raise PersonaCanonError(
                "persona canon owner does not match entity identity")
        assertions = payload.get("assertions")
        if not isinstance(assertions, list) or len(assertions) > MAX_ASSERTIONS:
            raise PersonaCanonError("persona canon assertions are invalid")
        seen: set[str] = set()
        out: list[dict[str, Any]] = []
        for item in assertions:
            out.append(self._validate_assertion(item, seen))
        return {
            "canon_version": CANON_VERSION,
            "owner_entity_id": owner,
            "assertions": out,
        }

    @staticmethod
    def _validate_assertion(item: Any, seen: set[str]) -> dict[str, Any]:
        if not isinstance(item, dict):
            raise PersonaCanonError("persona canon assertion must be a mapping")
        fields = set(item)
        if not _ASSERTION_FIELDS <= fields \
                or not fields <= (_ASSERTION_FIELDS | _ASSERTION_OPTIONAL):
            raise PersonaCanonError("persona canon assertion fields are invalid")
        assertion_id = item.get("assertion_id")
        if not isinstance(assertion_id, str) \
                or len(assertion_id) > 64 \
                or not _SLUG.fullmatch(assertion_id):
            raise PersonaCanonError("persona canon assertion id is invalid")
        if assertion_id in seen:
            raise PersonaCanonError("persona canon assertion id is duplicated")
        seen.add(assertion_id)
        if item.get("kind") not in SEED_KINDS:
            raise PersonaCanonError("persona canon assertion kind is invalid")
        statement = item.get("statement")
        if not isinstance(statement, str) or not statement.strip() \
                or len(statement) > MAX_STATEMENT_CHARS:
            raise PersonaCanonError(
                "persona canon assertion statement is invalid")
        check = item.get("runtime_check")
        if check is not None and check not in RUNTIME_CHECKS:
            raise PersonaCanonError(
                "persona canon assertion runtime check is invalid")
        subject = item.get("check_subject")
        if check == "verified_capability":
            if not isinstance(subject, str) or len(subject) > 64 \
                    or not _SLUG.fullmatch(subject):
                raise PersonaCanonError(
                    "verified_capability check requires a slug check_subject")
        elif subject is not None:
            raise PersonaCanonError(
                "check_subject is only valid for a verified_capability check")
        return {
            "assertion_id": assertion_id,
            "kind": item["kind"],
            "statement": statement,
            "runtime_check": check,
            "check_subject": subject,
        }


class PersonaCanonService:
    """Deterministic §16 evaluation plus the bounded receipt log."""

    def __init__(self, ctx) -> None:
        self._ctx = ctx
        self._identity = IdentityStore(ctx)
        self._canon = PersonaCanonStore(ctx)

    def enabled(self) -> bool:
        return self._identity.enabled() and _as_bool(
            self._ctx.get_config("persona_canon_enabled", False), False
        )

    def _limit(self) -> int:
        try:
            value = int(self._ctx.get_config(
                "persona_canon_log_limit", DEFAULT_LOG_LIMIT))
        except (TypeError, ValueError):
            value = DEFAULT_LOG_LIMIT
        return min(500, max(10, value))

    def log_path(self) -> Path:
        home = get_hermes_home().resolve()
        configured = Path(str(self._ctx.get_config(
            "persona_canon_log_path", str(DEFAULT_LOG_PATH))))
        if configured.is_absolute():
            configured = DEFAULT_LOG_PATH
        lexical = home / configured
        candidate = lexical.resolve()
        if not candidate.is_relative_to(home):
            lexical = home / DEFAULT_LOG_PATH
            candidate = lexical.resolve()
        if not candidate.is_relative_to(home):
            raise PersonaCanonError(
                "persona canon log path resolves outside the profile")
        if lexical.is_symlink():
            return lexical
        return candidate

    # -- runtime facts ------------------------------------------------

    def _runtime_facts(self) -> dict[str, Any]:
        heartbeat = probe_heartbeat(self._ctx)
        facts: dict[str, Any] = {
            "heartbeat_status": heartbeat.status,
            "heartbeat_healthy": bool(heartbeat.healthy),
            "live_goal_count": None,
            "relationship_count": None,
            "verified_capabilities": None,
        }
        layered = LayeredSelfModelService(self._ctx)
        if layered.enabled():
            try:
                objective = layered.snapshot()["objective"]
            except (IdentityError, LayeredSelfModelError, OSError):
                return facts
            facts["live_goal_count"] = objective["live_goal_count"]
            facts["relationship_count"] = objective["relationship_count"]
            facts["verified_capabilities"] = list(
                objective["verified_capabilities"])
        return facts

    @staticmethod
    def _check_fact(assertion: dict[str, Any],
                    facts: dict[str, Any]) -> bool | None:
        """True/False when the named fact is known, None when unknown."""
        check = assertion["runtime_check"]
        if check is None:
            return None
        if check == "memory_continuity":
            return bool(facts["heartbeat_healthy"])
        if check == "live_goals_present":
            count = facts["live_goal_count"]
            return None if count is None else count > 0
        if check == "relationships_present":
            count = facts["relationship_count"]
            return None if count is None else count > 0
        # verified_capability
        capabilities = facts["verified_capabilities"]
        if capabilities is None:
            return None
        return assertion["check_subject"] in capabilities

    # -- evaluation ---------------------------------------------------

    def evaluate(self) -> dict[str, Any]:
        """Evaluate canon against runtime facts. Pure read; writes nothing."""
        if not self.enabled():
            raise PersonaCanonError("persona canon is disabled")
        owner = self._identity.read().entity_id
        canon = self._canon.read()
        if canon is None:
            return {
                "canon_present": False,
                "owner_entity_id": owner,
                "evaluated_at": _fmt(_now_dt()),
                "total": 0, "supported": 0, "contradicted": 0,
                "unverifiable": 0,
                "assertions": [], "seeds": {}, "discrepancies": [],
                "runtime_facts": self._runtime_facts(),
            }
        facts = self._runtime_facts()
        results: list[dict[str, Any]] = []
        seeds: dict[str, list[str]] = {}
        discrepancies: list[dict[str, str]] = []
        counts = {"supported": 0, "contradicted": 0, "unverifiable": 0}
        for assertion in canon["assertions"]:
            seeds.setdefault(assertion["kind"], []).append(
                assertion["statement"])
            fact = self._check_fact(assertion, facts)
            if fact is None:
                status = "unverifiable"
            elif fact:
                status = "supported"
            else:
                status = "contradicted"
                discrepancies.append({
                    "kind": "persona_vs_runtime",
                    "assertion_id": assertion["assertion_id"],
                    "detail": (
                        f"persona canon assertion "
                        f"{assertion['assertion_id']} "
                        f"({assertion['runtime_check']}) is contradicted "
                        f"by runtime facts; the runtime fact stands"),
                })
            counts[status] += 1
            results.append({
                "assertion_id": assertion["assertion_id"],
                "kind": assertion["kind"],
                "statement": assertion["statement"],
                "runtime_check": assertion["runtime_check"],
                "check_subject": assertion["check_subject"],
                "status": status,
                "epistemic_basis": EPISTEMIC_BASIS,
            })
        return {
            "canon_present": True,
            "owner_entity_id": owner,
            "evaluated_at": _fmt(_now_dt()),
            "total": len(results),
            "supported": counts["supported"],
            "contradicted": counts["contradicted"],
            "unverifiable": counts["unverifiable"],
            "assertions": results,
            "seeds": seeds,
            "discrepancies": discrepancies,
            "runtime_facts": facts,
        }

    # -- evaluation receipt log ----------------------------------------

    def build_evaluation_record(
            self, evaluation: dict[str, Any] | None = None,
            *, recorded_at: str | None = None) -> dict[str, Any]:
        """Build a counts-only receipt from an evaluation. Pure."""
        evaluation = evaluation if evaluation is not None else self.evaluate()
        stamp = recorded_at or _fmt(_now_dt())
        if not _timestamp_ok(stamp):
            raise PersonaCanonError("evaluation recorded_at is invalid")
        record = {
            "evaluation_version": EVALUATION_VERSION,
            "kind": "persona_canon_evaluation",
            "record_id": str(uuid.uuid4()),
            "owner_entity_id": evaluation["owner_entity_id"],
            "recorded_at": stamp,
            "total": int(evaluation["total"]),
            "supported": int(evaluation["supported"]),
            "contradicted": int(evaluation["contradicted"]),
            "unverifiable": int(evaluation["unverifiable"]),
            "contradicted_ids": [
                item["assertion_id"]
                for item in evaluation["assertions"]
                if item["status"] == "contradicted"
            ],
        }
        self._validate_record(record, record["owner_entity_id"])
        return record

    def record_evaluation(
            self, evaluation: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.enabled():
            raise PersonaCanonError("persona canon is disabled")
        record = self.build_evaluation_record(evaluation)
        owner = self._identity.read().entity_id
        self._validate_record(record, owner)
        self._append(record)
        return record

    def evaluations(self, *, limit: int = 500) -> list[dict[str, Any]]:
        owner = self._identity.read().entity_id
        path = self.log_path()
        if path.is_symlink():
            raise PersonaCanonError(
                "persona canon log must not be a symbolic link")
        if not path.is_file():
            return []
        if path.stat().st_size > MAX_LOG_BYTES:
            raise PersonaCanonError("persona canon log exceeds its size limit")
        out: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except ValueError as exc:
                raise PersonaCanonError(
                    "persona canon log is malformed") from exc
            self._validate_record(payload, owner)
            out.append(payload)
        return out[-max(1, min(500, limit)):]

    def _validate_record(self, payload: Any, owner: str) -> None:
        if not isinstance(payload, dict):
            raise PersonaCanonError("persona canon evaluation is invalid")
        if set(payload) != _EVALUATION_FIELDS:
            raise PersonaCanonError(
                "persona canon evaluation fields are invalid")
        if payload.get("evaluation_version") != EVALUATION_VERSION:
            raise PersonaCanonError(
                "persona canon evaluation version is unsupported")
        if payload.get("kind") != "persona_canon_evaluation":
            raise PersonaCanonError("persona canon evaluation kind is invalid")
        if payload.get("owner_entity_id") != owner:
            raise PersonaCanonError(
                "persona canon evaluation owner does not match entity identity")
        if not _canonical_uuid(payload.get("record_id")):
            raise PersonaCanonError("persona canon evaluation id is invalid")
        if not _timestamp_ok(payload.get("recorded_at")):
            raise PersonaCanonError(
                "persona canon evaluation recorded_at is invalid")
        total = payload.get("total")
        parts = [payload.get(key) for key
                 in ("supported", "contradicted", "unverifiable")]
        for value in [total, *parts]:
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise PersonaCanonError(
                    "persona canon evaluation counts are invalid")
        if total != sum(parts):
            raise PersonaCanonError(
                "persona canon evaluation counts do not add up")
        ids = payload.get("contradicted_ids")
        if not isinstance(ids, list) or len(ids) != payload["contradicted"] \
                or len(set(ids)) != len(ids):
            raise PersonaCanonError(
                "persona canon evaluation contradicted ids are invalid")
        for value in ids:
            if not isinstance(value, str) or len(value) > 64 \
                    or not _SLUG.fullmatch(value):
                raise PersonaCanonError(
                    "persona canon evaluation contradicted ids are invalid")

    def _append(self, record: dict[str, Any]) -> None:
        path = self.log_path()
        if path.is_symlink():
            raise PersonaCanonError(
                "persona canon log must not be a symbolic link")
        lock_path = path.with_suffix(path.suffix + ".lock")
        mkdir_under_hermes_home(lock_path.parent)
        with lock_path.open("a+b") as lock:
            lock.seek(0, os.SEEK_END)
            if lock.tell() == 0:
                lock.write(b"\0")
                lock.flush()
            lock.seek(0)
            if fcntl is not None:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            elif msvcrt is not None:
                msvcrt.locking(lock.fileno(), msvcrt.LK_LOCK, 1)
            try:
                if path.exists() and path.stat().st_size > MAX_LOG_BYTES:
                    raise PersonaCanonError(
                        "persona canon log exceeds its size limit")
                with path.open("a", encoding="utf-8") as handle:
                    handle.write(
                        json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
                    handle.flush()
                    os.fsync(handle.fileno())
                lines = path.read_text(encoding="utf-8").splitlines()
                limit = self._limit()
                if len(lines) > limit:
                    tmp = path.with_suffix(path.suffix + ".tmp")
                    tmp.write_text("\n".join(lines[-limit:]) + "\n", encoding="utf-8")
                    os.replace(tmp, path)
            finally:
                lock.seek(0)
                if fcntl is not None:
                    fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
                elif msvcrt is not None:
                    msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)


class PersonaCanonBridge:
    """Surface a recorded §16 contradiction, content-bearing only.

    No session hook — evaluations are recorded only by explicit
    calls, and canon prose never enters the packet: the item names
    only the count of contradicted assertions.
    """

    def __init__(self, ctx) -> None:
        self._ctx = ctx
        self._service = PersonaCanonService(ctx)

    def hooks(self):
        return ()

    def packet_items(self, session_id: str, user_message: Any = "") -> list[ContextItem]:
        if not _as_bool(
            self._ctx.get_config("persona_canon_enabled", False), False
        ):
            return []
        try:
            rows = self._service.evaluations(limit=1)
        except (IdentityError, PersonaCanonError, OSError):
            return []
        if not rows:
            return []
        latest = rows[-1]
        if not latest["contradicted"]:
            return []
        return [ContextItem(
            section="current_state",
            content=(
                f"Persona canon (§16): {latest['contradicted']} persona "
                f"assertion(s) contradicted by runtime facts at last "
                f"evaluation; runtime facts stand — canon seeds the "
                f"narrative/ideal self but never overrides them."
            ),
            source="persona_canon",
            record_id=latest["record_id"],
            priority=0.4,
            updated_at=_epoch(latest["recorded_at"]),
        )]


__all__ = [
    "CANON_VERSION",
    "EVALUATION_VERSION",
    "DEFAULT_CANON_PATH",
    "SEED_KINDS",
    "RUNTIME_CHECKS",
    "EPISTEMIC_BASIS",
    "PersonaCanonError",
    "PersonaCanonStore",
    "PersonaCanonService",
    "PersonaCanonBridge",
    "seed_kinds",
    "runtime_checks",
]
