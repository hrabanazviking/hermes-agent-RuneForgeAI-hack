"""Contracts for the phase memory/router audit (Slice 160).

Persona Runtime roadmap §85 (Phase 5 — Memory Integration)
and §86 (Phase 6 — Model Router Integration): each phase's
roadmap items stand reconciled against the banked surfaces
that carry them — the Muninn / SQLite memory, Service Bible
promotion, and persona-aware consolidation items the three
equivalents, carried outside this module or under another
section's governance — and the pure ``memory_model_audit``
proves both phases' success criteria from supplied
artefacts. No memory store is created or written, and no
live model is routed. Tests load through real plugin
discovery.
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

SERVICE_BIBLE_DOC = """# Communication Style

Caducea writes plainly and warmly when she explains.
"""

RELATIONSHIP_DOC = """# Counsel and Advice

Caducea listens first when Volmarr disagrees.
"""

DOCS = {
    "core": ("core.md", CORE_DOC),
    "memory_policy": ("memory_policy.md", MEMORY_POLICY_DOC),
    "service_bible": ("service_bible.md", SERVICE_BIBLE_DOC),
    "relationship": ("relationship.md", RELATIONSHIP_DOC),
}

ANCHORS = [
    "Caducea is a counselor who lives in the longhouse terminal.",
    "Caducea gives advice carefully.",
]
ANTI_ANCHORS = [
    "Caducea is not a generic assistant.",
    "Caducea never relitigates settled decisions.",
]

MEMORY = [
    {"item": "persona_ir", "roadmap_name": "PersonaIR",
     "status": "implemented", "section": "§8",
     "surface": "build_persona_ir + compiled PersonaIR ir_hash"},
    {"item": "muninn_sqlite_memory",
     "roadmap_name": "Muninn / SQLite memory",
     "status": "equivalent", "section": "memory fabric",
     "surface": "probe_bifrost_muninn + ravens Muninn binding "
                "(persona layer owns no store)"},
    {"item": "service_bible_promotion",
     "roadmap_name": "Service Bible promotion",
     "status": "equivalent", "section": "§42",
     "surface": "retrieve_service_bible (selective promotion into "
                "context, never continuously injected)"},
    {"item": "relationship_memory",
     "roadmap_name": "relationship memory",
     "status": "implemented", "section": "§43",
     "surface": "retrieve_relationship_model + "
                "relationship_retrieval_need"},
    {"item": "trait_state_separation",
     "roadmap_name": "trait/state separation",
     "status": "implemented", "section": "§26",
     "surface": "trait_state_separation + classify_attribute"},
    {"item": "persona_aware_consolidation",
     "roadmap_name": "persona-aware consolidation",
     "status": "equivalent", "section": "§§55, 25-26",
     "surface": "compression_plan governed by the §25 summary guard "
                "+ §26 trait/state separation"},
]

ROUTER = [
    {"item": "kernel_tiers",
     "roadmap_name": "micro/medium/full kernels",
     "status": "implemented", "section": "§§64-65",
     "surface": "kernel_tiers + kernel_distillation_plan + "
                "micro_kernel"},
    {"item": "persona_handoff_packets",
     "roadmap_name": "persona handoff packets",
     "status": "implemented", "section": "§35",
     "surface": "handoff_packet + validate_handoff_packet"},
    {"item": "per_model_adherence_scores",
     "roadmap_name": "per-model adherence scores",
     "status": "implemented", "section": "§§61-63",
     "surface": "persona_adherence + model_quality_table + "
                "model_metrics"},
    {"item": "model_specific_context_budgets",
     "roadmap_name": "model-specific context budgets",
     "status": "implemented", "section": "§15",
     "surface": "budget_allocations + budget_items "
                "(model context classes)"},
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
                   core_doc: str = CORE_DOC,
                   anchors=ANCHORS, anti_anchors=ANTI_ANCHORS,
                   full_docs: bool = True) -> None:
    persona_dir = home / "persona"
    persona_dir.mkdir(parents=True, exist_ok=True)
    docs = dict(DOCS) if full_docs else {
        "core": DOCS["core"],
        "memory_policy": DOCS["memory_policy"],
    }
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


def test_memory_phase_items_roadmap_order_and_isolation():
    mods = _load_modules()
    runtime = mods[1]
    try:
        items = runtime.memory_phase_items()
        items.append({"item": "x"})
        muninn = runtime.memory_phase_item("muninn_sqlite_memory")
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.memory_phase_item("vector_database")
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.memory_phase_item(None)
    finally:
        mods[0].unload()
    assert runtime.memory_phase_items() == MEMORY
    assert [row[0] for row in runtime.MEMORY_PHASE_ITEMS] == [
        row["item"] for row in MEMORY]
    assert muninn == MEMORY[1]
    assert muninn["status"] == "equivalent"


def test_model_router_phase_items_roadmap_order_and_isolation():
    mods = _load_modules()
    runtime = mods[1]
    try:
        items = runtime.model_router_phase_items()
        items.append({"item": "x"})
        budgets = runtime.model_router_phase_item(
            "model_specific_context_budgets")
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.model_router_phase_item("model_registry")
    finally:
        mods[0].unload()
    assert runtime.model_router_phase_items() == ROUTER
    assert [row[0] for row in runtime.MODEL_ROUTER_PHASE_ITEMS] == [
        row["item"] for row in ROUTER]
    assert budgets == ROUTER[3]
    assert all(row["status"] == "implemented" for row in ROUTER)


def test_memory_phase_contract_counts_equivalents_honestly():
    mods = _load_modules()
    runtime = mods[1]
    try:
        contract = runtime.memory_phase_contract()
    finally:
        mods[0].unload()
    assert contract["name"] == "PersonaPhase5MemoryIntegration"
    assert contract["phase"] == 5
    assert contract["items"] == MEMORY
    assert contract["item_count"] == 6
    assert contract["implemented"] == 3
    assert contract["equivalent"] == 3
    assert contract["missing"] == 0
    assert contract["success_criterion"] == (
        "Caducea learns without rewriting her core personality.")
    assert contract["owns_memory_store"] is False
    assert contract["writes_memory"] is False
    assert contract["rewrites_core_personality"] is False
    assert contract["muninn_sqlite_carried_by"] == (
        "memory fabric probe + ravens binding")


def test_model_router_phase_contract():
    mods = _load_modules()
    runtime = mods[1]
    try:
        contract = runtime.model_router_phase_contract()
    finally:
        mods[0].unload()
    assert contract["name"] == "PersonaPhase6ModelRouterIntegration"
    assert contract["phase"] == 6
    assert contract["items"] == ROUTER
    assert contract["item_count"] == 4
    assert contract["implemented"] == 4
    assert contract["equivalent"] == 0
    assert contract["missing"] == 0
    assert contract["success_criterion"] == (
        "Switching models does not feel like switching characters.")
    assert contract["same_kernel_for_all_models"] is True
    assert contract["routes_live_models"] is False


def test_memory_model_contract_combined():
    mods = _load_modules()
    runtime = mods[1]
    try:
        combined = runtime.memory_model_contract()
    finally:
        mods[0].unload()
    assert combined["name"] == "PersonaPhases5And6"
    assert combined["memory_phase"] == runtime.memory_phase_contract()
    assert combined["model_router_phase"] == (
        runtime.model_router_phase_contract())
    assert combined["audit_surface"] == "memory_model_audit"
    assert combined["owns_memory_store"] is False
    assert combined["new_memory_store_created"] is False
    assert combined["routes_live_models"] is False
    assert combined["same_kernel_for_all_models"] is True


def test_audit_proves_criteria_from_compile():
    mods = _load_modules()
    runtime = mods[1]
    try:
        compiled = _compile(runtime, mods[2])
        audit = runtime.memory_model_audit(compiled)
    finally:
        mods[0].unload()
    assert audit["persona_id"] == "caducea"
    assert audit["checks"] == {
        "ir_matches_recomputation": True,
        "memory_record_validates": True,
        "memory_cannot_override": True,
        "memory_claims_classified": True,
        "trait_state_separation_holds": True,
        "service_bible_promotion_selective": True,
        "relationship_retrieval_selective": True,
        "consolidation_governed": True,
        "kernel_tiers_same_source": True,
        "switch_preserves_kernel": True,
        "hash_record_matches": True,
        "adherence_derived_from_drift": True,
        "metrics_adherence_agrees": True,
        "budgets_scale_by_model_class": True,
    }
    assert audit["service_bible_sections"] >= 1
    assert audit["relationship_sections"] >= 1
    # The §61 example averages: remote_model drifts least.
    assert audit["preferred_companionship_model"] == "remote_model"
    assert audit["switch_from"] == "local_model"
    assert audit["switch_to"] == "cloud_model"
    assert audit["kernel_hash"] == compiled["kernel"]["sha256"]
    assert audit["memory_phase"]["criterion_met"] is True
    assert audit["memory_phase"]["implemented"] == 3
    assert audit["memory_phase"]["equivalent"] == 3
    assert audit["model_router_phase"]["criterion_met"] is True
    assert audit["audits_only"] is True
    assert audit["loads_or_compiles"] is False
    assert audit["writes_memory"] is False
    assert audit["routes_live_models"] is False


def test_audit_supplied_models_and_averages():
    mods = _load_modules()
    runtime = mods[1]
    try:
        compiled = _compile(runtime, mods[2])
        audit = runtime.memory_model_audit(
            compiled,
            model_averages={"alpha": 0.5, "beta": 0.25},
            from_model="alpha", to_model="beta")
        record = runtime.persona_memory(
            "caducea", "chose the quieter road",
            considered="the louder road", recommended_by="volmarr",
            response_by="caducea", response="thanked him plainly")
        audit_record = runtime.memory_model_audit(
            compiled, memory_record=record)
    finally:
        mods[0].unload()
    assert audit["preferred_companionship_model"] == "beta"
    assert audit["switch_from"] == "alpha"
    assert audit["switch_to"] == "beta"
    assert audit["checks"]["adherence_derived_from_drift"] is True
    assert audit["checks"]["metrics_adherence_agrees"] is True
    assert audit["model_router_phase"]["criterion_met"] is True
    assert audit_record["checks"]["memory_record_validates"] is True
    assert audit_record["memory_phase"]["criterion_met"] is True


def test_audit_tamper_surfaces_as_unmet_not_invented():
    mods = _load_modules()
    runtime = mods[1]
    try:
        compiled = _compile(runtime, mods[2])
        bad_ir = dict(compiled)
        bad_ir["ir"] = dict(compiled["ir"])
        bad_ir["ir"]["ir_hash"] = "0" * 64
        audit_ir = runtime.memory_model_audit(bad_ir)
        bad_kernel = dict(compiled)
        bad_kernel["kernel"] = dict(compiled["kernel"])
        bad_kernel["kernel"]["sha256"] = "f" * 64
        audit_kernel = runtime.memory_model_audit(bad_kernel)
        audit_claim = runtime.memory_model_audit(
            compiled,
            trait_claim="Caducea was tired during the long review")
    finally:
        mods[0].unload()
    assert audit_ir["checks"]["ir_matches_recomputation"] is False
    assert audit_ir["memory_phase"]["criterion_met"] is False
    assert audit_ir["model_router_phase"]["criterion_met"] is True
    assert audit_kernel["checks"]["hash_record_matches"] is False
    assert audit_kernel["model_router_phase"]["criterion_met"] is False
    assert audit_kernel["memory_phase"]["criterion_met"] is True
    # A state-form claim supplied where a trait-form claim is
    # being tested for refusal surfaces as unmet, never as a
    # refused trait claim.
    assert audit_claim["checks"]["memory_claims_classified"] is False
    assert audit_claim["memory_phase"]["criterion_met"] is False
    assert audit_claim["model_router_phase"]["criterion_met"] is True


def test_audit_refuses_malformed():
    mods = _load_modules()
    runtime = mods[1]
    try:
        compiled = _compile(runtime, mods[2])
        for bad in (None, "compiled", [], {}, {"persona_id": "x"}):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.memory_model_audit(bad)
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.memory_model_audit(compiled, trait_claim=123)
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.memory_model_audit(compiled, state_claim=123)
        tampered = runtime.persona_memory(
            "caducea", "kept the northern road")
        tampered["persona_memory"]["memory_text"] = "Invented."
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.memory_model_audit(
                compiled, memory_record=tampered)
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.memory_model_audit(
                compiled, memory_record={"persona_memory": {}})
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.memory_model_audit(
                compiled, model_averages="averages")
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.memory_model_audit(
                compiled, model_averages={"m": 2.0})
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.memory_model_audit(
                compiled, models={"m": {"reasoning": 0.5}})
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.memory_model_audit(
                compiled, from_model="same", to_model="same")
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.memory_model_audit(compiled, from_model=123)
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
        audit = runtime.memory_model_audit(compiled)
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
                core_doc=OTHER_CORE_DOC, anchors=(), anti_anchors=(),
                full_docs=False)
            other_audit = runtime.memory_model_audit(
                runtime.PersonaCompiler(_Ctx(ENABLED)).compile())
        finally:
            reset_hermes_home_override(token)
        third = runtime.PersonaRuntimeBridge(
            _Ctx(ENABLED)).packet_items("s1", "hello")
    finally:
        mods[0].unload()
    assert before == after
    assert audit["memory_phase"]["criterion_met"] is True
    assert audit["model_router_phase"]["criterion_met"] is True
    assert other_audit["persona_id"] == "other"
    # Profile B carries no Service Bible or relationship
    # document: the selective-retrieval checks hold
    # vacuously and both criteria remain honestly met by
    # the surfaces B does carry.
    assert other_audit["service_bible_sections"] == 0
    assert other_audit["relationship_sections"] == 0
    assert other_audit["memory_phase"]["criterion_met"] is True
    assert other_audit["model_router_phase"]["criterion_met"] is True
    assert first[0].content == second[0].content == third[0].content
    assert len(first) == 1
    content = first[0].content
    assert "§§3-88" in content
    assert "§85 Phase 5 memory integration" in content
    assert "§86 Phase 6 model router integration" in content
    assert "memory_model_audit proves both" in content
    # The packet names the contracts only — never canonical
    # persona text.
    assert "longhouse terminal" not in content
