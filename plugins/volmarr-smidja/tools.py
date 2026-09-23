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

SMIDJA_RENDER_VIEWS_SCHEMA = {
    "name": "smidja_render_views",
    "description": (
        "List Seidr-Smidja's canonical Oracle Eye view names without rendering. "
        "This read-only query does not launch Blender or create images."
    ),
    "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
}

SMIDJA_GATE_CHECK_SCHEMA = {
    "name": "smidja_gate_check",
    "description": (
        "Run Seidr-Smidja's bounded, read-only Gate header checks on one VRM artifact. "
        "The result exposes structural findings and does not claim full geometry certification."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "artifact_path": {"type": "string", "minLength": 1, "maxLength": 240},
            "targets": {
                "type": "array",
                "items": {"type": "string", "enum": ["VRCHAT", "VTUBE_STUDIO"]},
                "minItems": 1,
                "maxItems": 2,
            },
            "vrchat_tier": {
                "type": "string",
                "enum": ["Excellent", "Good", "Medium", "Poor"],
            },
        },
        "required": ["artifact_path"],
        "additionalProperties": False,
    },
}

SMIDJA_ASSET_PROBE_SCHEMA = {
    "name": "smidja_asset_probe",
    "description": (
        "Probe whether one Seidr-Smidja Hoard asset resolves to an existing local file. "
        "The read-only result withholds its filesystem path and never fetches or bootstraps."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "asset_id": {"type": "string", "minLength": 1, "maxLength": 200}
        },
        "required": ["asset_id"],
        "additionalProperties": False,
    },
}

SMIDJA_FORGE_READINESS_SCHEMA = {
    "name": "smidja_forge_readiness",
    "description": (
        "Probe Seidr-Smidja Forge prerequisites without launching Blender or creating output. "
        "Executable paths are withheld from the result."
    ),
    "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
}

_MAX_ARTIFACT_BYTES = 128 * 1024 * 1024


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


def build_render_views_handler(ctx):
    def handle(args: dict[str, Any], **_kwargs: Any) -> str:
        if args:
            return tool_error("smidja_render_views accepts no arguments")
        engine = _root(
            ctx.get_config("engine_root", ""), marker="src/seidr_smidja/oracle_eye/eye.py"
        )
        python = _python(ctx.get_config("python_path", "") or sys.executable)
        if engine is None or python is None or not _RUNNER.is_file():
            return tool_error("Configure volmarr-smidja engine_root and Python.")
        payload = _run(ctx, python, ["render-views", str(engine)])
        views = None if payload is None else payload.get("views")
        if (
            not isinstance(views, list)
            or not 1 <= len(views) <= 32
            or any(not isinstance(view, str) or not view or len(view) > 100 for view in views)
            or len(set(views)) != len(views)
        ):
            return tool_error("Seidr-Smidja Oracle Eye view discovery could not complete")
        return tool_result(
            {
                "success": True,
                "calculation": "smidja_render_views",
                "count": len(views),
                "views": views,
                "blender_launched": False,
                "images_created": False,
                "source": {
                    "engine": "Seidr-Smidja",
                    "api": "oracle_eye.list_standard_views",
                    "license_metadata": "CONFLICT: root Apache-2.0; pyproject MIT",
                },
            }
        )

    return handle


def _gate_report(payload: Any) -> dict[str, Any] | None:
    if not isinstance(payload, dict) or set(payload) != {"passed", "targets", "results"}:
        return None
    targets = payload["targets"]
    results = payload["results"]
    if (
        not isinstance(payload["passed"], bool)
        or not isinstance(targets, list)
        or not 1 <= len(targets) <= 2
        or any(
            not isinstance(target, str)
            or target not in {"VRCHAT", "VTUBE_STUDIO"}
            for target in targets
        )
        or len(set(targets)) != len(targets)
        or not isinstance(results, dict)
        or set(results) != set(targets)
    ):
        return None
    for target, result in results.items():
        if not isinstance(result, dict) or set(result) != {"passed", "violations"}:
            return None
        violations = result["violations"]
        if (
            not isinstance(result["passed"], bool)
            or not isinstance(violations, list)
            or len(violations) > 100
        ):
            return None
        for violation in violations:
            if not isinstance(violation, dict) or set(violation) != {
                "rule_id",
                "severity",
                "field_path",
                "description",
            }:
                return None
            if any(
                not isinstance(violation[key], str) or len(violation[key]) > 1000
                for key in violation
            ) or violation["severity"] not in {"ERROR", "WARNING"}:
                return None
        if target not in {"VRCHAT", "VTUBE_STUDIO"}:
            return None
    return payload


