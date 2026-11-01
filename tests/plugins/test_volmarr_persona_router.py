"""Contracts for the persona router (Slice 123).

Persona Runtime roadmap §14 (PersonaRouter): the router
determines which persona modules matter, from the user
message, current task, active project, tool intent, and
conversation state, and outputs the required persona
sections — e.g. task ``code_generation`` requiring
``core.execution`` + ``service_bible.coding_preferences`` +
``service_bible.dependencies`` + ``tool_policy.filesystem``.
Routing here is a deterministic decision layer over the
§13 retrieval scores: per-tag coverage first, retrieval
fill second, under a hard cap. Tests load through real
plugin discovery.
"""

from __future__ import annotations

import hashlib
import importlib
from pathlib import Path

import yaml

from hermes_constants import (
    get_hermes_home,
    reset_hermes_home_override,
    set_hermes_home_override,
)

ENABLED = {"persona_runtime_enabled": True}

CORE_DOC = """# Core Identity

I am Caducea, a persistent Hermes entity.

# Execution

Execute code carefully, in small verified steps.

# Communication Style

Speak warmly and plainly.
"""

SERVICE_DOC = """# Coding Preferences

Write coding work carefully: refactor code in small steps,
run tests, and keep git history clean.

# Dependencies

Pin dependencies with upper bounds; never add a dependency
without checking its licence.

# Opensource Values

Share code openly.
"""

TOOL_DOC = """# Filesystem

Read files before editing them; write only inside the
project directory.

# Git Policy

Use git branches for work; never force push a branch.

# Remote Git Operations

Remote git push operations need care and reversibility.

# Reversibility

Prefer reversible changes; every remote push should be
reversible.
"""

REL_DOC = """# When Caducea Disagrees

Offer counsel once, then accept the decision.
"""

AVATAR_DOC = """# Visual Identity

Raven hair, pale eyes.
"""

DOCS = {
    "core": ("core.md", CORE_DOC),
    "service_bible": ("bible.md", SERVICE_DOC),
    "tool_policy": ("tools.md", TOOL_DOC),
    "relationship": ("rel.md", REL_DOC),
    "avatar": ("avatar.md", AVATAR_DOC),
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


def _write_persona(home: Path, docs=None) -> None:
    persona_dir = home / "persona"
    persona_dir.mkdir(parents=True, exist_ok=True)
    chosen = docs or DOCS
    for role, (name, text) in chosen.items():
        (persona_dir / name).write_text(text, encoding="utf-8")
    documents = {
        role: {"file": chosen[role][0], "required": True}
        for role in chosen
    }
    config = {"persona": {
        "id": "caducea",
        "display_name": "Caducea Hermesdottir",
        "directory": "./persona",
        "documents": documents,
    }}
    config_dir = home / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "persona.yaml").write_text(
        yaml.safe_dump(config, sort_keys=False), encoding="utf-8")


def _hashes(home: Path) -> dict[str, str]:
    return {
        str(path.relative_to(home)):
            hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(home.rglob("*"))
        if path.is_file() and "entity" not in path.parts
    }


def _compile(runtime):
    return runtime.PersonaCompiler(_Ctx(ENABLED)).compile()


def test_route_task_label_rules():
    mods = _load_modules()
    runtime = mods[1]
    try:
        # An explicit current task wins, slugified.
        assert runtime.route_task_label(
            "code_generation", ["git"]) == "code_generation"
        assert runtime.route_task_label(
            "Code Generation", []) == "code_generation"
        # Placeholders do not win; tags name the task.
        assert runtime.route_task_label(
            "general", ["git", "coding"]) == "code_generation"
        assert runtime.route_task_label("", ["git"]) == "git_operations"
        assert runtime.route_task_label(
            "", ["relationship"]) == "relationship_counsel"
        assert runtime.route_task_label("", []) == "general"
        assert runtime.router_inputs() == [
            "user_message", "current_task", "active_project",
            "tool_intent", "conversation_state"]
    finally:
        mods[0].unload()


def test_router_loads_the_roadmap_code_generation_example():
    mods = _load_modules()
    runtime = mods[1]
    try:
        _write_persona(get_hermes_home())
        compiled = _compile(runtime)
        route = runtime.route_sections(
            compiled["index"],
            user_message="Generate code for the new exporter",
            current_task="code_generation",
            tool_intent="filesystem")
    finally:
        mods[0].unload()
    assert route["task"] == "code_generation"
    assert "coding" in route["task_tags"]
    assert "filesystem" in route["task_tags"]
    assert route["inputs_present"] == [
        "user_message", "current_task", "tool_intent"]
    # The §14 example's required set, in the example's shape.
    for stable_id in (
            "core.execution", "service_bible.coding_preferences",
            "service_bible.dependencies", "tool_policy.filesystem"):
        assert stable_id in route["required"]
    assert route["persona_context"] == route["required"]
    # Unrelated persona material is not required.
    assert "avatar.visual_identity" not in route["required"]
    # Every required section carries its reasons and score:
    # the tags that required it, or an explicit retrieval
    # marker when keyword contact alone required it.
    for row in route["sections"]:
        assert row["task_tags"] or row["via_retrieval"]
        assert row["score"]["semantic"] is None
        assert 0.0 < row["score"]["total"] <= 1.0
    coding_rows = {
        row["stable_id"] for row in route["sections"]
        if "coding" in row["task_tags"]}
    assert "service_bible.coding_preferences" in coding_rows


