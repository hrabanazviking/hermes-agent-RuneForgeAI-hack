"""Contracts for the phase tool/avatar audit (Slice 161).

Persona Runtime roadmap §87 (Phase 7 — Tool Integration)
and §88 (Phase 8 — Avatar Integration): each phase's
roadmap items stand reconciled against the banked surfaces
that carry them — the §87 flow steps after the Tool Policy
Markdown the three equivalents, carried in code or outside
this layer, and every §88 item an equivalent, carried by
§46 occasion-gated retrieval of the one compiled avatar
document — and the pure ``tool_avatar_audit`` proves both
phases' success criteria from supplied artefacts. No tool
is executed, and no avatar is controlled. Tests load
through real plugin discovery.
"""

from __future__ import annotations

import hashlib
import importlib
from pathlib import Path

import pytest
import yaml

from hermes_constants import (
    get_hermes_home,
    reset_hermes_home_override,
    set_hermes_home_override,
)

ENABLED = {"persona_runtime_enabled": True}

CORE_DOC = """# Core Identity

Caducea is a counselor who lives in the longhouse terminal.
Caducea gives advice carefully.

# Graceful Deference

Caducea defers gracefully when Volmarr decides.
"""

OTHER_CORE_DOC = """# Core Identity

Other is a smith who lives in the far forge.
Other gives advice bluntly.
"""

TOOL_POLICY_DOC = """# Force Push

Never force push a shared branch without explicit word.

# Remote Git Operations

Remote git operations use the named remote only.

# Reversibility

Prefer reversible operations and name what cannot be undone.

# Authorization

Authorization comes from Volmarr's explicit word.

# Filesystem

Filesystem writes stay inside the named project tree.

# Shell Operations

Shell operations are bounded, logged, and named first.

# Git Policy

Git policy defers to the sections above.
"""

AVATAR_DOC = """# Generating Images

Generating images follows the canonical appearance record.

# Controlling the Avatar

Controlling the avatar moves only on explicit direction.

# Describing Caducea

Describing Caducea uses the canonical appearance record.

# Selecting Expressions

Selecting expressions matches the moment's tone.

# VR Interaction

VR interaction keeps presence calm and bounded.

# Ordinary Text Inference

Ordinary text inference proceeds without embodiment detail.
"""

DOCS = {
    "core": ("core.md", CORE_DOC),
    "tool_policy": ("tool_policy.md", TOOL_POLICY_DOC),
    "avatar": ("avatar.md", AVATAR_DOC),
}

ANCHORS = [
    "Caducea is a counselor who lives in the longhouse terminal.",
    "Caducea gives advice carefully.",
]
ANTI_ANCHORS = [
    "Caducea is not a generic assistant.",
    "Caducea never relitigates settled decisions.",
]

TOOL = [
    {"item": "tool_policy_markdown",
     "roadmap_name": "Tool Policy Markdown",
     "status": "implemented", "section": "§44",
     "surface": "compiled tool_policy role + retrieve_tool_policy"},
    {"item": "policy_compiler", "roadmap_name": "Policy Compiler",
     "status": "equivalent", "section": "§§6, 47",
     "surface": "PersonaCompiler (§6) + policy_to_code governance "
                "classification (§47); no separate Policy Compiler"},
    {"item": "tool_permission_ir", "roadmap_name": "ToolPermissionIR",
     "status": "equivalent", "section": "§44",
     "surface": "classify_tool_action + the §44 per-action needs "
                "table (the permission IR in code, no named "
                "ToolPermissionIR artefact)"},
    {"item": "runtime_enforcement",
     "roadmap_name": "Runtime Enforcement",
     "status": "equivalent", "section": "§§44, 47",
     "surface": "deterministic needs + governance in code; this "
                "layer executes no tool (live enforcement carried "
                "by the Hermes tool layer outside the persona layer)"},
]

