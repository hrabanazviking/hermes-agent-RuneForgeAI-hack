"""Contracts for the persona hash record and hot reload (Slice 127).

Persona Runtime roadmap §19 (Persona Hash) and §20 (Hot
Reload): every compile carries a stored hash record —
persona version, per-document hashes, kernel hash, persona
hash — so human edits to persona files are detectable, and
an explicit reload check walks the §20 chain (detect hash
change, reparse changed documents, update the IR, rebuild
the retrieval index, recompile the kernel only if
necessary) without a restart and without a file watcher.
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

# Core Communication Style

Warm, direct, and brief unless depth is asked for.

# Hobbies

She keeps bees behind the longhouse.
"""

AVATAR_DOC = """# Appearance

A long coat of deep green wool.
"""

DOCS = {
    "core": ("core.md", CORE_DOC),
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


def _write_persona(home: Path, docs=None, anchors=None) -> None:
    docs = DOCS if docs is None else docs
    persona_dir = home / "persona"
    persona_dir.mkdir(parents=True, exist_ok=True)
    for role, (name, text) in docs.items():
        (persona_dir / name).write_text(text, encoding="utf-8")
    persona = {
        "id": "caducea",
        "display_name": "Caducea Hermesdottir",
        "directory": "./persona",
        "documents": {
            role: {"file": name, "required": True}
            for role, (name, _text) in docs.items()
        },
    }
    if anchors is not None:
        persona["anchors"] = anchors
    config_dir = home / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "persona.yaml").write_text(
        yaml.safe_dump({"persona": persona}, sort_keys=False),
        encoding="utf-8")


def _edit_doc(home: Path, name: str, text: str) -> None:
    (home / "persona" / name).write_text(text, encoding="utf-8")


def _hashes(home: Path) -> dict[str, str]:
    return {
        str(path.relative_to(home)):
            hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(home.rglob("*"))
        if path.is_file() and "entity" not in path.parts
    }


def test_compile_carries_the_stored_hash_record():
    mods = _load_modules()
    runtime = mods[1]
    try:
        _write_persona(get_hermes_home())
        compiled = runtime.PersonaCompiler(_Ctx(ENABLED)).compile()
    finally:
        mods[0].unload()
    record = compiled["hash_record"]
    assert list(record) == list(runtime.HASH_RECORD_FIELDS)
    assert record["persona_id"] == "caducea"
    assert record["persona_version"] == runtime.PERSONA_CONFIG_VERSION
    # Document hashes by role, in document order, matching
    # the compiled artefact's own document rows.
    assert list(record["document_hashes"]) == ["core", "avatar"]
    for document in compiled["documents"]:
        assert (record["document_hashes"][document["role"]]
                == document["sha256"])
    assert record["kernel_hash"] == compiled["kernel"]["sha256"]
    assert record["persona_hash"] == compiled["persona_hash"]
    # Unstamped: a compile is deterministic, so no clock
    # reading ever enters the artefact.
    assert record["compiled_at"] is None


def test_hash_record_stamping_is_explicit_and_validated():
    mods = _load_modules()
    runtime = mods[1]
    try:
        _write_persona(get_hermes_home())
        compiled = runtime.PersonaCompiler(_Ctx(ENABLED)).compile()
        stamped = runtime.hash_record(
            compiled, compiled_at="2026-10-31T12:00:00+00:00")
        # A stamp changes nothing else in the record, and a
        # stamp alone is never a persona change.
        plain = runtime.hash_record(compiled)
        assert stamped == {**plain,
                           "compiled_at": "2026-10-31T12:00:00+00:00"}
        assert runtime.detect_changes(plain, stamped)["changed"] is False
        for bad in ("2026-10-31T12:00:00", "not-a-time", "", 42):
            with pytest.raises(runtime.PersonaRuntimeError):
                runtime.hash_record(compiled, compiled_at=bad)
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.hash_record({})
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.hash_record(None)
    finally:
        mods[0].unload()


def test_detect_changes_names_added_removed_and_changed_documents():
    mods = _load_modules()
    runtime = mods[1]
    home = get_hermes_home()
    try:
        _write_persona(home)
        compiler = runtime.PersonaCompiler(_Ctx(ENABLED))
        first = compiler.compile()
        # Change the avatar document (never kernel material).
        _edit_doc(home, "avatar.md",
                  AVATAR_DOC.replace("deep green", "deep blue"))
        second = compiler.compile()
        diff = runtime.detect_changes(
            first["hash_record"], second["hash_record"])
        # Add a document, then remove it again.
        wider = dict(DOCS)
        wider["relationship"] = (
            "relationship.md",
            "# Relationship Rules\n\nCounsel is offered, never imposed.\n")
        _write_persona(home, wider)
        third = compiler.compile()
        grown = runtime.detect_changes(
            second["hash_record"], third["hash_record"])
        shrunk = runtime.detect_changes(
            third["hash_record"], second["hash_record"])
        # Records for different personas are not comparable.
        other = dict(first["hash_record"], persona_id="someone-else")
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.detect_changes(first["hash_record"], other)
        # A tampered record shape is refused.
        with pytest.raises(runtime.PersonaRuntimeError):
            runtime.detect_changes(
                first["hash_record"],
                {**second["hash_record"], "extra": 1})
    finally:
        mods[0].unload()
    assert diff["changed"] is True
    assert diff["documents_changed"] == ["avatar"]
    assert diff["documents_added"] == []
    assert diff["documents_removed"] == []
    assert diff["documents_unchanged"] == 1
    assert diff["kernel_changed"] is False
    assert diff["persona_changed"] is True
    assert grown["documents_added"] == ["relationship"]
    assert shrunk["documents_removed"] == ["relationship"]


