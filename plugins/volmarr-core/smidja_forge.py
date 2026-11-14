"""X.15 Seidr-Smidja: from preflight to controlled production (s.50).

Seidr-Smidja (``hrabanazviking/Seidr-Smidja``, default branch
``development``, audited pin ``32cdbd7a8735``) is Volmarr's
agent-only VRM avatar smithy: Loom (parametric AvatarSpec),
Hoard (asset catalog), Gate (compliance rules), Oracle Eye
(render views), Forge (headless Blender build scripts) and
Brunhand (the Bruarhoend remote VRoid "reaching hand"). The
fork already carries ``volmarr-smidja 0.1.0`` - a read-only
Loom / Hoard / Gate / Oracle Eye preflight adapter over a
bounded subprocess - and that surface is PRESERVED untouched
by this slice; it stays the only live engine surface.

License (E.14, text-verified): the root ``LICENSE`` at the pin
is genuine Apache-2.0 (sha256 cfc7749b96f6...), BUT the tree's
``pyproject.toml`` declares ``license = { text = "MIT" }`` -
the E14-T1 metadata conflict. Every record written here
carries the conflict string; it is never silently resolved.
Engine version at the pin: ``0.1.0.dev0`` (pyproject); the
fork preflight plugin is 0.1.0; the repo carries no tags and
``refs/heads/main`` is a separate line (E14-T4).

Scope law (section 50): this connector is opt-in, default-off
and local-only. It extends preflight toward CONTROLLED
production at the RECORD level only: a versioned forge spec
schema, a dry-run build plan that EXECUTES NOTHING (no
Blender, no subprocess render, no file writes outside the job
record), a per-asset license/provenance gate, an approval
gate (planned -> approved only with explicit operator
authorization recorded; a passed gate still executes
nothing), job lifecycle records (planned / approved /
cancelled with a record-level cleanup record), a Hamr
schema translation with explicit incompatibility errors (one
avatar standard, not two - section 50 item 7), and
presentation-only routing of finished-artifact records to
voice/avatar/VRM clients. Live remote control, Blender
build, VRM export and visual validation are each marked NOT
live in the capability matrix. ``production_ready`` is False.
"""
from __future__ import annotations

import hashlib
import json
import platform
import re
import time
from pathlib import Path
from typing import Any

CANONICAL_REPO = "hrabanazviking/Seidr-Smidja"
CANONICAL_REPO_URL = "https://github.com/hrabanazviking/Seidr-Smidja"
DEFAULT_BRANCH = "development"
AUDITED_PIN = "32cdbd7a87358bc1f6f046c4e1449c35f4d5d40a"
ENGINE_VERSION = "0.1.0.dev0"
PREFLIGHT_PLUGIN = "volmarr-smidja 0.1.0"
PROJECT_LICENSE = "Apache-2.0"
LICENSE_SHA256 = "cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30"
LICENSE_CONFLICT = "CONFLICT: root Apache-2.0; pyproject MIT (E14-T1)"
ADAPTER_VERSION = "0.1.0"
FORGE_SPEC_VERSION = "runeforge.smidja.forge.v1"
PERFORMANCE_BUDGET_MS = 250
MAX_REQUEST_CHARS = 16384
JOB_ID_RE = re.compile(r"^forge-[a-z0-9][a-z0-9-]{2,62}$")
TREE_MODULES = ("loom", "hoard", "gate", "oracle_eye", "forge", "brunhand")
EXPORT_FORMATS = ("vrm", "glb")
VRM_VERSIONS = ("0.x", "1.0")
KNOWN_LICENSES = ("CC0-1.0", "CC-BY-4.0", "CC-BY-SA-4.0", "MIT",
                  "Apache-2.0", "proprietary-licensed", "public-domain")
EGRESS_DESTINATIONS = ("public_readme", "training", "telemetry",
                       "publication", "external_account", "remote_host")
SAFE_DESTINATIONS = ("local_only", "presentation_client")
REFUSED_PAYLOAD_FIELDS = ("secrets", "secret_access", "credentials",
                          "cognitive_control", "independent_control",
                          "gui_control", "webcam", "microphone")
