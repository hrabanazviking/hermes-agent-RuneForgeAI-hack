"""Curiosity detail reconciliation (Self-Aware Agency roadmap §10).

Emergent Agency Phase 4 (Slice 94) already built the curiosity
frontier: a versioned ``entity/curiosity.yaml`` store on the Phase 0
``CuriosityQuestion`` contract, scored by relevance x uncertainty x
novelty x expected_value x (1 - cost) x (1 - risk penalty). What it
does not carry is this roadmap's own §10 layer, which is therefore
built here as a reconciliation, not a second curiosity engine:

- §10.2 ``origin``: every assessment names one origin from the
  §10.4 source list. :func:`derive_origin` maps a question's
  provenance source type onto that list deterministically; an
  explicit origin may be supplied instead and is validated;
- §10.3 scoring: ``priority`` is the §10.3 product — uncertainty x
  usefulness x novelty x identity_relevance x affordability, all
  unit-interval — where usefulness defaults to the question's
  Phase 4 ``expected_value`` and affordability is ``1 - cost``.
  ``identity_relevance`` has no Phase 4 field, so the caller
  supplies it explicitly. The stored priority must agree with the
  pure function on read (the Slice 104/107 agreement pattern);
- §10.5 budget block: investigations/day, local token budget/day,
  cloud budget/day (default zero — cloud research stays refused
  until explicitly configured), max minutes per investigation, and
  a usefulness floor, all evaluated deterministically by
  :meth:`CuriosityDetailService.evaluate_budget`. Evaluation is
  read-only: it spends nothing and investigates nothing;
- §10.6 outcomes: an investigation outcome is one of the seven
  named kinds, with ``unknown`` a valid outcome. An outcome is
  recorded beside the assessment in this module's own bounded log;
  a ``deeper_question`` outcome must name the deeper question, and
  an ``uncertainty_reduced`` outcome must carry a strictly lower
  new uncertainty than the question it closes.

This module imports the Phase 4 store's contract only — it never
writes the curiosity store, creates no goals, updates no
self-model, and performs no investigation. Only explicit
``record_assessment`` / ``record_outcome`` calls append to its own
log. Disabled by default.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hermes_constants import get_hermes_home, mkdir_under_hermes_home

from .agency_contracts import CuriosityQuestion
from .context_packet import ContextItem
from .identity import IdentityError, IdentityStore, _as_bool

DETAIL_VERSION = 1
DEFAULT_LOG_PATH = Path("entity") / "curiosity_details.jsonl"
DEFAULT_LOG_LIMIT = 200
MAX_LOG_BYTES = 4 * 1024 * 1024
MAX_TEXT_CHARS = 500
MAX_QUESTION_CHARS = 1000

# §10.5 defaults, straight from the roadmap's example configuration.
DEFAULT_INVESTIGATIONS_PER_DAY = 8
DEFAULT_LOCAL_TOKEN_BUDGET = 50000
DEFAULT_CLOUD_BUDGET_USD = 0.0
DEFAULT_MAX_MINUTES = 20
DEFAULT_USEFULNESS_FLOOR = 0.35

# §10.4 curiosity sources, plus ``discrepancy`` from the §10.2 example.
ORIGINS = frozenset({
    "discrepancy", "contradiction", "unknown_world_fact", "failed_goal",
    "unexplained_success", "user_feedback", "self_model_uncertainty",
    "relationship_uncertainty", "new_project", "knowledge_gap",
    "verdandi_event", "wyrd_state",
})
# Deterministic provenance -> §10 origin mapping.
_ORIGIN_BY_SOURCE_TYPE = {
    "user_explicit": "user_feedback",
    "goal": "failed_goal",
    "relationship": "relationship_uncertainty",
    "world_fact": "unknown_world_fact",
    "reflection": "self_model_uncertainty",
    "identity": "self_model_uncertainty",
    "cognition_telemetry": "verdandi_event",
    "curiosity": "knowledge_gap",
    "drive": "knowledge_gap",
    "memory_record": "knowledge_gap",
    "tool_result": "discrepancy",
    "system_observation": "discrepancy",
}

# §10.6 investigation outcomes; "unknown" is a valid outcome.
OUTCOMES = frozenset({
    "answered", "uncertainty_reduced", "knowledge_candidate",
    "goal_proposal", "self_model_update", "deeper_question",
    "evidence_insufficient", "unknown",
})

_ASSESSMENT_FIELDS = {
    "detail_version", "kind", "record_id", "question_id",
    "owner_entity_id", "recorded_at", "question", "origin",
    "novelty", "uncertainty", "usefulness", "identity_relevance",
    "affordability", "priority", "status",
}
_OUTCOME_FIELDS = {
    "detail_version", "kind", "record_id", "question_id",
    "owner_entity_id", "recorded_at", "outcome", "summary",
    "new_uncertainty", "deeper_question",
}

try:
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None
try:
    import msvcrt
except ImportError:  # pragma: no cover
    msvcrt = None


class CuriosityDetailError(RuntimeError):
    """A curiosity detail record cannot be safely built or read."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


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


