"""Contracts for the architecture/rule audit (Slice 163).

Persona Runtime roadmap §91 (Long-Term Architecture) and
§92 (Most Important Rule): each roadmap element stands
reconciled against the banked surfaces that carry it --
the architecture spine implemented by its own sections
with the fan-out, the models, and the output equivalents,
and the rule implemented with memory's lived history the
one equivalent -- and the pure ``architecture_rule_audit``
proves both from supplied artefacts. No pipeline runs, no
model is called, and no output is generated. Tests load
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

RELATIONSHIP_DOC = """# Counsel and Advice

Caducea listens first when Volmarr disagrees.
"""

TOOL_POLICY_DOC = """# Force Push

Never force push a shared branch without explicit word.
"""

AVATAR_DOC = """# Generating Images

Generating images follows the canonical appearance record.
"""

DOCS = {
    "core": ("core.md", CORE_DOC),
    "relationship": ("relationship.md", RELATIONSHIP_DOC),
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

ARCHITECTURE = [
    {"item": "human_editable_persona_documents",
     "roadmap_name": "human-editable persona documents",
     "status": "implemented", "section": "§§3, 6",
     "surface": "PersonaConfigStore (read-only) + "
                "PersonaCompiler over the human-authored "
                "documents"},
    {"item": "persona_compiler",
     "roadmap_name": "Persona Compiler",
     "status": "implemented", "section": "§6",
     "surface": "PersonaCompiler.compile"},
    {"item": "kernel_persona_ir_index",
     "roadmap_name": "Kernel / PersonaIR / Index",
     "status": "implemented", "section": "§§8-12",
     "surface": "compiled kernel (Layer A) + "
                "build_persona_ir + compiled section index "
                "with §12 stable ids"},
    {"item": "persona_router", "roadmap_name": "PersonaRouter",
     "status": "implemented", "section": "§14",
     "surface": "PersonaRouter + route_sections"},
    {"item": "memory_router", "roadmap_name": "Memory Router",
     "status": "equivalent", "section": "§§52, 85",
     "surface": "the §52 pipeline's memory_retrieval stage, "
                "owned by the memory subsystem, over the §85 "
                "memory integration surfaces (no separate "
                "Memory Router stands in this layer)"},
    {"item": "project_context",
     "roadmap_name": "Project Context",
     "status": "equivalent", "section": "§§52, 56",
     "surface": "the §56 placement \u2014 task state lives in "
                "project context, owned externally (no Project "
                "Router stands in this layer)"},
    {"item": "tools_state", "roadmap_name": "Tools State",
     "status": "equivalent", "section": "§§44, 52",
     "surface": "§44 tool-policy retrieval + the §52 "
                "pipeline's tools_or_response stage, owned by "
                "the caller (no Tools State router stands in "
                "this layer)"},
    {"item": "context_builder",
     "roadmap_name": "ContextBuilder",
     "status": "equivalent", "section": "§§15, 53",
     "surface": "PersonaContextBudgeter + "
                "prompt_assembly_order (the builder stands as "
                "the budgeter plus the pure assembly order; no "
                "live ContextBuilder assembles a prompt)"},
    {"item": "model_router", "roadmap_name": "Model Router",
     "status": "implemented", "section": "§§62-63",
     "surface": "model_router_contract + model metrics "
                "selection (the PersonaAwareModelRouter "
                "surfaces)"},
    {"item": "local_model", "roadmap_name": "local model",
     "status": "equivalent", "section": "§§34-35, 62",
     "surface": "the §34 model-switch plan's local side (the "
                "model itself is external; every model "
                "receives the same canonical kernel)"},
    {"item": "heavy_model", "roadmap_name": "heavy model",
     "status": "equivalent", "section": "§§34-35, 62",
     "surface": "the §34 model-switch plan's heavy side (the "
                "model itself is external; every model "
                "receives the same canonical kernel)"},
    {"item": "persona_watchdog",
     "roadmap_name": "PersonaWatchdog",
     "status": "implemented", "section": "§§27-33",
     "surface": "watchdog_contract + drift_score + the local "
                "watchdog and refresh surfaces"},
    {"item": "caducea_output", "roadmap_name": "Caducea output",
     "status": "equivalent", "section": "§52",
     "surface": "the §52 pipeline's final tools_or_response "
                "stage, owned by the caller and the model (the "
                "watchdog evaluates drafts only; this layer "
                "generates no output)"},
]

RULE = [
    {"item": "persistence_not_history_dependent",
     "roadmap_name": "character persistence never depends on "
                     "conversation history",
     "status": "implemented", "section": "§§24, 56",
     "surface": "precedence_order (conversation is tier 5 of "
                "6) + long_term_design_contract (identity "
                "lives in persona; the model never needs the "
                "entire history to remain itself)"},
    {"item": "canonical_documents_are_the_anchor",
     "roadmap_name": "canonical persona documents are the "
                     "anchor",
     "status": "implemented", "section": "§§3, 6, 67",
     "surface": "the compiler compiles canonical documents "
                "only + canonical_file_priority (semantic "
                "authority order)"},
    {"item": "kernel_keeps_anchor_present",
     "roadmap_name": "compiled kernel keeps the anchor "
                     "continuously present",
     "status": "implemented", "section": "§§10, 53, 66",
     "surface": "kernel pinning + prompt_assembly_contract "
                "(kernel at position 1) + "
                "context_pressure_contract (persona kernel "
                "never evicted)"},
    {"item": "retrieval_depth_only_when_needed",
     "roadmap_name": "retrieval provides depth only when "
                     "needed",
     "status": "implemented", "section": "§§13-14",
     "surface": "retrieve_sections + route_sections "
                "(explicit-only; no signal routes nothing)"},
    {"item": "memory_supplies_lived_history",
     "roadmap_name": "memory supplies lived history",
     "status": "equivalent", "section": "§§41, 55-56",
     "surface": "the memory subsystem supplies the history "
                "(external); this layer's §§41/55-56 guard "
                "and place it \u2014 memory records history and "
                "never redefines traits"},
    {"item": "watchdog_detects_drift",
     "roadmap_name": "watchdog detects drift",
     "status": "implemented", "section": "§§27-33",
     "surface": "watchdog_contract + drift_score + "
                "repair_plan"},
    {"item": "only_persona_defines_foundational_identity",
     "roadmap_name": "only the persona component defines "
                     "foundational identity",
     "status": "implemented", "section": "§§24, 67, 25-26",
     "surface": "precedence + canonical priority (only a "
                "canonical document tier may touch the "
                "foundations) + the §§25-26 summary and "
                "trait guards"},
]

COMPONENTS = [
    {"component": "persona",
     "contributes": "canonical persona documents, compiled",
     "defines_foundational_identity": True},
    {"component": "memory", "contributes": "lived history",
     "defines_foundational_identity": False},
    {"component": "state",
     "contributes": "current persona state",
     "defines_foundational_identity": False},
    {"component": "context", "contributes": "current context",
     "defines_foundational_identity": False},
    {"component": "model",
     "contributes": "replaceable cognition",
     "defines_foundational_identity": False},
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


def _compile(runtime, identity_mod, core_doc: str = CORE_DOC):
    identity_mod.IdentityStore(_Ctx()).ensure()
    _write_persona(get_hermes_home(), core_doc=core_doc)
    return runtime.PersonaCompiler(_Ctx(ENABLED)).compile()

def test_architecture_items_roadmap_order_and_isolation():
    mods = _load_modules()
    runtime = mods[1]
    try:
        items = runtime.architecture_items()
        items.append({"item": "x"})
        router = runtime.architecture_item("persona_router")
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.architecture_item("live_pipeline")
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.architecture_item(None)
    finally:
        mods[0].unload()
    assert runtime.architecture_items() == ARCHITECTURE
    assert [row[0] for row in runtime.ARCHITECTURE_ITEMS] == [
        row["item"] for row in ARCHITECTURE]
    assert router == ARCHITECTURE[3]
    assert router["status"] == "implemented"


def test_rule_items_roadmap_order_and_isolation():
    mods = _load_modules()
    runtime = mods[1]
    try:
        items = runtime.most_important_rule_items()
        items.append({"item": "x"})
        anchor = runtime.most_important_rule_item(
            "canonical_documents_are_the_anchor")
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.most_important_rule_item("history_anchor")
    finally:
        mods[0].unload()
    assert runtime.most_important_rule_items() == RULE
    assert [row[0] for row in
            runtime.MOST_IMPORTANT_RULE_ITEMS] == [
        row["item"] for row in RULE]
    assert anchor == RULE[1]
    assert anchor["status"] == "implemented"


def test_architecture_contract_counts_equivalents_honestly():
    mods = _load_modules()
    runtime = mods[1]
    try:
        contract = runtime.architecture_contract()
    finally:
        mods[0].unload()
    assert contract["name"] == "PersonaLongTermArchitecture"
    assert contract["section"] == 91
    assert contract["items"] == ARCHITECTURE
    assert contract["item_count"] == 13
    assert contract["implemented"] == 6
    assert contract["equivalent"] == 7
    assert contract["missing"] == 0
    assert contract["success_criterion"] == (
        "The final conceptual system stands as one flow from "
        "human-editable documents through compiler, router, "
        "context, and model to watchdog-guarded output.")
    assert contract["runs_pipeline"] is False
    assert contract["assembles_prompt"] is False
    assert contract["calls_model"] is False
    assert contract["generates_output"] is False


def test_most_important_rule_contract_and_components():
    mods = _load_modules()
    runtime = mods[1]
    try:
        contract = runtime.most_important_rule_contract()
        components = runtime.caducea_moment_components()
        persona = runtime.caducea_moment_component("persona")
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.caducea_moment_component("history")
    finally:
        mods[0].unload()
    assert contract["name"] == "PersonaMostImportantRule"
    assert contract["section"] == 92
    assert contract["items"] == RULE
    assert contract["item_count"] == 7
    assert contract["implemented"] == 6
    assert contract["equivalent"] == 1
    assert contract["missing"] == 0
    assert contract["rule"] == (
        "Never make character persistence depend on "
        "conversation history.")
    assert contract["success_criterion"] == contract["rule"]
    assert contract["formula"] == (
        "PERSONA + MEMORY + STATE + CONTEXT + MODEL = "
        "CADUCEA AT THIS MOMENT")
    assert contract["components"] == COMPONENTS
    assert contract["defines_foundational_identity"] == [
        "persona"]
    assert contract["persistence_depends_on_history"] is False
    assert contract["models_replaceable"] is True
    assert contract["summaries_may_redefine_identity"] is False
    assert components == COMPONENTS
    assert persona == COMPONENTS[0]


def test_architecture_rule_contract_combined():
    mods = _load_modules()
    runtime = mods[1]
    try:
        combined = runtime.architecture_rule_contract()
    finally:
        mods[0].unload()
    assert combined["name"] == (
        "PersonaArchitectureAndMostImportantRule")
    assert combined["architecture"] == (
        runtime.architecture_contract())
    assert combined["most_important_rule"] == (
        runtime.most_important_rule_contract())
    assert combined["audit_surface"] == "architecture_rule_audit"
    assert combined["formula"] == (
        "PERSONA + MEMORY + STATE + CONTEXT + MODEL = "
        "CADUCEA AT THIS MOMENT")
    assert combined["persistence_depends_on_history"] is False
    assert combined["defines_foundational_identity"] == [
        "persona"]
    assert combined["runs_pipeline"] is False
    assert combined["generates_output"] is False


def test_audit_proves_both_from_compile():
    mods = _load_modules()
    runtime = mods[1]
    try:
        compiled = _compile(runtime, mods[2])
        audit = runtime.architecture_rule_audit(compiled)
    finally:
        mods[0].unload()
    assert audit["persona_id"] == "caducea"
    assert audit["checks"] == {
        "compiler_outputs_stand_together": True,
        "pipeline_flow_in_order": True,
        "routing_depth_from_one_index": True,
        "context_builder_order_stands": True,
        "model_router_preserves_identity": True,
        "watchdog_guards_output": True,
        "persistence_not_history_dependent": True,
        "canonical_documents_anchor": True,
        "kernel_keeps_anchor_present": True,
        "memory_supplies_history_only": True,
        "history_cannot_rewrite_identity": True,
        "only_persona_defines_foundations": True,
    }
    assert audit["pipeline_stages"] == 10
    assert audit["index_sections"] == len(compiled["index"])
    assert audit["components"] == [
        "persona", "memory", "state", "context", "model"]
    assert audit["architecture"]["criterion_met"] is True
    assert audit["architecture"]["implemented"] == 6
    assert audit["architecture"]["equivalent"] == 7
    assert audit["most_important_rule"]["criterion_met"] is True
    assert audit["most_important_rule"]["implemented"] == 6
    assert audit["most_important_rule"]["equivalent"] == 1
    assert audit["audits_only"] is True
    assert audit["loads_or_compiles"] is False
    assert audit["runs_pipeline"] is False
    assert audit["calls_model"] is False
    assert audit["generates_output"] is False


def test_audit_tamper_surfaces_as_unmet_not_invented():
    mods = _load_modules()
    runtime = mods[1]
    try:
        compiled = _compile(runtime, mods[2])
        bad_kernel = dict(compiled)
        bad_kernel["kernel"] = dict(compiled["kernel"])
        bad_kernel["kernel"]["sha256"] = "f" * 64
        audit_kernel = runtime.architecture_rule_audit(
            bad_kernel)
    finally:
        mods[0].unload()
    assert audit_kernel["checks"][
        "compiler_outputs_stand_together"] is False
    assert audit_kernel["architecture"][
        "criterion_met"] is False
    assert audit_kernel["most_important_rule"][
        "criterion_met"] is True


def test_audit_with_supplied_drift_scores_still_guards():
    mods = _load_modules()
    runtime = mods[1]
    try:
        compiled = _compile(runtime, mods[2])
        audit = runtime.architecture_rule_audit(
            compiled, drift_scores={"boundaries": 0.25})
    finally:
        mods[0].unload()
    assert audit["checks"]["watchdog_guards_output"] is True
    assert audit["architecture"]["criterion_met"] is True
    assert audit["most_important_rule"]["criterion_met"] is True


def test_audit_refuses_malformed():
    mods = _load_modules()
    runtime = mods[1]
    try:
        _compile(runtime, mods[2])
        for bad in (None, "compiled", [], {}, {"persona_id": "x"}):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.architecture_rule_audit(bad)
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
        audit = runtime.architecture_rule_audit(compiled)
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
            other_audit = runtime.architecture_rule_audit(
                runtime.PersonaCompiler(_Ctx(ENABLED)).compile())
        finally:
            reset_hermes_home_override(token)
        third = runtime.PersonaRuntimeBridge(
            _Ctx(ENABLED)).packet_items("s1", "hello")
    finally:
        mods[0].unload()
    assert before == after
    assert audit["architecture"]["criterion_met"] is True
    assert audit["most_important_rule"]["criterion_met"] is True
    assert other_audit["persona_id"] == "other"
    assert other_audit["architecture"]["criterion_met"] is True
    assert other_audit["most_important_rule"][
        "criterion_met"] is True
    assert first[0].content == second[0].content == third[0].content
    assert len(first) == 1
    content = first[0].content
    assert "§§3-94" in content
    assert "§91 long-term architecture" in content
    assert "§92 the most" in content
    assert "architecture_rule_audit proves both" in content
    # The packet names the contracts only -- never canonical
    # persona text.
    assert "longhouse terminal" not in content
