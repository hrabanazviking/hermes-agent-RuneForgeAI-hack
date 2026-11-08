"""W07 gate battery: live temporary gateway profile testbed.

The profile is disposable (the test harness home), staged with
the banked pieces only: persona config + authored corpus (one
buried section, one private + one shared + one public document,
one oversize-by-W04-standards document), W03 library, W04 index,
and ONE REAL GATEWAY TURN driven through the actual plugin
manager's pre_llm_call hook chain (the W05 gate pattern: the
same hooks the gateway invokes). Command outputs are verified
against independently computed ground truth. Also covers:
P.013 pager/editor proofs, the watchdog bounds proof, the
P.018 capturing-fake-provider battery (draft section 7 cases
a-f), honest-empty cases, and generation-store recovery.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import os
from pathlib import Path

import pytest
import yaml

from hermes_constants import get_hermes_home

PID = "gatew07"
DISPLAY = "Gate W07 Persona"
NEEDLE = "zqx gate needle w07 buried"
BIG_NEEDLE = "zqx gate big section needle"

CORE_DOC = f"""# Core Identity

I am the W07 gate fixture persona.

# Buried Lore

Somewhere below the fold: {NEEDLE} waits.
"""
BIBLE_DOC = """# Shell Policy

Never force-push.
"""
DIARY_DOC = """# Private Notes

zqx gate private diary secret text.
"""
BIG_DOC = "# Big Scroll\n\n## Giant Section\n\n" + (
    "filler words for the giant gate section " * 3000) + BIG_NEEDLE + "\n"


class _Ctx:
    def __init__(self, config=None):
        self._config = dict(config or {})

    def get_config(self, key, default=None):
        return self._config.get(key, default)


class _CapturingProvider:
    """The P.018 battery's fake cloud provider: records all bytes."""

    def __init__(self):
        self.captured: list[bytes] = []

    def capture(self, payload: bytes) -> None:
        self.captured.append(payload)

    @property
    def blob(self) -> bytes:
        return b"".join(self.captured)


@pytest.fixture(scope="module")
def mods():
    from hermes_cli import plugins as plugins_mod

    home = get_hermes_home()
    home.mkdir(parents=True, exist_ok=True)
    (home / "config.yaml").write_text(
        "plugins:\n  enabled: [volmarr-core]\n", encoding="utf-8")
    manager = plugins_mod.PluginManager()
    manager.discover_and_load()
    try:
        loaded = manager._plugins["volmarr-core"]
        pkg = loaded.module.__package__
        out = {name: importlib.import_module(f"{pkg}.{name}")
               for name in ("persona_ops", "canonical_library",
                            "persona_index", "persona_live", "cli")}
        out["manager"] = manager
    except Exception:
        manager.unload()
        raise
    return out


def _build_profile(mods, home: Path):
    (home / "SOUL.md").unlink(missing_ok=True)
    persona_dir = home / "persona"
    persona_dir.mkdir(parents=True, exist_ok=True)
    (persona_dir / "core.md").write_text(CORE_DOC, encoding="utf-8")
    (persona_dir / "bible.md").write_text(BIBLE_DOC, encoding="utf-8")
    (persona_dir / "diary.md").write_text(DIARY_DOC, encoding="utf-8")
    (persona_dir / "big.md").write_text(BIG_DOC, encoding="utf-8")
    config_dir = home / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "persona.yaml").write_text(yaml.safe_dump({"persona": {
        "id": PID, "display_name": DISPLAY, "directory": "./persona",
        "documents": {
            "core": {"file": "core.md", "required": True},
            "service_bible": {"file": "bible.md", "required": True},
            "memory": {"file": "diary.md", "required": False},
            "avatar": {"file": "big.md", "required": False},
        },
        "anchors": ["Never invent a fact."],
        "anti_anchors": ["Never become a generic corporate assistant."],
    }}, sort_keys=False), encoding="utf-8")
    lib = mods["canonical_library"].CanonicalLibrary(home, PID)
    lib.ingest("persona/core.md", "core", privacy_class="public")
    lib.ingest("persona/bible.md", "service_bible", privacy_class="shared")
    lib.ingest("persona/diary.md", "memory", privacy_class="private")
    lib.ingest("persona/big.md", "avatar", privacy_class="private")
    store = mods["canonical_library"].ManifestStore(home)
    manifest = store.load()
    for record in manifest["documents"].values():
        if record["role"] == "service_bible":
            record["destinations"] = ["cloud"]
            store.commit([mods["canonical_library"].DocumentRecord.from_dict(record)],
                         persona_id=PID)
    ops = mods["persona_ops"].PersonaOps(_Ctx(), home=home)
    ops.ensure_library()
    return ops


@pytest.fixture()
def ops(mods):
    return _build_profile(mods, get_hermes_home())


