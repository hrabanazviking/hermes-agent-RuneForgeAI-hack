"""Contracts for the phase foundation/compiler audit (Slice 158).

Persona Runtime roadmap §81 (Phase 1 — Foundation) and §82
(Phase 2 — Compiler): each phase's roadmap items stand
reconciled against the banked surfaces that carry them —
the PersonaLoader is the one equivalent, carried by the
§3 config store plus the §6 compiler — and the pure
``phase_audit`` proves both phases' success criteria from
a supplied compiled artefact itself. No new loader or
compiler stands, nothing is loaded or compiled by the
audit, and no live startup wiring is claimed. Tests load
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

MEMORY_POLICY_DOC = """# Resolving Memory Conflicts

When memories conflict, the newer verified record wins.
"""

DOCS = {
    "core": ("core.md", CORE_DOC),
    "memory_policy": ("memory_policy.md", MEMORY_POLICY_DOC),
}

FOUNDATION = [
    {"item": "persona_yaml", "roadmap_name": "persona.yaml",
     "status": "implemented", "section": "§3",
     "surface": "PersonaConfigStore"},
    {"item": "persona_loader", "roadmap_name": "PersonaLoader",
     "status": "equivalent", "section": "§§3, 6",
     "surface": "PersonaConfigStore + PersonaCompiler.compile"},
    {"item": "document_role_mapping",
     "roadmap_name": "document role mapping",
     "status": "implemented", "section": "§3",
     "surface": "PersonaConfigStore documents map"},
    {"item": "file_validation", "roadmap_name": "file validation",
     "status": "implemented", "section": "§§3, 6",
     "surface": "PersonaConfigStore + PersonaCompiler.compile"},
    {"item": "hot_reload", "roadmap_name": "hot reload",
     "status": "implemented", "section": "§20",
     "surface": "PersonaReloader.check"},
    {"item": "source_hashing", "roadmap_name": "source hashing",
     "status": "implemented", "section": "§19",
     "surface": "hash_record"},
]

COMPILER_PHASE = [
    {"item": "markdown_section_parser",
     "roadmap_name": "Markdown section parser",
     "status": "implemented", "section": "§11",
     "surface": "parse_sections"},
    {"item": "persona_ir", "roadmap_name": "PersonaIR",
     "status": "implemented", "section": "§8",
     "surface": "build_persona_ir"},
    {"item": "section_identifiers",
     "roadmap_name": "section identifiers",
     "status": "implemented", "section": "§12",
     "surface": "stable_section_id"},
    {"item": "priority_metadata", "roadmap_name": "priority metadata",
     "status": "implemented", "section": "§§11, 16",
     "surface": "section_priority + priority_level"},
    {"item": "compiled_manifest", "roadmap_name": "compiled manifest",
     "status": "implemented", "section": "§50",
     "surface": "manifest"},
    {"item": "persona_kernel_generation",
     "roadmap_name": "Persona Kernel generation",
     "status": "implemented", "section": "§9",
     "surface": "PersonaCompiler kernel"},
]


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
                   core_doc: str = CORE_DOC) -> None:
    persona_dir = home / "persona"
    persona_dir.mkdir(parents=True, exist_ok=True)
    docs = dict(DOCS)
    docs["core"] = ("core.md", core_doc)
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


def test_foundation_items_roadmap_order_and_isolation():
    mods = _load_modules()
    runtime = mods[1]
    try:
        items = runtime.foundation_items()
        items.append({"item": "x"})
        loader = runtime.foundation_item("persona_loader")
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.foundation_item("persona_watcher")
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.foundation_item(None)
    finally:
        mods[0].unload()
    assert runtime.foundation_items() == FOUNDATION
    assert [row[0] for row in runtime.FOUNDATION_ITEMS] == [
        row["item"] for row in FOUNDATION]
    assert loader == FOUNDATION[1]
    assert loader["status"] == "equivalent"


def test_compiler_phase_items_all_implemented():
    mods = _load_modules()
    runtime = mods[1]
    try:
        items = runtime.compiler_phase_items()
        kernel = runtime.compiler_phase_item(
            "persona_kernel_generation")
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.compiler_phase_item("embeddings")
    finally:
        mods[0].unload()
    assert items == COMPILER_PHASE
    assert all(row["status"] == "implemented" for row in items)
    assert kernel["section"] == "§9"


def test_foundation_contract():
    mods = _load_modules()
    runtime = mods[1]
    try:
        contract = runtime.foundation_contract()
    finally:
        mods[0].unload()
    assert contract["name"] == "PersonaPhase1Foundation"
    assert contract["phase"] == 1
    assert contract["items"] == FOUNDATION
    assert contract["item_count"] == 6
    assert contract["implemented"] == 5
    assert contract["equivalent"] == 1
    assert contract["missing"] == 0
    assert contract["success_criterion"] == (
        "Hermes can load arbitrarily named persona documents "
        "from configuration.")
    assert contract["criterion_met_at"] == (
        "compiler layer (explicit compile)")
    assert contract["new_loader_created"] is False
    assert contract["live_startup_wiring_claimed"] is False


def test_compiler_phase_contract():
    mods = _load_modules()
    runtime = mods[1]
    try:
        contract = runtime.compiler_phase_contract()
    finally:
        mods[0].unload()
    assert contract["name"] == "PersonaPhase2Compiler"
    assert contract["phase"] == 2
    assert contract["items"] == COMPILER_PHASE
    assert contract["item_count"] == 6
    assert contract["implemented"] == 6
    assert contract["equivalent"] == 0
    assert contract["missing"] == 0
    assert contract["success_criterion"] == (
        "Six large Markdown files become one compact runtime "
        "identity plus indexed detail.")
    assert contract["compact_identity"] == "§9 Persona Kernel"
    assert contract["new_compiler_created"] is False


def test_phases_contract_combined():
    mods = _load_modules()
    runtime = mods[1]
    try:
        combined = runtime.phases_contract()
    finally:
        mods[0].unload()
    assert combined["name"] == "PersonaPhases1And2"
    assert combined["foundation"] == runtime.foundation_contract()
    assert combined["compiler_phase"] == (
        runtime.compiler_phase_contract())
    assert combined["audit_surface"] == "phase_audit"
    assert combined["new_loader_created"] is False
    assert combined["new_compiler_created"] is False


def test_phase_audit_proves_criteria_from_compile():
    mods = _load_modules()
    runtime = mods[1]
    try:
        mods[2].IdentityStore(_Ctx()).ensure()
        _write_persona(get_hermes_home())
        compiled = runtime.PersonaCompiler(_Ctx(ENABLED)).compile()
        audit = runtime.phase_audit(compiled)
    finally:
        mods[0].unload()
    # The config names core.md / memory_policy.md — not the
    # roadmap's default filenames — and the compile loaded
    # them by role: the §81 criterion, from the artefact.
    assert [doc["file"] for doc in compiled["documents"]] == [
        "core.md", "memory_policy.md"]
    assert audit["persona_id"] == "caducea"
    assert audit["checks"] == {
        "documents_loaded": True,
        "role_mapping_present": True,
        "source_hashes_present": True,
        "kernel_present": True,
        "index_present": True,
        "stable_ids_present": True,
        "priority_metadata_present": True,
        "ir_present": True,
        "manifest_consistent": True,
        "hash_record_matches": True,
    }
    assert audit["document_count"] == 2
    assert audit["indexed_sections"] == 3
    assert audit["foundation"]["criterion_met"] is True
    assert audit["compiler_phase"]["criterion_met"] is True
    assert audit["audits_only"] is True
    assert audit["loads_or_compiles"] is False


def test_phase_audit_tamper_surfaces_as_unmet_not_invented():
    mods = _load_modules()
    runtime = mods[1]
    try:
        mods[2].IdentityStore(_Ctx()).ensure()
        _write_persona(get_hermes_home())
        compiled = runtime.PersonaCompiler(_Ctx(ENABLED)).compile()
        bad_id = dict(compiled)
        bad_id["index"] = [dict(entry) for entry in compiled["index"]]
        bad_id["index"][0]["stable_id"] = "core.elsewhere"
        audit_id = runtime.phase_audit(bad_id)
        bad_hash = dict(compiled)
        bad_hash["persona_hash"] = "0" * 64
        audit_hash = runtime.phase_audit(bad_hash)
        bad_doc = dict(compiled)
        bad_doc["documents"] = [
            dict(doc) for doc in compiled["documents"]]
        bad_doc["documents"][0]["sha256"] = "not-a-hash"
        audit_doc = runtime.phase_audit(bad_doc)
    finally:
        mods[0].unload()
    assert audit_id["checks"]["stable_ids_present"] is False
    assert audit_id["compiler_phase"]["criterion_met"] is False
    assert audit_id["foundation"]["criterion_met"] is True
    assert audit_hash["checks"]["hash_record_matches"] is False
    assert audit_doc["checks"]["source_hashes_present"] is False
    assert audit_doc["foundation"]["criterion_met"] is False


def test_phase_audit_refuses_malformed():
    mods = _load_modules()
    runtime = mods[1]
    try:
        for bad in (None, "compiled", [], {}, {"persona_id": "x"}):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.phase_audit(bad)
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
        audit = runtime.phase_audit(compiled)
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
                core_doc=OTHER_CORE_DOC)
            other_audit = runtime.phase_audit(
                runtime.PersonaCompiler(_Ctx(ENABLED)).compile())
        finally:
            reset_hermes_home_override(token)
        third = runtime.PersonaRuntimeBridge(
            _Ctx(ENABLED)).packet_items("s1", "hello")
    finally:
        mods[0].unload()
    assert before == after
    assert audit["foundation"]["criterion_met"] is True
    assert other_audit["persona_id"] == "other"
    assert other_audit["compiler_phase"]["criterion_met"] is True
    assert first[0].content == second[0].content == third[0].content
    assert len(first) == 1
    content = first[0].content
    assert "§§3-84" in content
    assert "§81 Phase 1 foundation" in content
    assert "§82 Phase 2" in content
    assert "phase_audit proves both" in content
    # The packet names the contracts only — never canonical
    # persona text.
    assert "longhouse terminal" not in content
