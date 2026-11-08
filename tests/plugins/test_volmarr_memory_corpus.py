"""Contracts for the W06 memory corpus foundation (P.014, M1/M2).

Design: docs/modernization/P5_DESIGN_DRAFT.md sections 4.1-4.4,
4.9. Invariants: import is verbatim and dry-run-first; the empty
profile is an honest no-op; sources are never copied, rewritten
or re-encoded; the index is derived and rebuildable; writes are
transactional through the W03 manifest; the section 41 guard
refuses observation-overwrites-canon; backup excludes the index
and restore rebuilds it.
"""

from __future__ import annotations

import hashlib
import importlib
import shutil
from pathlib import Path

import pytest

from hermes_constants import get_hermes_home

NS = "profile:w06-test"

MEMORY_DOC = (
    "# Long-Term Memory\n\n"
    "## Travel\n\nThe ferry to the northern skerries leaves at dawn; "
    "the needle phrase is amber lantern quay.\n\n"
    "## Garden\n\nWild berries and herbal teas, forest walks.\n"
).encode("utf-8")

USER_DOC = (
    "# User Profile\n\n"
    "## Preferences\n\nPlain words first; the user needle is "
    "copper kettle song.\n"
).encode("utf-8")


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
               for name in ("memory_corpus", "canonical_library",
                            "persona_index")}
    finally:
        manager.unload()
    return out


@pytest.fixture()
def stage(tmp_path):
    root = Path.home() / f".hermes-w06-test-{tmp_path.name}"
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True)
    yield root
    shutil.rmtree(root, ignore_errors=True)


def _corpus(mods, root):
    return mods["memory_corpus"].MemoryCorpus(root, namespace_id=NS)


def _write(root: Path, rel: str, data: bytes) -> Path:
    target = root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return target


def _populated(mods, stage):
    _write(stage, "memories/MEMORY.md", MEMORY_DOC)
    _write(stage, "memories/USER.md", USER_DOC)
    corpus = _corpus(mods, stage)
    corpus.import_corpus(confirm=True)
    corpus.sync_index()
    return corpus


def test_inventory_maps_known_files_and_reports_unmapped(mods, stage):
    _write(stage, "memories/MEMORY.md", MEMORY_DOC)
    _write(stage, "memories/USER.md", USER_DOC)
    _write(stage, "memories/NOTES.txt", b"loose notes\n")
    inv = _corpus(mods, stage).inventory()
    by_name = {f["name"]: f for f in inv["files"]}
    assert by_name["MEMORY.md"]["role"] == "memory"
    assert by_name["USER.md"]["role"] == "user"
    assert by_name["NOTES.txt"]["status"] == "unmapped"
    assert by_name["MEMORY.md"]["sha256"] == \
        hashlib.sha256(MEMORY_DOC).hexdigest()


def test_dry_run_moves_nothing_and_commits_nothing(mods, stage):
    _write(stage, "memories/MEMORY.md", MEMORY_DOC)
    _write(stage, "memories/USER.md", USER_DOC)
    corpus = _corpus(mods, stage)
    report = corpus.import_corpus()  # no confirm -> dry run only
    assert all(f["unchanged_after"] for f in report["files"])
    assert corpus.library.store.load()["generation"] == 0
    assert (stage / "memories/MEMORY.md").read_bytes() == MEMORY_DOC


def test_confirmed_import_is_verbatim(mods, stage):
    corpus = _populated(mods, stage)
    status = corpus.status()
    assert status["generation"] >= 1
    for target, doc in (("memory", MEMORY_DOC), ("user", USER_DOC)):
        row = status["targets"][target]
        assert row["ingested"] is True
        assert row["sha256"] == hashlib.sha256(doc).hexdigest()
        assert row["full_store_bytes"] == len(doc)
        assert row["trust_class"] == "authored-canon"
        assert row["privacy_class"] == "private"
    # Sources untouched by import.
    assert (stage / "memories/MEMORY.md").read_bytes() == MEMORY_DOC
    assert (stage / "memories/USER.md").read_bytes() == USER_DOC


def test_empty_profile_import_is_honest_noop(mods, stage):
    corpus = _corpus(mods, stage)
    result = corpus.import_corpus(confirm=True)
    assert result["status"] == "empty"
    assert result["documents"] == []
    # No stub files were manufactured.
    assert not (stage / "memories/MEMORY.md").exists()
    assert not (stage / "memories/USER.md").exists()


def test_retrieval_and_hash_verified_citation(mods, stage):
    corpus = _populated(mods, stage)
    found = corpus.retrieve("amber lantern quay")
    assert found["results"], "buried phrase must be recalled"
    top = found["results"][0]
    assert "amber lantern quay" in top["text"]
    cited = corpus.cite(top["stable_id"])
    assert "amber lantern quay" in cited["text"]
    assert cited["section_sha256"] == top["section_sha256"]
    assert found["receipt"]["cloud_egress"] == 0