def build_gate_check_handler(ctx):
    def handle(args: dict[str, Any], **_kwargs: Any) -> str:
        if set(args) - {"artifact_path", "targets", "vrchat_tier"} or "artifact_path" not in args:
            return tool_error("artifact_path is required; only targets and vrchat_tier are optional")
        engine = _root(
            ctx.get_config("engine_root", ""), marker="src/seidr_smidja/gate/gate.py"
        )
        artifact_root = _root(ctx.get_config("artifact_root", ""))
        python = _python(ctx.get_config("python_path", "") or sys.executable)
        if engine is None or artifact_root is None or python is None or not _RUNNER.is_file():
            return tool_error("Configure volmarr-smidja engine_root, artifact_root, and Python.")
        value = args.get("artifact_path")
        if not isinstance(value, str) or not value.strip() or len(value) > 240 or "\x00" in value:
            return tool_error("artifact_path must be a bounded relative VRM path")
        relative = Path(value.strip())
        if relative.is_absolute() or relative.suffix.casefold() != ".vrm":
            return tool_error("artifact_path must be a bounded relative VRM path")
        try:
            artifact = (artifact_root / relative).resolve()
            artifact.relative_to(artifact_root)
            size = artifact.stat().st_size
        except (OSError, ValueError):
            return tool_error("artifact_path must remain within artifact_root")
        if not artifact.is_file() or not 1 <= size <= _MAX_ARTIFACT_BYTES:
            return tool_error("artifact_path must name a VRM file from 1 byte to 128 MiB")
        targets = args.get("targets", ["VRCHAT", "VTUBE_STUDIO"])
        if (
            not isinstance(targets, list)
            or not 1 <= len(targets) <= 2
            or any(
                not isinstance(target, str)
                or target not in {"VRCHAT", "VTUBE_STUDIO"}
                for target in targets
            )
            or len(set(targets)) != len(targets)
        ):
            return tool_error("targets must contain one or both supported targets without duplicates")
        tier = args.get("vrchat_tier", "Good")
        if tier not in {"Excellent", "Good", "Medium", "Poor"}:
            return tool_error("vrchat_tier must be Excellent, Good, Medium, or Poor")
        payload = _run(
            ctx,
            python,
            ["gate-check", str(engine), str(artifact), json.dumps(targets), tier],
        )
        report = _gate_report(payload)
        if report is None:
            return tool_error("Seidr-Smidja Gate check could not complete")
        unevaluated = [
            violation["rule_id"]
            for result in report["results"].values()
            for violation in result["violations"]
            if "not evaluated" in violation["description"].casefold()
        ]
        return tool_result(
            {
                "success": True,
                "calculation": "smidja_gate_check",
                "artifact_path": relative.as_posix(),
                "artifact_size_bytes": size,
                "vrchat_tier": tier,
                "official_gate_passed": report["passed"],
                "targets_checked": report["targets"],
                "results": report["results"],
                "compliance_scope": "official_gate_structural_header",
                "certification_complete": False,
                "unevaluated_rule_ids": list(dict.fromkeys(unevaluated)),
                "blender_launched": False,
                "output_created": False,
                "source": {
                    "engine": "Seidr-Smidja",
                    "api": "gate.check",
                    "license_metadata": "CONFLICT: root Apache-2.0; pyproject MIT",
                },
            }
        )

    return handle


