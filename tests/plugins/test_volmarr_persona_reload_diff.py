"""Contracts for persona reload + diff (Slice 154).

Persona Runtime roadmap §73 (Persona Reload Command)
and §74 (Persona Diff): the reload command stands as
a pure forced-reload record over two supplied
compiles — reload, recompile, reindex, and kernel
refresh forced in full (the §20 chain walked
unconditionally), without restarting Hermes — and
the diff stands as a pure record and render over two
supplied compiles, built on the §21 change-impact
section diff, showing behavioral changes since the
previous version as +/- directive lines grouped by
document. The roadmap's ``hermes persona`` spelling
registers no new core command, because this plugin's
CLI surface is ``hermes volmarr``. This layer reloads
nothing live, persists no version, and interprets no
prose. Tests load through real plugin discovery.
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

CHANGED_CORE_DOC = """# Core Identity

Caducea is a counselor who lives in the longhouse terminal.
Caducea gives advice carefully.

# Graceful Deference

Caducea defers politely when Volmarr decides.
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

FORCED_ACTIONS = ["reload", "recompile", "reindex", "refresh_kernel"]

EXAMPLE_GROUPS = [
    {
        "role": "relationship",
        "label": "RELATIONSHIP",
        "lines": [
            {"sign": "+", "stable_id": None, "text":
             "Caducea may reopen decisions when materially "
             "new information appears."},
        ],
    },
    {
        "role": "tool_policy",
        "label": "TOOLS",
        "lines": [
            {"sign": "-", "stable_id": None, "text":
             "Git push required confirmation."},
            {"sign": "+", "stable_id": None, "text":
             "Git push allowed for preauthorized repositories."},
        ],
    },
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


def _rewrite_core(home: Path, core_doc: str) -> None:
    (home / "persona" / "core.md").write_text(
        core_doc, encoding="utf-8")


def _hashes(home: Path) -> dict[str, str]:
    return {
        str(path.relative_to(home)):
            hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(home.rglob("*"))
        if path.is_file() and "entity" not in path.parts
    }


def test_reload_forces_full_chain_when_unchanged():
    mods = _load_modules()
    runtime = mods[1]
    try:
        home = get_hermes_home()
        _write_persona(home)
        compiled = runtime.PersonaCompiler(_Ctx()).compile()
        record = runtime.persona_reload(compiled, compiled)
        actions = runtime.reload_forced_actions()
        actions.append("x")
    finally:
        mods[0].unload()
    assert list(runtime.RELOAD_FORCED_ACTIONS) == FORCED_ACTIONS
    assert runtime.RELOAD_COMMAND == "hermes persona reload"
    # The §20 plan for an unchanged pair names no steps;
    # the §73 record forces the full chain anyway, and
    # reports the hash comparison honestly as unchanged.
    assert runtime.reload_plan(compiled, compiled)["steps"] == []
    assert record == {
        "command": "hermes persona reload",
        "persona_id": "caducea",
        "forced": True,
        "actions": FORCED_ACTIONS,
        "steps": list(runtime.RELOAD_STEPS),
        "changed": False,
        "kernel_changed": False,
        "recompiled": True,
        "reindexed": True,
        "kernel_refreshed": True,
        "restart_required": False,
        "previous_version": "1.4.2",
        "current_version": "1.4.2",
    }


def test_reload_changed_and_first_compile():
    mods = _load_modules()
    runtime = mods[1]
    try:
        home = get_hermes_home()
        _write_persona(home)
        before = runtime.PersonaCompiler(_Ctx()).compile()
        _rewrite_core(home, CHANGED_CORE_DOC)
        after = runtime.PersonaCompiler(_Ctx()).compile()
        changed = runtime.persona_reload(before, after)
        first = runtime.persona_reload(None, before)
    finally:
        mods[0].unload()
    assert changed["changed"] is True
    # The edited section is not kernel material, so the
    # kernel hash honestly did not move — the refresh
    # is forced anyway (§73), not hash-driven (§20).
    assert changed["kernel_changed"] is False
    assert changed["kernel_refreshed"] is True
    assert changed["forced"] is True
    assert changed["restart_required"] is False
    assert first["changed"] is True
    assert first["previous_version"] is None
    assert first["current_version"] == "1.4.2"
    assert first["steps"] == list(runtime.RELOAD_STEPS)


def test_reload_refusals(tmp_path):
    profile_b = tmp_path / "profile-b"
    mods = _load_modules()
    runtime = mods[1]
    try:
        home = get_hermes_home()
        _write_persona(home)
        compiled = runtime.PersonaCompiler(_Ctx()).compile()
        token = set_hermes_home_override(str(profile_b))
        try:
            _write_profile(profile_b)
            mods[2].IdentityStore(_Ctx()).ensure()
            _write_persona(
                profile_b, persona_id="other",
                core_doc=OTHER_CORE_DOC)
            other = runtime.PersonaCompiler(_Ctx()).compile()
        finally:
            reset_hermes_home_override(token)
        for previous, current in (
                (compiled, None), (None, None),
                (compiled, other), (other, compiled),
                ("compile", compiled), (compiled, "compile"),
                (compiled, {}),
        ):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.persona_reload(previous, current)
    finally:
        mods[0].unload()


def test_reload_contract():
    mods = _load_modules()
    runtime = mods[1]
    try:
        contract = runtime.persona_reload_contract()
    finally:
        mods[0].unload()
    assert contract == {
        "name": "PersonaReload",
        "command": "hermes persona reload",
        "plugin_cli_surface": "hermes volmarr",
        "forced_actions": FORCED_ACTIONS,
        "steps": list(runtime.RELOAD_STEPS),
        "forced": True,
        "restart_required": False,
        "new_core_command": False,
        "basis": "§20 reload chain, forced in full",
    }


def test_diff_example_matches_roadmap():
    mods = _load_modules()
    runtime = mods[1]
    try:
        example = runtime.persona_diff_example()
        rendered = runtime.render_persona_diff(example)
        groups = runtime.persona_diff_contract()["example"]["groups"]
        groups.append("x")
    finally:
        mods[0].unload()
    assert runtime.DIFF_COMMAND == "hermes persona diff"
    assert example["groups"] == EXAMPLE_GROUPS
    assert example["changed"] is True
    assert rendered == (
        "RELATIONSHIP:\n"
        "+ Caducea may reopen decisions when materially "
        "new information appears.\n"
        "\n"
        "TOOLS:\n"
        "- Git push required confirmation.\n"
        "+ Git push allowed for preauthorized repositories.")
    assert not rendered.endswith("\n")


def test_diff_from_real_compiles():
    mods = _load_modules()
    runtime = mods[1]
    try:
        home = get_hermes_home()
        _write_persona(home)
        before = runtime.PersonaCompiler(_Ctx()).compile()
        _rewrite_core(home, CHANGED_CORE_DOC)
        after = runtime.PersonaCompiler(_Ctx()).compile()
        record = runtime.persona_diff(before, after)
        rendered = runtime.render_persona_diff(record)
    finally:
        mods[0].unload()
    assert record["persona_id"] == "caducea"
    assert record["previous_version"] == "1.4.2"
    assert record["current_version"] == "1.4.2"
    assert record["changed"] is True
    assert record["impact_class"] == \
        runtime.change_impact(before, after)["impact_class"]
    assert [group["role"] for group in record["groups"]] == ["core"]
    lines = record["groups"][0]["lines"]
    assert [line["sign"] for line in lines] == ["-", "+"]
    assert {line["stable_id"] for line in lines} == \
        {"core.graceful_deference"}
    assert "defers gracefully" in lines[0]["text"]
    assert "defers politely" in lines[1]["text"]
    assert rendered.startswith("CORE:\n- ")
    assert "\n+ " in rendered


def test_diff_unchanged_compiles():
    mods = _load_modules()
    runtime = mods[1]
    try:
        home = get_hermes_home()
        _write_persona(home)
        compiled = runtime.PersonaCompiler(_Ctx()).compile()
        record = runtime.persona_diff(compiled, compiled)
    finally:
        mods[0].unload()
    assert record["changed"] is False
    assert record["groups"] == []
    assert record["impact_class"] == "none"
    assert runtime.render_persona_diff(record) == \
        "No behavioral changes."


def test_diff_refusals(tmp_path):
    profile_b = tmp_path / "profile-b"
    mods = _load_modules()
    runtime = mods[1]
    try:
        home = get_hermes_home()
        _write_persona(home)
        compiled = runtime.PersonaCompiler(_Ctx()).compile()
        token = set_hermes_home_override(str(profile_b))
        try:
            _write_profile(profile_b)
            mods[2].IdentityStore(_Ctx()).ensure()
            _write_persona(
                profile_b, persona_id="other",
                core_doc=OTHER_CORE_DOC)
            other = runtime.PersonaCompiler(_Ctx()).compile()
        finally:
            reset_hermes_home_override(token)
        for previous, current in (
                (compiled, other), (None, compiled),
                (compiled, None), ("compile", compiled),
        ):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.persona_diff(previous, current)
        for bad in (None, "record", [], {"groups": "x"},
                    {"groups": [{"label": 7, "lines": []}]},
                    {"groups": [{"label": "CORE", "lines": [
                        {"sign": "?", "text": "x"}]}]}):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.render_persona_diff(bad)
    finally:
        mods[0].unload()


def test_diff_contract():
    mods = _load_modules()
    runtime = mods[1]
    try:
        contract = runtime.persona_diff_contract()
    finally:
        mods[0].unload()
    assert contract == {
        "name": "PersonaDiff",
        "command": "hermes persona diff",
        "plugin_cli_surface": "hermes volmarr",
        "basis": "§21 change impact section diff",
        "groups_by": "document role",
        "example": runtime.persona_diff_example(),
        "new_core_command": False,
        "persists_versions": False,
    }
    assert runtime.DIFF_GROUP_LABELS["tool_policy"] == "TOOLS"
    assert runtime.DIFF_GROUP_LABELS["relationship"] == \
        "RELATIONSHIP"
    assert runtime.MAX_DIFF_LINE_CHARS == 240


def test_packet_determinism_and_isolation(tmp_path):
    profile_b = tmp_path / "profile-b"
    mods = _load_modules()
    runtime = mods[1]
    try:
        mods[2].IdentityStore(_Ctx()).ensure()
        home = get_hermes_home()
        _write_persona(home)
        before = _hashes(home)
        contract = runtime.persona_reload_contract()
        diff = runtime.persona_diff_contract()
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
            other_contract = runtime.persona_reload_contract()
            other_diff = runtime.persona_diff_contract()
        finally:
            reset_hermes_home_override(token)
        third = runtime.PersonaRuntimeBridge(
            _Ctx(ENABLED)).packet_items("s1", "hello")
    finally:
        mods[0].unload()
    assert before == after
    assert contract == other_contract
    assert diff == other_diff
    assert first[0].content == second[0].content == third[0].content
    assert len(first) == 1
    content = first[0].content
    assert "§§3-84" in content
    assert "§73 persona reload" in content
    assert "without restarting" in content
    assert "§74 persona diff" in content
    assert "behavioral changes" in content
    # The packet names the contracts only — never canonical
    # persona text.
    assert "longhouse terminal" not in content
