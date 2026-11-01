"""Contracts for shared knowledge + persona bootstrap (Slice 157).

Persona Runtime roadmap §79 (Shared Knowledge vs Personal
Memory) and §80 (Persona Bootstrap): knowledge classified
over the §78 namespace kinds — ``shared:`` keys are shared
world knowledge visible to every persona (Project Aesir
architecture), ``persona:<id>:...`` keys are that persona's
private memory visible to its owner alone (Caducea's
reflections on designing it with Volmarr; Runa's own
interaction history) — and a new persona's bootstrap plan
names ``persona.yaml`` plus the six §3-role documents in
roadmap order, their names freely changeable in
configuration. Both surfaces are pure here: no memory
store is owned, read, or written, and no persona is
created and no file is written. Tests load through real
plugin discovery.
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

BOOTSTRAP_FILES = [
    {"file": "persona.yaml", "kind": "config", "role": None},
    {"file": "PERSONA_CORE.md", "kind": "document", "role": "core"},
    {"file": "SERVICE_BIBLE.md", "kind": "document",
     "role": "service_bible"},
    {"file": "MEMORY_POLICY.md", "kind": "document",
     "role": "memory_policy"},
    {"file": "TOOL_POLICY.md", "kind": "document",
     "role": "tool_policy"},
    {"file": "RELATIONSHIP_MODEL.md", "kind": "document",
     "role": "relationship"},
    {"file": "AVATAR.md", "kind": "document", "role": "avatar"},
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


def test_knowledge_kinds_and_classify_shared():
    mods = _load_modules()
    runtime = mods[1]
    try:
        kinds = runtime.knowledge_kinds()
        kinds.append("x")
        shared = runtime.classify_knowledge_key(
            "shared:project_aesir:architecture")
    finally:
        mods[0].unload()
    assert list(runtime.KNOWLEDGE_KINDS) == [
        "shared", "persona_private"]
    assert shared == {
        "key": "shared:project_aesir:architecture",
        "kind": "shared",
        "owner": "shared",
        "persona_id": None,
        "segments": ["project_aesir", "architecture"],
    }


def test_classify_private_owner_is_exact():
    mods = _load_modules()
    runtime = mods[1]
    try:
        caducea = runtime.classify_knowledge_key(
            "persona:caducea:reflections:project_aesir")
        runa = runtime.classify_knowledge_key(
            "persona:runa:interaction_history")
    finally:
        mods[0].unload()
    assert caducea["kind"] == "persona_private"
    assert caducea["owner"] == "caducea"
    assert caducea["persona_id"] == "caducea"
    # One persona's private item is never another's, and
    # never shared.
    assert runa["owner"] == "runa"
    assert runa["kind"] != "shared"
    assert caducea["owner"] != runa["owner"]


def test_classify_refusals():
    mods = _load_modules()
    runtime = mods[1]
    try:
        for bad in ("persona:caducea:", "other:caducea:x",
                    "shared:", "", None, 7,
                    "persona:Not A Slug:x"):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.classify_knowledge_key(bad)
    finally:
        mods[0].unload()


def test_knowledge_record_title_never_reclassifies():
    mods = _load_modules()
    runtime = mods[1]
    try:
        # A shared key titled like a private reflection
        # stays shared; a persona key titled like the
        # shared example stays that persona's private.
        shared = runtime.knowledge_record(
            "shared:project_aesir:architecture",
            "Her reflections on designing it with Volmarr")
        private = runtime.knowledge_record(
            "persona:caducea:reflections:project_aesir",
            "Project Aesir architecture")
        for bad_title in ("", "   ", "x" * 241, None, 7):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.knowledge_record(
                    "shared:world", bad_title)
    finally:
        mods[0].unload()
    assert shared["kind"] == "shared"
    assert shared["owner"] == "shared"
    assert private["kind"] == "persona_private"
    assert private["owner"] == "caducea"


def test_validate_knowledge_record_round_trip_and_tamper():
    mods = _load_modules()
    runtime = mods[1]
    try:
        record = runtime.knowledge_record(
            "persona:runa:interaction_history",
            "Her own interaction history")
        checked = runtime.validate_knowledge_record(record)
        tampered = []
        bad = dict(record); bad["kind"] = "shared"
        tampered.append(bad)
        bad = dict(record); bad["owner"] = "caducea"
        tampered.append(bad)
        bad = dict(record); bad["persona_id"] = None
        tampered.append(bad)
        bad = dict(record); bad["segments"] = ["elsewhere"]
        tampered.append(bad)
        bad = dict(record); bad["extra"] = True
        tampered.append(bad)
        for item in tampered + [None, "record", []]:
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.validate_knowledge_record(item)
    finally:
        mods[0].unload()
    assert checked == record
    assert checked is not record


def test_knowledge_visible_to_and_owner_matches():
    mods = _load_modules()
    runtime = mods[1]
    try:
        shared_key = "shared:project_aesir:architecture"
        private_key = "persona:caducea:reflections:project_aesir"
        results = (
            runtime.knowledge_visible_to(shared_key, "runa"),
            runtime.knowledge_visible_to(shared_key, "yrsa"),
            runtime.knowledge_visible_to(private_key, "caducea"),
            runtime.knowledge_visible_to(private_key, "runa"),
            runtime.knowledge_owner_matches(private_key, "caducea"),
            runtime.knowledge_owner_matches(private_key, "runa"),
            runtime.knowledge_owner_matches(shared_key, "caducea"),
        )
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.knowledge_visible_to(private_key, "Not A Slug")
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.knowledge_visible_to("bogus", "caducea")
    finally:
        mods[0].unload()
    assert results == (True, True, True, False, True, False, False)


def test_partition_knowledge():
    mods = _load_modules()
    runtime = mods[1]
    try:
        part = runtime.partition_knowledge([
            "shared:project_aesir:architecture",
            "persona:caducea:reflections:project_aesir",
            "persona:runa:interaction_history",
            "persona:caducea:notes",
            "shared:project_aesir:architecture",
            "shared:world:geography",
        ])
        empty = runtime.partition_knowledge([])
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.partition_knowledge(["bogus:key"])
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.partition_knowledge("shared:world")
    finally:
        mods[0].unload()
    assert part == {
        "shared": [
            "shared:project_aesir:architecture",
            "shared:world:geography",
        ],
        "persona_private": {
            "caducea": [
                "persona:caducea:reflections:project_aesir",
                "persona:caducea:notes",
            ],
            "runa": ["persona:runa:interaction_history"],
        },
    }
    assert empty == {"shared": [], "persona_private": {}}


def test_knowledge_example_verbatim():
    mods = _load_modules()
    runtime = mods[1]
    try:
        example = runtime.knowledge_example()
    finally:
        mods[0].unload()
    assert example == [
        {
            "key": "shared:project_aesir:architecture",
            "title": "Project Aesir architecture",
            "kind": "shared",
            "owner": "shared",
            "persona_id": None,
            "segments": ["project_aesir", "architecture"],
        },
        {
            "key": "persona:caducea:reflections:project_aesir",
            "title": "Her reflections on designing it with Volmarr",
            "kind": "persona_private",
            "owner": "caducea",
            "persona_id": "caducea",
            "segments": ["reflections", "project_aesir"],
        },
        {
            "key": "persona:runa:interaction_history",
            "title": "Her own interaction history",
            "kind": "persona_private",
            "owner": "runa",
            "persona_id": "runa",
            "segments": ["interaction_history"],
        },
    ]


def test_bootstrap_files_and_role_mapping():
    mods = _load_modules()
    runtime = mods[1]
    try:
        files = runtime.bootstrap_files()
        files.append({"file": "x", "kind": "x", "role": "x"})
        roles = (
            runtime.bootstrap_document_role("persona.yaml"),
            runtime.bootstrap_document_role("PERSONA_CORE.md"),
            runtime.bootstrap_document_role("RELATIONSHIP_MODEL.md"),
            runtime.bootstrap_file_for_role("core"),
            runtime.bootstrap_file_for_role("avatar"),
        )
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.bootstrap_document_role("UNKNOWN.md")
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.bootstrap_file_for_role("config")
    finally:
        mods[0].unload()
    assert runtime.bootstrap_files() == BOOTSTRAP_FILES
    assert list(runtime.BOOTSTRAP_DOCUMENTS) == [
        ("core", "PERSONA_CORE.md"),
        ("service_bible", "SERVICE_BIBLE.md"),
        ("memory_policy", "MEMORY_POLICY.md"),
        ("tool_policy", "TOOL_POLICY.md"),
        ("relationship", "RELATIONSHIP_MODEL.md"),
        ("avatar", "AVATAR.md"),
    ]
    assert runtime.BOOTSTRAP_CONFIG_FILE == "persona.yaml"
    assert roles == (None, "core", "relationship",
                     "PERSONA_CORE.md", "AVATAR.md")


def test_bootstrap_plan_and_validate():
    mods = _load_modules()
    runtime = mods[1]
    try:
        plan = runtime.bootstrap_plan("new_persona")
        unnamed = runtime.bootstrap_plan()
        checked = runtime.validate_bootstrap_plan(plan)
        tampered = []
        bad = dict(plan); bad["creates_persona"] = True
        tampered.append(bad)
        bad = dict(plan); bad["file_count"] = 6
        tampered.append(bad)
        bad = dict(plan)
        bad["files"] = [dict(entry) for entry in plan["files"]]
        bad["files"][1]["file"] = "RENAMED.md"
        tampered.append(bad)
        bad = dict(plan)
        bad["files"] = [dict(entry) for entry in plan["files"]]
        bad["files"][1]["role"] = "avatar"
        tampered.append(bad)
        bad = dict(plan); bad["extra"] = True
        tampered.append(bad)
        for item in tampered + [None, "plan", []]:
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.validate_bootstrap_plan(item)
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.bootstrap_plan("Not A Slug")
    finally:
        mods[0].unload()
    assert checked == plan
    assert checked is not plan
    assert plan["command"] == "hermes persona create"
    assert plan["persona_id"] == "new_persona"
    assert plan["config_file"] == "persona.yaml"
    assert plan["files"] == BOOTSTRAP_FILES
    assert plan["file_count"] == 7
    assert plan["document_count"] == 6
    assert plan["names_changeable_in_configuration"] is True
    assert plan["creates_persona"] is False
    assert plan["writes_files"] is False
    assert unnamed["persona_id"] is None


def test_bootstrap_example_and_contracts():
    mods = _load_modules()
    runtime = mods[1]
    try:
        knowledge = runtime.shared_knowledge_contract()
        bootstrap = runtime.bootstrap_contract()
    finally:
        mods[0].unload()
    assert knowledge == {
        "name": "SharedKnowledgeVsPersonalMemory",
        "kinds": ["shared", "persona_private"],
        "shared_kind": "shared",
        "private_kind": "persona_private",
        "basis": "§78 memory namespace",
        "example": runtime.knowledge_example(),
        "allows_genuine_individuality": True,
        "private_visible_to_owner_only": True,
        "shared_visible_to_all": True,
        "owns_memory_store": False,
    }
    assert bootstrap == {
        "name": "PersonaBootstrap",
        "command": "hermes persona create",
        "plugin_cli_surface": "hermes volmarr",
        "example": {
            "command": "hermes persona create",
            "files": [entry["file"] for entry in BOOTSTRAP_FILES],
            "names_changeable_in_configuration": True,
        },
        "files": BOOTSTRAP_FILES,
        "config_file": "persona.yaml",
        "names_changeable_in_configuration": True,
        "new_core_command": False,
        "creates_persona": False,
        "writes_files": False,
        "basis": "§3 persona config + §49 generated directory",
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
        example = runtime.knowledge_example()
        plan = runtime.bootstrap_plan("caducea")
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
            other_example = runtime.knowledge_example()
        finally:
            reset_hermes_home_override(token)
        third = runtime.PersonaRuntimeBridge(
            _Ctx(ENABLED)).packet_items("s1", "hello")
    finally:
        mods[0].unload()
    assert before == after
    assert example == other_example
    assert plan["document_count"] == 6
    assert first[0].content == second[0].content == third[0].content
    assert len(first) == 1
    content = first[0].content
    assert "§§3-94" in content
    assert "§79 shared knowledge" in content
    assert "§80 persona bootstrap" in content
    assert "Project Aesir architecture is shared" in content
    # The packet names the contracts only — never canonical
    # persona text.
    assert "longhouse terminal" not in content