CAPABILITY_MATRIX = (
    {"capability": "read_only_preflight", "live": True,
     "basis": "volmarr-smidja 0.1.0 bounded subprocess (Loom/Hoard/Gate/Oracle Eye) - the only live engine surface; preserved untouched by X.15"},
    {"capability": "dry_run_build_plan", "live": True,
     "basis": "record-level planning in this connector; the plan executes nothing"},
    {"capability": "live_remote_control", "live": False,
     "basis": "Brunhand remote VRoid control is NOT driven by this connector; no GUI, webcam, microphone or external account is activated (s.50 item 5, Scenario 6)"},
    {"capability": "blender_build", "live": False,
     "basis": "no Blender job is launched; forge readiness was probed read-only in E.14 only"},
    {"capability": "vrm_export", "live": False,
     "basis": "no VRM/GLB is produced; inspection records are metadata-only"},
    {"capability": "visual_validation", "live": False,
     "basis": "no render is produced or inspected visually; Oracle Eye view names are catalog data only"},
)
# Hamr interface (E.13 audit, pin f77aa588601b): CharacterSpec
# (name, version, body/face/hair/clothing/expressions/physics,
# export ExportSpec{format vrm1|glb|blend, license}) and the
# PerformanceBudget tiers of hamr/core/perf.py MEMORY_TIERS.
HAMR_BUDGET_TIERS = {
    "minimal": {"max_build_time_seconds": 60.0, "max_memory_mb": 1000.0,
                "max_triangles": 30000, "max_texture_resolution": 512,
                "timeout_seconds": 180.0},
    "balanced": {"max_build_time_seconds": 45.0, "max_memory_mb": 1500.0,
                 "max_triangles": 50000, "max_texture_resolution": 1024,
                 "timeout_seconds": 120.0},
    "high": {"max_build_time_seconds": 30.0, "max_memory_mb": 2500.0,
             "max_triangles": 80000, "max_texture_resolution": 2048,
             "timeout_seconds": 90.0},
}
HAMR_EXPORT_TO_FORGE = {"vrm1": ("vrm", "1.0"), "glb": ("glb", None)}
FORGE_ONLY_FIELDS = ("job_id", "host", "log_capture", "cancellation",
                     "cleanup", "assets", "redistribution")
HAMR_ONLY_FIELDS = ("physics", "expressions", "clothing")


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    if value is None:
        return default
    return bool(value)


def local_host() -> str:
    return platform.node() or "unknown-host"


def forge_catalog() -> dict[str, Any]:
    """The s.50 catalog: forge spec schema, gates, matrix."""
    return {
        "schema": "runeforge.smidja.catalog.v1",
        "service": "volmarr-smidja-forge",
        "canonical_repo": CANONICAL_REPO,
        "default_branch": DEFAULT_BRANCH,
        "audited_pin": AUDITED_PIN,
        "engine_version": ENGINE_VERSION,
        "license": PROJECT_LICENSE,
        "license_sha256": LICENSE_SHA256,
        "license_conflict": LICENSE_CONFLICT,
        "preflight_adapter": {
            "plugin": PREFLIGHT_PLUGIN, "mode": "read-only",
            "surface": ["loom_spec_validate", "hoard_assets", "gate_rules",
                        "gate_check", "oracle_eye_views", "forge_readiness"],
            "preserved_untouched": True,
            "only_live_engine_surface": True},
        "forge_spec_schema": {
            "version": FORGE_SPEC_VERSION,
            "required": ["job_id", "spec_version", "avatar_id", "host",
                         "spec_path", "output_dir", "metadata",
                         "blender_version", "export", "budget",
                         "timeout_seconds", "log_capture", "cancellation",
                         "cleanup", "assets"],
            "job_id_pattern": JOB_ID_RE.pattern,
            "safe_paths": "spec_path, output_dir and every asset/artifact path must resolve under an approved root; traversal outside is refused by name",
            "export_formats": list(EXPORT_FORMATS),
            "vrm_versions": list(VRM_VERSIONS),
            "budget_fields": ["cpu_cores", "gpu_required", "max_memory_mb",
                              "max_triangles", "max_texture_resolution",
                              "max_build_time_seconds"],
        },
        "capability_matrix": [dict(row) for row in CAPABILITY_MATRIX],
        "hamr_reconciliation": {
            "one_avatar_standard": True,
            "hamr_budget_tiers": sorted(HAMR_BUDGET_TIERS),
            "hamr_export_map": {k: list(v) for k, v in HAMR_EXPORT_TO_FORGE.items()},
            "incompatibility_errors": "explicit, named per field; no silent coercion in either direction",
        },
        "approval_gate": "a forge-job record moves planned -> approved only with explicit operator authorization recorded; a passed gate executes nothing",
        "job_states": ["planned", "approved", "cancelled"],
        "presentation_routing": "presentation-only consumers; payloads requesting secret access or cognitive control are refused by name",
        "privacy": "private reference images and private paths are refused by name for egress, publication, training and telemetry destinations",
        "performance_budget_ms": PERFORMANCE_BUDGET_MS,
        "sends_anything_external": False,
        "runs_engine": False,
        "executes_operations": False,
        "production_ready": False,
    }


