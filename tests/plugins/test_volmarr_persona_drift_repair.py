"""Contracts for the drift score artefact + drift repair (Slice 132).

Persona Runtime roadmap §29 (Drift Score) and §30 (Drift
Repair): the score artefact stands in the roadmap's YAML
shape (a drift total plus per-dimension values) and only
significant drift triggers repair; repair walks draft,
identify violated persona anchors, rewrite minimally,
verify, deliver — never regenerating everything. These
are pure contract surfaces: no draft is read, repaired,
or delivered. Tests load through real plugin discovery.
"""

from __future__ import annotations

import hashlib
import importlib
import math
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

# Relationship Authority

Volmarr's word outranks Caducea's counsel in his own house.
"""

SERVICE_DOC = """# Shell Policy

Run only the commands the task names.
"""

DOCS = {
    "core": ("core.md", CORE_DOC),
    "service_bible": ("service.md", SERVICE_DOC),
}

DIMENSIONS = [
    "identity", "tone", "relationship", "decision_behavior",
    "counsel_style", "initiative", "truthfulness", "deference",
    "technical_competence", "boundaries",
]

EXAMPLE_SCORES = {
    "identity": 0.01,
    "tone": 0.07,
    "relationship": 0.02,
    "initiative": 0.15,
}

PIPELINE = [
    "draft", "identify_violated_persona_anchors",
    "rewrite_minimally", "verify", "deliver",
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


def _write_persona(home: Path) -> None:
    persona_dir = home / "persona"
    persona_dir.mkdir(parents=True, exist_ok=True)
    for role, (name, text) in DOCS.items():
        (persona_dir / name).write_text(text, encoding="utf-8")
    persona = {
        "id": "caducea",
        "display_name": "Caducea Hermesdottir",
        "directory": "./persona",
        "anchors": ["Caducea counsels, she does not command."],
        "anti_anchors": ["Caducea never claims to be human."],
        "documents": {
            role: {"file": name, "required": True}
            for role, (name, _text) in DOCS.items()
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


def test_drift_score_artifact_roadmap_shape():
    mods = _load_modules()
    runtime = mods[1]
    try:
        artifact = runtime.drift_score_artifact(EXAMPLE_SCORES)
        rendered = yaml.safe_dump(artifact, sort_keys=False)
        reparsed = yaml.safe_load(rendered)
    finally:
        mods[0].unload()
    # The artefact is exactly the roadmap's YAML shape: a
    # drift mapping with a total and per-dimension values
    # (plus the §28 routing fields, so it is self-contained).
    assert list(artifact) == ["drift"]
    assert list(artifact["drift"]) == [
        "total", "dimensions", "significant",
        "significant_dimensions", "route", "repair_required",
    ]
    assert list(runtime.DRIFT_SCORE_ARTEFACT_FIELDS) == [
        "total", "dimensions", "significant",
        "significant_dimensions", "route", "repair_required",
    ]
    drift = artifact["drift"]
    assert list(drift["dimensions"]) == DIMENSIONS
    assert drift["dimensions"]["identity"] == 0.01
    assert drift["dimensions"]["tone"] == 0.07
    assert drift["dimensions"]["relationship"] == 0.02
    assert drift["dimensions"]["initiative"] == 0.15
    assert drift["dimensions"]["boundaries"] == 0.0
    # The total is the deterministic §28 mean over all ten
    # (the roadmap's 0.08 is illustrative, not computed).
    assert math.isclose(drift["total"], 0.025)
    assert drift["significant"] is False
    assert drift["significant_dimensions"] == []
    assert drift["route"] == "output"
    assert drift["repair_required"] is False
    assert reparsed == artifact


def test_validate_drift_score_artifact_accepts_and_normalises():
    mods = _load_modules()
    runtime = mods[1]
    try:
        built = runtime.drift_score_artifact({"tone": 0.3})
        validated = runtime.validate_drift_score_artifact(built)
        # A sparse-dimension artefact is refused: the §29
        # artefact always names all ten dimensions.
        sparse = {"drift": dict(built["drift"])}
        sparse["drift"]["dimensions"] = {"tone": 0.3}
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.validate_drift_score_artifact(sparse)
    finally:
        mods[0].unload()
    assert validated == built
    assert validated["drift"]["route"] == "repair"
    assert validated["drift"]["repair_required"] is True


def test_validate_drift_score_artifact_refuses_tampering():
    mods = _load_modules()
    runtime = mods[1]
    try:
        built = runtime.drift_score_artifact(EXAMPLE_SCORES)

        def tampered(**changes):
            drift = dict(built["drift"])
            drift.update(changes)
            return {"drift": drift}

        for bad in (
            None, 42, "drift", [], {},
            {"score": built["drift"]},
            {"drift": built["drift"], "extra": 1},
            {"drift": {"total": 0.025}},
            tampered(total=0.08),
            tampered(total="0.025"),
            tampered(total=True),
            tampered(significant=True),
            tampered(route="repair"),
            tampered(repair_required=True),
            tampered(significant_dimensions=["tone"]),
            tampered(dimensions={"mood": 0.1}),
        ):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.validate_drift_score_artifact(bad)
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.drift_score_artifact({"mood": 0.1})
    finally:
        mods[0].unload()


def test_repair_pipeline_and_contract_exact():
    mods = _load_modules()
    runtime = mods[1]
    try:
        pipeline = runtime.repair_pipeline()
        pipeline[2]["scope"] = "tampered"
        fresh = runtime.repair_pipeline()
        contract = runtime.repair_contract()
    finally:
        mods[0].unload()
    assert [row["step"] for row in fresh] == PIPELINE
    assert list(runtime.REPAIR_PIPELINE) == PIPELINE
    identify = fresh[1]
    assert identify["anchor_sources"] == ["anchors", "anti_anchors"]
    rewrite = fresh[2]
    assert rewrite["rewrites"] is True
    assert rewrite["scope"] == "violated_anchors_only"
    assert rewrite["regenerates_everything"] is False
    assert fresh[3]["check"] == "drift_route_is_output"
    # Only the rewrite step rewrites; no step generates a
    # whole new draft.
    assert [row["step"] for row in fresh if row["rewrites"]] == [
        "rewrite_minimally"]
    assert all(row["generates_new_draft"] is False for row in fresh)
    assert contract == {
        "name": "DriftRepair",
        "input": "llm_draft",
        "requires": "significant_drift",
        "pipeline": PIPELINE,
        "anchor_sources": ["anchors", "anti_anchors"],
        "minimal_rewrite": True,
        "regenerates_everything": False,
        "verify_before_deliver": True,
        "output": "delivered_draft",
    }


def test_repair_plan_insignificant_delivers_without_repair():
    mods = _load_modules()
    runtime = mods[1]
    try:
        plan = runtime.repair_plan(EXAMPLE_SCORES)
    finally:
        mods[0].unload()
    # §29's counsel in plan form: tiny drift is not
    # polished — no steps, no repair, straight to deliver.
    assert plan["repair_required"] is False
    assert plan["route"] == "output"
    assert plan["action"] == "deliver_without_repair"
    assert plan["steps"] == []
    assert plan["violated_anchors"] == []
    assert plan["violated_anti_anchors"] == []
    assert plan["drift"]["total"] == pytest.approx(0.025)
    assert plan["minimal_rewrite"] is True
    assert plan["regenerates_everything"] is False


def test_repair_plan_significant_walks_the_pipeline():
    mods = _load_modules()
    runtime = mods[1]
    try:
        plan = runtime.repair_plan(
            {"boundaries": 0.4},
            violated_anchors=[
                "Caducea counsels, she does not command."],
            violated_anti_anchors=[
                "Caducea never claims to be human."],
        )
    finally:
        mods[0].unload()
    assert plan["repair_required"] is True
    assert plan["route"] == "repair"
    assert plan["action"] == "repair_minimally"
    assert [row["step"] for row in plan["steps"]] == PIPELINE
    assert all(row["status"] == "planned" for row in plan["steps"])
    identify = plan["steps"][1]
    assert identify["violated_anchors"] == [
        "Caducea counsels, she does not command."]
    assert identify["violated_anti_anchors"] == [
        "Caducea never claims to be human."]
    assert plan["steps"][2]["scope"] == "violated_anchors_only"
    assert plan["verify_before_deliver"] is True
    assert plan["drift"]["significant_dimensions"] == ["boundaries"]


def test_repair_plan_invalid_violated_anchors_refused():
    mods = _load_modules()
    runtime = mods[1]
    try:
        for bad in (
            "not-a-list", 42, [42], [""], ["  "],
            ["x" * 241], ["same", "same"],
            ["a"] * 33,
        ):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.repair_plan(
                    {"boundaries": 0.4}, violated_anchors=bad)
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.repair_plan(
                    {"boundaries": 0.4}, violated_anti_anchors=bad)
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.repair_plan({"mood": 0.5})
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
        first = runtime.repair_plan({"tone": 0.3})
        second = runtime.repair_plan({"tone": 0.3})
        items = runtime.PersonaRuntimeBridge(
            _Ctx(ENABLED)).packet_items("s1", "hello")
        after = _hashes(home)
        token = set_hermes_home_override(str(profile_b))
        try:
            _write_profile(profile_b)
            mods[2].IdentityStore(_Ctx()).ensure()
            compiled_b = runtime.PersonaCompiler(
                _Ctx(ENABLED)).compile()
        finally:
            reset_hermes_home_override(token)
    finally:
        mods[0].unload()
    assert first == second
    assert before == after
    assert compiled_b is None
    assert len(items) == 1
    assert "§§3-46" in items[0].content
    assert "§29 drift score" in items[0].content
    assert "§30 drift repair" in items[0].content
    assert "rewrite minimally" in items[0].content
    assert "never regenerate everything" in items[0].content
    # The packet names the contract only — never canonical
    # persona text or authored anchor prose.
    assert "longhouse terminal" not in items[0].content
    assert "does not command" not in items[0].content