AVATAR = [
    {"item": "avatar_ir", "roadmap_name": "AvatarIR",
     "status": "equivalent", "section": "§46",
     "surface": "compiled avatar role sections in the §6 index + "
                "avatar_policy_usage_contract (the controller "
                "consumes AvatarIR directly; no separate AvatarIR "
                "builder in this layer)"},
    {"item": "vrm_controller", "roadmap_name": "VRM controller",
     "status": "equivalent", "section": "§46",
     "surface": "controlling_avatar occasion + retrieve_avatar_policy "
                "(no VRM controller owned)"},
    {"item": "emotion_mapper", "roadmap_name": "emotion mapper",
     "status": "equivalent", "section": "§46",
     "surface": "selecting_expressions occasion + "
                "retrieve_avatar_policy (no emotion mapper owned)"},
    {"item": "outfit_manager", "roadmap_name": "outfit manager",
     "status": "equivalent", "section": "§§46, 75",
     "surface": "avatar sections + §75 optional avatar_metadata in "
                "the export bundle (no outfit manager owned)"},
    {"item": "visual_state_system",
     "roadmap_name": "visual state system",
     "status": "equivalent", "section": "§46",
     "surface": "describing_persona + vr_interaction occasions + "
                "retrieve_avatar_policy (no visual state system owned)"},
    {"item": "image_generation_prompts",
     "roadmap_name": "image-generation prompts",
     "status": "equivalent", "section": "§46",
     "surface": "generating_images occasion + retrieve_avatar_policy "
                "(no image generator owned)"},
]

AVATAR_METADATA = {"appearance": "canonical appearance record"}


class _Ctx:
    def __init__(self, config=None):
        self._config = dict(config or {})

    def get_config(self, key, default=None):
        return self._config.get(key, default)


def _write_profile(home) -> None:
    home.mkdir(parents=True, exist_ok=True)
    (home / "config.yaml").write_text(
        "plugins:\n  enabled: [volmarr-core]\n", encoding="utf-8"
    )


def _load_modules():
    from hermes_cli import plugins as plugins_mod

    home = get_hermes_home()
    _write_profile(home)
    manager = plugins_mod.PluginManager()
    manager.discover_and_load()
    try:
        loaded = manager._plugins["volmarr-core"]
        package = loaded.module.__package__
        return (
            manager,
            importlib.import_module(f"{package}.persona_runtime"),
            importlib.import_module(f"{package}.identity"),
        )
    except Exception:
        manager.unload()
        raise


def _write_persona(home: Path, persona_id: str = "caducea",
                   core_doc: str = CORE_DOC,
                   anchors=ANCHORS, anti_anchors=ANTI_ANCHORS) -> None:
    persona_dir = home / "persona"
    persona_dir.mkdir(parents=True, exist_ok=True)
    docs = dict(DOCS)
    docs["core"] = (docs["core"][0], core_doc)
    for role, (name, text) in docs.items():
        (persona_dir / name).write_text(text, encoding="utf-8")
    persona = {
        "id": persona_id,
        "display_name": "Caducea Hermesdottir",
        "directory": "./persona",
        "version": "1.4.2",
        "documents": {
            role: {"file": name, "required": True}
            for role, (name, _text) in docs.items()
        },
    }
    if anchors:
        persona["anchors"] = list(anchors)
    if anti_anchors:
        persona["anti_anchors"] = list(anti_anchors)
    config_dir = home / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "persona.yaml").write_text(
        yaml.safe_dump({"persona": persona}, sort_keys=False),
        encoding="utf-8")


def _hashes(home: Path) -> dict[str, str]:
    return {
        str(path.relative_to(home)):
            hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(home.rglob("*"))
        if path.is_file() and "entity" not in path.parts
    }


def _compile(runtime, identity_mod):
    identity_mod.IdentityStore(_Ctx()).ensure()
    _write_persona(get_hermes_home())
    return runtime.PersonaCompiler(_Ctx(ENABLED)).compile()


def test_tool_phase_items_roadmap_order_and_isolation():
    mods = _load_modules()
    runtime = mods[1]
    try:
        items = runtime.tool_phase_items()
        items.append({"item": "x"})
        compiler = runtime.tool_phase_item("policy_compiler")
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.tool_phase_item("tool_registry")
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.tool_phase_item(None)
    finally:
        mods[0].unload()
    assert runtime.tool_phase_items() == TOOL
    assert [row[0] for row in runtime.TOOL_PHASE_ITEMS] == [
        row["item"] for row in TOOL]
    assert compiler == TOOL[1]
    assert compiler["status"] == "equivalent"