def test_gate_command_battery_against_ground_truth(ops):
    home = get_hermes_home()
    status = ops.status()
    assert status["status"] == "ok" and status["document_count"] == 4
    found = ops.search(NEEDLE)
    assert any(NEEDLE in r["text"] for r in found["results"])
    big = ops.search(BIG_NEEDLE)
    assert big["results"], "oversize-document needle not retrieved"
    assert ops.inspect()["record"]["persona"] == DISPLAY
    assert ops.validate()["valid"] is True
    battery = ops.test_battery()
    assert battery["passed"] == battery["total"], battery
    diag = ops.diagnostics()
    assert diag["persona_id"] == PID
    assert diag["receipt_count"] >= 1
    # Honest-empty + gateway probe transitions.
    assert ops.explain("no-such-turn-w07")["status"] == "no_such_turn"
    (home / "gateway.pid").write_text(str(os.getpid()), encoding="utf-8")
    try:
        assert ops.status()["gateway"]["state"] == "running"
    finally:
        (home / "gateway.pid").unlink()
    assert ops.status()["gateway"]["state"] == "gateway_not_running"
    # Canary: example records never surface.
    blob = json.dumps({"s": status, "i": ops.inspect()}, default=str)
    assert "Caducea" not in blob


def test_gate_one_real_gateway_turn_then_explain(mods, ops):
    home = get_hermes_home()
    (home / "config.yaml").write_text(
        "plugins:\n"
        "  enabled: [volmarr-core]\n"
        "  entries:\n"
        "    volmarr-core:\n"
        "      settings:\n"
        "        persona_live_owner: true\n"
        "        persona_live_legacy_soul_disabled: true\n",
        encoding="utf-8")
    manager = mods["manager"]
    results = manager.invoke_hook(
        "pre_llm_call", session_id="w07-gate-session",
        turn_id="w07-gate-turn-1",
        user_message="what is the shell policy on force push?",
        model="test/model", platform="cli", parent_session_id="",
        sender_id="w07-gate")
    assert results, "gateway turn produced no context"
    explained = ops.explain("w07-gate-turn-1")
    assert explained["status"] == "ok", explained
    assert explained["receipt_store"] == "w05_persona_live"
    status = ops.status()
    assert explained["kernel_sha256"] in (
        status["kernel_sha256"], "not_recorded") or explained["generation"] is not None


def test_pager_concatenation_and_continuation(ops):
    files = ops.files()
    big = next(r for r in files["documents"] if r["path"].endswith("big.md"))
    concat, cursor = b"", 0
    while True:
        page = ops.read_page(big["document_id"], cursor, 8192)
        concat += page["text"].encode("utf-8")
        assert page["page_sha256"] == hashlib.sha256(
            page["text"].encode("utf-8")).hexdigest()
        if page["complete"]:
            break
        cursor = page["next_cursor"]
    raw = (get_hermes_home() / big["path"]).read_bytes()
    assert concat == raw
    # Continuation handles from retrieval serve the giant section.
    found = ops.search(BIG_NEEDLE)
    hit = found["results"][0]
    if hit.get("windowed"):
        nxt = ops.continue_read(hit["more_from_this_section"]["next_handle"])
        assert nxt["status"] == "ok"


def test_editor_dry_run_then_confirmed_edit(ops):
    found = ops.search("shell policy")
    assert found["results"]
    sid = found["results"][0]["stable_id"]
    home = get_hermes_home()
    path = home / found["results"][0]["path"]
    before = path.read_bytes()
    citation = ops._index().cite(sid)
    section_bytes = before[citation["byte_start"]:citation["byte_end"]]
    dry = ops.edit_section(sid, section_bytes.decode("utf-8") + "Edited line.\n")
    assert dry["status"] == "dry_run"
    assert path.read_bytes() == before, "dry-run mutated the source"
    new_text = section_bytes.decode("utf-8").replace(
        "Never force-push.", "Never force-push, ever.")
    if new_text == section_bytes.decode("utf-8"):
        new_text = section_bytes.decode("utf-8") + "Edited line.\n"
    done = ops.edit_section(sid, new_text, confirm=True, approved=True)
    assert done["status"] == "ok", done
    after = path.read_bytes()
    assert after[:citation["byte_start"]] == before[:citation["byte_start"]]
    assert after[citation["byte_start"] + len(new_text.encode("utf-8")):] == \
        before[citation["byte_end"]:]


def test_watchdog_bounds_and_no_evidence(ops):
    home = get_hermes_home()
    before = {row["path"]: row["live_sha256"] for row in ops.files()["documents"]}
    empty = ops.watchdog()
    assert empty["status"] == "no_evidence"
    scored = ops.watchdog(samples=[{
        "turn_id": "t-drift", "scores": {"tone": 0.9},
        "violated_anchors": ["Never invent a fact."],
        "model": "test-model", "mode": "companion",
        "retrieved_sections": []}])
    assert scored["status"] == "ok"
    assert scored["corpus_unchanged"] is True
    row = scored["rows"][0]
    assert row["drift"]["route"] == "repair"
    assert row["repair_proposal"]["applied"] is False
    after = {row["path"]: row["live_sha256"] for row in ops.files()["documents"]}
    assert before == after
    assert (home / "generated" / "persona-ops" / "watchdog").is_dir()