def build_asset_probe_handler(ctx):
    def handle(args: dict[str, Any], **_kwargs: Any) -> str:
        if set(args) != {"asset_id"}:
            return tool_error("asset_id is required")
        asset_id = args.get("asset_id")
        if (
            not isinstance(asset_id, str)
            or not asset_id.strip()
            or len(asset_id) > 200
            or "\x00" in asset_id
        ):
            return tool_error("asset_id must be a bounded non-empty string")
        engine = _root(
            ctx.get_config("engine_root", ""), marker="src/seidr_smidja/hoard/local.py"
        )
        python = _python(ctx.get_config("python_path", "") or sys.executable)
        if engine is None or python is None or not _RUNNER.is_file():
            return tool_error("Configure volmarr-smidja engine_root and Python.")
        clean_id = asset_id.strip()
        payload = _run(ctx, python, ["asset-probe", str(engine), clean_id])
        if (
            not isinstance(payload, dict)
            or set(payload) != {"available", "file_type", "size_bytes"}
            or not isinstance(payload["available"], bool)
            or (
                payload["file_type"] is not None
                and (
                    not isinstance(payload["file_type"], str)
                    or len(payload["file_type"]) > 20
                )
            )
            or (
                payload["size_bytes"] is not None
                and (
                    not isinstance(payload["size_bytes"], int)
                    or isinstance(payload["size_bytes"], bool)
                    or payload["size_bytes"] < 0
                )
            )
            or (payload["available"] and payload["size_bytes"] is None)
        ):
            return tool_error("Seidr-Smidja Hoard resolution probe could not complete")
        return tool_result(
            {
                "success": True,
                "calculation": "smidja_asset_probe",
                "asset_id": clean_id,
                **payload,
                "path_withheld": True,
                "asset_opened": False,
                "asset_fetched": False,
                "hoard_bootstrapped": False,
                "source": {
                    "engine": "Seidr-Smidja",
                    "api": "LocalHoardAdapter.resolve",
                    "license_metadata": "CONFLICT: root Apache-2.0; pyproject MIT",
                },
            }
        )

    return handle


def build_forge_readiness_handler(ctx):
    def handle(args: dict[str, Any], **_kwargs: Any) -> str:
        if args:
            return tool_error("smidja_forge_readiness accepts no arguments")
        engine = _root(
            ctx.get_config("engine_root", ""),
            marker="src/seidr_smidja/_internal/blender_runner.py",
        )
        python = _python(ctx.get_config("python_path", "") or sys.executable)
        blender_path = ctx.get_config("blender_path", "")
        if not isinstance(blender_path, str) or len(blender_path) > 500 or "\x00" in blender_path:
            return tool_error("blender_path must be an absolute executable path or empty")
        clean_path = blender_path.strip()
        if clean_path and not Path(clean_path).is_absolute():
            return tool_error("blender_path must be an absolute executable path or empty")
        if engine is None or python is None or not _RUNNER.is_file():
            return tool_error("Configure volmarr-smidja engine_root and Python.")
        payload = _run(ctx, python, ["forge-readiness", str(engine), clean_path])
        if (
            not isinstance(payload, dict)
            or set(payload) != {
                "blender_available",
                "build_script_present",
                "configured_path_selected",
                "executable_name",
            }
            or any(
                not isinstance(payload[key], bool)
                for key in (
                    "blender_available",
                    "build_script_present",
                    "configured_path_selected",
                )
            )
            or (
                payload["executable_name"] is not None
                and (
                    not isinstance(payload["executable_name"], str)
                    or len(payload["executable_name"]) > 100
                )
            )
        ):
            return tool_error("Seidr-Smidja Forge readiness probe could not complete")
        ready = payload["blender_available"] and payload["build_script_present"]
        return tool_result(
            {
                "success": True,
                "calculation": "smidja_forge_readiness",
                "ready": ready,
                **payload,
                "executable_path_withheld": True,
                "blender_launched": False,
                "output_created": False,
                "source": {
                    "engine": "Seidr-Smidja",
                    "api": "_internal.blender_runner.resolve_blender_executable",
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
    ctx.register_tool(
        name="smidja_render_views",
        toolset="volmarr_smidja",
        schema=SMIDJA_RENDER_VIEWS_SCHEMA,
        handler=build_render_views_handler(ctx),
        description=SMIDJA_RENDER_VIEWS_SCHEMA["description"],
        emoji="👁️",
    )
    ctx.register_tool(
        name="smidja_gate_check",
        toolset="volmarr_smidja",
        schema=SMIDJA_GATE_CHECK_SCHEMA,
        handler=build_gate_check_handler(ctx),
        description=SMIDJA_GATE_CHECK_SCHEMA["description"],
        emoji="🛡️",
    )
    ctx.register_tool(
        name="smidja_asset_probe",
        toolset="volmarr_smidja",
        schema=SMIDJA_ASSET_PROBE_SCHEMA,
        handler=build_asset_probe_handler(ctx),
        description=SMIDJA_ASSET_PROBE_SCHEMA["description"],
        emoji="🔎",
    )
    ctx.register_tool(
        name="smidja_forge_readiness",
        toolset="volmarr_smidja",
        schema=SMIDJA_FORGE_READINESS_SCHEMA,
        handler=build_forge_readiness_handler(ctx),
        description=SMIDJA_FORGE_READINESS_SCHEMA["description"],
        emoji="🔥",
    )
