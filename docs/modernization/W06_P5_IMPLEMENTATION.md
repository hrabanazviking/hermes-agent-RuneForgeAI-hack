# W06 Implementation Record — Phase P5: Truly Large MEMORY.md and USER.md

Team 07 (W06), 2026-11-08. Ticket P.014 (core) plus the
memory-facing halves of P.015–P.020, per
`docs/modernization/P5_DESIGN_DRAFT.md` (committed on this branch
before implementation). Built on the banked W05 tree (contracts
baseline 123 files = 991 passed / 7 failed / 1 skipped, the 7 the
known live-transport set). All personal code is plugin-side in
`plugins/volmarr-core/`; no Hermes core file is touched and
README.md is untouched (sha256 verified at close:
`336813d11bbe5aa2ff745b4a4bc3abcf2a283cd13971c0c11d061377129db7f3`,
identical to banked main).

Roadmap §28.2 law held: a surface is declared live only where
this wave gave it a real caller on a real path. The surfaces this
wave did NOT complete are named as remainders below, never
declared complete.

## What was built (draft build order M1–M5, plus scoped halves)

- **M1 — Corpus foundation (P.014a).** New module
  `plugins/volmarr-core/memory_corpus.py` (551 lines):
  `MemoryCorpus` roots a W03 `CanonicalLibrary` at the profile
  (namespace ruling, draft §4.1: the library is keyed by the
  profile/user namespace id; a persona id is only a consumer
  label). `MEMORY.md`/`USER.md` are read in place under
  `memories/` — never copied, rewritten or re-encoded. Import is
  P.003-style: `inventory()` (files, streaming hashes, proposed
  roles, unmapped files reported never guessed), dry-run first
  (`import_corpus(confirm=False)` proves per-file
  `unchanged_after` and commits nothing), confirmed import as
  one manifest transaction. The empty profile is an honest no-op
  receipt; no stub files are manufactured. Flags declared in
  `plugin.yaml`: `memory_corpus_enabled`,
  `memory_corpus_digest_enabled`, `memory_corpus_root`,
  `memory_corpus_cloud_egress_enabled` (all default-off/empty).
- **M2 — Index wiring (P.014b).** The W04 `PersonaIndex` rooted
  at the same library: `sync_index()`, `index_status()`, and
  `repair_index()` — deletes ONLY the derived SQLite index and
  rebuilds it (manifest, journal and canonical bytes untouched;
  retrieval results proven identical across repair). Flag
  hygiene from draft finding 5: `mempalace_retrieval_enabled`
  and `openviking_retrieval_enabled` are now declared in
  `plugin.yaml` (bool, default `false` — the defaults the two
  bridges already read; no behaviour change).
- **M3 — Digest (P.014c, P.015).** New module
  `plugins/volmarr-core/memory_digest.py` (184 lines):
  deterministic, verbatim-section digest — entries are exact
  source sections selected whole (pinned headings first, then
  retrieval order when a query is supplied, then source order),
  each carrying stable id + section hash + source hash and
  traceable via `cite()`; overflow sections are excluded and
  reported, never truncated; no paraphrase or generated summary
  text exists. The digest is generation-bound derived data under
  `generated/`; `digest_status()` labels it absent / current /
  stale honestly. P.015 protection is enforced at the corpus's
  one write door: `replace_section_text(...,
  provenance != "authored")` raises
  `ObservationOverwriteRefused` (the §41 memory guard's first
  live caller), and agent observations are stored only as typed
  derived records (`generated/observations.jsonl`, provenance
  `agent-observed`) that never enter the authored files;
  promotion requires an authored write.
- **M4 — Tool adapter (P.014d).** New module
  `plugins/volmarr-core/memory_adapter.py` (312 lines):
  stock-shaped `add` / `replace` / `patch` / `remove` at the
  tool-result level, no core patch. Truthful three-store status
  block on every result (full-store bytes, snapshot chars vs the
  stock 2,200/1,375 hot caps, corpus generation, index state).
  Writes fitting the hot caps land `hot_and_full` with stock
  semantics; overflow writes SUCCEED in the full store
  (append-only, prior bytes preserved exactly) and report
  `landed_in: "full_store"`, `in_hot_view: false` with the
  reason — no silent truncation, no refusal cliff. Pinned-entry
  approval preserved: a staged write whose `matched_entry` is no
  longer present is refused `stale_entry`, nothing applied.
  Entry edits additionally require the file to be entry-shaped
  (it round-trips through the stock entry model AND either
  carries the stock `\n§\n` delimiter or has no heading
  structure); against a free-form authored document they are
  refused by name (`not_entry_model`) pointing at the
  section-scoped corpus write — authored bytes are never
  silently normalised. (This rule was tightened during the run:
  the first form, round-trip alone, let a headed document pass
  as one giant entry; the failing contract caught it and the
  fix is in the shipped code and tests.)
