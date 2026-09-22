"""Non-destructive entity consolidation checkpoints and daily cron attachment."""

from __future__ import annotations

import hashlib
import json
import os
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hermes_constants import get_hermes_home, mkdir_under_hermes_home
from tools.registry import tool_error, tool_result
from utils import atomic_json_write

from .goals import GoalError, GoalStore
from .heartbeat import HeartbeatError, HeartbeatStore
from .identity import IdentityError, IdentityStore
from .relationships import RelationshipError, RelationshipStore
from .routines import RoutineManager
from .verdandi import VerdandiPublisher


CONSOLIDATION_VERSION = 1
CONSOLIDATION_SCHEMA = "runeforge.entity.consolidation"
CONSOLIDATION_SCHEMA_VERSION = 1
DEFAULT_CONSOLIDATION_PATH = Path("entity") / "consolidation.json"
MAX_FILE_BYTES = 128 * 1024
SLEEP_JOB_NAME = "Volmarr Daily Consolidation"
SLEEP_SCHEDULE = "every 1440m"
SLEEP_SCRIPT_NAME = "volmarr_daily_consolidation.py"
SOURCES = {"manual", "cron", "tool"}

try:
    import fcntl
except ImportError:  # pragma: no cover - platform branch
    fcntl = None
try:
    import msvcrt
except ImportError:  # pragma: no cover - platform branch
    msvcrt = None


class ConsolidationError(RuntimeError):
    """A consolidation checkpoint cannot be safely read or committed."""


@dataclass(frozen=True)
class ConsolidationReport:
    healthy: bool
    status: str
    consolidation_path: str
    sequence: int | None = None
    last_run_at: str | None = None
    source: str | None = None
    summary: dict[str, int] | None = None
    event_published: bool | None = None
    error_type: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _valid_timestamp(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _digest(value: dict[str, Any]) -> str:
    canonical = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


class ConsolidationStore:
    def __init__(self, ctx) -> None:
        self._ctx = ctx

    def path(self) -> Path:
        home = get_hermes_home().resolve()
        configured = Path(
            str(
                self._ctx.get_config(
                    "consolidation_path", str(DEFAULT_CONSOLIDATION_PATH)
                )
            )
        )
        if configured.is_absolute():
            configured = DEFAULT_CONSOLIDATION_PATH
        candidate = (home / configured).resolve()
        if not candidate.is_relative_to(home):
            candidate = (home / DEFAULT_CONSOLIDATION_PATH).resolve()
        if not candidate.is_relative_to(home):
            raise ConsolidationError(
                "consolidation path resolves outside the active profile"
            )
        return candidate

    def read(self, owner: str) -> dict[str, Any]:
        path = self.path()
        with self._lock(path):
            return self._read_unlocked(path, owner)

    def commit(
        self,
        *,
        owner: str,
        source: str,
        summary: dict[str, int],
        component_digests: dict[str, str],
    ) -> dict[str, Any]:
        if source not in SOURCES:
            raise ConsolidationError("consolidation source is invalid")
        path = self.path()
        with self._lock(path):
            sequence = 0
            if path.exists():
                sequence = self._read_unlocked(path, owner)["consolidation_sequence"]
            checkpoint = {
                "consolidation_version": CONSOLIDATION_VERSION,
                "owner_entity_id": owner,
                "consolidation_sequence": sequence + 1,
                "last_run_at": _now(),
                "source": source,
                "summary": summary,
                "component_digests": component_digests,
            }
            atomic_json_write(
                path,
                checkpoint,
                indent=2,
                sort_keys=False,
                ensure_ascii=False,
                mode=0o600,
            )
            return checkpoint

    def _read_unlocked(self, path: Path, owner: str) -> dict[str, Any]:
        if path.is_symlink():
            raise ConsolidationError("consolidation file must not be a symbolic link")
        if not path.is_file():
            raise ConsolidationError("consolidation file is missing")
        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                raise ConsolidationError("consolidation file exceeds its size limit")
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ConsolidationError(
                "consolidation file is unreadable or malformed"
            ) from exc
        if not isinstance(payload, dict):
            raise ConsolidationError("consolidation document must be an object")
        version = payload.get("consolidation_version")
        if isinstance(version, bool) or version != CONSOLIDATION_VERSION:
            raise ConsolidationError("consolidation version is unsupported")
        if payload.get("owner_entity_id") != owner:
            raise ConsolidationError("consolidation owner does not match entity identity")
        sequence = payload.get("consolidation_sequence")
        if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1:
            raise ConsolidationError("consolidation sequence is invalid")
        if not _valid_timestamp(payload.get("last_run_at")):
            raise ConsolidationError("consolidation timestamp is invalid")
        if payload.get("source") not in SOURCES:
            raise ConsolidationError("consolidation source is invalid")
        summary = payload.get("summary")
        if not isinstance(summary, dict) or any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0
            for value in summary.values()
        ):
            raise ConsolidationError("consolidation summary is invalid")
        digests = payload.get("component_digests")
        if not isinstance(digests, dict) or any(
            not isinstance(value, str)
            or len(value) != 64
            or any(char not in "0123456789abcdef" for char in value)
            for value in digests.values()
        ):
            raise ConsolidationError("consolidation component digests are invalid")
        return payload

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


