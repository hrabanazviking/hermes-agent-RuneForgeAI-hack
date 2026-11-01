"""Contracts for persona state + modes (Slice 136).

Persona Runtime roadmap §37 (Persona State) and §38
(Modes): the persona state is a dynamic runtime object in
the roadmap's YAML shape (id, version, active_mode,
emotional_state warmth/playfulness/focus,
relationship_state trust, active_project, current_task)
that must never replace canonical PersonaIR, and modes
modify emphasis without changing identity — a mode
foregrounds parts of the same personality. These are pure
contract surfaces: no state is stored, nothing live is
tracked, and no mode is switched.
Tests load through real plugin discovery.
"""

from __future__ import annotations

import copy
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
    "id", "version", "active_mode", "emotional_state",
    "relationship_state", "active_project", "current_task",
]

MODES = [
    "counselor", "executor", "architect", "skald",
    "companion", "researcher", "forge_worker",
]

EMOTIONAL = {"warmth": 0.88, "playfulness": 0.44, "focus": 0.91}
RELATIONSHIP = {"trust": 0.95}


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
        "version": "1.4.2",
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


def _state(runtime, compiled, **overrides):
    kwargs = {
        "active_mode": "architect",
        "emotional_state": dict(EMOTIONAL),
        "relationship_state": dict(RELATIONSHIP),
        "active_project": "hermes",
        "current_task": "persona_runtime",
    }
    kwargs.update(overrides)
    return runtime.persona_state(compiled, **kwargs)


def test_persona_state_contract_exact():
    mods = _load_modules()
    runtime = mods[1]
    try:
        contract = runtime.persona_state_contract()
        fields = runtime.persona_state_fields()
        fields.append("tampered")
        fresh = runtime.persona_state_fields()
    finally:
        mods[0].unload()
    assert fresh == FIELDS
    assert list(runtime.PERSONA_STATE_FIELDS) == FIELDS
    # Dynamic, and never a replacement for canonical IR.
    assert contract == {
        "name": "PersonaState",
        "fields": FIELDS,
        "emotional_state_fields": ["warmth", "playfulness", "focus"],
        "relationship_state_fields": ["trust"],
        "dynamic": True,
        "replaces_persona_ir": False,
        "canonical_source": "persona_ir",
        "stores_state": False,
    }


def test_modes_contract_exact():
    mods = _load_modules()
    runtime = mods[1]
    try:
        contract = runtime.mode_contract()
        modes = runtime.persona_modes()
        modes.append("tampered")
        fresh = runtime.persona_modes()
    finally:
        mods[0].unload()
    assert fresh == MODES
    assert list(runtime.PERSONA_MODES) == MODES
    # Modes modify emphasis only — identity never changes.
    assert contract == {
        "name": "PersonaModes",
        "modes": MODES,
        "modifies_emphasis": True,
        "changes_identity": False,
        "foregrounds_same_personality": True,
        "switches_modes": False,
    }


def test_persona_state_roadmap_shape():
    mods = _load_modules()
    runtime = mods[1]
    try:
        mods[2].IdentityStore(_Ctx()).ensure()
        _write_persona(get_hermes_home())
        compiled = _compiled(runtime)
        state = _state(runtime, compiled)
    finally:
        mods[0].unload()
    # The roadmap §37 example, exactly: caducea 1.4.2,
    # architect, the example scores, hermes / persona_runtime.
    assert state == {
        "persona_state": {
            "id": "caducea",
            "version": "1.4.2",
            "active_mode": "architect",
            "emotional_state": EMOTIONAL,
            "relationship_state": RELATIONSHIP,
            "active_project": "hermes",
            "current_task": "persona_runtime",
        }
    }
    assert runtime.validate_persona_state(state) == state


