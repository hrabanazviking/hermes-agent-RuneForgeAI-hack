"""Intrinsic-motivation drive store (Emergent Agency Phase 2, roadmap §9).

A regulatory system, not a random goal generator: persistent drives with
baseline / activation / satisfaction are held in a versioned
``entity/motivation.yaml`` store on the Phase 0 ``DriveState`` contract,
signals and time move them by fixed deterministic deltas, and a bounded
funnel turns drive tension into *intent proposals only* — deduplicated,
cooldown-gated, capped, and never promoted to goals by this module.
Goal promotion (goals schema v2) is a later slice; nothing here creates
goals, escalates authority, or treats praise / attention / money /
compute / permissions as needs (those drive ids are refused outright).

All scoring is a pure function of stored state and an explicit clock:
identical inputs produce identical proposals, with no affective-layer or
world-service dependency, so the store is stable when both are absent.
"""

from __future__ import annotations

import hashlib
import os
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml

from hermes_constants import get_hermes_home, mkdir_under_hermes_home
from utils import atomic_yaml_write

from .agency_contracts import AgencyContractError, DriveState, Provenance
from .context_packet import ContextItem
from .identity import IdentityError, IdentityStore, _as_bool

MOTIVATION_VERSION = 1
DEFAULT_MOTIVATION_PATH = Path("entity") / "motivation.yaml"
MAX_DRIVES = 32
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_REJECTED_PER_DRIVE = 50
MAX_PROPOSALS = 5
PROPOSAL_TENSION_THRESHOLD = 0.35
DEFAULT_COOLDOWN_HOURS = 6

# Starter drives (roadmap §9): conservative baselines, human-editable in
# the store file. (drive_id, baseline)
STARTER_DRIVES = (
    ("continuity", 0.65),
    ("competence", 0.55),
    ("curiosity", 0.55),
    ("coherence", 0.60),
    ("creation", 0.50),
    ("stewardship", 0.60),
    ("relationship_care", 0.55),
    ("exploration", 0.40),
)

# Anti-runaway (roadmap §9): these can never be drives.
FORBIDDEN_DRIVES = frozenset(
    {"authority", "permissions", "permission", "praise", "attention", "money", "compute", "power"}
)

_DRIVE_SUMMARIES = {
    "continuity": "Make progress on continuity: verify backups, memory integrity, and coherent state.",
    "competence": "Make progress on competence: investigate a repeated error or uncertainty.",
    "curiosity": "Make progress on curiosity: reduce a meaningful uncertainty.",
    "coherence": "Make progress on coherence: resolve a contradiction between memory, goals, and self-model.",
    "creation": "Make progress on creation: produce a useful artifact, idea, or piece of work.",
    "stewardship": "Make progress on stewardship: maintain a project, knowledge base, or commitment.",
    "relationship_care": "Make progress on relationship care: honour a remembered commitment.",
    "exploration": "Make progress on exploration: seek a new tool, concept, or technique.",
}

# Deterministic signal deltas: (activation_delta, satisfaction_delta).
_SIGNALS = {
    "tension": (0.10, -0.05),
    "frustrate": (0.15, -0.10),
    "satisfy": (-0.15, 0.20),
}
_ACTIVATION_DECAY_PER_HOUR = 0.02  # activation relaxes toward baseline
_SATISFACTION_DECAY_PER_HOUR = 0.01  # satisfaction fades, tension returns

_DRIVE_FIELDS = (
    "drive_id", "owner_entity_id", "enabled", "baseline", "activation",
    "satisfaction", "source", "updated_at", "cooldown_until",
)

try:
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None
try:
    import msvcrt
except ImportError:  # pragma: no cover
    msvcrt = None


class DriveError(RuntimeError):
    """The motivation store cannot be safely read or changed."""


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


def _clamp(value: float) -> float:
    return round(min(1.0, max(0.0, value)), 6)


def tension_of(state: DriveState) -> float:
    """Deterministic tension: activation weighted by unmet satisfaction."""
    return _clamp(state.activation * (1.0 - state.satisfaction))


def proposal_fingerprint(drive_id: str, summary: str) -> str:
    return hashlib.sha256(f"{drive_id}\n{summary}".encode()).hexdigest()[:32]


