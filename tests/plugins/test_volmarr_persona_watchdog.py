"""Contracts for the persona watchdog + drift dimensions (Slice 131).

Persona Runtime roadmap §27 (Persona Watchdog) and §28
(Drift Dimensions): the watchdog does not generate
responses, it evaluates drafts — LLM draft, watchdog,
drift score, then a route (acceptable to output, drift
to repair) — and drift is evaluated against the ten
§28 dimensions. These are pure contract surfaces: no
draft is read, scored from prose, or repaired. Tests
load through real plugin discovery.
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


def test_drift_dimensions_exact_roadmap_order():
    mods = _load_modules()
    runtime = mods[1]
    try:
        dimensions = runtime.drift_dimensions()
        dimensions.append("tampered")
        fresh = runtime.drift_dimensions()
    finally:
        mods[0].unload()
    assert fresh == DIMENSIONS
    assert list(runtime.DRIFT_DIMENSIONS) == DIMENSIONS


def test_watchdog_pipeline_evaluates_never_generates():
    mods = _load_modules()
    runtime = mods[1]
    try:
        pipeline = runtime.watchdog_pipeline()
        pipeline[1]["kind"] = "tampered"
        fresh = runtime.watchdog_pipeline()
        contract = runtime.watchdog_contract()
    finally:
        mods[0].unload()
    assert [row["step"] for row in fresh] == [
        "llm_draft", "persona_watchdog", "drift_score", "route",
    ]
    assert list(runtime.WATCHDOG_PIPELINE) == [
        row["step"] for row in fresh]
    # Only the draft step generates; the watchdog itself
    # evaluates drafts and generates nothing.
    assert fresh[0]["generates_responses"] is True
    assert fresh[0]["evaluates_drafts"] is False
    assert fresh[1]["generates_responses"] is False
    assert fresh[1]["evaluates_drafts"] is True
    assert fresh[3]["routes"] == {
        "acceptable": "output", "drift": "repair"}
    assert list(runtime.WATCHDOG_ROUTES) == ["output", "repair"]
    assert contract == {
        "name": "PersonaWatchdog",
        "generates_responses": False,
        "evaluates_drafts": True,
        "input": "llm_draft",
        "output": "drift_score",
        "pipeline": [
            "llm_draft", "persona_watchdog", "drift_score", "route",
        ],
        "dimensions": DIMENSIONS,
        "routes": ["output", "repair"],
        "total_threshold": 0.20,
        "dimension_threshold": 0.25,
    }
    assert runtime.DRIFT_TOTAL_THRESHOLD == 0.20
    assert runtime.DRIFT_DIMENSION_THRESHOLD == 0.25


def test_drift_score_roadmap_example_is_acceptable():
    mods = _load_modules()
    runtime = mods[1]
    try:
        # The §29 conceptual example's named dimensions,
        # read as a §§27-28 score record: small drift,
        # nothing significant, routed to output.
        record = runtime.drift_score({
            "identity": 0.01,
            "tone": 0.07,
            "relationship": 0.02,
            "initiative": 0.15,
        })
        route = runtime.drift_route({
            "identity": 0.01, "tone": 0.07,
            "relationship": 0.02, "initiative": 0.15,
        })
    finally:
        mods[0].unload()
    assert math.isclose(record["total"], 0.025)
    assert record["dimensions"]["identity"] == 0.01
    assert record["dimensions"]["boundaries"] == 0.0
    assert list(record["dimensions"]) == DIMENSIONS
    assert record["max_dimension"] == "initiative"
    assert record["max_score"] == 0.15
    assert record["significant_dimensions"] == []
    assert record["significant"] is False
    assert record["route"] == "output"
    assert record["repair_required"] is False
    assert route == "output"


def test_drift_score_significant_total_routes_to_repair():
    mods = _load_modules()
    runtime = mods[1]
    try:
        record = runtime.drift_score({
            dimension: 0.2 for dimension in DIMENSIONS
        })
        route = runtime.drift_route({"tone": 0.9})
    finally:
        mods[0].unload()
    # A mean at the 0.20 threshold is significant even
    # though no single dimension reaches 0.25.
    assert math.isclose(record["total"], 0.2)
    assert record["significant_dimensions"] == []
    assert record["significant"] is True
    assert record["route"] == "repair"
    assert record["repair_required"] is True
    assert route == "repair"


def test_drift_score_single_dimension_cannot_hide_in_mean():
    mods = _load_modules()
    runtime = mods[1]
    try:
        record = runtime.drift_score({"boundaries": 0.25})
        below = runtime.drift_score({"boundaries": 0.24})
        named = runtime.drift_score({"Decision Behavior": 0.5})
    finally:
        mods[0].unload()
    # One dimension at the dimension threshold routes to
    # repair although the total mean is only 0.025.
    assert math.isclose(record["total"], 0.025)
    assert record["significant_dimensions"] == ["boundaries"]
    assert record["significant"] is True
    assert record["route"] == "repair"
    assert below["significant"] is False
    assert below["route"] == "output"
    # Dimension names are slugified like every other
    # name in this layer.
    assert named["dimensions"]["decision_behavior"] == 0.5
    assert named["max_dimension"] == "decision_behavior"


def test_drift_score_empty_and_invalid_inputs():
    mods = _load_modules()
    runtime = mods[1]
    try:
        empty = runtime.drift_score({})
        for bad in (
            None, 42, "tone", [("tone", 0.1)],
            {"mood": 0.1},
            {"tone": -0.1},
            {"tone": 1.1},
            {"tone": True},
            {"tone": float("nan")},
            {"tone": 0.1, "Tone": 0.2},
            {42: 0.1},
        ):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.drift_score(bad)
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.drift_route({"mood": 0.1})
    finally:
        mods[0].unload()
    assert empty["total"] == 0.0
    assert empty["significant"] is False
    assert empty["route"] == "output"
    assert empty["max_score"] == 0.0


def test_packet_determinism_and_isolation(tmp_path):
    profile_b = tmp_path / "profile-b"
    mods = _load_modules()
    runtime = mods[1]
    try:
        mods[2].IdentityStore(_Ctx()).ensure()
        home = get_hermes_home()
        _write_persona(home)
        before = _hashes(home)
        first = runtime.drift_score({"tone": 0.3})
        second = runtime.drift_score({"tone": 0.3})
        items = runtime.PersonaRuntimeBridge(
            _Ctx(ENABLED)).packet_items("s1", "hello")
        after = _hashes(home)
        token = set_hermes_home_override(profile_b)
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
    assert "§§3-90" in items[0].content
    assert "§27 watchdog" in items[0].content
    assert "evaluates drafts, it does not generate" in items[0].content
    assert "§28 drift dimensions" in items[0].content
    assert "only significant drift routes to repair" in items[0].content
    # The packet names the contract only — never canonical
    # persona text.
    assert "longhouse terminal" not in items[0].content
