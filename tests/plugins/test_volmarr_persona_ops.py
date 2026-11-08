"""W07/P6 persona operations: the section 12 command table, live.

Every command runs against a real fixture profile built in the
test home (persona config + authored files + W03 library + W04
index). Ground truth is computed independently in the test
(hashlib over the fixture bytes). The example-record canary:
fixture values (persona id, display name, needle phrases) differ
from every roadmap example, and the builders' example records
(Caducea, zero hash) are asserted ABSENT from command output --
a command regurgitating an example fails loudly here.
"""

from __future__ import annotations

import hashlib
import importlib
import json
from pathlib import Path

import pytest
import yaml

from hermes_constants import get_hermes_home

PID = "opsette"
DISPLAY = "Opsette Zqx Tester"
NEEDLE = "zqx buried needle opsette seven"

CORE_DOC = f"""# Core Identity

I am Opsette, a fixture persona for the W07 battery.

# Buried Lore

Deep in the corpus sits the {NEEDLE} phrase, hidden well.

# Communication Style

Plain words first.
"""

BIBLE_DOC = """# Shell Policy

Never force-push. Always verify the remote.

# Coding Preferences

Test everything twice.
"""

DIARY_DOC = """# Private Notes

The operator secret zqx diary phrase must never egress.
"""


class _Ctx:
    def __init__(self, config=None):
        self._config = dict(config or {})

    def get_config(self, key, default=None):
        return self._config.get(key, default)


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
                            "persona_index", "persona_live")}
    finally:
        manager.unload()
    return out


def _write_persona(home: Path) -> None:
    (home / "SOUL.md").unlink(missing_ok=True)
    persona_dir = home / "persona"
    persona_dir.mkdir(parents=True, exist_ok=True)
    (persona_dir / "core.md").write_text(CORE_DOC, encoding="utf-8")
    (persona_dir / "bible.md").write_text(BIBLE_DOC, encoding="utf-8")
    (persona_dir / "diary.md").write_text(DIARY_DOC, encoding="utf-8")
    config_dir = home / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "persona.yaml").write_text(yaml.safe_dump({"persona": {
        "id": PID, "display_name": DISPLAY, "directory": "./persona",
        "documents": {
            "core": {"file": "core.md", "required": True},
            "service_bible": {"file": "bible.md", "required": True},
            "memory": {"file": "diary.md", "required": False},
        },
        "anchors": ["Never invent a fact."],
        "anti_anchors": ["Never become a generic corporate assistant."],
    }}, sort_keys=False), encoding="utf-8")


@pytest.fixture()
def ops(mods):
    home = get_hermes_home()
    _write_persona(home)
    lib = mods["canonical_library"].CanonicalLibrary(home, PID)
    lib.ingest("persona/core.md", "core", privacy_class="public")
    lib.ingest("persona/bible.md", "service_bible",
               privacy_class="shared")
    lib.ingest("persona/diary.md", "memory", privacy_class="private")
    # Shared bible lists the cloud destination explicitly.
    store = mods["canonical_library"].ManifestStore(home)
    manifest = store.load()
    from hermes_cli import plugins as _p  # noqa: F401  (package anchor)
    for record in manifest["documents"].values():
        if record["role"] == "service_bible":
            record["destinations"] = ["cloud"]
            store.commit([mods["canonical_library"].DocumentRecord.from_dict(record)],
                         persona_id=PID)
    o = mods["persona_ops"].PersonaOps(_Ctx(), home=home)
    o.ensure_library()
    return o


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def test_status_and_files_match_ground_truth(ops):
    home = get_hermes_home()
    status = ops.status()
    assert status["status"] == "ok"
    assert status["persona_id"] == PID
    assert status["document_count"] == 3
    expected_bytes = sum(
        (home / "persona" / name).stat().st_size
        for name in ("core.md", "bible.md", "diary.md"))
    assert status["corpus_bytes"] == expected_bytes
    assert status["privacy_counts"] == {"public": 1, "shared": 1, "private": 1}
    assert status["effective_privacy"] == "private"
    assert status["gateway"]["state"] == "gateway_not_running"
    files = ops.files()
    assert files["status"] == "ok"
    for row in files["documents"]:
        raw = (home / row["path"]).read_bytes()
        assert row["sha256"] == _sha(raw)
        assert row["live_sha256"] == _sha(raw)
        assert row["verified"] is True
        assert row["byte_length"] == len(raw)
    # Canary: no roadmap example material anywhere.
    blob = json.dumps({"status": status, "files": files})
    assert "Caducea" not in blob
    assert "0" * 64 not in blob.replace(status["kernel_sha256"], "")


def test_search_buried_needle_and_citation(ops):
    out = ops.search(NEEDLE)
    assert out["status"] == "ok"
    assert out["results"], "buried needle not retrieved"
    hit = out["results"][0]
    assert NEEDLE in hit["text"]
    assert hit["privacy_class"] == "public"
    assert out["receipt"]["cloud_egress"] == 0


