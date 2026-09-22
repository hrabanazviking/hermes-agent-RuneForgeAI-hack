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
_PRESETS_RUNNER = Path(__file__).with_name("_presets_runner.py").resolve()
_BUDGET_RUNNER = Path(__file__).with_name("_budget_runner.py").resolve()
_ARTIFACT_RUNNER = Path(__file__).with_name("_artifact_runner.py").resolve()

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

HAMR_PRESETS_SCHEMA = {
    "name": "hamr_presets",
    "description": (
        "List the configured official Hamr engine's body and character preset catalogs. "
        "This read-only discovery tool does not build or modify an avatar."
    ),
    "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
}

HAMR_BUDGET_CHECK_SCHEMA = {
    "name": "hamr_budget_check",
    "description": (
        "Estimate one validated Hamr spec against an official minimal, balanced, or high "
        "performance budget without launching Blender or creating output."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "spec_path": {"type": "string", "minLength": 1, "maxLength": 240},
            "budget": {"type": "string", "enum": ["minimal", "balanced", "high"]},
        },
        "required": ["spec_path", "budget"],
        "additionalProperties": False,
    },
}

HAMR_ARTIFACT_PROBE_SCHEMA = {
    "name": "hamr_artifact_probe",
    "description": (
        "Probe one existing VRM or GLB through Hamr's current public inspect API. "
        "The result explicitly distinguishes metadata from real compliance checks."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "artifact_path": {"type": "string", "minLength": 1, "maxLength": 240},
            "targets": {
                "type": "array",
                "minItems": 1,
                "maxItems": 2,
                "uniqueItems": True,
                "items": {"type": "string", "enum": ["VRCHAT", "VROID"]},
            },
        },
        "required": ["artifact_path", "targets"],
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


def _artifact_file(artifact_root: Path, value: Any) -> tuple[Path | None, str | None]:
    if not isinstance(value, str) or not value.strip() or len(value) > 240 or "\x00" in value:
        return None, None
    relative = Path(value.strip())
    if relative.is_absolute() or relative.suffix.casefold() not in {".vrm", ".glb"}:
        return None, None
    try:
        resolved = (artifact_root / relative).resolve()
        resolved.relative_to(artifact_root)
        size = resolved.stat().st_size
    except (OSError, ValueError):
        return None, None
    if not resolved.is_file() or not 1 <= size <= 512 * 1024 * 1024:
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


def build_presets_handler(ctx):
    def handle(args: dict[str, Any], **_kwargs: Any) -> str:
        if args:
            return tool_error("hamr_presets accepts no arguments")
        runtime = _runtime(ctx)
        if runtime is None or not _PRESETS_RUNNER.is_file():
            return tool_error(
                "Configure volmarr-hamr engine_root, spec_root, and a compatible Python interpreter."
            )
        python, engine_root, _spec_root = runtime
        try:
            completed = subprocess.run(
                [str(python), "-B", "-P", "-s", str(_PRESETS_RUNNER), str(engine_root)],
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
            return tool_error("Hamr preset discovery timed out")
        except OSError:
            return tool_error("Hamr preset discovery could not be started")
        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        if (
            len(stdout.encode("utf-8", errors="replace")) > _MAX_OUTPUT_BYTES
            or len(stderr.encode("utf-8", errors="replace")) > _MAX_OUTPUT_BYTES
        ):
            return tool_error("Hamr returned an oversized preset response")
        if completed.returncode != 0:
            return tool_error("Hamr could not list presets")
        try:
            payload = json.loads(stdout)
        except (TypeError, json.JSONDecodeError):
            return tool_error("Hamr returned an invalid preset response")
        if not isinstance(payload, dict) or set(payload) != {"body", "character"}:
            return tool_error("Hamr returned an invalid preset response")
        body = payload["body"]
        character = payload["character"]
        if not isinstance(body, list) or not isinstance(character, list):
            return tool_error("Hamr returned an invalid preset response")
        return tool_result(
            {
                "success": True,
                "calculation": "hamr_presets",
                "body_count": len(body),
                "character_count": len(character),
                "body": body,
                "character": character,
                "blender_launched": False,
                "source": {"engine": "Hamr", "api": "preset catalogs", "license": "MIT"},
            }
        )

    return handle


def build_budget_check_handler(ctx):
    def handle(args: dict[str, Any], **_kwargs: Any) -> str:
        if set(args) != {"spec_path", "budget"}:
            return tool_error("spec_path and budget are required")
        budget = args.get("budget")
        if budget not in {"minimal", "balanced", "high"}:
            return tool_error("budget must be minimal, balanced, or high")
        runtime = _runtime(ctx)
        if runtime is None or not _BUDGET_RUNNER.is_file():
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
                [
                    str(python),
                    "-B",
                    "-P",
                    "-s",
                    str(_BUDGET_RUNNER),
                    str(engine_root),
                    str(spec_file),
                    budget,
                ],
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
            return tool_error("Hamr budget check timed out")
        except OSError:
            return tool_error("Hamr budget check could not be started")
        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        if (
            len(stdout.encode("utf-8", errors="replace")) > _MAX_OUTPUT_BYTES
            or len(stderr.encode("utf-8", errors="replace")) > _MAX_OUTPUT_BYTES
        ):
            return tool_error("Hamr returned an oversized budget response")
        if completed.returncode != 0:
            return tool_error("Hamr could not check the spec budget")
        try:
            payload = json.loads(stdout)
        except (TypeError, json.JSONDecodeError):
            return tool_error("Hamr returned an invalid budget response")
        if not isinstance(payload, dict) or set(payload) != {
            "within_budget",
            "estimates",
            "limits",
            "warnings",
        }:
            return tool_error("Hamr returned an invalid budget response")
        if not isinstance(payload["within_budget"], bool) or not isinstance(
            payload["warnings"], list
        ):
            return tool_error("Hamr returned an invalid budget response")
        return tool_result(
            {
                "success": True,
                "calculation": "hamr_budget_check",
                "spec_path": relative_path,
                "budget": budget,
                **payload,
                "blender_launched": False,
                "output_created": False,
                "source": {"engine": "Hamr", "api": "check_budget", "license": "MIT"},
            }
        )

    return handle


def build_artifact_probe_handler(ctx):
    def handle(args: dict[str, Any], **_kwargs: Any) -> str:
        if set(args) != {"artifact_path", "targets"}:
            return tool_error("artifact_path and targets are required")
        targets = args.get("targets")
        if (
            not isinstance(targets, list)
            or not 1 <= len(targets) <= 2
            or len(set(targets)) != len(targets)
            or any(target not in {"VRCHAT", "VROID"} for target in targets)
        ):
            return tool_error("targets must contain unique VRCHAT or VROID values")
        runtime = _runtime(ctx)
        artifact_root = _configured_root(ctx.get_config("artifact_root", ""))
        if runtime is None or artifact_root is None or not _ARTIFACT_RUNNER.is_file():
            return tool_error(
                "Configure volmarr-hamr engine_root, spec_root, artifact_root, and Python."
            )
        python, engine_root, _spec_root = runtime
        artifact_file, relative_path = _artifact_file(
            artifact_root, args.get("artifact_path")
        )
        if artifact_file is None or relative_path is None:
            return tool_error(
                "artifact_path must name an existing VRM or GLB up to 512 MiB within artifact_root"
            )
        try:
            completed = subprocess.run(
                [
                    str(python),
                    "-B",
                    "-P",
                    "-s",
                    str(_ARTIFACT_RUNNER),
                    str(engine_root),
                    str(artifact_file),
                    *targets,
                ],
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
            return tool_error("Hamr artifact probe timed out")
        except OSError:
            return tool_error("Hamr artifact probe could not be started")
        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        if (
            len(stdout.encode("utf-8", errors="replace")) > _MAX_OUTPUT_BYTES
            or len(stderr.encode("utf-8", errors="replace")) > _MAX_OUTPUT_BYTES
        ):
            return tool_error("Hamr returned an oversized artifact response")
        if completed.returncode != 0:
            return tool_error("Hamr could not probe the artifact")
        try:
            payload = json.loads(stdout)
        except (TypeError, json.JSONDecodeError):
            return tool_error("Hamr returned an invalid artifact response")
        if not isinstance(payload, dict) or set(payload) != {
            "exists",
            "size_mb",
            "targets",
            "checks",
        } or not isinstance(payload["checks"], list):
            return tool_error("Hamr returned an invalid artifact response")
        checks = payload["checks"]
        return tool_result(
            {
                "success": True,
                "calculation": "hamr_artifact_probe",
                "artifact_path": relative_path,
                **payload,
                "compliance_performed": bool(checks),
                "inspection_scope": "official_checks" if checks else "metadata_only",
                "blender_launched": False,
                "source": {"engine": "Hamr", "api": "builder.inspect", "license": "MIT"},
            }
        )

    return handle


def register_tools(ctx) -> None:
    for name, schema, handler, emoji in (
        (
            "hamr_spec_validate",
            HAMR_SPEC_VALIDATE_SCHEMA,
            build_spec_validate_handler(ctx),
            "🔨",
        ),
        ("hamr_presets", HAMR_PRESETS_SCHEMA, build_presets_handler(ctx), "🧍"),
        (
            "hamr_budget_check",
            HAMR_BUDGET_CHECK_SCHEMA,
            build_budget_check_handler(ctx),
            "📐",
        ),
        (
            "hamr_artifact_probe",
            HAMR_ARTIFACT_PROBE_SCHEMA,
            build_artifact_probe_handler(ctx),
            "🔍",
        ),
    ):
        ctx.register_tool(
            name=name,
            toolset="volmarr_hamr",
            schema=schema,
            handler=handler,
            description=schema["description"],
            emoji=emoji,
        )
