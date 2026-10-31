"""Curiosity engine store (Emergent Agency Phase 4, roadmap §11).

A persistent frontier of things the entity wants to understand, held
in a versioned ``entity/curiosity.yaml`` store on the Phase 0
``CuriosityQuestion`` contract. Questions are deduplicated by
normalised text, scored by one deterministic formula, and investigated
only through bounded local steps: an attempt limit, a cooldown, a
maximum subquestion depth, and cost/risk suppression are all enforced
in code. This module performs no research itself — external network
research and cloud inference stay policy-controlled elsewhere
(roadmap §11 default policy), and nothing here sends messages, calls
tools, or creates goals. Resolved questions stay in the store as
memory, so a resolved question is never silently re-asked.
"""

from __future__ import annotations

import os
import re
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml

from hermes_constants import get_hermes_home, mkdir_under_hermes_home
from utils import atomic_yaml_write

from .agency_contracts import AgencyContractError, CuriosityQuestion
from .context_packet import ContextItem
from .identity import IdentityError, IdentityStore, _as_bool

CURIOSITY_VERSION = 1
DEFAULT_CURIOSITY_PATH = Path("entity") / "curiosity.yaml"
MAX_QUESTIONS = 100
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_ATTEMPTS_DEFAULT = 3
MAX_SUBQUESTION_DEPTH = 2
MAX_USER_QUESTIONS = 5
DEFAULT_COOLDOWN_HOURS = 6
FRONTIER_SCORE_THRESHOLD = 0.05
RISK_SUPPRESSION_CLASS = 4  # risk classes 4-5 never enter the frontier

_TERMINAL = frozenset({"resolved", "abandoned", "invalidated"})
# Dedupe memory: a question in any of these statuses blocks re-adding
# the same normalised text (resolved-question memory, roadmap §11).
_DEDUPE_BLOCKING = frozenset({"open", "investigating", "deferred", "resolved"})
_TRANSITIONS = {
    "open": frozenset({"investigating", "deferred", "abandoned", "invalidated"}),
    "investigating": frozenset({"open", "resolved", "deferred", "abandoned", "invalidated"}),
    "deferred": frozenset({"open", "abandoned", "invalidated"}),
    "resolved": frozenset(),
    "abandoned": frozenset(),
    "invalidated": frozenset(),
}

try:
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None
try:
    import msvcrt
except ImportError:  # pragma: no cover
    msvcrt = None


class CuriosityError(RuntimeError):
    """The curiosity store cannot be safely read or changed."""


def _now_dt() -> datetime:
    return datetime.now(timezone.utc)