- **M5 — Packet integration (P.014 turn-path half, P.017,
  P.018).** New module `plugins/volmarr-core/memory_bridge.py`
  (210 lines): `MemoryBridge`, a PresentState packet SOURCE
  registered in `plugins/volmarr-core/__init__.py` alongside the
  other retrieval bridges. `PresentStateBridge` remains the sole
  prompt owner / `pre_llm_call` assembler (the banked W05 seam,
  consumed exactly as draft §3.3 orders); the bridge registers
  no hooks of its own. Fully gated by `memory_corpus_enabled`:
  disabled ⇒ `[]` with zero filesystem work. With a query it
  serves W04 retrieval as verbatim `durable_knowledge` items
  naming stable id, source hash and the corpus generation
  captured BEFORE any read for the turn (generation-snapshot
  discipline: a mid-turn write activates next turn). With no
  query it serves the hot digest only under the separate digest
  opt-in, rebuilding a stale digest before serving it. P.018:
  local by default (receipts record `cloud_egress: 0`); cloud
  egress requires BOTH the operator flag
  `memory_corpus_cloud_egress_enabled` AND a cloud-bound turn,
  and then the corpus refuses private-classified sources before
  egress, naming refusals on the receipt (corpus-level
  `retrieve(destination="cloud")` / `cite(destination="cloud")`
  enforce the same filter for every caller). Fail-open: any
  corpus problem yields `[]` and a receipt, never a blocked turn.
- **M6 — Editor/API, plugin-side half only.** The draft's API
  audit outcome is implemented as data doors, not endpoints:
  the editor read path already exists as W04
  `PersonaIndex.read_page()` (exposed via
  `MemoryCorpus.read_page`; gate-proven byte-exact below) and
  the write path as the section-scoped
  `MemoryCorpus.replace_section_text` with pinned-hash approval.
  No HTTP endpoint and no Desktop UI were built in this wave —
  see Remainders.
- **M7 — Consolidation links.** Scoped to the draft's core law
  only: consolidation-style derived metadata exists as the
  digest + observations records (both derived, source-linked,
  never deleting or rewriting source history). A separate
  memory-consolidation record format was NOT built — see
  Remainders.
- **M8 — Gates + diagnostics (P.016/P.017/P.019/P.020 memory
  halves).** The §6 gate suite below; diagnostics via
  `hermes volmarr memory corpus status` (new CLI subcommand in
  `plugins/volmarr-core/cli.py`: full-store bytes vs hot-view
  chars per target, corpus generation, index state, digest
  state; `--json` supported; read-only) and this record as the
  operator how-to for the full-vs-hot distinction.

## Ticket map

- **P.014** — complete as designed: corpus (M1) + index (M2) +
  adapter (M4) + packet source (M5).
- **P.015** — memory half complete: authored canon outranks
  observations mechanically (§41 guard live at the write door;
  observations derived-only).
- **P.016** — memory half complete: §11 sizes proven by the
  gate (below); interrupted-import recovery inherits the W03
  journal/quarantine discipline unchanged; index repair proven.
- **P.017** — memory half complete: corpus/digest continuity is
  generational — restarts keep the manifest generation, stale
  digests are labelled and rebuilt, mid-turn writes activate
  next turn (bridge receipt discipline).
- **P.018** — complete for the memory egress paths built here:
  private sources refused before cloud egress at corpus,
  citation and bridge level, with receipt evidence.
- **P.019** — memory half complete: `MemoryCorpus.backup()` =
  canonical files + manifest + journal, index EXCLUDED;
  `restore()` into a fresh profile verifies per-file hashes and
  REBUILDS the index, with identical retrieval/citation proven
  by contract. Encryption inherits the open W00.03-ENC question:
  backups are stamped `none-unencrypted-local` in their manifest
  — named, never silent; no key was invented.
- **P.020** — memory half complete: CLI status + this record.

## Evidence (all counts from log files on the laptop)

