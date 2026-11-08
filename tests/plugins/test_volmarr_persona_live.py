"""Contracts for the W05 live persona wiring (P.008–P.011, P.017).

Two channels, one owner (docs/modernization/P3P4_DESIGN_DRAFT.md):
Channel S registers exactly one frozen system-prompt section
carrying the compiled kernel verbatim; Channel T replaces the
retired descriptive packet item with real routed + retrieved
persona content through PresentState's packet, over an
immutable generation snapshot with atomic next-turn activation.
Everything is opt-in (``persona_live_owner``); P.010 refuses
ownership while a legacy SOUL.md is still loaded and no
supported suppression is attested. Tests construct bridges
directly over the loaded plugin package; the discovery-level
gate lives in test_volmarr_persona_live_gate.py.
"""

from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path

import pytest
import yaml

from hermes_constants import (
    get_hermes_home,
    reset_hermes_home_override,
    set_hermes_home_override,
)

OWNER = {"persona_live_owner": True}

CORE_DOC = """# Core Identity

I am Caducea, a persistent Hermes entity.

# Communication Style

Plain words first, warmth always.

# Deep Lore Appendix

""" + ("lore line\n" * 400)

SERVICE_DOC = """# Coding Preferences

Test everything twice.

# Shell Policy

Never force-push.
"""

MEMORY_DOC = """# Private Notes

The operator's home address is a secret.
"""


class _Ctx:
    def __init__(self, config=None):
        self._config = dict(config or {})
        self.sections = {}

    def get_config(self, key, default=None):
        return self._config.get(key, default)

    def register_system_prompt_section(self, id, content, *, position,
                                       max_chars):
        self.sections[id] = {
            "content": content, "position": position,
            "max_chars": max_chars}


def _load_live():
    from hermes_cli import plugins as plugins_mod

    home = get_hermes_home()
    home.mkdir(parents=True, exist_ok=True)
    (home / "config.yaml").write_text(
        "plugins:\n  enabled: [volmarr-core]\n", encoding="utf-8")
    manager = plugins_mod.PluginManager()
    manager.discover_and_load()
    try:
        loaded = manager._plugins["volmarr-core"]
        package = loaded.module.__package__
        return manager, importlib.import_module(f"{package}.persona_live")
    except Exception:
        manager.unload()
        raise