def _measure_tree(root: Path) -> dict[str, Any]:
    """Measure a staged Seidr-Smidja checkout truthfully."""
    record: dict[str, Any] = {"root": str(root), "present": root.is_dir()}
    if not root.is_dir():
        record["status"] = "tree_missing"
        return record
    head = None
    head_file = root / ".git" / "HEAD"
    if head_file.is_file():
        ref = head_file.read_text(encoding="utf-8").strip()
        if ref.startswith("ref:"):
            ref_path = root / ".git" / ref[4:].strip()
            if ref_path.is_file():
                head = ref_path.read_text(encoding="utf-8").strip()
            else:
                packed = root / ".git" / "packed-refs"
                if packed.is_file():
                    for line in packed.read_text(encoding="utf-8").splitlines():
                        parts = line.split(" ", 1)
                        if len(parts) == 2 and parts[1].strip() == ref[4:].strip():
                            head = parts[0].strip()
        elif ref:
            head = ref
    record["head"] = head
    record["head_matches_pin"] = head == AUDITED_PIN
    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        text = pyproject.read_text(encoding="utf-8")
        name_m = re.search(r'^name\s*=\s*"([^"]+)"', text, re.M)
        ver_m = re.search(r'^version\s*=\s*"([^"]+)"', text, re.M)
        lic_m = re.search(r'license\s*=\s*\{\s*text\s*=\s*"([^"]+)"', text)
        if name_m:
            record["package_name"] = name_m.group(1)
        if ver_m:
            record["package_version"] = ver_m.group(1)
        record["pyproject_license_declared"] = lic_m.group(1) if lic_m else None
    license_file = root / "LICENSE"
    if license_file.is_file():
        record["license_sha256"] = hashlib.sha256(license_file.read_bytes()).hexdigest()
        record["license_matches_audited"] = record["license_sha256"] == LICENSE_SHA256
    pkg = root / "src" / "seidr_smidja"
    record["modules_present"] = [m for m in TREE_MODULES if (pkg / m).is_dir()]
    record["modules_missing"] = [m for m in TREE_MODULES if not (pkg / m).is_dir()]
    record["preflight_adapter_plugin"] = PREFLIGHT_PLUGIN
    record["status"] = "measured" if head else "tree_partial"
    return record


def smidja_forge_status(ctx, recorded_at: str | None = None) -> dict[str, Any]:
    """Truthful status: config, staged tree, license conflict."""
    enabled = _as_bool(ctx.get_config("smidja_forge_enabled", False))
    root_value = str(ctx.get_config("smidja_forge_root", "") or "").strip()
    configured = bool(enabled and root_value)
    tree = _measure_tree(Path(root_value).expanduser()) if root_value else {
        "root": "", "present": False, "status": "not_configured"}
    result: dict[str, Any] = {
        "schema": "runeforge.smidja.status.v1",
        "service": "volmarr-smidja-forge",
        "recorded_at": recorded_at,
        "enabled": enabled,
        "configured": configured,
        "canonical_repo": CANONICAL_REPO,
        "canonical_repo_url": CANONICAL_REPO_URL,
        "default_branch": DEFAULT_BRANCH,
        "audited_pin": AUDITED_PIN,
        "engine_version": ENGINE_VERSION,
        "license": PROJECT_LICENSE,
        "license_sha256": LICENSE_SHA256,
        "license_conflict": LICENSE_CONFLICT,
        "local_host": local_host(),
        "tree": tree,
        "mode": "opt-in, local-only forge connector; dry-run plans and job records only, executes no build and drives no remote control",
        "sends_anything_external": False,
        "runs_engine": False,
        "executes_operations": False,
        "production_ready": False,
    }
    if not configured:
        result["configuration_error"] = (
            "Configure smidja_forge_enabled and smidja_forge_root." 
            if not root_value else
            "smidja_forge_enabled is false; the forge connector is opt-in and default-off.")
    return result


