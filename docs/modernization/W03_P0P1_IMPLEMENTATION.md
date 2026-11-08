# W03 Implementation — Phases P0+P1: Unbounded Canon (Team 04)

Status: IMPLEMENTED on branch `yrsa/hermes-team-04`, commit-only
(keeper banks serially). Base: `073660ff15` (banked main
`b5c6743a22` + Team 04 design draft `849bcf1110`). Design:
`docs/modernization/P0P1_DESIGN_DRAFT.md`, build order followed
exactly: P.001 → P.002 → P.004 → P.003 → P.005 → P.016 gate.

## What landed

One new plugin-side module, `plugins/volmarr-core/canonical_library.py`
(no core files touched; `agent/prompt_builder.py` and its
`CONTEXT_FILE_MAX_CHARS` cap are byte-for-byte intact):

- **P.001 policy + schema.** Role/trust/privacy/priority/status
  vocabularies, the full document-record field contract, and the
  no-cap clause enforced mechanically: `validate_record` rejects
  any key in the forbidden set or matching `^max_` / `_limit$`
  with a named error, rejects unknown fields, absolute/escaping
  paths and malformed hashes. `document_id` is minted once from
  persona + canonical relpath and kept across renames.
- **P.002 streaming ingestion.** `StreamingIngester`: chunked
  binary reads (1 MiB default work unit — an operations quota,
  never a document property), incremental SHA-256 over raw
  bytes, incremental UTF-8 validation (invalid sequences yield
  `unreadable` + the exact byte offset; no replacement chars
  anywhere), byte-range section extraction, checkpoints carrying
  serialised prefix-hash state with verified resume, and
  streaming export that reproduces the original byte stream.
  Sources are read in place — never copied, rewritten,
  normalised or re-encoded.
- **P.004 transactional manifest.** `ManifestStore`: tmp-file +
  fsync + atomic rename + directory fsync, generation bumped
  exactly once per transaction, an append-only journal (per-doc
  old/new hash + revision + full record), a single-writer flock
  with an operator-visible timeout error, and recovery that
  quarantines a torn/generation-divergent manifest and rebuilds
  from the journal. Rollback rewinds derived state only.
- **P.003 migration dry-run.** `migration_dry_run`: inventory
  with streaming hashes, role proposals (unmapped files are
  reported unmapped, never guessed), verify-only simulated
  ingestion with section previews, per-file proof the dry-run
  moved nothing, and a comparable payload that makes the
  two-run idempotence check exact. Real migration + rollback
  rehearsal are exercised against disposable $HOME-staged
  libraries in the test suite — never the dormant `~/.hermes`.
- **P.005 section identity.** Heading sections (ATX + Setext),
  preamble as reserved slug `_preamble`, fenced `#` lines never
  headings, duplicate headings disambiguated in document order
  (`name`, `name_2`, …), no-heading files get one root section
  whose identity is the document id. Slugs reuse the compiler's
  `_slugify`/`display_heading`; persistent ids are
  `persona_runtime.stable_section_id(role, slug)` — no second
  identity scheme. Every span records exact byte start/end and
  the SHA-256 of that byte slice.

## Tests (scripts/run_tests.sh only; counts from log files)

- `tests/plugins/test_volmarr_canonical_library.py` — policy,
  schema canary, size ladder (1 KB / 20 KB / 20,001 / 501 KB),
  UTF-8 refusal offset, CRLF ranges, checkpoint resume, section
  identity + stability across unrelated edits, giant section,
  manifest transactions/journal/rollback/quarantine, missing
  source honesty, one-transaction tree ingest, dry-run
  idempotence, 100-cycle byte identity, stock-path control.
- `tests/plugins/test_volmarr_canonical_library_scale.py` —
  the P.016 gate (see the completion report for log numbers).

## Deliberate non-goals (per the design draft)

- No live-prompt wiring: removing the duplicate legacy
  injection on opt-in profiles is P.010 in W05.
- `plugins/volmarr-core/context_packet.py` packet budgets are
  lawful retrieval bounds (Invariant D) and are untouched.
- Curated MEMORY/USER store caps are W06/P.014, untouched.
- Subspans of giant sections are W04/P.006; W03 byte ranges are
  shaped so subspans can be derived without re-ingestion.

## Verified results (2026-11-07, purplelongship, logs on the laptop)

- W03 tests: `~/team04-w03-both.log` — 2 files, **28 passed / 0
  failed** (26 unit/contract + 2 gate).
- P.016 gate evidence (`~/team04-w03-scale2.log`): corpus
  **148,174,328 bytes across 30 files** (>= 100 MB), ingestion
  wall **7.1 s**, peak RSS 259,008 KB -> 270,912 KB (**~11.6 MB
  growth for a 148 MB corpus** — memory tracks the work unit,
  not the corpus). Byte identity held across ingestion, verify,
  reindex and export for every file, and every section's byte
  range slice-hashed to its recorded digest.
- Contract baseline (`~/team04-w03-contracts.log`): 119 files
  (117 baseline + 2 new W03 files) = **957 passed / 7 failed /
  1 skipped**; 957 = 929 baseline + 28 new. The 7 failures are
  name-identical to the grading baseline (5 core-plugin
  Verdandi socket/discovery in `test_volmarr_core_plugin.py`,
  1 Verdandi stimuli, 1 voice-runner loopback) — zero new
  failures, zero regressions.
- README.md sha256 unchanged:
  `336813d11bbe5aa2ff745b4a4bc3abcf2a283cd13971c0c11d061377129db7f3`.

## Found and fixed in scope

- YAML front matter: the closing `---` of a leading front-matter
  block was promoting its last line (`title: ...`) to a Setext
  heading, corrupting section identity for any authored doc
  with front matter. Fixed in the ingester (front matter is
  preamble content) with regression tests in both test files.
- Two test-side defects (mid-UTF-8-sequence ladder cut; corpus
  size arithmetic) were fixed in the tests, not the module.

## Ticketed remainders (not blockers)

- Checkpoint resume re-streams the prefix to rebuild decoder/
  section state (hash state itself is serialised and verified);
  a fully serialisable parser-state checkpoint is a W04
  refinement if subspan work needs it.
- Low-memory (`ulimit -v`) honest-failure behaviour from the
  draft's test plan item 7 is not yet exercised; ingestion
  failure paths are covered via the unreadable/offset tests.
  Ticket for the keeper's W03 closure pass.
