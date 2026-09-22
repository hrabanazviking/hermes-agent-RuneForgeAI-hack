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

SMIDJA_ASSETS_SCHEMA = {
    "name": "smidja_assets",
    "description": (
        "List bounded public metadata from Seidr-Smidja's local Hoard catalog. "
        "This read-only query does not resolve, fetch, bootstrap, or modify assets."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "asset_type": {"type": "string", "minLength": 1, "maxLength": 40},
            "tags": {
                "type": "array",
                "items": {"type": "string", "minLength": 1, "maxLength": 40},
                "maxItems": 8,
            },
        },
        "additionalProperties": False,
    },
}

SMIDJA_GATE_RULES_SCHEMA = {
    "name": "smidja_gate_rules",
    "description": (
        "List bounded Seidr-Smidja Gate rule metadata for one compliance target. "
        "This read-only query does not inspect an avatar or issue a compliance verdict."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "target": {"type": "string", "enum": ["VRCHAT", "VTUBE_STUDIO"]}
        },
        "required": ["target"],
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


def _run(ctx, python: Path, arguments: list[str]) -> dict[str, Any] | None:
    try:
        completed = subprocess.run(
            [str(python), "-B", "-P", "-s", str(_RUNNER), *arguments],
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
        return None
    stdout = completed.stdout or ""
    stderr = completed.stderr or ""
    if (
        completed.returncode != 0
        or len(stdout.encode("utf-8", errors="replace")) > _MAX_BYTES
        or len(stderr.encode("utf-8", errors="replace")) > _MAX_BYTES
    ):
        return None
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


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
        payload = _run(ctx, python, ["validate", str(engine), str(spec_file)])
        if payload is None:
            return tool_error("Seidr-Smidja Loom validation could not complete")
        if not isinstance(payload.get("valid"), bool) or not isinstance(
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


def _asset(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict) or set(value) != {
        "asset_id",
        "display_name",
        "asset_type",
        "tags",
        "vrm_version",
        "file_size_bytes",
        "cached",
    }:
        return None
    text_fields = ("asset_id", "display_name", "asset_type")
    if any(not isinstance(value[key], str) or len(value[key]) > 300 for key in text_fields):
        return None
    tags = value["tags"]
    if not isinstance(tags, list) or len(tags) > 32 or any(
        not isinstance(tag, str) or len(tag) > 100 for tag in tags
    ):
        return None
    vrm_version = value["vrm_version"]
    if vrm_version is not None and (not isinstance(vrm_version, str) or len(vrm_version) > 40):
        return None
    file_size = value["file_size_bytes"]
    if file_size is not None and (
        not isinstance(file_size, int) or isinstance(file_size, bool) or file_size < 0
    ):
        return None
    if not isinstance(value["cached"], bool):
        return None
    return value


def build_assets_handler(ctx):
    def handle(args: dict[str, Any], **_kwargs: Any) -> str:
        if not set(args).issubset({"asset_type", "tags"}):
            return tool_error("Only asset_type and tags are accepted")
        engine = _root(
            ctx.get_config("engine_root", ""), marker="src/seidr_smidja/hoard/local.py"
        )
        python = _python(ctx.get_config("python_path", "") or sys.executable)
        if engine is None or python is None or not _RUNNER.is_file():
            return tool_error("Configure volmarr-smidja engine_root and Python.")
        asset_type = args.get("asset_type")
        if asset_type is not None and (
            not isinstance(asset_type, str)
            or not asset_type.strip()
            or len(asset_type) > 40
            or "\x00" in asset_type
        ):
            return tool_error("asset_type must be a bounded non-empty string")
        clean_type = asset_type.strip() if asset_type is not None else None
        tags = args.get("tags", [])
        if (
            not isinstance(tags, list)
            or len(tags) > 8
            or any(
                not isinstance(tag, str)
                or not tag.strip()
                or len(tag) > 40
                or "\x00" in tag
                for tag in tags
            )
        ):
            return tool_error("tags must contain at most eight bounded strings")
        clean_tags = list(dict.fromkeys(tag.strip() for tag in tags))
        payload = _run(
            ctx,
            python,
            ["assets", str(engine), clean_type or "", json.dumps(clean_tags)],
        )
        raw_assets = None if payload is None else payload.get("assets")
        if not isinstance(raw_assets, list) or len(raw_assets) > 100:
            return tool_error("Seidr-Smidja Hoard discovery could not complete")
        assets = [_asset(item) for item in raw_assets]
        if any(item is None for item in assets):
            return tool_error("Seidr-Smidja returned invalid Hoard metadata")
        return tool_result(
            {
                "success": True,
                "calculation": "smidja_assets",
                "filters": {"asset_type": clean_type, "tags": clean_tags},
                "count": len(assets),
                "assets": assets,
                "asset_resolved": False,
                "asset_fetched": False,
                "hoard_bootstrapped": False,
                "source": {
                    "engine": "Seidr-Smidja",
                    "api": "LocalHoardAdapter.list_assets",
                    "license_metadata": "CONFLICT: root Apache-2.0; pyproject MIT",
                },
            }
        )

    return handle


def build_gate_rules_handler(ctx):
    def handle(args: dict[str, Any], **_kwargs: Any) -> str:
        if set(args) != {"target"} or args.get("target") not in {
            "VRCHAT",
            "VTUBE_STUDIO",
        }:
            return tool_error("target must be VRCHAT or VTUBE_STUDIO")
        engine = _root(
            ctx.get_config("engine_root", ""), marker="src/seidr_smidja/gate/gate.py"
        )
        python = _python(ctx.get_config("python_path", "") or sys.executable)
        if engine is None or python is None or not _RUNNER.is_file():
            return tool_error("Configure volmarr-smidja engine_root and Python.")
        target = args["target"]
        payload = _run(ctx, python, ["gate-rules", str(engine), target])
        raw_rules = None if payload is None else payload.get("rules")
        if not isinstance(raw_rules, list) or not 1 <= len(raw_rules) <= 100:
            return tool_error("Seidr-Smidja Gate rule discovery could not complete")
        expected = {"rule_id", "display_name", "severity", "description"}
        for rule in raw_rules:
            if not isinstance(rule, dict) or set(rule) != expected:
                return tool_error("Seidr-Smidja returned invalid Gate rule metadata")
            if any(not isinstance(rule[key], str) or len(rule[key]) > 1000 for key in expected):
                return tool_error("Seidr-Smidja returned invalid Gate rule metadata")
            if rule["severity"] not in {"ERROR", "WARNING"}:
                return tool_error("Seidr-Smidja returned invalid Gate rule metadata")
        return tool_result(
            {
                "success": True,
                "calculation": "smidja_gate_rules",
                "target": target,
                "count": len(raw_rules),
                "rules": raw_rules,
                "artifact_inspected": False,
                "compliance_performed": False,
                "source": {
                    "engine": "Seidr-Smidja",
                    "api": "gate.list_rules",
                    "license_metadata": "CONFLICT: root Apache-2.0; pyproject MIT",
                },
            }
        )

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
    ctx.register_tool(
        name="smidja_assets",
        toolset="volmarr_smidja",
        schema=SMIDJA_ASSETS_SCHEMA,
        handler=build_assets_handler(ctx),
        description=SMIDJA_ASSETS_SCHEMA["description"],
        emoji="🗃️",
    )
    ctx.register_tool(
        name="smidja_gate_rules",
        toolset="volmarr_smidja",
        schema=SMIDJA_GATE_RULES_SCHEMA,
        handler=build_gate_rules_handler(ctx),
        description=SMIDJA_GATE_RULES_SCHEMA["description"],
        emoji="🚪",
    )