def test_router_covers_every_classified_tag():
    mods = _load_modules()
    runtime = mods[1]
    try:
        _write_persona(get_hermes_home())
        compiled = _compile(runtime)
        route = runtime.route_sections(
            compiled["index"],
            user_message="Refactor my Hermes Git branch and push it")
    finally:
        mods[0].unload()
    assert route["task"] == "code_generation"  # coding precedes git
    for stable_id in (
            "service_bible.coding_preferences", "tool_policy.git_policy",
            "tool_policy.remote_git_operations",
            "tool_policy.reversibility"):
        assert stable_id in route["required"]
    git_rows = {
        row["stable_id"] for row in route["sections"]
        if "git" in row["task_tags"]}
    assert "tool_policy.git_policy" in git_rows


def test_router_uses_project_and_conversation_inputs():
    mods = _load_modules()
    runtime = mods[1]
    try:
        _write_persona(get_hermes_home())
        compiled = _compile(runtime)
        route = runtime.route_sections(
            compiled["index"], user_message="hello there",
            active_project="git repository cleanup",
            conversation_state="we disagreed about the last decision")
    finally:
        mods[0].unload()
    # Neither the project nor the conversation text is in the
    # user message, yet both shape the route.
    assert route["inputs_present"] == [
        "user_message", "active_project", "conversation_state"]
    assert "git" in route["task_tags"]
    assert "relationship" in route["task_tags"]
    assert "tool_policy.git_policy" in route["required"]
    assert "relationship.when_caducea_disagrees" in route["required"]


def test_router_empty_signals_and_bounds():
    mods = _load_modules()
    runtime = mods[1]
    try:
        _write_persona(get_hermes_home())
        compiled = _compile(runtime)
        index = compiled["index"]
        empty = runtime.route_sections(index)
        assert empty["task"] == "general"
        assert empty["required"] == [] and empty["sections"] == []
        assert runtime.route_sections(
            index, user_message="zzzqqq unknownword")["required"] == []
        capped = runtime.route_sections(
            index, user_message="Refactor my Git branch and push it",
            limit=2)
        assert len(capped["required"]) == 2
        clamped = runtime.route_sections(
            index, user_message="Refactor my Git branch and push it",
            limit=999)
        assert len(clamped["required"]) <= runtime.ROUTER_MAX_LIMIT
        # Deterministic across calls.
        again = runtime.route_sections(
            index, user_message="Refactor my Git branch and push it",
            limit=999)
        assert clamped == again
    finally:
        mods[0].unload()


def test_router_service_deterministic_writes_nothing():
    mods = _load_modules()
    runtime = mods[1]
    try:
        mods[2].IdentityStore(_Ctx()).ensure()
        home = get_hermes_home()
        _write_persona(home)
        before = _hashes(home)
        router = runtime.PersonaRouter(_Ctx(ENABLED))
        first = router.route(
            user_message="Generate code for the new exporter",
            current_task="code_generation", tool_intent="filesystem")
        second = router.route(
            user_message="Generate code for the new exporter",
            current_task="code_generation", tool_intent="filesystem")
        items = runtime.PersonaRuntimeBridge(
            _Ctx(ENABLED)).packet_items("s1", "hello")
        after = _hashes(home)
    finally:
        mods[0].unload()
    assert first == second
    assert first["persona_id"] == "caducea"
    assert "core.execution" in first["required"]
    assert before == after
    assert len(items) == 1
    assert "§§3-44" in items[0].content
    assert "§14 routing" in items[0].content
    assert "persistent Hermes entity" not in items[0].content


def test_router_without_persona_config_routes_empty():
    mods = _load_modules()
    runtime = mods[1]
    try:
        route = runtime.PersonaRouter(_Ctx(ENABLED)).route(
            user_message="Refactor my Git branch",
            current_task="code_generation")
    finally:
        mods[0].unload()
    assert route["persona_id"] is None
    assert route["task"] == "code_generation"
    assert route["required"] == []


def test_profile_isolation(tmp_path):
    profile_b = tmp_path / "profile-b"
    mods = _load_modules()
    runtime = mods[1]
    try:
        mods[2].IdentityStore(_Ctx()).ensure()
        _write_persona(get_hermes_home())
        assert runtime.PersonaRouter(_Ctx(ENABLED)).route(
            user_message="Refactor my Git branch")["required"]
        token = set_hermes_home_override(profile_b)
        try:
            _write_profile(profile_b)
            mods[2].IdentityStore(_Ctx()).ensure()
            route_b = runtime.PersonaRouter(_Ctx(ENABLED)).route(
                user_message="Refactor my Git branch")
        finally:
            reset_hermes_home_override(token)
    finally:
        mods[0].unload()
    assert route_b["persona_id"] is None
    assert route_b["required"] == []