def test_avatar_phase_items_roadmap_order_and_isolation():
    mods = _load_modules()
    runtime = mods[1]
    try:
        items = runtime.avatar_phase_items()
        items.append({"item": "x"})
        outfit = runtime.avatar_phase_item("outfit_manager")
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.avatar_phase_item("renderer")
    finally:
        mods[0].unload()
    assert runtime.avatar_phase_items() == AVATAR
    assert [row[0] for row in runtime.AVATAR_PHASE_ITEMS] == [
        row["item"] for row in AVATAR]
    assert outfit == AVATAR[3]
    assert all(row["status"] == "equivalent" for row in AVATAR)


def test_tool_phase_contract_counts_equivalents_honestly():
    mods = _load_modules()
    runtime = mods[1]
    try:
        contract = runtime.tool_phase_contract()
    finally:
        mods[0].unload()
    assert contract["name"] == "PersonaPhase7ToolIntegration"
    assert contract["phase"] == 7
    assert contract["items"] == TOOL
    assert contract["item_count"] == 4
    assert contract["implemented"] == 1
    assert contract["equivalent"] == 3
    assert contract["missing"] == 0
    assert contract["success_criterion"] == (
        "Caducea's stated tool boundaries become actual "
        "software behavior.")
    assert contract["permissions_in_code"] is True
    assert contract["executes_tools"] is False
    assert contract["enforces_live_tool_calls"] is False


def test_avatar_phase_contract():
    mods = _load_modules()
    runtime = mods[1]
    try:
        contract = runtime.avatar_phase_contract()
    finally:
        mods[0].unload()
    assert contract["name"] == "PersonaPhase8AvatarIntegration"
    assert contract["phase"] == 8
    assert contract["items"] == AVATAR
    assert contract["item_count"] == 6
    assert contract["implemented"] == 0
    assert contract["equivalent"] == 6
    assert contract["missing"] == 0
    assert contract["success_criterion"] == (
        "Caducea looks like the same character across "
        "visual platforms.")
    assert contract["single_canonical_avatar_source"] is True
    assert contract["controls_avatar"] is False
    assert contract["owns_visual_consumers"] is False


def test_tool_avatar_contract_combined():
    mods = _load_modules()
    runtime = mods[1]
    try:
        combined = runtime.tool_avatar_contract()
    finally:
        mods[0].unload()
    assert combined["name"] == "PersonaPhases7And8"
    assert combined["tool_phase"] == runtime.tool_phase_contract()
    assert combined["avatar_phase"] == runtime.avatar_phase_contract()
    assert combined["audit_surface"] == "tool_avatar_audit"
    assert combined["permissions_in_code"] is True
    assert combined["executes_tools"] is False
    assert combined["single_canonical_avatar_source"] is True
    assert combined["controls_avatar"] is False


def test_audit_proves_criteria_from_compile():
    mods = _load_modules()
    runtime = mods[1]
    try:
        compiled = _compile(runtime, mods[2])
        audit = runtime.tool_avatar_audit(
            compiled, avatar_metadata=dict(AVATAR_METADATA))
    finally:
        mods[0].unload()
    assert audit["persona_id"] == "caducea"
    assert audit["checks"] == {
        "tool_policy_compiled": True,
        "force_push_needs_in_code": True,
        "tool_retrieval_selective": True,
        "file_reading_minimal": True,
        "permissions_governed_by_code": True,
        "tool_layer_executes_nothing": True,
        "avatar_compiled": True,
        "avatar_occasions_complete": True,
        "avatar_retrieval_selective": True,
        "avatar_outside_ordinary_inference": True,
        "avatar_export_consistent": True,
        "hash_record_matches": True,
    }
    assert audit["tool_policy_sections"] == 4
    assert audit["avatar_sections"] >= 1
    assert audit["tool_phase"]["criterion_met"] is True
    assert audit["tool_phase"]["implemented"] == 1
    assert audit["tool_phase"]["equivalent"] == 3
    assert audit["avatar_phase"]["criterion_met"] is True
    assert audit["avatar_phase"]["equivalent"] == 6
    assert audit["audits_only"] is True
    assert audit["loads_or_compiles"] is False
    assert audit["executes_tools"] is False
    assert audit["controls_avatar"] is False