def _fmt(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


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


def normalize_question(text: str) -> str:
    """Canonical text for duplicate detection (case/space/punct-insensitive)."""
    folded = re.sub(r"\s+", " ", text.strip().casefold())
    return folded.rstrip("?.! ")


def curiosity_score(question: CuriosityQuestion) -> float:
    """The §11 score: relevance x uncertainty x novelty x expected_value
    x (1 - cost) x (1 - risk_penalty), risk_penalty = 0.1 x risk_class."""
    risk_penalty = 0.1 * question.risk_class
    score = (
        question.relevance
        * question.uncertainty
        * question.novelty
        * question.expected_value
        * (1.0 - question.cost)
        * (1.0 - risk_penalty)
    )
    return round(min(1.0, max(0.0, score)), 6)


def cheapest_step(question: CuriosityQuestion, *, for_user: bool = False) -> str:
    """The cheapest useful local step for a question (roadmap §11).

    Pure and local-only: asking the user for flagged questions, a cheap
    local inspection first, local deterministic tools after that. No
    external research is ever the cheapest step here.
    """
    if for_user:
        return "ask_user"
    if question.attempts == 0:
        return "cheap_local_inspection"
    return "local_deterministic_tools"


class CuriosityStore:
    """Versioned curiosity frontier with deterministic scoring and bounds."""

    def __init__(self, ctx) -> None:
        self._ctx = ctx
        self._identity = IdentityStore(ctx)

    def enabled(self) -> bool:
        return self._identity.enabled() and _as_bool(
            self._ctx.get_config("curiosity_enabled", True), True
        )

    def path(self) -> Path:
        home = get_hermes_home().resolve()
        configured = Path(str(self._ctx.get_config("curiosity_path", str(DEFAULT_CURIOSITY_PATH))))
        if configured.is_absolute():
            configured = DEFAULT_CURIOSITY_PATH
        lexical = home / configured
        candidate = lexical.resolve()
        if not candidate.is_relative_to(home):
            lexical = home / DEFAULT_CURIOSITY_PATH
            candidate = lexical.resolve()
        if not candidate.is_relative_to(home):
            raise CuriosityError("curiosity path resolves outside the active profile")
        # Resolution hides a symlinked final component; return the
        # lexical path in that case so the readers refuse it (the
        # Slice 87 probe lesson).
        if lexical.is_symlink():
            return lexical
        return candidate

    def _cooldown_hours(self) -> float:
        try:
            value = float(self._ctx.get_config("curiosity_cooldown_hours", DEFAULT_COOLDOWN_HOURS))
        except (TypeError, ValueError):
            value = float(DEFAULT_COOLDOWN_HOURS)
        return min(168.0, max(0.0, value))

    def _max_attempts(self) -> int:
        try:
            value = int(self._ctx.get_config("curiosity_max_attempts", MAX_ATTEMPTS_DEFAULT))
        except (TypeError, ValueError):
            value = MAX_ATTEMPTS_DEFAULT
        return min(10, max(1, value))

    # -- lifecycle --------------------------------------------------------
    def ensure(self) -> dict[str, Any]:
        owner = self._identity.ensure().entity_id
        path = self.path()
        with self._lock(path):
            if path.exists():
                return self._read_unlocked(path, owner)
            data = {
                "curiosity_version": CURIOSITY_VERSION,
                "owner_entity_id": owner,
                "updated_at": _fmt(_now_dt()),
                "questions": {},
                "depths": {},
                "cooldowns": {},
                "for_user": [],
            }
            self._write(path, data)
            return data

    def questions(self) -> list[CuriosityQuestion]:
        owner = self._identity.read().entity_id
        path = self.path()
        with self._lock(path):
            data = self._read_unlocked(path, owner)
        return [CuriosityQuestion.from_dict(data["questions"][k]) for k in sorted(data["questions"])]

    # -- mutation -----------------------------------------------------------
    def add_question(
        self,
        question: CuriosityQuestion,
        *,
        parent_id: str = "",
        for_user: bool = False,
    ) -> CuriosityQuestion:
        """Add a question, or return the existing duplicate unchanged.

        Duplicate normalised text in a blocking status is returned
        as-is (no write). Subquestions inherit parent depth + 1 and
        are refused past ``MAX_SUBQUESTION_DEPTH``.
        """
        if not isinstance(question, CuriosityQuestion):
            raise CuriosityError("question must be a CuriosityQuestion contract record")
        if question.status != "open":
            raise CuriosityError("new curiosity questions must start open")
        owner = self._identity.read().entity_id
        if question.owner_entity_id != owner:
            raise CuriosityError("question owner does not match entity identity")
        path = self.path()
        with self._lock(path):
            data = self._read_unlocked(path, owner)
            wanted = normalize_question(question.question)
            for existing_id in sorted(data["questions"]):
                existing = CuriosityQuestion.from_dict(data["questions"][existing_id])
                if (
                    existing.status in _DEDUPE_BLOCKING
                    and normalize_question(existing.question) == wanted
                ):
                    return existing
            if question.question_id in data["questions"]:
                raise CuriosityError("question_id already exists with different text")
            if len(data["questions"]) >= MAX_QUESTIONS:
                raise CuriosityError("curiosity queue is full")
            depth = 0
            if parent_id:
                if parent_id not in data["questions"]:
                    raise CuriosityError("parent question was not found")
                depth = int(data["depths"].get(parent_id, 0)) + 1
                if depth > MAX_SUBQUESTION_DEPTH:
                    raise CuriosityError("subquestion depth limit reached")
            data["questions"][question.question_id] = question.to_dict()
            data["depths"][question.question_id] = depth
            if for_user and question.question_id not in data["for_user"]:
                data["for_user"] = (list(data["for_user"]) + [question.question_id])[
                    -MAX_USER_QUESTIONS:
                ]
            data["updated_at"] = _fmt(_now_dt())
            self._write(path, data)
            return question

    def set_status(self, question_id: str, status: str) -> CuriosityQuestion:
        owner = self._identity.read().entity_id
        path = self.path()
        with self._lock(path):
            data = self._read_unlocked(path, owner)
            record = data["questions"].get(question_id)
            if record is None:
                raise CuriosityError("question was not found")
            current = CuriosityQuestion.from_dict(record)
            if status not in _TRANSITIONS[current.status]:
                raise CuriosityError(
                    f"curiosity transition {current.status} -> {status} is not allowed"
                )
            updated = CuriosityQuestion(
                **{**current.to_dict(), "status": status,
                   "source": current.source}
            )
            data["questions"][question_id] = updated.to_dict()
            if status in _TERMINAL:
                data["cooldowns"].pop(question_id, None)
                data["for_user"] = [q for q in data["for_user"] if q != question_id]
            data["updated_at"] = _fmt(_now_dt())
            self._write(path, data)
            return updated

    def record_attempt(
        self, question_id: str, *, now: datetime | None = None
    ) -> CuriosityQuestion:
        """Record one investigation attempt under the anti-rabbit-hole bounds.

        Increments attempts, stamps ``last_investigated_at``, moves the
        question to ``investigating``, and sets its cooldown. A question
        already in cooldown, or one that has spent its attempt budget,
        is refused; spending the last attempt defers the question.
        """
        moment = now or _now_dt()
        owner = self._identity.read().entity_id
        path = self.path()
        with self._lock(path):
            data = self._read_unlocked(path, owner)
            record = data["questions"].get(question_id)
            if record is None:
                raise CuriosityError("question was not found")
            current = CuriosityQuestion.from_dict(record)
            if current.status not in ("open", "investigating"):
                raise CuriosityError("only open or investigating questions can be attempted")
            cooldown_until = data["cooldowns"].get(question_id, "")
            if cooldown_until and _parse(cooldown_until) > moment:
                raise CuriosityError("question is in cooldown")
            if current.attempts >= self._max_attempts():
                raise CuriosityError("question attempt limit reached")
            attempts = current.attempts + 1
            exhausted = attempts >= self._max_attempts()
            updated = CuriosityQuestion(
                **{
                    **current.to_dict(),
                    "status": "deferred" if exhausted else "investigating",
                    "attempts": attempts,
                    "last_investigated_at": _fmt(moment),
                    "source": current.source,
                }
            )
            data["questions"][question_id] = updated.to_dict()
            if self._cooldown_hours() > 0:
                data["cooldowns"][question_id] = _fmt(
                    moment + timedelta(hours=self._cooldown_hours())
                )
            data["updated_at"] = _fmt(moment)
            self._write(path, data)
            return updated

    # -- frontier -----------------------------------------------------------
    def frontier(self, *, now: datetime | None = None) -> list[dict[str, Any]]:
        """Ranked, bounded next investigations — local steps only.

        Open questions only, score at/above the frontier threshold,
        risk classes 4-5 suppressed, cooldown-active and
        attempt-exhausted questions held back, deterministic order
        (score desc, then question_id).
        """
        moment = now or _now_dt()
        owner = self._identity.read().entity_id
        path = self.path()
        with self._lock(path):
            data = self._read_unlocked(path, owner)
        for_user = set(data["for_user"])
        scored: list[tuple[float, str, dict[str, Any]]] = []
        for question_id in sorted(data["questions"]):
            question = CuriosityQuestion.from_dict(data["questions"][question_id])
            if question.status != "open":
                continue
            if question.risk_class >= RISK_SUPPRESSION_CLASS:
                continue
            if question.attempts >= self._max_attempts():
                continue
            cooldown_until = data["cooldowns"].get(question_id, "")
            if cooldown_until and _parse(cooldown_until) > moment:
                continue
            score = curiosity_score(question)
            if score < FRONTIER_SCORE_THRESHOLD:
                continue
            scored.append((score, question_id, {
                "question_id": question_id,
                "question": question.question,
                "score": score,
                "attempts": question.attempts,
                "depth": int(data["depths"].get(question_id, 0)),
                "cheapest_step": cheapest_step(question, for_user=question_id in for_user),
            }))
        scored.sort(key=lambda row: (-row[0], row[1]))
        return [row[2] for row in scored]

    def questions_for_user(self) -> list[dict[str, Any]]:
        """The bounded questions-for-user queue (roadmap §11).

        Only flagged, still-open questions, deduplicated by normalised
        text, capped at ``MAX_USER_QUESTIONS``.
        """
        owner = self._identity.read().entity_id
        path = self.path()
        with self._lock(path):
            data = self._read_unlocked(path, owner)
        seen: set[str] = set()
        out: list[dict[str, Any]] = []
        for question_id in data["for_user"]:
            record = data["questions"].get(question_id)
            if record is None:
                continue
            question = CuriosityQuestion.from_dict(record)
            if question.status not in ("open", "investigating"):
                continue
            key = normalize_question(question.question)
            if key in seen:
                continue
            seen.add(key)
            out.append({
                "question_id": question_id,
                "question": question.question,
                "score": curiosity_score(question),
            })
            if len(out) >= MAX_USER_QUESTIONS:
                break
        return out

    # -- reading / validation ---------------------------------------------
    def _read_unlocked(self, path: Path, owner: str) -> dict[str, Any]:
        if path.is_symlink():
            raise CuriosityError("curiosity file must not be a symbolic link")
        if not path.is_file():
            raise CuriosityError("curiosity file is missing")
        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                raise CuriosityError("curiosity file exceeds its size limit")
            payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, yaml.YAMLError) as exc:
            raise CuriosityError("curiosity file is unreadable or malformed") from exc
        if not isinstance(payload, dict):
            raise CuriosityError("curiosity document must be a mapping")
        version = payload.get("curiosity_version")
        if isinstance(version, bool) or version != CURIOSITY_VERSION:
            raise CuriosityError("curiosity version is unsupported")
        if payload.get("owner_entity_id") != owner:
            raise CuriosityError("curiosity owner does not match entity identity")
        if not _timestamp_ok(payload.get("updated_at")):
            raise CuriosityError("curiosity updated_at is invalid")
        questions = payload.get("questions")
        if not isinstance(questions, dict) or len(questions) > MAX_QUESTIONS:
            raise CuriosityError("curiosity questions mapping is invalid or oversized")
        for question_id, record in questions.items():
            try:
                question = CuriosityQuestion.from_dict(record)
            except (AgencyContractError, KeyError, TypeError) as exc:
                raise CuriosityError("curiosity question record is invalid") from exc
            if question.question_id != question_id or question.owner_entity_id != owner:
                raise CuriosityError("curiosity question record is invalid")
        depths = payload.get("depths")
        if not isinstance(depths, dict) or set(depths) != set(questions):
            raise CuriosityError("curiosity depths mapping is invalid")
        for depth in depths.values():
            if isinstance(depth, bool) or not isinstance(depth, int) or not 0 <= depth <= MAX_SUBQUESTION_DEPTH:
                raise CuriosityError("curiosity depth value is invalid")
        cooldowns = payload.get("cooldowns")
        if not isinstance(cooldowns, dict) or not set(cooldowns) <= set(questions):
            raise CuriosityError("curiosity cooldowns mapping is invalid")
        for until in cooldowns.values():
            if not _timestamp_ok(until):
                raise CuriosityError("curiosity cooldown value is invalid")
        for_user = payload.get("for_user")
        if (
            not isinstance(for_user, list)
            or len(for_user) > MAX_USER_QUESTIONS
            or any(not isinstance(q, str) or q not in questions for q in for_user)
        ):
            raise CuriosityError("curiosity for_user queue is invalid")
        return payload

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


