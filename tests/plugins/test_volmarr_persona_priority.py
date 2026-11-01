"""Contracts for the persona priority system (Slice 125).

Persona Runtime roadmap §16 (Priority System): persona
information carries priority — P0 identity-critical, P1
strong behavioral rule, P2 important preference, P3
context-specific preference, P4 aesthetic/background
detail — and P0 material is never evicted from the kernel
merely to save a few tokens. The level may be authored by
a trailing [Pn] heading marker or derived deterministically
from the signals the compiler already computes, reconciled
with the §11 derived priority bands and the §15 budgeter.
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

BIG = "word " * 640  # 3200 chars -> 800 estimated tokens

CORE_DOC = f"""# Core Identity

{BIG}
# Core Essence [P0]

{BIG}
"""

REL_DOC = """# Care Rules

Offer counsel once, then accept the decision.
"""

DOCS = {
    "core": ("core.md", CORE_DOC),
    "relationship": ("rel.md", REL_DOC),
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


def test_priority_levels_table_and_scores():
    mods = _load_modules()
    runtime = mods[1]
    try:
        assert runtime.priority_levels() == [
            {"level": "P0", "name": "identity-critical"},
            {"level": "P1", "name": "strong behavioral rule"},
            {"level": "P2", "name": "important preference"},
            {"level": "P3", "name": "context-specific preference"},
            {"level": "P4", "name": "aesthetic/background detail"},
        ]
        assert runtime.priority_level_score("P0") == 1.0
        assert runtime.priority_level_score("P4") == 0.25
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.priority_level_score("P9")
    finally:
        mods[0].unload()


def test_authored_marker_is_pure_and_not_identity():
    mods = _load_modules()
    runtime = mods[1]
    try:
        assert runtime.authored_priority_level("Core Essence [P0]") == "P0"
        assert runtime.authored_priority_level("Care Rules [p3]") == "P3"
        assert runtime.authored_priority_level("Core Identity") is None
        # An out-of-range marker is ordinary heading text.
        assert runtime.authored_priority_level("Notes [P9]") is None
        # The marker is stripped from the semantic heading,
        # so authoring a level never changes a stable id.
        assert runtime.display_heading("Core Essence [P0]") == "Core Essence"
        assert runtime.display_heading("Notes [P9]") == "Notes [P9]"
        sections = runtime.parse_sections(
            "# Core Essence [P0]\n\nBody text.\n")
        assert sections[0]["heading"] == "Core Essence"
        assert sections[0]["section_id"] == "core_essence"
        assert sections[0]["authored_priority"] == "P0"
    finally:
        mods[0].unload()


def test_derived_levels_reconcile_with_existing_signals():
    mods = _load_modules()
    runtime = mods[1]
    try:
        level = runtime.priority_level
        assert level("core", "Core Identity", in_kernel=True) == "P0"
        assert level("tool_policy", "Git Policy", in_kernel=True) == "P1"
        # Kernel-marked but not selected: still a strong rule.
        assert level("relationship", "Boundary Rules") == "P1"
        assert level("relationship", "When Caducea Disagrees") == "P2"
        assert level("service_bible", "Coding Preferences") == "P3"
        assert level("avatar", "Appearance") == "P4"
        assert level("core", "preamble") == "P4"
    finally:
        mods[0].unload()


def test_authored_level_wins_over_derived():
    mods = _load_modules()
    runtime = mods[1]
    try:
        assert runtime.priority_level(
            "avatar", "Appearance", authored="P1") == "P1"
        assert runtime.section_priority(
            "avatar", "Appearance", authored="P1") == 0.85
        assert runtime.section_priority(
            "core", "Core Identity", authored="P4") == 0.25
        # Without a marker the §11 bands are unchanged.
        assert runtime.section_priority(
            "core", "Core Identity", in_kernel=True) == 0.90
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.priority_level("core", "X", authored="P9")
    finally:
        mods[0].unload()


def test_kernel_never_evicts_p0_to_save_tokens():
    mods = _load_modules()
    runtime = mods[1]
    try:
        _write_persona(get_hermes_home())
        compiled = runtime.PersonaCompiler(_Ctx(ENABLED)).compile()
    finally:
        mods[0].unload()
    kernel = compiled["kernel"]
    # Both 800-token core sections are P0: the second is
    # picked past the 1500-token ceiling rather than
    # evicted, and the kernel surfaces over-band honestly.
    assert kernel["stable_ids"] == [
        "core.core_identity", "core.core_essence"]
    assert kernel["within_band"] is False
    assert kernel["estimated_tokens"] > 1500
    # The P1 relationship rule no longer fits and is skipped.
    assert "relationship.care_rules" not in kernel["stable_ids"]
    by_id = {row["stable_id"]: row for row in compiled["index"]}
    essence = by_id["core.core_essence"]
    assert essence["priority_level"] == "P0"
    assert essence["priority_authored"] is True
    assert essence["priority"] == 1.0
    identity = by_id["core.core_identity"]
    assert identity["priority_level"] == "P0"
    assert identity["priority_authored"] is False
    care = by_id["relationship.care_rules"]
    assert care["priority_level"] == "P1"
    assert care["priority"] == 0.80


def test_budgeter_never_excludes_p0_kernel_item():
    mods = _load_modules()
    runtime = mods[1]
    try:
        p0 = {"id": "persona_kernel", "category": "persona_kernel",
              "estimated_tokens": 5000, "priority": 1.0,
              "priority_level": "P0"}
        p1 = {"id": "other", "category": "persona_kernel",
              "estimated_tokens": 5000, "priority": 0.85,
              "priority_level": "P1"}
        kept = runtime.budget_items(
            [p0], budgets={"persona_kernel": 100})
        dropped = runtime.budget_items(
            [p1], budgets={"persona_kernel": 100})
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.budget_items([{
                "id": "x", "category": "persona_kernel",
                "estimated_tokens": 1, "priority_level": "P9"}])
    finally:
        mods[0].unload()
    cat = kept["categories"]["persona_kernel"]
    assert cat["included"] == ["persona_kernel"]
    assert cat["excluded"] == []
    # The overage is reported, not hidden: remaining goes
    # negative rather than evicting P0 material.
    assert cat["remaining"] == 100 - 5000
    assert dropped["categories"]["persona_kernel"]["excluded"] == [
        "other"]


def test_budgeter_service_keeps_kernel_under_tiny_budget():
    mods = _load_modules()
    runtime = mods[1]
    try:
        _write_persona(get_hermes_home())
        result = runtime.PersonaContextBudgeter(
            _Ctx(ENABLED)).budget(budgets={"persona_kernel": 1})
    finally:
        mods[0].unload()
    assert result["categories"]["persona_kernel"]["included"] == [
        "persona_kernel"]


def test_compile_deterministic_packet_and_isolation(tmp_path):
    profile_b = tmp_path / "profile-b"
    mods = _load_modules()
    runtime = mods[1]
    try:
        mods[2].IdentityStore(_Ctx()).ensure()
        home = get_hermes_home()
        _write_persona(home)
        before = _hashes(home)
        compiler = runtime.PersonaCompiler(_Ctx(ENABLED))
        first = compiler.compile()
        second = compiler.compile()
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
    assert len(items) == 1
    assert "§§3-74" in items[0].content
    assert "§16 priority" in items[0].content
    assert "never evicted" in items[0].content
    assert "word word" not in items[0].content
