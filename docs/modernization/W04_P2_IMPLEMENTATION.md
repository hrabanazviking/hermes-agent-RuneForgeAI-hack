# W04 Implementation Record — Phase P2: Incremental Section Index, Retrieval and Full-Fidelity Read

Team 05 (W04), 2026-11-07/08. Tickets P.006/P.007 per
`docs/modernization/P2_DESIGN_DRAFT.md` (committed this branch,
`docs(w04): P2 retrieval design draft`), built on the banked
W03 canonical library (`plugins/volmarr-core/canonical_library.py`,
origin/main 7ce3db56f0 merged into this branch). Roadmap section 8
law held: the new code builds on `persona_runtime.py`'s section 13
scorer — no second compiler, parser, slugger or scorer — and all
personal code is plugin-side in `plugins/volmarr-core/`.

## What was built

New module `plugins/volmarr-core/persona_index.py` (PersonaIndex):

- **P.006a index skeleton + tokenizer measurement.** SQLite schema
  per draft section 3 (documents / sections / subspans /
  search_rows / index_journal / index_meta, WAL, layout version in
  `index_meta`), ONE search projection feeding two external-content
  FTS5 tables (`unicode61 remove_diacritics 2` + trigram).
  Measurement harness `measure_tokenizers` run against runes /
  diacritics / code samples: unicode61 hit 4/4, trigram 3/4 on the
  test sample set — trigram misses only the diacritic-folded case
  (café vs cafe) that unicode61 covers, and NEITHER tokenizer turns
  þórr into thor (thorn is a letter, not a digraph; recorded
  honestly). Decision per draft: keep BOTH tables, trigram as the
  exact-substring fallback.
- **P.006b incremental indexer.** `sync()` diffs the W03 manifest
  by per-document source hash: unchanged documents are untouched
  (journal-proven), each changed document is replaced in ONE
  transaction, removals are journaled, and the manifest generation
  advances in `index_meta` only after all document transactions
  commit (a crash leaves the index honestly `outdated`). Section
  slice hashes are verified against the manifest during indexing.
- **P.006c FTS query path under the section 13 scorer.** Candidates
  (cap 200, recorded) are re-scored by the untouched
  `retrieval_score`; scores are bit-identical to the in-memory path
  when embeddings are off (contract-tested). BM25 enters only as a
  named fusion constant (`BM25_FUSION_WEIGHT = 0.15`, min-max
  normalised over the candidate set, so ordering is deterministic
  across rebuilds — contract-tested). The section 13 contact rule
  is enforced after fusion, with one fusion-layer reconciliation
  (see Found and fixed, item 2). Results carry byte/line ranges,
  section + source hashes, privacy/trust labels, and a
  `more_from_this_section` continuation handle when windowed.
- **P.006d subspans + continuation handles.** Sections over the
  threshold (operations value, default 32 KiB) split at paragraph /
  sentence / line boundaries (hard split last) with recorded
  overlap; concatenating subspan slices minus declared overlaps
  reproduces the section bytes exactly (contract-tested). Handles
  are base64url JSON validated at serve time against the source
  hash + manifest generation; a stale handle returns a named
  `stale_continuation` result with the current first window, never
  silent bytes from a changed source (contract-tested).
- **P.006e exact citation + receipts.** `cite()` slices from the
  canonical source at serve time and verifies the slice hash;
  CRLF, trailing spaces and blank runs survive (contract-tested).
  Citation works from the manifest alone when the index is
  unbuilt/outdated, recording index status honestly. Every
  retrieval / citation / paged-read / continuation call appends a
  receipt (draft section 6 schema) to `generated/receipts/` and
  returns it: query, task tags, generations, candidate count/cap,
  chosen with full score breakdowns, omitted with named reasons
  (`no_contact`, `over_budget`, `source_hash_mismatch`),
  continuations issued, embeddings state, `cloud_egress`.
- **P.006f paged full-fidelity read.** `read_page` /
  `read_section_page`: byte-cursor paging, UTF-8-boundary-safe, no
  redaction/formatting/dedup; page concatenation reproduces the
  source byte-for-byte, proven against the whole-source hash
  (contract-tested).
- **P.007 embeddings consent gate.** Off by default; no vector is
  computed, stored or queried without a per-source consent record
  (provider kind/provider/model/version/dimensions pinned).
  Cloud embedding of a `private` source is refused at grant time
  without a recorded operator override. Consent is re-checked at
  embed time and at query time; source-hash drift invalidates
  vectors; revocation deletes the source's vectors in the same
  transaction (all contract-tested with an injected local fake
  provider — the real A.E.S.I.R./local-server contract is W08/E.02
  and does not block P.006, per the draft). Vectors live in a
  separate `generated/semantic/embeddings.sqlite`. Without a
  consented vector, `semantic` stays `None` and the five-component
  score is bit-identical to today.

## Gate (draft section 9, scaled fixture)

