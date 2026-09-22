"""Idempotent Hermes-cron routines; no plugin-owned scheduler or resident loop."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from hermes_constants import get_hermes_home
from utils import atomic_write_text

from .goals import GoalStore
from .heartbeat import HeartbeatService
from .verdandi import VerdandiPublisher


ROUTINE_SCHEMA = "runeforge.entity.routine"
ROUTINE_SCHEMA_VERSION = 1
FREQUENT_JOB_NAME = "Volmarr Frequent Continuity"
FREQUENT_SCHEDULE = "every 10m"
FREQUENT_SCRIPT_NAME = "volmarr_frequent_continuity.py"


class RoutineError(RuntimeError):
    """A routine definition cannot be inspected, installed, or executed safely."""


@dataclass(frozen=True)
class RoutineStatus:
    status: str
    name: str
    schedule: str
    script_path: str
    job_id: str | None = None
    enabled: bool | None = None
    definition_current: bool = False
    drift: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RoutineRunReport:
    success: bool
    routine: str
    heartbeat_sequence: int
    planned_goals: int
    active_goals: int
    blocked_goals: int
    event_published: bool

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _script_content() -> str:
    return '''"""Generated entrypoint for the Volmarr frequent continuity routine."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def _hermes_executable() -> str | None:
    discovered = shutil.which("hermes")
    if discovered:
        return discovered
    suffix = ".exe" if sys.platform == "win32" else ""
    sibling = Path(sys.executable).with_name(f"hermes{suffix}")
    return str(sibling) if sibling.is_file() else None


