"""Agency-cycle reconciliation (Self-Aware Agency roadmap §12).

Emergent Agency Phase 6 (Slice 96) already built the agency
orchestrator: one bounded cycle per explicit invocation over the
identity/continuity, autonomy, self-model, drives, curiosity, and
goals stores, with policy-checked candidates, registered-executor
execution, verification, a bounded journal, post-execution
reflection, and a content-free cycle report. What it does not
carry is this roadmap's own §12 shape, which is therefore built
here as a reconciliation, not a second orchestrator:

- the twelve §12 steps are named in canonical order
  (:data:`CYCLE_STEPS`), and :func:`step_coverage` states honestly
  how the Phase 6 cycle covers each: covered (observe, policy
  check, act-or-request-approval, verify, record), partial
  (orient — discrepancies live in the layered self-model and the
  orchestrator does not call it; generate — no self-improvement
  candidate kind; rank — a single deterministic score, not the
  §12 factors; reflect — only when the cycle executed something),
  and deferred (reflect-if-needed before generation, self-model
  update, and the content-free Verðandi event emission of §14);
- §12 ranking factors: :func:`rank_score` is the pure seven-factor
  function §12 names (value, relevance, urgency, expected benefit,
  cost, uncertainty, reversibility) — the positive factors averaged,
  discounted by cost and uncertainty — supplied here for later
  wiring; the orchestrator's own scoring is unchanged;
- the hard maximum-actions-per-cycle bound: a cycle trace may be
  recorded only when its executed count is within the configured
  bound (``agency_cycle_detail_max_actions``, 1-10, default 3, the
  Phase 6 candidate-cap default), and a stored trace whose
  ``within_bound`` flag disagrees with that pure check is refused
  on read;
- cycle traces: one explicit record per cycle in this module's own
  bounded log — the cycle id, a slug trigger, the twelve step
  statuses in canonical order, and the proposed/executed counts.
  Recording is explicit only: no hook, loop, scheduler, or
  turn-path caller records a trace, and this module runs no cycle
  and executes nothing — the Phase 6 orchestrator remains the
  only cycle.

Disabled by default.
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

TRACE_VERSION = 1
DEFAULT_LOG_PATH = Path("entity") / "agency_cycle_traces.jsonl"
DEFAULT_LOG_LIMIT = 200
MAX_LOG_BYTES = 4 * 1024 * 1024
DEFAULT_MAX_ACTIONS = 3

# The twelve §12 steps, in canonical order.
CYCLE_STEPS = (
    "observe",
    "orient",
    "reflect_if_needed",
    "generate_candidates",
    "rank_candidates",
    "check_autonomy_policy",
    "act_or_request_approval",
    "verify_outcome",
    "record_experience",
    "reflect",
    "update_self_model",
    "emit_verdandi_events",
)

STEP_STATUSES = frozenset({"completed", "skipped", "blocked", "deferred"})

# How the Phase 6 orchestrator (Slice 96) covers each §12 step.
STEP_COVERAGE = {
    "observe": "covered",
    "orient": "partial",
    "reflect_if_needed": "deferred",
    "generate_candidates": "partial",
    "rank_candidates": "partial",
    "check_autonomy_policy": "covered",
    "act_or_request_approval": "covered",
    "verify_outcome": "covered",
    "record_experience": "covered",
    "reflect": "partial",
    "update_self_model": "deferred",
    "emit_verdandi_events": "deferred",
}

# The seven §12 ranking factors.
RANKING_FACTORS = (
    "value", "relevance", "urgency", "expected_benefit",
    "cost", "uncertainty", "reversibility",
)
_POSITIVE_FACTORS = (
    "value", "relevance", "urgency", "expected_benefit", "reversibility",
)

_TRACE_FIELDS = {
    "trace_version", "kind", "record_id", "cycle_id",
    "owner_entity_id", "trigger", "recorded_at", "steps",
    "actions_proposed", "actions_executed", "max_actions",
    "within_bound",
}

try:
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None
try:
    import msvcrt
except ImportError:  # pragma: no cover
    msvcrt = None


class AgencyCycleDetailError(RuntimeError):
    """An agency cycle trace cannot be safely built or read."""


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


def _unit(name: str, value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) \
            or not 0.0 <= float(value) <= 1.0:
        raise AgencyCycleDetailError(f"ranking factor {name} is invalid")
    return float(value)


def step_coverage() -> list[dict[str, str]]:
    """The §12 steps in order, with their Phase 6 coverage class."""
    return [
        {"step": step, "coverage": STEP_COVERAGE[step]} for step in CYCLE_STEPS
    ]


def rank_score(factors: dict[str, Any]) -> float:
    """The pure §12 ranking function over the seven named factors.

    The five positive factors are averaged, then discounted by
    cost and by uncertainty (each at half weight, so neither alone
    can zero a candidate). Pure and deterministic; bounded [0, 1].
    """
    if not isinstance(factors, dict) or set(factors) != set(RANKING_FACTORS):
        raise AgencyCycleDetailError("ranking factors are invalid")
    values = {name: _unit(name, factors[name]) for name in RANKING_FACTORS}
    base = sum(values[name] for name in _POSITIVE_FACTORS) / len(_POSITIVE_FACTORS)
    return base * (1.0 - 0.5 * values["cost"]) * (1.0 - 0.5 * values["uncertainty"])


def within_bound(actions_executed: int, max_actions: int) -> bool:
    """The §12 hard bound: executed actions may not exceed the cap."""
    return actions_executed <= max_actions


class AgencyCycleDetailService:
    """The §12 step-trace layer beside the Phase 6 orchestrator."""

    def __init__(self, ctx) -> None:
        self._ctx = ctx
        self._identity = IdentityStore(ctx)

    def enabled(self) -> bool:
        return self._identity.enabled() and _as_bool(
            self._ctx.get_config("agency_cycle_detail_enabled", False), False
        )

    def _limit(self) -> int:
        try:
            value = int(self._ctx.get_config(
                "agency_cycle_detail_log_limit", DEFAULT_LOG_LIMIT))
        except (TypeError, ValueError):
            value = DEFAULT_LOG_LIMIT
        return min(500, max(10, value))

    def max_actions(self) -> int:
        try:
            value = int(self._ctx.get_config(
                "agency_cycle_detail_max_actions", DEFAULT_MAX_ACTIONS))
        except (TypeError, ValueError):
            value = DEFAULT_MAX_ACTIONS
        return min(10, max(1, value))

    def path(self) -> Path:
        home = get_hermes_home().resolve()
        configured = Path(str(self._ctx.get_config(
            "agency_cycle_detail_log_path", str(DEFAULT_LOG_PATH))))
        if configured.is_absolute():
            configured = DEFAULT_LOG_PATH
        lexical = home / configured
        candidate = lexical.resolve()
        if not candidate.is_relative_to(home):
            lexical = home / DEFAULT_LOG_PATH
            candidate = lexical.resolve()
        if not candidate.is_relative_to(home):
            raise AgencyCycleDetailError(
                "agency cycle trace log path resolves outside the profile")
        if lexical.is_symlink():
            return lexical
        return candidate

    # -- trace building ---------------------------------------------------
    def build_trace(self, cycle_id: str, *, trigger: str,
                    steps: dict[str, str], actions_proposed: int,
                    actions_executed: int, max_actions: int | None = None,
                    recorded_at: str | None = None) -> dict[str, Any]:
        """Build a §12 cycle trace record. Pure; records nothing."""
        if not _canonical_uuid(cycle_id):
            raise AgencyCycleDetailError("cycle_id is invalid")
        if not isinstance(trigger, str) \
                or not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", trigger):
            raise AgencyCycleDetailError("cycle trace trigger is invalid")
        if not isinstance(steps, dict) or set(steps) != set(CYCLE_STEPS):
            raise AgencyCycleDetailError(
                "cycle trace must name exactly the twelve §12 steps")
        for status in steps.values():
            if status not in STEP_STATUSES:
                raise AgencyCycleDetailError("cycle trace step status is invalid")
        for name, count in (("actions_proposed", actions_proposed),
                            ("actions_executed", actions_executed)):
            if isinstance(count, bool) or not isinstance(count, int) or count < 0:
                raise AgencyCycleDetailError(f"cycle trace {name} is invalid")
        if actions_executed > actions_proposed:
            raise AgencyCycleDetailError(
                "cycle trace executed exceeds its proposed count")
        cap = self.max_actions() if max_actions is None else max_actions
        if isinstance(cap, bool) or not isinstance(cap, int) \
                or not 1 <= cap <= 10:
            raise AgencyCycleDetailError("cycle trace max_actions is invalid")
        if not within_bound(actions_executed, cap):
            raise AgencyCycleDetailError(
                "cycle trace exceeds the hard maximum actions per cycle")
        stamp = recorded_at or _fmt(_now_dt())
        if not _timestamp_ok(stamp):
            raise AgencyCycleDetailError("cycle trace recorded_at is invalid")
        trace = {
            "trace_version": TRACE_VERSION,
            "kind": "cycle_trace",
            "record_id": str(uuid.uuid4()),
            "cycle_id": cycle_id,
            "owner_entity_id": self._identity.read().entity_id,
            "trigger": trigger,
            "recorded_at": stamp,
            "steps": [
                {"step": step, "status": steps[step]} for step in CYCLE_STEPS
            ],
            "actions_proposed": actions_proposed,
            "actions_executed": actions_executed,
            "max_actions": cap,
            "within_bound": True,
        }
        self._validate(trace, trace["owner_entity_id"])
        return trace

    def record_trace(self, trace: dict[str, Any]) -> dict[str, Any]:
        if not self.enabled():
            raise AgencyCycleDetailError("agency cycle detail is disabled")
        owner = self._identity.read().entity_id
        self._validate(trace, owner)
        self._append(trace)
        return trace

    def traces(self, *, limit: int = 500) -> list[dict[str, Any]]:
        owner = self._identity.read().entity_id
        path = self.path()
        if path.is_symlink():
            raise AgencyCycleDetailError(
                "agency cycle trace log must not be a symbolic link")
        if not path.is_file():
            return []
        if path.stat().st_size > MAX_LOG_BYTES:
            raise AgencyCycleDetailError(
                "agency cycle trace log exceeds its size limit")
        out: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except ValueError as exc:
                raise AgencyCycleDetailError(
                    "agency cycle trace log is malformed") from exc
            self._validate(payload, owner)
            out.append(payload)
        return out[-max(1, min(500, limit)):]

    def trace_for_cycle(self, cycle_id: str) -> dict[str, Any] | None:
        if not _canonical_uuid(cycle_id):
            raise AgencyCycleDetailError("cycle_id is invalid")
        found = None
        for trace in self.traces(limit=500):
            if trace["cycle_id"] == cycle_id:
                found = trace  # the latest recorded trace for the cycle wins
        return found

    def _validate(self, payload: Any, owner: str) -> None:
        if not isinstance(payload, dict):
            raise AgencyCycleDetailError("agency cycle trace is invalid")
        if set(payload) != _TRACE_FIELDS:
            raise AgencyCycleDetailError("agency cycle trace fields are invalid")
        if payload.get("trace_version") != TRACE_VERSION:
            raise AgencyCycleDetailError("agency cycle trace version is unsupported")
        if payload.get("kind") != "cycle_trace":
            raise AgencyCycleDetailError("agency cycle trace kind is invalid")
        if payload.get("owner_entity_id") != owner:
            raise AgencyCycleDetailError(
                "agency cycle trace owner does not match entity identity")
        if not _canonical_uuid(payload.get("record_id")) \
                or not _canonical_uuid(payload.get("cycle_id")):
            raise AgencyCycleDetailError("agency cycle trace ids are invalid")
        trigger = payload.get("trigger")
        if not isinstance(trigger, str) \
                or not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", trigger):
            raise AgencyCycleDetailError("agency cycle trace trigger is invalid")
        if not _timestamp_ok(payload.get("recorded_at")):
            raise AgencyCycleDetailError("agency cycle trace recorded_at is invalid")
        steps = payload.get("steps")
        if not isinstance(steps, list) or len(steps) != len(CYCLE_STEPS):
            raise AgencyCycleDetailError("agency cycle trace steps are invalid")
        for entry, name in zip(steps, CYCLE_STEPS):
            if not isinstance(entry, dict) or set(entry) != {"step", "status"} \
                    or entry.get("step") != name \
                    or entry.get("status") not in STEP_STATUSES:
                raise AgencyCycleDetailError(
                    "agency cycle trace steps are out of canonical order")
        proposed = payload.get("actions_proposed")
        executed = payload.get("actions_executed")
        cap = payload.get("max_actions")
        for value in (proposed, executed, cap):
            if isinstance(value, bool) or not isinstance(value, int):
                raise AgencyCycleDetailError("agency cycle trace counts are invalid")
        if proposed < 0 or executed < 0 or not 1 <= cap <= 10:
            raise AgencyCycleDetailError("agency cycle trace counts are invalid")
        if executed > proposed:
            raise AgencyCycleDetailError(
                "agency cycle trace executed exceeds its proposed count")
        if payload.get("within_bound") is not within_bound(executed, cap):
            raise AgencyCycleDetailError(
                "agency cycle trace within_bound disagrees with its counts")

    def _append(self, record: dict[str, Any]) -> None:
        path = self.path()
        if path.is_symlink():
            raise AgencyCycleDetailError(
                "agency cycle trace log must not be a symbolic link")
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
                    raise AgencyCycleDetailError(
                        "agency cycle trace log exceeds its size limit")
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


class AgencyCycleDetailBridge:
    """Surface the latest §12 cycle trace, content-bearing only.

    No session hook — traces are written only by explicit calls,
    and nothing here runs a cycle.
    """

    def __init__(self, ctx) -> None:
        self._ctx = ctx
        self._service = AgencyCycleDetailService(ctx)

    def hooks(self):
        return ()

    def packet_items(self, session_id: str, user_message: Any = "") -> list[ContextItem]:
        if not _as_bool(
            self._ctx.get_config("agency_cycle_detail_enabled", False), False
        ):
            return []
        try:
            traces = self._service.traces(limit=1)
        except (IdentityError, AgencyCycleDetailError, OSError):
            return []
        if not traces:
            return []
        latest = traces[-1]
        completed = sum(
            1 for entry in latest["steps"] if entry["status"] == "completed")
        blocked = any(
            entry["status"] == "blocked" for entry in latest["steps"])
        if not latest["actions_executed"] and not blocked:
            return []
        return [ContextItem(
            section="current_state",
            content=(
                f"Agency cycle (§12 trace): {latest['actions_executed']} "
                f"executed within bound {latest['max_actions']}, "
                f"{completed} of {len(CYCLE_STEPS)} steps completed"
            ),
            source="agency_cycle_detail",
            record_id=latest["record_id"],
            priority=0.5,
            updated_at=_epoch(latest["recorded_at"]),
        )]


__all__ = [
    "TRACE_VERSION",
    "DEFAULT_LOG_PATH",
    "CYCLE_STEPS",
    "STEP_STATUSES",
    "STEP_COVERAGE",
    "RANKING_FACTORS",
    "AgencyCycleDetailError",
    "AgencyCycleDetailService",
    "AgencyCycleDetailBridge",
    "step_coverage",
    "rank_score",
    "within_bound",
]