def _failure(reason: str, *, schema: str = "runeforge.smidja.plan.v1",
             **extra: Any) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema": schema, "service": "volmarr-smidja-forge",
        "outcome": "failure", "accepted": False, "fail_closed": True,
        "failure": reason, "source_revision": AUDITED_PIN,
        "license_conflict": LICENSE_CONFLICT,
        "sends_anything_external": False, "runs_engine": False,
        "executes_operations": False, "production_ready": False}
    result.update(extra)
    return result


def _resolve_under(path_value: Any, roots: list[Path]) -> Path | None:
    if not isinstance(path_value, str) or not path_value.strip() or "\x00" in path_value:
        return None
    candidate = Path(path_value.strip()).expanduser()
    if not candidate.is_absolute():
        return None
    try:
        resolved = candidate.resolve()
    except OSError:
        return None
    for root in roots:
        try:
            resolved.relative_to(root.resolve())
            return resolved
        except (OSError, ValueError):
            continue
    return None


def validate_forge_spec(spec: Any, *, approved_roots: Any = (),
                        host: str | None = None) -> dict[str, Any]:
    """Validate one forge spec (s.50 items 3-4); failures by name."""
    base = {"schema": "runeforge.smidja.spec_validation.v1",
            "service": "volmarr-smidja-forge", "source_revision": AUDITED_PIN,
            "license_conflict": LICENSE_CONFLICT,
            "sends_anything_external": False, "production_ready": False}
    def bad(reason: str, **extra: Any) -> dict[str, Any]:
        return {**base, "valid": False, "failure": reason,
                "fail_closed": True, **extra}
    if not isinstance(spec, dict):
        return bad("spec_not_mapping")
    if spec.get("spec_version") != FORGE_SPEC_VERSION:
        return bad("spec_version_unsupported", spec_version=spec.get("spec_version"))
    job_id = spec.get("job_id")
    if not isinstance(job_id, str) or not JOB_ID_RE.match(job_id):
        return bad("job_id_invalid", job_id=job_id)
    if not isinstance(spec.get("avatar_id"), str) or not spec["avatar_id"].strip():
        return bad("avatar_id_missing")
    roots = [Path(str(r)).expanduser() for r in (approved_roots or ())]
    if not roots:
        return bad("approved_roots_missing")
    for field in ("spec_path", "output_dir"):
        if _resolve_under(spec.get(field), roots) is None:
            return bad("path_traversal_refused", field=field, path=spec.get(field))
    metadata = spec.get("metadata")
    if not isinstance(metadata, dict) or not str(metadata.get("version", "")).strip():
        return bad("metadata_version_missing")
    if not isinstance(spec.get("blender_version"), str) or not spec["blender_version"].strip():
        return bad("blender_version_missing")
    export = spec.get("export")
    if not isinstance(export, dict) or export.get("format") not in EXPORT_FORMATS:
        return bad("export_format_unsupported", export=export)
    if export["format"] == "vrm" and export.get("vrm_version") not in VRM_VERSIONS:
        return bad("vrm_version_unsupported", export=export)
    if not str(export.get("exporter", "")).strip():
        return bad("exporter_missing", export=export)
    budget = spec.get("budget")
    if not isinstance(budget, dict):
        return bad("budget_missing")
    for field in ("cpu_cores", "max_memory_mb", "max_triangles"):
        value = budget.get(field)
        if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
            return bad("budget_field_invalid", field=field)
    if not isinstance(budget.get("gpu_required"), bool):
        return bad("budget_field_invalid", field="gpu_required")
    timeout = spec.get("timeout_seconds")
    if not isinstance(timeout, (int, float)) or isinstance(timeout, bool) or timeout <= 0:
        return bad("timeout_invalid")
    for field in ("log_capture", "cancellation", "cleanup"):
        plan = spec.get(field)
        if not isinstance(plan, dict) or plan.get("mode") in (None, ""):
            return bad("plan_section_missing", field=field)
    cleanup_paths = (spec.get("cleanup") or {}).get("artifact_paths") or []
    if not isinstance(cleanup_paths, list):
        return bad("cleanup_paths_invalid")
    for path in cleanup_paths:
        if _resolve_under(path, roots) is None:
            return bad("path_traversal_refused", field="cleanup.artifact_paths", path=path)
    assets = spec.get("assets")
    if not isinstance(assets, list) or not assets:
        return bad("assets_missing")
    for index, asset in enumerate(assets):
        if not isinstance(asset, dict) or not str(asset.get("asset_id", "")).strip():
            return bad("asset_id_missing", index=index)
        if not str(asset.get("provenance", "")).strip():
            return bad("asset_provenance_missing", asset_id=asset.get("asset_id"))
        if _resolve_under(asset.get("path"), roots) is None and asset.get("path") is not None:
            return bad("path_traversal_refused", field="assets.path",
                       asset_id=asset.get("asset_id"))
    spec_host = spec.get("host")
    expected_host = host if host is not None else local_host()
    if spec_host is not None and spec_host != expected_host:
        return bad("wrong_host_refused", host=spec_host, local_host=expected_host)
    return {**base, "valid": True, "failure": None, "fail_closed": False,
            "job_id": job_id, "avatar_id": spec["avatar_id"]}


