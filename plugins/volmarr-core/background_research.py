"""Background curiosity and research (Emergent Agency Phase 10, roadmap §17).

Low-cost exploration is enabled only when every §17 gate holds at the
moment of one explicit ``run_once`` invocation:

- no urgent user goal is pending (a live ``user`` goal with
  ``urgency == "urgent"`` blocks the run);
- health is good (the continuity heartbeat probe reports healthy —
  a fresh pulse inside the stale window);
- the resource budget permits (fewer than
  ``background_research_daily_budget`` completed runs today, UTC);
- curiosity has a sufficiently valuable open question (the frontier's
  top score reaches ``background_research_min_score``).

The first safe forms are local only, exactly as §17 lists them:
inspect the entity's own local stores (its project docs/state),
examine its own metrics, compare self-model claims, find
inconsistencies in its own documentation/state, and run a
deterministic experiment (frontier scoring recomputed twice must
agree exactly). External/network research is a later form behind an
explicit network policy: it is NOT part of this slice — any form
outside the local registry is refused, and nothing here touches the
network, sends a message, calls a model, or creates a goal.

One run investigates one question: the attempt is recorded through
the Phase 4 curiosity store (its cooldown and attempt limits apply),
the chosen form runs read-only against the local stores, and the
only writes are that attempt record and one bounded record in this
module's own ``entity/background_research.jsonl`` log. Findings are
recorded as facts in the log; they are not treated as truth beyond
what the local stores actually showed (§17 source-verification rule).
There is no hook, loop, or scheduler here — Hermes cron or an
operator invokes ``run_once`` and it exits.
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
from .curiosity import CuriosityError, CuriosityStore, curiosity_score, normalize_question
from .goals import GoalStore
from .heartbeat import HeartbeatStore, probe_heartbeat
from .identity import IdentityError, IdentityStore, _as_bool
from .metacognition import MetacognitionStore
from .self_model import SelfModelStore

RESEARCH_LOG_VERSION = 1
DEFAULT_LOG_PATH = Path("entity") / "background_research.jsonl"
DEFAULT_LOG_LIMIT = 200
MAX_LOG_BYTES = 4 * 1024 * 1024
DEFAULT_DAILY_BUDGET = 5
DEFAULT_MIN_SCORE = 0.10

# The §17 first safe forms: local only. Anything not listed here —
# web research, repository discovery, package research, external
# reading — is refused until an explicit network policy exists.
RESEARCH_FORMS = frozenset({
    "inspect_local_stores",
    "examine_own_metrics",
    "compare_self_model_claims",
    "find_doc_inconsistencies",
    "deterministic_experiment",
})

_LOG_FIELDS = {
    "log_version", "record_id", "owner_entity_id", "form",
    "question_id", "outcome", "summary", "detail", "created_at",
}

try:
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None
try:
    import msvcrt
except ImportError:  # pragma: no cover
    msvcrt = None


class BackgroundResearchError(RuntimeError):
    """A background research run cannot be safely performed or logged."""


def _now_dt() -> datetime:
    return datetime.now(timezone.utc)


def _fmt(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class ResearchLog:
    """Bounded profile-local log of completed background research runs."""

    def __init__(self, ctx) -> None:
        self._ctx = ctx
        self._identity = IdentityStore(ctx)

    def _limit(self) -> int:
        try:
            value = int(self._ctx.get_config("background_research_log_limit", DEFAULT_LOG_LIMIT))
        except (TypeError, ValueError):
            value = DEFAULT_LOG_LIMIT
        return min(500, max(10, value))

    def path(self) -> Path:
        home = get_hermes_home().resolve()
        configured = Path(str(self._ctx.get_config(
            "background_research_log_path", str(DEFAULT_LOG_PATH))))
        if configured.is_absolute():
            configured = DEFAULT_LOG_PATH
        lexical = home / configured
        candidate = lexical.resolve()
        if not candidate.is_relative_to(home):
            lexical = home / DEFAULT_LOG_PATH
            candidate = lexical.resolve()
        if not candidate.is_relative_to(home):
            raise BackgroundResearchError("research log path resolves outside the active profile")
        if lexical.is_symlink():
            return lexical
        return candidate

    def append(self, *, form: str, question_id: str, summary: str,
               detail: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
        if form not in RESEARCH_FORMS:
            raise BackgroundResearchError("research form is not in the local registry")
        owner = self._identity.read().entity_id
        clean_detail: dict[str, Any] = {}
        for key, value in detail.items():
            if not isinstance(key, str) or not re.fullmatch(r"[a-z0-9_]+", key):
                raise BackgroundResearchError("research log detail key is invalid")
            if isinstance(value, bool) or not isinstance(value, (int, str)):
                raise BackgroundResearchError("research log detail value is invalid")
            clean_detail[key] = value if isinstance(value, int) else value[:200]
        record = {
            "log_version": RESEARCH_LOG_VERSION,
            "record_id": str(uuid.uuid4()),
            "owner_entity_id": owner,
            "form": form,
            "question_id": question_id,
            "outcome": "completed",
            "summary": summary[:500],
            "detail": clean_detail,
            "created_at": _fmt(now or _now_dt()),
        }
        path = self.path()
        if path.is_symlink():
            raise BackgroundResearchError("research log must not be a symbolic link")
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
                    raise BackgroundResearchError("research log exceeds its size limit")
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
            raise BackgroundResearchError("research log must not be a symbolic link")
        if not path.is_file():
            return []
        if path.stat().st_size > MAX_LOG_BYTES:
            raise BackgroundResearchError("research log exceeds its size limit")
        out: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except ValueError as exc:
                raise BackgroundResearchError("research log is malformed") from exc
            if not isinstance(payload, dict) or set(payload) != _LOG_FIELDS:
                raise BackgroundResearchError("research log record fields are invalid")
            if payload.get("log_version") != RESEARCH_LOG_VERSION:
                raise BackgroundResearchError("research log version is unsupported")
            if payload.get("owner_entity_id") != owner:
                raise BackgroundResearchError("research log owner does not match entity identity")
            if payload.get("form") not in RESEARCH_FORMS:
                raise BackgroundResearchError("research log form is invalid")
            if payload.get("outcome") != "completed":
                raise BackgroundResearchError("research log outcome is invalid")
            if not isinstance(payload.get("detail"), dict):
                raise BackgroundResearchError("research log detail is invalid")
            out.append(payload)
        return out[-max(1, min(500, limit)):]


class BackgroundResearchService:
    """Run ONE gated, local-only background research step, explicitly."""

    def __init__(self, ctx) -> None:
        self._ctx = ctx
        self._identity = IdentityStore(ctx)
        self._goals = GoalStore(ctx)
        self._curiosity = CuriosityStore(ctx)
        self._self_model = SelfModelStore(ctx)
        self._metacognition = MetacognitionStore(ctx)
        self._heartbeat = HeartbeatStore(ctx)
        self._log = ResearchLog(ctx)

    def enabled(self) -> bool:
        return self._identity.enabled() and _as_bool(
            self._ctx.get_config("background_research_enabled", False), False
        )

    def _daily_budget(self) -> int:
        try:
            value = int(self._ctx.get_config("background_research_daily_budget", DEFAULT_DAILY_BUDGET))
        except (TypeError, ValueError):
            value = DEFAULT_DAILY_BUDGET
        return min(20, max(1, value))

    def _min_score(self) -> float:
        try:
            value = float(self._ctx.get_config("background_research_min_score", DEFAULT_MIN_SCORE))
        except (TypeError, ValueError):
            value = DEFAULT_MIN_SCORE
        return min(1.0, max(0.0, value))

    # -- gates -------------------------------------------------------------
    def gates(self, *, now: datetime | None = None) -> dict[str, Any]:
        """Evaluate the four §17 gates without running anything."""
        moment = now or _now_dt()
        urgent_pending = False
        try:
            goals = self._goals.get().get("goals", {})
            urgent_pending = any(
                goal.get("origin", "user") == "user"
                and goal.get("urgency", "normal") == "urgent"
                and goal.get("status") in ("planned", "active", "blocked")
                for goal in goals.values()
            )
        except Exception:
            urgent_pending = True  # unreadable goals: fail closed on this gate
        health = probe_heartbeat(self._ctx)
        runs_today = 0
        try:
            today = moment.date().isoformat()
            runs_today = sum(
                1 for record in self._log.records()
                if str(record.get("created_at", "")).startswith(today)
            )
        except (IdentityError, BackgroundResearchError, OSError):
            runs_today = self._daily_budget()  # unreadable log: budget closed
        frontier = []
        try:
            frontier = self._curiosity.frontier(now=moment)
        except (IdentityError, CuriosityError, OSError):
            frontier = []
        top_score = frontier[0]["score"] if frontier else 0.0
        return {
            "no_urgent_user_goal": not urgent_pending,
            "health_good": bool(health.healthy),
            "health_status": health.status,
            "budget_permits": runs_today < self._daily_budget(),
            "runs_today": runs_today,
            "daily_budget": self._daily_budget(),
            "valuable_question": bool(frontier) and top_score >= self._min_score(),
            "top_score": top_score,
            "min_score": self._min_score(),
            "frontier_question_id": frontier[0]["question_id"] if frontier else "",
        }

    # -- the run -------------------------------------------------------------
    def run_once(self, form: str = "inspect_local_stores", *,
                 now: datetime | None = None) -> dict[str, Any]:
        if form not in RESEARCH_FORMS:
            raise BackgroundResearchError(
                "research form is not a local first-safe form; external/network "
                "research requires an explicit network policy and is not enabled"
            )
        if not self.enabled():
            raise BackgroundResearchError("background research is disabled")
        moment = now or _now_dt()
        gates = self.gates(now=moment)
        blocked = [
            name for name in (
                "no_urgent_user_goal", "health_good", "budget_permits", "valuable_question"
            )
            if not gates[name]
        ]
        if blocked:
            return {"ran": False, "blocked_by": blocked, "gates": gates, "form": form}
        question_id = gates["frontier_question_id"]
        try:
            self._curiosity.record_attempt(question_id, now=moment)
        except CuriosityError:
            return {"ran": False, "blocked_by": ["attempt_refused"], "gates": gates, "form": form}
        summary, detail = self._FORMS[form](self)
        record = self._log.append(
            form=form, question_id=question_id, summary=summary, detail=detail, now=moment
        )
        return {
            "ran": True, "blocked_by": [], "gates": gates, "form": form,
            "question_id": question_id, "summary": summary, "detail": detail,
            "record_id": record["record_id"],
        }

    # -- local forms (read-only against the entity's own stores) ------------
    def _form_inspect_local_stores(self) -> tuple[str, dict[str, Any]]:
        claims = self._self_model.claims()
        goals = self._goals.get().get("goals", {})
        questions = self._curiosity.questions()
        reflections = self._metacognition.reflections(limit=500)
        detail = {
            "claims": len(claims),
            "goals": len(goals),
            "questions": len(questions),
            "reflections": len(reflections),
        }
        return (
            f"Local stores inspected: {detail['claims']} self-model claims, "
            f"{detail['goals']} goals, {detail['questions']} curiosity questions, "
            f"{detail['reflections']} reflections; all readable.",
            detail,
        )

    def _form_examine_own_metrics(self) -> tuple[str, dict[str, Any]]:
        summary = self._metacognition.summary()
        calibration = summary.get("calibration", {})
        buckets_with_data = sum(
            1 for bucket in calibration.values()
            if isinstance(bucket, dict) and int(bucket.get("count", 0)) > 0
        )
        detail = {
            "total_reflections": int(summary.get("total_reflections", 0)),
            "calibration_buckets_with_data": buckets_with_data,
            "claims": len(self._self_model.claims()),
            "questions": len(self._curiosity.questions()),
        }
        return (
            f"Own metrics examined: {detail['total_reflections']} reflections, "
            f"{buckets_with_data} calibration bucket(s) with data.",
            detail,
        )

    def _form_compare_self_model_claims(self) -> tuple[str, dict[str, Any]]:
        claims = self._self_model.claims()
        low = [c for c in claims if c.confidence < 0.35]
        high = [c for c in claims if c.confidence >= 0.9]
        never_confirmed = [c for c in claims if not c.last_confirmed_at]
        detail = {
            "claims": len(claims),
            "low_confidence": len(low),
            "high_confidence": len(high),
            "never_confirmed": len(never_confirmed),
        }
        weakest = (
            min(claims, key=lambda c: (c.confidence, c.claim_id)) if claims else None
        )
        detail["weakest_claim"] = (
            f"{weakest.domain}/{weakest.key}" if weakest is not None else "none"
        )
        return (
            f"Self-model claims compared: {len(claims)} claims, {len(low)} below "
            f"0.35 confidence, {len(never_confirmed)} never confirmed; weakest "
            f"{detail['weakest_claim']}.",
            detail,
        )

    def _form_find_doc_inconsistencies(self) -> tuple[str, dict[str, Any]]:
        goals = self._goals.get().get("goals", {})
        titles: dict[str, int] = {}
        blocked_without_next = 0
        for goal in goals.values():
            if goal.get("status") in ("planned", "active", "blocked"):
                key = normalize_question(str(goal.get("title", "")))
                titles[key] = titles.get(key, 0) + 1
                if goal.get("status") == "blocked" and not str(
                    goal.get("next_action", "")
                ).strip():
                    blocked_without_next += 1
        duplicate_titles = sum(1 for count in titles.values() if count > 1)
        questions = self._curiosity.questions()
        texts: dict[str, int] = {}
        for question in questions:
            if question.status in ("abandoned", "invalidated"):
                key = normalize_question(question.question)
                texts[key] = texts.get(key, 0) + 1
        duplicate_texts = sum(1 for count in texts.values() if count > 1)
        claims = self._self_model.claims()
        pairs: dict[tuple[str, str], int] = {}
        for claim in claims:
            key = (claim.domain, claim.key)
            pairs[key] = pairs.get(key, 0) + 1
        duplicate_claim_keys = sum(1 for count in pairs.values() if count > 1)
        total = duplicate_titles + duplicate_texts + duplicate_claim_keys + blocked_without_next
        detail = {
            "duplicate_goal_titles": duplicate_titles,
            "duplicate_retired_question_texts": duplicate_texts,
            "duplicate_claim_keys": duplicate_claim_keys,
            "blocked_goals_without_next_action": blocked_without_next,
            "inconsistencies": total,
        }
        return (
            f"Documentation/state inconsistencies found: {total} "
            f"({duplicate_titles} duplicate live goal titles, "
            f"{blocked_without_next} blocked goals without a next action, "
            f"{duplicate_claim_keys} duplicate claim keys, "
            f"{duplicate_texts} duplicate retired question texts).",
            detail,
        )

    def _form_deterministic_experiment(self) -> tuple[str, dict[str, Any]]:
        questions = self._curiosity.questions()
        first = [curiosity_score(q) for q in questions]
        second = [curiosity_score(q) for q in questions]
        detail = {
            "questions_scored": len(questions),
            "deterministic": "true" if first == second else "false",
        }
        return (
            f"Deterministic experiment: curiosity scoring recomputed twice over "
            f"{len(questions)} questions; agreement "
            f"{detail['deterministic']}.",
            detail,
        )

    _FORMS = {
        "inspect_local_stores": _form_inspect_local_stores,
        "examine_own_metrics": _form_examine_own_metrics,
        "compare_self_model_claims": _form_compare_self_model_claims,
        "find_doc_inconsistencies": _form_find_doc_inconsistencies,
        "deterministic_experiment": _form_deterministic_experiment,
    }


class BackgroundResearchBridge:
    """Surface the last completed background research run, if any.

    Content-bearing only: disabled, or no completed run, contributes
    nothing. No session hook — a run happens only by explicit
    invocation of the service.
    """

    def __init__(self, ctx) -> None:
        self._ctx = ctx
        self._log = ResearchLog(ctx)
        self._identity = IdentityStore(ctx)

    def hooks(self):
        return ()

    def packet_items(self, session_id: str, user_message: Any = "") -> list[ContextItem]:
        if not _as_bool(self._ctx.get_config("background_research_enabled", False), False):
            return []
        try:
            records = self._log.records(limit=1)
        except (IdentityError, BackgroundResearchError, OSError):
            return []
        if not records:
            return []
        last = records[-1]
        return [ContextItem(
            section="current_state",
            content=f"Background research ({last['form']}): {last['summary']}",
            source="background_research",
            record_id=last["record_id"],
            priority=0.4,
            updated_at=_parse(last["created_at"]).timestamp(),
        )]


__all__ = [
    "RESEARCH_FORMS", "RESEARCH_LOG_VERSION", "DEFAULT_LOG_PATH",
    "BackgroundResearchError", "ResearchLog", "BackgroundResearchService",
    "BackgroundResearchBridge",
]
