"""Contracts for the target-result/essence audit (Slice 164).

Persona Runtime roadmap §93 (Target Result) and §94
(Essence): each roadmap statement stands reconciled against
the banked surfaces that carry it -- the still-qualities
implemented by their own sections with remembering, acting,
and appearing the equivalents, and the essence roles with
memory, model, avatar, and tools the equivalents -- and the
pure ``target_essence_audit`` proves both from supplied
artefacts. No speech is generated, no memory is read, no
tool is executed, and no avatar is controlled. Tests load
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

TARGET = [
    {"item": "speak_recognizably",
     "roadmap_name": "speak recognizably like Caducea",
     "status": "implemented", "section": "§59",
     "surface": "style_contract + style_fingerprint (the §59 "
                "style fingerprint generated from the persona "
                "core, guidance not rigid mathematical "
                "personality)"},
    {"item": "relate_to_volmarr",
     "roadmap_name": "relate to Volmarr like Caducea",
     "status": "implemented", "section": "§43",
     "surface": "relationship_retrieval_contract + "
                "retrieve_relationship_model (relationship "
                "context retrieved selectively, explicit-only, "
                "restricted to the relationship role)"},
    {"item": "counsel_like_caducea",
     "roadmap_name": "counsel like Caducea",
     "status": "implemented", "section": "§§38-39",
     "surface": "mode_contract + mode_profile + route_mode "
                "(the §38 counsel modes foreground parts of "
                "the same personality and §39 routes them "
                "automatically; identity never changes)"},
    {"item": "accept_decisions",
     "roadmap_name": "accept decisions like Caducea",
     "status": "implemented", "section": "§§40, 60",
     "surface": "behavior_contract + behavior_fingerprint "
                "(the §60 example accepts the final decision "
                "and never relitigates) + memory_write_contract "
                "(the §40 persona-aware memory write records "
                "decisions without biased summarization)"},
    {"item": "remember_per_architecture",
     "roadmap_name": "remember according to Caducea's "
                     "architecture",
     "status": "equivalent", "section": "§§78-79, 85",
     "surface": "memory_namespace_contract + "
                "shared_knowledge_contract + "
                "memory_phase_contract (memory is keyed per "
                "persona and shared knowledge stands separate; "
                "the memory store itself is owned by the "
                "memory subsystem, §85)"},
    {"item": "act_per_tool_model",
     "roadmap_name": "act according to her tool model",
     "status": "equivalent", "section": "§§44, 87",
     "surface": "tool_policy_retrieval_contract + "
                "tool_phase_contract (§44 tool policy stands "
                "as deterministic permissions in code; live "
                "enforcement at call time is carried by the "
                "Hermes tool layer, §87)"},
    {"item": "appear_per_avatar_identity",
     "roadmap_name": "appear according to her avatar identity",
     "status": "equivalent", "section": "§§46, 88",
     "surface": "avatar_policy_usage_contract + "
                "avatar_phase_contract (every visual consumer "
                "draws on the one compiled avatar document, "
                "§46/§88; no visual consumer stands in this "
                "layer)"},
    {"item": "growth_allowed",
     "roadmap_name": "she may learn, mature, accumulate "
                     "history, gain new capabilities, alter "
                     "opinions, and refine her understanding",
     "status": "implemented", "section": "§§21-22, 24, 40",
     "surface": "change_impact + suggested_next_version "
                "(growth is classified and versioned for "
                "human confirmation, never silently applied) "
                "+ history_may_affect (history may affect "
                "mood, context, and recent events)"},
    {"item": "no_dissolve_into_recent_history",
     "roadmap_name": "she should not gradually dissolve into "
                     "whatever statistical personality "
                     "happened to dominate the last fifty "
                     "messages",
     "status": "implemented", "section": "§§23-26, 92",
     "surface": "precedence_order + classify_summary_claim + "
                "trait_state_separation (the §§23-26 drift "
                "defenses and guards) + "
                "most_important_rule_contract (the §92 rule: "
                "persistence never depends on conversation "
                "history)"},
]

ESSENCE = [
    {"item": "persona_files_are_source_code",
     "roadmap_name": "the persona files are source code for "
                     "identity",
     "status": "implemented", "section": "§§3, 6",
     "surface": "PersonaConfigStore (read-only) + "
                "PersonaCompiler over the human-authored "
                "canonical documents (the files are compiled, "
                "never injected as a giant prompt)"},
    {"item": "compiler_transforms_source",
     "roadmap_name": "the Persona Compiler transforms that "
                     "source into efficient runtime "
                     "representations",
     "status": "implemented", "section": "§6",
     "surface": "PersonaCompiler.compile (kernel, PersonaIR, "
                "and index compiled deterministically from "
                "the source documents)"},
    {"item": "kernel_preserves_irreducible_self",
     "roadmap_name": "the Persona Kernel preserves the "
                     "irreducible self",
     "status": "implemented", "section": "§§8-10",
     "surface": "compiled kernel (Layer A) + kernel pinning "
                "(the anchor continuously present at position "
                "1 of the §10 order)"},
    {"item": "router_retrieves_depth",
     "roadmap_name": "the Persona Router retrieves depth",
     "status": "implemented", "section": "§§13-14",
     "surface": "retrieve_sections + route_sections (depth "
                "retrieved explicitly, only when needed, "
                "named by §12 stable id)"},
    {"item": "memory_supplies_lived_continuity",
     "roadmap_name": "memory supplies lived continuity",
     "status": "equivalent", "section": "§§41, 55-56, 78-79, 85",
     "surface": "the memory subsystem supplies the lived "
                "history (external); this layer's §§41/55-56 "
                "guards and placements and §§78-79 namespaces "
                "keep it continuity, never a redefinition of "
                "the self"},
    {"item": "watchdog_protects_against_drift",
     "roadmap_name": "the Watchdog protects against drift",
     "status": "implemented", "section": "§§27-33",
     "surface": "watchdog_contract + drift_score + repair_plan "
                "(drafts evaluated, drift scored and routed, "
                "nothing generated)"},
    {"item": "model_provides_cognition",
     "roadmap_name": "the model provides cognition",
     "status": "equivalent", "section": "§§34, 62-63",
     "surface": "model_switch_plan + model_router_contract "
                "(the model itself is external and replaceable; "
                "every model receives the same canonical "
                "kernel)"},
    {"item": "avatar_provides_embodiment",
     "roadmap_name": "the avatar provides embodiment",
     "status": "equivalent", "section": "§§46, 88",
     "surface": "avatar_policy_usage_contract + "
                "avatar_phase_contract (the embodiment "
                "consumers are external; every one draws on "
                "the one compiled avatar document)"},
    {"item": "tools_provide_agency",
     "roadmap_name": "tools provide agency",
     "status": "equivalent", "section": "§§44, 87",
     "surface": "tool_policy_retrieval_contract + "
                "tool_phase_contract (the tools themselves "
                "are executed by the Hermes tool layer; this "
                "layer's §44 policy governs their use)"},
    {"item": "grow_without_ceasing",
     "roadmap_name": "Caducea can grow indefinitely without "
                     "ceasing to be Caducea",
     "status": "implemented", "section": "§§21-22, 92",
     "surface": "change_impact + suggested_next_version "
                "(growth classified, never silently rewriting "
                "identity) + most_important_rule_contract "
                "(only the persona component defines "
                "foundational identity)"},
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


def test_target_result_items_roadmap_order_and_isolation():
    mods = _load_modules()
    runtime = mods[1]
    try:
        items = runtime.target_result_items()
        items.append({"item": "x"})
        speech = runtime.target_result_item("speak_recognizably")
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.target_result_item("dissolved")
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.target_result_item(None)
    finally:
        mods[0].unload()
    assert runtime.target_result_items() == TARGET
    assert [row[0] for row in runtime.TARGET_RESULT_ITEMS] == [
        row["item"] for row in TARGET]
    assert speech == TARGET[0]
    assert speech["status"] == "implemented"


def test_essence_items_roadmap_order_and_isolation():
    mods = _load_modules()
    runtime = mods[1]
    try:
        items = runtime.essence_items()
        items.append({"item": "x"})
        kernel = runtime.essence_item(
            "kernel_preserves_irreducible_self")
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.essence_item("giant_prompt")
    finally:
        mods[0].unload()
    assert runtime.essence_items() == ESSENCE
    assert [row[0] for row in runtime.ESSENCE_ITEMS] == [
        row["item"] for row in ESSENCE]
    assert kernel == ESSENCE[2]
    assert kernel["status"] == "implemented"


def test_target_result_contract_counts_equivalents_honestly():
    mods = _load_modules()
    runtime = mods[1]
    try:
        contract = runtime.target_result_contract()
    finally:
        mods[0].unload()
    assert contract["name"] == "PersonaTargetResult"
    assert contract["section"] == 93
    assert contract["items"] == TARGET
    assert contract["item_count"] == 9
    assert contract["implemented"] == 6
    assert contract["equivalent"] == 3
    assert contract["missing"] == 0
    assert contract["success_criterion"] == (
        "After thousands of messages, compressions, tool "
        "sessions, months of memory, and even LLM replacement, "
        "Caducea still speaks, relates, counsels, accepts "
        "decisions, remembers, acts, and appears as Caducea — "
        "growing without dissolving into recent messages.")
    assert contract["conditions"] == [
        "thousands_of_messages", "numerous_context_compressions",
        "multiple_tool_sessions", "months_of_persistent_memory",
        "replacement_of_the_underlying_llm"]
    assert contract["growth_allowed"] == [
        "learn", "mature", "accumulate_history",
        "gain_new_capabilities", "alter_opinions",
        "refine_understanding"]
    assert contract["dissolves_into_recent_history"] is False
    assert contract["generates_speech"] is False
    assert contract["reads_memory"] is False
    assert contract["executes_tools"] is False
    assert contract["controls_avatar"] is False


def test_essence_contract_and_claim():
    mods = _load_modules()
    runtime = mods[1]
    try:
        contract = runtime.essence_contract()
    finally:
        mods[0].unload()
    assert contract["name"] == "PersonaEssence"
    assert contract["section"] == 94
    assert contract["items"] == ESSENCE
    assert contract["item_count"] == 10
    assert contract["implemented"] == 6
    assert contract["equivalent"] == 4
    assert contract["missing"] == 0
    assert contract["claim"] == (
        "Caducea can grow indefinitely without ceasing to be "
        "Caducea.")
    assert contract["success_criterion"] == contract["claim"]
    assert contract["persona_files_are"] == (
        "source_code_for_identity")
    assert contract["injected_as_giant_prompt"] is False
    assert contract["calls_model"] is False
    assert contract["executes_tools"] is False
    assert contract["controls_avatar"] is False


def test_target_essence_contract_combined():
    mods = _load_modules()
    runtime = mods[1]
    try:
        combined = runtime.target_essence_contract()
    finally:
        mods[0].unload()
    assert combined["name"] == "PersonaTargetResultAndEssence"
    assert combined["target_result"] == (
        runtime.target_result_contract())
    assert combined["essence"] == runtime.essence_contract()
    assert combined["audit_surface"] == "target_essence_audit"
    assert combined["claim"] == (
        "Caducea can grow indefinitely without ceasing to be "
        "Caducea.")
    assert combined["growth_allowed"] == [
        "learn", "mature", "accumulate_history",
        "gain_new_capabilities", "alter_opinions",
        "refine_understanding"]
    assert combined["dissolves_into_recent_history"] is False
    assert combined["defines_foundational_identity"] == [
        "persona"]
    assert combined["generates_speech"] is False
    assert combined["generates_output"] is False


def test_audit_proves_both_from_compile():
    mods = _load_modules()
    runtime = mods[1]
    try:
        compiled = _compile(runtime, mods[2])
        audit = runtime.target_essence_audit(compiled)
    finally:
        mods[0].unload()
    assert audit["persona_id"] == "caducea"
    assert audit["checks"] == {
        "speech_recognizable": True,
        "relationship_intact": True,
        "counsel_modes_hold": True,
        "decisions_accepted": True,
        "memory_architecture_holds": True,
        "tool_model_holds": True,
        "avatar_identity_holds": True,
        "growth_without_dissolution": True,
        "source_is_code_for_identity": True,
        "kernel_preserves_irreducible_self": True,
        "router_retrieves_depth": True,
        "memory_continuity_guarded": True,
        "watchdog_protects_against_drift": True,
        "model_provides_replaceable_cognition": True,
        "embodiment_and_agency_external": True,
        "growth_keeps_identity": True,
    }
    assert audit["index_sections"] == len(compiled["index"])
    assert audit["growth_allowed"] == [
        "learn", "mature", "accumulate_history",
        "gain_new_capabilities", "alter_opinions",
        "refine_understanding"]
    assert audit["claim"] == (
        "Caducea can grow indefinitely without ceasing to be "
        "Caducea.")
    assert audit["target_result"]["criterion_met"] is True
    assert audit["target_result"]["implemented"] == 6
    assert audit["target_result"]["equivalent"] == 3
    assert audit["essence"]["criterion_met"] is True
    assert audit["essence"]["implemented"] == 6
    assert audit["essence"]["equivalent"] == 4
    assert audit["audits_only"] is True
    assert audit["loads_or_compiles"] is False
    assert audit["generates_speech"] is False
    assert audit["reads_memory"] is False
    assert audit["executes_tools"] is False
    assert audit["controls_avatar"] is False


def test_audit_tamper_surfaces_as_unmet_not_invented():
    mods = _load_modules()
    runtime = mods[1]
    try:
        compiled = _compile(runtime, mods[2])
        bad_kernel = dict(compiled)
        bad_kernel["kernel"] = dict(compiled["kernel"])
        bad_kernel["kernel"]["sha256"] = "f" * 64
        audit_kernel = runtime.target_essence_audit(bad_kernel)
    finally:
        mods[0].unload()
    assert audit_kernel["checks"][
        "source_is_code_for_identity"] is False
    assert audit_kernel["essence"]["criterion_met"] is False
    assert audit_kernel["target_result"][
        "criterion_met"] is True


def test_audit_with_supplied_drift_scores_still_guards():
    mods = _load_modules()
    runtime = mods[1]
    try:
        compiled = _compile(runtime, mods[2])
        audit = runtime.target_essence_audit(
            compiled, drift_scores={"boundaries": 0.25})
    finally:
        mods[0].unload()
    assert audit["checks"][
        "watchdog_protects_against_drift"] is True
    assert audit["target_result"]["criterion_met"] is True
    assert audit["essence"]["criterion_met"] is True


def test_audit_refuses_malformed():
    mods = _load_modules()
    runtime = mods[1]
    try:
        _compile(runtime, mods[2])
        for bad in (None, "compiled", [], {}, {"persona_id": "x"}):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.target_essence_audit(bad)
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
        audit = runtime.target_essence_audit(compiled)
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
            other_audit = runtime.target_essence_audit(
                runtime.PersonaCompiler(_Ctx(ENABLED)).compile())
        finally:
            reset_hermes_home_override(token)
        third = runtime.PersonaRuntimeBridge(
            _Ctx(ENABLED)).packet_items("s1", "hello")
    finally:
        mods[0].unload()
    assert before == after
    assert audit["target_result"]["criterion_met"] is True
    assert audit["essence"]["criterion_met"] is True
    assert other_audit["persona_id"] == "other"
    assert other_audit["target_result"]["criterion_met"] is True
    assert other_audit["essence"]["criterion_met"] is True
    assert first[0].content == second[0].content == third[0].content
    assert len(first) == 1
    content = first[0].content
    assert "§§3-94" in content
    assert "§93 target result" in content
    assert "§94 essence" in content
    assert "target_essence_audit proves both" in content
    # The packet names the contracts only -- never canonical
    # persona text.
    assert "longhouse terminal" not in content