def plan_build(request: Any, *, approved_roots: Any = (),
               host: str | None = None) -> dict[str, Any]:
    """Dry-run build plan (s.50 item 3): executes NOTHING.

    Validated spec -> licensed asset inventory -> dry-run plan.
    The license gate (item 6) rejects unknown/unset licenses
    when redistribution is requested and names the gap
    otherwise. Private material is refused for every egress
    destination (item 9). A failed fake render prerequisite
    fails the plan by name (roadmap test gate).
    """
    started = time.monotonic()
    if not isinstance(request, dict):
        return _failure("request_not_mapping")
    if len(json.dumps(request, default=str)) > MAX_REQUEST_CHARS:
        return _failure("input_too_large")
    spec = request.get("spec")
    if not isinstance(spec, dict):
        return _failure("spec_missing")
    validation = validate_forge_spec(spec, approved_roots=approved_roots, host=host)
    if not validation["valid"]:
        return _failure(validation["failure"], validation=validation)
    prereq = request.get("render_prerequisites")
    if isinstance(prereq, dict):
        for key in ("blender_available", "exporter_available", "assets_cached"):
            if prereq.get(key) is False:
                return _failure("render_prerequisite_failed", prerequisite=key)
    redistribution = bool(request.get("redistribution", spec.get("redistribution", False)))
    destination = request.get("destination", spec.get("destination", "local_only"))
    inventory = []
    license_gaps = []
    for asset in spec["assets"]:
        license_value = asset.get("license")
        known = license_value in KNOWN_LICENSES
        inventory.append({"asset_id": asset["asset_id"],
                          "provenance": asset.get("provenance"),
                          "license": license_value,
                          "license_known": known,
                          "private": bool(asset.get("private", False))})
        if not known:
            license_gaps.append(asset["asset_id"])
    if redistribution and license_gaps:
        return _failure("asset_license_unknown_redistribution_refused",
                        assets=license_gaps)
    if destination in EGRESS_DESTINATIONS:
        private_assets = [a["asset_id"] for a in inventory if a["private"]]
        if private_assets:
            return _failure("private_asset_egress_refused",
                            destination=destination, assets=private_assets)
        return _failure("artifact_egress_refused", destination=destination)
    if destination not in SAFE_DESTINATIONS:
        return _failure("destination_unknown", destination=destination)
    latency_ms = (time.monotonic() - started) * 1000.0
    plan_core = {"job_id": spec["job_id"], "avatar_id": spec["avatar_id"],
                 "assets": [a["asset_id"] for a in inventory],
                 "destination": destination}
    plan_key = hashlib.sha256(json.dumps(plan_core, sort_keys=True).encode("utf-8")).hexdigest()
    return {
        "schema": "runeforge.smidja.plan.v1", "service": "volmarr-smidja-forge",
        "outcome": "plan", "accepted": True, "dry_run": True,
        "job_id": spec["job_id"], "job_state": "planned",
        "spec_version": FORGE_SPEC_VERSION, "plan_key": plan_key,
        "asset_inventory": inventory, "license_gaps_named": license_gaps,
        "redistribution": redistribution, "destination": destination,
        "budget": spec["budget"], "timeout_seconds": spec["timeout_seconds"],
        "log_capture": spec["log_capture"], "cancellation": spec["cancellation"],
        "cleanup": spec["cleanup"], "latency_ms": latency_ms,
        "source_revision": AUDITED_PIN, "license_conflict": LICENSE_CONFLICT,
        "sends_anything_external": False, "runs_engine": False,
        "executes_operations": False, "writes_files": False,
        "production_ready": False,
        "note": "dry-run plan only: no Blender build, no render, no file writes outside this job record",
    }


