"""Contracts for the W04 / P2 persona retrieval layer (P.006/P.007).

Design: docs/modernization/P2_DESIGN_DRAFT.md; implementation:
plugins/volmarr-core/persona_index.py, built on the W03
canonical library manifest (byte ranges + source-byte hashes)
and the persona_runtime section 13 scorer (no second scorer).

Invariants under test: FTS generates candidates and section 13
still decides; citations are sliced from source at serve time
and hash-verified; paged reads concatenate byte-exactly;
subspan continuation reproduces a section exactly; receipts
record omissions with cloud_egress 0 offline; embeddings stay
absent (semantic None, bit-identical scores) until a per-source
consent record opens the gate, and revocation deletes vectors.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import shutil
from pathlib import Path

import pytest

from hermes_constants import get_hermes_home

PERSONA = "w04-test-persona"


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
               for name in ("canonical_library", "persona_index",
                            "persona_runtime")}
    finally:
        manager.unload()
    return out


@pytest.fixture()
def stage(tmp_path):
    """A library root staged directly under $HOME (ravens lesson)."""
    root = Path.home() / f".hermes-w04-test-{tmp_path.name}"
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True)
    yield root
    shutil.rmtree(root, ignore_errors=True)


def _write(root: Path, rel: str, data: bytes) -> Path:
    target = root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return target


SOUL_DOC = (
    "# Soul\n\nPreamble about the wandering seiðr practice.\n\n"
    "## Seiðr Practice\n\n"
    "The seiðr practice keeps a galdr journal and a needle phrase "
    "zqx wandering needle one for retrieval. Þórr is named here.\n\n"
    "## Quiet Garden\n\n"
    "Wild berries and herbal teas, forest walks at dawn.\n"
).encode("utf-8")

IDENTITY_DOC = (
    "# Identity\n\n"
    "## Seiðr Practice\n\n"
    "A different document sharing a heading slug with the soul "
    "document; its needle is zqx identity needle two.\n"
).encode("utf-8")


def _library(mods, stage: Path):
    cl = mods["canonical_library"]
    _write(stage, "canonical/SOUL.md", SOUL_DOC)
    _write(stage, "canonical/IDENTITY.md", IDENTITY_DOC)
    lib = cl.CanonicalLibrary(stage, PERSONA)
    lib.ingest("canonical/SOUL.md", "soul")
    lib.ingest("canonical/IDENTITY.md", "identity")
    return lib


def _index(mods, stage: Path, **kw):
    pi = mods["persona_index"]
    return pi.PersonaIndex(stage, PERSONA, **kw)


# ---------------------------------------------------------------
# P.006a/b -- index build, status, incremental discipline
# ---------------------------------------------------------------

def test_sync_builds_index_and_status_current(mods, stage):
    lib = _library(mods, stage)
    idx = _index(mods, stage)
    status = idx.sync()
    assert status["status"] == "current"
    assert status["sections"] >= 5
    assert sorted(status["changed"]) == sorted(
        d["document_id"] for d in lib.list_documents())
    again = idx.sync()
    assert again["changed"] == [] and again["status"] == "current"


def test_incremental_sync_touches_only_changed_document(mods, stage):
    lib = _library(mods, stage)
    idx = _index(mods, stage)
    idx.sync()
    edited = SOUL_DOC + b"\nAppended wandering line.\n"
    _write(stage, "canonical/SOUL.md", edited)
    record = lib.ingest("canonical/SOUL.md", "soul")
    status = idx.sync()
    assert status["changed"] == [record.document_id]
    journal = (stage / "generated" / "sections.sqlite")
    assert journal.exists()
    import sqlite3
    conn = sqlite3.connect(journal)
    rows = conn.execute(
        "SELECT document_id, change_kind FROM index_journal "
        "ORDER BY generation").fetchall()
    conn.close()
    kinds = {(r[0], r[1]) for r in rows}
    assert (record.document_id, "changed") in kinds


def test_index_is_derived_and_rebuildable(mods, stage):
    _library(mods, stage)
    before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
              for p in (stage / "canonical").iterdir()}
    idx = _index(mods, stage)
    idx.sync()
    (stage / "generated" / "sections.sqlite").unlink()
    status = idx.sync()
    assert status["status"] == "current" and status["sections"] >= 5
    after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
             for p in (stage / "canonical").iterdir()}
    assert before == after


# ---------------------------------------------------------------
# P.006c -- query path under the section 13 scorer
# ---------------------------------------------------------------

def test_retrieve_finds_section_with_receipt(mods, stage):
    _library(mods, stage)
    idx = _index(mods, stage)
    idx.sync()
    out = idx.retrieve("wandering needle", limit=5)
    ids = [r["stable_id"] for r in out["results"]]
    assert "soul.sei_r_practice" in ids
    receipt = out["receipt"]
    assert receipt["kind"] == "retrieval"
    assert receipt["cloud_egress"] == 0
    assert receipt["embeddings"] == "off"
    assert receipt["candidate_count"] >= 1
    assert any(c["stable_id"] == "soul.sei_r_practice"
               for c in receipt["chosen"])
    for result in out["results"]:
        assert result["score"]["semantic"] is None
    lines = (stage / "generated" / "receipts" / "receipts.jsonl").read_text(
        encoding="utf-8").strip().splitlines()
    assert json.loads(lines[-1])["receipt_id"] == receipt["receipt_id"]


def test_retrieve_scores_bit_identical_to_section13(mods, stage):
    _library(mods, stage)
    idx = _index(mods, stage)
    idx.sync()
    out = idx.retrieve("wandering needle", limit=5)
    top = next(r for r in out["results"]
               if r["stable_id"] == "soul.sei_r_practice")
    pr = mods["persona_runtime"]
    expected = pr.retrieval_score(
        {"role": "soul", "heading": "Seiðr Practice",
         "section_id": "sei_r_practice", "text": top["text"],
         "priority": top["priority"]},
        query="wandering needle",
        task_tags_=pr.classify_task("wandering needle"))
    assert top["score"] == expected


def test_retrieve_deterministic_across_rebuild(mods, stage):
    _library(mods, stage)
    idx = _index(mods, stage)
    idx.sync()
    first = idx.retrieve("needle", limit=10)
    idx.sync(force=True)
    second = idx.retrieve("needle", limit=10)
    assert [r["stable_id"] for r in first["results"]] == \
        [r["stable_id"] for r in second["results"]]
    assert [r["fused_total"] for r in first["results"]] == \
        [r["fused_total"] for r in second["results"]]


def test_retrieve_omissions_are_named(mods, stage):
    _library(mods, stage)
    idx = _index(mods, stage)
    idx.sync()
    out = idx.retrieve("needle", limit=1)
    assert len(out["results"]) == 1
    reasons = {o["reason"] for o in out["receipt"]["omitted"]}
    assert "over_budget" in reasons
    empty = idx.retrieve("zzzqqq nonexistentterm", limit=5)
    assert empty["results"] == []


def test_fallback_retrieve_is_the_incumbent_path(mods, stage):
    pi = mods["persona_index"]
    pr = mods["persona_runtime"]
    entries = [{"role": "soul", "heading": "Seiðr Practice",
                "section_id": "sei_r_practice",
                "text": "wandering needle text", "priority": 0.6}]
    assert pi.fallback_retrieve(entries, query="wandering needle") == \
        pr.retrieve_sections(entries, query="wandering needle")


# ---------------------------------------------------------------
# P.006d/e/f -- subspans, continuation, citation, paged read
# ---------------------------------------------------------------

BIG_SECTION = ("# Big\n\n## Wandering Saga\n\n" + (
    "The wandering saga line with þórr and runes ᚠᚢᚦ inside. " * 40)
    + "\n\n" + ("Filler wandering prose for the saga middle. " * 40)
    + "\n\n" + ("Final wandering prose at the saga end. " * 40)
    + "\n").encode("utf-8")


def _big_library(mods, stage: Path):
    cl = mods["canonical_library"]
    _write(stage, "canonical/BIG.md", BIG_SECTION)
    lib = cl.CanonicalLibrary(stage, PERSONA)
    lib.ingest("canonical/BIG.md", "soul")
    return lib


def test_subspan_concatenation_reproduces_section(mods, stage):
    _big_library(mods, stage)
    idx = _index(mods, stage, subspan_threshold=512, subspan_target=300,
                 subspan_overlap=32)
    status = idx.sync()
    assert status["subspans"] >= 3
    citation = idx.cite("soul.wandering_saga")
    source = (stage / "canonical" / "BIG.md").read_bytes()
    section = source[citation["byte_start"]:citation["byte_end"]]
    import sqlite3
    conn = sqlite3.connect(stage / "generated" / "sections.sqlite")
    conn.row_factory = sqlite3.Row
    pk = conn.execute("SELECT section_pk FROM sections WHERE stable_id = ?",
                      ("soul.wandering_saga",)).fetchone()["section_pk"]
    subs = conn.execute(
        "SELECT * FROM subspans WHERE section_pk = ? ORDER BY ordinal",
        (pk,)).fetchall()
    conn.close()
    rebuilt = bytearray()
    for sub in subs:
        piece = source[sub["byte_start"]:sub["byte_end"]]
        assert hashlib.sha256(piece).hexdigest() == sub["subspan_sha256"]
        rebuilt += piece[sub["overlap_prev_bytes"]:]
    assert bytes(rebuilt) == section


def test_windowed_retrieval_continuation_reproduces_section(mods, stage):
    _big_library(mods, stage)
    idx = _index(mods, stage, subspan_threshold=512, subspan_target=300,
                 subspan_overlap=32)
    idx.sync()
    out = idx.retrieve("wandering saga", limit=5, window_bytes=400)
    top = next(r for r in out["results"]
               if r["stable_id"] == "soul.wandering_saga")
    assert top["windowed"] is True
    pieces = [top["text"]]
    handle = top["more_from_this_section"]["next_handle"]
    while handle:
        step = idx.continue_read(handle, max_bytes=300)
        assert step["status"] == "ok"
        pieces.append(step["text"])
        handle = step["next_handle"]
    citation = idx.cite("soul.wandering_saga")
    assert "".join(pieces) == citation["text"]


def test_stale_handle_is_named_not_silently_served(mods, stage):
    lib = _big_library(mods, stage)
    idx = _index(mods, stage, subspan_threshold=512, subspan_target=300,
                 subspan_overlap=32)
    idx.sync()
    out = idx.retrieve("wandering saga", limit=5, window_bytes=400)
    top = next(r for r in out["results"]
               if r["stable_id"] == "soul.wandering_saga")
    handle = top["more_from_this_section"]["next_handle"]
    _write(stage, "canonical/BIG.md", BIG_SECTION + b"Changed tail.\n")
    lib.ingest("canonical/BIG.md", "soul")
    idx.sync()
    step = idx.continue_read(handle, max_bytes=300)
    assert step["status"] == "stale_continuation"
    assert step["current_first_window"] is not None


def test_citation_exact_bytes_crlf(mods, stage):
    cl = mods["canonical_library"]
    raw = b"# Doc\r\n\r\n## Trailing Spaces  \r\n\r\nBody line one.  \r\n\r\n\r\nBody after blank run.\r\n"
    _write(stage, "canonical/CRLF.md", raw)
    lib = cl.CanonicalLibrary(stage, PERSONA)
    record = lib.ingest("canonical/CRLF.md", "soul")
    idx = _index(mods, stage)
    idx.sync()
    span = next(s for s in record.sections
                if s["section_id"] == "trailing_spaces")
    got = idx.cite("soul.trailing_spaces")
    assert got["text"].encode("utf-8") == raw[span["byte_start"]:span["byte_end"]]
    assert got["section_sha256"] == span["sha256"]
    assert got["source_sha256"] == record.sha256
    assert got["mode"] == "exact_citation"


def test_citation_works_before_index_built(mods, stage):
    _library(mods, stage)
    idx = _index(mods, stage)
    got = idx.cite("soul.sei_r_practice")
    assert "zqx wandering needle one" in got["text"]
    assert got["index_status"] == "unbuilt"


def test_paged_read_concatenates_byte_exact(mods, stage):
    cl = mods["canonical_library"]
    raw = ("# Paged\n\n" + "seiðr þórr ᚠᚢᚦ text with multibyte. " * 30
           + "\n").encode("utf-8")
    _write(stage, "canonical/PAGED.md", raw)
    lib = cl.CanonicalLibrary(stage, PERSONA)
    record = lib.ingest("canonical/PAGED.md", "soul")
    idx = _index(mods, stage)
    pages = bytearray()
    cursor = 0
    while True:
        page = idx.read_page(record.document_id, cursor=cursor, max_bytes=64)
        pages += page["text"].encode("utf-8")
        if page["complete"]:
            assert page["source_sha256"] == record.sha256
            break
        cursor = page["next_cursor"]
    assert bytes(pages) == raw
    section_page = idx.read_section_page("soul.paged", max_bytes=32)
    assert section_page["byte_start"] == 0
    assert section_page["complete"] is False


# ---------------------------------------------------------------
# P.007 -- embeddings consent gate
# ---------------------------------------------------------------

def _fake_embed(text: str):
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    return [b / 255.0 for b in digest[:8]]


def test_embeddings_absent_without_consent(mods, stage):
    lib = _library(mods, stage)
    idx = _index(mods, stage)
    idx.sync()
    doc_id = lib.list_documents()[0]["document_id"]
    pi = mods["persona_index"]
    with pytest.raises(pi.ConsentError):
        idx.embed_document(doc_id, _fake_embed, provider="fake-local",
                           model="fake-embed", version="1")
    assert idx.vector_count() == 0
    out = idx.retrieve("wandering needle", limit=5,
                       query_vector=_fake_embed("wandering needle"))
    for result in out["results"]:
        assert result["score"]["semantic"] is None


def test_consent_gate_embed_retrieve_revoke(mods, stage):
    lib = _library(mods, stage)
    idx = _index(mods, stage)
    idx.sync()
    doc = next(d for d in lib.list_documents()
               if d["path"].endswith("SOUL.md"))
    consent = idx.grant_consent(
        doc["document_id"], "local", "fake-local", "fake-embed", "1",
        8, granted_by="operator")
    stored = idx.embed_document(doc["document_id"], _fake_embed,
                                provider="fake-local", model="fake-embed",
                                version="1")
    assert stored["vectors_stored"] == len(doc["sections"])
    assert idx.vector_count(doc["document_id"]) == len(doc["sections"])
    span_text = None
    source = (stage / doc["path"]).read_bytes()
    span = next(s for s in doc["sections"]
                if s["stable_id"] == "soul.sei_r_practice")
    span_text = source[span["byte_start"]:span["byte_end"]].decode("utf-8")
    out = idx.retrieve("wandering needle", limit=5,
                       query_vector=_fake_embed(span_text))
    top = next(r for r in out["results"]
               if r["stable_id"] == "soul.sei_r_practice")
    assert top["score"]["semantic"] == pytest.approx(1.0, abs=0.02)
    revoked = idx.revoke_consent(consent["consent_id"])
    assert revoked["vectors_deleted"] == len(doc["sections"])
    assert idx.vector_count(doc["document_id"]) == 0
    out2 = idx.retrieve("wandering needle", limit=5,
                        query_vector=_fake_embed(span_text))
    top2 = next(r for r in out2["results"]
                if r["stable_id"] == "soul.sei_r_practice")
    assert top2["score"]["semantic"] is None


def test_cloud_consent_for_private_source_needs_override(mods, stage):
    lib = _library(mods, stage)
    idx = _index(mods, stage)
    doc_id = lib.list_documents()[0]["document_id"]
    pi = mods["persona_index"]
    with pytest.raises(pi.ConsentError):
        idx.grant_consent(doc_id, "cloud", "some-cloud", "m", "1", 8,
                          granted_by="operator")
    consent = idx.grant_consent(doc_id, "cloud", "some-cloud", "m", "1", 8,
                                granted_by="operator", cloud_override=True)
    assert consent["cloud_override"] is True


def test_measure_tokenizers_runes_and_diacritics(mods, stage):
    pi = mods["persona_index"]
    report = pi.measure_tokenizers([
        ("the runes ᚠᚢᚦᚨᚱᚲ are carved", "ᚠᚢᚦᚨᚱᚲ"),
        ("þórr rides over miðgarðr", "þórr"),
        ("needle_code_token = 42 in a fence", "needle_code_token"),
        ("cafe society meets weekly", "café"),
    ])
    assert report["samples"] == 4
    # Trigram is the guaranteed exact-substring fallback: it
    # hits every verbatim sample except the diacritic-folded
    # one (café vs cafe), which unicode61 remove_diacritics
    # covers. Thorn is a letter, not a digraph: neither
    # tokenizer turns þórr into thor, and the harness must
    # show that honestly rather than hide it.
    assert report["trigram_hits"] == 3
    assert report["unicode61_hits"] == 4