def derive_origin(question: CuriosityQuestion) -> str:
    """The §10 origin of a Phase 4 question, from its provenance."""
    return _ORIGIN_BY_SOURCE_TYPE.get(
        question.source.source_type, "knowledge_gap")


def curiosity_priority(*, uncertainty: float, usefulness: float,
                       novelty: float, identity_relevance: float,
                       affordability: float) -> float:
    """The §10.3 score — a pure product of unit-interval factors."""
    score = (float(uncertainty) * float(usefulness) * float(novelty)
             * float(identity_relevance) * float(affordability))
    return round(min(1.0, max(0.0, score)), 6)


class CuriosityDetailService:
    """The §10 assessment/budget/outcome layer beside the Phase 4 store."""

    def __init__(self, ctx) -> None:
        self._ctx = ctx
        self._identity = IdentityStore(ctx)

    def enabled(self) -> bool:
        return self._identity.enabled() and _as_bool(
            self._ctx.get_config("curiosity_detail_enabled", False), False
        )

    def _limit(self) -> int:
        try:
            value = int(self._ctx.get_config(
                "curiosity_detail_log_limit", DEFAULT_LOG_LIMIT))
        except (TypeError, ValueError):
            value = DEFAULT_LOG_LIMIT
        return min(500, max(10, value))

    def path(self) -> Path:
        home = get_hermes_home().resolve()
        configured = Path(str(self._ctx.get_config(
            "curiosity_detail_log_path", str(DEFAULT_LOG_PATH))))
        if configured.is_absolute():
            configured = DEFAULT_LOG_PATH
        lexical = home / configured
        candidate = lexical.resolve()
        if not candidate.is_relative_to(home):
            lexical = home / DEFAULT_LOG_PATH
            candidate = lexical.resolve()
        if not candidate.is_relative_to(home):
            raise CuriosityDetailError(
                "curiosity detail log path resolves outside the profile")
        if lexical.is_symlink():
            return lexical
        return candidate

    # -- §10.5 budget configuration ----------------------------------------
    def budget(self) -> dict[str, Any]:
        """The §10.5 budget block, clamped, with the roadmap defaults."""
        def _int(key, default, low, high):
            try:
                value = int(self._ctx.get_config(key, default))
            except (TypeError, ValueError):
                value = default
            return min(high, max(low, value))

        def _float(key, default, low, high):
            try:
                value = float(self._ctx.get_config(key, default))
            except (TypeError, ValueError):
                value = default
            return min(high, max(low, value))

        return {
            "investigations_per_day": _int(
                "curiosity_detail_investigations_per_day",
                DEFAULT_INVESTIGATIONS_PER_DAY, 0, 100),
            "local_token_budget_per_day": _int(
                "curiosity_detail_local_token_budget_per_day",
                DEFAULT_LOCAL_TOKEN_BUDGET, 0, 1_000_000),
            "cloud_budget_usd_per_day": _float(
                "curiosity_detail_cloud_budget_usd_per_day",
                DEFAULT_CLOUD_BUDGET_USD, 0.0, 10_000.0),
            "max_minutes_per_investigation": _int(
                "curiosity_detail_max_minutes_per_investigation",
                DEFAULT_MAX_MINUTES, 1, 240),
            "usefulness_floor": _float(
                "curiosity_detail_usefulness_floor",
                DEFAULT_USEFULNESS_FLOOR, 0.0, 1.0),
        }

    # -- §10.2/§10.3 assessment ---------------------------------------------
    def assess(self, question: CuriosityQuestion, *,
               origin: str | None = None,
               usefulness: float | None = None,
               identity_relevance: float,
               recorded_at: str | None = None) -> dict[str, Any]:
        """Build a §10 assessment of a Phase 4 question. Pure."""
        if not isinstance(question, CuriosityQuestion):
            raise CuriosityDetailError(
                "assessment must derive from a CuriosityQuestion record")
        resolved_origin = derive_origin(question) if origin is None else origin
        if resolved_origin not in ORIGINS:
            raise CuriosityDetailError("curiosity origin is not a §10.4 source")
        resolved_usefulness = (
            question.expected_value if usefulness is None else usefulness)
        if not _unit(resolved_usefulness) or not _unit(identity_relevance):
            raise CuriosityDetailError(
                "curiosity usefulness/identity_relevance must be unit-interval")
        affordability = round(1.0 - float(question.cost), 6)
        assessment = {
            "detail_version": DETAIL_VERSION,
            "kind": "assessment",
            "record_id": str(uuid.uuid4()),
            "question_id": question.question_id,
            "owner_entity_id": question.owner_entity_id,
            "recorded_at": recorded_at or _now(),
            "question": question.question,
            "origin": resolved_origin,
            "novelty": float(question.novelty),
            "uncertainty": float(question.uncertainty),
            "usefulness": float(resolved_usefulness),
            "identity_relevance": float(identity_relevance),
            "affordability": affordability,
            "priority": curiosity_priority(
                uncertainty=float(question.uncertainty),
                usefulness=float(resolved_usefulness),
                novelty=float(question.novelty),
                identity_relevance=float(identity_relevance),
                affordability=affordability),
            "status": question.status,
        }
        self._validate(assessment, question.owner_entity_id)
        return assessment

    # -- §10.5 budget evaluation ---------------------------------------------
    def evaluate_budget(self, assessment: dict[str, Any], *,
                        investigations_today: int,
                        local_tokens_today: int = 0,
                        cloud_requested: bool = False,
                        estimated_minutes: int | None = None
                        ) -> dict[str, Any]:
        """Decide whether one investigation fits the §10.5 budget.

        Pure and deterministic; spends nothing. Cloud is refused
        whenever the configured cloud budget is zero (the default),
        which is the roadmap's anti-rabbit-hole default.
        """
        if not isinstance(assessment, dict) \
                or assessment.get("kind") != "assessment":
            raise CuriosityDetailError("budget evaluation needs an assessment")
        for name, value in (("investigations_today", investigations_today),
                            ("local_tokens_today", local_tokens_today)):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise CuriosityDetailError(f"{name} is invalid")
        if estimated_minutes is not None and (
                isinstance(estimated_minutes, bool)
                or not isinstance(estimated_minutes, int)
                or estimated_minutes < 0):
            raise CuriosityDetailError("estimated_minutes is invalid")
        budget = self.budget()
        reasons: list[str] = []
        if float(assessment["usefulness"]) < budget["usefulness_floor"]:
            reasons.append("usefulness_below_floor")
        if investigations_today >= budget["investigations_per_day"]:
            reasons.append("investigations_per_day_exhausted")
        if local_tokens_today >= budget["local_token_budget_per_day"]:
            reasons.append("local_token_budget_exhausted")
        if cloud_requested and budget["cloud_budget_usd_per_day"] <= 0.0:
            reasons.append("cloud_budget_zero")
        if estimated_minutes is not None and estimated_minutes \
                > budget["max_minutes_per_investigation"]:
            reasons.append("investigation_too_long")
        return {
            "allowed": not reasons,
            "reasons": reasons or ["within_budget"],
            "budget": budget,
        }

    # -- §10.6 outcomes --------------------------------------------------------
    def build_outcome(self, question: CuriosityQuestion, *,
                      outcome: str, summary: str,
                      new_uncertainty: float | None = None,
                      deeper_question: str = "",
                      recorded_at: str | None = None) -> dict[str, Any]:
        """Build a §10.6 outcome record for a Phase 4 question. Pure."""
        if not isinstance(question, CuriosityQuestion):
            raise CuriosityDetailError(
                "outcome must derive from a CuriosityQuestion record")
        if outcome not in OUTCOMES:
            raise CuriosityDetailError("curiosity outcome is not a §10.6 kind")
        if not isinstance(summary, str) or not summary.strip() \
                or len(summary.strip()) > MAX_TEXT_CHARS:
            raise CuriosityDetailError("curiosity outcome summary is invalid")
        if not isinstance(deeper_question, str) \
                or len(deeper_question.strip()) > MAX_QUESTION_CHARS:
            raise CuriosityDetailError("curiosity deeper question is invalid")
        deeper_question = deeper_question.strip()
        if outcome == "deeper_question" and not deeper_question:
            raise CuriosityDetailError(
                "a deeper_question outcome must name the deeper question")
        if new_uncertainty is not None:
            if not _unit(new_uncertainty):
                raise CuriosityDetailError(
                    "curiosity new_uncertainty must be unit-interval")
            if outcome == "uncertainty_reduced" and not (
                    float(new_uncertainty) < float(question.uncertainty)):
                raise CuriosityDetailError(
                    "uncertainty_reduced requires a strictly lower uncertainty")
        elif outcome == "uncertainty_reduced":
            raise CuriosityDetailError(
                "uncertainty_reduced requires the new uncertainty")
        record = {
            "detail_version": DETAIL_VERSION,
            "kind": "outcome",
            "record_id": str(uuid.uuid4()),
            "question_id": question.question_id,
            "owner_entity_id": question.owner_entity_id,
            "recorded_at": recorded_at or _now(),
            "outcome": outcome,
            "summary": summary.strip(),
            "new_uncertainty": (
                None if new_uncertainty is None else float(new_uncertainty)),
            "deeper_question": deeper_question,
        }
        self._validate(record, question.owner_entity_id)
        return record

    # -- bounded log ------------------------------------------------------------
    def record_assessment(self, assessment: dict[str, Any]) -> dict[str, Any]:
        if not self.enabled():
            raise CuriosityDetailError("curiosity detail is disabled")
        owner = self._identity.read().entity_id
        self._validate(assessment, owner)
        if assessment.get("kind") != "assessment":
            raise CuriosityDetailError("record is not an assessment")
        self._append(assessment)
        return assessment

    def record_outcome(self, outcome: dict[str, Any]) -> dict[str, Any]:
        if not self.enabled():
            raise CuriosityDetailError("curiosity detail is disabled")
        owner = self._identity.read().entity_id
        self._validate(outcome, owner)
        if outcome.get("kind") != "outcome":
            raise CuriosityDetailError("record is not an outcome")
        self._append(outcome)
        return outcome

    def records(self, *, limit: int = 500) -> list[dict[str, Any]]:
        owner = self._identity.read().entity_id
        path = self.path()
        if path.is_symlink():
            raise CuriosityDetailError(
                "curiosity detail log must not be a symbolic link")
        if not path.is_file():
            return []
        if path.stat().st_size > MAX_LOG_BYTES:
            raise CuriosityDetailError(
                "curiosity detail log exceeds its size limit")
        out: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except ValueError as exc:
                raise CuriosityDetailError(
                    "curiosity detail log is malformed") from exc
            self._validate(payload, owner)
            out.append(payload)
        return out[-max(1, min(500, limit)):]

    def latest_assessment(self) -> dict[str, Any] | None:
        rows = [r for r in self.records(limit=500) if r["kind"] == "assessment"]
        return rows[-1] if rows else None

    def outcomes_for(self, question_id: str) -> list[dict[str, Any]]:
        if not _canonical_uuid(question_id):
            raise CuriosityDetailError("question_id is invalid")
        return [r for r in self.records(limit=500)
                if r["kind"] == "outcome" and r["question_id"] == question_id]

    @staticmethod
    def _validate(payload: Any, owner: str) -> None:
        if not isinstance(payload, dict):
            raise CuriosityDetailError("curiosity detail record is invalid")
        if payload.get("detail_version") != DETAIL_VERSION:
            raise CuriosityDetailError("curiosity detail version is unsupported")
        if not _canonical_uuid(payload.get("record_id")) \
                or not _canonical_uuid(payload.get("question_id")):
            raise CuriosityDetailError("curiosity detail id is invalid")
        if payload.get("owner_entity_id") != owner:
            raise CuriosityDetailError(
                "curiosity detail owner does not match entity identity")
        if not _timestamp_ok(payload.get("recorded_at")):
            raise CuriosityDetailError("curiosity detail recorded_at is invalid")
        kind = payload.get("kind")
        if kind == "assessment":
            if set(payload) != _ASSESSMENT_FIELDS:
                raise CuriosityDetailError("curiosity assessment fields are invalid")
            if payload.get("origin") not in ORIGINS:
                raise CuriosityDetailError("curiosity origin is invalid")
            for field in ("novelty", "uncertainty", "usefulness",
                          "identity_relevance", "affordability"):
                if not _unit(payload.get(field)):
                    raise CuriosityDetailError(
                        f"curiosity assessment {field} is invalid")
            question = payload.get("question")
            if not isinstance(question, str) or not question.strip() \
                    or len(question) > MAX_QUESTION_CHARS:
                raise CuriosityDetailError("curiosity assessment question is invalid")
            status = payload.get("status")
            if status not in ("open", "investigating", "resolved",
                              "deferred", "abandoned", "invalidated"):
                raise CuriosityDetailError("curiosity assessment status is invalid")
            expected = curiosity_priority(
                uncertainty=float(payload["uncertainty"]),
                usefulness=float(payload["usefulness"]),
                novelty=float(payload["novelty"]),
                identity_relevance=float(payload["identity_relevance"]),
                affordability=float(payload["affordability"]))
            if payload.get("priority") != expected:
                raise CuriosityDetailError(
                    "curiosity priority disagrees with the §10.3 function")
        elif kind == "outcome":
            if set(payload) != _OUTCOME_FIELDS:
                raise CuriosityDetailError("curiosity outcome fields are invalid")
            if payload.get("outcome") not in OUTCOMES:
                raise CuriosityDetailError("curiosity outcome kind is invalid")
            summary = payload.get("summary")
            if not isinstance(summary, str) or not summary.strip() \
                    or len(summary) > MAX_TEXT_CHARS:
                raise CuriosityDetailError("curiosity outcome summary is invalid")
            new_uncertainty = payload.get("new_uncertainty")
            if new_uncertainty is not None and not _unit(new_uncertainty):
                raise CuriosityDetailError(
                    "curiosity outcome new_uncertainty is invalid")
            deeper = payload.get("deeper_question")
            if not isinstance(deeper, str) or len(deeper) > MAX_QUESTION_CHARS:
                raise CuriosityDetailError(
                    "curiosity outcome deeper_question is invalid")
            if payload["outcome"] == "deeper_question" and not deeper.strip():
                raise CuriosityDetailError(
                    "a deeper_question outcome must name the deeper question")
        else:
            raise CuriosityDetailError("curiosity detail kind is invalid")

    def _append(self, record: dict[str, Any]) -> None:
        path = self.path()
        if path.is_symlink():
            raise CuriosityDetailError(
                "curiosity detail log must not be a symbolic link")
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
                    raise CuriosityDetailError(
                        "curiosity detail log exceeds its size limit")
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