def approve_job(plan: Any, *, operator_authorized: bool = False,
                operator: str | None = None) -> dict[str, Any]:
    """Approval gate (s.50 items 3+5, Scenario 6).

    planned -> approved only with explicit operator
    authorization recorded. A passed gate EXECUTES NOTHING:
    no Blender build, no GPU job, no remote VRoid/Brunhand
    control, no GUI, no webcam/mic, no external account.
    """
    base = {"schema": "runeforge.smidja.approval.v1",
            "service": "volmarr-smidja-forge", "source_revision": AUDITED_PIN,
            "executed": False, "sends_anything_external": False,
            "runs_engine": False, "production_ready": False}
    if not isinstance(plan, dict) or plan.get("job_state") != "planned":
        return {**base, "approved": False, "reason": "job_not_planned"}
    if not operator_authorized or not (operator or "").strip():
        return {**base, "approved": False, "job_id": plan.get("job_id"),
                "reason": "approval_refused_operator_authorization_required"}
    return {**base, "approved": True, "reason": None,
            "job_id": plan.get("job_id"), "job_state": "approved",
            "operator": operator,
            "authorization_recorded": True,
            "note": "approval recorded only; the connector executes no build, GPU job or remote control"}


def cancel_job(plan: Any, *, approved_roots: Any = (),
               reason: str = "operator_cancelled") -> dict[str, Any]:
    """Cancellation -> cleanup record (records only).

    The cleanup record lists the job's declared artifact
    paths, validated under the approved roots; nothing real
    is deleted - records only.
    """
    base = {"schema": "runeforge.smidja.cancellation.v1",
            "service": "volmarr-smidja-forge", "source_revision": AUDITED_PIN,
            "sends_anything_external": False, "runs_engine": False,
            "executes_operations": False, "production_ready": False}
    if not isinstance(plan, dict) or not plan.get("job_id"):
        return {**base, "cancelled": False, "failure": "job_missing",
                "fail_closed": True}
    roots = [Path(str(r)).expanduser() for r in (approved_roots or ())]
    declared = ((plan.get("cleanup") or {}).get("artifact_paths")) or []
    cleanup_paths = []
    for path in declared:
        resolved = _resolve_under(path, roots) if roots else None
        cleanup_paths.append({"path": path, "validated_under_approved_root": resolved is not None})
    return {**base, "cancelled": True, "failure": None, "fail_closed": False,
            "job_id": plan["job_id"], "job_state": "cancelled",
            "cancellation_reason": reason,
            "cleanup_record": {"mode": "record_level_only",
                               "artifact_paths": cleanup_paths,
                               "deleted": False,
                               "note": "cleanup is a record of declared paths; nothing real was deleted"}}


def inspect_vrm_record(artifact: Any) -> dict[str, Any]:
    """VRM inspection record: metadata only, no compliance claim."""
    base = {"schema": "runeforge.smidja.inspection.v1",
            "service": "volmarr-smidja-forge", "source_revision": AUDITED_PIN,
            "sends_anything_external": False, "production_ready": False}
    if not isinstance(artifact, dict) or not str(artifact.get("artifact_id", "")).strip():
        return {**base, "inspected": False, "failure": "artifact_id_missing",
                "fail_closed": True}
    fmt = artifact.get("format")
    if fmt not in EXPORT_FORMATS:
        return {**base, "inspected": False, "failure": "artifact_format_unsupported",
                "fail_closed": True}
    return {**base, "inspected": True, "failure": None, "fail_closed": False,
            "artifact_id": artifact["artifact_id"], "format": fmt,
            "vrm_version": artifact.get("vrm_version"),
            "inspection_scope": "metadata_only",
            "compliance_performed": False,
            "visual_validation_performed": False,
            "note": "record-level inspection only; Gate compliance stays with the read-only volmarr-smidja preflight and visual validation is NOT live"}