def main() -> int:
    executable = _hermes_executable()
    if executable is None:
        print("Hermes executable was not found for the continuity routine.", file=sys.stderr)
        return 1
    try:
        completed = subprocess.run(
            [
                executable,
                "volmarr",
                "routines",
                "run",
                "--kind",
                "frequent",
                "--json",
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"Continuity routine failed: {type(exc).__name__}", file=sys.stderr)
        return 1
    if completed.returncode:
        detail = (completed.stderr or completed.stdout or "routine failed").strip()[:2000]
        print(detail, file=sys.stderr)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
'''


class RoutineManager:
    """Reconcile a named cron job through Hermes' existing cron management surface."""

    def __init__(
        self,
        ctx,
        *,
        name: str = FREQUENT_JOB_NAME,
        schedule: str = FREQUENT_SCHEDULE,
        script_name: str = FREQUENT_SCRIPT_NAME,
        script_content: str | None = None,
    ) -> None:
        self._ctx = ctx
        self._name = name
        self._schedule = schedule
        self._script_name = script_name
        self._script_content = script_content or _script_content()

    def script_path(self) -> Path:
        return get_hermes_home().resolve() / "scripts" / self._script_name

    def status(self) -> RoutineStatus:
        jobs = self._jobs()
        matches = [job for job in jobs if job.get("name") == self._name]
        script_path = self.script_path()
        if len(matches) > 1:
            return RoutineStatus(
                "ambiguous",
                self._name,
                self._schedule,
                str(script_path),
            )
        if not matches:
            return RoutineStatus(
                "uninstalled",
                self._name,
                self._schedule,
                str(script_path),
            )
        job = matches[0]
        drift = self._drift(job, script_path)
        current = not drift
        enabled = bool(job.get("enabled", True))
        status = "installed_active" if enabled else "installed_paused"
        if not current:
            status = "drifted"
        return RoutineStatus(
            status,
            self._name,
            self._schedule,
            str(script_path),
            job_id=str(job.get("job_id") or "") or None,
            enabled=enabled,
            definition_current=current,
            drift=drift,
        )

    def install(self, *, activate: bool = False) -> RoutineStatus:
        script_path = self.script_path()
        atomic_write_text(
            script_path,
            self._script_content,
            create_mode=0o700,
        )
        jobs = self._jobs()
        matches = [job for job in jobs if job.get("name") == self._name]
        if len(matches) > 1:
            raise RoutineError(
                "multiple cron jobs use the Volmarr routine name; resolve them manually"
            )
        if not matches:
            result = self._cronjob(
                action="create",
                prompt="",
                schedule=self._schedule,
                name=self._name,
                script=self._script_name,
                no_agent=True,
                deliver="local",
                paused=True,
                paused_reason="Installed paused; activate explicitly after reviewing the routine.",
            )
            if not result.get("success"):
                raise RoutineError(str(result.get("error") or "cron job creation failed"))
            if activate:
                result = self._cronjob(action="resume", job_id=str(result["job_id"]))
                if not result.get("success"):
                    raise RoutineError(str(result.get("error") or "cron job resume failed"))
        else:
            job = matches[0]
            job_id = str(job["job_id"])
            if not self._job_current(job):
                result = self._cronjob(
                    action="update",
                    job_id=job_id,
                    prompt="",
                    schedule=self._schedule,
                    name=self._name,
                    script=self._script_name,
                    no_agent=True,
                    deliver="local",
                )
                if not result.get("success"):
                    raise RoutineError(str(result.get("error") or "cron job update failed"))
            if activate and not bool(job.get("enabled", True)):
                result = self._cronjob(action="resume", job_id=job_id)
                if not result.get("success"):
                    raise RoutineError(str(result.get("error") or "cron job resume failed"))
        return self.status()

    @staticmethod
    def _cronjob(**kwargs: Any) -> dict[str, Any]:
        from tools.cronjob_tools import cronjob

        try:
            result = json.loads(cronjob(**kwargs))
        except (TypeError, json.JSONDecodeError) as exc:
            raise RoutineError("Hermes cron returned an invalid response") from exc
        if not isinstance(result, dict):
            raise RoutineError("Hermes cron returned an invalid response")
        return result

    def _jobs(self) -> list[dict[str, Any]]:
        result = self._cronjob(action="list", include_disabled=True)
        jobs = result.get("jobs")
        if result.get("success") is not True or not isinstance(jobs, list):
            raise RoutineError(str(result.get("error") or "cron jobs could not be listed"))
        return [job for job in jobs if isinstance(job, dict)]

    def _job_current(self, job: dict[str, Any]) -> bool:
        return not self._job_drift(job)

    def _job_drift(self, job: dict[str, Any]) -> tuple[str, ...]:
        drift: list[str] = []
        if job.get("schedule") != self._schedule:
            drift.append("schedule")
        if job.get("script") != self._script_name:
            drift.append("script")
        if job.get("no_agent") is not True:
            drift.append("no_agent")
        if job.get("deliver") != "local":
            drift.append("deliver")
        if str(job.get("prompt_preview") or "").strip():
            drift.append("prompt")
        return tuple(drift)

    def _drift(self, job: dict[str, Any], path: Path) -> tuple[str, ...]:
        drift = list(self._job_drift(job))
        if not self._script_current(path):
            drift.append("script_content")
        return tuple(drift)

    def _script_current(self, path: Path) -> bool:
        try:
            return path.is_file() and not path.is_symlink() and path.read_text(
                encoding="utf-8"
            ) == self._script_content
        except (OSError, UnicodeError):
            return False


class RoutineService:
    def __init__(self, ctx, publisher: VerdandiPublisher | None = None) -> None:
        self._ctx = ctx
        self._publisher = publisher or VerdandiPublisher()

    def run_frequent(self) -> RoutineRunReport:
        heartbeat = HeartbeatService(self._ctx, publisher=self._publisher).pulse("cron")
        goals = GoalStore(self._ctx)
        goals.ensure()
        records = goals.get()["goals"].values()
        counts = {
            status: sum(1 for goal in records if goal["status"] == status)
            for status in ("planned", "active", "blocked")
        }
        published = self._publisher.publish(
            self._ctx,
            "hermes.entity.routine.completed",
            {
                "routine": "frequent",
                "heartbeat_sequence": heartbeat.sequence,
                "planned_goals": counts["planned"],
                "active_goals": counts["active"],
                "blocked_goals": counts["blocked"],
            },
            schema=ROUTINE_SCHEMA,
            schema_version=ROUTINE_SCHEMA_VERSION,
        )
        return RoutineRunReport(
            True,
            "frequent",
            int(heartbeat.sequence or 0),
            counts["planned"],
            counts["active"],
            counts["blocked"],
            published,
        )
