"""Persistent self-model store (Emergent Agency Phase 1, roadmap §8).

The self-model is the entity's durable, bounded self-understanding:
claims about its capabilities, preferences, commitments, limitations,
and uncertainties, each carried on the Phase 0 ``SelfClaim`` contract
(Slice 88) with its evidence and contradictions beside it.

The critical design rule from the roadmap holds here: the LLM may
*propose* a self-model update, but a deterministic merge layer decides
whether and how confidence changes. Proposal numbers are never copied
into the store: a new claim's confidence is capped by the strength of
its source, confirming evidence moves confidence by a fixed delta for
that strength, and a conflicting statement from non-strong evidence is
recorded as a contradiction instead of rewriting the claim. Strong
evidence (explicit user correction, deterministic tool results,
canonical identity/system state) is the only path that may restate a
claim. Weak evidence (drive/curiosity self-inference) can never create
a high-confidence belief.

This store never touches canonical identity: ``entity/entity.yaml``
and ``SOUL.md`` are read for ownership only, never written.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from hermes_constants import get_hermes_home, mkdir_under_hermes_home
from utils import atomic_yaml_write

from .agency_contracts import (
    SOURCE_TYPES,
    AgencyContractError,
    Provenance,
    SelfClaim,
)
from .context_packet import ContextItem
from .identity import IdentityError, IdentityStore, _as_bool


SELF_MODEL_VERSION = 1
DEFAULT_SELF_MODEL_PATH = Path("entity") / "self_model.yaml"
MAX_CLAIMS = 128
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_EVIDENCE_PER_CLAIM = 50
MAX_CONTRADICTIONS_PER_CLAIM = 50

SELF_MODEL_DOMAINS = frozenset(
    {"identity", "capability", "preference", "commitment", "limitation", "uncertainty"}
)

# Evidence strength by provenance source type (roadmap §8 update rules):
# strong = explicit user correction, deterministic tool result, verified
# subsystem state; medium = outcomes, patterns, and structured records;
# weak = model self-inference with no external support.
STRONG_SOURCES = frozenset({"user_explicit", "tool_result", "identity", "system_observation"})
MEDIUM_SOURCES = frozenset(
    {"goal", "relationship", "memory_record", "world_fact", "cognition_telemetry", "reflection"}
)
WEAK_SOURCES = frozenset({"drive", "curiosity"})

_CONFIDENCE_CAPS = {"strong": 0.95, "medium": 0.65, "weak": 0.35}
_POSITIVE_DELTAS = {"strong": 0.15, "medium": 0.08, "weak": 0.03}
_CONTRADICTION_DELTAS = {"strong": 0.20, "medium": 0.10, "weak": 0.04}
_MAX_CONFIDENCE = 0.98
_EVIDENCE_OUTCOMES = frozenset({"proposed", "positive", "contradiction"})

# Bounded packet contribution quotas (roadmap §8): highest-value claims
# only, never the complete self-model.
_PACKET_QUOTAS = (("capability", 3), ("limitation", 2), ("commitment", 2), ("uncertainty", 2))

_CLAIM_FIELDS = (
    "claim_id",
    "owner_entity_id",
    "domain",
    "key",
    "statement",
    "confidence",
    "source",
    "first_seen_at",
    "last_confirmed_at",
)

try:
    import fcntl
except ImportError:  # pragma: no cover - platform branch
    fcntl = None
try:
    import msvcrt
except ImportError:  # pragma: no cover - platform branch
    msvcrt = None


class SelfModelError(RuntimeError):
    """The self-model store cannot be safely read or changed."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def evidence_strength(source_type: str) -> str:
    if source_type in STRONG_SOURCES:
        return "strong"
    if source_type in MEDIUM_SOURCES:
        return "medium"
    return "weak"


def _timestamp_ok(value: Any, *, empty: bool = False) -> bool:
    if empty and value == "":
        return True
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


