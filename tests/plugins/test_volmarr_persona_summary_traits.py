"""Contracts for summary claims + trait vs state (Slice 130).

Persona Runtime roadmap §25 (Conversation Summaries Must
Not Define Persona) and §26 (Trait vs State): a summary
may record state ("Caducea was frustrated during
debugging") but must never become a trait claim
("Caducea is a frustrated personality"), and traits and
states stay separate — traits come from persona files
and never decay, temporary states decay deterministically
and never become traits. These are pure contract
surfaces: no summary is built or read, no state is
tracked. Tests load through real plugin discovery.
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


def test_roadmap_summary_examples_state_allowed_trait_refused():
    mods = _load_modules()
    runtime = mods[1]
    try:
        state = runtime.classify_summary_claim(
            "Caducea was frustrated during debugging.")
        trait = runtime.classify_summary_claim(
            "Caducea is a frustrated personality.")
        allowed = runtime.summary_claim_allowed(
            "Caducea was frustrated during debugging.")
        refused = runtime.summary_claim_allowed(
            "Caducea is a frustrated personality.")
    finally:
        mods[0].unload()
    assert state == {
        "form": "state",
        "summary_may_record": True,
        "may_define_persona": False,
        "may_redefine_traits": False,
        "reason_code": "state_record_allowed",
    }
    assert trait == {
        "form": "trait",
        "summary_may_record": False,
        "may_define_persona": False,
        "may_redefine_traits": False,
        "reason_code": "trait_form_refused",
    }
    assert allowed is True
    assert refused is False


def test_summary_claim_forms_markers_and_fail_closed():
    mods = _load_modules()
    runtime = mods[1]
    try:
        forms = runtime.summary_claim_forms()
        cases = {
            "Caducea is currently amused.": "state",
            "She felt concerned about the architecture today.":
                "state",
            "Caducea was a frustrated personality during "
            "debugging.": "trait",
            "Caducea is an inherently warm counselor.": "trait",
            "Caducea always helps.": "trait",
            "Caducea debugged the terminal.": "unclassified",
            "Caducea is frustrated.": "unclassified",
        }
        results = {
            text: runtime.classify_summary_claim(text)
            for text in cases
        }
    finally:
        mods[0].unload()
    assert forms == ["state", "trait", "unclassified"]
    assert list(runtime.SUMMARY_CLAIM_FORMS) == forms
    for text, expected in cases.items():
        row = results[text]
        assert row["form"] == expected, text
        # Only state form may be recorded, and no form may
        # ever define persona or redefine traits.
        assert row["summary_may_record"] is (expected == "state")
        assert row["may_define_persona"] is False
        assert row["may_redefine_traits"] is False
    # Trait markers win over state markers (fail closed),
    # and an unclassified claim is refused, not guessed.
    assert results[
        "Caducea was a frustrated personality during "
        "debugging."]["reason_code"] == "trait_form_refused"
    assert results["Caducea debugged the terminal."][
        "reason_code"] == "unclassified_refused"


def test_summary_claim_invalid_inputs_are_refused():
    mods = _load_modules()
    runtime = mods[1]
    try:
        for bad in ("", "   ", None, 42, "x" * 1001):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.classify_summary_claim(bad)
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.summary_claim_allowed(None)
    finally:
        mods[0].unload()


def test_trait_state_separation_exact():
    mods = _load_modules()
    runtime = mods[1]
    try:
        rows = runtime.trait_state_separation()
        rows[0]["examples"].append("tampered")
        fresh = runtime.trait_state_separation()
    finally:
        mods[0].unload()
    assert runtime.trait_state_kinds() == ["trait", "state"]
    assert list(runtime.TRAIT_STATE_KINDS) == ["trait", "state"]
    assert fresh == [
        {
            "kind": "trait",
            "source": "canonical_persona_files",
            "defined_by": ["canonical_persona_files"],
            "decays": False,
            "half_life_hours": None,
            "expiry_threshold": None,
            "examples": [
                "warm", "devoted", "intelligent",
                "non_oppositional_counselor",
            ],
        },
        {
            "kind": "state",
            "source": "current_experience",
            "defined_by": [],
            "decays": True,
            "half_life_hours": 24.0,
            "expiry_threshold": 0.05,
            "examples": [
                "currently_amused",
                "currently_concerned_about_architecture",
            ],
        },
    ]
    assert list(runtime.EXAMPLE_TRAITS) == fresh[0]["examples"]
    assert list(runtime.EXAMPLE_STATES) == fresh[1]["examples"]
    assert runtime.STATE_HALF_LIFE_HOURS == 24.0
    assert runtime.STATE_EXPIRY_THRESHOLD == 0.05


def test_classify_attribute_traits_only_from_canonical_files():
    mods = _load_modules()
    runtime = mods[1]
    try:
        classify = runtime.classify_attribute
        results = {
            "core_default": classify("core"),
            "core_state": classify("core", "state"),
            "relationship_trait": classify(
                "relationship_model", "trait"),
            "conversation_trait": classify(
                "conversation_history", "trait"),
            "summary_trait": classify("summary", "trait"),
            "memory_trait": classify("memory", "trait"),
            "temporary_default": classify("temporary_roleplay"),
            "conversation_state": classify(
                "current_conversation", "state"),
        }
    finally:
        mods[0].unload()
    assert results["core_default"]["kind"] == "trait"
    assert results["core_default"]["claimed_kind"] is None
    assert results["core_default"]["may_define_persona"] is True
    assert results["core_default"]["decays"] is False
    assert results["core_state"]["kind"] == "state"
    assert results["core_state"]["may_define_persona"] is False
    assert results["core_state"]["decays"] is True
    assert results["relationship_trait"]["kind"] == "trait"
    assert results["relationship_trait"]["canonical"] is True
    # A trait claimed from any non-canonical source comes
    # back as a state with the trait claim refused.
    for key in ("conversation_trait", "summary_trait",
                "memory_trait"):
        row = results[key]
        assert row["claimed_kind"] == "trait", key
        assert row["kind"] == "state", key
        assert row["trait_claim_allowed"] is False, key
        assert row["may_define_persona"] is False, key
        assert row["decays"] is True, key
    assert results["summary_trait"]["tier"] == \
        "current_conversation"
    assert results["temporary_default"]["kind"] == "state"
    assert results["conversation_state"]["kind"] == "state"


def test_classify_attribute_invalid_inputs_are_refused():
    mods = _load_modules()
    runtime = mods[1]
    try:
        for bad_source in ("", None, 42, "weather", "avatar"):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.classify_attribute(bad_source)
        for bad_kind in ("", "mood", 42, "permanent"):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.classify_attribute("core", bad_kind)
    finally:
        mods[0].unload()


def test_state_decay_math_traits_never_decay():
    mods = _load_modules()
    runtime = mods[1]
    try:
        checks = (
            runtime.decayed_strength("trait", 0.8, 0),
            runtime.decayed_strength("trait", 0.8, 10000),
            runtime.decayed_strength("state", 0.8, 0),
            runtime.decayed_strength("state", 0.8, 24),
            runtime.decayed_strength("state", 0.8, 48),
            runtime.decayed_strength(
                "state", 0.9, 6, half_life_hours=6),
            runtime.state_decay("state", 0.8, 24),
            runtime.state_decay("state", 0.1, 48),
            runtime.state_decay("trait", 0.8, 10000),
        )
    finally:
        mods[0].unload()
    assert checks[0] == 0.8
    assert checks[1] == 0.8
    assert checks[2] == 0.8
    assert math.isclose(checks[3], 0.4)
    assert math.isclose(checks[4], 0.2)
    assert math.isclose(checks[5], 0.45)
    assert checks[6] == {
        "kind": "state",
        "initial_strength": 0.8,
        "elapsed_hours": 24.0,
        "half_life_hours": 24.0,
        "strength": 0.4,
        "decays": True,
        "expired": False,
    }
    # 0.1 halved twice is 0.025, below the 0.05 threshold:
    # the state expires; it never becomes a trait.
    assert math.isclose(checks[7]["strength"], 0.025)
    assert checks[7]["expired"] is True
    assert checks[7]["kind"] == "state"
    assert checks[8]["strength"] == 0.8
    assert checks[8]["half_life_hours"] is None
    assert checks[8]["decays"] is False
    assert checks[8]["expired"] is False


def test_decay_invalid_inputs_are_refused():
    mods = _load_modules()
    runtime = mods[1]
    try:
        bad_calls = (
            ("mood", 0.5, 1),
            ("state", -0.1, 1),
            ("state", 1.1, 1),
            ("state", True, 1),
            ("state", 0.5, -1),
            ("state", 0.5, float("nan")),
            ("trait", 0.5, float("inf")),
        )
        for kind, strength, elapsed in bad_calls:
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.decayed_strength(kind, strength, elapsed)
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.decayed_strength(
                "state", 0.5, 1, half_life_hours=0)
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.state_decay("state", 0.5, 1,
                                half_life_hours=-2)
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
        first = runtime.classify_summary_claim(
            "Caducea was frustrated during debugging.")
        second = runtime.classify_summary_claim(
            "Caducea was frustrated during debugging.")
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
    assert "§§3-40" in items[0].content
    assert "§25 summaries" in items[0].content
    assert "must never become a trait claim" in items[0].content
    assert "§26 trait vs state" in items[0].content
    assert "traits come from persona files" in items[0].content
    # The packet names the contract only — never canonical
    # persona text.
    assert "longhouse terminal" not in items[0].content