class CuriosityBridge:
    """Create the curiosity store at session start; offer its bounded packet."""

    def __init__(self, ctx) -> None:
        self._store = CuriosityStore(ctx)

    def hooks(self):
        return (("on_session_start", self.on_session_start),)

    def on_session_start(self, **_: Any) -> None:
        if not self._store.enabled():
            return
        try:
            self._store.ensure()
        except (IdentityError, CuriosityError, OSError):
            return

    def packet_items(self, session_id: str, user_message: Any = "") -> list[ContextItem]:
        if not self._store.enabled():
            return []
        try:
            frontier = self._store.frontier()
            questions = {q.question_id: q for q in self._store.questions()}
        except (IdentityError, CuriosityError, OSError):
            return []
        items: list[ContextItem] = []
        for entry in frontier[:3]:
            question = questions[entry["question_id"]]
            items.append(ContextItem(
                section="current_state",
                content=(
                    f"Curious about: {entry['question']} "
                    f"(score {entry['score']:.2f}; cheapest step: {entry['cheapest_step']})"
                ),
                source="curiosity",
                record_id=entry["question_id"],
                priority=entry["score"],
                updated_at=_parse(question.created_at).timestamp(),
            ))
        return items


__all__ = [
    "CURIOSITY_VERSION", "DEFAULT_CURIOSITY_PATH", "MAX_QUESTIONS",
    "MAX_SUBQUESTION_DEPTH", "MAX_USER_QUESTIONS", "FRONTIER_SCORE_THRESHOLD",
    "CuriosityError", "CuriosityStore", "CuriosityBridge",
    "curiosity_score", "normalize_question", "cheapest_step",
]