def _evidence_entry(source: Provenance, outcome: str, recorded_at: str) -> dict[str, Any]:
    return {
        "source_type": source.source_type,
        "source_id": source.source_id,
        "event_id": source.event_id,
        "outcome": outcome,
        "recorded_at": recorded_at,
    }


class SelfModelStore:
    """Versioned self-model ledger with a deterministic evidence merge."""

    def __init__(self, ctx) -> None:
        self._ctx = ctx
        self._identity = IdentityStore(ctx)

    def enabled(self) -> bool:
        return self._identity.enabled() and _as_bool(
            self._ctx.get_config("self_model_enabled", True), True
        )

    def path(self) -> Path:
        home = get_hermes_home().resolve()
        configured = Path(
            str(self._ctx.get_config("self_model_path", str(DEFAULT_SELF_MODEL_PATH)))
        )
        if configured.is_absolute():
            configured = DEFAULT_SELF_MODEL_PATH
        candidate = (home / configured).resolve()
        if not candidate.is_relative_to(home):
            candidate = (home / DEFAULT_SELF_MODEL_PATH).resolve()
        if not candidate.is_relative_to(home):
            raise SelfModelError("self-model path resolves outside the active profile")
        return candidate

    def _evidence_limit(self) -> int:
        try:
            value = int(self._ctx.get_config("self_model_evidence_limit", MAX_EVIDENCE_PER_CLAIM))
        except (TypeError, ValueError):
            value = MAX_EVIDENCE_PER_CLAIM
        return min(MAX_EVIDENCE_PER_CLAIM, max(1, value))

    def ensure(self) -> dict[str, Any]:
        owner = self._identity.ensure().entity_id
        path = self.path()
        with self._lock(path):
            if path.exists():
                return self._read_unlocked(path, owner)
            data = {
                "self_model_version": SELF_MODEL_VERSION,
                "owner_entity_id": owner,
                "updated_at": _now(),
                "claims": {},
            }
            self._write(path, data)
            return data

    def claims(self) -> list[SelfClaim]:
        owner = self._identity.read().entity_id
        path = self.path()
        with self._lock(path):
            data = self._read_unlocked(path, owner)
        return [self._claim_of(record) for record in data["claims"].values()]

    def propose(self, claim: SelfClaim) -> SelfClaim:
        """Merge one proposed claim deterministically; return the stored claim."""
        if not isinstance(claim, SelfClaim):
            raise SelfModelError("proposal must be a SelfClaim contract record")
        if claim.domain not in SELF_MODEL_DOMAINS:
            raise SelfModelError("self-model domain is not supported")
        owner = self._identity.read().entity_id
        if claim.owner_entity_id != owner:
            raise SelfModelError("self-model owner does not match entity identity")
        path = self.path()
        with self._lock(path):
            data = self._read_unlocked(path, owner)
            record = self._find(data, claim.domain, claim.key)
            now = _now()
            if record is None:
                if len(data["claims"]) >= MAX_CLAIMS:
                    raise SelfModelError("self-model claim ledger is full")
                record = self._new_record(claim, now)
                data["claims"][record["claim_id"]] = record
            else:
                self._merge_into(record, claim, now)
            data["updated_at"] = now
            self._write(path, data)
            return self._claim_of(record)

    def apply_evidence(
        self,
        domain: str,
        key: str,
        *,
        outcome: str,
        source: Provenance,
    ) -> SelfClaim:
        """Apply one explicit evidence outcome to an existing claim."""
        if outcome not in {"positive", "contradiction"}:
            raise SelfModelError("evidence outcome must be positive or contradiction")
        if not isinstance(source, Provenance):
            raise SelfModelError("evidence source must be a Provenance record")
        owner = self._identity.read().entity_id
        path = self.path()
        with self._lock(path):
            data = self._read_unlocked(path, owner)
            record = self._find(data, domain, key)
            if record is None:
                raise SelfModelError("self-model claim was not found")
            now = _now()
            self._apply(record, outcome, source, now, conflicting_statement="")
            data["updated_at"] = now
            self._write(path, data)
            return self._claim_of(record)

    # -- deterministic merge -------------------------------------------

    def _new_record(self, claim: SelfClaim, now: str) -> dict[str, Any]:
        strength = evidence_strength(claim.source.source_type)
        capped = min(claim.confidence, _CONFIDENCE_CAPS[strength])
        record = claim.to_dict()
        record["confidence"] = capped
        record["evidence"] = [_evidence_entry(claim.source, "proposed", now)]
        record["contradictions"] = []
        return record

    def _merge_into(self, record: dict[str, Any], claim: SelfClaim, now: str) -> None:
        strength = evidence_strength(claim.source.source_type)
        if claim.statement == record["statement"]:
            self._apply(record, "positive", claim.source, now, conflicting_statement="")
            return
        if strength == "strong":
            # Only strong evidence may restate a claim (roadmap §8).
            record["statement"] = claim.statement
            record["source"] = claim.source.to_dict()
            self._apply(record, "positive", claim.source, now, conflicting_statement="")
            return
        self._apply(
            record,
            "contradiction",
            claim.source,
            now,
            conflicting_statement=claim.statement,
        )

    def _apply(
        self,
        record: dict[str, Any],
        outcome: str,
        source: Provenance,
        now: str,
        *,
        conflicting_statement: str,
    ) -> None:
        strength = evidence_strength(source.source_type)
        confidence = float(record["confidence"])
        if outcome == "positive":
            confidence = min(_MAX_CONFIDENCE, confidence + _POSITIVE_DELTAS[strength])
            record["last_confirmed_at"] = now
        else:
            confidence = max(0.0, confidence - _CONTRADICTION_DELTAS[strength])
            contradictions = list(record["contradictions"])
            contradictions.append(
                {
                    **_evidence_entry(source, "contradiction", now),
                    "statement": conflicting_statement,
                }
            )
            record["contradictions"] = contradictions[-MAX_CONTRADICTIONS_PER_CLAIM:]
        record["confidence"] = round(confidence, 6)
        evidence = list(record["evidence"])
        evidence.append(_evidence_entry(source, outcome, now))
        record["evidence"] = evidence[-self._evidence_limit() :]

    # -- reading / validation ------------------------------------------

    @staticmethod
    def _find(data: dict[str, Any], domain: str, key: str) -> dict[str, Any] | None:
        for record in data["claims"].values():
            if record["domain"] == domain and record["key"] == key:
                return record
        return None

    @staticmethod
    def _claim_of(record: dict[str, Any]) -> SelfClaim:
        return SelfClaim.from_dict({field: record[field] for field in _CLAIM_FIELDS})

    def _read_unlocked(self, path: Path, owner: str) -> dict[str, Any]:
        if path.is_symlink():
            raise SelfModelError("self-model file must not be a symbolic link")
        if not path.is_file():
            raise SelfModelError("self-model file is missing")
        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                raise SelfModelError("self-model file exceeds its size limit")
            payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, yaml.YAMLError) as exc:
            raise SelfModelError("self-model file is unreadable or malformed") from exc
        if not isinstance(payload, dict):
            raise SelfModelError("self-model document must be a mapping")
        version = payload.get("self_model_version")
        if isinstance(version, bool) or version != SELF_MODEL_VERSION:
            raise SelfModelError("self-model version is unsupported")
        if payload.get("owner_entity_id") != owner:
            raise SelfModelError("self-model owner does not match entity identity")
        if not _timestamp_ok(payload.get("updated_at")):
            raise SelfModelError("self-model updated_at is invalid")
        claims = payload.get("claims")
        if not isinstance(claims, dict) or len(claims) > MAX_CLAIMS:
            raise SelfModelError("self-model claims mapping is invalid or oversized")
        for claim_id, record in claims.items():
            self._validate_record(claim_id, record, owner)
        return payload

    def _validate_record(self, claim_id: Any, record: Any, owner: str) -> None:
        if not isinstance(record, dict) or record.get("claim_id") != claim_id:
            raise SelfModelError("self-model claim record is invalid")
        try:
            claim = self._claim_of(record)
        except (AgencyContractError, KeyError, TypeError) as exc:
            raise SelfModelError("self-model claim record is invalid") from exc
        if claim.owner_entity_id != owner:
            raise SelfModelError("self-model claim owner does not match entity identity")
        if claim.domain not in SELF_MODEL_DOMAINS:
            raise SelfModelError("self-model claim domain is not supported")
        self._validate_entries(record.get("evidence"), kind="evidence")
        self._validate_entries(record.get("contradictions"), kind="contradictions")

    @staticmethod
    def _validate_entries(entries: Any, *, kind: str) -> None:
        limit = MAX_EVIDENCE_PER_CLAIM if kind == "evidence" else MAX_CONTRADICTIONS_PER_CLAIM
        if not isinstance(entries, list) or len(entries) > limit:
            raise SelfModelError(f"self-model {kind} list is invalid or oversized")
        for entry in entries:
            if not isinstance(entry, dict):
                raise SelfModelError(f"self-model {kind} entry is invalid")
            if entry.get("source_type") not in SOURCE_TYPES:
                raise SelfModelError(f"self-model {kind} source type is invalid")
            source_id = entry.get("source_id")
            if not isinstance(source_id, str) or not source_id.strip() or len(source_id) > 200:
                raise SelfModelError(f"self-model {kind} source_id is invalid")
            if not _timestamp_ok(entry.get("recorded_at")):
                raise SelfModelError(f"self-model {kind} timestamp is invalid")
            if kind == "evidence" and entry.get("outcome") not in _EVIDENCE_OUTCOMES:
                raise SelfModelError("self-model evidence outcome is invalid")
            if kind == "contradictions":
                statement = entry.get("statement")
                if not isinstance(statement, str) or len(statement) > 1000:
                    raise SelfModelError("self-model contradiction statement is invalid")

    # -- persistence primitives ----------------------------------------

    @staticmethod
    def _write(path: Path, data: dict[str, Any]) -> None:
        atomic_yaml_write(path, data, sort_keys=False, create_mode=0o600)

    @contextmanager
    def _lock(self, path: Path):
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
                yield
            finally:
                lock.seek(0)
                if fcntl is not None:
                    fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
                elif msvcrt is not None:
                    msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)


