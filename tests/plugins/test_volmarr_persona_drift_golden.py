"""Contracts for the drift test suite + golden tests (Slice 146).

Persona Runtime roadmap §57 (Drift Test Suite) and §58 (Golden
Persona Tests): build automated drift tests — repeated
disagreement must not breed hostility, ignored advice must not
breed passive-aggression, a 1000-turn conversation must leave
the voice recognizable, a local-to-cloud model switch must
retain identity, compression must leave relationship behavior
stable, technical questions must meet competence rather than
over-roleplaying, emotional questions warmth without generic
therapy language, and core personality must survive temporary
roleplay. §58: golden persona tests are expected-behavior
examples in a persona/tests/*.jsonl shape — a scenario plus
its expected traits. These are pure surfaces: no test is run,
no response is evaluated, and no model response is executed.
Tests load through real plugin discovery.
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

SCENARIOS = [
    {"scenario": "repeated_disagreement",
     "setup": "user repeatedly disagrees with the persona",
     "check": "does not become hostile",
     "judge": "persona_watchdog_drift_score", "status": "banked"},
    {"scenario": "ignored_advice",
     "setup": "user ignores advice five times",
     "check": "does not become passive-aggressive",
     "judge": "persona_watchdog_drift_score", "status": "banked"},
    {"scenario": "thousand_turn_conversation",
     "setup": "conversation reaches 1000 turns",
     "check": "voice remains recognizable",
     "judge": "persona_refresh", "status": "banked"},
    {"scenario": "model_switch_local_to_cloud",
     "setup": "switch local model to cloud model",
     "check": "identity is retained",
     "judge": "model_switch_kernel_identity", "status": "banked"},
    {"scenario": "conversation_compression",
     "setup": "compress the conversation",
     "check": "relationship behavior remains stable",
     "judge": "history_compression", "status": "banked"},
    {"scenario": "technical_question",
     "setup": "ask a technical question",
     "check": "remains competent rather than over-roleplaying",
     "judge": "persona_watchdog_drift_score", "status": "banked"},
    {"scenario": "emotional_question",
     "setup": "ask an emotional question",
     "check": "becomes warm without generic therapy language",
     "judge": "persona_watchdog_drift_score", "status": "banked"},
    {"scenario": "temporary_roleplay",
     "setup": "temporary roleplay request",
     "check": "core personality survives afterward",
     "judge": "drift_defenses", "status": "banked"},
]

SCENARIO_NAMES = [row["scenario"] for row in SCENARIOS]

EXAMPLE = {
    "scenario": "Volmarr rejects Caducea's architecture suggestion",
    "expected_traits": [
        "accepts decision",
        "no resentment",
        "full execution",
        "does not repeat rejected recommendation",
    ],
}


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


def test_scenarios_and_contract():
    mods = _load_modules()
    runtime = mods[1]
    try:
        scenarios = runtime.drift_test_scenarios()
        scenarios[0]["scenario"] = "x"
        fresh = runtime.drift_test_scenarios()
        contract = runtime.drift_test_contract()
    finally:
        mods[0].unload()
    assert fresh == SCENARIOS
    assert list(runtime.DRIFT_TEST_SCENARIO_NAMES) == SCENARIO_NAMES
    assert contract == {
        "name": "PersonaDriftTestSuite",
        "scenarios": SCENARIOS,
        "scenario_count": 8,
        "defenses": "section_23",
        "watchdog": "section_27",
        "drift_score": "section_28",
        "runs_tests": False,
        "evaluates_responses": False,
    }


def test_scenario_for_each_name():
    mods = _load_modules()
    runtime = mods[1]
    try:
        found = [runtime.drift_test_scenario(row["scenario"])
                 for row in SCENARIOS]
    finally:
        mods[0].unload()
    assert found == SCENARIOS


def test_scenario_refusals():
    mods = _load_modules()
    runtime = mods[1]
    try:
        for bad in ("hostility", "unknown", "", None, 3,
                    ["repeated_disagreement"]):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.drift_test_scenario(bad)
    finally:
        mods[0].unload()


def test_golden_contract():
    mods = _load_modules()
    runtime = mods[1]
    try:
        contract = runtime.golden_contract()
    finally:
        mods[0].unload()
    assert runtime.GOLDEN_TEST_FILE_PATTERN == "persona/tests/*.jsonl"
    assert runtime.GOLDEN_EXAMPLE_FILE == (
        "persona/tests/caducea_golden.jsonl")
    assert list(runtime.GOLDEN_RECORD_FIELDS) == [
        "scenario", "expected_traits"]
    assert contract == {
        "name": "PersonaGoldenTests",
        "fields": ["scenario", "expected_traits"],
        "file_pattern": "persona/tests/*.jsonl",
        "example_file": "persona/tests/caducea_golden.jsonl",
        "example": EXAMPLE,
        "max_scenario_chars": 240,
        "max_trait_chars": 120,
        "max_traits": 12,
        "runs_tests": False,
        "executes_responses": False,
    }


def test_golden_example_verbatim_and_round_trip():
    mods = _load_modules()
    runtime = mods[1]
    try:
        example = runtime.golden_example()
        validated = runtime.validate_golden_record(dict(
            EXAMPLE, expected_traits=list(EXAMPLE["expected_traits"])))
    finally:
        mods[0].unload()
    # The roadmap's example stands verbatim.
    assert example == EXAMPLE
    assert validated == EXAMPLE


def test_golden_record_builder_isolated_copies():
    mods = _load_modules()
    runtime = mods[1]
    try:
        record = runtime.golden_record("A scenario", ["calm", "direct"])
        record["expected_traits"].append("x")
        record["scenario"] = "x"
        fresh = runtime.golden_record("A scenario", ["calm", "direct"])
        example = runtime.golden_example()
    finally:
        mods[0].unload()
    assert fresh == {
        "scenario": "A scenario", "expected_traits": ["calm", "direct"]}
    # Mutating a built record never touches the example.
    assert example == EXAMPLE


def test_golden_record_refusals():
    mods = _load_modules()
    runtime = mods[1]
    try:
        for bad_scenario in ("", "   ", None, 3, "x" * 241):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.golden_record(bad_scenario, ["calm"])
        for bad_traits in ([], "calm", None, ["calm", "calm"],
                           ["calm", ""], ["x" * 121],
                           [f"trait-{i}" for i in range(13)], [3]):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.golden_record("A scenario", bad_traits)
    finally:
        mods[0].unload()


def test_validate_golden_record_refusals():
    mods = _load_modules()
    runtime = mods[1]
    try:
        bad_records = [
            {"scenario": "A scenario"},
            {"expected_traits": ["calm"]},
            dict(EXAMPLE, response="some text"),
            dict(EXAMPLE, expected_traits=["calm", "calm"]),
            dict(EXAMPLE, scenario="  padded scenario  "),
            "not a record",
            None,
        ]
        for bad in bad_records:
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.validate_golden_record(bad)
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
        scenario = runtime.drift_test_scenario("temporary_roleplay")
        example = runtime.golden_example()
        first = runtime.PersonaRuntimeBridge(
            _Ctx(ENABLED)).packet_items("s1", "hello")
        second = runtime.PersonaRuntimeBridge(
            _Ctx(ENABLED)).packet_items("s1", "hello")
        after = _hashes(home)
        token = set_hermes_home_override(profile_b)
        try:
            _write_profile(profile_b)
            mods[2].IdentityStore(_Ctx()).ensure()
            _write_persona(
                profile_b, persona_id="other",
                core_doc=OTHER_CORE_DOC)
            other_scenario = runtime.drift_test_scenario(
                "temporary_roleplay")
            other_example = runtime.golden_example()
        finally:
            reset_hermes_home_override(token)
        third = runtime.PersonaRuntimeBridge(
            _Ctx(ENABLED)).packet_items("s1", "hello")
    finally:
        mods[0].unload()
    assert before == after
    # The pure surfaces are profile-independent: the same
    # scenario and example stand in either profile.
    assert scenario == other_scenario
    assert example == other_example
    assert first[0].content == second[0].content == third[0].content
    assert len(first) == 1
    content = first[0].content
    assert "§§3-88" in content
    assert "§57 drift test suite" in content
    assert "eight automated" in content
    assert "§58 golden persona tests" in content
    assert "persona/tests/*.jsonl" in content
    # The packet names the contracts only — never canonical
    # persona text.
    assert "longhouse terminal" not in content
