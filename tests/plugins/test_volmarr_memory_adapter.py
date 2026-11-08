"""Contracts for the old-tool memory adapter (W06 / M4, P.014).

Invariants (draft section 4.5): a write that fits the hot caps
behaves exactly as stock and lands hot+full; a write that would
overflow SUCCEEDS in the full store and says so plainly
(landed_in full_store, in_hot_view false) -- no silent
truncation, no hard-refusal cliff; pinned-entry (matched_entry)
approval semantics are preserved, including the stale refusal;
entry edits against a free-form authored document are refused by
name instead of silently normalising authored bytes, while add
stays append-only and byte-preserving there.
"""

from __future__ import annotations

import importlib
import shutil
from pathlib import Path

import pytest

from hermes_constants import get_hermes_home

NS = "profile:w06-adapter"

ENTRY_DOC = "First durable fact.\n\u00a7\nSecond durable fact."

AUTHORED_DOC = (
    "# Long-Term Memory\n\n"
    "## Travel\n\nThe ferry leaves at dawn; needle amber lantern.\n"
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
               for name in ("memory_corpus", "memory_adapter")}
    finally:
        manager.unload()
    return out


def _stage(mods, tmp_path, memory_text: bytes | str | None):
    root = Path.home() / f".hermes-w06-adapter-{tmp_path.name}"
    shutil.rmtree(root, ignore_errors=True)
    (root / "memories").mkdir(parents=True)
    if memory_text is not None:
        data = memory_text if isinstance(memory_text, bytes) \
            else memory_text.encode("utf-8")
        (root / "memories/MEMORY.md").write_bytes(data)
    corpus = mods["memory_corpus"].MemoryCorpus(root, namespace_id=NS)
    if memory_text is not None:
        corpus.import_corpus(confirm=True)
        corpus.sync_index()
    adapter = mods["memory_adapter"].MemoryAdapter(corpus)
    return root, corpus, adapter


@pytest.fixture()
def entry_env(mods, tmp_path):
    root, corpus, adapter = _stage(mods, tmp_path, ENTRY_DOC)
    yield root, corpus, adapter
    shutil.rmtree(root, ignore_errors=True)


def test_add_within_caps_lands_hot_and_full(entry_env):
    _root, _corpus, adapter = entry_env
    out = adapter.add("memory", "Third durable fact.")
    assert out["success"] is True
    assert out["landed_in"] == "hot_and_full"
    assert out["in_hot_view"] is True
    assert out["in_full_store"] is True
    assert "Third durable fact." in adapter.corpus.target_path(
        "memory").read_text(encoding="utf-8")


def test_add_duplicate_is_idempotent(entry_env):
    _root, _corpus, adapter = entry_env
    out = adapter.add("memory", "First durable fact.")
    assert out["success"] is True
    assert "already exists" in out["message"]


def test_overflow_add_succeeds_in_full_store_only(entry_env):
    root, corpus, adapter = entry_env
    big = "Overflow fact " + ("x" * 3000)
    out = adapter.add("memory", big)
    assert out["success"] is True
    assert out["landed_in"] == "full_store"
    assert out["in_hot_view"] is False
    assert out["in_full_store"] is True
    assert "NOT in the hot view" in out["message"]
    # The full store holds it complete and exactly recallable.
    corpus.sync_index()
    found = corpus.retrieve("Overflow fact")
    assert found["results"]
    text = (root / "memories/MEMORY.md").read_text(encoding="utf-8")
    assert big in text  # complete, never truncated
    assert out["memory_status"]["snapshot_over_cap"]["memory"] is True


def test_replace_patch_remove_on_entry_model(entry_env):
    _root, _corpus, adapter = entry_env
    out = adapter.replace("memory", "Second durable fact.",
                          "Second fact, revised.")
    assert out["success"] is True and out["landed_in"] == "hot_and_full"
    assert out["replaced_entry"] == "Second durable fact."
    out = adapter.patch("memory", "revised", "rewritten")
    assert out["success"] is True
    assert out["patched_entry_after"] == "Second fact, rewritten."
    out = adapter.remove("memory", "First durable fact.")
    assert out["success"] is True
    assert out["removed_entry"] == "First durable fact."
    remaining = adapter.corpus.target_path("memory").read_text(
        encoding="utf-8")
    assert remaining == "Second fact, rewritten."


def test_pinned_entry_stale_refusal(entry_env):
    _root, _corpus, adapter = entry_env
    out = adapter.replace(
        "memory", "Second", "hijacked",
        matched_entry="An entry that was never there.")
    assert out["success"] is False
    assert out["failure_class"] == "stale_entry"
    text = adapter.corpus.target_path("memory").read_text(
        encoding="utf-8")
    assert "hijacked" not in text  # nothing applied
    ok = adapter.replace(
        "memory", "Second", "Second, pinned.",
        matched_entry="Second durable fact.")
    assert ok["success"] is True


def test_ambiguous_and_no_match_refusals(entry_env):
    _root, _corpus, adapter = entry_env
    out = adapter.remove("memory", "durable fact")
    assert out["success"] is False
    assert out["failure_class"] == "ambiguous"
    out = adapter.remove("memory", "nonexistent needle")
    assert out["success"] is False
    assert out["failure_class"] == "no_match"


def test_entry_edit_refused_on_authored_doc_but_add_appends(mods, tmp_path):
    root, corpus, adapter = _stage(mods, tmp_path, AUTHORED_DOC)
    try:
        out = adapter.replace("memory", "ferry", "hijacked")
        assert out["success"] is False
        assert out["failure_class"] == "not_entry_model"
        assert (root / "memories/MEMORY.md").read_bytes() == AUTHORED_DOC
        added = adapter.add("memory", "Appended through the adapter.")
        assert added["success"] is True
        data = (root / "memories/MEMORY.md").read_bytes()
        assert data[:len(AUTHORED_DOC)] == AUTHORED_DOC  # prefix intact
        assert data.endswith(b"Appended through the adapter.")
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_status_block_is_truthful(entry_env):
    _root, _corpus, adapter = entry_env
    status = adapter.status("memory")
    assert status["hot_cap_chars"] == 2200
    assert status["hot_chars"] == len(ENTRY_DOC)
    assert status["full_store_bytes"]["memory"] == len(
        ENTRY_DOC.encode("utf-8"))
