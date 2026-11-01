"""Contracts for multi-persona support + memory namespace (Slice 156).

Persona Runtime roadmap §77 (Multi-Persona Support) and
§78 (Memory Namespace): several personas stand side by
side under one ``personas/`` root — the roadmap's layout
names caducea, runa, yrsa, and another_agent — the
config chooses one ``active_persona``, and each persona
is independent in documents, kernel, memory namespace,
relationship state, avatar, and compiled index; and
autobiographical memory is keyed ``persona:<id>:...``
per persona and never mixed across personas, with
shared world knowledge keyed separately. Both surfaces
are pure records / key functions here: no persona is
loaded or activated, and no memory store is owned, read,
or written. Tests load through real plugin discovery.
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

# Graceful Deference

Caducea defers gracefully when Volmarr decides.
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

EXAMPLES = ["caducea", "runa", "yrsa", "another_agent"]
FACETS = [
    "documents", "kernel", "memory_namespace",
    "relationship_state", "avatar", "compiled_index",
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


def test_multi_persona_examples_facets_and_directory():
    mods = _load_modules()
    runtime = mods[1]
    try:
        examples = runtime.multi_persona_examples()
        examples.append("x")
        facets = runtime.persona_independent_facets()
        facets.append("x")
    finally:
        mods[0].unload()
    assert list(runtime.MULTI_PERSONA_EXAMPLES) == EXAMPLES
    assert list(runtime.PERSONA_INDEPENDENT_FACETS) == FACETS
    assert runtime.PERSONAS_ROOT == "personas"
    assert runtime.persona_directory("caducea") == "personas/caducea"
    assert runtime.persona_directory("yrsa") == "personas/yrsa"
    with pytest.raises(runtime.PersonaRuntimeError):
        runtime.persona_directory("Not A Slug")
    with pytest.raises(runtime.PersonaRuntimeError):
        runtime.persona_directory(None)


def test_roster_example_and_active_choice():
    mods = _load_modules()
    runtime = mods[1]
    try:
        roster = runtime.multi_persona_example()
        plain = runtime.multi_persona_roster(["caducea", "runa"])
    finally:
        mods[0].unload()
    assert roster["root"] == "personas"
    assert roster["active_persona"] == "caducea"
    assert roster["count"] == 4
    assert [entry["persona_id"] for entry in roster["personas"]] \
        == EXAMPLES
    assert roster["personas"][0] == {
        "persona_id": "caducea",
        "directory": "personas/caducea",
        "active": True,
        "independent": FACETS,
        "memory_namespace_prefix": "persona:caducea:",
    }
    assert all(
        entry["active"] is False for entry in roster["personas"][1:])
    assert all(
        entry["independent"] == FACETS for entry in roster["personas"])
    assert plain["active_persona"] is None
    assert all(
        entry["active"] is False for entry in plain["personas"])


def test_roster_refusals():
    mods = _load_modules()
    runtime = mods[1]
    try:
        for args, kwargs in (
                (([],), {}),
                ((["caducea", "caducea"],), {}),
                ((["Not A Slug"],), {}),
                (([7],), {}),
                (([f"p{i}" for i in range(33)],), {}),
                ((["caducea"],), {"active_persona": "runa"}),
                ((["caducea"],), {"active_persona": "Not A Slug"}),
                ((["caducea"],), {"active_persona": 7}),
        ):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.multi_persona_roster(*args, **kwargs)
    finally:
        mods[0].unload()


def test_validate_roster_round_trip_and_tamper():
    mods = _load_modules()
    runtime = mods[1]
    try:
        roster = runtime.multi_persona_example()
        checked = runtime.validate_multi_persona_roster(roster)
        tampered = []
        bad = dict(roster); bad["count"] = 99
        tampered.append(bad)
        bad = dict(roster); bad["root"] = "elsewhere"
        tampered.append(bad)
        bad = dict(roster); bad["active_persona"] = "runa"
        tampered.append(bad)
        bad = dict(roster); bad["extra"] = True
        tampered.append(bad)
        bad = dict(roster)
        bad["personas"] = [dict(entry) for entry in roster["personas"]]
        bad["personas"][1]["directory"] = "personas/elsewhere"
        tampered.append(bad)
        bad = dict(roster)
        bad["personas"] = [dict(entry) for entry in roster["personas"]]
        bad["personas"][1]["active"] = True
        tampered.append(bad)
        bad = dict(roster)
        bad["personas"] = [dict(entry) for entry in roster["personas"]]
        bad["personas"][0]["independent"] = ["documents"]
        tampered.append(bad)
        for record in tampered + [None, "roster", []]:
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.validate_multi_persona_roster(record)
    finally:
        mods[0].unload()
    assert checked == roster
    assert checked is not roster


def test_memory_namespace_builders():
    mods = _load_modules()
    runtime = mods[1]
    try:
        prefix = runtime.memory_namespace_prefix("caducea")
        key = runtime.memory_namespace("caducea", "episodic", "2026")
        shared = runtime.shared_memory_namespace("world", "aesir")
        examples = runtime.memory_namespace_examples()
    finally:
        mods[0].unload()
    assert prefix == "persona:caducea:"
    assert key == "persona:caducea:episodic:2026"
    assert shared == "shared:world:aesir"
    assert examples == [
        "persona:caducea:", "persona:runa:", "persona:yrsa:"]
    assert runtime.MEMORY_NAMESPACE_KIND == "persona"
    assert runtime.SHARED_MEMORY_KIND == "shared"


def test_memory_namespace_builder_refusals():
    mods = _load_modules()
    runtime = mods[1]
    try:
        for call in (
                lambda: runtime.memory_namespace("caducea"),
                lambda: runtime.memory_namespace("Not A Slug", "x"),
                lambda: runtime.memory_namespace("caducea", "Bad Seg"),
                lambda: runtime.memory_namespace("caducea", ""),
                lambda: runtime.memory_namespace(
                    "caducea", *[f"s{i}" for i in range(9)]),
                lambda: runtime.shared_memory_namespace(),
                lambda: runtime.shared_memory_namespace("Bad Seg"),
                lambda: runtime.memory_namespace_prefix(""),
        ):
            with pytest.raises(runtime.PersonaRuntimeError):
                call()
    finally:
        mods[0].unload()


def test_parse_and_owner():
    mods = _load_modules()
    runtime = mods[1]
    try:
        parsed = runtime.parse_memory_namespace(
            "persona:runa:episodic:childhood")
        shared = runtime.parse_memory_namespace("shared:world:aesir")
        owners = (
            runtime.memory_namespace_owner("persona:yrsa:notes"),
            runtime.memory_namespace_owner("shared:world"),
        )
        for bad in ("persona:caducea:", "persona:caducea",
                    "other:caducea:x", "shared:", "",
                    "persona:Not A Slug:x", None, 7):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.parse_memory_namespace(bad)
    finally:
        mods[0].unload()
    assert parsed == {
        "kind": "persona",
        "persona_id": "runa",
        "segments": ["episodic", "childhood"],
        "key": "persona:runa:episodic:childhood",
    }
    assert shared == {
        "kind": "shared",
        "persona_id": None,
        "segments": ["world", "aesir"],
        "key": "shared:world:aesir",
    }
    assert owners == ("yrsa", "shared")


def test_memory_namespaces_mixed():
    mods = _load_modules()
    runtime = mods[1]
    try:
        same = runtime.memory_namespaces_mixed(
            ["persona:caducea:a", "persona:caducea:b"])
        with_shared = runtime.memory_namespaces_mixed(
            ["persona:caducea:a", "shared:world"])
        mixed = runtime.memory_namespaces_mixed(
            ["persona:caducea:a", "persona:runa:b"])
        empty = runtime.memory_namespaces_mixed([])
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.memory_namespaces_mixed(["bogus"])
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.memory_namespaces_mixed("persona:caducea:a")
    finally:
        mods[0].unload()
    assert same is False
    assert with_shared is False
    assert mixed is True
    assert empty is False


def test_multi_and_namespace_contracts():
    mods = _load_modules()
    runtime = mods[1]
    try:
        multi = runtime.multi_persona_contract()
        namespace = runtime.memory_namespace_contract()
    finally:
        mods[0].unload()
    assert multi == {
        "name": "MultiPersonaSupport",
        "root": "personas",
        "examples": EXAMPLES,
        "example": runtime.multi_persona_example(),
        "config_key": "active_persona",
        "independent_facets": FACETS,
        "max_personas": 32,
        "loads_personas": False,
        "activates_persona": False,
    }
    assert namespace == {
        "name": "MemoryNamespace",
        "persona_key_form": "persona:<persona_id>:...",
        "examples": [
            "persona:caducea:", "persona:runa:", "persona:yrsa:"],
        "shared_kind": "shared",
        "shared_separate": True,
        "never_mix_autobiographical": True,
        "max_segments": 8,
        "owns_memory_store": False,
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
        roster = runtime.multi_persona_example()
        key = runtime.memory_namespace("caducea", "episodic")
        first = runtime.PersonaRuntimeBridge(
            _Ctx(ENABLED)).packet_items("s1", "hello")
        second = runtime.PersonaRuntimeBridge(
            _Ctx(ENABLED)).packet_items("s1", "hello")
        after = _hashes(home)
        token = set_hermes_home_override(str(profile_b))
        try:
            _write_profile(profile_b)
            mods[2].IdentityStore(_Ctx()).ensure()
            _write_persona(
                profile_b, persona_id="other",
                core_doc=OTHER_CORE_DOC)
            other_roster = runtime.multi_persona_example()
        finally:
            reset_hermes_home_override(token)
        third = runtime.PersonaRuntimeBridge(
            _Ctx(ENABLED)).packet_items("s1", "hello")
    finally:
        mods[0].unload()
    assert before == after
    assert roster == other_roster
    assert key == "persona:caducea:episodic"
    assert first[0].content == second[0].content == third[0].content
    assert len(first) == 1
    content = first[0].content
    assert "§§3-92" in content
    assert "§77 multi-persona support" in content
    assert "§78 memory namespace" in content
    assert "never mixed" in content
    # The packet names the contracts only — never canonical
    # persona text.
    assert "longhouse terminal" not in content
