"""Reusable confidence contract (Self-Aware Agency roadmap §18).

§18 adds one reusable confidence contract for important
self-beliefs: every such belief may carry a unit-interval
``confidence``, a ``basis`` list drawn from the seven named
basis values, and a ``last_verified_at`` timestamp, and is
described by one of the seven suggested epistemic labels
(verified / strongly_supported / supported / uncertain /
speculative / subjective / symbolic).

The label is a deterministic function of the record — pure
:func:`label_for` — and strict read validation refuses a
stored label that disagrees with it, so a belief can never
quietly claim a stronger epistemic standing than its basis
and confidence earn:

- a belief whose only basis is ``self_report`` is
  ``subjective`` and one whose only basis is
  ``persona_canon`` is ``symbolic``, at any confidence —
  neither can be promoted to a factual label by confidence
  alone (the §7 rule, generalised);
- ``verified`` requires a ``runtime_fact`` basis, confidence
  at least 0.9, and a ``last_verified_at`` actually present;
- two or more independent evidence bases (runtime fact,
  memory, user feedback, external source) at confidence at
  least 0.75 are ``strongly_supported``; one evidence base at
  confidence at least 0.5 is ``supported``; anything else
  with an evidence or inference basis is ``uncertain`` at
  confidence at least 0.3 and ``speculative`` below it.

This layer is a contract plus a bounded assessment log at
``entity/epistemic_assessments.jsonl``. It imports no other
store and writes nothing else; assessments are recorded only
by explicit calls. Existing stores adopt the contract by
carrying its fields — rewriting any store to do so is a
separate slice per store. Disabled by default.
"""

from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hermes_constants import get_hermes_home, mkdir_under_hermes_home

from .context_packet import ContextItem
from .identity import IdentityError, IdentityStore, _as_bool

EPISTEMIC_VERSION = 1
DEFAULT_LOG_PATH = Path("entity") / "epistemic_assessments.jsonl"
DEFAULT_LOG_LIMIT = 200
MAX_LOG_BYTES = 4 * 1024 * 1024
MAX_BASIS = 7
MAX_CLAIM_CHARS = 500
VERIFIED_MIN_CONFIDENCE = 0.9
STRONG_MIN_CONFIDENCE = 0.75
SUPPORTED_MIN_CONFIDENCE = 0.5
UNCERTAIN_MIN_CONFIDENCE = 0.3

# The seven §18 basis values, in roadmap order.
BASIS_VALUES = (
    "runtime_fact",
    "memory",
    "user_feedback",
    "self_report",
    "inference",
    "persona_canon",
    "external_source",
)

# Basis values that count as evidence about the world.
EVIDENCE_BASIS = frozenset(
    {"runtime_fact", "memory", "user_feedback", "external_source"}
)

# The seven §18 epistemic labels, in roadmap order.
LABELS = (
    "verified",
    "strongly_supported",
    "supported",
    "uncertain",
    "speculative",
    "subjective",
    "symbolic",
)

_FIELDS = {
    "epistemic_version", "record_id", "owner_entity_id",
    "recorded_at", "subject", "claim", "confidence", "basis",
    "last_verified_at", "label",
}

_SLUG = re.compile(r"^[a-z][a-z0-9_]*$")

try:
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None
try:
    import msvcrt
except ImportError:  # pragma: no cover
    msvcrt = None


class EpistemicError(RuntimeError):
    """An epistemic assessment cannot be safely built or read."""


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


def _unit(value: Any) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and 0.0 <= float(value) <= 1.0
    )


