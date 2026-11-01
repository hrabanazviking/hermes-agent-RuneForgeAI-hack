"""Contracts for the persona token budgeter (Slice 124).

Persona Runtime roadmap §15 (Token Budgeter): a
PersonaContextBudgeter with suggested budgets — persona
kernel 500-1500, dynamic persona retrieval 300-2500,
relevant memories 500-3000, project state 500-3000
estimated tokens — configurable, with larger allocations
for large-context models and much less for small local
models. Budgeting here is a pure trimming layer over the
§13 retrieval / §14 router outputs plus caller-supplied
memory and project items: whole items only, priority
order, per-category independence. Tests load through real
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


def _item(item_id, category, tokens, priority=0.4, score=0.0):
    return {"id": item_id, "category": category,
            "estimated_tokens": tokens, "priority": priority,
            "score": score}


def test_suggested_budgets_and_context_classes():
    mods = _load_modules()
    runtime = mods[1]
    try:
        assert runtime.budget_categories() == [
            "persona_kernel", "persona_retrieval",
            "relevant_memories", "project_state"]
        assert runtime.suggested_budgets() == {
            "persona_kernel": {"min": 500, "max": 1500},
            "persona_retrieval": {"min": 300, "max": 2500},
            "relevant_memories": {"min": 500, "max": 3000},
            "project_state": {"min": 500, "max": 3000},
        }
        assert runtime.context_classes() == [
            "small_local", "standard", "large"]
        small = runtime.budget_allocations("small_local")
        assert small == {
            "persona_kernel": 500, "persona_retrieval": 300,
            "relevant_memories": 500, "project_state": 500}
        standard = runtime.budget_allocations("standard")
        assert standard == {
            "persona_kernel": 1500, "persona_retrieval": 2500,
            "relevant_memories": 3000, "project_state": 3000}
        large = runtime.budget_allocations("large")
        assert all(large[c] == 2 * standard[c] for c in standard)
        # Configurable per category; the rest stay at class values.
        custom = runtime.budget_allocations(
            "standard", {"persona_retrieval": 42})
        assert custom["persona_retrieval"] == 42
        assert custom["persona_kernel"] == 1500
    finally:
        mods[0].unload()


def test_budget_validation_refusals():
    mods = _load_modules()
    runtime = mods[1]
    try:
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.budget_allocations("huge")
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.budget_allocations("standard", {"nope": 1})
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.budget_allocations("standard", {"persona_kernel": -1})
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.budget_items([_item("x", "nope", 1)])
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.budget_items([_item("x", "persona_kernel", -1)])
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.budget_items([
                _item("x", "persona_kernel", 1),
                _item("x", "persona_kernel", 1)])
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.budget_items([
                _item("x", "persona_kernel", 1, priority=1.5)])
    finally:
        mods[0].unload()


def test_budget_trims_in_priority_order_whole_items_only():
    mods = _load_modules()
    runtime = mods[1]
    try:
        items = [
            _item("low", "persona_retrieval", 100, priority=0.4),
            _item("high", "persona_retrieval", 100, priority=0.9),
            _item("huge", "persona_retrieval", 500, priority=0.8),
            _item("mid", "persona_retrieval", 100, priority=0.6),
        ]
        result = runtime.budget_items(
            items, budgets={"persona_retrieval": 250})
    finally:
        mods[0].unload()
    cat = result["categories"]["persona_retrieval"]
    # Priority order first: high + mid fit; huge is skipped
    # whole (never cut) and low no longer fits either.
    assert cat["included"] == ["high", "mid"]
    assert cat["excluded"] == ["huge", "low"]
    assert cat["used"] == 200 and cat["remaining"] == 50
    assert all(row["reason"] == "over_budget"
               for row in result["excluded"])
    assert result["total_used"] == 200


def test_budget_categories_are_independent_and_deterministic():
    mods = _load_modules()
    runtime = mods[1]
    try:
        items = [
            _item("r1", "persona_retrieval", 400, priority=0.9),
            _item("m1", "relevant_memories", 400, priority=0.9),
            _item("m2", "relevant_memories", 400, priority=0.8),
        ]
        budgets = {"persona_retrieval": 300, "relevant_memories": 500}
        first = runtime.budget_items(items, budgets=budgets)
        second = runtime.budget_items(items, budgets=budgets)
    finally:
        mods[0].unload()
    assert first == second
    # Retrieval overflow does not spend the memories budget.
    assert first["categories"]["persona_retrieval"]["included"] == []
    assert first["categories"]["relevant_memories"]["included"] == ["m1"]
    assert first["categories"]["relevant_memories"]["excluded"] == ["m2"]
    # Untouched categories keep their full standard allocation.
    assert first["categories"]["project_state"]["remaining"] == 3000


def test_budgeter_budgets_kernel_and_route():
    mods = _load_modules()
    runtime = mods[1]
    try:
        _write_persona(get_hermes_home())
        route = runtime.PersonaRouter(_Ctx(ENABLED)).route(
            user_message="Generate code for the new exporter",
            current_task="code_generation", tool_intent="filesystem")
        result = runtime.PersonaContextBudgeter(
            _Ctx(ENABLED)).budget(route=route)
    finally:
        mods[0].unload()
    assert result["persona_id"] == "caducea"
    kernel = result["categories"]["persona_kernel"]
    assert kernel["included"] == ["persona_kernel"]
    assert kernel["used"] > 0
    retrieval = result["categories"]["persona_retrieval"]
    assert retrieval["included"]
    assert set(retrieval["included"]) <= set(route["required"])
    for stable_id in (
            "core.execution", "service_bible.coding_preferences"):
        assert stable_id in retrieval["included"]


def test_budgeter_trims_route_with_small_local_and_overrides():
    mods = _load_modules()
    runtime = mods[1]
    try:
        _write_persona(get_hermes_home())
        budgeter = runtime.PersonaContextBudgeter(_Ctx(ENABLED))
        route = runtime.PersonaRouter(_Ctx(ENABLED)).route(
            user_message="Refactor my Hermes Git branch and push it")
        trimmed = budgeter.budget(
            route=route, budgets={"persona_retrieval": 1})
        full = budgeter.budget(route=route, context_class="large")
    finally:
        mods[0].unload()
    # A 1-token retrieval allocation fits no whole section.
    assert trimmed["categories"]["persona_retrieval"]["included"] == []
    assert trimmed["categories"]["persona_retrieval"]["excluded"]
    # The kernel category is independent of that trim.
    assert trimmed["categories"]["persona_kernel"]["included"] == [
        "persona_kernel"]
    assert full["categories"]["persona_retrieval"]["included"]


def test_budgeter_budgets_caller_memory_and_project_items():
    mods = _load_modules()
    runtime = mods[1]
    try:
        _write_persona(get_hermes_home())
        result = runtime.PersonaContextBudgeter(_Ctx(ENABLED)).budget(
            memories=[
                {"id": "ep1", "text": "x" * 400, "priority": 0.9},
                {"id": "ep2", "estimated_tokens": 2900,
                 "priority": 0.8}],
            project_state=[
                {"id": "proj", "estimated_tokens": 100,
                 "priority": 0.5}],
            budgets={"relevant_memories": 200})
    finally:
        mods[0].unload()
    memories = result["categories"]["relevant_memories"]
    # ep1 estimates to 100 tokens from its text and fits;
    # ep2 does not fit the remaining 100 and is excluded whole.
    assert memories["included"] == ["ep1"]
    assert memories["excluded"] == ["ep2"]
    assert result["categories"]["project_state"]["included"] == ["proj"]


def test_budgeter_no_config_and_packet_and_isolation(tmp_path):
    profile_b = tmp_path / "profile-b"
    mods = _load_modules()
    runtime = mods[1]
    try:
        mods[2].IdentityStore(_Ctx()).ensure()
        home = get_hermes_home()
        _write_persona(home)
        before = _hashes(home)
        budgeter = runtime.PersonaContextBudgeter(_Ctx(ENABLED))
        first = budgeter.budget(memories=[
            {"id": "ep1", "estimated_tokens": 10, "priority": 0.5}])
        second = budgeter.budget(memories=[
            {"id": "ep1", "estimated_tokens": 10, "priority": 0.5}])
        items = runtime.PersonaRuntimeBridge(
            _Ctx(ENABLED)).packet_items("s1", "hello")
        after = _hashes(home)
        token = set_hermes_home_override(profile_b)
        try:
            _write_profile(profile_b)
            mods[2].IdentityStore(_Ctx()).ensure()
            route_b = runtime.PersonaContextBudgeter(
                _Ctx(ENABLED)).budget(memories=[
                    {"id": "ep1", "estimated_tokens": 10,
                     "priority": 0.5}])
        finally:
            reset_hermes_home_override(token)
    finally:
        mods[0].unload()
    assert first == second
    assert first["persona_id"] == "caducea"
    assert before == after
    assert len(items) == 1
    assert "§§3-94" in items[0].content
    assert "§15 budgeting" in items[0].content
    assert "persistent Hermes entity" not in items[0].content
    # Profile B has no persona config: caller items are
    # still budgeted, with no persona kernel.
    assert route_b["persona_id"] is None
    assert route_b["categories"]["persona_kernel"]["included"] == []
    assert route_b["categories"]["relevant_memories"]["included"] == [
        "ep1"]