def test_cloud_destination_refuses_private_sources(mods, stage):
    corpus = _populated(mods, stage)
    local = corpus.retrieve("copper kettle")
    assert local["results"]
    stable_id = local["results"][0]["stable_id"]
    cloud = corpus.retrieve("copper kettle", destination="cloud")
    assert cloud["results"] == []
    assert cloud["receipt"]["privacy_refused"]
    assert cloud["receipt"]["privacy_refused"][0]["stable_id"] == stable_id
    with pytest.raises(mods["memory_corpus"].MemoryCorpusError):
        corpus.cite(stable_id, destination="cloud")


def test_index_repair_rebuilds_identical_results(mods, stage):
    corpus = _populated(mods, stage)
    before = corpus.retrieve("amber lantern quay")
    ids_before = [r["stable_id"] for r in before["results"]]
    report = corpus.repair_index()
    assert report["after"]["status"] == "current"
    after = corpus.retrieve("amber lantern quay")
    assert [r["stable_id"] for r in after["results"]] == ids_before
    # Canonical bytes never touched by repair.
    assert (stage / "memories/MEMORY.md").read_bytes() == MEMORY_DOC


def test_status_block_reports_full_vs_hot_honestly(mods, stage):
    corpus = _populated(mods, stage)
    block = corpus.status_block()
    assert block["full_store_bytes"]["memory"] == len(MEMORY_DOC)
    assert block["snapshot_caps"] == {"memory": 2200, "user": 1375}
    assert block["corpus_generation"] >= 1
    assert block["index_status"] == "current"


def test_append_entry_preserves_prior_bytes(mods, stage):
    corpus = _populated(mods, stage)
    info = corpus.append_entry("memory", "A new durable fact.")
    data = (stage / "memories/MEMORY.md").read_bytes()
    assert data.startswith(MEMORY_DOC.rstrip(b"\n")) or \
        data[:len(MEMORY_DOC)] == MEMORY_DOC
    assert data.endswith(b"A new durable fact.")
    assert info["generation"] >= 2
    assert corpus.library.verify(corpus.document_id("memory"))


def test_section_replace_and_stale_pin_refusal(mods, stage):
    corpus = _populated(mods, stage)
    found = corpus.retrieve("amber lantern")
    stable_id = found["results"][0]["stable_id"]
    cited = corpus.cite(stable_id)
    new_text = cited["text"].replace("amber lantern quay",
                                     "amber lantern harbour")
    out = corpus.replace_section_text(
        stable_id, new_text,
        expected_section_sha256=cited["section_sha256"])
    assert out["stable_id"] == stable_id
    assert b"amber lantern harbour" in \
        (stage / "memories/MEMORY.md").read_bytes()
    # The old pin is now stale and must be refused.
    with pytest.raises(mods["memory_corpus"].MemoryCorpusError):
        corpus.replace_section_text(
            stable_id, "anything",
            expected_section_sha256=cited["section_sha256"])


def test_observation_guard_and_derived_observations(mods, stage):
    corpus = _populated(mods, stage)
    found = corpus.retrieve("amber lantern")
    stable_id = found["results"][0]["stable_id"]
    cited = corpus.cite(stable_id)
    with pytest.raises(
            mods["memory_corpus"].ObservationOverwriteRefused):
        corpus.replace_section_text(
            stable_id, "agent rewrite of canon",
            expected_section_sha256=cited["section_sha256"],
            provenance="agent-observed")
    record = corpus.record_observation(
        "memory", "The user mentioned a ferry once.")
    assert record["provenance"] == "agent-observed"
    assert corpus.list_observations()[0]["content"].startswith("The user")
    # Canon bytes are untouched by the observation.
    assert (stage / "memories/MEMORY.md").read_bytes() == MEMORY_DOC


def test_backup_excludes_index_and_restore_rebuilds(mods, stage, tmp_path):
    corpus = _populated(mods, stage)
    backup_dir = stage / "backup-out"
    manifest = corpus.backup(backup_dir)
    assert manifest["index_included"] is False
    assert manifest["encryption"] == "none-unencrypted-local"
    assert not (backup_dir / "sections.sqlite").exists()
    dest = Path.home() / f".hermes-w06-restore-{tmp_path.name}"
    shutil.rmtree(dest, ignore_errors=True)
    try:
        mc = mods["memory_corpus"]
        report = mc.MemoryCorpus.restore(backup_dir, dest, namespace_id=NS)
        assert report["repair"]["after"]["status"] == "current"
        restored = mc.MemoryCorpus(dest, namespace_id=NS)
        found = restored.retrieve("copper kettle song")
        assert found["results"]
        cited = restored.cite(found["results"][0]["stable_id"])
        assert "copper kettle song" in cited["text"]
        assert (dest / "memories/MEMORY.md").read_bytes() == MEMORY_DOC
    finally:
        shutil.rmtree(dest, ignore_errors=True)