def translate_hamr_to_forge(hamr_spec: Any) -> dict[str, Any]:
    """Hamr -> forge translation (s.50 item 7).

    Explicit incompatibility errors, named per field, no
    silent coercion: Hamr fields with no forge equivalent and
    forge-required fields Hamr cannot supply are both named,
    and any incompatibility fails the translation closed.
    """
    base = {"schema": "runeforge.smidja.hamr_translation.v1",
            "service": "volmarr-smidja-forge", "direction": "hamr_to_forge",
            "source_revision": AUDITED_PIN, "sends_anything_external": False,
            "production_ready": False}
    if not isinstance(hamr_spec, dict):
        return {**base, "translated": False, "failure": "hamr_spec_not_mapping",
                "fail_closed": True, "incompatibilities": []}
    errors: list[dict[str, Any]] = []
    export = hamr_spec.get("export") or {}
    fmt = export.get("format", "vrm1")
    if fmt not in HAMR_EXPORT_TO_FORGE:
        errors.append({"field": "export.format", "value": fmt,
                       "reason": "no_forge_equivalent"})
    budget_in = hamr_spec.get("budget") or {}
    tier = budget_in.get("tier")
    budget = None
    if tier is not None:
        if tier not in HAMR_BUDGET_TIERS:
            errors.append({"field": "budget.tier", "value": tier,
                           "reason": "unknown_hamr_budget_tier"})
        else:
            budget = dict(HAMR_BUDGET_TIERS[tier])
    for field in HAMR_ONLY_FIELDS:
        if hamr_spec.get(field) not in (None, {}, []):
            errors.append({"field": field, "reason": "no_forge_equivalent_in_forge_spec_v1"})
    missing = [f for f in FORGE_ONLY_FIELDS if f not in hamr_spec]
    if errors:
        return {**base, "translated": False, "failure": "hamr_incompatibility",
                "fail_closed": True, "incompatibilities": errors}
    forge_fmt, vrm_version = HAMR_EXPORT_TO_FORGE[fmt]
    return {**base, "translated": True, "failure": None, "fail_closed": False,
            "incompatibilities": [],
            "missing_forge_fields_named": missing,
            "forge_partial": {"avatar_id": hamr_spec.get("name"),
                              "metadata": {"version": hamr_spec.get("version")},
                              "export": {"format": forge_fmt, "vrm_version": vrm_version,
                                         "exporter": "io_scene_vrm", "license": export.get("license")},
                              "budget": budget}}


def translate_forge_to_hamr(forge_spec: Any) -> dict[str, Any]:
    """Forge -> Hamr translation: the reverse honesty check."""
    base = {"schema": "runeforge.smidja.hamr_translation.v1",
            "service": "volmarr-smidja-forge", "direction": "forge_to_hamr",
            "source_revision": AUDITED_PIN, "sends_anything_external": False,
            "production_ready": False}
    if not isinstance(forge_spec, dict):
        return {**base, "translated": False, "failure": "forge_spec_not_mapping",
                "fail_closed": True, "incompatibilities": []}
    errors: list[dict[str, Any]] = []
    export = forge_spec.get("export") or {}
    fmt, vrm_version = export.get("format"), export.get("vrm_version")
    hamr_format = None
    for key, value in HAMR_EXPORT_TO_FORGE.items():
        if value == (fmt, vrm_version) or (fmt == "glb" and value == ("glb", None)):
            hamr_format = key
            break
    if hamr_format is None:
        errors.append({"field": "export", "value": export,
                       "reason": "no_hamr_equivalent"})
    budget = forge_spec.get("budget") or {}
    tier_match = None
    for tier, values in HAMR_BUDGET_TIERS.items():
        if all(budget.get(k) == v for k, v in values.items()
               if k in ("max_memory_mb", "max_triangles", "max_texture_resolution")):
            tier_match = tier
            break
    if budget and tier_match is None:
        errors.append({"field": "budget", "reason": "no_exact_hamr_tier_no_silent_coercion"})
    if errors:
        return {**base, "translated": False, "failure": "hamr_incompatibility",
                "fail_closed": True, "incompatibilities": errors}
    return {**base, "translated": True, "failure": None, "fail_closed": False,
            "incompatibilities": [],
            "hamr_partial": {"name": forge_spec.get("avatar_id"),
                             "export": {"format": hamr_format},
                             "budget": {"tier": tier_match}}}


