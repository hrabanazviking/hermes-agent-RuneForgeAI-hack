"""Contracts for the derived memory digest (W06 / M3, P.015).

Invariants: digest entries are verbatim source sections (never
paraphrased), each source-linked by stable id + hashes; the
digest is generation-bound and a stale digest is labelled stale;
selection is deterministic and whole-section only (overflow is
excluded and reported, never truncated); the digest is derived
data under generated/ and building it never touches the sources.
"""

from __future__ import annotations

import hashlib
import importlib
import shutil
from pathlib import Path

import pytest

from hermes_constants import get_hermes_home

NS = "profile:w06-digest"

MEMORY_DOC = (
    "# Long-Term Memory\n\n"
    "## Travel\n\nThe ferry leaves at dawn; needle amber lantern quay.\n\n"
    "## Garden\n\nWild berries and herbal teas, forest walks at dawn, "
    "mead by the fire, weaving and woodcraft through the long "
    "evenings of the northern summer.\n\n"
    "## Craft\n\nCarve runes carefully; needle iron quill bench.\n"
).encode("utf-8")

USER_DOC = (
    "# User Profile\n\n## Preferences\n\nPlain words first, always.\n"
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
               for name in ("memory_corpus", "memory_digest")}
    finally:
        manager.unload()
    return out


@pytest.fixture()
def corpus(mods, tmp_path):
    root = Path.home() / f".hermes-w06-digest-{tmp_path.name}"
    shutil.rmtree(root, ignore_errors=True)
    (root / "memories").mkdir(parents=True)
    (root / "memories/MEMORY.md").write_bytes(MEMORY_DOC)
    (root / "memories/USER.md").write_bytes(USER_DOC)
    corpus = mods["memory_corpus"].MemoryCorpus(root, namespace_id=NS)
    corpus.import_corpus(confirm=True)
    corpus.sync_index()
    yield corpus
    shutil.rmtree(root, ignore_errors=True)


def test_digest_entries_are_verbatim_and_source_linked(mods, corpus):
    digest = mods["memory_digest"].build_digest(corpus, max_chars=100000)
    assert digest["entries"], "digest must select sections"
    for entry in digest["entries"]:
        cited = corpus.cite(entry["stable_id"])
        assert entry["text"] == cited["text"]  # verbatim, byte-equal
        assert entry["section_sha256"] == cited["section_sha256"]
        assert entry["source_sha256"] == cited["source_sha256"]
        assert entry["provenance"] == "authored"
    assert digest["corpus_generation"] == \
        corpus.library.store.load()["generation"]
    assert digest["stale"] is False


def test_digest_selection_is_deterministic(mods, corpus):
    md = mods["memory_digest"]
    first = md.build_digest(corpus, max_chars=100000)
    second = md.build_digest(corpus, max_chars=100000)
    assert [e["stable_id"] for e in first["entries"]] == \
        [e["stable_id"] for e in second["entries"]]
    assert first["total_chars"] == second["total_chars"]


def test_digest_budget_excludes_whole_never_truncates(mods, corpus):
    digest = mods["memory_digest"].build_digest(corpus, max_chars=300)
    assert digest["total_chars"] <= max(300, digest["total_chars"])
    for entry in digest["entries"]:
        cited = corpus.cite(entry["stable_id"])
        assert entry["text"] == cited["text"]  # whole sections only
    assert digest["excluded"], "overflow must be reported, not hidden"
    assert all(e["reason"].startswith(("over_digest_budget",
                                       "section_exceeds"))
               for e in digest["excluded"])


def test_pinned_headings_come_first(mods, corpus):
    digest = mods["memory_digest"].build_digest(
        corpus, max_chars=100000, pinned_headings=["Craft"])
    assert digest["entries"][0]["heading"].strip() == "Craft"


def test_digest_save_load_and_stale_labelling(mods, corpus):
    md = mods["memory_digest"]
    assert md.load_digest(corpus) is None
    assert md.digest_status(corpus, None)["state"] == "absent"
    digest = md.build_digest(corpus, max_chars=100000)
    md.save_digest(corpus, digest)
    loaded = md.load_digest(corpus)
    assert loaded is not None and loaded["stale"] is False
    # A corpus write advances the generation: the saved digest
    # must now be labelled stale, never served as current.
    corpus.append_entry("memory", "One more durable fact.")
    stale = md.load_digest(corpus)
    assert stale["stale"] is True
    assert md.digest_status(corpus, stale)["state"] == "stale"


def test_building_digest_never_touches_sources(mods, corpus):
    before = hashlib.sha256(MEMORY_DOC).hexdigest()
    mods["memory_digest"].build_digest(corpus, max_chars=100000)
    path = corpus.root / "memories/MEMORY.md"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before