class ConsolidationService:
    """Validate durable domains and record a content-free checkpoint; mutate none of them."""

    def __init__(self, ctx, publisher: VerdandiPublisher | None = None) -> None:
        self._ctx = ctx
        self._publisher = publisher or VerdandiPublisher()
        self._store = ConsolidationStore(ctx)

    def run(self, source: str) -> ConsolidationReport:
        identity_store = IdentityStore(self._ctx)
        identity = identity_store.ensure()
        relationships_store = RelationshipStore(self._ctx)
        relationships = relationships_store.ensure()
        goals_store = GoalStore(self._ctx)
        goals = goals_store.ensure()
        heartbeat_store = HeartbeatStore(self._ctx)
        heartbeat = heartbeat_store.ensure()

        relationship_records = relationships["relationships"].values()
        goal_records = goals["goals"].values()
        summary = {
            "relationships_total": len(relationships["relationships"]),
            "relationships_active": sum(
                1 for record in relationship_records if record["status"] == "active"
            ),
            "goals_total": len(goals["goals"]),
            "goals_planned": sum(
                1 for record in goal_records if record["status"] == "planned"
            ),
            "goals_active": sum(
                1 for record in goals["goals"].values() if record["status"] == "active"
            ),
            "goals_blocked": sum(
                1 for record in goals["goals"].values() if record["status"] == "blocked"
            ),
            "goals_completed": sum(
                1 for record in goals["goals"].values() if record["status"] == "completed"
            ),
            "heartbeat_sequence": heartbeat["heartbeat_sequence"],
        }
        component_digests = {
            "identity": _digest(identity.as_dict()),
            "relationships": _digest(relationships),
            "goals": _digest(goals),
            "continuity": _digest(heartbeat),
        }
        checkpoint = self._store.commit(
            owner=identity.entity_id,
            source=source,
            summary=summary,
            component_digests=component_digests,
        )
        published = self._publisher.publish(
            self._ctx,
            "hermes.entity.consolidation.completed",
            {
                "consolidation_sequence": checkpoint["consolidation_sequence"],
                "source": source,
                **summary,
            },
            schema=CONSOLIDATION_SCHEMA,
            schema_version=CONSOLIDATION_SCHEMA_VERSION,
        )
        return ConsolidationReport(
            True,
            "healthy",
            str(self._store.path()),
            sequence=checkpoint["consolidation_sequence"],
            last_run_at=checkpoint["last_run_at"],
            source=source,
            summary=summary,
            event_published=published,
        )


def probe_consolidation(ctx) -> ConsolidationReport:
    store = ConsolidationStore(ctx)
    try:
        path = store.path()
    except ConsolidationError as exc:
        return ConsolidationReport(
            False,
            "unsafe_path",
            "",
            error_type=type(exc).__name__,
        )
    try:
        owner = IdentityStore(ctx).read().entity_id
        state = store.read(owner)
    except ConsolidationError as exc:
        status = "never_run" if not path.exists() else "invalid"
        return ConsolidationReport(
            False,
            status,
            str(path),
            error_type=type(exc).__name__,
        )
    except (IdentityError, OSError) as exc:
        return ConsolidationReport(
            False,
            "unavailable",
            str(path),
            error_type=type(exc).__name__,
        )
    return ConsolidationReport(
        True,
        "healthy",
        str(path),
        sequence=state["consolidation_sequence"],
        last_run_at=state["last_run_at"],
        source=state["source"],
        summary=state["summary"],
    )


def _sleep_script_content() -> str:
    return '''"""Generated entrypoint for the Volmarr daily consolidation routine."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def main() -> int:
    suffix = ".exe" if sys.platform == "win32" else ""
    executable = shutil.which("hermes")
    if executable is None:
        sibling = Path(sys.executable).with_name(f"hermes{suffix}")
        executable = str(sibling) if sibling.is_file() else None
    if executable is None:
        print("Hermes executable was not found for consolidation.", file=sys.stderr)
        return 1
    try:
        completed = subprocess.run(
            [
                executable,
                "volmarr",
                "sleep",
                "run",
                "--source",
                "cron",
                "--json",
            ],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"Consolidation failed: {type(exc).__name__}", file=sys.stderr)
        return 1
    if completed.returncode:
        detail = (completed.stderr or completed.stdout or "consolidation failed").strip()[:2000]
        print(detail, file=sys.stderr)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
'''


def sleep_routine_manager(ctx) -> RoutineManager:
    return RoutineManager(
        ctx,
        name=SLEEP_JOB_NAME,
        schedule=SLEEP_SCHEDULE,
        script_name=SLEEP_SCRIPT_NAME,
        script_content=_sleep_script_content(),
    )


ENTITY_SLEEP_SCHEMA = {
    "name": "entity_sleep_cycle",
    "description": (
        "Validate durable entity state and record a non-destructive consolidation checkpoint. "
        "This does not rewrite memory, relationships, goals, or world state."
    ),
    "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
}


def build_entity_sleep_handler(ctx):
    def handle(_args: dict[str, Any], **_kwargs: Any) -> str:
        try:
            report = ConsolidationService(ctx).run("tool")
        except (
            IdentityError,
            RelationshipError,
            GoalError,
            HeartbeatError,
            ConsolidationError,
            OSError,
        ) as exc:
            return tool_error(str(exc))
        return tool_result(report.as_dict())

    return handle


def register_sleep_tool(ctx) -> None:
    ctx.register_tool(
        name="entity_sleep_cycle",
        toolset="volmarr_identity",
        schema=ENTITY_SLEEP_SCHEMA,
        handler=build_entity_sleep_handler(ctx),
        description=ENTITY_SLEEP_SCHEMA["description"],
        emoji="🌙",
    )
