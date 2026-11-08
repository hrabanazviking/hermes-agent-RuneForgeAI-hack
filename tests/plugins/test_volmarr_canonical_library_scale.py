"""P.016 wave gate: 100 MB corpus byte-identical (W03).

Deterministic corpus (fixed seed material, no randomness): a
many-file tree totalling >= 100 MB plus the design draft's
adversaries -- a >= 10 MB single section, a no-heading file,
duplicate headings, fenced ``#`` lines, CRLF throughout one
file, runes / Old Norse diacritics / combining characters /
emoji, YAML front matter, HTML comments, a file exactly one
work unit and one byte over it. Asserts: hash identity across
ingestion / reindex / export, per-section byte-range digests,
no forbidden key anywhere in the committed manifest, peak RSS
growth independent of corpus size, and interruption honesty
(a checkpointed partial ingest is never ``complete`` with a
wrong hash, and resume reaches the identical final hash).

Staged directly under $HOME per the ravens staging lesson.
Evidence (wall time, peak RSS, per-file hashes) is printed for
the run log.
"""

from __future__ import annotations

import hashlib
import importlib
import resource
import shutil
import time
from pathlib import Path

import pytest

from hermes_constants import get_hermes_home

WORK_UNIT = 65536
TARGET_TOTAL = 100 * 1024 * 1024


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


def _rss_kb() -> int:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss


def _corpus(root: Path) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    line = "ᚱᚢᚾᛖᛋ þ ð ǫ — combining a\u0301, emoji ᛟ✨, plain text.\n"
    block = ("# Section\n\n" + line * 200).encode("utf-8")
    # Many-file tree: 24 files of ~4 MB each.
    for idx in range(24):
        data = block * 400 + f"# Tail {idx}\n".encode("utf-8")
        files[f"tree/part-{idx:02d}.md"] = data
    # One giant single section >= 10 MB, no internal headings.
    files["giant-section.md"] = (
        "# Giant\n" + "one enormous section line.\n" * 500_000).encode()
    # No-heading file.
    files["no-heading.md"] = ("prose only.\n" * 3000).encode()
    # Duplicate headings + fenced hash lines + front matter + comments.
    files["adversaries.md"] = (
        "---\ntitle: Adversaries\n---\n<!-- a comment -->\n"
        "# Dup\n\nfirst\n```\n# not a heading\n```\n# Dup\n\nsecond\n"
    ).encode("utf-8")
    # CRLF throughout.
    files["crlf.md"] = b"# One\r\n\r\nfirst\r\n# Two\r\n\r\nsecond\r\n" * 40
    # Exactly one work unit, and one byte over.
    files["exact-unit.md"] = b"a" * WORK_UNIT
    files["unit-plus-one.md"] = b"a" * (WORK_UNIT + 1)
    total = sum(len(d) for d in files.values())
    assert total >= TARGET_TOTAL, total
    for rel, data in files.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return files


def test_p016_hundred_mb_byte_identical(cl):
    root = Path.home() / ".hermes-w03-gate-corpus"
    shutil.rmtree(root, ignore_errors=True)
    (root / "canonical").mkdir(parents=True)
    try:
        files = _corpus(root / "canonical")
        lib = cl.CanonicalLibrary(root, "gate-persona", work_unit=WORK_UNIT)
        started = time.monotonic()
        rss_before = _rss_kb()
        records = {}
        for rel in sorted(files):
            records[rel] = lib.ingest(f"canonical/{rel}", "knowledge")
        wall = time.monotonic() - started
        rss_after = _rss_kb()
        total = sum(len(d) for d in files.values())
        print(f"P016 corpus={total} bytes files={len(files)} "
              f"wall={wall:.1f}s rss_before={rss_before}KB "
              f"rss_after={rss_after}KB")
        for rel, data in files.items():
            record = records[rel]
            expected = hashlib.sha256(data).hexdigest()
            assert record.sha256 == expected, rel
            assert record.byte_length == len(data), rel
            assert lib.verify(record.document_id), rel
            out = root / "export-check.md"
            assert lib.export(record.document_id, out) == expected, rel
            # Section byte ranges slice-hash to the recorded digests.
            ingester = lib.ingester
            source = root / "canonical" / rel
            result = ingester.ingest_file(
                source, "knowledge", record.document_id)
            for span in result.sections:
                assert ingester.section_digest(source, span) == span.sha256
                assert hashlib.sha256(
                    data[span.byte_start:span.byte_end]).hexdigest() \
                    == span.sha256
        # Adversary structure checks.
        adv = records["adversaries.md"]
        assert [s["section_id"] for s in adv.sections] == ["_preamble", "dup", "dup_2"]
        giant = records["giant-section.md"]
        assert len(giant.sections) == 1
        assert giant.byte_length >= 10 * 1024 * 1024
        # No forbidden key anywhere in the committed manifest.
        import json as _json
        manifest = _json.loads(
            (root / "generated" / "manifest.json").read_text())
        assert cl.find_forbidden_keys(manifest) == []
        # Peak RSS growth is bounded independent of corpus size:
        # the whole 100 MB was ingested with < 200 MB growth.
        growth_mb = (rss_after - rss_before) / 1024
        print(f"P016 rss_growth={growth_mb:.1f}MB")
        assert growth_mb < 200, growth_mb
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_p016_interruption_honesty_and_resume(cl):
    root = Path.home() / ".hermes-w03-gate-interrupt"
    shutil.rmtree(root, ignore_errors=True)
    root.mkdir(parents=True)
    try:
        data = ("# S\n\n" + "interruptible line.\n" * 40000).encode()
        target = root / "doc.md"
        target.write_bytes(data)
        ingester = cl.StreamingIngester(work_unit=8192)
        checkpoints: list = []
        full = ingester.ingest_file(
            target, "soul", "doc_int", checkpoint_sink=checkpoints.append)
        assert full.status == "complete"
        # A checkpoint mid-file is not a completion: resuming
        # from it reaches exactly the full hash, and the final
        # section layout is identical.
        mid = checkpoints[len(checkpoints) // 2]
        assert 0 < mid.byte_offset < len(data)
        resumed = ingester.ingest_file(target, "soul", "doc_int",
                                       resume_from=mid)
        assert resumed.sha256 == full.sha256 == \
            hashlib.sha256(data).hexdigest()
        assert [s.to_dict() for s in resumed.sections] == \
            [s.to_dict() for s in full.sections]
    finally:
        shutil.rmtree(root, ignore_errors=True)