def _canonical_uuid(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        return str(uuid.UUID(value)) == value
    except ValueError:
        return False


def basis_values() -> list[str]:
    return list(BASIS_VALUES)


def labels() -> list[str]:
    return list(LABELS)


def _normalise_basis(value: Any) -> list[str]:
    if not isinstance(value, (list, tuple)) or not value \
            or len(value) > MAX_BASIS:
        raise EpistemicError("epistemic basis is invalid or oversized")
    out: list[str] = []
    for item in value:
        if item not in BASIS_VALUES:
            raise EpistemicError("epistemic basis value is invalid")
        if item not in out:
            out.append(item)
    return [name for name in BASIS_VALUES if name in out]


def label_for(confidence: Any, basis: Any, *,
              last_verified_at: Any = None) -> str:
    """The §18 epistemic label of a belief — a pure function.

    ``basis`` is normalised first (unknown values refused).
    Subjective and symbolic are basis-determined: a belief
    resting only on self-report or only on persona canon
    keeps that label at any confidence.
    """
    if not _unit(confidence):
        raise EpistemicError("epistemic confidence is invalid")
    names = _normalise_basis(basis)
    basis_set = set(names)
    evidence = basis_set & EVIDENCE_BASIS
    if not evidence and "inference" not in basis_set:
        if basis_set <= {"persona_canon"}:
            return "symbolic"
        return "subjective"
    score = float(confidence)
    if "runtime_fact" in basis_set and score >= VERIFIED_MIN_CONFIDENCE \
            and _timestamp_ok(last_verified_at):
        return "verified"
    if len(evidence) >= 2 and score >= STRONG_MIN_CONFIDENCE:
        return "strongly_supported"
    if evidence and score >= SUPPORTED_MIN_CONFIDENCE:
        return "supported"
    if score >= UNCERTAIN_MIN_CONFIDENCE:
        return "uncertain"
    return "speculative"


def make_assessment_fields(*, confidence: Any, basis: Any,
                           last_verified_at: Any = None
                           ) -> dict[str, Any]:
    """The reusable §18 contract fields for any store to carry.

    Pure: returns the normalised confidence / basis /
    last_verified_at triple plus its derived label. Any store
    may embed these fields; the label always derives, it is
    never asserted independently.
    """
    names = _normalise_basis(basis)
    if not _unit(confidence):
        raise EpistemicError("epistemic confidence is invalid")
    if last_verified_at is not None and not _timestamp_ok(last_verified_at):
        raise EpistemicError("epistemic last_verified_at is invalid")
    return {
        "confidence": float(confidence),
        "basis": names,
        "last_verified_at": last_verified_at,
        "label": label_for(confidence, names,
                           last_verified_at=last_verified_at),
    }


class EpistemicsService:
    """The §18 assessment log."""

    def __init__(self, ctx) -> None:
        self._ctx = ctx
        self._identity = IdentityStore(ctx)

    def enabled(self) -> bool:
        return self._identity.enabled() and _as_bool(
            self._ctx.get_config("epistemics_enabled", False), False
        )

    def _limit(self) -> int:
        try:
            value = int(self._ctx.get_config(
                "epistemics_log_limit", DEFAULT_LOG_LIMIT))
        except (TypeError, ValueError):
            value = DEFAULT_LOG_LIMIT
        return min(500, max(10, value))

    def path(self) -> Path:
        home = get_hermes_home().resolve()
        configured = Path(str(self._ctx.get_config(
            "epistemics_log_path", str(DEFAULT_LOG_PATH))))
        if configured.is_absolute():
            configured = DEFAULT_LOG_PATH
        lexical = home / configured
        candidate = lexical.resolve()
        if not candidate.is_relative_to(home):
            lexical = home / DEFAULT_LOG_PATH
            candidate = lexical.resolve()
        if not candidate.is_relative_to(home):
            raise EpistemicError(
                "epistemic log path resolves outside the profile")
        if lexical.is_symlink():
            return lexical
        return candidate

    # -- assessments ---------------------------------------------------

    def assess(self, subject: str, *, claim: str, confidence: float,
               basis: Any, last_verified_at: str | None = None,
               recorded_at: str | None = None) -> dict[str, Any]:
        """Record one §18 assessment (explicit only)."""
        if not self.enabled():
            raise EpistemicError("epistemics are disabled")
        if not isinstance(subject, str) or not _SLUG.match(subject):
            raise EpistemicError("epistemic subject is invalid")
        if not isinstance(claim, str) or not claim.strip() \
                or len(claim.strip()) > MAX_CLAIM_CHARS:
            raise EpistemicError("epistemic claim is invalid")
        fields = make_assessment_fields(
            confidence=confidence, basis=basis,
            last_verified_at=last_verified_at)
        owner = self._identity.read().entity_id
        stamp = recorded_at or _fmt(_now_dt())
        record = {
            "epistemic_version": EPISTEMIC_VERSION,
            "record_id": str(uuid.uuid4()),
            "owner_entity_id": owner,
            "recorded_at": stamp,
            "subject": subject,
            "claim": claim.strip(),
            **fields,
        }
        self._validate(record, owner)
        self._append(record)
        return record

    def assessments(self, *, limit: int = 500) -> list[dict[str, Any]]:
        owner = self._identity.read().entity_id
        path = self.path()
        if path.is_symlink():
            raise EpistemicError("epistemic log must not be a symbolic link")
        if not path.is_file():
            return []
        if path.stat().st_size > MAX_LOG_BYTES:
            raise EpistemicError("epistemic log exceeds its size limit")
        out: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except ValueError as exc:
                raise EpistemicError("epistemic log is malformed") from exc
            self._validate(payload, owner)
            out.append(payload)
        return out[-max(1, min(500, limit)):]

    def latest_for(self, subject: str) -> dict[str, Any] | None:
        """The latest assessment of one subject. Read-only."""
        rows = [row for row in self.assessments(limit=500)
                if row["subject"] == subject]
        return rows[-1] if rows else None

    def summary_by_label(self) -> dict[str, list[str]]:
        """The §18 internal summary: latest claims grouped by label.

        Read-only and deterministic: for each label in roadmap
        order, the bounded claim texts of the latest assessment
        per subject carrying that label, in subject order.
        """
        latest: dict[str, dict[str, Any]] = {}
        for row in self.assessments(limit=500):
            latest[row["subject"]] = row
        grouped: dict[str, list[str]] = {label: [] for label in LABELS}
        for subject in sorted(latest):
            grouped[latest[subject]["label"]].append(latest[subject]["claim"])
        return grouped

    # -- validation / bounded log --------------------------------------

    @staticmethod
    def _validate(payload: Any, owner: str) -> None:
        if not isinstance(payload, dict) or set(payload) != _FIELDS:
            raise EpistemicError("epistemic fields are invalid")
        if payload.get("epistemic_version") != EPISTEMIC_VERSION:
            raise EpistemicError("epistemic version is unsupported")
        if not _canonical_uuid(payload.get("record_id")):
            raise EpistemicError("epistemic id is invalid")
        if payload.get("owner_entity_id") != owner:
            raise EpistemicError(
                "epistemic owner does not match entity identity")
        if not _timestamp_ok(payload.get("recorded_at")):
            raise EpistemicError("epistemic timestamps are invalid")
        if not isinstance(payload.get("subject"), str) \
                or not _SLUG.match(payload["subject"]):
            raise EpistemicError("epistemic subject is invalid")
        claim = payload.get("claim")
        if not isinstance(claim, str) or not claim.strip() \
                or len(claim.strip()) > MAX_CLAIM_CHARS:
            raise EpistemicError("epistemic claim is invalid")
        names = _normalise_basis(payload.get("basis"))
        if payload.get("basis") != names:
            raise EpistemicError("epistemic basis is not normalised")
        verified_at = payload.get("last_verified_at")
        if verified_at is not None and not _timestamp_ok(verified_at):
            raise EpistemicError("epistemic last_verified_at is invalid")
        if not _unit(payload.get("confidence")):
            raise EpistemicError("epistemic confidence is invalid")
        label = payload.get("label")
        if label not in LABELS:
            raise EpistemicError("epistemic label is invalid")
        if label != label_for(payload["confidence"], names,
                              last_verified_at=verified_at):
            raise EpistemicError(
                "epistemic label disagrees with the §18 label function")

    def _append(self, record: dict[str, Any]) -> None:
        path = self.path()
        if path.is_symlink():
            raise EpistemicError("epistemic log must not be a symbolic link")
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
                    raise EpistemicError("epistemic log exceeds its size limit")
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


class EpistemicsBridge:
    """Surface the epistemic standing of the latest beliefs.

    No session hook — assessments are recorded only by
    explicit calls. The item is content-bearing only: it names
    how many latest beliefs stand at each factual label and
    the strongest verified claim's subject.
    """

    def __init__(self, ctx) -> None:
        self._ctx = ctx
        self._service = EpistemicsService(ctx)

    def hooks(self):
        return ()

    def packet_items(self, session_id: str, user_message: Any = "") -> list[ContextItem]:
        if not _as_bool(
            self._ctx.get_config("epistemics_enabled", False), False
        ):
            return []
        try:
            grouped = self._service.summary_by_label()
            latest = self._service.assessments(limit=500)
        except (IdentityError, EpistemicError, OSError):
            return []
        if not latest:
            return []
        counts = ", ".join(
            f"{label} {len(grouped[label])}" for label in LABELS
            if grouped[label])
        newest = latest[-1]
        content = (
            f"Epistemic state (§18): {counts}. Latest assessment: "
            f"{newest['subject']} is {newest['label']} "
            f"(confidence {newest['confidence']:.2f}, basis "
            f"{'+'.join(newest['basis'])})."
        )
        return [ContextItem(
            section="current_state",
            content=content,
            source="epistemics",
            record_id=newest["record_id"],
            priority=0.4,
            updated_at=_epoch(newest["recorded_at"]),
        )]


__all__ = [
    "EPISTEMIC_VERSION",
    "DEFAULT_LOG_PATH",
    "BASIS_VALUES",
    "EVIDENCE_BASIS",
    "LABELS",
    "EpistemicError",
    "EpistemicsService",
    "EpistemicsBridge",
    "basis_values",
    "labels",
    "label_for",
    "make_assessment_fields",
]
