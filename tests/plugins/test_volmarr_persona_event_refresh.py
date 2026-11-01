"""Contracts for event refresh + model switching (Slice 134).

Persona Runtime roadmap §33 (Event-Based Refresh) and §34
(Model Switching): refresh is better than a fixed interval
alone — it is also due after context compression, a model
switch, an agent handoff, a long idle period, a persona
file modification, a major relationship event, or memory
consolidation, carrying the §32 contents with no interval
required — and every model receives the same canonical
Persona Kernel, the model being the engine and the persona
system the identity layer, so identity is preserved
exactly when the kernel hash is unchanged across a switch.
These are pure contract surfaces: no session is watched,
no event is detected, no model is routed or switched.
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

EVENTS = [
    "context_compression", "model_switch", "agent_handoff",
    "long_idle_period", "persona_file_modification",
    "major_relationship_event", "memory_consolidation",
]

CONTENTS = [
    "persona_kernel", "current_relationship_state",
    "relevant_service_bible_anchors",
]

KERNEL_HASH = "kernel-hash-1"


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


def test_event_refresh_triggers_roadmap_order():
    mods = _load_modules()
    runtime = mods[1]
    try:
        triggers = runtime.event_refresh_triggers()
        triggers.append("tampered")
        fresh = runtime.event_refresh_triggers()
    finally:
        mods[0].unload()
    # The seven §33 events stand in roadmap order, as a
    # fresh copy each call.
    assert fresh == EVENTS
    assert list(runtime.EVENT_REFRESH_TRIGGERS) == EVENTS


def test_event_refresh_contract_exact():
    mods = _load_modules()
    runtime = mods[1]
    try:
        contract = runtime.event_refresh_contract()
    finally:
        mods[0].unload()
    # Better than a fixed interval alone: no interval is
    # required, and a due refresh carries the §32 contents.
    assert contract == {
        "name": "EventBasedPersonaRefresh",
        "triggers": EVENTS,
        "better_than_fixed_interval_alone": True,
        "fixed_interval_required": False,
        "contents": CONTENTS,
        "prevents": "slow_identity_evaporation",
        "watches_session": False,
        "injects_context": False,
    }


def test_event_refresh_due_on_occurrence():
    mods = _load_modules()
    runtime = mods[1]
    try:
        for event in EVENTS:
            assert runtime.event_refresh_due(event) is True
        # Human spellings slugify onto the same events.
        assert runtime.event_refresh_due("Agent Handoff") is True
        assert runtime.event_refresh_due(
            "memory consolidation") is True
        # §32-only triggers are not §33 events, and no other
        # name is an event — refused, never guessed.
        for bad in (None, 42, "", "message_interval",
                    "context_summarization", "user_logged_in"):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.event_refresh_due(bad)
    finally:
        mods[0].unload()


def test_event_refresh_plan_carries_section32_contents():
    mods = _load_modules()
    runtime = mods[1]
    try:
        plan = runtime.event_refresh_plan("agent_handoff")
        for event in EVENTS:
            row = runtime.event_refresh_plan(event)
            assert row["due"] is True
            assert row["contents"] == CONTENTS
    finally:
        mods[0].unload()
    assert plan == {
        "trigger": "agent_handoff",
        "due": True,
        "action": "refresh",
        "basis": "event",
        "fixed_interval_required": False,
        "contents": CONTENTS,
        "prevents": "slow_identity_evaporation",
    }


def test_section32_refresh_still_refuses_section33_only_events():
    mods = _load_modules()
    runtime = mods[1]
    try:
        # The §32 list is not silently widened by §33: its
        # own due/plan surfaces still refuse the events
        # only §33 names (Slice 133's contract stands).
        for event in ("agent_handoff", "context_compression",
                      "long_idle_period",
                      "persona_file_modification",
                      "major_relationship_event",
                      "memory_consolidation"):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.refresh_due(event)
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.refresh_plan(event)
        # The one shared trigger, model switch, is due on
        # both surfaces.
        assert runtime.refresh_due("model_switch") is True
        assert runtime.event_refresh_due("model_switch") is True
    finally:
        mods[0].unload()


def test_model_switch_contract_exact():
    mods = _load_modules()
    runtime = mods[1]
    try:
        contract = runtime.model_switch_contract()
    finally:
        mods[0].unload()
    # The model is the engine; the persona system is the
    # identity layer. A switch is also a refresh trigger.
    assert contract == {
        "name": "PersonaModelSwitching",
        "kernel": "canonical_persona_kernel",
        "same_kernel_for_all_models": True,
        "model_role": "engine",
        "persona_system_role": "identity_layer",
        "identity_survives_switch": True,
        "refresh_trigger": "model_switch",
        "routes_models": False,
    }


def test_model_switch_plan_same_kernel_both_sides():
    mods = _load_modules()
    runtime = mods[1]
    try:
        plan = runtime.model_switch_plan(
            "Gemma local", "remote model", KERNEL_HASH)
    finally:
        mods[0].unload()
    # The roadmap's own example shape: the local engine and
    # the remote engine receive the SAME Persona Kernel.
    assert plan == {
        "from_model": "gemma_local",
        "to_model": "remote_model",
        "kernel": "canonical_persona_kernel",
        "kernel_hash": KERNEL_HASH,
        "from_kernel_hash": KERNEL_HASH,
        "to_kernel_hash": KERNEL_HASH,
        "same_kernel": True,
        "identity_preserved": True,
        "model_role": "engine",
        "persona_system_role": "identity_layer",
        "refresh_trigger": "model_switch",
    }


def test_model_switch_plan_refusals():
    mods = _load_modules()
    runtime = mods[1]
    try:
        # A switch to the same model is no switch.
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.model_switch_plan(
                "gemma_local", "Gemma local", KERNEL_HASH)
        # Missing or malformed names and hashes are refused.
        for args in ((None, "remote", KERNEL_HASH),
                     ("local", 42, KERNEL_HASH),
                     ("", "remote", KERNEL_HASH),
                     ("local", "remote", None),
                     ("local", "remote", ""),
                     ("local", "remote", "   ")):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.model_switch_plan(*args)
    finally:
        mods[0].unload()


def test_kernel_identity_preserved_is_hash_equality():
    mods = _load_modules()
    runtime = mods[1]
    try:
        assert runtime.kernel_identity_preserved(
            KERNEL_HASH, KERNEL_HASH) is True
        assert runtime.kernel_identity_preserved(
            KERNEL_HASH, "kernel-hash-2") is False
        for args in ((None, KERNEL_HASH), (KERNEL_HASH, ""),
                     (42, 42)):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.kernel_identity_preserved(*args)
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
        first = runtime.event_refresh_plan("memory_consolidation")
        second = runtime.event_refresh_plan("memory_consolidation")
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
    assert "§33 event refresh" in items[0].content
    assert "agent handoff" in items[0].content
    assert "§34 model switching" in items[0].content
    assert "same canonical Persona Kernel" in items[0].content
    # The packet names the contract only — never canonical
    # persona text or authored anchor prose.
    assert "longhouse terminal" not in items[0].content
    assert "does not command" not in items[0].content
