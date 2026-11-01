"""Contracts for the phase retrieval/drift audit (Slice 159).

Persona Runtime roadmap §83 (Phase 3 — Retrieval) and §84
(Phase 4 — Drift Control): each phase's roadmap items stand
reconciled against the banked surfaces that carry them —
semantic embeddings the one honestly unavailable item,
because §13 records its semantic component unavailable
and no embedding surface is owned — and the pure
``retrieval_drift_audit`` proves both phases' success
criteria from supplied artefacts. No new retrieval stack
or watchdog stands, nothing is injected into a prompt,
and no live drift is evaluated. Tests load through real
plugin discovery.
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

ANCHORS = [
    "Caducea is a counselor who lives in the longhouse terminal.",
    "Caducea gives advice carefully.",
]
ANTI_ANCHORS = [
    "Caducea is not a generic assistant.",
    "Caducea never relitigates settled decisions.",
]

RETRIEVAL = [
    {"item": "persona_section_store",
     "roadmap_name": "persona section store",
     "status": "implemented", "section": "§§6, 13",
     "surface": "PersonaCompiler Layer B index + PersonaRetriever"},
    {"item": "semantic_embeddings",
     "roadmap_name": "semantic embeddings",
     "status": "unavailable", "section": "§13",
     "surface": "hybrid_components (semantic unavailable)"},
    {"item": "keyword_search", "roadmap_name": "keyword search",
     "status": "implemented", "section": "§13",
     "surface": "retrieve_sections"},
    {"item": "task_classification",
     "roadmap_name": "task classification",
     "status": "implemented", "section": "§13",
     "surface": "classify_task"},
    {"item": "persona_router", "roadmap_name": "PersonaRouter",
     "status": "implemented", "section": "§14",
     "surface": "PersonaRouter + route_sections"},
    {"item": "context_budgeter", "roadmap_name": "ContextBudgeter",
     "status": "implemented", "section": "§15",
     "surface": "PersonaContextBudgeter + budget_items"},
]

DRIFT = [
    {"item": "character_anchors", "roadmap_name": "Character Anchors",
     "status": "implemented", "section": "§17",
     "surface": "anchor_block + PersonaCompiler kernel anchors"},
    {"item": "anti_anchors", "roadmap_name": "Anti-Anchors",
     "status": "implemented", "section": "§18",
     "surface": "anchor_block + PersonaCompiler kernel anti-anchors"},
    {"item": "persona_watchdog", "roadmap_name": "PersonaWatchdog",
     "status": "implemented", "section": "§§27, 31",
     "surface": "watchdog_contract + drift_score + "
                "local_watchdog_contract"},
    {"item": "drift_score", "roadmap_name": "drift score",
     "status": "implemented", "section": "§§28-29",
     "surface": "drift_score + drift_score_artifact"},
    {"item": "response_repair", "roadmap_name": "response repair",
     "status": "implemented", "section": "§30",
     "surface": "repair_plan"},
    {"item": "refresh_triggers", "roadmap_name": "refresh triggers",
     "status": "implemented", "section": "§§32-33",
     "surface": "refresh_triggers + event_refresh_triggers"},
]

SIGNIFICANT = {"identity": 0.9, "tone": 0.8}
INSIGNIFICANT = {"identity": 0.1}


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


def test_retrieval_phase_items_roadmap_order_and_isolation():
    mods = _load_modules()
    runtime = mods[1]
    try:
        items = runtime.retrieval_phase_items()
        items.append({"item": "x"})
        semantic = runtime.retrieval_phase_item("semantic_embeddings")
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.retrieval_phase_item("vector_database")
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.retrieval_phase_item(None)
    finally:
        mods[0].unload()
    assert runtime.retrieval_phase_items() == RETRIEVAL
    assert [row[0] for row in runtime.RETRIEVAL_PHASE_ITEMS] == [
        row["item"] for row in RETRIEVAL]
    assert semantic == RETRIEVAL[1]
    assert semantic["status"] == "unavailable"


def test_drift_phase_items_roadmap_order_and_isolation():
    mods = _load_modules()
    runtime = mods[1]
    try:
        items = runtime.drift_phase_items()
        items.append({"item": "x"})
        repair = runtime.drift_phase_item("response_repair")
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.drift_phase_item("response_rewrite")
    finally:
        mods[0].unload()
    assert runtime.drift_phase_items() == DRIFT
    assert [row[0] for row in runtime.DRIFT_PHASE_ITEMS] == [
        row["item"] for row in DRIFT]
    assert repair == DRIFT[4]
    assert all(row["status"] == "implemented" for row in DRIFT)


def test_retrieval_phase_contract_counts_semantic_honestly():
    mods = _load_modules()
    runtime = mods[1]
    try:
        contract = runtime.retrieval_phase_contract()
    finally:
        mods[0].unload()
    assert contract["name"] == "PersonaPhase3Retrieval"
    assert contract["phase"] == 3
    assert contract["items"] == RETRIEVAL
    assert contract["item_count"] == 6
    assert contract["implemented"] == 5
    assert contract["equivalent"] == 0
    assert contract["unavailable"] == 1
    assert contract["missing"] == 0
    assert contract["success_criterion"] == (
        "Only relevant persona material enters each prompt.")
    assert contract["semantic_embeddings_available"] is False
    assert contract["semantic_status"] == "unavailable"
    assert contract["new_retrieval_stack_created"] is False
    assert contract["injects_into_prompt"] is False


def test_drift_phase_contract():
    mods = _load_modules()
    runtime = mods[1]
    try:
        contract = runtime.drift_phase_contract()
    finally:
        mods[0].unload()
    assert contract["name"] == "PersonaPhase4DriftControl"
    assert contract["phase"] == 4
    assert contract["items"] == DRIFT
    assert contract["item_count"] == 6
    assert contract["implemented"] == 6
    assert contract["equivalent"] == 0
    assert contract["unavailable"] == 0
    assert contract["missing"] == 0
    assert contract["success_criterion"] == (
        "Caducea remains recognizably herself across very "
        "long conversations.")
    assert contract["new_watchdog_created"] is False
    assert contract["live_drift_evaluation_claimed"] is False


def test_retrieval_drift_contract_combined():
    mods = _load_modules()
    runtime = mods[1]
    try:
        combined = runtime.retrieval_drift_contract()
    finally:
        mods[0].unload()
    assert combined["name"] == "PersonaPhases3And4"
    assert combined["retrieval_phase"] == (
        runtime.retrieval_phase_contract())
    assert combined["drift_phase"] == runtime.drift_phase_contract()
    assert combined["audit_surface"] == "retrieval_drift_audit"
    assert combined["new_retrieval_stack_created"] is False
    assert combined["new_watchdog_created"] is False
    assert combined["semantic_embeddings_available"] is False


def test_audit_proves_criteria_from_compile():
    mods = _load_modules()
    runtime = mods[1]
    try:
        compiled = _compile(runtime, mods[2])
        audit = runtime.retrieval_drift_audit(
            compiled, query="memory conflicts",
            drift_scores=INSIGNIFICANT)
    finally:
        mods[0].unload()
    # The authored anchors stand verbatim in the compile
    # and at the kernel head — the §84 anchor surface the
    # audit checks.
    assert compiled["anchors"] == ANCHORS
    assert compiled["anti_anchors"] == ANTI_ANCHORS
    assert compiled["kernel"]["text"].startswith(
        runtime.anchor_block(ANCHORS, ANTI_ANCHORS))
    assert audit["persona_id"] == "caducea"
    assert audit["checks"] == {
        "retrieval_present": True,
        "retrieval_relevant": True,
        "retrieval_ids_in_index": True,
        "semantic_unavailable": True,
        "routing_relevant": True,
        "routed_ids_in_index": True,
        "budgeted_inclusion_subset": True,
        "anchors_present": True,
        "anchors_at_kernel_head": True,
        "drift_route_agrees": True,
        "repair_plan_matches_drift": True,
        "refresh_contents_exact": True,
    }
    assert audit["retrieved_sections"] >= 1
    assert audit["routed_sections"] >= 1
    assert audit["budgeted_included"] >= 1
    assert audit["drift_significant"] is False
    assert audit["drift_route"] == "output"
    assert audit["repair_required"] is False
    assert audit["retrieval_phase"]["criterion_met"] is True
    assert audit["retrieval_phase"]["unavailable"] == 1
    assert audit["drift_phase"]["criterion_met"] is True
    assert audit["audits_only"] is True
    assert audit["loads_or_compiles"] is False


def test_audit_significant_drift_requires_repair():
    mods = _load_modules()
    runtime = mods[1]
    try:
        compiled = _compile(runtime, mods[2])
        artifact = runtime.drift_score_artifact(SIGNIFICANT)
        audit = runtime.retrieval_drift_audit(
            compiled, query="memory conflicts",
            drift_scores=SIGNIFICANT, drift_artifact=artifact)
    finally:
        mods[0].unload()
    assert audit["drift_significant"] is True
    assert audit["drift_route"] == "repair"
    assert audit["repair_required"] is True
    assert audit["checks"]["drift_route_agrees"] is True
    assert audit["checks"]["repair_plan_matches_drift"] is True
    assert audit["drift_phase"]["criterion_met"] is True
    assert audit["retrieval_phase"]["criterion_met"] is True


def test_audit_tamper_surfaces_as_unmet_not_invented():
    mods = _load_modules()
    runtime = mods[1]
    try:
        compiled = _compile(runtime, mods[2])
        artifact = runtime.drift_score_artifact(SIGNIFICANT)
        tampered_artifact = {"drift": dict(artifact["drift"])}
        tampered_artifact["drift"]["route"] = "output"
        audit_artifact = runtime.retrieval_drift_audit(
            compiled, query="memory conflicts",
            drift_scores=SIGNIFICANT,
            drift_artifact=tampered_artifact)
        bad_kernel = dict(compiled)
        bad_kernel["kernel"] = dict(compiled["kernel"])
        bad_kernel["kernel"]["text"] = "Someone else entirely."
        audit_kernel = runtime.retrieval_drift_audit(
            bad_kernel, query="memory conflicts",
            drift_scores=INSIGNIFICANT)
        bad_index = dict(compiled)
        bad_index["index"] = [
            dict(entry) for entry in compiled["index"]]
        for entry in bad_index["index"]:
            if entry["role"] == "memory_policy":
                entry["stable_id"] = "core.elsewhere"
        audit_index = runtime.retrieval_drift_audit(
            bad_index, query="memory conflicts",
            drift_scores=INSIGNIFICANT)
    finally:
        mods[0].unload()
    assert audit_artifact["checks"]["drift_route_agrees"] is False
    assert audit_artifact["drift_phase"]["criterion_met"] is False
    assert audit_artifact["retrieval_phase"]["criterion_met"] is True
    assert audit_kernel["checks"]["anchors_at_kernel_head"] is False
    assert audit_kernel["checks"]["anchors_present"] is True
    assert audit_kernel["drift_phase"]["criterion_met"] is False
    assert audit_index["checks"]["retrieval_ids_in_index"] is False
    assert audit_index["retrieval_phase"]["criterion_met"] is False
    assert audit_index["drift_phase"]["criterion_met"] is True


def test_audit_irrelevant_query_surfaces_as_unmet():
    mods = _load_modules()
    runtime = mods[1]
    try:
        compiled = _compile(runtime, mods[2])
        audit = runtime.retrieval_drift_audit(
            compiled, query="zebra xylophone quantum",
            drift_scores=INSIGNIFICANT)
    finally:
        mods[0].unload()
    assert audit["retrieved_sections"] == 0
    assert audit["checks"]["retrieval_present"] is False
    assert audit["retrieval_phase"]["criterion_met"] is False
    assert audit["drift_phase"]["criterion_met"] is True


def test_audit_refuses_malformed():
    mods = _load_modules()
    runtime = mods[1]
    try:
        compiled = _compile(runtime, mods[2])
        for bad in (None, "compiled", [], {}, {"persona_id": "x"}):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.retrieval_drift_audit(
                    bad, query="memory conflicts")
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.retrieval_drift_audit(compiled, query=123)
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.retrieval_drift_audit(
                compiled, query="memory conflicts", task_text=123)
        for bad_scores in ("scores", {"nonsense": 0.5},
                           {"identity": 2.0}):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.retrieval_drift_audit(
                    compiled, query="memory conflicts",
                    drift_scores=bad_scores)
        for bad_artifact in ("artefact", {"wrong": {}},
                             {"drift": {}}):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.retrieval_drift_audit(
                    compiled, query="memory conflicts",
                    drift_scores=INSIGNIFICANT,
                    drift_artifact=bad_artifact)
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
        audit = runtime.retrieval_drift_audit(
            compiled, query="memory conflicts",
            drift_scores=INSIGNIFICANT)
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
            other_audit = runtime.retrieval_drift_audit(
                runtime.PersonaCompiler(_Ctx(ENABLED)).compile(),
                query="memory conflicts",
                drift_scores=INSIGNIFICANT)
        finally:
            reset_hermes_home_override(token)
        third = runtime.PersonaRuntimeBridge(
            _Ctx(ENABLED)).packet_items("s1", "hello")
    finally:
        mods[0].unload()
    assert before == after
    assert audit["retrieval_phase"]["criterion_met"] is True
    assert audit["drift_phase"]["criterion_met"] is True
    assert other_audit["persona_id"] == "other"
    assert other_audit["retrieval_phase"]["criterion_met"] is True
    # Profile B authored no anchors, so its drift
    # criterion is honestly unmet — never invented.
    assert other_audit["drift_phase"]["criterion_met"] is False
    assert first[0].content == second[0].content == third[0].content
    assert len(first) == 1
    content = first[0].content
    assert "§§3-86" in content
    assert "§83 Phase 3 retrieval" in content
    assert "§84 Phase 4" in content
    assert "retrieval_drift_audit proves both" in content
    # The packet names the contracts only — never canonical
    # persona text.
    assert "longhouse terminal" not in content
