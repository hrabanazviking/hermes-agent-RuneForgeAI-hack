"""Bounded subprocess tools for the official AI Agent Astrology Engine."""

from __future__ import annotations

import math
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from tools.registry import tool_error, tool_result


_MAX_OUTPUT_BYTES = 64 * 1024
_ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
_BASE_ENV = (
    "PATH",
    "HOME",
    "USERPROFILE",
    "SYSTEMROOT",
    "WINDIR",
    "TMPDIR",
    "TEMP",
    "LANG",
    "LC_ALL",
)

ASTROLOGY_LUNAR_SCHEMA = {
    "name": "astrology_lunar",
    "description": (
        "Calculate the current lunar phase, illumination, void-of-course status, "
        "next lunations, and Moon aspects locally with the configured official "
        "Astrology Engine. Returns calculations only, not an LLM interpretation."
    ),
    "parameters": {
        "type": "object",
        "properties": {},
        "additionalProperties": False,
    },
}


def _configured_file(value: Any, *, executable: bool = False) -> Path | None:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        return None
    configured = value.strip()
    candidate = Path(configured).expanduser()
    if not candidate.is_absolute() and candidate.parent == Path("."):
        found = shutil.which(configured) if executable else None
        if found is None:
            return None
        candidate = Path(found)
    try:
        resolved = candidate.resolve()
    except OSError:
        return None
    if not resolved.is_file():
        return None
    if executable and not os.access(resolved, os.X_OK):
        return None
    return resolved


def _runtime(ctx) -> tuple[Path, Path] | None:
    engine = _configured_file(ctx.get_config("engine_path", ""))
    python_value = ctx.get_config("python_path", "")
    python = _configured_file(python_value or sys.executable, executable=True)
    if engine is None or engine.suffix.lower() != ".py" or python is None:
        return None
    return python, engine


def _timeout(ctx) -> float:
    try:
        value = float(ctx.get_config("timeout_seconds", 20))
    except (TypeError, ValueError):
        value = 20.0
    if not math.isfinite(value):
        value = 20.0
    return min(60.0, max(1.0, value))


def _child_env() -> dict[str, str]:
    env = {key: os.environ[key] for key in _BASE_ENV if key in os.environ}
    env.update({"NO_COLOR": "1", "PYTHONUTF8": "1"})
    return env


def _run_lunar(ctx) -> tuple[str | None, str | None]:
    runtime = _runtime(ctx)
    if runtime is None:
        return None, (
            "Configure volmarr-astrology engine_path and a Python interpreter "
            "with pyswisseph installed."
        )
    python, engine = runtime
    timeout = _timeout(ctx)
    try:
        completed = subprocess.run(
            [str(python), str(engine), "lunar"],
            env=_child_env(),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return None, "The local astrology calculation timed out."
    except OSError:
        return None, "The local Astrology Engine could not be started."

    stdout = completed.stdout or ""
    stderr = completed.stderr or ""
    if (
        len(stdout.encode("utf-8", errors="replace")) > _MAX_OUTPUT_BYTES
        or len(stderr.encode("utf-8", errors="replace")) > _MAX_OUTPUT_BYTES
    ):
        return None, "The local Astrology Engine returned an oversized response."
    if completed.returncode != 0:
        return None, "The local Astrology Engine failed to calculate lunar state."
    report = _ANSI_RE.sub("", stdout).strip()
    if "pyswisseph required" in f"{report}\n{stderr}".lower():
        return None, (
            "The configured Astrology Engine Python environment does not have "
            "pyswisseph installed."
        )
    if not report:
        return None, "The local Astrology Engine returned no lunar calculation."
    return report, None


def build_lunar_handler(ctx):
    def handle(args: dict[str, Any], **_kwargs: Any) -> str:
        if args:
            return tool_error("astrology_lunar does not accept arguments")
        report, error = _run_lunar(ctx)
        if error is not None:
            return tool_error(error)
        return tool_result(
            {
                "success": True,
                "engine": "hrabanazviking/astrology-engine",
                "calculation": "lunar",
                "interpretation_included": False,
                "report": report,
            }
        )

    return handle


def register_tools(ctx) -> None:
    ctx.register_tool(
        name="astrology_lunar",
        toolset="volmarr_astrology",
        schema=ASTROLOGY_LUNAR_SCHEMA,
        handler=build_lunar_handler(ctx),
        check_fn=lambda: _runtime(ctx) is not None,
        description=ASTROLOGY_LUNAR_SCHEMA["description"],
        emoji="🌙",
    )
