"""Phase 0 agency contracts: schemas before intelligence (Emergent Agency §7).

This module defines the shared data contracts every later emergent-agency
phase builds on — self-model claims, drive state, reflection records,
curiosity questions, action proposals, policy decisions, action results,
and cycle reports — plus the shared provenance model. It contains no
behavior: no stores, no LLM calls, no execution, no scheduling. The
completion gate for Phase 0 is that these schemas, their bounds, their
owner checks, and their tests exist before any autonomous behavior is
started.

Every contract is a frozen dataclass with:

- a canonical-UUID ``owner_entity_id`` (wrong-owner state is refused at
  parse time by the stores that will own these records);
- strict ``to_dict`` / ``from_dict`` round-tripping — unknown keys are
  rejected, which is also how raw chain-of-thought can never be smuggled
  into a reflection record: there is simply no field that accepts it;
- bounded text, bounded unit-interval scores, and timezone-aware ISO
  timestamps, validated identically on construction and on parse.
"""

from __future__ import annotations

import math
import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

AGENCY_CONTRACTS_VERSION = 1

SOURCE_TYPES = frozenset(
    {
        "identity",
        "user_explicit",
        "goal",
        "relationship",
        "tool_result",
        "cognition_telemetry",
        "world_fact",
        "memory_record",
        "reflection",
        "drive",
        "curiosity",
        "system_observation",
    }
)

REFLECTION_OUTCOMES = frozenset({"success", "failure", "partial", "unknown"})
CURIOSITY_STATUSES = frozenset(
    {"open", "investigating", "resolved", "deferred", "abandoned", "invalidated"}
)
POLICY_DECISIONS = frozenset({"allow", "require_confirmation", "deny"})
ACTION_RESULT_STATUSES = frozenset({"succeeded", "failed", "denied", "skipped"})
CYCLE_STATUSES = frozenset({"completed", "paused", "failed"})
ESTIMATED_COSTS = frozenset({"none", "low", "medium", "high"})

MAX_SOURCE_ID_CHARS = 200
MAX_EVENT_ID_CHARS = 200
MAX_SLUG_CHARS = 64
MAX_STATEMENT_CHARS = 1_000
MAX_TEXT_CHARS = 1_000
MAX_REF_CHARS = 200
MAX_LESSONS = 10
MAX_LESSON_CHARS = 500

_SLUG = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


class AgencyContractError(ValueError):
    """An agency contract record is malformed, out of bounds, or ownerless."""


def _fail(message: str) -> None:
    raise AgencyContractError(message)


def _canonical_uuid(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        _fail(f"{field_name} must be a canonical UUID string")
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError):
        _fail(f"{field_name} must be a canonical UUID string")
    if str(parsed) != value:
        _fail(f"{field_name} must be a canonical UUID string")
    return value


def _owner(value: Any) -> str:
    return _canonical_uuid(value, "owner_entity_id")


def _slug(value: Any, field_name: str) -> str:
    if (
        not isinstance(value, str)
        or not value
        or len(value) > MAX_SLUG_CHARS
        or not _SLUG.match(value)
    ):
        _fail(f"{field_name} must be a bounded slug")
    return value


def _text(value: Any, field_name: str, maximum: int, *, required: bool = True) -> str:
    if not isinstance(value, str):
        _fail(f"{field_name} must be text")
    value = value.strip()
    if (required and not value) or len(value) > maximum:
        _fail(f"{field_name} is empty or exceeds {maximum} characters")
    return value


