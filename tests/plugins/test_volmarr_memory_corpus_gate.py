"""W06 acceptance gate: 2 MB USER.md + 20 MB MEMORY.md (P.016).

Roadmap section 11 sizes, made measurable per the P5 design
draft section 6 gate item 1: deterministic generated fixtures
staged in a $HOME-level disposable profile (ravens staging law;
never the live ~/.hermes). Assertions:

1. Import is byte-identical (per-document sha256 proof) at the
   full roadmap sizes -- 2 MB USER.md, 20 MB MEMORY.md.
2. Exact recall: planted needle phrases at the start, middle
   and end of BOTH files are retrieved by exact phrase and
   cited with hash verification against the source bytes --
   no silent truncation anywhere in the matrix.
3. Paged read concatenation reproduces the 2 MB USER.md
   byte-for-byte; the 20 MB MEMORY.md verifies by export hash
   plus hash-checked citations of its buried sections.
4. Zero source loss: per-file sha256 identical before import,
   after import, after index sync, after a forced reindex and
   after index repair.
"""

from __future__ import annotations

import hashlib
import importlib
import shutil
from pathlib import Path

import pytest

from hermes_constants import get_hermes_home

NS = "profile:w06-gate"

FILLER = ("Fjords and longships, seidr and galdr, harvest and "
          "blot, weaving and woodcraft by the fire. ")

MEMORY_NEEDLES = {
    0: "gate needle memory alpha first fjord",
    1250: "gate needle memory middle hidden skerry",
    2499: "gate needle memory omega last ember",
}
USER_NEEDLES = {
    0: "gate needle user alpha first hearth",
    125: "gate needle user middle hidden loom",
    249: "gate needle user omega last word",
}


def _doc(title: str, sections: int, section_bytes: int,
         needles: dict[int, str]) -> bytes:
    parts = [f"# {title}\n\n"]
    for i in range(sections):
        body = (FILLER * (section_bytes // len(FILLER) + 1))[:section_bytes]
        if i in needles:
            mid = len(body) // 2
            body = body[:mid] + " " + needles[i] + " " + body[mid:]
        parts.append(f"## Section {i:04d} of {title}\n\n{body}\n\n")
    return "".join(parts).encode("utf-8")


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
               for name in ("memory_corpus",)}
    finally:
        manager.unload()
    return out


@pytest.fixture(scope="module")
def gate(mods):
    root = Path.home() / ".hermes-w06-gate-corpus"
    shutil.rmtree(root, ignore_errors=True)
    (root / "memories").mkdir(parents=True)
    memory_doc = _doc("Gate Memory", 2500, 8000, MEMORY_NEEDLES)
    user_doc = _doc("Gate User", 250, 8000, USER_NEEDLES)
    assert len(memory_doc) >= 20 * 1000 * 1000, len(memory_doc)
    assert len(user_doc) >= 2 * 1000 * 1000, len(user_doc)
    (root / "memories/MEMORY.md").write_bytes(memory_doc)
    (root / "memories/USER.md").write_bytes(user_doc)
    hashes = {
        "memory": hashlib.sha256(memory_doc).hexdigest(),
        "user": hashlib.sha256(user_doc).hexdigest()}
    corpus = mods["memory_corpus"].MemoryCorpus(root, namespace_id=NS)
    result = corpus.import_corpus(confirm=True)
    assert result["status"] == "imported"
    corpus.sync_index()
    yield corpus, root, hashes, memory_doc, user_doc
    shutil.rmtree(root, ignore_errors=True)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_gate_import_byte_identical_at_roadmap_sizes(gate):
    corpus, root, hashes, memory_doc, user_doc = gate
    status = corpus.status()
    assert status["targets"]["memory"]["sha256"] == hashes["memory"]
    assert status["targets"]["user"]["sha256"] == hashes["user"]
    assert status["targets"]["memory"]["full_store_bytes"] == len(memory_doc)
    assert status["targets"]["user"]["full_store_bytes"] == len(user_doc)
    assert status["targets"]["memory"]["snapshot_over_cap"] is True
    assert corpus.library.verify(corpus.document_id("memory"))
    assert corpus.library.verify(corpus.document_id("user"))


def test_gate_exact_recall_of_buried_needles(gate):
    corpus, _root, _hashes, _m, _u = gate
    for needle in list(MEMORY_NEEDLES.values()) + list(USER_NEEDLES.values()):
        found = corpus.retrieve(needle)
        assert found["results"], f"no recall for {needle!r}"
        top = found["results"][0]
        assert needle in top["text"] or top.get("windowed"), needle
        cited = corpus.cite(top["stable_id"])
        assert needle in cited["text"], needle
        assert cited["section_sha256"] == top["section_sha256"]


def test_gate_paged_read_reproduces_user_doc(gate):
    corpus, _root, hashes, _m, user_doc = gate
    doc_id = corpus.document_id("user")
    chunks: list[bytes] = []
    cursor = 0
    while True:
        page = corpus.read_page(doc_id, cursor)
        chunks.append(page["text"].encode("utf-8"))
        if page["complete"]:
            break
        cursor = page["next_cursor"]
    joined = b"".join(chunks)
    assert joined == user_doc
    assert hashlib.sha256(joined).hexdigest() == hashes["user"]


def test_gate_zero_source_loss_across_reindex_and_repair(gate):
    corpus, root, hashes, _m, _u = gate
    corpus.sync_index()
    corpus.index.sync(force=True)
    assert _sha(root / "memories/MEMORY.md") == hashes["memory"]
    assert _sha(root / "memories/USER.md") == hashes["user"]
    corpus.repair_index()
    assert _sha(root / "memories/MEMORY.md") == hashes["memory"]
    assert _sha(root / "memories/USER.md") == hashes["user"]
    found = corpus.retrieve(MEMORY_NEEDLES[1250])
    assert found["results"], "recall must survive index repair"