`tests/plugins/test_volmarr_persona_index_gate.py`: deterministic
corpus of 24 documents, > 2,000,000 bytes asserted in-test, with
planted needles — nonce phrase mid-corpus, Old Norse phrase with
diacritics, rune sequence, fenced-code line, duplicate headings in
different roles, start/middle/end needles in one giant subspanned
section (~190 KB), and a needle in a no-heading file. Assertions:
exact-match recall 100% (every needle returns its section AND
cites with a verifying hash), zero source loss across indexing,
3 reindex cycles and a forced rebuild, reference stability after
an unrelated early edit (stable ids unchanged, citations still
verify), and offline honesty (every receipt `cloud_egress: 0`,
embeddings off, `semantic: None`). PASSED (log
`~/team05-w04-gate.log`). The full 100 MB battery is the same code
path with a larger fixture parameter; running it is ticketed
below rather than claimed.

## Verified results (2026-11-08, purplelongship, logs on the laptop)

- W04 tests: `tests/plugins/test_volmarr_persona_index.py` (18
  tests) + gate file (1 test) = **19 passed / 0 failed**
  (logs `~/team05-w04-tests.log` — first run 18 passed / 1 gate
  failure, since fixed, see below — and `~/team05-w04-gate.log`,
  gate green standalone).
- Contract baseline (`~/team05-w04-contracts.log`): **121 files =
  976 passed / 7 failed / 1 skipped**; 976 = 957 baseline (W03)
  + 19 new W04 tests. The 7 failures are name-identical to the
  grading baseline live-transport set (5 core-plugin Verdandi
  socket/discovery in `test_volmarr_core_plugin.py`, 1 Verdandi
  stimuli, 1 voice-runner loopback) — zero regressions, zero new
  failures. Note: the contract run overlapped a Mythic Coder
  suite launch on the shared laptop; counts are log-verified and
  unaffected, wall times under contention are not baselines.
- README.md sha256 unchanged:
  `336813d11bbe5aa2ff745b4a4bc3abcf2a283cd13971c0c11d061377129db7f3`.

## Found and fixed in scope

1. **Subspan search-projection decode crash.** Subspan windows
   rewind by the overlap and hard splits are byte operations, so a
   window can start/end mid-character; decoding its normalised
   search text strictly raised `UnicodeDecodeError` and failed
   indexing of any large section containing multibyte text. Fixed:
   the search projection (only) decodes tolerantly; exact bytes and
   the subspan hash are unaffected, and serving always slices
   source bytes. Found by the first W04 test run (3 failures).
2. **Section 13 slug vocabulary is ASCII-only (discovered
   limitation, reconciled at the fusion layer).**
   `persona_runtime._slugify` maps every non-[a-z0-9] run to `_`,
   so a query written in runes or CJK tokenises to the empty set
   and token contact can never fire — the draft's buried-rune-
   needle gate case is unreachable through token contact alone.
   The scorer itself is untouched (§13 parity is a contract); the
   P2 fusion layer accepts a verbatim trigram exact-phrase hit as
   contact evidence (draft section 3.4 already routes phrase/exact
   terms to the trigram table), records `exact_phrase_hit` on the
   result and the why-reason on the receipt. Ticketed below for
   the keeper/Volmarr: whether §13's vocabulary should grow a
   Unicode tokeniser in a later wave.
3. **Test-fixture corrections (not code bugs):** the true slug of
   "Seiðr Practice" is `sei_r_practice` (ð -> _), and W03's design
   gives a no-heading file's root section the document_id as its
   stable identity — the gate now asserts against both truths.

## Deliberate deviations / ticketed remainders

- `search_rows.row_pk` uses a large offset (2^40) for subspan
  rows: the draft's literal "= section_pk or subspan_pk" collides
  between the two populations and FTS5 content rowids must be
  unique. Schema intent (one projection, two granularities) is
  unchanged.
- Retrieval result windows trim to a UTF-8 boundary and the
  continuation handle names the trimmed offset (a window is a
  snippet surface; exactness lives in citation/paged-read).
- `in_kernel` is recorded 0 for manifest-sourced sections: the
  W03 manifest carries no kernel membership, so priority is the
  compiler's derived priority for a non-kernel section. If W05
  wires kernel membership into the manifest, the indexer picks it
  up without a schema change (column exists).
- TICKET W04-R1: run the full 100 MB gate corpus (draft section
  9 sizes) on an uncontended laptop window and file wall time /
  P50/P95 / DB size / peak RSS with the banking evidence.
- TICKET W04-R2: receipt retention/rotation default (draft open
  question 3) — receipts currently append without rotation;
  operator preference needed before W07 builds on the store.
- TICKET W04-R3: §13 Unicode tokenisation question (Found and
  fixed, item 2) — P2-side reconciliation stands until a later
  wave rules on the scorer's vocabulary.
- Real embedding provider contract (A.E.S.I.R. / local server)
  remains W08/E.02 by design; P.007's gate is provider-agnostic
  and tested against a local fake.
