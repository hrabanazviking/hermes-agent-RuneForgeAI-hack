"""Bounded read-only tools for the official local Hamr engine."""

from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from tools.registry import tool_error, tool_result


_MAX_OUTPUT_BYTES = 64 * 1024
_MAX_SPEC_BYTES = 64 * 1024
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
_RUNNER = Path(__file__).with_name("_runner.py").resolve()

HAMR_SPEC_VALIDATE_SCHEMA = {
    "name": "hamr_spec_validate",
    "description": (
        "Validate one YAML avatar spec through the configured official local Hamr engine. "
        "This read-only preflight does not launch Blender or build an avatar."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "spec_path": {
                "type": "string",
                "minLength": 1,
                "maxLength": 240,
                "description": "YAML path relative to the configured spec_root.",
            }
        },
        "required": ["spec_path"],
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
    if not resolved.is_file() or (executable and not os.access(resolved, os.X_OK)):
        return None
    return resolved


def _configured_root(value: Any, *, marker: str | None = None) -> Path | None:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        return None
    candidate = Path(value.strip()).expanduser()
    if not candidate.is_absolute():
        return None
    try:
        resolved = candidate.resolve()
    except OSError:
        return None
    if not resolved.is_dir() or (marker and not (resolved / marker).is_file()):
        return None
    return resolved


def _runtime(ctx) -> tuple[Path, Path, Path] | None:
    engine_root = _configured_root(
        ctx.get_config("engine_root", ""), marker="src/hamr/core/spec.py"
    )
    spec_root = _configured_root(ctx.get_config("spec_root", ""))
    python_value = ctx.get_config("python_path", "")
    python = _configured_file(python_value or sys.executable, executable=True)
    if engine_root is None or spec_root is None or python is None or not _RUNNER.is_file():
        return None
    return python, engine_root, spec_root


def _timeout(ctx) -> float:
    try:
        value = float(ctx.get_config("timeout_seconds", 10))
    except (TypeError, ValueError):
        value = 10.0
    if not math.isfinite(value):
        value = 10.0
    return min(30.0, max(1.0, value))


def _child_env() -> dict[str, str]:
    env = {key: os.environ[key] for key in _BASE_ENV if key in os.environ}
    env.update(
        {
            "NO_COLOR": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONUTF8": "1",
            "PYTHONNOUSERSITE": "1",
        }
    )
    return env


def _spec_file(spec_root: Path, value: Any) -> tuple[Path | None, str | None]:
    if not isinstance(value, str) or not value.strip() or len(value) > 240 or "\x00" in value:
        return None, None
    relative = Path(value.strip())
    if relative.is_absolute() or relative.suffix.casefold() not in {".yaml", ".yml"}:
        return None, None
    try:
        resolved = (spec_root / relative).resolve()
        resolved.relative_to(spec_root)
        size = resolved.stat().st_size
    except (OSError, ValueError):
        return None, None
    if not resolved.is_file() or not 1 <= size <= _MAX_SPEC_BYTES:
        return None, None
    return resolved, relative.as_posix()


def build_spec_validate_handler(ctx):
    def handle(args: dict[str, Any], **_kwargs: Any) -> str:
        if set(args) != {"spec_path"}:
            return tool_error("spec_path is required")
        runtime = _runtime(ctx)
        if runtime is None:
            return tool_error(
                "Configure volmarr-hamr engine_root, spec_root, and a compatible Python interpreter."
            )
        python, engine_root, spec_root = runtime
        spec_file, relative_path = _spec_file(spec_root, args.get("spec_path"))
        if spec_file is None or relative_path is None:
            return tool_error(
                "spec_path must name an existing YAML file of at most 64 KiB within spec_root"
            )
        try:
            completed = subprocess.run(
                [str(python), "-B", "-P", "-s", str(_RUNNER), str(engine_root), str(spec_file)],
                env=_child_env(),
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=_timeout(ctx),
                check=False,
            )
        except subprocess.TimeoutExpired:
            return tool_error("Hamr spec validation timed out")
        except OSError:
            return tool_error("Hamr spec validation could not be started")

        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        if (
            len(stdout.encode("utf-8", errors="replace")) > _MAX_OUTPUT_BYTES
            or len(stderr.encode("utf-8", errors="replace")) > _MAX_OUTPUT_BYTES
        ):
            return tool_error("Hamr returned an oversized validation response")
        if completed.returncode != 0:
            return tool_error("Hamr could not validate the spec")
        try:
            payload = json.loads(stdout)
        except (TypeError, json.JSONDecodeError):
            return tool_error("Hamr returned an invalid validation response")
        if not isinstance(payload, dict) or payload.get("status") != "ok":
            return tool_error("Hamr returned an invalid validation response")
        valid = payload.get("valid")
        errors = payload.get("errors")
        if not isinstance(valid, bool) or not isinstance(errors, list) or any(
            not isinstance(error, str) for error in errors
        ):
            return tool_error("Hamr returned an invalid validation response")
        result = {
            "success": True,
            "calculation": "hamr_spec_validate",
            "spec_path": relative_path,
            "valid": valid,
            "errors": errors,
            "blender_launched": False,
            "output_created": False,
            "source": {"engine": "Hamr", "api": "Spec.from_yaml", "license": "MIT"},
        }
        if valid:
            summary = payload.get("summary")
            if not isinstance(summary, dict) or set(summary) != {
                "name",
                "version",
                "export_format",
            } or any(not isinstance(value, str) for value in summary.values()):
                return tool_error("Hamr returned an invalid validation response")
            result["summary"] = summary
        return tool_result(result)

    return handle


def register_tools(ctx) -> None:
    ctx.register_tool(
        name="hamr_spec_validate",
        toolset="volmarr_hamr",
        schema=HAMR_SPEC_VALIDATE_SCHEMA,
        handler=build_spec_validate_handler(ctx),
        description=HAMR_SPEC_VALIDATE_SCHEMA["description"],
        emoji="🔨",
    )