- New W06 tests: 5 files, 38 tests, all passing —
  `test_volmarr_memory_corpus.py` 12/12 (`~/team07-w06-corpus.log`),
  `test_volmarr_memory_digest.py` 6/6,
  `test_volmarr_memory_adapter.py` 8/8 (`~/team07-w06-adapter2.log`;
  first run 7/8 caught the entry-model flaw described in M4),
  `test_volmarr_memory_bridge.py` 8/8 (`~/team07-w06-bridge3.log`,
  including the CLI status contract),
  `test_volmarr_memory_corpus_gate.py` 4/4 (`~/team07-w06-gate.log`).
- **W06 gate (draft §6 item 1):** deterministic fixtures of
  MEMORY.md of at least 20,000,000 bytes (2,500 sections) and
  USER.md of at least 2,000,000 bytes (250 sections) -- both
  sizes asserted by the gate fixture itself -- in a disposable $HOME-level
  profile: import byte-identical per-document sha256; six
  planted needles (start/middle/end of both files) recalled by
  exact phrase and cited with hash verification; paged-read
  concatenation reproduces USER.md byte-for-byte; per-file
  sha256 identical before import, after sync, after forced
  reindex and after index repair (zero source loss). Gate wall
  68.6s under neighbouring-campaign load (a Rúnmál suite shared
  the laptop; correctness assertions are load-independent).
- Neighbours: 10 files = 97 passed / 5 failed
  (`~/team07-w06-neighbours.log`) — the 5 are exactly the
  core-plugin members of the known live-transport set.
- Stock control (draft §6 item 6): `tests/tools/test_memory_tool*.py`
  + `tests/agent/test_memory_*.py` = 21 files, 230 passed /
  0 failed (`~/team07-w06-stock.log`) — stock snapshot behaviour
  unchanged with the plugin present.
- **Full contracts: 128 files = 1,029 passed / 7 failed /
  1 skipped** (`~/team07-w06-contracts.log`) = W05 baseline
  991 + 38 new; the 7 failures verified name-identical to the
  W05 baseline set (diff of the FAILED lines: identical — 5×
  `test_volmarr_core_plugin.py` Verdandi socket/discovery, 1×
  `test_volmarr_verdandi_stimuli.py`, 1×
  `test_volmarr_voice_runner.py` loopback).

## Evidence stage (§28.3)

M1–M4 bank as *contract implemented*; M5 plus gate items 1–3
promote the corpus to *end-to-end working*. Nothing here is
called *production qualified*.

## Bugs found and fixed in scope

1. Adapter entry-model flaw (found by its own contract test,
   first run 7/8): a headed Markdown document with no entry
   delimiter trivially round-trips as a single "entry", so an
   entry replace would have rewritten the whole authored
   document. Fixed by the entry-shaped rule in M4; contract now
   proves refusal + byte-prefix preservation on authored docs.
2. CLI/test namespace mismatch (found by the CLI contract's
   first run): `corpus status` reported `ingested: false` for a
   corpus imported under a test-local namespace id, because the
   CLI derives the profile namespace from the profile itself
   (draft §4.1). Behaviour is correct for real profiles (one
   construction path); the contract now imports under the
   profile-derived namespace, matching production.

## Honest remainders (not built, not declared complete)

- **M6 Desktop/API surface:** no HTTP endpoint and no Desktop
  "Full store" view. The paged read + section-scoped write doors
  exist plugin-side; the frontend/API audit-and-build remains
  for a later wave.
- **M7 memory-consolidation record:** only the digest +
  observations derived records exist; the draft's separate
  consolidation-link record and its CLI review surface were not
  built.
- **ChatIndex (draft Q5):** not built — the draft's own
  recommendation was deferral to the W08 engine pass; recorded
  here so the name is not silently dropped.
- **Bifröst read path (draft Q6/Q7):** no `bifrost_retrieval`
  bridge was built; Bifröst/Mímir stays health/operator-only
  until the W08 engine row, as the draft framed it.
- **Concurrency gate (draft §6 item 4)** was not run as a
  multi-process battery; the corpus inherits the W03 manifest
  flock + named `LockTimeoutError` and the W04 WAL discipline,
  and single-process gateway+CLI+editor-shaped access is
  exercised by the contracts, but true concurrent-process
  contention evidence is still owed.
- **Open draft questions Q1–Q4** (corpus root identity, digest
  default, hot-snapshot future, sequencing) were implemented as
  the draft's own design decisions (profile namespace; digest
  as second opt-in, default off; stock snapshot independent;
  M1–M4 independent of W05, M5 on the banked seam) and remain
  Volmarr's to overrule.