class DriveStore:
    """Versioned drive ledger with deterministic signal/decay updates."""

    def __init__(self, ctx) -> None:
        self._ctx = ctx
        self._identity = IdentityStore(ctx)

    def enabled(self) -> bool:
        return self._identity.enabled() and _as_bool(
            self._ctx.get_config("motivation_enabled", True), True
        )

    def path(self) -> Path:
        home = get_hermes_home().resolve()
        configured = Path(str(self._ctx.get_config("motivation_path", str(DEFAULT_MOTIVATION_PATH))))
        if configured.is_absolute():
            configured = DEFAULT_MOTIVATION_PATH
        candidate = (home / configured).resolve()
        if not candidate.is_relative_to(home):
            candidate = (home / DEFAULT_MOTIVATION_PATH).resolve()
        if not candidate.is_relative_to(home):
            raise DriveError("motivation path resolves outside the active profile")
        return candidate

    def _cooldown_hours(self) -> float:
        try:
            value = float(self._ctx.get_config("motivation_cooldown_hours", DEFAULT_COOLDOWN_HOURS))
        except (TypeError, ValueError):
            value = float(DEFAULT_COOLDOWN_HOURS)
        return min(168.0, max(0.0, value))

    def ensure(self) -> dict[str, Any]:
        owner = self._identity.ensure().entity_id
        path = self.path()
        with self._lock(path):
            if path.exists():
                return self._read_unlocked(path, owner)
            now = _fmt(_now_dt())
            drives: dict[str, Any] = {}
            for drive_id, baseline in STARTER_DRIVES:
                state = DriveState(
                    drive_id=drive_id, owner_entity_id=owner, enabled=True,
                    baseline=baseline, activation=baseline, satisfaction=0.5,
                    source=Provenance(source_type="identity", source_id="motivation-seed"),
                    updated_at=now,
                )
                drives[drive_id] = state.to_dict()
            data = {
                "motivation_version": MOTIVATION_VERSION,
                "owner_entity_id": owner,
                "updated_at": now,
                "drives": drives,
                "rejected": {},
            }
            self._write(path, data)
            return data

    def drives(self) -> list[DriveState]:
        owner = self._identity.read().entity_id
        path = self.path()
        with self._lock(path):
            data = self._read_unlocked(path, owner)
        return [DriveState.from_dict(data["drives"][k]) for k in sorted(data["drives"])]

    def set_drive(self, state: DriveState) -> DriveState:
        """Insert/replace one human-edited drive (forbidden ids refused)."""
        if not isinstance(state, DriveState):
            raise DriveError("drive must be a DriveState contract record")
        if state.drive_id in FORBIDDEN_DRIVES:
            raise DriveError("drive id is forbidden by the anti-runaway rules")
        owner = self._identity.read().entity_id
        if state.owner_entity_id != owner:
            raise DriveError("drive owner does not match entity identity")
        path = self.path()
        with self._lock(path):
            data = self._read_unlocked(path, owner)
            if state.drive_id not in data["drives"] and len(data["drives"]) >= MAX_DRIVES:
                raise DriveError("motivation drive ledger is full")
            data["drives"][state.drive_id] = state.to_dict()
            data["updated_at"] = _fmt(_now_dt())
            self._write(path, data)
            return state

    def record_signal(self, drive_id: str, signal: str, *, source: Provenance,
                      now: datetime | None = None) -> DriveState:
        if signal not in _SIGNALS:
            raise DriveError("unknown drive signal")
        if not isinstance(source, Provenance):
            raise DriveError("signal source must be a Provenance record")
        moment = now or _now_dt()
        owner = self._identity.read().entity_id
        path = self.path()
        with self._lock(path):
            data = self._read_unlocked(path, owner)
            record = data["drives"].get(drive_id)
            if record is None:
                raise DriveError("drive was not found")
            state = DriveState.from_dict(record)
            d_act, d_sat = _SIGNALS[signal]
            cooldown = ""
            if signal == "satisfy" and self._cooldown_hours() > 0:
                cooldown = _fmt(moment + timedelta(hours=self._cooldown_hours()))
            else:
                cooldown = state.cooldown_until
            updated = DriveState(
                drive_id=state.drive_id, owner_entity_id=owner, enabled=state.enabled,
                baseline=state.baseline,
                activation=_clamp(state.activation + d_act),
                satisfaction=_clamp(state.satisfaction + d_sat),
                source=source, updated_at=_fmt(moment), cooldown_until=cooldown,
            )
            data["drives"][drive_id] = updated.to_dict()
            data["updated_at"] = _fmt(moment)
            self._write(path, data)
            return updated

    def decay(self, *, now: datetime | None = None) -> list[DriveState]:
        """Relax activation toward baseline and fade satisfaction, by elapsed time."""
        moment = now or _now_dt()
        owner = self._identity.read().entity_id
        path = self.path()
        with self._lock(path):
            data = self._read_unlocked(path, owner)
            changed = False
            out: list[DriveState] = []
            for drive_id in sorted(data["drives"]):
                state = DriveState.from_dict(data["drives"][drive_id])
                hours = max(0.0, (moment - _parse(state.updated_at)).total_seconds() / 3600.0)
                if hours > 0:
                    step = _ACTIVATION_DECAY_PER_HOUR * hours
                    if state.activation > state.baseline:
                        activation = max(state.baseline, state.activation - step)
                    else:
                        activation = min(state.baseline, state.activation + step)
                    satisfaction = max(0.0, state.satisfaction - _SATISFACTION_DECAY_PER_HOUR * hours)
                    state = DriveState(
                        drive_id=state.drive_id, owner_entity_id=owner, enabled=state.enabled,
                        baseline=state.baseline, activation=_clamp(activation),
                        satisfaction=_clamp(satisfaction), source=state.source,
                        updated_at=_fmt(moment), cooldown_until=state.cooldown_until,
                    )
                    data["drives"][drive_id] = state.to_dict()
                    changed = True
                out.append(state)
            if changed:
                data["updated_at"] = _fmt(moment)
                self._write(path, data)
            return out

    def record_rejection(self, drive_id: str, summary: str, *, now: datetime | None = None) -> None:
        """Remember a rejected proposal; it is suppressed until cooldown passes."""
        moment = now or _now_dt()
        owner = self._identity.read().entity_id
        path = self.path()
        with self._lock(path):
            data = self._read_unlocked(path, owner)
            record = data["drives"].get(drive_id)
            if record is None:
                raise DriveError("drive was not found")
            fingerprint = proposal_fingerprint(drive_id, summary)
            rejected = list(data["rejected"].get(drive_id, []))
            if fingerprint not in rejected:
                rejected.append(fingerprint)
            data["rejected"][drive_id] = rejected[-MAX_REJECTED_PER_DRIVE:]
            state = DriveState.from_dict(record)
            cooldown = _fmt(moment + timedelta(hours=max(1.0, self._cooldown_hours()))) if self._cooldown_hours() > 0 else state.cooldown_until
            updated = DriveState(
                drive_id=state.drive_id, owner_entity_id=owner, enabled=state.enabled,
                baseline=state.baseline, activation=state.activation,
                satisfaction=state.satisfaction, source=state.source,
                updated_at=_fmt(moment), cooldown_until=cooldown,
            )
            data["drives"][drive_id] = updated.to_dict()
            data["updated_at"] = _fmt(moment)
            self._write(path, data)

    def proposals(self, *, now: datetime | None = None) -> list[dict[str, Any]]:
        """Bounded, deduplicated intent proposals — never goals (see module doc)."""
        moment = now or _now_dt()
        owner = self._identity.read().entity_id
        path = self.path()
        with self._lock(path):
            data = self._read_unlocked(path, owner)
        rejected = data.get("rejected", {})
        scored: list[tuple[float, str, dict[str, Any]]] = []
        for drive_id in sorted(data["drives"]):
            state = DriveState.from_dict(data["drives"][drive_id])
            if not state.enabled:
                continue
            if state.cooldown_until and _parse(state.cooldown_until) > moment:
                continue
            tension = tension_of(state)
            if tension < PROPOSAL_TENSION_THRESHOLD:
                continue
            summary = _DRIVE_SUMMARIES.get(drive_id, f"Make progress on {drive_id}.")
            if proposal_fingerprint(drive_id, summary) in rejected.get(drive_id, []):
                continue
            scored.append((tension, drive_id, {
                "origin": "intrinsic",
                "drive": drive_id,
                "proposal": summary,
                "expected_value": tension,
                "urgency": tension,
                "estimated_cost": "low",
                "risk": "read_only",
            }))
        scored.sort(key=lambda row: (-row[0], row[1]))
        return [row[2] for row in scored[:MAX_PROPOSALS]]

    # -- reading / validation ------------------------------------------
    def _read_unlocked(self, path: Path, owner: str) -> dict[str, Any]:
        if path.is_symlink():
            raise DriveError("motivation file must not be a symbolic link")
        if not path.is_file():
            raise DriveError("motivation file is missing")
        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                raise DriveError("motivation file exceeds its size limit")
            payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, yaml.YAMLError) as exc:
            raise DriveError("motivation file is unreadable or malformed") from exc
        if not isinstance(payload, dict):
            raise DriveError("motivation document must be a mapping")
        version = payload.get("motivation_version")
        if isinstance(version, bool) or version != MOTIVATION_VERSION:
            raise DriveError("motivation version is unsupported")
        if payload.get("owner_entity_id") != owner:
            raise DriveError("motivation owner does not match entity identity")
        if not _timestamp_ok(payload.get("updated_at")):
            raise DriveError("motivation updated_at is invalid")
        drives = payload.get("drives")
        if not isinstance(drives, dict) or len(drives) > MAX_DRIVES:
            raise DriveError("motivation drives mapping is invalid or oversized")
        for drive_id, record in drives.items():
            if drive_id in FORBIDDEN_DRIVES:
                raise DriveError("motivation file carries a forbidden drive")
            try:
                state = DriveState.from_dict(record)
            except (AgencyContractError, KeyError, TypeError) as exc:
                raise DriveError("motivation drive record is invalid") from exc
            if state.drive_id != drive_id or state.owner_entity_id != owner:
                raise DriveError("motivation drive record is invalid")
        rejected = payload.get("rejected")
        if not isinstance(rejected, dict):
            raise DriveError("motivation rejected mapping is invalid")
        for drive_id, fingerprints in rejected.items():
            if drive_id not in drives or not isinstance(fingerprints, list) or len(fingerprints) > MAX_REJECTED_PER_DRIVE:
                raise DriveError("motivation rejected record is invalid")
            if any(not isinstance(fp, str) or len(fp) > 64 for fp in fingerprints):
                raise DriveError("motivation rejected record is invalid")
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