def test_reload_plan_walks_only_the_steps_the_hashes_require():
    mods = _load_modules()
    runtime = mods[1]
    home = get_hermes_home()
    try:
        _write_persona(home)
        compiler = runtime.PersonaCompiler(_Ctx(ENABLED))
        first = compiler.compile()
        # Non-kernel edit: a non-kernel core section changes
        # the document and the index, never the kernel.
        _edit_doc(home, "core.md",
                  CORE_DOC.replace("keeps bees", "keeps bees and ducks"))
        second = compiler.compile()
        plan = runtime.reload_plan(first, second)
        # Kernel edit: identity material changes the kernel.
        _edit_doc(home, "core.md", CORE_DOC.replace(
            "lives in the longhouse terminal",
            "lives in the longhouse terminal by the fjord"))
        third = compiler.compile()
        kernel_plan = runtime.reload_plan(second, third)
    finally:
        mods[0].unload()
    assert runtime.reload_steps() == list(runtime.RELOAD_STEPS)
    assert plan["changed"] is True
    assert plan["steps"] == [
        "detect_hash_change", "reparse_changed_documents",
        "update_persona_ir", "rebuild_retrieval_index"]
    assert plan["documents_reparsed"] == ["core"]
    assert plan["ir_updated"] is True
    assert plan["index_rebuilt"] is True
    assert plan["kernel_recompile_required"] is False
    assert plan["restart_required"] is False
    assert kernel_plan["steps"] == [
        "detect_hash_change", "reparse_changed_documents",
        "update_persona_ir", "rebuild_retrieval_index",
        "recompile_kernel"]
    assert kernel_plan["kernel_recompile_required"] is True
    # Identity / absence edges of the pure plan.
    assert runtime.reload_plan(first, first)["changed"] is False
    assert runtime.reload_plan(first, first)["steps"] == []
    assert runtime.reload_plan(None, None)["changed"] is False
    initial = runtime.reload_plan(None, first)
    assert initial["steps"] == list(runtime.RELOAD_STEPS)
    assert initial["documents_reparsed"] == ["core", "avatar"]
    removed = runtime.reload_plan(first, None)
    assert removed["changed"] is True
    assert removed["documents_removed"] == ["core", "avatar"]
    assert removed["kernel_recompile_required"] is False


def test_anchor_change_recompiles_kernel_without_reparsing_documents():
    mods = _load_modules()
    runtime = mods[1]
    home = get_hermes_home()
    try:
        _write_persona(home, anchors=["She thinks independently."])
        compiler = runtime.PersonaCompiler(_Ctx(ENABLED))
        first = compiler.compile()
        _write_persona(home, anchors=["She thinks independently and says so."])
        second = compiler.compile()
        plan = runtime.reload_plan(first, second)
    finally:
        mods[0].unload()
    # Anchors live in the config, not in any document: no
    # document is reparsed, but the kernel hash moved, so
    # exactly the kernel step stands.
    assert plan["documents_reparsed"] == []
    assert plan["ir_updated"] is False
    assert plan["steps"] == ["detect_hash_change", "recompile_kernel"]
    assert plan["kernel_recompile_required"] is True


def test_reloader_returns_previous_untouched_until_something_changes():
    mods = _load_modules()
    runtime = mods[1]
    home = get_hermes_home()
    try:
        _write_persona(home)
        reloader = runtime.PersonaReloader(_Ctx(ENABLED))
        initial = reloader.check(None)
        assert initial["changed"] is True
        first = initial["compiled"]
        # Nothing changed: the previous artefact itself is
        # handed back — no rebuild happened.
        quiet = reloader.check(first)
        assert quiet["changed"] is False
        assert quiet["compiled"] is first
        assert quiet["plan"]["steps"] == []
        assert quiet["hash_record"] == first["hash_record"]
        # A document edit is picked up by the next explicit
        # check, with the fresh compile as the result.
        _edit_doc(home, "avatar.md",
                  AVATAR_DOC.replace("deep green", "deep blue"))
        woken = reloader.check(first)
    finally:
        mods[0].unload()
    assert woken["changed"] is True
    assert woken["compiled"] is not first
    assert woken["compiled"]["persona_hash"] != first["persona_hash"]
    assert woken["plan"]["documents_reparsed"] == ["avatar"]
    assert woken["plan"]["kernel_recompile_required"] is False
    assert woken["hash_record"] == woken["compiled"]["hash_record"]


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
            quiet_b = runtime.PersonaReloader(
                _Ctx(ENABLED)).check(None)
        finally:
            reset_hermes_home_override(token)
    finally:
        mods[0].unload()
    assert first == second
    assert first["hash_record"] == second["hash_record"]
    assert before == after
    assert compiled_b is None
    assert quiet_b["changed"] is False
    assert quiet_b["compiled"] is None
    assert len(items) == 1
    assert "§§3-32" in items[0].content
    assert "§19 hash record" in items[0].content
    assert "§20 hot reload" in items[0].content