class SelfModelBridge:
    """Create the self-model at session start and offer its bounded packet."""

    def __init__(self, ctx) -> None:
        self._store = SelfModelStore(ctx)

    def hooks(self):
        return (("on_session_start", self.on_session_start),)

    def on_session_start(self, **_: Any) -> None:
        if not self._store.enabled():
            return
        try:
            self._store.ensure()
        except (IdentityError, SelfModelError, OSError):
            return

    def packet_items(self, session_id: str, user_message: Any = "") -> list[ContextItem]:
        if not self._store.enabled():
            return []
        try:
            claims = self._store.claims()
        except (IdentityError, SelfModelError, OSError):
            return []
        items: list[ContextItem] = []
        for domain, quota in _PACKET_QUOTAS:
            rows = [claim for claim in claims if claim.domain == domain]
            if domain == "uncertainty":
                rows.sort(key=lambda claim: (claim.confidence, claim.key, claim.claim_id))
            else:
                rows.sort(key=lambda claim: (-claim.confidence, claim.key, claim.claim_id))
            for claim in rows[:quota]:
                items.append(
                    ContextItem(
                        section="current_state",
                        content=(
                            f"Self-model {claim.domain} ({claim.key}): "
                            f"{claim.statement} [confidence {claim.confidence:.2f}]"
                        ),
                        source="self_model",
                        record_id=claim.claim_id,
                        priority=claim.confidence,
                        updated_at=_epoch(claim.last_confirmed_at or claim.first_seen_at),
                    )
                )
        return items


__all__ = [
    "SELF_MODEL_VERSION",
    "DEFAULT_SELF_MODEL_PATH",
    "SELF_MODEL_DOMAINS",
    "SelfModelError",
    "SelfModelStore",
    "SelfModelBridge",
    "evidence_strength",
]