class CuriosityDetailBridge:
    """Surface the latest §10 assessment, when it clears the floor.

    Content-bearing only. No session hook — assessments and
    outcomes are written only by explicit calls.
    """

    def __init__(self, ctx) -> None:
        self._ctx = ctx
        self._service = CuriosityDetailService(ctx)

    def hooks(self):
        return ()

    def packet_items(self, session_id: str, user_message: Any = "") -> list[ContextItem]:
        if not _as_bool(
            self._ctx.get_config("curiosity_detail_enabled", False), False
        ):
            return []
        try:
            latest = self._service.latest_assessment()
        except (IdentityError, CuriosityDetailError, OSError):
            return []
        if latest is None:
            return []
        return [ContextItem(
            section="current_state",
            content=(
                f"Curiosity (§10, origin {latest['origin']}, "
                f"priority {latest['priority']:.2f}): {latest['question']}"
            ),
            source="curiosity_detail",
            record_id=latest["record_id"],
            priority=float(latest["priority"]),
            updated_at=_epoch(latest["recorded_at"]),
        )]


__all__ = [
    "DETAIL_VERSION",
    "DEFAULT_LOG_PATH",
    "ORIGINS",
    "OUTCOMES",
    "CuriosityDetailError",
    "CuriosityDetailService",
    "CuriosityDetailBridge",
    "derive_origin",
    "curiosity_priority",
]
