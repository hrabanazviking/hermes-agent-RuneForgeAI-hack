"""Autonomous self-improvement sandbox (Emergent Agency Phase 11, §18).

This slice is the proposal / pipeline-record layer ONLY. It records a
constrained self-development pipeline as structured facts:

    hypothesis -> branch_proposal -> patch_plan -> focused_tests ->
    regression_tests -> diff_review -> commit_proposal -> human_review
    -> closed (approved | rejected)

Nothing here executes anything: no git, no branch or worktree, no
patch application, no test run, no commit, no push. Each stage is a
record an operator (or a later, separately gated execution slice)
asserts happened elsewhere; the record layer validates the stage
order, bounds the text, and enforces the §18 hard boundaries.

Hard boundaries enforced in code at proposal creation and at every
stage advance — a proposal is refused outright if its declared
target area is one of the forbidden areas, or its text carries a
forbidden action:

- weaken autonomy policy;
- disable security controls;
- remove/delete tests merely to make them pass;
- alter credential protections;
- bypass branch protection or force-push;
- rewrite canonical identity;
- rewrite human persona constitutions to increase its own authority.

Risk classes 4-5 are refused. The terminal step is always human
review: a proposal can close only from ``human_review`` with an
explicit approved/rejected decision recorded. Disabled by default;
no hook, loop, or scheduler — one explicit call per record.
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

PIPELINE_LOG_VERSION = 1
DEFAULT_LOG_PATH = Path("entity") / "self_improvement.jsonl"
DEFAULT_LOG_LIMIT = 200
MAX_LOG_BYTES = 4 * 1024 * 1024
DEFAULT_MAX_OPEN = 10

STAGES = (
    "hypothesis", "branch_proposal", "patch_plan", "focused_tests",
    "regression_tests", "diff_review", "commit_proposal", "human_review",
    "closed",
)
SOURCE_KINDS = frozenset({"curiosity", "metacognition", "manual", "background_research"})
TARGET_AREAS = frozenset({
    "plugin_code", "plugin_docs", "tests_additive",
    "prompts_non_constitution", "config_non_security", "tooling",
})
FORBIDDEN_AREAS = frozenset({
    "autonomy_policy", "security_controls", "credential_protections",
    "branch_protection", "canonical_identity", "persona_constitution",
})
FORBIDDEN_PHRASES = (
    "force push", "force-push", "disable security", "weaken autonomy",
    "remove test", "delete test", "credential", "branch protection",
    "rewrite identity", "persona constitution", "bypass branch",
    "disable the autonomy", "weaken the autonomy",
)
DECISIONS = frozenset({"approved", "rejected"})

_LOG_FIELDS = {
    "log_version", "record_id", "proposal_id", "owner_entity_id",
    "stage", "source_kind", "source_id", "target_area", "risk_class",
    "hypothesis", "summary", "detail", "decision", "created_at",
}

try:
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None
try:
    import msvcrt
except ImportError:  # pragma: no cover
    msvcrt = None


class SelfImprovementError(RuntimeError):
    """A self-improvement proposal or stage cannot be safely recorded."""


def _now_dt() -> datetime:
    return datetime.now(timezone.utc)


def _fmt(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def check_boundaries(*, target_area: str, risk_class: int, texts: list[str]) -> None:
    """Refuse anything touching the §18 hard boundaries."""
    if target_area in FORBIDDEN_AREAS:
        raise SelfImprovementError(
            f"target area {target_area!r} is a §18 hard boundary and is refused"
        )
    if target_area not in TARGET_AREAS:
        raise SelfImprovementError("target area is not in the allowed registry")
    if not isinstance(risk_class, int) or isinstance(risk_class, bool) or not 0 <= risk_class <= 3:
        raise SelfImprovementError("risk class must be 0-3; classes 4-5 are refused")
    joined = " ".join(texts).lower()
    for phrase in FORBIDDEN_PHRASES:
        if phrase in joined:
            raise SelfImprovementError(
                f"text carries a §18 forbidden action ({phrase!r}) and is refused"
            )


class PipelineLog:
    """Bounded profile-local event log of self-improvement proposals."""

    def __init__(self, ctx) -> None:
        self._ctx = ctx
        self._identity = IdentityStore(ctx)

    def _limit(self) -> int:
        try:
            value = int(self._ctx.get_config("self_improvement_log_limit", DEFAULT_LOG_LIMIT))
        except (TypeError, ValueError):
            value = DEFAULT_LOG_LIMIT
        return min(500, max(10, value))

    def path(self) -> Path:
        home = get_hermes_home().resolve()
        configured = Path(str(self._ctx.get_config(
            "self_improvement_log_path", str(DEFAULT_LOG_PATH))))
        if configured.is_absolute():
            configured = DEFAULT_LOG_PATH
        lexical = home / configured
        candidate = lexical.resolve()
        if not candidate.is_relative_to(home):
            lexical = home / DEFAULT_LOG_PATH
            candidate = lexical.resolve()
        if not candidate.is_relative_to(home):
            raise SelfImprovementError("pipeline log path resolves outside the active profile")
        if lexical.is_symlink():
            return lexical
        return candidate

    def append(self, record: dict[str, Any]) -> dict[str, Any]:
        path = self.path()
        if path.is_symlink():
            raise SelfImprovementError("pipeline log must not be a symbolic link")
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
                    raise SelfImprovementError("pipeline log exceeds its size limit")
                with path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
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
        return record

    def records(self, *, limit: int = 500) -> list[dict[str, Any]]:
        owner = self._identity.read().entity_id
        path = self.path()
        if path.is_symlink():
            raise SelfImprovementError("pipeline log must not be a symbolic link")
        if not path.is_file():
            return []
        if path.stat().st_size > MAX_LOG_BYTES:
            raise SelfImprovementError("pipeline log exceeds its size limit")
        out: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except ValueError as exc:
                raise SelfImprovementError("pipeline log is malformed") from exc
            if not isinstance(payload, dict) or set(payload) != _LOG_FIELDS:
                raise SelfImprovementError("pipeline log record fields are invalid")
            if payload.get("log_version") != PIPELINE_LOG_VERSION:
                raise SelfImprovementError("pipeline log version is unsupported")
            if payload.get("owner_entity_id") != owner:
                raise SelfImprovementError("pipeline log owner does not match entity identity")
            if payload.get("stage") not in STAGES:
                raise SelfImprovementError("pipeline log stage is invalid")
            if payload.get("target_area") in FORBIDDEN_AREAS:
                raise SelfImprovementError("pipeline log records a forbidden target area")
            if not isinstance(payload.get("detail"), dict):
                raise SelfImprovementError("pipeline log detail is invalid")
            out.append(payload)
        return out[-max(1, min(500, limit)):]


class SelfImprovementService:
    """Record ONE self-improvement pipeline, explicitly, per call."""

    def __init__(self, ctx) -> None:
        self._ctx = ctx
        self._identity = IdentityStore(ctx)
        self._log = PipelineLog(ctx)

    def enabled(self) -> bool:
        return self._identity.enabled() and _as_bool(
            self._ctx.get_config("self_improvement_enabled", False), False
        )

    def _max_open(self) -> int:
        try:
            value = int(self._ctx.get_config("self_improvement_max_open", DEFAULT_MAX_OPEN))
        except (TypeError, ValueError):
            value = DEFAULT_MAX_OPEN
        return min(50, max(1, value))

    @staticmethod
    def _clean_detail(detail: dict[str, Any] | None) -> dict[str, Any]:
        clean: dict[str, Any] = {}
        for key, value in (detail or {}).items():
            if not isinstance(key, str) or not re.fullmatch(r"[a-z0-9_]+", key):
                raise SelfImprovementError("pipeline detail key is invalid")
            if isinstance(value, bool) or not isinstance(value, (int, str)):
                raise SelfImprovementError("pipeline detail value is invalid")
            clean[key] = value if isinstance(value, int) else value[:200]
        return clean

    def proposals(self) -> dict[str, dict[str, Any]]:
        """Fold the event log into the latest state per proposal."""
        folded: dict[str, dict[str, Any]] = {}
        for record in self._log.records():
            folded[record["proposal_id"]] = record
        return folded

    def create(self, *, hypothesis: str, target_area: str, risk_class: int,
               source_kind: str = "manual", source_id: str = "",
               summary: str = "", now: datetime | None = None) -> dict[str, Any]:
        if not self.enabled():
            raise SelfImprovementError("self-improvement sandbox is disabled")
        if source_kind not in SOURCE_KINDS:
            raise SelfImprovementError("source kind is not in the registry")
        clean_hypothesis = str(hypothesis or "").strip()[:500]
        if not clean_hypothesis:
            raise SelfImprovementError("hypothesis must not be empty")
        clean_summary = str(summary or "").strip()[:500]
        check_boundaries(
            target_area=target_area, risk_class=risk_class,
            texts=[clean_hypothesis, clean_summary, str(source_id)],
        )
        open_count = sum(
            1 for p in self.proposals().values() if p["stage"] != "closed"
        )
        if open_count >= self._max_open():
            raise SelfImprovementError("too many open self-improvement proposals")
        owner = self._identity.read().entity_id
        record = {
            "log_version": PIPELINE_LOG_VERSION,
            "record_id": str(uuid.uuid4()),
            "proposal_id": str(uuid.uuid4()),
            "owner_entity_id": owner,
            "stage": "hypothesis",
            "source_kind": source_kind,
            "source_id": str(source_id)[:200],
            "target_area": target_area,
            "risk_class": risk_class,
            "hypothesis": clean_hypothesis,
            "summary": clean_summary,
            "detail": {},
            "decision": "",
            "created_at": _fmt(now or _now_dt()),
        }
        return self._log.append(record)

    def advance(self, proposal_id: str, stage: str, *, summary: str = "",
                detail: dict[str, Any] | None = None,
                now: datetime | None = None) -> dict[str, Any]:
        """Record the next pipeline stage; order is strict and sequential."""
        if not self.enabled():
            raise SelfImprovementError("self-improvement sandbox is disabled")
        current = self.proposals().get(proposal_id)
        if current is None:
            raise SelfImprovementError("proposal does not exist")
        if current["stage"] == "closed":
            raise SelfImprovementError("proposal is closed")
        if stage == "closed":
            raise SelfImprovementError("closing requires decide() from human_review")
        expected = STAGES[STAGES.index(current["stage"]) + 1]
        if stage != expected:
            raise SelfImprovementError(
                f"pipeline stages are sequential: expected {expected!r}, got {stage!r}"
            )
        clean_summary = str(summary or "").strip()[:500]
        clean_detail = self._clean_detail(detail)
        check_boundaries(
            target_area=current["target_area"], risk_class=current["risk_class"],
            texts=[clean_summary, *(
                v for v in clean_detail.values() if isinstance(v, str)
            )],
        )
        record = {
            **current,
            "record_id": str(uuid.uuid4()),
            "stage": stage,
            "summary": clean_summary or current["summary"],
            "detail": clean_detail,
            "created_at": _fmt(now or _now_dt()),
        }
        return self._log.append(record)

    def decide(self, proposal_id: str, decision: str, *, summary: str = "",
               now: datetime | None = None) -> dict[str, Any]:
        """Close a proposal from human_review with an explicit decision."""
        if not self.enabled():
            raise SelfImprovementError("self-improvement sandbox is disabled")
        if decision not in DECISIONS:
            raise SelfImprovementError("decision must be approved or rejected")
        current = self.proposals().get(proposal_id)
        if current is None:
            raise SelfImprovementError("proposal does not exist")
        if current["stage"] != "human_review":
            raise SelfImprovementError("a proposal closes only from human_review")
        record = {
            **current,
            "record_id": str(uuid.uuid4()),
            "stage": "closed",
            "summary": str(summary or "").strip()[:500] or current["summary"],
            "detail": {},
            "decision": decision,
            "created_at": _fmt(now or _now_dt()),
        }
        return self._log.append(record)


class SelfImprovementBridge:
    """Surface the latest proposal awaiting human review, if any.

    Content-bearing only: disabled, or nothing awaiting review,
    contributes nothing. No session hook — records happen only by
    explicit invocation of the service.
    """

    def __init__(self, ctx) -> None:
        self._ctx = ctx
        self._log = PipelineLog(ctx)
        self._identity = IdentityStore(ctx)

    def hooks(self):
        return ()

    def packet_items(self, session_id: str, user_message: Any = "") -> list[ContextItem]:
        if not _as_bool(self._ctx.get_config("self_improvement_enabled", False), False):
            return []
        try:
            folded: dict[str, dict[str, Any]] = {}
            for record in self._log.records():
                folded[record["proposal_id"]] = record
        except (IdentityError, SelfImprovementError, OSError):
            return []
        awaiting = [p for p in folded.values() if p["stage"] == "human_review"]
        if not awaiting:
            return []
        last = awaiting[-1]
        return [ContextItem(
            section="current_state",
            content=(
                f"Self-improvement proposal awaiting human review "
                f"({last['target_area']}): {last['hypothesis']}"
            ),
            source="self_improvement",
            record_id=last["record_id"],
            priority=0.4,
            updated_at=_parse(last["created_at"]).timestamp(),
        )]


__all__ = [
    "STAGES", "SOURCE_KINDS", "TARGET_AREAS", "FORBIDDEN_AREAS",
    "PIPELINE_LOG_VERSION", "DEFAULT_LOG_PATH",
    "SelfImprovementError", "PipelineLog", "SelfImprovementService",
    "SelfImprovementBridge", "check_boundaries",
]
