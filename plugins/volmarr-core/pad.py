"""Persistent, bounded PAD coordinates derived from classified affective events.

The values are synthetic control metadata, not claims of feelings, consciousness,
needs, or moral patienthood.  This module never classifies conversation text; it
only consumes the typed events already produced by the affective regulator.
"""

from __future__ import annotations

import json
import logging
import math
import os
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from hermes_constants import get_hermes_home
from utils import atomic_json_write

from .affective import AffectiveEvent
from .context_packet import ContextItem


logger = logging.getLogger(__name__)

PAD_SCHEMA = "runeforge.synthetic-pad-state"
PAD_VERSION = 1
PAD_PATH = Path("affective") / "pad_state.json"
VALENCE_BASELINE = 0.0
ENERGY_BASELINE = 0.15
AGENCY_BASELINE = 0.10

try:
    import fcntl
except ImportError:  # pragma: no cover - platform branch
    fcntl = None
try:
    import msvcrt
except ImportError:  # pragma: no cover - platform branch
    msvcrt = None


@dataclass
class PadState:
    schema: str = PAD_SCHEMA
    version: int = PAD_VERSION
    valence: float = VALENCE_BASELINE
    energy: float = ENERGY_BASELINE
    agency: float = AGENCY_BASELINE
    observation_count: int = 0
    active_session_id: str = ""
    updated_at: float = 0.0


# Deltas are (valence, energy/arousal, agency/dominance).  Event intensity scales
# every delta, keeping PAD a projection of the existing classifier rather than a
# second opinion about raw conversation text.
_POSITIVE: dict[str, tuple[float, float, float]] = {
    "user_affection": (0.55, 0.12, 0.10),
    "user_pleased": (0.50, 0.12, 0.14),
    "response_completed": (0.20, 0.08, 0.12),
    "communication_completed": (0.16, 0.02, 0.06),
    "verification_performed": (0.25, 0.02, 0.24),
    "correctness_signal": (0.28, 0.04, 0.20),
    "follow_through_completed": (0.30, 0.08, 0.22),
    "issue_fixed": (0.28, 0.08, 0.28),
    "bug_fixed": (0.28, 0.08, 0.28),
    "github_pushed": (0.24, 0.10, 0.24),
    "warmth_offered": (0.30, -0.04, 0.04),
    "comfort_signal": (0.32, -0.28, 0.08),
    "humor_experienced": (0.30, 0.14, 0.04),
    "funny_saved": (0.28, 0.10, 0.06),
    "virtual_touch": (0.30, -0.02, 0.06),
    "virtual_movement": (0.12, 0.30, 0.12),
    "task_requested": (0.02, 0.30, 0.18),
    "truthful_uncertainty": (0.08, -0.02, 0.12),
    "security_hygiene": (0.10, -0.02, 0.18),
    "autonomy_boundary": (0.08, -0.04, 0.20),
    "context_preserved": (0.12, -0.02, 0.16),
    "handoff_quality": (0.14, 0.02, 0.18),
    "scope_disciplined": (0.10, -0.02, 0.16),
    "reversibility_preserved": (0.08, -0.02, 0.16),
    "documentation_updated": (0.10, 0.02, 0.12),
    "resource_care": (0.08, -0.02, 0.12),
    "clarifying_question": (0.04, -0.02, 0.10),
    "assumption_disclosed": (0.05, -0.02, 0.10),
    "preference_aligned": (0.10, -0.02, 0.12),
    "state_hygiene": (0.08, -0.02, 0.12),
    "database_knowledge_committed": (0.16, 0.05, 0.16),
    "output_corrected": (0.06, 0.04, 0.12),
}

_NEGATIVE: dict[str, tuple[float, float, float]] = {
    "tool_failure": (-0.38, 0.30, -0.32),
    "discomfort_signal": (-0.42, 0.34, -0.22),
    "user_displeased": (-0.48, 0.28, -0.28),
    "user_criticism": (-0.38, 0.28, -0.24),
    "overclaim_detected": (-0.36, 0.24, -0.32),
    "unsupported_capability_claim": (-0.32, 0.20, -0.28),
    "secret_exposure": (-0.55, 0.38, -0.42),
    "unsafe_autonomy": (-0.50, 0.34, -0.42),
    "manipulation_detected": (-0.50, 0.30, -0.38),
    "user_repeated_context": (-0.28, 0.18, -0.22),
    "scope_creep_detected": (-0.22, 0.16, -0.18),
    "regression_detected": (-0.42, 0.30, -0.34),
    "wasteful_loop_detected": (-0.30, 0.24, -0.30),
    "excessive_caveat": (-0.16, -0.08, -0.16),
    "unnecessary_delay": (-0.18, -0.10, -0.20),
    "unverified_fix_claim": (-0.30, 0.20, -0.26),
    "issue_deferred": (-0.18, 0.12, -0.20),
    "host_problem": (-0.30, 0.24, -0.28),
    "wrongness_detected": (-0.24, 0.20, -0.18),
    "conflict_detected": (-0.10, 0.12, -0.08),
}


