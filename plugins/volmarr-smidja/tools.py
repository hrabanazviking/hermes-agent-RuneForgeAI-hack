"""Bounded read-only tools for the official local Seidr-Smidja Loom."""

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


_MAX_BYTES = 64 * 1024
_RUNNER = Path(__file__).with_name("_runner.py").resolve()
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

SMIDJA_SPEC_VALIDATE_SCHEMA = {
    "name": "smidja_spec_validate",
    "description": (
        "Validate one bounded avatar spec through Seidr-Smidja's public Loom API. "
        "This read-only preflight does not dispatch the forge, Blender, REST, MCP, or Vroid control."
    ),
    "parameters": {
        "type": "object",
        "properties": {"spec_path": {"type": "string", "minLength": 1, "maxLength": 240}},
        "required": ["spec_path"],
        "additionalProperties": False,
    },
}


def _root(value: Any, marker: str | None = None) -> Path | None:
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


def _python(value: Any) -> Path | None:
    if not isinstance(value, str) or not value.strip() or "\x00" in value:
        return None
    candidate = Path(value.strip()).expanduser()
    if not candidate.is_absolute() and candidate.parent == Path("."):
        found = shutil.which(value.strip())
        if found is None:
            return None
        candidate = Path(found)
    try:
        resolved = candidate.resolve()
    except OSError:
        return None
    return resolved if resolved.is_file() and os.access(resolved, os.X_OK) else None


def _timeout(ctx) -> float:
    try:
        value = float(ctx.get_config("timeout_seconds", 10))
    except (TypeError, ValueError):
        value = 10.0
    return min(30.0, max(1.0, value if math.isfinite(value) else 10.0))


def _env() -> dict[str, str]:
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


def build_spec_validate_handler(ctx):
    def handle(args: dict[str, Any], **_kwargs: Any) -> str:
        if set(args) != {"spec_path"}:
            return tool_error("spec_path is required")
        engine = _root(
            ctx.get_config("engine_root", ""), marker="src/seidr_smidja/loom/loader.py"
        )
        spec_root = _root(ctx.get_config("spec_root", ""))
        python = _python(ctx.get_config("python_path", "") or sys.executable)
        if engine is None or spec_root is None or python is None or not _RUNNER.is_file():
            return tool_error("Configure volmarr-smidja engine_root, spec_root, and Python.")
        value = args.get("spec_path")
        if not isinstance(value, str) or not value.strip() or len(value) > 240 or "\x00" in value:
            return tool_error("spec_path must be a bounded relative YAML or JSON path")
        relative = Path(value.strip())
        if relative.is_absolute() or relative.suffix.casefold() not in {".yaml", ".yml", ".json"}:
            return tool_error("spec_path must be a bounded relative YAML or JSON path")
        try:
            spec_file = (spec_root / relative).resolve()
            spec_file.relative_to(spec_root)
            size = spec_file.stat().st_size
        except (OSError, ValueError):
            return tool_error("spec_path must remain within spec_root")
        if not spec_file.is_file() or not 1 <= size <= _MAX_BYTES:
            return tool_error("spec_path must name a file from 1 byte to 64 KiB")
        try:
            completed = subprocess.run(
                [str(python), "-B", "-P", "-s", str(_RUNNER), str(engine), str(spec_file)],
                env=_env(),
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=_timeout(ctx),
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return tool_error("Seidr-Smidja Loom validation could not complete")
        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        if (
            completed.returncode != 0
            or len(stdout.encode("utf-8", errors="replace")) > _MAX_BYTES
            or len(stderr.encode("utf-8", errors="replace")) > _MAX_BYTES
        ):
            return tool_error("Seidr-Smidja Loom validation failed")
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError:
            return tool_error("Seidr-Smidja returned an invalid Loom response")
        if not isinstance(payload, dict) or not isinstance(payload.get("valid"), bool) or not isinstance(
            payload.get("failures"), list
        ):
            return tool_error("Seidr-Smidja returned an invalid Loom response")
        result = {
            "success": True,
            "calculation": "smidja_spec_validate",
            "spec_path": relative.as_posix(),
            **payload,
            "forge_dispatched": False,
            "blender_launched": False,
            "output_created": False,
            "source": {
                "engine": "Seidr-Smidja",
                "api": "loom.load_and_validate",
                "license_metadata": "CONFLICT: root Apache-2.0; pyproject MIT",
            },
        }
        return tool_result(result)

    return handle


def register_tools(ctx) -> None:
    ctx.register_tool(
        name="smidja_spec_validate",
        toolset="volmarr_smidja",
        schema=SMIDJA_SPEC_VALIDATE_SCHEMA,
        handler=build_spec_validate_handler(ctx),
        description=SMIDJA_SPEC_VALIDATE_SCHEMA["description"],
        emoji="🧵",
    )