def test_persona_state_refusals():
    mods = _load_modules()
    runtime = mods[1]
    try:
        mods[2].IdentityStore(_Ctx()).ensure()
        _write_persona(get_hermes_home())
        compiled = _compiled(runtime)
        # A mode outside the §38 list is refused.
        with pytest.raises(runtime.PersonaRuntimeError):
            _state(runtime, compiled, active_mode="wizard")
        # Emotional state: missing, extra, out-of-range,
        # boolean, and non-numeric values are refused.
        for emotional in (
                {"warmth": 0.5, "playfulness": 0.5},
                dict(EMOTIONAL, mood=0.5),
                dict(EMOTIONAL, warmth=1.5),
                dict(EMOTIONAL, warmth=-0.1),
                dict(EMOTIONAL, warmth=True),
                dict(EMOTIONAL, warmth="warm"),
                None, [0.88, 0.44, 0.91]):
            with pytest.raises(runtime.PersonaRuntimeError):
                _state(runtime, compiled, emotional_state=emotional)
        # Relationship state carries trust only.
        for relationship in ({}, {"trust": 1.01},
                             {"trust": 0.9, "warmth": 0.5}, None):
            with pytest.raises(runtime.PersonaRuntimeError):
                _state(runtime, compiled,
                       relationship_state=relationship)
        # Missing project / task names are refused.
        for overrides in ({"active_project": ""},
                          {"active_project": None},
                          {"current_task": "   "},
                          {"current_task": 42}):
            with pytest.raises(runtime.PersonaRuntimeError):
                _state(runtime, compiled, **overrides)
    finally:
        mods[0].unload()


def test_validate_persona_state_refuses_tampering():
    mods = _load_modules()
    runtime = mods[1]
    try:
        good = {
            "persona_state": {
                "id": "caducea",
                "version": "1.4.2",
                "active_mode": "architect",
                "emotional_state": dict(EMOTIONAL),
                "relationship_state": dict(RELATIONSHIP),
                "active_project": "hermes",
                "current_task": "persona_runtime",
            }
        }
        assert runtime.validate_persona_state(good) == good
        for mutate in (
                lambda s: s["persona_state"].update(extra=1),
                lambda s: s["persona_state"].pop("version"),
                lambda s: s["persona_state"].update(version="1.4"),
                lambda s: s["persona_state"].update(
                    active_mode="wizard"),
                lambda s: s["persona_state"].update(
                    id="Caducea Prime"),
                lambda s: s["persona_state"]["emotional_state"]
                .update(focus=2.0),
                lambda s: s.update(persona_ir={"fake": True})):
            state = copy.deepcopy(good)
            mutate(state)
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.validate_persona_state(state)
        for bad in (None, 42, {}, {"persona_state": []}):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.validate_persona_state(bad)
    finally:
        mods[0].unload()


def test_mode_profile_classification():
    mods = _load_modules()
    runtime = mods[1]
    try:
        architect = runtime.mode_profile("Architect")
        forge = runtime.mode_profile("forge worker")
        for mode in MODES:
            profile = runtime.mode_profile(mode)
            assert profile["mode"] == mode
            assert profile["identity_preserved"] is True
        for bad in (None, 42, "", "   ", "wizard", "admin"):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.mode_profile(bad)
    finally:
        mods[0].unload()
    assert architect == {
        "mode": "architect", "modifies_emphasis": True,
        "changes_identity": False, "foreground": "architect",
        "identity_preserved": True,
    }
    assert forge["mode"] == "forge_worker"
    assert forge["changes_identity"] is False


def test_state_never_replaces_persona_ir():
    mods = _load_modules()
    runtime = mods[1]
    try:
        mods[2].IdentityStore(_Ctx()).ensure()
        _write_persona(get_hermes_home())
        compiled = _compiled(runtime)
        before = copy.deepcopy(compiled)
        calm = _state(
            runtime, compiled,
            emotional_state={"warmth": 0.5, "playfulness": 0.5,
                             "focus": 0.5})
        intense = _state(
            runtime, compiled,
            emotional_state={"warmth": 0.9, "playfulness": 0.9,
                             "focus": 0.9})
        after = copy.deepcopy(compiled)
    finally:
        mods[0].unload()
    # Building dynamic state changes no compile, kernel,
    # or IR — different states, identical identity hashes.
    assert before == after
    assert calm != intense
    assert compiled["kernel"]["sha256"] == before["kernel"]["sha256"]
    assert compiled["ir"]["ir_hash"] == before["ir"]["ir_hash"]
    assert compiled["persona_hash"] == before["persona_hash"]
    assert "persona_ir" not in calm["persona_state"]
    assert "kernel" not in calm["persona_state"]


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
        first = _state(runtime, compiled)
        second = _state(runtime, compiled)
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
    assert "§§3-84" in items[0].content
    assert "§37 persona state" in items[0].content
    assert "never replaces" in items[0].content
    assert "§38 modes" in items[0].content
    assert "without changing identity" in items[0].content
    # The packet names the contract only — never canonical
    # persona text or authored anchor prose.
    assert "longhouse terminal" not in items[0].content
    assert "does not command" not in items[0].content