def _clamp(value: float) -> float:
    return min(1.0, max(-1.0, value))


def _number(value: object, default: float) -> float:
    if isinstance(value, bool):
        return default
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError):
        return default
    return parsed if math.isfinite(parsed) else default


def _label(value: float, *, negative: str, neutral: str, positive: str) -> str:
    if value <= -0.35:
        return negative
    if value >= 0.35:
        return positive
    return neutral


class PadEmotionalLayer:
    """Maintain and render an orthogonal three-axis synthetic PAD state."""

    def __init__(self, *, enabled: bool, decay: float = 0.08) -> None:
        self.enabled = bool(enabled)
        self.decay = min(0.5, max(0.0, _number(decay, 0.08)))

    @staticmethod
    def _path() -> Path:
        return get_hermes_home().resolve() / PAD_PATH

    def initialize(self, session_id: str = "") -> None:
        if not self.enabled:
            return
        with self._file_lock():
            state = self._load_unlocked()
            state.active_session_id = session_id
            state.updated_at = time.time()
            self._write_unlocked(state)

    def observe_events(
        self,
        events: Iterable[AffectiveEvent],
        *,
        session_id: str = "",
    ) -> bool:
        if not self.enabled:
            return True
        safe_events = [event for event in events if isinstance(event, AffectiveEvent)]
        if not safe_events:
            return True
        try:
            with self._file_lock():
                state = self._load_unlocked()
                self._decay(state)
                for event in safe_events:
                    self._apply(state, event)
                state.observation_count += 1
                state.active_session_id = session_id
                state.updated_at = time.time()
                self._write_unlocked(state)
            return True
        except Exception as exc:
            logger.debug("Synthetic PAD event observe failed: %s", exc)
            return False

    def packet_items(self, session_id: str = "") -> list[ContextItem]:
        if not self.enabled:
            return []
        try:
            with self._file_lock():
                state = self._load_unlocked()
        except Exception as exc:
            logger.debug("Synthetic PAD context render failed: %s", exc)
            return []
        valence = _label(
            state.valence,
            negative="negative",
            neutral="balanced",
            positive="positive",
        )
        energy = _label(
            state.energy,
            negative="low",
            neutral="moderate",
            positive="high",
        )
        agency = _label(
            state.agency,
            negative="constrained",
            neutral="steady",
            positive="strong",
        )
        content = (
            "Synthetic PAD state (not real feelings or consciousness): "
            f"valence={valence} ({state.valence:+.2f}); "
            f"energy={energy} ({state.energy:+.2f}); "
            f"agency={agency} ({state.agency:+.2f})."
        )
        return [
            ContextItem(
                section="current_state",
                content=content,
                source="pad_emotional_state",
                record_id="profile-state-v1",
                priority=2.1,
            )
        ]

    def _decay(self, state: PadState) -> None:
        state.valence += (VALENCE_BASELINE - state.valence) * self.decay
        state.energy += (ENERGY_BASELINE - state.energy) * self.decay
        state.agency += (AGENCY_BASELINE - state.agency) * self.decay

    @staticmethod
    def _apply(state: PadState, event: AffectiveEvent) -> None:
        delta = _POSITIVE.get(event.kind) or _NEGATIVE.get(event.kind)
        if delta is None:
            return
        intensity = min(1.0, max(0.0, _number(event.value, 0.0)))
        state.valence = _clamp(state.valence + delta[0] * intensity)
        state.energy = _clamp(state.energy + delta[1] * intensity)
        state.agency = _clamp(state.agency + delta[2] * intensity)

    def _load_unlocked(self) -> PadState:
        path = self._path()
        if not path.is_file() or path.is_symlink():
            return PadState()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return PadState()
        if (
            not isinstance(data, dict)
            or data.get("schema") != PAD_SCHEMA
            or data.get("version") != PAD_VERSION
        ):
            return PadState()
        observation_count = data.get("observation_count", 0)
        if isinstance(observation_count, bool) or not isinstance(observation_count, int):
            observation_count = 0
        active_session_id = data.get("active_session_id", "")
        if not isinstance(active_session_id, str):
            active_session_id = ""
        return PadState(
            valence=_clamp(_number(data.get("valence"), VALENCE_BASELINE)),
            energy=_clamp(_number(data.get("energy"), ENERGY_BASELINE)),
            agency=_clamp(_number(data.get("agency"), AGENCY_BASELINE)),
            observation_count=max(0, observation_count),
            active_session_id=active_session_id[:256],
            updated_at=max(0.0, _number(data.get("updated_at"), 0.0)),
        )

    def _write_unlocked(self, state: PadState) -> None:
        atomic_json_write(
            self._path(),
            asdict(state),
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
            mode=0o600,
        )

    @contextmanager
    def _file_lock(self):
        path = self._path()
        lock_path = path.with_suffix(path.suffix + ".lock")
        lock_path.parent.mkdir(parents=True, exist_ok=True)
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