def test_privacy_battery_capturing_provider(ops, mods):
    po = mods["persona_ops"]
    items = [
        {"stable_id": "core.public_thing", "privacy_class": "public",
         "destinations": [], "text": "PUBLIC GATE TEXT"},
        {"stable_id": "memory.private_thing", "privacy_class": "private",
         "destinations": [], "text": "PRIVATE GATE SECRET"},
        {"stable_id": "bible.shared_listed", "privacy_class": "shared",
         "destinations": ["cloud"], "text": "SHARED LISTED TEXT"},
        {"stable_id": "bible.shared_unlisted", "privacy_class": "shared",
         "destinations": ["other"], "text": "SHARED UNLISTED TEXT"},
        {"stable_id": "x.unlabelled", "privacy_class": "",
         "destinations": [], "text": "UNLABELLED TEXT"},
    ]
    # (a) private, no override -> zero private bytes captured.
    provider = _CapturingProvider()
    out = ops.offer_to_provider(items, "cloud", provider)
    assert b"PRIVATE GATE SECRET" not in provider.blob
    assert b"SHARED UNLISTED TEXT" not in provider.blob
    assert b"UNLABELLED TEXT" not in provider.blob
    assert b"PUBLIC GATE TEXT" in provider.blob
    assert b"SHARED LISTED TEXT" in provider.blob
    assert out["cloud_egress"] == 2
    # (b) private + recorded override -> egress, receipt names it.
    provider2 = _CapturingProvider()
    out2 = ops.offer_to_provider(items, "cloud", provider2, overrides=[
        {"stable_id": "memory.private_thing", "destination": "cloud",
         "consent_id": "consent-gate-1"}])
    assert b"PRIVATE GATE SECRET" in provider2.blob
    assert out2["offered"] == 3
    # (c) revoked override -> refused again.
    provider3 = _CapturingProvider()
    ops.offer_to_provider(items, "cloud", provider3, overrides=[
        {"stable_id": "memory.private_thing", "destination": "cloud",
         "consent_id": "consent-gate-1", "revoked": True}])
    assert b"PRIVATE GATE SECRET" not in provider3.blob
    # (f) local destination -> no cloud call semantics: all local.
    local = po.egress_decision(items, "local")
    assert local["cloud_egress"] == 0 and len(local["allowed"]) == 5
    # W06 double gate consumed, not rebuilt: both gates off here.
    gated = ops.memory_egress("anything")
    assert gated["status"] == "egress_not_enabled"
    assert gated["cloud_egress"] == 0


def test_generation_store_recovery(ops, mods):
    ops.reload_activate()
    store = ops.store
    assert store.read_pointer() is not None
    store.pointer_path.write_text("{ torn", encoding="utf-8")
    recovered = store.read_pointer()
    assert recovered is not None
    assert recovered["activation_scope"] == "recovered_from_generation_store"
    assert list(store.root.glob("active-generation.corrupt-*.json"))


def test_honest_empty_profile(mods, tmp_path):
    empty = tmp_path / "empty-home"
    empty.mkdir()
    o = mods["persona_ops"].PersonaOps(_Ctx(), home=empty)
    assert o.status()["status"] in ("no_persona_config", "no_profile")
    assert o.files()["status"] == "manifest_missing"
    assert o.explain("nope")["status"] == "no_such_turn"
    assert o.diff()["status"] == "no_active_generation"


def test_cli_persona_family(mods, ops):
    import argparse
    cli = mods["cli"]
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="volmarr_action")
    # register_cli expects the volmarr parser itself.
    volmarr_parser = sub.add_parser("volmarr")
    cli.register_cli(volmarr_parser)
    args = parser.parse_args(["volmarr", "persona", "status", "--json"])
    import io
    from contextlib import redirect_stdout
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = cli.health_command(args, ctx=_Ctx())
    assert rc == 0
    record = json.loads(buf.getvalue())
    assert record["persona_id"] == PID
    # The bounded editor verb, dry-run through the same CLI path:
    # writes nothing without --confirm.
    found = ops.search("shell policy")
    sid = found["results"][0]["stable_id"]
    src = get_hermes_home() / found["results"][0]["path"]
    before = src.read_bytes()
    args2 = parser.parse_args(
        ["volmarr", "persona", "edit", sid, "--text", "replacement", "--json"])
    buf2 = io.StringIO()
    with redirect_stdout(buf2):
        rc2 = cli.health_command(args2, ctx=_Ctx())
    assert rc2 == 0
    assert json.loads(buf2.getvalue())["status"] == "dry_run"
    assert src.read_bytes() == before
