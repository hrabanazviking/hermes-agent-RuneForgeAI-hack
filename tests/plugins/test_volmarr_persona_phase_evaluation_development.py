"""Contracts for the phase evaluation/development audit (Slice 162).

Persona Runtime roadmap §89 (Phase 9 — Evaluation Framework)
and §90 (Phase 10 — Persona Development System): each phase's
roadmap items stand reconciled against the banked surfaces
that carry them — every §89 item implemented by its own
sections, and §90's diff and recompile implemented with the
remaining four flow steps equivalents, carried measurably,
as a diff record, by the human gate, or by human edit — and
the pure ``evaluation_development_audit`` proves both
phases' success criteria from supplied artefacts. No
evaluation is run, no patch is proposed, and no canonical
file is updated. Tests load through real plugin discovery.
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

EVALUATION = [
    {"item": "golden_scenarios", "roadmap_name": "golden scenarios",
     "status": "implemented", "section": "§58",
     "surface": "golden_record + golden_example + "
                "validate_golden_record"},
    {"item": "long_context_tests",
     "roadmap_name": "long-context tests",
     "status": "implemented", "section": "§§57, 32-33, 55",
     "surface": "drift_test_scenario "
                "thousand_turn_conversation + refresh plans + "
                "compression_plan"},
    {"item": "model_switch_tests",
     "roadmap_name": "model-switch tests",
     "status": "implemented", "section": "§§57, 34-35",
     "surface": "drift_test_scenario "
                "model_switch_local_to_cloud + model_switch_plan "
                "+ handoff_packet"},
    {"item": "memory_drift_tests",
     "roadmap_name": "memory drift tests",
     "status": "implemented", "section": "§§40-41, 25-26",
     "surface": "memory_write_contract + "
                "memory_override_contract + evaluate_memory_claim "
                "(memory never redefines traits)"},
    {"item": "relationship_consistency_tests",
     "roadmap_name": "relationship consistency tests",
     "status": "implemented", "section": "§§43, 55, 57",
     "surface": "retrieve_relationship_model + the "
                "conversation_compression drift scenario "
                "(relationship behavior remains stable)"},
    {"item": "persona_regression_tests",
     "roadmap_name": "persona regression tests",
     "status": "implemented", "section": "§§57-63, 19, 28-29",
     "surface": "drift_test_scenarios + style/behavior "
                "fingerprints + drift_score_artifact + telemetry "
                "averages + the §19 hash record baseline"},
]

DEVELOPMENT = [
    {"item": "notices_recurring_pattern",
     "roadmap_name": "notices recurring pattern",
     "status": "equivalent", "section": "§§57, 61",
     "surface": "drift_test_scenarios + drift telemetry records "
                "name recurring drift measurably (no "
                "pattern-noticing proposer stands in this layer)"},
    {"item": "proposed_persona_patch",
     "roadmap_name": "creates proposed persona patch",
     "status": "equivalent", "section": "§§21, 74",
     "surface": "change_impact + persona_diff over two compiles "
                "(the patch stands as a diff record; no patch "
                "proposer stands in this layer)"},
    {"item": "human_readable_diff",
     "roadmap_name": "human-readable diff",
     "status": "implemented", "section": "§74",
     "surface": "persona_diff + render_persona_diff"},
    {"item": "human_review_and_approval",
     "roadmap_name": "Volmarr reviews / approved",
     "status": "equivalent", "section": "§§22, 76",
     "surface": "change_impact suggested version (a suggestion "
                "only, confirmed by a human config edit) + "
                "persona_import_plan explicit handling (no "
                "approval workflow is owned)"},
    {"item": "canonical_markdown_updated",
     "roadmap_name": "canonical Markdown updated",
     "status": "equivalent", "section": "§§3, 6",
     "surface": "human edit of the human-authored documents "
                "(the runtime reads the config and documents, "
                "it never writes them)"},
    {"item": "persona_recompiles",
     "roadmap_name": "persona recompiles",
     "status": "implemented", "section": "§§73, 20",
     "surface": "persona_reload (forced recompile) + reload_plan"},
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


def test_evaluation_phase_items_roadmap_order_and_isolation():
    mods = _load_modules()
    runtime = mods[1]
    try:
        items = runtime.evaluation_phase_items()
        items.append({"item": "x"})
        golden = runtime.evaluation_phase_item("golden_scenarios")
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.evaluation_phase_item("live_evaluator")
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.evaluation_phase_item(None)
    finally:
        mods[0].unload()
    assert runtime.evaluation_phase_items() == EVALUATION
    assert [row[0] for row in runtime.EVALUATION_PHASE_ITEMS] == [
        row["item"] for row in EVALUATION]
    assert golden == EVALUATION[0]
    assert golden["status"] == "implemented"


def test_development_phase_items_roadmap_order_and_isolation():
    mods = _load_modules()
    runtime = mods[1]
    try:
        items = runtime.development_phase_items()
        items.append({"item": "x"})
        diff = runtime.development_phase_item("human_readable_diff")
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.development_phase_item("auto_apply")
    finally:
        mods[0].unload()
    assert runtime.development_phase_items() == DEVELOPMENT
    assert [row[0] for row in runtime.DEVELOPMENT_PHASE_ITEMS] == [
        row["item"] for row in DEVELOPMENT]
    assert diff == DEVELOPMENT[2]
    assert diff["status"] == "implemented"


def test_evaluation_phase_contract():
    mods = _load_modules()
    runtime = mods[1]
    try:
        contract = runtime.evaluation_phase_contract()
    finally:
        mods[0].unload()
    assert contract["name"] == "PersonaPhase9EvaluationFramework"
    assert contract["phase"] == 9
    assert contract["items"] == EVALUATION
    assert contract["item_count"] == 6
    assert contract["implemented"] == 6
    assert contract["equivalent"] == 0
    assert contract["missing"] == 0
    assert contract["success_criterion"] == (
        "Character stability becomes measurable rather than "
        "subjective.")
    assert contract["stability_measurable"] is True
    assert contract["runs_evaluations"] is False
    assert contract["evaluates_live_responses"] is False


def test_development_phase_contract_counts_equivalents_honestly():
    mods = _load_modules()
    runtime = mods[1]
    try:
        contract = runtime.development_phase_contract()
    finally:
        mods[0].unload()
    assert contract["name"] == "PersonaPhase10DevelopmentSystem"
    assert contract["phase"] == 10
    assert contract["items"] == DEVELOPMENT
    assert contract["item_count"] == 6
    assert contract["implemented"] == 2
    assert contract["equivalent"] == 4
    assert contract["missing"] == 0
    assert contract["success_criterion"] == (
        "Persona improvements are proposed as a human-readable "
        "diff for Volmarr's review and approval, and foundational "
        "identity is never silently rewritten.")
    assert contract["human_approval_required"] is True
    assert contract["proposes_patches"] is False
    assert contract["updates_canonical_files"] is False
    assert contract["silently_rewrites_identity"] is False


def test_evaluation_development_contract_combined():
    mods = _load_modules()
    runtime = mods[1]
    try:
        combined = runtime.evaluation_development_contract()
    finally:
        mods[0].unload()
    assert combined["name"] == "PersonaPhases9And10"
    assert combined["evaluation_phase"] == (
        runtime.evaluation_phase_contract())
    assert combined["development_phase"] == (
        runtime.development_phase_contract())
    assert combined["audit_surface"] == (
        "evaluation_development_audit")
    assert combined["stability_measurable"] is True
    assert combined["runs_evaluations"] is False
    assert combined["human_approval_required"] is True
    assert combined["proposes_patches"] is False
    assert combined["updates_canonical_files"] is False
    assert combined["silently_rewrites_identity"] is False


def test_audit_proves_criteria_from_compile():
    mods = _load_modules()
    runtime = mods[1]
    try:
        compiled = _compile(runtime, mods[2])
        audit = runtime.evaluation_development_audit(compiled)
    finally:
        mods[0].unload()
    assert audit["persona_id"] == "caducea"
    assert audit["checks"] == {
        "golden_scenarios_valid": True,
        "drift_scenarios_complete": True,
        "long_context_measurable": True,
        "model_switch_measurable": True,
        "memory_drift_guarded": True,
        "relationship_consistency_selective": True,
        "fingerprints_measurable": True,
        "telemetry_adherence_measurable": True,
        "regression_baseline_holds": True,
        "impact_classified": True,
        "diff_human_readable": True,
        "human_gate_holds": True,
        "identity_never_silently_rewritten": True,
        "recompile_forced": True,
    }
    assert audit["drift_scenarios"] == 8
    assert audit["relationship_sections"] >= 1
    assert audit["impact_class"] == "none"
    assert audit["diff_changed"] is False
    assert audit["evaluation_phase"]["criterion_met"] is True
    assert audit["evaluation_phase"]["implemented"] == 6
    assert audit["development_phase"]["criterion_met"] is True
    assert audit["development_phase"]["implemented"] == 2
    assert audit["development_phase"]["equivalent"] == 4
    assert audit["audits_only"] is True
    assert audit["loads_or_compiles"] is False
    assert audit["runs_evaluations"] is False
    assert audit["proposes_patches"] is False
    assert audit["updates_canonical_files"] is False


def test_audit_with_previous_compile_shows_readable_diff():
    mods = _load_modules()
    runtime = mods[1]
    try:
        previous = _compile(runtime, mods[2],
                            core_doc=OTHER_CORE_DOC)
        compiled = _compile(runtime, mods[2])
        audit = runtime.evaluation_development_audit(
            compiled, previous=previous)
    finally:
        mods[0].unload()
    assert audit["diff_changed"] is True
    assert audit["impact_class"] != "none"
    assert audit["checks"]["diff_human_readable"] is True
    assert audit["checks"]["impact_classified"] is True
    assert audit["development_phase"]["criterion_met"] is True
    assert audit["evaluation_phase"]["criterion_met"] is True


def test_audit_tamper_surfaces_as_unmet_not_invented():
    mods = _load_modules()
    runtime = mods[1]
    try:
        compiled = _compile(runtime, mods[2])
        bad_kernel = dict(compiled)
        bad_kernel["kernel"] = dict(compiled["kernel"])
        bad_kernel["kernel"]["sha256"] = "f" * 64
        audit_kernel = runtime.evaluation_development_audit(
            bad_kernel)
    finally:
        mods[0].unload()
    assert audit_kernel["checks"][
        "regression_baseline_holds"] is False
    assert audit_kernel["evaluation_phase"][
        "criterion_met"] is False
    assert audit_kernel["development_phase"][
        "criterion_met"] is True


def test_audit_refuses_malformed():
    mods = _load_modules()
    runtime = mods[1]
    try:
        _compile(runtime, mods[2])
        for bad in (None, "compiled", [], {}, {"persona_id": "x"}):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.evaluation_development_audit(bad)
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
        audit = runtime.evaluation_development_audit(compiled)
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
            other_audit = runtime.evaluation_development_audit(
                runtime.PersonaCompiler(_Ctx(ENABLED)).compile())
        finally:
            reset_hermes_home_override(token)
        third = runtime.PersonaRuntimeBridge(
            _Ctx(ENABLED)).packet_items("s1", "hello")
    finally:
        mods[0].unload()
    assert before == after
    assert audit["evaluation_phase"]["criterion_met"] is True
    assert audit["development_phase"]["criterion_met"] is True
    assert other_audit["persona_id"] == "other"
    assert other_audit["evaluation_phase"]["criterion_met"] is True
    assert other_audit["development_phase"]["criterion_met"] is True
    assert first[0].content == second[0].content == third[0].content
    assert len(first) == 1
    content = first[0].content
    assert "§§3-94" in content
    assert "§89 Phase 9 evaluation" in content
    assert "§90 Phase 10 persona development" in content
    assert "evaluation_development_audit proves both" in content
    # The packet names the contracts only — never canonical
    # persona text.
    assert "longhouse terminal" not in content
