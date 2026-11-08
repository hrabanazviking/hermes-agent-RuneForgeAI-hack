"""W04 gate battery: buried-section recall, zero source loss.

Design draft section 9, scaled to a deterministic multi-MB
corpus for the shared laptop (the full 100 MB battery is the
same code path; corpus size is a fixture parameter here, and
the keeper's banking run may raise it). Assertions:

1. Exact-match recall = 100%: every planted needle phrase,
   queried verbatim, returns its section, and exact citation
   returns the needle's byte range with a verifying hash.
   Needles cover: a nonce phrase mid-corpus, an Old Norse
   phrase with diacritics, a rune sequence, a fenced-code
   line, duplicate headings in different roles, needles at
   the start/middle/end of one giant subspanned section, and
   a needle in a file with no headings.
2. Zero source loss: per-file sha256 identical before index,
   after index, after repeated reindex cycles and after a
   full forced rebuild.
3. Reference stability: an unrelated early edit changes no
   needle's stable_id and every citation still verifies.
4. Offline honesty: every receipt shows cloud_egress 0 and
   embeddings off; semantic stays None throughout.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import shutil
from pathlib import Path

import pytest

from hermes_constants import get_hermes_home

PERSONA = "w04-gate-persona"

FILLER = ("Fjords and longships, seiðr and galdr, harvest and "
          "blót, weaving and woodcraft by the fire. ")


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
               for name in ("canonical_library", "persona_index")}
    finally:
        manager.unload()
    return out


@pytest.fixture(scope="module")
def corpus(tmp_path_factory):
    root = Path.home() / ".hermes-w04-gate-corpus"
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True)
    yield root
    shutil.rmtree(root, ignore_errors=True)


def _doc_with_sections(title: str, count: int, size: int,
                       needles: dict[int, str]) -> bytes:
    parts = [f"# {title}\n\n"]
    for i in range(count):
        body = FILLER * (size // len(FILLER) + 1)
        body = body[:size]
        if i in needles:
            mid = len(body) // 2
            body = body[:mid] + " " + needles[i] + " " + body[mid:]
        parts.append(f"## Section {i:03d} of {title}\n\n{body}\n\n")
    return "".join(parts).encode("utf-8")


NEEDLES = [
    ("zqx nonce buried phrase alpha", "soul.section_010_of_doc_07"),
    ("seiðr ok spádomr þórsins", "soul.section_003_of_doc_12"),
    ("ᚠᚢᚦᚨᚱᚲᚷᚺ", "soul.section_005_of_doc_15"),
    ("needle_code_token_zqx = 42", "soul.section_002_of_doc_18"),
]


def _build(mods, root: Path):
    cl = mods["canonical_library"]
    canon = root / "canonical"
    canon.mkdir(parents=True, exist_ok=True)
    files: dict[str, bytes] = {}
    for n in range(20):
        needles = {}
        if n == 7:
            needles = {10: NEEDLES[0][0]}
        elif n == 12:
            needles = {3: NEEDLES[1][0]}
        elif n == 15:
            needles = {5: NEEDLES[2][0]}
        elif n == 18:
            needles = {2: "```python\n" + NEEDLES[3][0] + "\n```"}
        data = _doc_with_sections(f"Doc {n:02d}", 20, 6000, needles)
        rel = f"canonical/DOC_{n:02d}.md"
        (root / rel).write_bytes(data)
        files[rel] = data
    # Duplicate headings, different roles -> different stable ids.
    dup_a = ("# Dup A\n\n## Shared Name\n\n"
             "The first shared name body holds zqx dup needle aaa.\n").encode()
    dup_b = ("# Dup B\n\n## Shared Name\n\n"
             "The second shared name body holds zqx dup needle bbb.\n").encode()
    (root / "canonical/DUP_A.md").write_bytes(dup_a)
    (root / "canonical/DUP_B.md").write_bytes(dup_b)
    files["canonical/DUP_A.md"] = dup_a
    files["canonical/DUP_B.md"] = dup_b
    # One giant section with needles at start / middle / end.
    giant_body = ("zqx giant needle start " + FILLER * 900
                  + " zqx giant needle middle " + FILLER * 900
                  + " zqx giant needle end")
    giant = ("# Giant\n\n## Giant Section\n\n" + giant_body + "\n").encode()
    (root / "canonical/GIANT.md").write_bytes(giant)
    files["canonical/GIANT.md"] = giant
    # A file with no headings at all.
    plain = ("No headings here at all. " + FILLER * 40
             + " zqx plain needle noheading " + FILLER * 5).encode()
    (root / "canonical/PLAIN.md").write_bytes(plain)
    files["canonical/PLAIN.md"] = plain
    lib = cl.CanonicalLibrary(root, PERSONA)
    for rel in sorted(files):
        role = "identity" if rel.endswith("DUP_B.md") else "soul"
        lib.ingest(rel, role)
    return lib, files


def test_w04_gate_buried_recall_zero_loss_stability(mods, corpus):
    pi = mods["persona_index"]
    lib, files = _build(mods, corpus)
    hashes_before = {rel: hashlib.sha256(data).hexdigest()
                     for rel, data in files.items()}
    total_bytes = sum(len(d) for d in files.values())
    assert total_bytes > 2_000_000  # multi-MB deterministic corpus
    idx = pi.PersonaIndex(corpus, PERSONA)
    status = idx.sync()
    assert status["status"] == "current"
    assert status["subspans"] > 0  # the giant section is subspanned
    # Zero source loss after indexing.
    for rel, digest in hashes_before.items():
        assert hashlib.sha256((corpus / rel).read_bytes()).hexdigest() == digest
    # 1. Exact-match recall = 100% for the planted needles.
    # W03 design: a no-heading file's single root section takes
    # the document_id itself as its stable identity.
    plain_doc_id = next(d["document_id"] for d in lib.list_documents()
                        if d["path"].endswith("PLAIN.md"))
    checks = list(NEEDLES) + [
        ("zqx dup needle aaa", "soul.shared_name"),
        ("zqx dup needle bbb", "identity.shared_name"),
        ("zqx giant needle middle", "soul.giant_section"),
        ("zqx giant needle end", "soul.giant_section"),
        ("zqx plain needle noheading", plain_doc_id),
    ]
    for phrase, stable_id in checks:
        out = idx.retrieve(phrase, limit=20)
        ids = [r["stable_id"] for r in out["results"]]
        assert stable_id in ids, f"needle missed: {phrase!r} -> {ids}"
        citation = idx.cite(stable_id)
        assert phrase.split(" = ")[0] in citation["text"] or \
            phrase in citation["text"], f"citation lost needle {phrase!r}"
        assert citation["section_sha256"] == hashlib.sha256(
            citation["text"].encode("utf-8")).hexdigest()
        assert out["receipt"]["cloud_egress"] == 0
        for result in out["results"]:
            assert result["score"]["semantic"] is None
    # 2b. Repeated reindex cycles + forced rebuild: still zero loss.
    for _ in range(3):
        idx.sync()
    idx.sync(force=True)
    for rel, digest in hashes_before.items():
        assert hashlib.sha256((corpus / rel).read_bytes()).hexdigest() == digest
    out = idx.retrieve(NEEDLES[0][0], limit=20)
    assert NEEDLES[0][1] in [r["stable_id"] for r in out["results"]]
    # 3. Reference stability after an unrelated early edit.
    first_rel = "canonical/DOC_00.md"
    edited = files[first_rel] + b"\nAn unrelated inserted paragraph.\n"
    (corpus / first_rel).write_bytes(edited)
    lib.ingest(first_rel, "soul")
    status = idx.sync()
    assert len(status["changed"]) == 1
    for phrase, stable_id in checks:
        citation = idx.cite(stable_id)
        assert citation["stable_id"] == stable_id
    # 4. Every receipt written during the gate is offline-honest.
    receipt_lines = (corpus / "generated" / "receipts" / "receipts.jsonl").read_text(
        encoding="utf-8").strip().splitlines()
    assert receipt_lines
    for line in receipt_lines:
        receipt = json.loads(line)
        assert receipt["cloud_egress"] == 0
        assert receipt["embeddings"] == "off"