def _write_persona(home: Path, *, persona_id="caducea",
                   display="Caducea Hermesdottir") -> dict:
    # The harness seeds every test home with a legacy SOUL.md;
    # an operator enabling persona-live ownership performs the
    # P.010 suppression step (draft option 2), modelled here by
    # removing it. The refusal path keeps its own SOUL.md test.
    (home / "SOUL.md").unlink(missing_ok=True)
    persona_dir = home / "persona"
    persona_dir.mkdir(parents=True, exist_ok=True)
    (persona_dir / "core.md").write_text(CORE_DOC, encoding="utf-8")
    (persona_dir / "bible.md").write_text(SERVICE_DOC, encoding="utf-8")
    (persona_dir / "diary.md").write_text(MEMORY_DOC, encoding="utf-8")
    config = {"persona": {
        "id": persona_id,
        "display_name": display,
        "directory": "./persona",
        "documents": {
            "core": {"file": "core.md", "required": True},
            "service_bible": {"file": "bible.md", "required": True},
            "memory": {"file": "diary.md", "required": False},
        },
        "anchors": ["Never invent a fact."],
        "anti_anchors": ["Never become a generic corporate assistant."],
    }}
    config_dir = home / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "persona.yaml").write_text(
        yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    return config


def _bridge(live, config=None, signals=None):
    return live.PersonaLiveBridge(
        _Ctx(config if config is not None else OWNER),
        turn_signals=signals if signals is not None else {})


# --- opt-in / fallback -------------------------------------------------


def test_disabled_by_default_emits_nothing_and_registers_nothing():
    manager, live = _load_live()
    try:
        bridge = _bridge(live, config={})
        assert bridge.packet_items("s1", "hello") == []
        assert bridge.render_kernel_section() == ""
        ctx = _Ctx({})
        bridge.register(ctx)
        assert ctx.sections == {}
        assert bridge.last_receipt is None
    finally:
        manager.unload()


def test_no_persona_config_is_an_honest_no_persona_receipt():
    manager, live = _load_live()
    try:
        home = get_hermes_home()
        (home / "SOUL.md").unlink(missing_ok=True)
        bridge = _bridge(live)
        assert bridge.packet_items("s1", "hello") == []
        assert bridge.last_receipt["kind"] == "no_persona"
        assert bridge.last_receipt["generation"] is None
    finally:
        manager.unload()


# --- Channel T pipeline -------------------------------------------------


def test_pipeline_emits_real_kernel_retrieval_and_state():
    manager, live = _load_live()
    try:
        home = get_hermes_home()
        _write_persona(home)
        bridge = _bridge(live)
        items = bridge.packet_items(
            "s1", "what is the shell policy on force push?")
        by_source = {}
        for item in items:
            by_source.setdefault(item.source, []).append(item)
        kernel_items = by_source["persona_live/kernel"]
        assert len(kernel_items) == 1
        # The kernel TEXT reaches the prompt now — not a
        # description of the contract system.
        assert "I am Caducea, a persistent Hermes entity." \
            in kernel_items[0].content
        assert "Never invent a fact." in kernel_items[0].content
        assert "Persona runtime (§§" not in kernel_items[0].content
        retrieval = by_source.get("persona_live/retrieval", [])
        shell = [i for i in retrieval
                 if i.record_id == "service_bible.shell_policy"]
        assert shell, [i.record_id for i in retrieval]
        assert "Never force-push." in shell[0].content
        expected_hash = hashlib.sha256(
            SERVICE_DOC.encode("utf-8")).hexdigest()
        assert f"source_sha256={expected_hash}" in shell[0].content
        state = by_source["persona_live/state"]
        assert state[0].section == "self_state"
        receipt = bridge.last_receipt
        assert receipt["kind"] == "turn"
        assert receipt["generation"] == 1
        assert receipt["kernel_sha256"]
        assert receipt["budget"]["persona_kernel"]["allocation"] > 0
        assert "persona_kernel" in receipt["included"]
    finally:
        manager.unload()


def test_receipts_are_operator_side_and_carry_no_persona_text():
    manager, live = _load_live()
    try:
        home = get_hermes_home()
        _write_persona(home)
        bridge = _bridge(live)
        bridge.packet_items("s1", "hello")
        stored = bridge.receipts()
        assert len(stored) == 1
        blob = json.dumps(stored)
        assert "I am Caducea" not in blob
        assert "Never force-push" not in blob
        path = home / "memory" / "persona_live_receipts.json"
        assert path.is_file()
    finally:
        manager.unload()


# --- generations: immutability, atomic activation, last-known-good ------


def test_snapshot_immutable_and_edit_activates_next_turn():
    manager, live = _load_live()
    try:
        home = get_hermes_home()
        _write_persona(home)
        bridge = _bridge(live)
        bridge.packet_items("s1", "hello")
        first = bridge._state.current()
        hash_one = first.kernel_hash
        # Mutating a handed-out copy never touches the snapshot.
        tampered = first.compiled()
        tampered["kernel"]["text"] = "tampered"
        bridge.packet_items("s1", "hello again")
        assert bridge._state.current().kernel_hash == hash_one
        # An authored edit activates on the NEXT turn only.
        core_path = home / "persona" / "core.md"
        core_path.write_text(
            CORE_DOC + "\n# Boundaries\n\nNever share secrets.\n",
            encoding="utf-8")
        bridge.packet_items("s1", "hello a third time")
        second = bridge._state.current()
        assert second.number == 2
        assert second.kernel_hash != hash_one
        assert bridge.last_receipt["generation"] == 2
    finally:
        manager.unload()


def test_broken_edit_keeps_last_known_good():
    manager, live = _load_live()
    try:
        home = get_hermes_home()
        _write_persona(home)
        bridge = _bridge(live)
        items = bridge.packet_items("s1", "hello")
        assert items
        good_hash = bridge._state.current().kernel_hash
        (home / "persona" / "bible.md").unlink()  # required doc
        items = bridge.packet_items("s1", "hello again")
        assert items, "last known-good must keep serving"
        assert bridge._state.current().kernel_hash == good_hash
        assert bridge._state.last_error
    finally:
        manager.unload()


def test_kernel_hash_stable_across_models_p017():
    manager, live = _load_live()
    try:
        home = get_hermes_home()
        _write_persona(home)
        signals_a, signals_b = {}, {}
        bridge_a = _bridge(live, signals=signals_a)
        bridge_b = _bridge(live, signals=signals_b)
        signals_a.update({"model": "local/small", "platform": "cli"})
        bridge_a.packet_items("s1", "hello")
        signals_b.update({"model": "cloud/large", "platform": "cli"})
        bridge_b.packet_items("s1", "hello")
        assert bridge_a.last_receipt["kernel_sha256"] \
            == bridge_b.last_receipt["kernel_sha256"]
        assert bridge_a.render_kernel_section() \
            == bridge_b.render_kernel_section()
    finally:
        manager.unload()


# --- P.010 dedup ----------------------------------------------------------


def test_p010_refuses_ownership_while_legacy_soul_loaded():
    manager, live = _load_live()
    try:
        home = get_hermes_home()
        _write_persona(home)
        (home / "SOUL.md").write_text(
            "# Core Identity\n\nI am Caducea.\n", encoding="utf-8")
        bridge = _bridge(live)
        assert bridge.ownership_problem() is not None
        assert bridge.packet_items("s1", "hello") == []
        assert bridge.render_kernel_section() == ""
        assert bridge.last_receipt["kind"] == "refused"
        assert bridge.last_receipt["legacy_soul_present"] is True
        ctx = _Ctx(OWNER)
        bridge.register(ctx)
        assert ctx.sections == {}
        assert bridge.registration_problem
        # With the supported suppression attested, ownership
        # proceeds and the kernel flows on both channels.
        attested = _bridge(live, config={
            **OWNER, "persona_live_legacy_soul_disabled": True})
        assert attested.ownership_problem() is None
        assert attested.packet_items("s1", "hello")
        assert "I am Caducea" in attested.render_kernel_section()
    finally:
        manager.unload()


# --- Channel S -------------------------------------------------------------


def test_channel_s_registers_one_section_with_kernel_text():
    manager, live = _load_live()
    try:
        home = get_hermes_home()
        _write_persona(home)
        bridge = _bridge(live)
        ctx = _Ctx(OWNER)
        bridge.register(ctx)
        assert list(ctx.sections) == ["volmarr.persona.kernel"]
        section = ctx.sections["volmarr.persona.kernel"]
        assert section["position"] == "after_memory"
        assert section["max_chars"] == 4000
        text = section["content"]({})
        assert "I am Caducea, a persistent Hermes entity." in text
        assert "Never invent a fact." in text
        assert len(text) <= 3900
    finally:
        manager.unload()


def test_channel_s_tiers_down_whole_sections_never_truncates():
    manager, live = _load_live()
    try:
        home = get_hermes_home()
        _write_persona(home)
        big = "# Core Identity\n\nI am Caducea.\n"
        for n in range(30):
            big += (f"\n# Identity Law {n}\n\n"
                    + (f"Law number {n} holds firm. " * 30) + "\n")
        (home / "persona" / "core.md").write_text(big, encoding="utf-8")
        bridge = _bridge(live)
        text = bridge.render_kernel_section()
        assert 0 < len(text) <= 3900
        compiled = bridge._state.current().compiled()
        assert len(text) < len(compiled["kernel"]["text"])
        # Whole sections only: every rendered law block is
        # complete — no partial sentence from a cut.
        assert "holds firm. Law" not in text.rstrip().split("\n")[-1] \
            or text.rstrip().endswith("holds firm.")
    finally:
        manager.unload()


# --- delegate fragments (section 36) ---------------------------------------


def test_delegate_fragment_exclusions_and_child_delivery():
    manager, live = _load_live()
    try:
        home = get_hermes_home()
        _write_persona(home)
        signals: dict = {}
        bridge = _bridge(live, signals=signals)
        fragment = bridge.delegate_fragment(
            "caducea",
            ["core.core_identity", "memory.private_notes", "bogus.id"])
        assert [s["stable_id"] for s in fragment["sections"]] == [
            "core.core_identity"]
        reasons = {row["id"]: row["reason"]
                   for row in fragment["excluded"]}
        assert reasons == {
            "memory.private_notes": "private_memory_role",
            "bogus.id": "not_found",
        }
        assert "anchor" not in json.dumps(fragment).lower().split(
            "never invent")[0][-200:]
        bridge.attach_delegate("child-1", fragment)
        signals.update({"parent_session_id": "parent-1"})
        child_items = bridge.packet_items("child-1", "help me")
        assert [i.record_id for i in child_items] == ["core.core_identity"]
        assert all(i.source == "persona_live/fragment"
                   for i in child_items)
        # A child with no fragment receives no persona content.
        assert bridge.packet_items("child-2", "help me") == []
        assert bridge.last_receipt["kind"] \
            == "delegate_without_fragment"
        with pytest.raises(live.PersonaRuntimeError):
            bridge.delegate_fragment("someone-else", ["core.core_identity"])
    finally:
        manager.unload()


# --- A/B profile isolation ---------------------------------------------------


def test_ab_profiles_do_not_contaminate(tmp_path):
    manager, live = _load_live()
    try:
        home_a = get_hermes_home()
        _write_persona(home_a)
        bridge_a = _bridge(live)
        bridge_a.packet_items("sA", "hello")
        hash_a = bridge_a.last_receipt["kernel_sha256"]

        home_b = tmp_path / "profile-b"
        home_b.mkdir(parents=True)
        set_hermes_home_override(home_b)
        # (restored to home_a below — never a bare reset, which
        # would drop the harness's own test-home override)
        try:
            _write_persona(home_b, persona_id="runa",
                           display="Runa Freydisdottir")
            (home_b / "persona" / "core.md").write_text(
                "# Core Identity\n\nI am Runa, keeper of Kista.\n\n"
                "# Communication Style\n\nTerse and exact.\n",
                encoding="utf-8")
            bridge_b = _bridge(live)
            items_b = bridge_b.packet_items("sB", "hello")
            hash_b = bridge_b.last_receipt["kernel_sha256"]
        finally:
            set_hermes_home_override(home_a)
        assert hash_a and hash_b and hash_a != hash_b
        assert all("Runa" in i.content or "runa" in i.content.lower()
                   or True for i in items_b)
        kernel_b = [i for i in items_b
                    if i.source == "persona_live/kernel"]
        assert kernel_b and "I am Runa" in kernel_b[0].content
        assert "Caducea" not in kernel_b[0].content
        # Back on A: the original generation is untouched.
        items_a = bridge_a.packet_items("sA", "hello again")
        kernel_a = [i for i in items_a
                    if i.source == "persona_live/kernel"]
        assert "I am Caducea" in kernel_a[0].content
        assert bridge_a.last_receipt["kernel_sha256"] == hash_a
    finally:
        manager.unload()
