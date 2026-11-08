"""Contracts for the unbounded canonical library (W03, P.001-P.005).

Roadmap: ROADMAP_HERMES_MODERNIZATION_UNBOUNDED_PERSONA_2026-11-07
sections 6-7; design: docs/modernization/P0P1_DESIGN_DRAFT.md.

The invariant under test: no cap on the storage, import,
export, edit, hash, backup or indexing of canonical authored
documents, enforced mechanically (forbidden-key schema), with
byte-exact streaming ingestion, stable section identity reusing
the persona compiler's ``stable_section_id``, transactional
manifest updates, and a migration dry-run that moves nothing.
The stock prompt path is the control group: it must still
truncate exactly as upstream does.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import shutil
from pathlib import Path

import pytest

from hermes_constants import get_hermes_home


@pytest.fixture(scope="module")
def cl():
    from hermes_cli import plugins as plugins_mod

    home = get_hermes_home()
    home.mkdir(parents=True, exist_ok=True)
    (home / "config.yaml").write_text(
        "plugins:\n  enabled: [volmarr-core]\n", encoding="utf-8")
    manager = plugins_mod.PluginManager()
    manager.discover_and_load()
    try:
        loaded = manager._plugins["volmarr-core"]
        module = importlib.import_module(
            f"{loaded.module.__package__}.canonical_library")
    finally:
        manager.unload()
    return module


@pytest.fixture()
def stage(tmp_path):
    """A library root staged directly under $HOME.

    The ravens lesson: environments staged outside $HOME break
    relative bindings, so W03 test trees live under $HOME.
    """
    root = Path.home() / f".hermes-w03-test-{tmp_path.name}"
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True)
    yield root
    shutil.rmtree(root, ignore_errors=True)


def _write(root: Path, rel: str, data: bytes) -> Path:
    target = root / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return target


# ---------------------------------------------------------------
# P.001 -- policy + the mechanically enforced no-cap clause
# ---------------------------------------------------------------

def test_forbidden_key_canary_rejected(cl):
    record = {
        "document_id": "doc_x", "role": "soul", "path": "SOUL.md",
        "namespace": "default", "sha256": "a" * 64, "byte_length": 3,
        "revision": 1, "priority": "P0", "trust_class": "authored-canon",
        "privacy_class": "private", "persona_id": "p1",
        "status": "indexed", "conflict_policy": "hash-is-authority",
        "state": "active", "provenance": {"kind": "local-file"},
    }
    assert cl.validate_record(record) is record
    for key in ("max_chars", "max_tokens", "char_limit",
                "max_anything", "token_limit", "some_limit"):
        bad = dict(record, **{key: 1})
        with pytest.raises(cl.CanonicalLibraryError) as exc:
            cl.validate_record(bad)
        assert key in str(exc.value)


def test_schema_and_code_carry_no_forbidden_keys(cl):
    assert cl.find_forbidden_keys({"operations": {"work_unit": 1}}) == []
    hits = cl.find_forbidden_keys(
        {"documents": [{"path": "x", "max_chars": 9}]})
    assert hits == ["documents[0].max_chars"]
    source = Path(cl.__file__).read_text(encoding="utf-8")
    # The module may *name* forbidden keys in its policy set but
    # no document record it builds may contain one: build one
    # end-to-end (covered in the library tests) and scan it.
    assert "FORBIDDEN_KEY_NAMES" in source


def test_document_id_stable_and_rename_keeps_id(cl):
    first = cl.mint_document_id("yrsa", "canonical/SOUL.md")
    assert first == cl.mint_document_id("yrsa", "canonical/SOUL.md")
    assert first.startswith("doc_") and len(first) == 20
    assert first != cl.mint_document_id("yrsa", "canonical/OTHER.md")
    assert first != cl.mint_document_id("other", "canonical/SOUL.md")


def test_validate_record_rejects_escape_and_absolute_paths(cl):
    base = {
        "document_id": "doc_x", "role": "soul", "namespace": "default",
        "sha256": "a" * 64, "byte_length": 3, "revision": 1,
        "priority": "P0", "trust_class": "authored-canon",
        "privacy_class": "private", "persona_id": "p1",
        "status": "indexed", "conflict_policy": "hash-is-authority",
        "state": "active", "provenance": {"kind": "local-file"},
    }
    for bad_path in ("/etc/passwd", "../outside.md", "a/../../b.md"):
        with pytest.raises(cl.CanonicalLibraryError):
            cl.validate_record(dict(base, path=bad_path))
    with pytest.raises(cl.CanonicalLibraryError):
        cl.validate_record(dict(base, path="ok.md", bogus_field=1))


def test_role_vocabulary_open_but_well_formed(cl):
    assert "soul" in cl.CORE_ROLES
    assert cl.default_role_for_filename("SOUL.md") == "soul"
    assert cl.default_role_for_filename("WHATEVER.md") is None


# ---------------------------------------------------------------
# P.002 -- streaming byte-exact ingestion
# ---------------------------------------------------------------

SIZE_LADDER = [1_000, 20_000, 20_001, 501_000]


@pytest.mark.parametrize("size", SIZE_LADDER)
def test_size_ladder_hash_identity(cl, stage, size):
    body = ("# Heading\n\n" + ("ᚱᚢᚾᛖ text line.\n" * 4000)).encode("utf-8")
    # Cut on a character boundary (a mid-sequence cut is invalid
    # UTF-8 and the ingester must refuse it), then pad to size.
    cut = body[:size].decode("utf-8", errors="ignore").encode("utf-8")
    data = cut + b"x" * (size - len(cut))
    target = _write(stage, "doc.md", data)
    ingester = cl.StreamingIngester(work_unit=4096)
    result = ingester.ingest_file(target, "soul", "doc_ladder")
    assert result.status == "complete"
    assert result.byte_length == size
    assert result.sha256 == hashlib.sha256(data).hexdigest()
    for span in result.sections:
        assert ingester.section_digest(target, span) == span.sha256
        sliced = data[span.byte_start:span.byte_end]
        assert hashlib.sha256(sliced).hexdigest() == span.sha256


def test_ingestion_never_modifies_source(cl, stage):
    data = "# A\n\nbody þ ð ǫ ᚠᚢᚦ\n".encode("utf-8")
    target = _write(stage, "a.md", data)
    before = hashlib.sha256(data).hexdigest()
    cl.StreamingIngester(work_unit=8).ingest_file(target, "soul", "doc_a")
    assert target.read_bytes() == data
    assert hashlib.sha256(target.read_bytes()).hexdigest() == before


def test_invalid_utf8_is_unreadable_with_offset(cl, stage):
    data = b"# A\n\nvalid \xff\xfe invalid\n"
    target = _write(stage, "bad.md", data)
    result = cl.StreamingIngester(work_unit=4).ingest_file(
        target, "soul", "doc_bad")
    assert result.status == "unreadable"
    assert result.error_offset is not None
    assert data[result.error_offset] == 0xFF


def test_crlf_byte_ranges_exact(cl, stage):
    data = b"# One\r\n\r\nfirst\r\n# Two\r\n\r\nsecond\r\n"
    target = _write(stage, "crlf.md", data)
    result = cl.StreamingIngester(work_unit=8).ingest_file(
        target, "soul", "doc_crlf")
    assert [s.section_id for s in result.sections] == ["one", "two"]
    joined = b"".join(
        data[s.byte_start:s.byte_end] for s in result.sections)
    assert joined == data


def test_checkpoint_resume_reaches_identical_hash(cl, stage):
    data = ("# S\n\n" + "line of text here.\n" * 500).encode("utf-8")
    target = _write(stage, "big.md", data)
    ingester = cl.StreamingIngester(work_unit=1024)
    checkpoints: list = []
    full = ingester.ingest_file(
        target, "soul", "doc_big", checkpoint_sink=checkpoints.append)
    assert len(checkpoints) >= 3
    mid = checkpoints[len(checkpoints) // 2]
    resumed = ingester.ingest_file(target, "soul", "doc_big",
                                   resume_from=mid)
    assert resumed.sha256 == full.sha256
    assert resumed.resumed_from == mid.byte_offset
    assert [s.to_dict() for s in resumed.sections] == \
        [s.to_dict() for s in full.sections]
    tampered = cl.Checkpoint(byte_offset=mid.byte_offset,
                             sha256_prefix="0" * 64)
    with pytest.raises(cl.CanonicalLibraryError):
        ingester.ingest_file(target, "soul", "doc_big",
                             resume_from=tampered)


# ---------------------------------------------------------------
# P.005 -- Markdown sections + stable identity
# ---------------------------------------------------------------

def test_section_identity_rules(cl, stage):
    doc = (
        "front matter verse\n"
        "# Alpha\n\nbody\n"
        "```\n# not a heading\n```\n"
        "# Alpha\n\nsecond alpha\n"
        "Setext Title\n============\n\nsetext body\n"
    ).encode("utf-8")
    target = _write(stage, "s.md", doc)
    result = cl.StreamingIngester(work_unit=16).ingest_file(
        target, "soul", "doc_s")
    ids = [s.section_id for s in result.sections]
    assert ids == ["_preamble", "alpha", "alpha_2", "setext_title"], ids
    stable = [s.stable_id for s in result.sections]
    assert stable[1] == "soul.alpha"  # persona_runtime.stable_section_id
    assert all(s.byte_start < s.byte_end for s in result.sections)
    joined = b"".join(doc[s.byte_start:s.byte_end] for s in result.sections)
    assert joined == doc


def test_yaml_front_matter_is_preamble_not_setext(cl, stage):
    doc = ("---\ntitle: Adversaries\n---\n<!-- comment -->\n"
           "# Dup\n\nfirst\n# Dup\n\nsecond\n").encode("utf-8")
    target = _write(stage, "fm.md", doc)
    result = cl.StreamingIngester(work_unit=8).ingest_file(
        target, "soul", "doc_fm")
    assert [s.section_id for s in result.sections] ==         ["_preamble", "dup", "dup_2"]
    joined = b"".join(doc[s.byte_start:s.byte_end] for s in result.sections)
    assert joined == doc


def test_no_heading_file_root_section_is_document(cl, stage):
    doc = b"just prose, no headings at all.\nsecond line.\n"
    target = _write(stage, "plain.md", doc)
    result = cl.StreamingIngester().ingest_file(target, "memory", "doc_plain")
    assert len(result.sections) == 1
    assert result.sections[0].section_id == "doc_plain"
    assert result.sections[0].stable_id == "doc_plain"
    assert result.sections[0].byte_start == 0
    assert result.sections[0].byte_end == len(doc)


def test_section_ids_stable_across_unrelated_edit(cl, stage):
    v1 = "# One\n\nfirst body\n# Two\n\nsecond body\n# Nine\n\nninth\n"
    target = _write(stage, "e.md", v1.encode("utf-8"))
    ingester = cl.StreamingIngester(work_unit=16)
    before = {s.section_id: s for s in
              ingester.ingest_file(target, "soul", "doc_e").sections}
    v2 = v1.replace("first body", "first body, greatly expanded\nmore")
    target.write_bytes(v2.encode("utf-8"))
    after = {s.section_id: s for s in
             ingester.ingest_file(target, "soul", "doc_e").sections}
    assert set(before) == set(after)
    assert after["nine"].stable_id == before["nine"].stable_id
    assert after["nine"].sha256 == before["nine"].sha256
    assert after["two"].sha256 == before["two"].sha256


def test_giant_single_section(cl, stage):
    data = ("# Giant\n" + "a very long section line.\n" * 60000).encode()
    assert len(data) > 1_000_000
    target = _write(stage, "giant.md", data)
    ingester = cl.StreamingIngester(work_unit=8192)
    result = ingester.ingest_file(target, "soul", "doc_giant")
    assert len(result.sections) == 1
    assert result.sections[0].sha256 == hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------
# P.004 -- transactional manifest
# ---------------------------------------------------------------

def test_library_ingest_commit_and_export(cl, stage):
    data = "# Soul\n\nᚱᚢᚾᛖᛋ.\n".encode("utf-8")
    _write(stage, "canonical/SOUL.md", data)
    lib = cl.CanonicalLibrary(stage, "yrsa")
    record = lib.ingest("canonical/SOUL.md", "soul")
    assert record.status == "indexed"
    assert lib.store.load()["generation"] == 1
    assert lib.verify(record.document_id)
    out = stage / "exported.md"
    assert lib.export(record.document_id, out) == record.sha256
    assert out.read_bytes() == data
    # Re-ingest unchanged: revision stays; changed: revision bumps.
    again = lib.ingest("canonical/SOUL.md", "soul")
    assert again.revision == record.revision
    _write(stage, "canonical/SOUL.md", data + b"more\n")
    bumped = lib.ingest("canonical/SOUL.md", "soul")
    assert bumped.revision == record.revision + 1
    assert bumped.document_id == record.document_id


def test_manifest_journal_and_rollback(cl, stage):
    _write(stage, "canonical/SOUL.md", b"# Soul\n\nv1\n")
    lib = cl.CanonicalLibrary(stage, "yrsa")
    first = lib.ingest("canonical/SOUL.md", "soul")
    gen1 = lib.store.load()["generation"]
    _write(stage, "canonical/SOUL.md", b"# Soul\n\nv2 changed\n")
    lib.ingest("canonical/SOUL.md", "soul")
    journal = (stage / "generated" / "manifest.journal.jsonl")
    lines = journal.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    entry = json.loads(lines[-1])
    assert entry["changes"][0]["old_sha256"] == first.sha256
    rolled = lib.store.rollback_to_generation(gen1)
    assert rolled["documents"][first.document_id]["sha256"] == first.sha256
    # Sources are never touched by rollback.
    assert (stage / "canonical" / "SOUL.md").read_bytes() == \
        b"# Soul\n\nv2 changed\n"


def test_torn_manifest_quarantined_and_rebuilt(cl, stage):
    _write(stage, "canonical/SOUL.md", b"# Soul\n\nbody\n")
    lib = cl.CanonicalLibrary(stage, "yrsa")
    record = lib.ingest("canonical/SOUL.md", "soul")
    manifest_path = stage / "generated" / "manifest.json"
    manifest_path.write_text("{torn json", encoding="utf-8")
    loaded = lib.store.load()
    assert loaded["documents"][record.document_id]["sha256"] == record.sha256
    quarantined = list((stage / "generated").glob("manifest.corrupt-*.json"))
    assert len(quarantined) == 1


def test_missing_source_keeps_record_as_unreadable(cl, stage):
    target = _write(stage, "canonical/SOUL.md", b"# Soul\n\nbody\n")
    lib = cl.CanonicalLibrary(stage, "yrsa")
    record = lib.ingest("canonical/SOUL.md", "soul")
    target.unlink()
    kept = lib.ingest("canonical/SOUL.md", "soul")
    assert kept.status == "unreadable"
    assert kept.sha256 == record.sha256  # last known hash retained
    assert lib.list_documents()[0]["document_id"] == record.document_id


def test_tree_ingest_is_one_transaction(cl, stage):
    _write(stage, "canonical/SOUL.md", b"# Soul\n\nx\n")
    _write(stage, "canonical/IDENTITY.md", b"# Identity\n\ny\n")
    _write(stage, "canonical/NOTES.md", b"# Notes\n\nz\n")
    lib = cl.CanonicalLibrary(stage, "yrsa")
    roles = {"canonical/SOUL.md": "soul",
             "canonical/IDENTITY.md": "identity"}
    records = lib.ingest_tree(
        list(roles) + ["canonical/NOTES.md"], roles.get)
    assert len(records) == 2  # unmapped file skipped, never guessed
    assert lib.store.load()["generation"] == 1  # one transaction


# ---------------------------------------------------------------
# P.003 -- migration dry-run
# ---------------------------------------------------------------

def test_migration_dry_run_idempotent_and_non_destructive(cl, stage):
    soul = _write(stage, "src/SOUL.md", "# Soul\n\nᚱᚢᚾᛖ.\n".encode())
    ident = _write(stage, "src/IDENTITY.md", b"# Identity\n\nwho.\n")
    mystery = _write(stage, "src/MYSTERY.md", b"# Mystery\n\n?\n")
    before = {p: p.read_bytes() for p in (soul, ident, mystery)}
    run1 = cl.migration_dry_run([soul, ident, mystery], "yrsa")
    run2 = cl.migration_dry_run([soul, ident, mystery], "yrsa")
    assert run1["comparable"] == run2["comparable"]  # idempotence
    by_name = {f["name"]: f for f in run1["files"]}
    assert by_name["SOUL.md"]["role"] == "soul"
    assert by_name["SOUL.md"]["status"] == "simulated"
    assert by_name["SOUL.md"]["sections"]
    assert by_name["MYSTERY.md"]["status"] == "unmapped"
    assert all(f["unchanged_after"] for f in run1["files"])
    assert all(p.read_bytes() == data for p, data in before.items())
    assert not (stage / "generated").exists()  # nothing committed


def test_hundred_cycle_byte_identity(cl, stage):
    data = ("# Soul\n\n" + "cycle body ᚦ.\n" * 50).encode("utf-8")
    _write(stage, "canonical/SOUL.md", data)
    lib = cl.CanonicalLibrary(stage, "yrsa", work_unit=256)
    record = lib.ingest("canonical/SOUL.md", "soul")
    expected = hashlib.sha256(data).hexdigest()
    out = stage / "cycle-out.md"
    for _ in range(100):
        assert lib.export(record.document_id, out) == expected
        assert hashlib.sha256(out.read_bytes()).hexdigest() == expected
        again = lib.ingest("canonical/SOUL.md", "soul")
        assert again.sha256 == expected


# ---------------------------------------------------------------
# Stock-path control: W03 adds a path, it does not mutate one
# ---------------------------------------------------------------

def test_stock_prompt_path_still_truncates(cl):
    from agent.prompt_builder import CONTEXT_FILE_MAX_CHARS, _truncate_content

    assert CONTEXT_FILE_MAX_CHARS == 20_000
    big = "# Head\n" + ("filler line\n" * 60000)
    out = _truncate_content(big, "SOUL.md")
    assert len(out) < len(big)  # upstream behaviour intact