def test_inspect_live_compile_and_section(ops):
    out = ops.inspect()
    assert out["status"] == "ok"
    assert out["record"]["persona"] == DISPLAY
    assert out["record"]["documents"] == 3
    assert out["record"]["status"] == "VALID"
    # A section inspect verifies against source bytes.
    files = ops.files()
    core = next(r for r in files["documents"] if r["role"] == "core")
    manifest = ops._index()._manifest()
    sections = manifest["documents"][core["document_id"]]["sections"]
    buried = next(s for s in sections if NEEDLE.encode() in
                  (get_hermes_home() / core["path"]).read_bytes()
                  [s["byte_start"]:s["byte_end"]])
    sec = ops.inspect(buried["stable_id"])
    assert sec["section"]["verified"] is True
    assert NEEDLE in sec["section"]["text"]


def test_validate_clean_then_fault_injection(ops, mods):
    assert ops.validate()["valid"] is True
    home = get_hermes_home()
    # Anchor/anti-anchor collision.
    cfg_path = home / "config" / "persona.yaml"
    good = cfg_path.read_text(encoding="utf-8")
    cfg = yaml.safe_load(good)
    cfg["persona"]["anti_anchors"] = ["Never invent a fact."]
    cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
    ops2 = mods["persona_ops"].PersonaOps(_Ctx(), home=home)
    kinds = {i["kind"] for i in ops2.validate()["issues"]}
    assert "anchor_anti_anchor_collision" in kinds
    cfg_path.write_text(good, encoding="utf-8")
    # Invalid UTF-8 with a named offset.
    diary = home / "persona" / "diary.md"
    raw = diary.read_bytes()
    diary.write_bytes(raw + b"\xff\xfe broken")
    ops3 = mods["persona_ops"].PersonaOps(_Ctx(), home=home)
    bad = [i for i in ops3.validate()["issues"] if i["kind"] == "invalid_utf8"]
    assert bad and bad[0]["offset"] == len(raw)
    diary.write_bytes(raw)
    # Symlink escape.
    diary.unlink()
    diary.symlink_to("/etc/hostname")
    ops4 = mods["persona_ops"].PersonaOps(_Ctx(), home=home)
    kinds = {i["kind"] for i in ops4.validate()["issues"]}
    assert "symlink_escape" in kinds or "compile_refused" in kinds
    diary.unlink()
    diary.write_bytes(raw)


def test_reload_dry_run_purity_and_diff(ops):
    home = get_hermes_home()
    first = ops.reload_activate()
    assert first["status"] == "ok"
    assert first["activation_scope"] in ("next_gateway_start", "live_next_turn")
    active_before = ops.store.read_pointer()["generation"]
    dry = ops.reload_dry_run()
    assert dry["status"] == "ok" and dry["dry_run"] is True
    assert ops.store.read_pointer()["generation"] == active_before
    assert ops.diff()["record"]["changed"] is False
    # Edit one section on disk: diff names exactly that change.
    core = home / "persona" / "core.md"
    core.write_text(CORE_DOC + "\n# Extra Heading\n\nA brand new directive line.\n",
                    encoding="utf-8")
    ops.ensure_library()
    changed = ops.diff()
    assert changed["status"] == "ok"
    assert changed["record"]["changed"] is True
    core.write_text(CORE_DOC, encoding="utf-8")
    ops.ensure_library()


def test_reload_activate_live_scope_with_w05_state(ops, mods):
    live_state = mods["persona_live"].PersonaLiveState(_Ctx())
    live_ops = mods["persona_ops"].PersonaOps(_Ctx(), home=get_hermes_home(),
                                              live_state=live_state)
    live_state.ensure()
    out = live_ops.reload_activate()
    assert out["status"] == "ok"
    assert out["activation_scope"] == "live_next_turn"
    assert out["live_generation"] is not None


def test_export_import_dry_run_round_trip(ops, tmp_path):
    exported = ops.export_bundle(tmp_path / "opsette.persona")
    assert exported["status"] == "ok"
    assert exported["record"]["persona_id"] == PID
    before = {row["path"]: row["live_sha256"] for row in ops.files()["documents"]}
    plan = ops.import_dry_run(tmp_path / "opsette.persona")
    assert plan["status"] == "ok" and plan["mutated"] is False
    assert plan["plan"]["collision"] is True
    assert plan["plan"]["action"] == "refuse"
    after = {row["path"]: row["live_sha256"] for row in ops.files()["documents"]}
    assert before == after


def test_backup_restore_and_corruption_refusal(ops, tmp_path):
    home = get_hermes_home()
    backup_dir = tmp_path / "snap"
    out = ops.backup(backup_dir)
    assert out["status"] == "ok"
    assert out["encryption"] == "unencrypted-local"
    target = tmp_path / "restored-home"
    restored = ops.restore(backup_dir, target)
    assert restored["status"] == "ok"
    for name in ("core.md", "bible.md", "diary.md"):
        assert (target / "persona" / name).read_bytes() == \
            (home / "persona" / name).read_bytes()
    # One corrupted byte refuses the whole restore.
    victim = backup_dir / "receipts.json"
    data = bytearray(victim.read_bytes())
    data[0] = (data[0] + 1) % 256
    victim.write_bytes(bytes(data))
    with pytest.raises(ops.__class__.__mro__[1].__class__ if False else Exception):
        ops.restore(backup_dir, tmp_path / "restored2")
