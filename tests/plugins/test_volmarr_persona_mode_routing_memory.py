"""Contracts for mode routing + persona-aware memory (Slice 137).

Persona Runtime roadmap §39 (Mode Routing) and §40
(Persona-Aware Memory Write): modes route automatically
from the task signal — the user does not manually select
them — and a memory write is interpreted through the
persona system in one neutral template, never biased
summarization that introduces personality drift. These
are pure contract surfaces: no mode is switched live and
no memory is written.
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

EXAMPLES = [
    {"signal": "coding", "modes": ["architect", "forge_worker"]},
    {"signal": "personal_reflection",
     "modes": ["companion", "counselor"]},
    {"signal": "research", "modes": ["researcher"]},
    {"signal": "creative_article", "modes": ["skald"]},
]

FIELDS = [
    "subject", "decision", "considered", "recommended_by",
    "response_by", "response", "memory_text",
]

CORRECT_TEXT = (
    "Volmarr selected architecture B after considering "
    "Caducea's recommendation of A. Caducea accepted "
    "decision and implemented B."
)


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


def _record(runtime, **overrides):
    kwargs = {
        "subject": "Volmarr",
        "decision": "architecture B",
        "considered": "A",
        "recommended_by": "Caducea",
        "response_by": "Caducea",
        "response": "accepted decision and implemented B",
    }
    kwargs.update(overrides)
    return runtime.persona_memory(**kwargs)


def test_mode_routing_contract_exact():
    mods = _load_modules()
    runtime = mods[1]
    try:
        contract = runtime.mode_routing_contract()
        examples = runtime.mode_routing_examples()
        examples.append({"signal": "tampered", "modes": []})
        fresh = runtime.mode_routing_examples()
    finally:
        mods[0].unload()
    assert fresh == EXAMPLES
    # Automatic routing — no manual selection, no identity change.
    assert contract == {
        "name": "PersonaModeRouting",
        "examples": EXAMPLES,
        "automatic": True,
        "manual_selection_required": False,
        "changes_identity": False,
        "switches_modes": False,
    }


def test_route_mode_roadmap_examples():
    mods = _load_modules()
    runtime = mods[1]
    try:
        coding = runtime.route_mode("coding")
        reflection = runtime.route_mode("Personal Reflection")
        research = runtime.route_mode("research")
        article = runtime.route_mode("creative article")
        for example in EXAMPLES:
            route = runtime.route_mode(example["signal"])
            assert route["modes"] == example["modes"]
            # Every routed mode is a valid §38 mode.
            for mode in route["modes"]:
                assert mode in runtime.PERSONA_MODES
    finally:
        mods[0].unload()
    assert coding == {
        "signal": "coding",
        "modes": ["architect", "forge_worker"],
        "initial_mode": "architect",
        "final_mode": "forge_worker",
        "manual_selection_required": False,
        "changes_identity": False,
        "identity_preserved": True,
    }
    assert reflection["modes"] == ["companion", "counselor"]
    assert research["modes"] == ["researcher"]
    assert article["modes"] == ["skald"]


def test_route_mode_from_task_text():
    mods = _load_modules()
    runtime = mods[1]
    try:
        assert runtime.route_mode(
            "debug this python function")["signal"] == "coding"
        assert runtime.route_mode(
            "research the documentation")["signal"] == "research"
        assert runtime.route_mode(
            "a moment of personal reflection")["signal"] == (
                "personal_reflection")
        assert runtime.route_mode(
            "write a creative article")["signal"] == (
                "creative_article")
        for bad in (None, 42, "", "   ", "wizardry and tea"):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.route_mode(bad)
    finally:
        mods[0].unload()


def test_memory_write_contract_exact():
    mods = _load_modules()
    runtime = mods[1]
    try:
        contract = runtime.memory_write_contract()
    finally:
        mods[0].unload()
    assert contract == {
        "name": "PersonaAwareMemoryWrite",
        "fields": FIELDS,
        "interprets_through_persona": True,
        "biased_summarization_allowed": False,
        "introduces_personality_drift": False,
        "writes_memory": False,
        "bias_markers": list(runtime.MEMORY_BIAS_MARKERS),
    }
    assert list(runtime.PERSONA_MEMORY_FIELDS) == FIELDS
    assert "ignored_good_advice" in runtime.MEMORY_BIAS_MARKERS


def test_persona_memory_roadmap_example():
    mods = _load_modules()
    runtime = mods[1]
    try:
        record = _record(runtime)
    finally:
        mods[0].unload()
    # The roadmap §40 correct memory, exactly.
    assert record == {
        "persona_memory": {
            "subject": "volmarr",
            "decision": "architecture B",
            "considered": "A",
            "recommended_by": "caducea",
            "response_by": "caducea",
            "response": "accepted decision and implemented B",
            "memory_text": CORRECT_TEXT,
        }
    }
    assert runtime.validate_persona_memory(record) == record


def test_persona_memory_minimal_and_refusals():
    mods = _load_modules()
    runtime = mods[1]
    try:
        minimal = runtime.persona_memory("Volmarr", "a quiet day")
        assert minimal["persona_memory"]["memory_text"] == (
            "Volmarr selected a quiet day.")
        assert minimal["persona_memory"]["considered"] is None
        # A considered recommendation needs its recommender,
        # and a response needs who responded.
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.persona_memory(
                "Volmarr", "architecture B", considered="A")
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.persona_memory(
                "Volmarr", "architecture B",
                recommended_by="Caducea")
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.persona_memory(
                "Volmarr", "architecture B",
                response="accepted the decision")
        # Biased phrasing is refused in any field.
        with pytest.raises(runtime.PersonaRuntimeError):
            _record(runtime, decision="ignored good advice")
        with pytest.raises(runtime.PersonaRuntimeError):
            _record(runtime,
                    response="noted the bad advice and moved on")
        for bad_subject in (None, "", "   ", 42):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.persona_memory(bad_subject, "architecture B")
    finally:
        mods[0].unload()


def test_validate_persona_memory_refuses_tampering():
    mods = _load_modules()
    runtime = mods[1]
    try:
        good = _record(runtime)
        assert runtime.validate_persona_memory(good) == good
        for mutate in (
                lambda r: r["persona_memory"].update(extra=1),
                lambda r: r["persona_memory"].pop("decision"),
                lambda r: r["persona_memory"].update(
                    memory_text="Volmarr ignored good advice."),
                lambda r: r["persona_memory"].update(
                    subject="someone_else"),
                lambda r: r.update(memory={"fake": True})):
            record = copy.deepcopy(good)
            mutate(record)
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.validate_persona_memory(record)
        for bad in (None, 42, {}, {"persona_memory": []}):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.validate_persona_memory(bad)
    finally:
        mods[0].unload()


def test_classify_memory_write_bias():
    mods = _load_modules()
    runtime = mods[1]
    try:
        biased = runtime.classify_memory_write(
            "Volmarr ignored good advice.")
        neutral = runtime.classify_memory_write(CORRECT_TEXT)
        for bad in (None, 42, "", "   "):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.classify_memory_write(bad)
    finally:
        mods[0].unload()
    # The roadmap's incorrect memory is biased summarization.
    assert biased == {
        "biased": True,
        "bias_markers": ["ignored_good_advice", "good_advice"],
        "allowed_as_memory": False,
        "introduces_personality_drift": True,
    }
    assert neutral == {
        "biased": False,
        "bias_markers": [],
        "allowed_as_memory": True,
        "introduces_personality_drift": False,
    }


def test_packet_determinism_and_isolation(tmp_path):
    profile_b = tmp_path / "profile-b"
    mods = _load_modules()
    runtime = mods[1]
    try:
        mods[2].IdentityStore(_Ctx()).ensure()
        home = get_hermes_home()
        _write_persona(home)
        before = _hashes(home)
        first = runtime.route_mode("coding")
        second = runtime.route_mode("coding")
        record = _record(runtime)
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
    assert record["persona_memory"]["memory_text"] == CORRECT_TEXT
    assert len(items) == 1
    assert "§§3-48" in items[0].content
    assert "§39 mode routing" in items[0].content
    assert "manually select" in items[0].content
    assert "§40 persona-aware" in items[0].content
    assert "biased summarization" in items[0].content
    # The packet names the contract only — never canonical
    # persona text or authored anchor prose.
    assert "longhouse terminal" not in items[0].content
    assert "does not command" not in items[0].content