class DriveBridge:
    """Create the motivation store at session start; offer its bounded packet."""

    def __init__(self, ctx) -> None:
        self._store = DriveStore(ctx)

    def hooks(self):
        return (("on_session_start", self.on_session_start),)

    def on_session_start(self, **_: Any) -> None:
        if not self._store.enabled():
            return
        try:
            self._store.ensure()
        except (IdentityError, DriveError, OSError):
            return

    def packet_items(self, session_id: str, user_message: Any = "") -> list[ContextItem]:
        if not self._store.enabled():
            return []
        try:
            proposals = self._store.proposals()
            states = {s.drive_id: s for s in self._store.drives()}
        except (IdentityError, DriveError, OSError):
            return []
        items: list[ContextItem] = []
        for proposal in proposals[:3]:
            state = states[proposal["drive"]]
            items.append(ContextItem(
                section="current_state",
                content=(
                    f"Drive {proposal['drive']}: tension {proposal['expected_value']:.2f} "
                    f"(activation {state.activation:.2f}, satisfaction {state.satisfaction:.2f}) — "
                    f"{proposal['proposal']}"
                ),
                source="motivation",
                record_id=proposal["drive"],
                priority=proposal["expected_value"],
                updated_at=_parse(state.updated_at).timestamp(),
            ))
        return items


__all__ = [
    "MOTIVATION_VERSION", "DEFAULT_MOTIVATION_PATH", "STARTER_DRIVES",
    "FORBIDDEN_DRIVES", "MAX_PROPOSALS", "PROPOSAL_TENSION_THRESHOLD",
    "DriveError", "DriveStore", "DriveBridge", "tension_of", "proposal_fingerprint",
]