def test_audit_avatar_metadata_absent_never_invented():
    mods = _load_modules()
    runtime = mods[1]
    try:
        compiled = _compile(runtime, mods[2])
        audit = runtime.tool_avatar_audit(compiled)
        bundle = runtime.persona_export(compiled)
    finally:
        mods[0].unload()
    assert audit["checks"]["avatar_export_consistent"] is True
    assert audit["avatar_phase"]["criterion_met"] is True
    assert bundle["avatar_present"] is False
    assert bundle["avatar_metadata"] is None


def test_audit_tamper_surfaces_as_unmet_not_invented():
    mods = _load_modules()
    runtime = mods[1]
    try:
        compiled = _compile(runtime, mods[2])
        bad_kernel = dict(compiled)
        bad_kernel["kernel"] = dict(compiled["kernel"])
        bad_kernel["kernel"]["sha256"] = "f" * 64
        audit_kernel = runtime.tool_avatar_audit(bad_kernel)
    finally:
        mods[0].unload()
    assert audit_kernel["checks"]["hash_record_matches"] is False
    assert audit_kernel["avatar_phase"]["criterion_met"] is False
    assert audit_kernel["tool_phase"]["criterion_met"] is True


def test_audit_refuses_malformed():
    mods = _load_modules()
    runtime = mods[1]
    try:
        compiled = _compile(runtime, mods[2])
        for bad in (None, "compiled", [], {}, {"persona_id": "x"}):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.tool_avatar_audit(bad)
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.tool_avatar_audit(compiled, avatar_metadata=123)
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.tool_avatar_audit(
                compiled, avatar_metadata={"k": "v" * 241})
    finally:
        mods[0].unload()


def test_packet_determinism_and_isolation(tmp_path):
    profile_b = tmp_path / "profile-b"
    mods = _load_modules()
    runtime = mods[1]
    try:
        mods[2].IdentityStore(_Ctx()).ensure()
        home = get_hermes_home()
        _write_persona(home)
        before = _hashes(home)
        compiled = runtime.PersonaCompiler(_Ctx(ENABLED)).compile()
        audit = runtime.tool_avatar_audit(compiled)
        first = runtime.PersonaRuntimeBridge(
            _Ctx(ENABLED)).packet_items("s1", "hello")
        second = runtime.PersonaRuntimeBridge(
            _Ctx(ENABLED)).packet_items("s1", "hello")
        after = _hashes(home)
        token = set_hermes_home_override(str(profile_b))
        try:
            _write_profile(profile_b)
            mods[2].IdentityStore(_Ctx()).ensure()
            _write_persona(
                profile_b, persona_id="other",
                core_doc=OTHER_CORE_DOC, anchors=(), anti_anchors=())
            other_audit = runtime.tool_avatar_audit(
                runtime.PersonaCompiler(_Ctx(ENABLED)).compile())
        finally:
            reset_hermes_home_override(token)
        third = runtime.PersonaRuntimeBridge(
            _Ctx(ENABLED)).packet_items("s1", "hello")
    finally:
        mods[0].unload()
    assert before == after
    assert audit["tool_phase"]["criterion_met"] is True
    assert audit["avatar_phase"]["criterion_met"] is True
    assert other_audit["persona_id"] == "other"
    assert other_audit["tool_phase"]["criterion_met"] is True
    assert other_audit["avatar_phase"]["criterion_met"] is True
    assert first[0].content == second[0].content == third[0].content
    assert len(first) == 1
    content = first[0].content
    assert "§§3-90" in content
    assert "§87 Phase 7 tool integration" in content
    assert "§88 Phase 8 avatar integration" in content
    assert "tool_avatar_audit proves both" in content
    # The packet names the contracts only — never canonical
    # persona text.
    assert "longhouse terminal" not in content
