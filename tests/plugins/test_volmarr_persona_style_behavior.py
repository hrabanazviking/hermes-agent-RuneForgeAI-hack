"""Contracts for the style + behavior fingerprints (Slice 147).

Persona Runtime roadmap §59 (Style Fingerprint) and §60
(Behavior Fingerprint): generate a lightweight style
fingerprint from the Persona Core over nine possible
dimensions, used as guidance, not rigid mathematical
personality; the behavior fingerprint, more important
than style, is named boolean behaviors that can be
automatically tested. These are pure surfaces: no live
style is scored, no dimension is derived from prose, and
no response is evaluated. Tests load through real plugin
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

STYLE_DIMENSIONS = [
    "warmth", "formality", "verbosity", "playfulness",
    "deference", "initiative", "technicality",
    "mythic_language", "emotional_intensity",
]

STYLE_EXAMPLE = {"style": {
    "warmth": 0.85, "formality": 0.35, "playfulness": 0.55,
    "deference": 0.72, "initiative": 0.90, "technicality": 0.84,
    "mythic_language": 0.42,
}}

BEHAVIOR_NAMES = [
    "counsel_before_material_risk", "accept_final_decision",
    "relitigate_decisions", "surface_new_information",
    "anticipate_needs", "avoid_unnecessary_questions",
    "prefer_complete_outputs",
]

BEHAVIOR_EXAMPLE = {"behavior": {
    "counsel_before_material_risk": True,
    "accept_final_decision": True,
    "relitigate_decisions": False,
    "surface_new_information": True,
    "anticipate_needs": True,
    "avoid_unnecessary_questions": True,
    "prefer_complete_outputs": True,
}}


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


def test_style_dimensions_and_contract():
    mods = _load_modules()
    runtime = mods[1]
    try:
        dims = runtime.style_dimensions()
        dims.append("x")
        contract = runtime.style_contract()
    finally:
        mods[0].unload()
    assert runtime.style_dimensions() == STYLE_DIMENSIONS
    assert list(runtime.STYLE_DIMENSIONS) == STYLE_DIMENSIONS
    assert contract == {
        "name": "PersonaStyleFingerprint",
        "dimensions": STYLE_DIMENSIONS,
        "example": STYLE_EXAMPLE,
        "generated_from": "persona_core",
        "guidance_not_rigid": True,
        "scores_live_style": False,
        "derives_from_prose": False,
    }


def test_style_example_verbatim_and_round_trip():
    mods = _load_modules()
    runtime = mods[1]
    try:
        example = runtime.style_example()
        validated = runtime.validate_style_fingerprint(
            {"style": dict(STYLE_EXAMPLE["style"])})
    finally:
        mods[0].unload()
    # The roadmap's example stands verbatim, subset included.
    assert example == STYLE_EXAMPLE
    assert validated == STYLE_EXAMPLE
    assert "verbosity" not in example["style"]
    assert "emotional_intensity" not in example["style"]


def test_style_fingerprint_subset_order_and_isolation():
    mods = _load_modules()
    runtime = mods[1]
    try:
        built = runtime.style_fingerprint(
            {"technicality": 0.5, "warmth": 1, "verbosity": 0})
        built["style"]["warmth"] = 0.0
        fresh = runtime.style_fingerprint(
            {"technicality": 0.5, "warmth": 1, "verbosity": 0})
    finally:
        mods[0].unload()
    # Supplied out of order, returned in roadmap order;
    # int values normalise to float; mutation is isolated.
    assert list(fresh["style"]) == [
        "warmth", "verbosity", "technicality"]
    assert fresh == {"style": {
        "warmth": 1.0, "verbosity": 0.0, "technicality": 0.5}}


def test_style_refusals():
    mods = _load_modules()
    runtime = mods[1]
    try:
        for bad in ({}, {"unknown": 0.5}, {"warmth": 1.01},
                    {"warmth": -0.1}, {"warmth": True},
                    {"warmth": "high"}, {"warmth": None},
                    "warmth", None, [("warmth", 0.5)]):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.style_fingerprint(bad)
    finally:
        mods[0].unload()


def test_validate_style_refusals():
    mods = _load_modules()
    runtime = mods[1]
    try:
        reversed_style = {"style": dict(reversed(
            list(STYLE_EXAMPLE["style"].items())))}
        bad_records = [
            {"style": dict(STYLE_EXAMPLE["style"]), "extra": 1},
            {"dimensions": dict(STYLE_EXAMPLE["style"])},
            {"style": {"warmth": 2.0}},
            {"style": {}},
            reversed_style,
            "not a fingerprint",
            None,
        ]
        for bad in bad_records:
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.validate_style_fingerprint(bad)
    finally:
        mods[0].unload()


def test_behavior_names_and_contract():
    mods = _load_modules()
    runtime = mods[1]
    try:
        names = runtime.behavior_names()
        names.append("x")
        contract = runtime.behavior_contract()
    finally:
        mods[0].unload()
    assert runtime.behavior_names() == BEHAVIOR_NAMES
    assert list(runtime.BEHAVIOR_NAMES) == BEHAVIOR_NAMES
    assert contract == {
        "name": "PersonaBehaviorFingerprint",
        "behaviors": BEHAVIOR_NAMES,
        "example": BEHAVIOR_EXAMPLE,
        "automatically_testable": True,
        "evaluates_responses": False,
    }


def test_behavior_example_verbatim_expectations_round_trip():
    mods = _load_modules()
    runtime = mods[1]
    try:
        example = runtime.behavior_example()
        validated = runtime.validate_behavior_fingerprint(
            {"behavior": dict(BEHAVIOR_EXAMPLE["behavior"])})
        expectations = {
            name: runtime.behavior_expectation(name)
            for name in BEHAVIOR_NAMES}
    finally:
        mods[0].unload()
    assert example == BEHAVIOR_EXAMPLE
    assert validated == BEHAVIOR_EXAMPLE
    assert expectations == BEHAVIOR_EXAMPLE["behavior"]
    # Never relitigate: the negative behavior stands false.
    assert expectations["relitigate_decisions"] is False


def test_behavior_refusals():
    mods = _load_modules()
    runtime = mods[1]
    try:
        full = dict(BEHAVIOR_EXAMPLE["behavior"])
        missing = dict(full)
        del missing["anticipate_needs"]
        for bad in (missing, dict(full, unknown=True),
                    dict(full, anticipate_needs="yes"),
                    dict(full, anticipate_needs=1),
                    {}, "behavior", None):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.behavior_fingerprint(bad)
        for bad_name in ("relitigate", "unknown", "", None, 3):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.behavior_expectation(bad_name)
    finally:
        mods[0].unload()


def test_validate_behavior_refusals():
    mods = _load_modules()
    runtime = mods[1]
    try:
        reversed_behavior = {"behavior": dict(reversed(
            list(BEHAVIOR_EXAMPLE["behavior"].items())))}
        bad_records = [
            {"behavior": dict(BEHAVIOR_EXAMPLE["behavior"]),
             "extra": True},
            {"behaviors": dict(BEHAVIOR_EXAMPLE["behavior"])},
            {"behavior": {"counsel_before_material_risk": True}},
            reversed_behavior,
            "not a fingerprint",
            None,
        ]
        for bad in bad_records:
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.validate_behavior_fingerprint(bad)
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
        example_style = runtime.style_example()
        example_behavior = runtime.behavior_example()
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
            other_style = runtime.style_example()
            other_behavior = runtime.behavior_example()
        finally:
            reset_hermes_home_override(token)
        third = runtime.PersonaRuntimeBridge(
            _Ctx(ENABLED)).packet_items("s1", "hello")
    finally:
        mods[0].unload()
    assert before == after
    assert example_style == other_style
    assert example_behavior == other_behavior
    assert first[0].content == second[0].content == third[0].content
    assert len(first) == 1
    content = first[0].content
    assert "§§3-94" in content
    assert "§59 style fingerprint" in content
    assert "guidance, not rigid" in content
    assert "§60 behavior fingerprint" in content
    assert "automatically testable" in content
    # The packet names the contracts only — never canonical
    # persona text.
    assert "longhouse terminal" not in content