def _unit(value: Any, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _fail(f"{field_name} must be a number in [0, 1]")
    parsed = float(value)
    if not math.isfinite(parsed) or not 0.0 <= parsed <= 1.0:
        _fail(f"{field_name} must be a finite number in [0, 1]")
    return parsed


def _risk_class(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 5:
        _fail("risk_class must be an integer from 0 to 5")
    return value


def _count(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 1_000_000:
        _fail(f"{field_name} must be a bounded non-negative integer")
    return value


def _timestamp(value: Any, field_name: str, *, empty: bool = False) -> str:
    if empty and value == "":
        return ""
    if not isinstance(value, str):
        _fail(f"{field_name} must be an ISO timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        _fail(f"{field_name} must be an ISO timestamp")
    if parsed.tzinfo is None:
        _fail(f"{field_name} must be timezone-aware")
    return value


def _check_keys(payload: Any, allowed: set[str], record: str) -> dict[str, Any]:
    if not isinstance(payload, dict):
        _fail(f"{record} must be a mapping")
    unknown = set(payload) - allowed
    if unknown:
        _fail(f"{record} carries unknown fields: {sorted(unknown)}")
    missing = allowed - set(payload)
    if missing:
        _fail(f"{record} is missing fields: {sorted(missing)}")
    return payload


@dataclass(frozen=True)
class Provenance:
    """Where an inferred agency state came from (roadmap §7 model)."""

    source_type: str
    source_id: str
    event_id: str = ""

    def __post_init__(self) -> None:
        if self.source_type not in SOURCE_TYPES:
            _fail(f"source_type must be one of {sorted(SOURCE_TYPES)}")
        object.__setattr__(
            self, "source_id", _text(self.source_id, "source_id", MAX_SOURCE_ID_CHARS)
        )
        object.__setattr__(
            self,
            "event_id",
            _text(self.event_id, "event_id", MAX_EVENT_ID_CHARS, required=False),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.source_type,
            "source_id": self.source_id,
            "event_id": self.event_id,
        }

    @classmethod
    def from_dict(cls, payload: Any) -> "Provenance":
        data = _check_keys(payload, {"type", "source_id", "event_id"}, "provenance")
        return cls(
            source_type=data["type"],
            source_id=data["source_id"],
            event_id=data["event_id"],
        )


def _provenance(value: Any) -> Provenance:
    if isinstance(value, Provenance):
        return value
    return Provenance.from_dict(value)


@dataclass(frozen=True)
class SelfClaim:
    """One bounded self-model claim (Phase 1 consumes this contract)."""

    claim_id: str
    owner_entity_id: str
    domain: str
    key: str
    statement: str
    confidence: float
    source: Provenance
    first_seen_at: str
    last_confirmed_at: str = ""

    def __post_init__(self) -> None:
        _canonical_uuid(self.claim_id, "claim_id")
        _owner(self.owner_entity_id)
        object.__setattr__(self, "domain", _slug(self.domain, "domain"))
        object.__setattr__(self, "key", _slug(self.key, "key"))
        object.__setattr__(
            self, "statement", _text(self.statement, "statement", MAX_STATEMENT_CHARS)
        )
        object.__setattr__(self, "confidence", _unit(self.confidence, "confidence"))
        object.__setattr__(self, "source", _provenance(self.source))
        _timestamp(self.first_seen_at, "first_seen_at")
        _timestamp(self.last_confirmed_at, "last_confirmed_at", empty=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            "owner_entity_id": self.owner_entity_id,
            "domain": self.domain,
            "key": self.key,
            "statement": self.statement,
            "confidence": self.confidence,
            "source": self.source.to_dict(),
            "first_seen_at": self.first_seen_at,
            "last_confirmed_at": self.last_confirmed_at,
        }

    @classmethod
    def from_dict(cls, payload: Any) -> "SelfClaim":
        data = _check_keys(payload, set(cls.__dataclass_fields__), "self claim")
        return cls(**{**data, "source": _provenance(data["source"])})


@dataclass(frozen=True)
class DriveState:
    """One intrinsic drive's bounded state (Phase 2 consumes this)."""

    drive_id: str
    owner_entity_id: str
    enabled: bool
    baseline: float
    activation: float
    satisfaction: float
    source: Provenance
    updated_at: str
    cooldown_until: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "drive_id", _slug(self.drive_id, "drive_id"))
        _owner(self.owner_entity_id)
        if not isinstance(self.enabled, bool):
            _fail("enabled must be a boolean")
        for name in ("baseline", "activation", "satisfaction"):
            object.__setattr__(self, name, _unit(getattr(self, name), name))
        object.__setattr__(self, "source", _provenance(self.source))
        _timestamp(self.updated_at, "updated_at")
        _timestamp(self.cooldown_until, "cooldown_until", empty=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "drive_id": self.drive_id,
            "owner_entity_id": self.owner_entity_id,
            "enabled": self.enabled,
            "baseline": self.baseline,
            "activation": self.activation,
            "satisfaction": self.satisfaction,
            "source": self.source.to_dict(),
            "updated_at": self.updated_at,
            "cooldown_until": self.cooldown_until,
        }

    @classmethod
    def from_dict(cls, payload: Any) -> "DriveState":
        data = _check_keys(payload, set(cls.__dataclass_fields__), "drive state")
        return cls(**{**data, "source": _provenance(data["source"])})


@dataclass(frozen=True)
class ReflectionRecord:
    """A structured reflection conclusion — never hidden reasoning (§4.3)."""

    reflection_id: str
    owner_entity_id: str
    trigger: str
    subject_ref: str
    observed_outcome: str
    source: Provenance
    created_at: str
    predicted_success: float | None = None
    lessons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _canonical_uuid(self.reflection_id, "reflection_id")
        _owner(self.owner_entity_id)
        object.__setattr__(self, "trigger", _slug(self.trigger, "trigger"))
        object.__setattr__(
            self, "subject_ref", _text(self.subject_ref, "subject_ref", MAX_REF_CHARS)
        )
        if self.observed_outcome not in REFLECTION_OUTCOMES:
            _fail(f"observed_outcome must be one of {sorted(REFLECTION_OUTCOMES)}")
        object.__setattr__(self, "source", _provenance(self.source))
        _timestamp(self.created_at, "created_at")
        if self.predicted_success is not None:
            object.__setattr__(
                self,
                "predicted_success",
                _unit(self.predicted_success, "predicted_success"),
            )
        if not isinstance(self.lessons, (list, tuple)) or len(self.lessons) > MAX_LESSONS:
            _fail(f"lessons must be a list of at most {MAX_LESSONS} entries")
        object.__setattr__(
            self,
            "lessons",
            tuple(_text(lesson, "lesson", MAX_LESSON_CHARS) for lesson in self.lessons),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "reflection_id": self.reflection_id,
            "owner_entity_id": self.owner_entity_id,
            "trigger": self.trigger,
            "subject_ref": self.subject_ref,
            "observed_outcome": self.observed_outcome,
            "source": self.source.to_dict(),
            "created_at": self.created_at,
            "predicted_success": self.predicted_success,
            "lessons": list(self.lessons),
        }

    @classmethod
    def from_dict(cls, payload: Any) -> "ReflectionRecord":
        data = _check_keys(payload, set(cls.__dataclass_fields__), "reflection record")
        return cls(**{**data, "source": _provenance(data["source"])})


@dataclass(frozen=True)
class CuriosityQuestion:
    """One bounded question on the curiosity frontier (Phase 4)."""

    question_id: str
    owner_entity_id: str
    question: str
    status: str
    novelty: float
    uncertainty: float
    relevance: float
    expected_value: float
    cost: float
    risk_class: int
    source: Provenance
    created_at: str
    attempts: int = 0
    last_investigated_at: str = ""

    def __post_init__(self) -> None:
        _canonical_uuid(self.question_id, "question_id")
        _owner(self.owner_entity_id)
        object.__setattr__(
            self, "question", _text(self.question, "question", MAX_TEXT_CHARS)
        )
        if self.status not in CURIOSITY_STATUSES:
            _fail(f"status must be one of {sorted(CURIOSITY_STATUSES)}")
        for name in ("novelty", "uncertainty", "relevance", "expected_value", "cost"):
            object.__setattr__(self, name, _unit(getattr(self, name), name))
        object.__setattr__(self, "risk_class", _risk_class(self.risk_class))
        object.__setattr__(self, "source", _provenance(self.source))
        _timestamp(self.created_at, "created_at")
        object.__setattr__(self, "attempts", _count(self.attempts, "attempts"))
        _timestamp(self.last_investigated_at, "last_investigated_at", empty=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "question_id": self.question_id,
            "owner_entity_id": self.owner_entity_id,
            "question": self.question,
            "status": self.status,
            "novelty": self.novelty,
            "uncertainty": self.uncertainty,
            "relevance": self.relevance,
            "expected_value": self.expected_value,
            "cost": self.cost,
            "risk_class": self.risk_class,
            "source": self.source.to_dict(),
            "created_at": self.created_at,
            "attempts": self.attempts,
            "last_investigated_at": self.last_investigated_at,
        }

    @classmethod
    def from_dict(cls, payload: Any) -> "CuriosityQuestion":
        data = _check_keys(payload, set(cls.__dataclass_fields__), "curiosity question")
        return cls(**{**data, "source": _provenance(data["source"])})


@dataclass(frozen=True)
class ActionProposal:
    """A proposed action awaiting a deterministic policy decision (§12)."""

    proposal_id: str
    owner_entity_id: str
    action: str
    summary: str
    risk_class: int
    estimated_cost: str
    source: Provenance
    created_at: str
    drive_ref: str = ""
    expires_at: str = ""

    def __post_init__(self) -> None:
        _canonical_uuid(self.proposal_id, "proposal_id")
        _owner(self.owner_entity_id)
        object.__setattr__(self, "action", _slug(self.action, "action"))
        object.__setattr__(self, "summary", _text(self.summary, "summary", MAX_TEXT_CHARS))
        object.__setattr__(self, "risk_class", _risk_class(self.risk_class))
        if self.estimated_cost not in ESTIMATED_COSTS:
            _fail(f"estimated_cost must be one of {sorted(ESTIMATED_COSTS)}")
        object.__setattr__(self, "source", _provenance(self.source))
        _timestamp(self.created_at, "created_at")
        object.__setattr__(
            self, "drive_ref", _text(self.drive_ref, "drive_ref", MAX_REF_CHARS, required=False)
        )
        _timestamp(self.expires_at, "expires_at", empty=True)

    def to_dict(self) -> dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "owner_entity_id": self.owner_entity_id,
            "action": self.action,
            "summary": self.summary,
            "risk_class": self.risk_class,
            "estimated_cost": self.estimated_cost,
            "source": self.source.to_dict(),
            "created_at": self.created_at,
            "drive_ref": self.drive_ref,
            "expires_at": self.expires_at,
        }

    @classmethod
    def from_dict(cls, payload: Any) -> "ActionProposal":
        data = _check_keys(payload, set(cls.__dataclass_fields__), "action proposal")
        return cls(**{**data, "source": _provenance(data["source"])})


@dataclass(frozen=True)
class PolicyDecision:
    """The deterministic gate's verdict on one proposal (Phase 5 shape)."""

    proposal_id: str
    owner_entity_id: str
    decision: str
    reason_code: str
    risk_class: int
    budget_remaining: bool
    policy_version: int
    decided_at: str

    def __post_init__(self) -> None:
        _canonical_uuid(self.proposal_id, "proposal_id")
        _owner(self.owner_entity_id)
        if self.decision not in POLICY_DECISIONS:
            _fail(f"decision must be one of {sorted(POLICY_DECISIONS)}")
        object.__setattr__(self, "reason_code", _slug(self.reason_code, "reason_code"))
        object.__setattr__(self, "risk_class", _risk_class(self.risk_class))
        if not isinstance(self.budget_remaining, bool):
            _fail("budget_remaining must be a boolean")
        if (
            isinstance(self.policy_version, bool)
            or not isinstance(self.policy_version, int)
            or self.policy_version < 1
        ):
            _fail("policy_version must be a positive integer")
        _timestamp(self.decided_at, "decided_at")

    def to_dict(self) -> dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "owner_entity_id": self.owner_entity_id,
            "decision": self.decision,
            "reason_code": self.reason_code,
            "risk_class": self.risk_class,
            "budget_remaining": self.budget_remaining,
            "policy_version": self.policy_version,
            "decided_at": self.decided_at,
        }

    @classmethod
    def from_dict(cls, payload: Any) -> "PolicyDecision":
        data = _check_keys(payload, set(cls.__dataclass_fields__), "policy decision")
        return cls(**data)


@dataclass(frozen=True)
class ActionResult:
    """The recorded outcome of one decided proposal."""

    result_id: str
    proposal_id: str
    owner_entity_id: str
    status: str
    summary: str
    source: Provenance
    completed_at: str

    def __post_init__(self) -> None:
        _canonical_uuid(self.result_id, "result_id")
        _canonical_uuid(self.proposal_id, "proposal_id")
        _owner(self.owner_entity_id)
        if self.status not in ACTION_RESULT_STATUSES:
            _fail(f"status must be one of {sorted(ACTION_RESULT_STATUSES)}")
        object.__setattr__(self, "summary", _text(self.summary, "summary", MAX_TEXT_CHARS))
        object.__setattr__(self, "source", _provenance(self.source))
        _timestamp(self.completed_at, "completed_at")

    def to_dict(self) -> dict[str, Any]:
        return {
            "result_id": self.result_id,
            "proposal_id": self.proposal_id,
            "owner_entity_id": self.owner_entity_id,
            "status": self.status,
            "summary": self.summary,
            "source": self.source.to_dict(),
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_dict(cls, payload: Any) -> "ActionResult":
        data = _check_keys(payload, set(cls.__dataclass_fields__), "action result")
        return cls(**{**data, "source": _provenance(data["source"])})


@dataclass(frozen=True)
class AgencyCycleReport:
    """Aggregate, content-free summary of one agency cycle (Phase 6)."""

    cycle_id: str
    owner_entity_id: str
    status: str
    started_at: str
    finished_at: str
    source: Provenance
    proposals_considered: int = 0
    decisions_allow: int = 0
    decisions_confirmation: int = 0
    decisions_deny: int = 0
    actions_executed: int = 0
    actions_failed: int = 0

    def __post_init__(self) -> None:
        _canonical_uuid(self.cycle_id, "cycle_id")
        _owner(self.owner_entity_id)
        if self.status not in CYCLE_STATUSES:
            _fail(f"status must be one of {sorted(CYCLE_STATUSES)}")
        _timestamp(self.started_at, "started_at")
        _timestamp(self.finished_at, "finished_at")
        object.__setattr__(self, "source", _provenance(self.source))
        for name in (
            "proposals_considered",
            "decisions_allow",
            "decisions_confirmation",
            "decisions_deny",
            "actions_executed",
            "actions_failed",
        ):
            object.__setattr__(self, name, _count(getattr(self, name), name))
        decided = self.decisions_allow + self.decisions_confirmation + self.decisions_deny
        if decided > self.proposals_considered:
            _fail("decisions cannot exceed proposals considered")
        if self.actions_executed + self.actions_failed > self.decisions_allow:
            _fail("executed/failed actions cannot exceed allowed decisions")

    def to_dict(self) -> dict[str, Any]:
        return {
            "cycle_id": self.cycle_id,
            "owner_entity_id": self.owner_entity_id,
            "status": self.status,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "source": self.source.to_dict(),
            "proposals_considered": self.proposals_considered,
            "decisions_allow": self.decisions_allow,
            "decisions_confirmation": self.decisions_confirmation,
            "decisions_deny": self.decisions_deny,
            "actions_executed": self.actions_executed,
            "actions_failed": self.actions_failed,
        }

    @classmethod
    def from_dict(cls, payload: Any) -> "AgencyCycleReport":
        data = _check_keys(payload, set(cls.__dataclass_fields__), "agency cycle report")
        return cls(**{**data, "source": _provenance(data["source"])})


__all__ = [
    "AGENCY_CONTRACTS_VERSION",
    "SOURCE_TYPES",
    "AgencyContractError",
    "Provenance",
    "SelfClaim",
    "DriveState",
    "ReflectionRecord",
    "CuriosityQuestion",
    "ActionProposal",
    "PolicyDecision",
    "ActionResult",
    "AgencyCycleReport",
]
