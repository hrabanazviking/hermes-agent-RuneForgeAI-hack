"""Contracts for handoff packet + subagent separation (Slice 135).

Persona Runtime roadmap §35 (Persona Handoff Packet) and §36
(Subagent Separation): when routing to another model, a
handoff packet carries persona_id, persona_version, kernel,
current_mode, relationship_state, and relevant_sections named
by stable id — avoiding passing the whole conversation when
unnecessary — and subagents are not turned into the primary
persona: each carries its own identity and role, while the
primary persona may delegate and maintains its own identity.
These are pure contract surfaces: no model is routed, nothing
is handed off, nothing is delegated or spawned.
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

FIELDS = [
    "persona_id", "persona_version", "kernel", "current_mode",
    "relationship_state", "relevant_sections",
]

SECTIONS = ["core.core_identity", "service_bible.shell_policy"]

STATE = "Volmarr is the householder; counsel is offered, not imposed."


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


def _compiled(runtime):
    return runtime.PersonaCompiler(_Ctx(ENABLED)).compile()


def test_handoff_contract_exact():
    mods = _load_modules()
    runtime = mods[1]
    try:
        contract = runtime.handoff_contract()
        fields = runtime.handoff_packet_fields()
        fields.append("tampered")
        fresh = runtime.handoff_packet_fields()
    finally:
        mods[0].unload()
    assert fresh == FIELDS
    assert list(runtime.HANDOFF_PACKET_FIELDS) == FIELDS
    # The packet is created on routing, names sections by
    # stable id, and never carries the whole conversation.
    assert contract == {
        "name": "PersonaHandoffPacket",
        "created_when": "routing_to_another_model",
        "fields": FIELDS,
        "kernel_form": "kernel_hash",
        "sections_named_by": "stable_id",
        "passes_whole_conversation": False,
        "routes_models": False,
    }


def test_handoff_packet_roadmap_shape():
    mods = _load_modules()
    runtime = mods[1]
    try:
        mods[2].IdentityStore(_Ctx()).ensure()
        _write_persona(get_hermes_home())
        compiled = _compiled(runtime)
        packet = runtime.handoff_packet(
            compiled, "Architect", STATE, SECTIONS)
    finally:
        mods[0].unload()
    # The roadmap's own YAML shape, with the §34 switch's
    # kernel named by hash and sections by stable id.
    assert packet == {
        "persona_handoff": {
            "persona_id": "caducea",
            "persona_version": compiled["persona_version"],
            "kernel": compiled["kernel"]["sha256"],
            "current_mode": "architect",
            "relationship_state": STATE,
            "relevant_sections": SECTIONS,
        }
    }
    assert runtime.validate_handoff_packet(packet) == packet


def test_handoff_packet_refusals():
    mods = _load_modules()
    runtime = mods[1]
    try:
        mods[2].IdentityStore(_Ctx()).ensure()
        _write_persona(get_hermes_home())
        compiled = _compiled(runtime)
        # A section the compiled index does not contain, a
        # malformed stable id, and a duplicate are refused.
        for sections in (["core.no_such_section"],
                         ["Core Identity"], ["core."],
                         ["core.core_identity", "core.core_identity"],
                         "core.core_identity", [42]):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.handoff_packet(
                    compiled, "architect", STATE, sections)
        # Missing or malformed mode and state are refused.
        for mode, state in ((None, STATE), ("", STATE),
                            ("architect", None), ("architect", ""),
                            ("architect", "x" * 1001)):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.handoff_packet(compiled, mode, state, SECTIONS)
    finally:
        mods[0].unload()


def test_validate_handoff_packet_refuses_tampering():
    mods = _load_modules()
    runtime = mods[1]
    try:
        good = {
            "persona_handoff": {
                "persona_id": "caducea",
                "persona_version": "1.4.2",
                "kernel": "kernel-hash-1",
                "current_mode": "architect",
                "relationship_state": STATE,
                "relevant_sections": SECTIONS,
            }
        }
        assert runtime.validate_handoff_packet(good) == good
        # Extra or missing fields, a non-semver version, an
        # empty kernel, and a duplicated section are refused.
        import copy

        for mutate in (
                lambda p: p["persona_handoff"].update(extra=1),
                lambda p: p["persona_handoff"].pop("kernel"),
                lambda p: p["persona_handoff"].update(
                    persona_version="1.4"),
                lambda p: p["persona_handoff"].update(kernel="  "),
                lambda p: p["persona_handoff"].update(
                    relevant_sections=SECTIONS + SECTIONS[:1]),
                lambda p: p.update(conversation="whole history")):
            packet = copy.deepcopy(good)
            mutate(packet)
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.validate_handoff_packet(packet)
        for bad in (None, 42, {}, {"persona_handoff": []}):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.validate_handoff_packet(bad)
    finally:
        mods[0].unload()


def test_subagent_examples_roadmap_roster():
    mods = _load_modules()
    runtime = mods[1]
    try:
        roster = runtime.subagent_examples()
        roster[0]["agent"] = "tampered"
        fresh = runtime.subagent_examples()
    finally:
        mods[0].unload()
    # The roadmap's example: Caducea primary, then Völundr,
    # Saga, and Eir — none of them Caducea.
    assert fresh == [
        {"agent": "caducea", "role": "orchestrator_companion",
         "is_primary_persona": True, "carries_primary_persona": True},
        {"agent": "volundr", "role": "specialized_builder",
         "is_primary_persona": False, "carries_primary_persona": False},
        {"agent": "saga", "role": "historian",
         "is_primary_persona": False, "carries_primary_persona": False},
        {"agent": "eir", "role": "repair_agent",
         "is_primary_persona": False, "carries_primary_persona": False},
    ]


def test_subagent_contract_exact():
    mods = _load_modules()
    runtime = mods[1]
    try:
        contract = runtime.subagent_contract()
    finally:
        mods[0].unload()
    assert contract == {
        "name": "SubagentSeparation",
        "primary_persona": "caducea",
        "examples": ["caducea", "volundr", "saga", "eir"],
        "subagents_carry_primary_persona": False,
        "subagents_have_own_identities": True,
        "primary_may_delegate": True,
        "primary_identity_maintained": True,
        "delegates_work": False,
    }


def test_subagent_separation_classification():
    mods = _load_modules()
    runtime = mods[1]
    try:
        primary = runtime.subagent_separation("Caducea")
        builder = runtime.subagent_separation("Volundr")
        other = runtime.subagent_separation("some other agent")
        named = runtime.subagent_separation("eir", "Eir")
        for bad in (None, 42, "", "   "):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.subagent_separation(bad)
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.subagent_separation("eir", bad)
    finally:
        mods[0].unload()
    assert primary == {
        "agent": "caducea", "is_primary_persona": True,
        "carries_primary_persona": True, "has_own_identity": True,
        "may_delegate": True, "primary_identity_maintained": True,
    }
    # A subagent keeps its own identity and never becomes
    # the primary persona, whoever the primary is named as.
    assert builder["is_primary_persona"] is False
    assert builder["carries_primary_persona"] is False
    assert builder["may_delegate"] is False
    assert other["carries_primary_persona"] is False
    assert named["is_primary_persona"] is True


def test_packet_determinism_and_isolation(tmp_path):
    profile_b = tmp_path / "profile-b"
    mods = _load_modules()
    runtime = mods[1]
    try:
        mods[2].IdentityStore(_Ctx()).ensure()
        home = get_hermes_home()
        _write_persona(home)
        before = _hashes(home)
        compiled = _compiled(runtime)
        first = runtime.handoff_packet(
            compiled, "architect", STATE, SECTIONS)
        second = runtime.handoff_packet(
            compiled, "architect", STATE, SECTIONS)
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
    assert "§§3-48" in items[0].content
    assert "§35 handoff packet" in items[0].content
    assert "whole" in items[0].content
    assert "§36 subagent separation" in items[0].content
    assert "not" in items[0].content
    # The packet names the contract only — never canonical
    # persona text or authored anchor prose.
    assert "longhouse terminal" not in items[0].content
    assert "does not command" not in items[0].content
