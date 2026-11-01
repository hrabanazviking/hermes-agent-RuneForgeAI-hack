"""Contracts for the local watchdog + persona refresh (Slice 133).

Persona Runtime roadmap §31 (Fast Local Persona Watchdog)
and §32 (Persona Refresh): the small local nervous-system
model is the ideal watchdog worker — six lightweight tasks
without expensive heavy inference, while the larger model
generates difficult content — and extremely long sessions
refresh the active context (message interval, context
summarization, model switch) with exactly the Persona
Kernel, the current relationship state, and the relevant
Service Bible anchors, preventing slow identity
evaporation. These are pure contract surfaces: no model
runs, no session is watched, nothing is injected. Tests
load through real plugin discovery.
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

TASKS = [
    "persona_classification", "drift_detection",
    "section_retrieval", "tone_checking", "memory_routing",
    "response_scoring",
]

SURFACES = {
    "persona_classification": "persona_ir",
    "drift_detection": "drift_score",
    "section_retrieval": "hybrid_retrieval",
    "tone_checking": "drift_dimension_tone",
    "memory_routing": "persona_router",
    "response_scoring": "drift_score_artifact",
}

TRIGGERS = [
    "message_interval", "context_summarization", "model_switch",
]

CONTENTS = [
    "persona_kernel", "current_relationship_state",
    "relevant_service_bible_anchors",
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


def test_local_watchdog_tasks_roadmap_order_and_grounding():
    mods = _load_modules()
    runtime = mods[1]
    try:
        rows = runtime.local_watchdog_tasks()
        rows[0]["worker"] = "tampered"
        fresh = runtime.local_watchdog_tasks()
    finally:
        mods[0].unload()
    # The six §31 tasks stand in roadmap order, each local,
    # none needing heavy inference or generating difficult
    # content, each grounded in its banked surface.
    assert [row["task"] for row in fresh] == TASKS
    assert list(runtime.LOCAL_WATCHDOG_TASKS) == TASKS
    assert {row["task"]: row["surface"] for row in fresh} == SURFACES
    assert all(row["worker"] == "local_model" for row in fresh)
    assert all(
        row["heavy_inference_required"] is False for row in fresh)
    assert all(
        row["generates_difficult_content"] is False
        for row in fresh)


def test_local_watchdog_contract_exact():
    mods = _load_modules()
    runtime = mods[1]
    try:
        contract = runtime.local_watchdog_contract()
    finally:
        mods[0].unload()
    # The larger model generates difficult content; the
    # local model keeps the personality coherent.
    assert contract == {
        "name": "FastLocalPersonaWatchdog",
        "worker": "small_local_model",
        "role": "nervous_system",
        "tasks": TASKS,
        "heavy_inference_required": False,
        "generates_difficult_content": False,
        "difficult_content_worker": "larger_model",
        "keeps_persona_coherent": True,
    }


def test_watchdog_worker_assignment():
    mods = _load_modules()
    runtime = mods[1]
    try:
        for task in TASKS:
            assert runtime.watchdog_worker(task) == "local_model"
        # Human spellings slugify onto the same tasks.
        assert runtime.watchdog_worker(
            "Drift Detection") == "local_model"
        assert runtime.watchdog_worker(
            "difficult content generation") == "larger_model"
        assert runtime.watchdog_worker(
            "generate_difficult_content") == "larger_model"
        for bad in (None, 42, "", "heavy_reasoning",
                    "write_the_book"):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.watchdog_worker(bad)
    finally:
        mods[0].unload()


def test_refresh_contract_exact():
    mods = _load_modules()
    runtime = mods[1]
    try:
        contract = runtime.refresh_contract()
        triggers = runtime.refresh_triggers()
        contents = runtime.refresh_contents()
    finally:
        mods[0].unload()
    assert triggers == TRIGGERS
    assert list(runtime.REFRESH_TRIGGERS) == TRIGGERS
    assert contents == CONTENTS
    assert list(runtime.REFRESH_CONTENTS) == CONTENTS
    assert runtime.REFRESH_MESSAGE_INTERVAL == 50
    assert contract == {
        "name": "PersonaRefresh",
        "triggers": TRIGGERS,
        "message_interval": 50,
        "contents": CONTENTS,
        "prevents": "slow_identity_evaporation",
        "injects_context": False,
    }


def test_refresh_due_event_triggers():
    mods = _load_modules()
    runtime = mods[1]
    try:
        # Naming an event trigger is naming the event: the
        # refresh is due the moment it has occurred.
        assert runtime.refresh_due("context_summarization") is True
        assert runtime.refresh_due("model switch") is True
        for bad in (None, 42, "", "long_idle_period",
                    "persona_file_modification"):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.refresh_due(bad)
    finally:
        mods[0].unload()


def test_refresh_due_message_interval():
    mods = _load_modules()
    runtime = mods[1]
    try:
        assert runtime.refresh_due("message_interval", 0) is False
        assert runtime.refresh_due("message_interval", 49) is False
        assert runtime.refresh_due("message_interval", 50) is True
        assert runtime.refresh_due("message_interval", 500) is True
        # A missing or malformed count is refused, never
        # guessed — this layer counts no live messages.
        for bad in (None, True, -1, 12.5, "50"):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.refresh_due("message_interval", bad)
    finally:
        mods[0].unload()


def test_refresh_plan_due_and_not_due():
    mods = _load_modules()
    runtime = mods[1]
    try:
        due = runtime.refresh_plan("model_switch")
        not_due = runtime.refresh_plan("message_interval", 10)
        interval_due = runtime.refresh_plan("message_interval", 50)
    finally:
        mods[0].unload()
    # A due refresh carries exactly the three §32 contents.
    assert due == {
        "trigger": "model_switch",
        "due": True,
        "action": "refresh",
        "contents": CONTENTS,
        "prevents": "slow_identity_evaporation",
        "message_interval": 50,
        "messages_since_refresh": None,
    }
    assert interval_due["due"] is True
    assert interval_due["contents"] == CONTENTS
    assert interval_due["messages_since_refresh"] == 50
    # An unelapsed interval refreshes nothing and carries
    # no contents.
    assert not_due["due"] is False
    assert not_due["action"] == "no_refresh"
    assert not_due["contents"] == []
    assert not_due["messages_since_refresh"] == 10


def test_packet_determinism_and_isolation(tmp_path):
    profile_b = tmp_path / "profile-b"
    mods = _load_modules()
    runtime = mods[1]
    try:
        mods[2].IdentityStore(_Ctx()).ensure()
        home = get_hermes_home()
        _write_persona(home)
        before = _hashes(home)
        first = runtime.refresh_plan("context_summarization")
        second = runtime.refresh_plan("context_summarization")
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
    assert "§§3-38" in items[0].content
    assert "§31 local watchdog" in items[0].content
    assert "small local" in items[0].content
    assert "§32 refresh" in items[0].content
    assert "slow identity" in items[0].content
    assert "evaporation" in items[0].content
    # The packet names the contract only — never canonical
    # persona text or authored anchor prose.
    assert "longhouse terminal" not in items[0].content
    assert "does not command" not in items[0].content
