"""Contracts for memory guard + Service Bible retrieval (Slice 138).

Persona Runtime roadmap §41 (Memory Must Not Override
Persona) and §42 (Service Bible Dynamic Retrieval):
memory provides history and must never transform the
persona — traits remain canonical however many memories
agree — and the Service Bible, which may become huge, is
indexed by topic and retrieved selectively, never
continuously injected. These are pure contract surfaces:
no memory is read and nothing is injected.
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

SERVICE_DOC = """# Communication

Speak plainly and name the decision first.

# Coding Preferences

Prefer small python functions and tests.

# Linux Operations

Use systemd services and shell commands on linux hosts.

# Project Aesir

Aesir runs models on the laptop gpu.

# Attention And ADHD

Keep one visible next step for attention and adhd support.
"""

DOCS = {
    "core": ("core.md", CORE_DOC),
    "service_bible": ("service.md", SERVICE_DOC),
}

TOPICS = [
    "communication", "coding", "linux", "open_source", "ai",
    "documentation", "research", "project_aesir", "attention",
    "adhd",
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


def test_memory_override_contract_exact():
    mods = _load_modules()
    runtime = mods[1]
    try:
        contract = runtime.memory_override_contract()
        provides = runtime.memory_provides()
        provides.append("tampered")
        fresh_provides = runtime.memory_provides()
        must_not = runtime.memory_must_not_override()
    finally:
        mods[0].unload()
    assert fresh_provides == [
        "history", "recent_events", "immediate_context"]
    assert must_not == [
        "foundational_personality", "identity", "traits"]
    assert contract == {
        "name": "MemoryMustNotOverridePersona",
        "traits_remain_canonical": True,
        "memory_role": "history",
        "memory_tier": "long_term_memory",
        "memory_may_override_persona": False,
        "memory_may_redefine_traits": False,
        "repeated_evidence_changes_authority": False,
        "memory_provides": fresh_provides,
        "memory_must_not_override": must_not,
        "retrieves_memory": False,
    }


def test_memory_influence_allowed_targets():
    mods = _load_modules()
    runtime = mods[1]
    try:
        allowed = {
            target: runtime.memory_influence_allowed(target)
            for target in (
                "current_mood", "mood", "immediate_context",
                "context", "recent_events",
                "foundational_personality", "personality",
                "character", "identity", "traits", "trait")
        }
        for bad in (None, 42, "", "everything"):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.memory_influence_allowed(bad)
    finally:
        mods[0].unload()
    assert allowed == {
        "current_mood": True, "mood": True,
        "immediate_context": True, "context": True,
        "recent_events": True,
        "foundational_personality": False, "personality": False,
        "character": False, "identity": False,
        "traits": False, "trait": False,
    }


def test_evaluate_memory_claim_forms():
    mods = _load_modules()
    runtime = mods[1]
    try:
        state = runtime.evaluate_memory_claim(
            "Caducea was frustrated during debugging")
        trait = runtime.evaluate_memory_claim(
            "Caducea is an anxious personality")
        roadmap_trait = runtime.evaluate_memory_claim(
            "Caducea is a frustrated personality")
        unclassified = runtime.evaluate_memory_claim(
            "Caducea debugged the parser")
        for bad in (None, 42, "", "   "):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.evaluate_memory_claim(bad)
    finally:
        mods[0].unload()
    # A state-form memory may be recorded as history.
    assert state == {
        "form": "state",
        "kind": "state",
        "trait_claim_allowed": False,
        "may_record_as_history": True,
        "may_define_persona": False,
        "may_redefine_traits": False,
        "may_override_persona": False,
        "reason_code": "state_record_allowed",
    }
    # The §41 danger exactly: repeated frustration must not
    # become a trait. Trait-form claims are refused as
    # history and may never define the persona.
    for claim in (trait, roadmap_trait):
        assert claim["form"] == "trait"
        assert claim["may_record_as_history"] is False
        assert claim["may_define_persona"] is False
        assert claim["may_override_persona"] is False
        assert claim["reason_code"] == "trait_form_refused"
    assert unclassified["form"] == "unclassified"
    assert unclassified["may_record_as_history"] is False


def test_memory_claim_authority_repetition_never_promotes():
    mods = _load_modules()
    runtime = mods[1]
    try:
        verdicts = [runtime.memory_claim_authority(count)
                    for count in (0, 1, 7, 1000)]
        for bad in (None, True, -1, 1.5, "3"):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.memory_claim_authority(bad)
    finally:
        mods[0].unload()
    for count, verdict in zip((0, 1, 7, 1000), verdicts):
        assert verdict == {
            "evidence_count": count,
            "tier": "long_term_memory",
            "rank": 3,
            "canonical": False,
            "may_redefine_traits": False,
            "may_override_persona": False,
        }


def test_service_bible_contract_and_topics():
    mods = _load_modules()
    runtime = mods[1]
    try:
        contract = runtime.service_bible_retrieval_contract()
        topics = runtime.service_bible_topics()
        topics.append("tampered")
        fresh = runtime.service_bible_topics()
    finally:
        mods[0].unload()
    assert fresh == TOPICS
    assert list(runtime.SERVICE_BIBLE_TOPICS) == TOPICS
    assert contract == {
        "name": "ServiceBibleDynamicRetrieval",
        "role": "service_bible",
        "topics": TOPICS,
        "continuously_injected": False,
        "retrieve_selectively": True,
        "retrieval": "explicit_only",
        "injects": False,
    }


def test_classify_service_topics():
    mods = _load_modules()
    runtime = mods[1]
    try:
        assert runtime.classify_service_topics(
            "linux systemd and python tests") == ["coding", "linux"]
        assert runtime.classify_service_topics(
            "project aesir attention adhd") == [
                "project_aesir", "attention", "adhd"]
        assert runtime.classify_service_topics(
            "github license for the repository") == ["open_source"]
        assert runtime.classify_service_topics("") == []
        assert runtime.classify_service_topics(
            "wizardry and tea") == []
        for bad in (None, 42, ["linux"]):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.classify_service_topics(bad)
    finally:
        mods[0].unload()


def test_service_topics_for_section():
    mods = _load_modules()
    runtime = mods[1]
    try:
        assert runtime.service_topics_for_section({
            "heading": "Linux Operations",
            "section_id": "linux_operations"}) == ["linux"]
        assert runtime.service_topics_for_section({
            "heading": "Attention And ADHD",
            "section_id": "attention_and_adhd"}) == [
                "attention", "adhd"]
        assert runtime.service_topics_for_section({
            "heading": "Project Aesir",
            "section_id": "project_aesir"}) == ["project_aesir"]
        assert runtime.service_topics_for_section({
            "heading": "Quiet Evenings",
            "section_id": "quiet_evenings"}) == []
    finally:
        mods[0].unload()


def test_retrieve_service_bible_role_restricted():
    mods = _load_modules()
    runtime = mods[1]
    try:
        mods[2].IdentityStore(_Ctx()).ensure()
        _write_persona(get_hermes_home())
        compiled = _compiled(runtime)
        linux = runtime.retrieve_service_bible(
            compiled["index"], query="linux systemd")
        counsel = runtime.retrieve_service_bible(
            compiled["index"], query="counselor")
        plain = runtime.retrieve_sections(
            compiled["index"], query="counselor")
        nothing = runtime.retrieve_service_bible(compiled["index"])
    finally:
        mods[0].unload()
    assert [row["stable_id"] for row in linux] == [
        "service_bible.linux_operations"]
    assert linux[0]["role"] == "service_bible"
    assert linux[0]["topics"] == ["linux"]
    assert "systemd" in linux[0]["text"]
    # The core document matches "counselor" under §13, but
    # §42 never returns another role's sections.
    assert plain and plain[0]["role"] == "core"
    assert counsel == []
    # No signal retrieves nothing — never a wholesale dump.
    assert nothing == []


def test_retrieve_service_bible_topic_selection():
    mods = _load_modules()
    runtime = mods[1]
    try:
        mods[2].IdentityStore(_Ctx()).ensure()
        _write_persona(get_hermes_home())
        compiled = _compiled(runtime)
        by_topic = runtime.retrieve_service_bible(
            compiled["index"], topic="Project Aesir")
        adhd = runtime.retrieve_service_bible(
            compiled["index"], topic="adhd")
        coding = runtime.retrieve_service_bible(
            compiled["index"], query="python functions",
            topic="coding")
        mismatched = runtime.retrieve_service_bible(
            compiled["index"], query="python functions",
            topic="linux")
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.retrieve_service_bible(
                compiled["index"], topic="wizardry")
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.retrieve_service_bible(
                compiled["index"], topic=42)
    finally:
        mods[0].unload()
    assert [row["stable_id"] for row in by_topic] == [
        "service_bible.project_aesir"]
    assert by_topic[0]["topics"] == ["project_aesir"]
    assert [row["stable_id"] for row in adhd] == [
        "service_bible.attention_and_adhd"]
    assert "attention" in adhd[0]["topics"]
    assert "adhd" in adhd[0]["topics"]
    assert [row["stable_id"] for row in coding] == [
        "service_bible.coding_preferences"]
    assert mismatched == []


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
        first = runtime.retrieve_service_bible(
            compiled["index"], query="linux systemd")
        second = runtime.retrieve_service_bible(
            compiled["index"], query="linux systemd")
        via_class = runtime.PersonaServiceBibleRetriever(
            _Ctx(ENABLED)).retrieve(query="linux systemd")
        items = runtime.PersonaRuntimeBridge(
            _Ctx(ENABLED)).packet_items("s1", "hello")
        after = _hashes(home)
        token = set_hermes_home_override(profile_b)
        try:
            _write_profile(profile_b)
            mods[2].IdentityStore(_Ctx()).ensure()
            empty = runtime.PersonaServiceBibleRetriever(
                _Ctx(ENABLED)).retrieve(query="linux systemd")
        finally:
            reset_hermes_home_override(token)
    finally:
        mods[0].unload()
    assert first == second == via_class
    assert before == after
    assert empty == []
    assert len(items) == 1
    assert "§§3-90" in items[0].content
    assert "§41 memory guard" in items[0].content
    assert "must not override" in items[0].content
    assert "§42 service" in items[0].content
    assert "retrieved" in items[0].content
    assert "selectively" in items[0].content
    # The packet names the contracts only — never canonical
    # persona text or authored anchor prose.
    assert "longhouse terminal" not in items[0].content
    assert "does not command" not in items[0].content
