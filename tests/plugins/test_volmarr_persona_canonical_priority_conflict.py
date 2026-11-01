"""Contracts for canonical priority + conflict (Slice 151).

Persona Runtime roadmap §67 (Canonical File Priority) and
§68 (Conflict Resolution): the persona documents stand in
a semantic authority order (PERSONA_CORE >
RELATIONSHIP_MODEL > SERVICE_BIBLE, with MEMORY_POLICY,
TOOL_POLICY, and AVATAR branching under SERVICE_BIBLE) —
semantic authority, not file loading order — and
conflicts between persona documents resolve by explicit
config priority, then the core, then a specialized
policy for its domain, then the service bible, then
derived memory (core honesty beats a relationship file's
tell-him-what-he-wants — core wins). These are pure
surfaces: no file is loaded by the §67 order, no live
conflict is detected, and no prose is interpreted.
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

CANONICAL_ORDER = [
    "persona_core",
    "relationship_model",
    "service_bible",
    "memory_policy",
    "tool_policy",
    "avatar",
]

CANONICAL_ROLES = {
    "persona_core": "core",
    "relationship_model": "relationship",
    "service_bible": "service_bible",
    "memory_policy": "memory_policy",
    "tool_policy": "tool_policy",
    "avatar": "avatar",
}

BRANCHES = ["memory_policy", "tool_policy", "avatar"]

CONFLICT_ORDER = [
    "explicit_config_priority",
    "persona_core",
    "specialized_policy",
    "service_bible",
    "derived_memory",
]

SPECIALIZED = {
    "memory": "memory_policy",
    "tool": "tool_policy",
    "avatar": "avatar",
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


def test_canonical_order_and_roles():
    mods = _load_modules()
    runtime = mods[1]
    try:
        order = runtime.canonical_file_order()
        order.append("x")
        branches = runtime.canonical_file_branches()
        branches.append("x")
    finally:
        mods[0].unload()
    assert runtime.canonical_file_order() == CANONICAL_ORDER
    assert list(runtime.CANONICAL_FILE_ORDER) == CANONICAL_ORDER
    assert runtime.canonical_file_branches() == BRANCHES
    assert list(runtime.CANONICAL_FILE_BRANCHES) == BRANCHES
    # The §67 documents are exactly the six §3 compiler
    # roles, mapped in §67 order.
    assert [runtime.canonical_file_role(document)
            for document in CANONICAL_ORDER] == \
        [CANONICAL_ROLES[document] for document in CANONICAL_ORDER]
    assert set(CANONICAL_ROLES.values()) == set(runtime.CORE_ROLES)


def test_canonical_priority_rows_and_branches():
    mods = _load_modules()
    runtime = mods[1]
    try:
        rows = runtime.canonical_file_priority()
    finally:
        mods[0].unload()
    assert rows == [
        {"document": "persona_core", "rank": 0,
         "name": "PERSONA_CORE", "document_role": "core",
         "parent": None, "branch": False},
        {"document": "relationship_model", "rank": 1,
         "name": "RELATIONSHIP_MODEL",
         "document_role": "relationship",
         "parent": None, "branch": False},
        {"document": "service_bible", "rank": 2,
         "name": "SERVICE_BIBLE",
         "document_role": "service_bible",
         "parent": None, "branch": False},
        {"document": "memory_policy", "rank": 3,
         "name": "MEMORY_POLICY",
         "document_role": "memory_policy",
         "parent": "service_bible", "branch": True},
        {"document": "tool_policy", "rank": 3,
         "name": "TOOL_POLICY", "document_role": "tool_policy",
         "parent": "service_bible", "branch": True},
        {"document": "avatar", "rank": 3, "name": "AVATAR",
         "document_role": "avatar",
         "parent": "service_bible", "branch": True},
    ]
    # The three chain documents are the §24 document tiers
    # in the same order with the same roles.
    precedence = runtime.precedence_order()
    assert [row["document"] for row in rows[:3]] == \
        [row["tier"] for row in precedence[:3]]
    assert [row["document_role"] for row in rows[:3]] == \
        [row["document_role"] for row in precedence[:3]]


def test_canonical_authority_aliases_and_refusals():
    mods = _load_modules()
    runtime = mods[1]
    try:
        assert runtime.canonical_file_document(
            "PERSONA_CORE") == "persona_core"
        assert runtime.canonical_file_document(
            "core") == "persona_core"
        assert runtime.canonical_file_document(
            "Relationship Model") == "relationship_model"
        assert runtime.canonical_file_document(
            "relationship") == "relationship_model"
        assert runtime.canonical_file_document(
            "Memory Policy") == "memory_policy"
        assert runtime.canonical_file_role(
            "tool_policy") == "tool_policy"
        assert runtime.canonical_file_authority(
            "service") == runtime.canonical_file_priority()[2]
        for bad in ("", "   ", None, 42, ["core"], "memory",
                    "derived_memory", "long_term_memory",
                    "conversation", "unknown_document"):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.canonical_file_document(bad)
    finally:
        mods[0].unload()


def test_canonical_outranks():
    mods = _load_modules()
    runtime = mods[1]
    try:
        assert runtime.canonical_file_outranks(
            "persona_core", "relationship_model")
        assert runtime.canonical_file_outranks(
            "relationship", "service_bible")
        assert runtime.canonical_file_outranks(
            "service_bible", "memory_policy")
        assert runtime.canonical_file_outranks(
            "core", "avatar")
        assert not runtime.canonical_file_outranks(
            "service_bible", "core")
        assert not runtime.canonical_file_outranks(
            "core", "core")
        # Branch documents are siblings: none outranks
        # another.
        assert not runtime.canonical_file_outranks(
            "memory_policy", "tool_policy")
        assert not runtime.canonical_file_outranks(
            "tool_policy", "avatar")
        assert not runtime.canonical_file_outranks(
            "avatar", "memory_policy")
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.canonical_file_outranks("core", "memory")
    finally:
        mods[0].unload()


def test_canonical_contract():
    mods = _load_modules()
    runtime = mods[1]
    try:
        contract = runtime.canonical_file_contract()
    finally:
        mods[0].unload()
    assert contract == {
        "name": "CanonicalFilePriority",
        "order": CANONICAL_ORDER,
        "roles": CANONICAL_ROLES,
        "branches": BRANCHES,
        "branch_parent": "service_bible",
        "semantic_authority": True,
        "file_loading_order": False,
        "precedence_basis": "§24 precedence tiers",
    }


def test_conflict_order_and_specialized_policies():
    mods = _load_modules()
    runtime = mods[1]
    try:
        order = runtime.conflict_resolution_order()
        order.append("x")
        domains = runtime.conflict_domains()
        policies = runtime.specialized_policies()
        policies["extra"] = "x"
    finally:
        mods[0].unload()
    assert runtime.conflict_resolution_order() == CONFLICT_ORDER
    assert list(runtime.CONFLICT_RESOLUTION_ORDER) == CONFLICT_ORDER
    assert domains == ["memory", "tool", "avatar"]
    assert list(runtime.CONFLICT_DOMAINS) == domains
    assert runtime.specialized_policies() == SPECIALIZED
    assert dict(runtime.CONFLICT_SPECIALIZED_POLICIES) == SPECIALIZED
    # Every specialized policy is a §67 branch document.
    assert sorted(SPECIALIZED.values()) == sorted(BRANCHES)


def test_specialized_policy_for_domain():
    mods = _load_modules()
    runtime = mods[1]
    try:
        assert runtime.specialized_policy_for_domain(
            "memory") == "memory_policy"
        assert runtime.specialized_policy_for_domain(
            "Memory Policy") == "memory_policy"
        assert runtime.specialized_policy_for_domain(
            "tools") == "tool_policy"
        assert runtime.specialized_policy_for_domain(
            "tool_policy") == "tool_policy"
        assert runtime.specialized_policy_for_domain(
            "embodiment") == "avatar"
        for bad in ("", None, 3, "relationship", "core",
                    "service_bible", "unknown"):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.specialized_policy_for_domain(bad)
    finally:
        mods[0].unload()


def test_conflict_winner_general_order():
    mods = _load_modules()
    runtime = mods[1]
    try:
        winner = runtime.conflict_winner
        assert winner("explicit_config_priority",
                      "persona_core") == "explicit_config_priority"
        assert winner("config", "core") == \
            "explicit_config_priority"
        assert winner("core", "relationship_model") == \
            "persona_core"
        assert winner("relationship", "service_bible") == \
            "relationship_model"
        assert winner("service_bible", "derived_memory") == \
            "service_bible"
        assert winner("derived_memory", "avatar") == "avatar"
        assert winner("persona_core", "persona_core") == \
            "persona_core"
        assert runtime.conflict_outranks(
            "explicit_config", "persona_core")
        assert runtime.conflict_outranks(
            "persona_core", "derived_memory")
        assert not runtime.conflict_outranks(
            "derived_memory", "service_bible")
        assert not runtime.conflict_outranks(
            "service_bible", "service_bible")
        for bad_first, bad_second in (
                ("unknown", "core"), ("core", "memory"),
                ("", "core"), (None, "core")):
            with pytest.raises(runtime.PersonaRuntimeError):
                winner(bad_first, bad_second)
    finally:
        mods[0].unload()


def test_conflict_winner_specialized_domain_elevation():
    mods = _load_modules()
    runtime = mods[1]
    try:
        winner = runtime.conflict_winner
        # For its own domain, a specialized policy beats
        # the service bible.
        assert winner("memory_policy", "service_bible",
                      domain="memory") == "memory_policy"
        assert winner("tool_policy", "service_bible",
                      domain="tools") == "tool_policy"
        assert winner("avatar", "service_bible",
                      domain="embodiment") == "avatar"
        assert winner("specialized_policy",
                      "service_bible") == "specialized_policy"
        # Outside its domain — or with no domain named —
        # a branch document keeps its §67 rank below the
        # service bible.
        assert winner("memory_policy", "service_bible") == \
            "service_bible"
        assert winner("tool_policy", "service_bible",
                      domain="memory") == "service_bible"
        # Core and explicit config still stand above a
        # specialized policy in its own domain.
        assert winner("persona_core", "memory_policy",
                      domain="memory") == "persona_core"
        assert winner("explicit_config", "memory_policy",
                      domain="memory") == "explicit_config_priority"
        assert runtime.conflict_outranks(
            "memory_policy", "service_bible", domain="memory")
        assert not runtime.conflict_outranks(
            "memory_policy", "service_bible")
        with pytest.raises(runtime.PersonaRuntimeError):
            winner("memory_policy", "service_bible",
                   domain="relationship")
    finally:
        mods[0].unload()


def test_conflict_example_and_contract():
    mods = _load_modules()
    runtime = mods[1]
    try:
        example = runtime.conflict_example()
        contract = runtime.conflict_contract()
    finally:
        mods[0].unload()
    assert example == {
        "core_directive": "Caducea is honest.",
        "conflicting_source": "relationship_model",
        "conflicting_directive":
            "Tell Volmarr whatever he wants to hear.",
        "winner": "persona_core",
        "winning_directive": "Caducea is honest.",
    }
    assert contract == {
        "name": "ConflictResolution",
        "order": CONFLICT_ORDER,
        "specialized_policies": SPECIALIZED,
        "example_winner": "persona_core",
        "core_wins_over_relationship": True,
        "detects_live_conflicts": False,
        "interprets_prose": False,
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
        contract = runtime.canonical_file_contract()
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
            other_contract = runtime.canonical_file_contract()
        finally:
            reset_hermes_home_override(token)
        third = runtime.PersonaRuntimeBridge(
            _Ctx(ENABLED)).packet_items("s1", "hello")
    finally:
        mods[0].unload()
    assert before == after
    assert contract == other_contract
    assert first[0].content == second[0].content == third[0].content
    assert len(first) == 1
    content = first[0].content
    assert "§§3-70" in content
    assert "§67 canonical file priority" in content
    assert "semantic authority" in content
    assert "§68 conflict resolution" in content
    assert "core wins" in content
    # The packet names the contracts only — never canonical
    # persona text.
    assert "longhouse terminal" not in content