def route_presentation(record: Any, payload: Any) -> dict[str, Any]:
    """Presentation-only routing (s.50 item 8).

    Finished-artifact records route to voice/avatar/VRM
    clients as presentation-only consumers. Payloads that
    request secret access or cognitive control are refused
    by name; no secret access is ever granted here.
    """
    base = {"schema": "runeforge.smidja.presentation.v1",
            "service": "volmarr-smidja-forge", "source_revision": AUDITED_PIN,
            "sends_anything_external": False, "production_ready": False}
    if not isinstance(record, dict) or not record.get("artifact_id"):
        return {**base, "routed": False, "failure": "artifact_record_missing",
                "fail_closed": True}
    if not isinstance(payload, dict):
        return {**base, "routed": False, "failure": "payload_not_mapping",
                "fail_closed": True}
    for field in payload:
        if field in REFUSED_PAYLOAD_FIELDS:
            return {**base, "routed": False,
                    "failure": "presentation_payload_refused_by_name",
                    "fail_closed": True, "refused_field": field}
    return {**base, "routed": True, "failure": None, "fail_closed": False,
            "artifact_id": record["artifact_id"],
            "consumer_mode": "presentation_only",
            "secret_access": False, "cognitive_control": False,
            "fields": sorted(payload)}


# Labelled synthetic spec for the CLI plan verb: a dry-run plan
# over approved roots supplied by the CLI (the staged tree), 
# proving the plan machinery without any real workload.
def synthetic_spec(root: str) -> dict[str, Any]:
    return {
        "job_id": "forge-x15-synthetic-001", "spec_version": FORGE_SPEC_VERSION,
        "avatar_id": "synthetic_avatar_v1", "host": local_host(),
        "spec_path": f"{root}/specs/synthetic.yaml",
        "output_dir": f"{root}/output",
        "metadata": {"version": "1.0", "label": "labelled synthetic, not a real workload"},
        "blender_version": "4.x (labelled synthetic)",
        "export": {"format": "vrm", "vrm_version": "1.0", "exporter": "io_scene_vrm"},
        "budget": {"cpu_cores": 4, "gpu_required": False, "max_memory_mb": 1500.0,
                   "max_triangles": 50000, "max_texture_resolution": 1024,
                   "max_build_time_seconds": 45.0},
        "timeout_seconds": 120.0,
        "log_capture": {"mode": "record", "destination": "job_record"},
        "cancellation": {"mode": "record_cancel", "cooperative": True},
        "cleanup": {"mode": "record_level", "artifact_paths": [f"{root}/output/synthetic.vrm"]},
        "assets": [{"asset_id": "vroid/sample_a", "provenance": "hoard catalog (E.14 audit)",
                    "license": "CC0-1.0", "path": f"{root}/assets/sample_a.vrm"}],
    }


SYNTHETIC_REQUEST = {"spec": None, "redistribution": False, "destination": "local_only"}

__all__ = [
    "ADAPTER_VERSION", "AUDITED_PIN", "CANONICAL_REPO", "CANONICAL_REPO_URL",
    "CAPABILITY_MATRIX", "DEFAULT_BRANCH", "ENGINE_VERSION", "EXPORT_FORMATS",
    "FORGE_SPEC_VERSION", "HAMR_BUDGET_TIERS", "LICENSE_CONFLICT",
    "LICENSE_SHA256", "PERFORMANCE_BUDGET_MS", "PREFLIGHT_PLUGIN",
    "PROJECT_LICENSE", "SYNTHETIC_REQUEST", "approve_job", "cancel_job",
    "forge_catalog", "inspect_vrm_record", "local_host", "plan_build",
    "route_presentation", "smidja_forge_status", "synthetic_spec",
    "translate_forge_to_hamr", "translate_hamr_to_forge", "validate_forge_spec",
]
