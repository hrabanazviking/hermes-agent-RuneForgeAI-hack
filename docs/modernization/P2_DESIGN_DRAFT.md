# P2 Design Draft — Phase P2: Incremental Section Index, Retrieval and Full-Fidelity Read

Team 05 (W04 prep), 2026-11-07. Status: DRAFT, uncommitted, in worktree
`~/hermes-team-05` (branch `yrsa/hermes-team-05`; WAVE_PLAN.md names the
branch `team-05/w04-p2-retrieval` — the on-disk precedent of Teams
02/03/04/09 is the `yrsa/hermes-team-NN` form, and this draft follows
that precedent; the keeper should reconcile the naming once).

Scope note: PREP / AUDIT / DESIGN only. No code was changed, nothing was
committed or pushed this run. W04 formally follows W03 (Team 04, P0/P1);
its base is the banked W02 tree. All findings below were verified from
source on purplelongship on 2026-11-07 unless marked otherwise.

Base verified this run: worktree `~/hermes-team-05` already existed;
HEAD = `b5c6743a2281d9f6663e6d5fe2636b1c23ea9d26` (banked W02 closure,
`docs(w02): keeper banking closure - W02 banked to main at 4c676d0587`),
branch `yrsa/hermes-team-05`, working tree clean before this draft.
README.md untouched (never touched by this team; sha256 stands at
336813d11bbe5aa2ff745b4a4bc3abcf2a283cd13971c0c11d061377129db7f3).

Governing texts read this run: WAVE_PLAN.md (Team 05 section),
CAMPAIGN_STATE_MODERNIZATION.md, Team 04's
`~/hermes-team-04/docs/modernization/P0P1_DESIGN_DRAFT.md` (the W03
design this layer builds on), and the roadmap
ROADMAP_HERMES_MODERNIZATION_UNBOUNDED_PERSONA_2026-11-07.md —
Part II invariants (section 2), Phase P1 layout and manifest fields
(section 7), Phase P2 in full (section 8), and tickets P.006/P.007
(section 31). Roadmap section 8 law, verbatim in substance: build on
`plugins/volmarr-core/persona_runtime.py`; do not create a competing
persona compiler.

## 0. Headline findings

1. **Persona retrieval today is an in-memory linear scan over a fresh
   compile — there is no persistent index at all.** `PersonaRetriever`
   (`persona_runtime.py:13920`) recompiles the whole persona on every
   call and `retrieve_sections` (`:1403`) scores every section of a
   Python list. That is correct, deterministic and explainable — and
   it cannot survive a 100 MB corpus: cost per query is O(corpus),
   and the compile itself refuses documents over 512 KiB (finding 2).
   P2 is therefore a persistence + candidate-generation layer under
   the existing scorer, not a new retriever.
2. **The compiler's own size cap blocks P2's input before W03 lands.**
   `MAX_DOCUMENT_BYTES = 512 * 1024` (`persona_runtime.py:720`);
   `PersonaCompiler.compile` (`:13711`, cap enforced `:13731`) raises
   on any larger document, reads whole files with `path.read_text`
   (`:13735`), and hashes the *re-encoded* text
   (`hashlib.sha256(text.encode(...))`, `:13740`) rather than the
   original bytes. W03's streamer, byte-exact hashes and byte ranges
   (Team 04 draft sections 2–4) are hard prerequisites for P2's index
   schema: the index stores byte ranges and source-byte hashes, and
   neither exists in the tree today. P2 must not invent parallel
   versions of them (section 9 of this draft sequences around this).
3. **No persona FTS5 / SQLite index exists anywhere in the tree.**
   Grep-verified this run: no `sections.sqlite`, no FTS5 DDL, no
   `bm25(` call in `plugins/volmarr-core/`. The roadmap's section 7.1
   layout names `generated/sections.sqlite`; today `generated/`
   discipline exists only as the compiler's cache-manifest artefact
   names (`persona_runtime.py:5936`: `sections.jsonl`,
   `embeddings.db`, `manifest.json`) — JSONL, not SQLite, and the
   embeddings entry is an honesty placeholder whose hash is `None`
   (`:5746–5762`, `:5838`).
4. **The tree already contains a production-grade FTS5 discipline —
   for sessions, not persona.** `hermes_state_common.py:941` (`FTS_SQL`)
   and `:1066` (trigram), `hermes_state_fts.py` (CJK bigram tokenizer,
   layout registry, corruption discipline), `hermes_state_search.py`
   and `tools/session_search_tool.py` prove the patterns P2 needs:
   external-content FTS5, stable indexed-content projection, trigger
   discipline with rebuild markers, WAL, fail-open reads. P2 reuses
   these *patterns*; it must not reuse the session tables, the
   session schema, or import `hermes_state*` from the plugin (wrong
   owner, wrong lifecycle — section 2).
5. **Semantic similarity is honestly unavailable, by design, today.**
   `hybrid_components` (`persona_runtime.py:1346`) records
   `semantic_similarity: available False — no embedding surface is
   owned by this plugin`, and every `retrieval_score` (`:1358`)
   carries `semantic: None`. P.007's job is to make that component
   *available under consent*, preserving the honesty discipline:
   when embeddings are off, unconsented, or the provider is down,
   the score still records `None` — never a faked or stale value.
6. **Nothing in the tree can cite exactly or read canon in full.**
   Retrieval results carry verbatim section *text* but no source
   path, byte range, line range, or hash — because `parse_sections`
   (`:918`) normalises text (blank-line collapse, trailing-strip)
   and discards offsets entirely; the returned text is therefore
   *not* guaranteed byte-identical to the source. The generic file
   tool (`tools/file_tools.py:605`) pages by line with a ~100K-char
   formatted budget, redaction, and dedup stubs — a lawful agent
   tool, but not a full-fidelity persona read. Exact citation and
   paged full-fidelity read are both new P2 surfaces (sections 5, 8).
7. **Adjacent retrieval bridges truncate — lawfully for episodes,
   never as a model for canon.** MemPalace and OpenViking bridges
   cap content at 800 chars with an ellipsis
   (`mempalace_retrieval.py`, `openviking_retrieval.py`) and the
   context packet is bounded at 6,000 chars by default
   (`context_packet.py:13`). Those bounds govern *packets of
   episodic memory*; P2's canonical path must keep the W03 rule:
   bounded packets, unbounded store, and any truncation visible
   with a continuation handle — never an ellipsis presented as the
   whole.
8. **SQLite FTS5 is available on this host, verified this run:**
   system Python `sqlite3` reports SQLite 3.46.1,
   `ENABLE_FTS5` = 1, and a scratch `CREATE VIRTUAL TABLE ... USING
   fts5` succeeds. The laptop was under shared load during the
   audit (load average ~0.6/2.1/3.5, ~22 GB MemAvailable); no heavy
   suite was run, per the prep-only scope.

## 1. Source audit — what exists vs what must be built

All line numbers measured on the banked tree at b5c6743a22,
2026-11-07 ~23:18 EST, in `~/hermes-team-05`.

### 1A. The persona compiler and its section model (build on)

`plugins/volmarr-core/persona_runtime.py` (15,408 lines, 486 `def`s):

| Asset | Evidence | P2 disposition |
|---|---|---|
| Stable section identity | `stable_section_id(role, section_id)` `:904` returns `role.section`; `parse_sections` `:918` slugs headings, disambiguates duplicates in document order (`name`, `name_2`, …), keeps a `preamble` section | REUSE unchanged. P2 keys every index row by this id (plus `document_id`, section 3) |
| Section record shape today | `parse_sections` returns heading / level / normalised text / authored priority only — no byte range, no line range, no source path, no per-section hash | EXTEND via W03: Team 04 draft section 4 already specifies byte ranges from the streamer; P2 consumes them, never re-derives identity |
| Compiled index (Layer B) | `PersonaCompiler.compile` `:13711` builds `index`: role, section_id, stable_id, heading, level, estimated tokens, verbatim-ish text, priority, priority_level per section | The indexer's input contract. P2 persists exactly this population (plus W03 byte ranges) into SQLite |
| Change detection | `hash_record` / `detect_changes` / `reload_plan` (`:1842+`, `:1900+`, `:1950+`): per-document sha256 by role, kernel hash, persona hash; reload chain names `rebuild_retrieval_index` as a step | REUSE as the incrementality trigger: a changed document hash is what schedules re-indexing of that document only |
| Cache-manifest discipline | `:5495+`, `cache_manifest` `:5767`, `_validate_cache_manifest` `:5795`; artefact names `:5936` (`sections.jsonl`, `embeddings.db`, `manifest.json`) | MIRROR the discipline (generated, deletable, validated, hash-pinned) for `sections.sqlite`; the embeddings placeholder convention is the honesty model for section 7 |

Compiler limits that bound P2 until W03 lands (do not code around
them inside P2): the 512 KiB per-document cap (`:720`, enforced
`:13731`), whole-file `read_text` ingestion (`:13735`), hash of
re-encoded text rather than original bytes (`:13740`), and
`parse_sections` normalisation (blank runs collapsed `:~945`), which
means today's section text can differ from source bytes. Any P2
prototype built pre-W03 must label its citations *unverified*
(see Open Questions).

### 1B. The section 13 retrieval layer (keep as the scorer)

- `retrieval_score` (`:1358`): pure, explainable; components keyword
  0.35 / heading 0.10 / task 0.25 / role 0.10 / priority 0.20, each
  in [0, 1], plus `semantic: None`. Tokenisation is `_tokens`
  (`:1310`) over the slug vocabulary with a retrieval stopword set
  (`:1296`).
- `retrieve_sections` (`:1403`): requires actual contact (keyword,
  heading or task > 0 — a bare priority float is not a result),
  sorts by descending total with stable-id tiebreak, clamps limit
  to 1–20 (`RETRIEVAL_DEFAULT_LIMIT = 5`, `RETRIEVAL_MAX_LIMIT =
  20`, `:1219`).
- Role-scoped retrievers (Service Bible `:4682`, Relationship
  `:4874`, Tool Policy `:5069`, Memory Policy `:5364`, Avatar
  `:5462`) and the section 14 router (`route_sections` `:1515`) and
  section 15 budgeter all consume the same in-memory index.
- `PersonaRetriever` (`:13920`) and its five siblings compile fresh
  per call — no caching, no persistence, no shared handle.
- Explainability assets: `persona_explain` (`:8995`) verifies stable
  ids against a compile's index but `explains_live_response` is
  honestly `False`; `retrieval_drift_audit` (`:10932`) re-runs
  sections 13/14 over a supplied compile and checks contact,
  membership and `semantic is None`. There is **no retrieval
  receipt**: no record of query, budget, chosen spans, or omitted
  sections survives a call. Section 6 of this draft designs it.
- Test anchors: `tests/plugins/test_volmarr_persona_retrieval.py`
  (341 lines, 8 tests: task classification, hybrid-component
  honesty, score purity, roadmap-example retrieval, bounds,
  determinism/writes-nothing, no-config emptiness, profile
  isolation) and `test_volmarr_persona_phase_retrieval_drift.py`
  (502 lines). P2 acceptance keeps both green unchanged against
  the FTS-backed path (section 9, step 3).

### 1C. Session FTS5 (patterns to mirror, code not to touch)

- DDL: `hermes_state_common.py:941` `FTS_SQL` — external-content
  `messages_fts` over a stable-projection view (`messages_fts_src`)
  so triggers, backfill and `rebuild` always agree on indexed
  content; `:1066` `FTS_TRIGRAM_SQL` for substring/CJK; the header
  comment at `:935` records the checksum-drift lesson that forced
  the single-projection rule. `SCHEMA_VERSION = 32` (`:289`),
  `FTS_STORAGE_VERSION` tracked independently, `MAX_FTS5_QUERY_CHARS
  = 2_048` (`:335`).
- Tokenizer engineering: `hermes_state_fts.py` — a loadable
  `cjk_unicode61` tokenizer, a stored-layout registry
  (`FTS_VTABLE_LAYOUTS`) so older DDL is recognised rather than
  rebuilt blindly, FTS-scoped corruption detection, fail-open
  trigger detach.
- Search discipline: `hermes_state_search.py` — FTS5 query
  sanitisation (special-char stripping, operator handling), LIKE
  fallback for short CJK terms, slow-query logging.
- P2 takes from this: external content, one stable projection,
  versioned layout, sanitised queries, corruption honesty. P2 does
  NOT take: the messages schema, tool-row exclusions, session
  lineage, or any import of `hermes_state*` into the plugin — the
  persona index lives and dies with the persona library
  (`generated/`), independently of `state.db`.

### 1D. Other retrieval surfaces (integrate by reference, never duplicate)

- MemPalace bridge (`mempalace.py`, `mempalace_retrieval.py`):
  read-only BM25 over `chroma.sqlite3`, opt-in, default off,
  5 results, 800-char content cap. Episodic ownership stays with
  MemPalace (roadmap section 8: integrate without duplicating
  ownership).
- OpenViking bridge (`openviking_retrieval.py`): opt-in, dev-auth
  fail-closed, server-side embedding of the query disclosed in its
  header — the consent-gate precedent P.007 generalises (section 7).
- Ravens (`ravens.py`, `ravens_writes.py`): Huginn is the retrieval/
  ingestion association engine, profile-bound only when constructed
  directly (`backend="local"`); bridge-mediated Huginn is NO-GO.
  P2 does not route canonical section search through Huginn; the
  E-wave (W08) owns that integration. P2 receipts reserve a
  provenance slot so a later Huginn-sourced hit can be recorded
  without schema change.
- Bifröst/Mímir (`memory_fabric.py`): health probes only today.
  Same reservation as Huginn.
- ChatIndex: named in the roadmap (sections 8, 11) as a concept to
  integrate; **no ChatIndex code exists in this tree** (grep-verified
  this run). Recorded as absent, not as a dependency.

### 1E. Generic paged read (not the persona read)

`tools/file_tools.py:605` `read_file_tool`: line-offset pagination
(default limit from `DEFAULT_READ_LIMIT`, max 2,000 lines), ~100K-char
budget on *formatted* output with a `next_offset` continuation,
sensitive-text redaction, dedup stubs for repeated reads, and a
hard block after 4 identical reads. Correct for an agent browsing
code; wrong for canon: redaction and formatting mean the bytes
returned are not the bytes stored, and there is no hash, no section
addressing, and no completeness proof. Section 8 designs the
persona paged read as a separate, plugin-side surface.

### 1F. Embeddings (absent, honestly)

No embedding provider, model, vector store, or similarity function
exists in `plugins/volmarr-core/` (grep-verified: every `embedding`
mention is the section 13/48 honesty record). External candidates
named by the roadmap: A.E.S.I.R. local inference or a chosen local
embedding server first; cloud only after explicit per-source
authorization (roadmap section 8). Their live contracts are E-wave
territory (W08/E.02); P.007 designs the gate and the storage so the
provider can arrive later without re-indexing canon (section 7).

## 2. Design principles (P2-specific, under the roadmap invariants)

1. **One compiler, one scorer, one new store.** P2 adds exactly one
   artefact — `generated/sections.sqlite` — and one service layer
   inside `persona_runtime.py`'s ownership (new module beside it in
   `plugins/volmarr-core/`, e.g. `persona_index.py`, importing the
   compiler's types; never a second parser, slugger, or scorer).
   Section identity, priorities, task classification and the
   section 13 score stay where they are.
2. **FTS generates candidates; section 13 still decides.** BM25
   narrows the corpus to a candidate set; the existing explainable
   score re-ranks deterministically. A hit that FTS finds but
   section 13 scores as no-contact is not returned — the section 13
   contact rule (section 1B) survives the move to SQLite.
3. **The index is derived and disposable.** Deleting
   `sections.sqlite` and re-indexing from the W03 manifest +
   canonical sources must reproduce it (modulo timestamps). Canon
   bytes never live only in the index: section text in the DB is a
   cache of source slices, always verifiable against the source
   hash (Invariant C).
4. **Exactness is a separate mode, never a rendering of a snippet.**
   Anything labelled a citation is sliced from source bytes at
   serve time and hash-checked (section 5). Anything derived
   (snippets, summaries) is labelled derived.
5. **Omission is always visible.** Every bounded answer names what
   it left out and how to continue (subspan handles, section 4;
   receipts, section 6). A truncated-looking answer with no
   continuation is a defect, per the roadmap's section 8 wording.
6. **Offline is the default truth.** With no consent records and no
   network, every P2 feature except embeddings works in full, and
   the receipt records `cloud_egress: 0` (roadmap section 8
   acceptance). Embeddings-off must be indistinguishable from
   embeddings-never-built in behaviour, except speed.
7. **Execution bounds live on operations, never on documents.**
   Page sizes, candidate caps, query length caps and timeouts are
   operations config (mirroring Team 04 draft section 2's no-cap
   clause); no P2 schema field may carry a document-size limit.

## 3. Index schema — `generated/sections.sqlite` (P.006 core)

Location: `HERMES_HOME/personas/<persona-id>/generated/sections.sqlite`
(roadmap section 7.1 layout), beside the W03 `manifest.json`.
SQLite settings: WAL journal, `synchronous = NORMAL` for the index
(it is rebuildable; the manifest keeps FULL discipline),
`foreign_keys = ON`, user_version pragma = index schema version.
One writer (the indexer, under the same library lock family as the
manifest commit), many readers.

### 3.1 Tables

```sql
-- One row; bumped schema + build provenance.
index_meta(key TEXT PRIMARY KEY, value TEXT NOT NULL)
  -- keys: schema_version, compiler_version, tokenizer_profile,
  --       built_from_manifest_generation, created_at, rebuilt_at

-- Mirror of the W03 manifest document record (never authoritative;
-- the manifest is). Lets one SQL query scope by role/trust/privacy.
documents(
  document_id   TEXT PRIMARY KEY,      -- W03 manifest id
  persona_id    TEXT NOT NULL,
  role          TEXT NOT NULL,
  path          TEXT NOT NULL,         -- relative to library root
  sha256        TEXT NOT NULL,         -- source BYTES (W03 streamer)
  byte_length   INTEGER NOT NULL,      -- diagnostics only
  revision      INTEGER NOT NULL,      -- W03 per-document revision
  manifest_generation INTEGER NOT NULL,
  status        TEXT NOT NULL          -- complete/indexed/outdated/...
)

-- One row per canonical section, keyed by W03/W04-stable identity.
sections(
  section_pk    INTEGER PRIMARY KEY,
  document_id   TEXT NOT NULL REFERENCES documents,
  stable_id     TEXT NOT NULL,         -- stable_section_id(role, slug)
  section_id    TEXT NOT NULL,         -- bare slug
  role          TEXT NOT NULL,
  heading       TEXT NOT NULL,
  level         INTEGER NOT NULL,
  ordinal       INTEGER NOT NULL,      -- document order
  byte_start    INTEGER NOT NULL,      -- into source bytes (W03)
  byte_end      INTEGER NOT NULL,
  line_start    INTEGER NOT NULL,      -- 1-based, derived at index time
  line_end      INTEGER NOT NULL,
  section_sha256 TEXT NOT NULL,        -- hash of the exact byte slice
  priority      REAL NOT NULL,         -- compiler priority (float)
  priority_level TEXT NOT NULL,        -- P0..P4
  tags          TEXT NOT NULL,         -- JSON array, section_tags()
  in_kernel     INTEGER NOT NULL,
  UNIQUE(document_id, section_id)
)

-- Logical subspans of large sections (section 4 of this draft).
subspans(
  subspan_pk    INTEGER PRIMARY KEY,
  section_pk    INTEGER NOT NULL REFERENCES sections,
  ordinal       INTEGER NOT NULL,      -- order within the section
  byte_start    INTEGER NOT NULL,      -- absolute in source bytes
  byte_end      INTEGER NOT NULL,
  overlap_prev_bytes INTEGER NOT NULL, -- shared with previous subspan
  boundary_kind TEXT NOT NULL,         -- paragraph/sentence/codeblock/heading-hard
  subspan_sha256 TEXT NOT NULL,
  UNIQUE(section_pk, ordinal)
)

-- The search projection. EXACTLY ONE projection feeds both FTS
-- tables (the hermes_state_common.py:935 lesson): normalised text
-- is computed by one Python function at index time and stored on
-- the row; FTS tables are external-content over it.
search_rows(
  row_pk        INTEGER PRIMARY KEY,   -- = section_pk or subspan_pk
  granularity   TEXT NOT NULL,         -- 'section' | 'subspan'
  section_pk    INTEGER NOT NULL REFERENCES sections,
  heading_norm  TEXT NOT NULL,
  body_norm     TEXT NOT NULL,         -- normalised search text
  tags_text     TEXT NOT NULL
)
CREATE VIRTUAL TABLE sections_fts USING fts5(
  heading_norm, body_norm, tags_text,
  content='search_rows', content_rowid='row_pk',
  tokenize='unicode61 remove_diacritics 2');
CREATE VIRTUAL TABLE sections_fts_trigram USING fts5(
  body_norm,
  content='search_rows', content_rowid='row_pk',
  tokenize='trigram');

-- Append-only indexing journal: the incremental audit spine.
index_journal(
  generation    INTEGER NOT NULL,
  document_id   TEXT NOT NULL,
  old_sha256    TEXT, new_sha256 TEXT,
  change_kind   TEXT NOT NULL,         -- added/changed/removed/reindexed
  sections_added INTEGER, sections_removed INTEGER,
  committed_at  TEXT NOT NULL,
  PRIMARY KEY(generation, document_id)
)
```

Embeddings storage is a *separate* file (`generated/semantic/
embeddings.sqlite`, section 7) so the lexical index never carries
vector weight and deleting all vectors is one file removal.

### 3.2 Normalisation (search fields only — source bytes untouched)

`body_norm` is derived by one documented function: Unicode NFC,
case-folded, diacritics preserved in the stored field (the
`remove_diacritics 2` tokenizer option folds at tokenise time, so
`þór` is findable as `thor` while the stored text keeps its marks).
Runes (U+16A0 block) and Old Norse diacritics must survive
tokenisation — asserted by dedicated tests (section 9), because
`unicode61` category handling of runes is a measured risk, with the
trigram table as the guaranteed fallback for exact substring hits.
Code fences, tables and verse are indexed as text; no Markdown
structure is stripped beyond heading separation already done by
the compiler.

### 3.3 Incremental update algorithm

Trigger: W03 manifest generation change (or explicit reindex).

1. Read the manifest at generation G; read `index_meta`'s
   `built_from_manifest_generation` G'. If G = G', no work.
2. Diff documents by `sha256`: unchanged documents are not touched
   (their rows, subspans and FTS entries stand).
3. For each added/changed document, in ONE transaction per
   document: delete its old search_rows/subspans/sections, insert
   the new population from the compiler/streamer feed, append the
   journal row. A crash mid-document leaves the old population or
   the new one — never a mix (the manifest generation only
   advances in `index_meta` after ALL document transactions
   commit; a behind index reports itself `outdated`, honestly).
4. Removed documents: rows deleted in one transaction, journal
   records the removal with the last known hash (mirroring Team 04
   draft section 2's absence-is-a-state rule for the manifest).
5. Garbage collection: obsolete generations of derived artefacts
   (old embedding builds, staged rebuild DBs) are deleted only
   after the new snapshot verifies (roadmap section 8), where
   verification = row counts + per-section slice-hash spot audit
   + an FTS `integrity-check`.
6. Full rebuild = drop and re-run from the manifest; it must be
   possible under constrained memory because the streamer feed is
   paged (Team 04 draft section 3) — the indexer never holds a
   whole document, let alone the corpus.

Concurrency: readers open the DB read-only and pin the generation
they read; a mid-read reindex is detectable via `index_meta` and
re-readable, never a mixed view (same rule as the W03 manifest).

### 3.4 Query path

1. Sanitise the query with the session-search discipline
   (FTS5 special chars neutralised, operators explicit, length
   capped as an *operations* bound — start from
   `MAX_FTS5_QUERY_CHARS = 2_048` parity).
2. Candidate generation: phrase/exact terms hit the trigram table;
   word terms hit `sections_fts` with `bm25(sections_fts, 10, 1,
   5)` (heading weighted above body above tags — weights are
   design values to be measured in step 1 of the build order, not
   doctrine). Candidate cap is an operations bound (default 200
   rows) recorded in the receipt.
3. Re-score candidates with the untouched section 13
   `retrieval_score` (query tokens, task tags from `classify_task`,
   role, priority) plus a normalised BM25 component; the fusion
   weight is a named constant with the section 13 weights left
   intact when BM25 is absent (pure-FTS-off fallback = today's
   behaviour). Contact rule enforced after fusion.
4. Deterministic order: descending total, stable-id tiebreak —
   identical inputs give identical outputs across runs and across
   index rebuilds (asserted in tests).
5. Whole-section-first serving under the caller's budget (section
   15 budgeter, unchanged): whole section if it fits; else subspan
   windows + continuation handles (section 4).

## 4. Subspans and continuation handles (P.006)

A subspan is a *retrieval aid only* (roadmap section 8): it never
mutates, replaces, or renames its parent section, and no subspan
id is ever a citation target for identity — citations name the
section; subspans name positions inside it.

- **When:** a section is subspanned when its byte length exceeds an
  operations threshold (design value 32 KiB, tunable; sections at
  or under it are served whole or not at all — no handles needed).
- **Where boundaries fall:** paragraph breaks first, then sentence
  boundaries, then line breaks; fenced code blocks and tables are
  kept intact where possible (a fence longer than the target size
  splits at line boundaries and records `boundary_kind =
  codeblock`). Target subspan size is an operations value (design
  8 KiB) with a recorded overlap (design 256 bytes) shared with the
  previous subspan so a phrase straddling a boundary is findable
  in at least one subspan whole.
- **Identity:** a subspan is `(stable_id, ordinal)`; ordinals are
  section-content order and are recomputed on reindex of that
  section only. A subspan carries absolute source byte offsets, so
  serving it is the same slice-and-verify operation as serving a
  section (section 5).
- **Continuation handle:** an opaque-to-the-caller string encoding
  `{document_id, stable_id, next_byte_offset, section_byte_end,
   source_sha256, manifest_generation}` (base64url JSON; integrity
  by the source hash check at serve time, not by signature — the
  store is local and operator-owned). Handles are *validated, not
  trusted*: on use, the server re-checks that the document hash
  and generation still match; a stale handle fails with a named
  `stale_continuation` result that re-resolves the section and
  offers the current first window — it never silently serves
  bytes from a changed source under an old handle.
- **Navigation shape:** every windowed answer carries
  `more_from_this_section: {remaining_bytes, next_handle,
  section_total_bytes}` — the roadmap's “more from this section”
  made structural. Reading a section to its end via handles must
  reproduce the section's exact bytes concatenated (minus declared
  overlaps, which are marked in each window) — asserted in tests.

## 5. Exact-citation mode (P.006)

Separate from ranked retrieval and from derived snippets
(roadmap section 8). A citation request names a stable_id (or a
subspan position inside one) and returns:

```json
{
  "mode": "exact_citation",
  "persona_id": "...", "document_id": "doc_...",
  "role": "soul", "stable_id": "soul.section_slug",
  "path": "canonical/SOUL.md",
  "byte_start": 12345, "byte_end": 13456,
  "line_start": 210, "line_end": 228,
  "source_sha256": "<whole-source bytes>",
  "section_sha256": "<exact slice>",
  "manifest_generation": 17, "index_generation": 17,
  "text": "<bytes sliced from the source at serve time, UTF-8>"
}
```

Rules:

1. `text` is sliced from the canonical source file at serve time
   (never served from the FTS store), and the server verifies
   `sha256(slice) == section_sha256` before returning; a mismatch
   is a named corruption result, not a quiet re-read.
2. Citation mode performs no ranking, no summarisation, no
   normalisation: CRLF, trailing spaces and blank runs survive
   exactly as stored (this is why it depends on W03 byte ranges
   and cannot be built honestly on today's normalised
   `parse_sections` text).
3. A citation for a section that exists in the manifest but is
   `unindexed`/`outdated` is still servable — citation needs the
   manifest's byte range, not the FTS index — and the result
   records the index status honestly.
4. Privacy/trust labels from the manifest (`privacy_class`,
   `trust_class`, `destinations`) ride every citation, per
   Invariant E; a citation is operator-surface data and is never
   emitted to an untrusted tool surface (mirroring roadmap
   section 9's receipt rule).

## 6. Retrieval receipts (P.006)

One receipt per retrieval / citation / paged-read call, stored as
JSONL under `generated/receipts/` (the roadmap section 7.1 layout
already reserves this directory) and returned to the caller in
full. Receipts are the audit spine P.012 explain (W07) will read;
P2 defines the schema, W07 builds the commands on it.

| Field | Content |
|---|---|
| `receipt_id`, `ts` | UUID, UTC timestamp |
| `kind` | `retrieval` / `exact_citation` / `paged_read` / `continuation` |
| `persona_id`, `profile_scope` | Who was searched; cross-profile access is impossible by construction and any attempt is recorded |
| `query` | The query as received + the sanitised FTS form actually run |
| `task_tags` | `classify_task` output used in scoring |
| `index_generation`, `manifest_generation` | The generations the answer was computed against |
| `candidate_count`, `candidate_cap` | FTS narrowing, honestly reported |
| `budget` | Caller budget (tokens/chars) and what it admitted |
| `chosen` | Per hit: stable_id, subspan ordinal if windowed, byte range, full score breakdown (section 13 components + bm25 + semantic or `None`), why-chosen reason (contact components > 0) |
| `omitted` | Per considered-but-not-served section: stable_id + named reason (`over_budget`, `no_contact`, `below_threshold`, `duplicate_of <stable_id>`) — the roadmap's “why other sections were omitted” |
| `continuations_issued` | Handles minted by this call (ids, not contents) |
| `embeddings` | `off` / `local:<provider>:<model>:<version>` / `cloud:<provider>:<model>` + consent record ids consulted |
| `cloud_egress` | Count of external calls made (0 in offline mode) |
| `latency_ms`, `index_status` | Measured cost; `current`/`outdated` honesty |

Retention is an operations setting; receipts contain queries and
section ids but never section *text*, so the receipt store cannot
become a shadow copy of canon.

## 7. Embeddings consent gate (P.007)

Default state: **off**. No vector is computed, stored, or queried
until the gate opens, and the lexical path is complete without it.

### 7.1 Gate model

- **Consent is per-source and recorded**, extending the
  OpenViking precedent (section 1D) from one bridge to the corpus:
  a consent record names `document_id` (or a role/glob the
  operator explicitly expands to document ids at grant time),
  provider kind (`local` / `cloud`), provider + model + version +
  dimensions, granted_by, granted_at, and scope (`embed_query_only`
  is not a thing — queries are embedded by the *retrieval* call
  under the same record or not at all).
- **Local-first:** a local provider (A.E.S.I.R. or a chosen local
  embedding server, contracted in W08/E.02) needs one consent
  record per source naming it. **Cloud** needs a *separate*
  explicit record per source; a local consent never implies cloud
  consent, and a source whose `privacy_class = private` is refused
  cloud embedding at grant time unless the operator overrides
  with a named, recorded exception (the W07 P.018 filter family
  consumes the same records — one gate, two consumers).
- **Fail-closed checks at embed time**, not just grant time: a
  document whose consent was revoked, whose provider version
  drifted from the pinned record, or whose privacy class was
  raised is excluded and the exclusion is receipted (section 6).

### 7.2 Storage and scoring

- Vectors live in `generated/semantic/embeddings.sqlite`:
  `embeddings(document_id, stable_id, subspan_ordinal NULL,
  provider, model, version, dimensions, source_sha256,
  vector BLOB float32, created_at)` with a consent-record FK by
  value. Vectors are content-addressed by source hash: a changed
  section invalidates exactly its vectors.
- Revocation deletes the source's vectors in the same transaction
  that records the revocation. Export of the persona library
  excludes `semantic/` unless the operator explicitly includes it.
- Fusion: when (and only when) a valid consent covers both the
  query embedding and the candidate's source, the section 13
  score gains its `semantic` component (cosine, [0, 1]) with a
  named fusion weight; the receipt records the component. In
  every other case `semantic` stays `None` and the five-component
  score is bit-identical to today's — the honesty tests of
  section 1B keep passing in embeddings-off deployments.
- Rebuild: vectors are the most disposable artefact in the
  design; a provider/model change is a delete-and-rebuild, never
  a migration of old vectors.

## 8. Paged full-fidelity read (P.006)

A plugin-side read service over canonical sources, distinct from
the generic file tool (section 1E):

- **Addressing:** by `document_id` + byte cursor (not line
  offset): `read(document_id, cursor, max_bytes)` returns
  `{bytes_b64 or text, next_cursor, page_sha256, source_sha256,
  byte_start, byte_end, source_byte_length, complete}`.
  `max_bytes` is an operations bound (design default 64 KiB);
  pages split only at UTF-8 character boundaries, and the cursor
  names the exact next byte — no character is ever split or lost.
- **Fidelity:** no redaction, no formatting, no line numbering, no
  dedup stub, no repeat-read block. Concatenating all pages
  reproduces the source byte-for-byte; the final page's
  `complete: true` plus the whole-source hash is the proof. (The
  generic tool's redaction exists because it serves arbitrary
  files to a model; this surface serves the operator's own canon
  to the operator's surfaces — CLI/TUI/Web per roadmap section 8 —
  under the profile's own trust scope. Model-facing reads keep
  going through budgeted retrieval.)
- **Section-shaped paging:** `read_section(stable_id, cursor)`
  is the same service bounded to a section's byte range, and is
  the transport continuation handles (section 4) resolve through.
- **Search-in-read:** the read surface exposes the FTS search of
  section 3 so a surface can jump from a hit to its page; this is
  an integration of the two P2 services, not a third index.

## 9. The 100 MB buried-section recall gate plan (W04 gate)

Gate (WAVE_PLAN, Team 05): **buried-section recall in 100 MB
corpus, zero source loss.** Roadmap section 8 acceptance adds:
exact-match recall against buried passages, stable references
after unrelated edits, index rebuild under constrained memory, no
cloud egress offline. Runner discipline: `scripts/run_tests.sh`
only, counts from log files, one heavy suite at a time on the
shared laptop, test trees staged directly under `$HOME` (the
ravens staging lesson), disposable profile only — never the
dormant `~/.hermes`.

Corpus: share W03's deterministic generator (Team 04 draft
section 7) and extend it; the same corpus serves both gates.
P2-specific structure:

- A many-file tree totalling ≥100 MB plus the W03 size ladder;
  planted **needle sections**: at measured depths (first 1%,
  middle, last 1% of the corpus and of individual files), sections
  whose bodies contain unique exact phrases (a nonce phrase, an
  Old Norse phrase with diacritics, a rune sequence, a code block
  line, a table cell string) recorded in a needle manifest with
  their stable ids and byte ranges.
- One giant section ≥10 MB with needles at its start, middle and
  end (subspan territory), one no-heading file with a needle, a
  needle inside a fenced code block (must be found as content,
  never parsed as a heading), duplicate-heading needles
  (`name` vs `name_2` must resolve to the right one).

Assertions:

1. **Exact-match recall = 100%.** Every needle phrase, queried
   verbatim, returns its section in the top-k (k = the section 13
   default limit raised for the test, recorded) — hit@k per
   needle in the log, and exact-citation mode returns the needle's
   byte range with a verifying slice hash. A single miss fails
   the gate; “recall” is not averaged away.
2. **Zero source loss.** Per-file and corpus sha256 before index,
   after index, after 100 reindex cycles, after full rebuild —
   identical (the W03 invariant, re-asserted from the P2 side).
3. **Reference stability.** Edit an unrelated early section
   (insert a paragraph in file 1); every needle's stable_id is
   unchanged and its citation still verifies (byte ranges may
   move; identity and content hash may not).
4. **Subspan completeness.** Concatenated continuation windows
   over the giant section reproduce its exact bytes (overlap
   accounting per section 4); every giant-section needle is
   reachable both by search and by continuation from the
   section head.
5. **Constrained-memory rebuild.** Full index rebuild of the
   100 MB corpus under a capped address space (`ulimit -v`, value
   measured and recorded on this laptop) completes; peak RSS is
   a function of work-unit size, not corpus size (compare 5 MB
   vs 100 MB runs, as in Team 04 draft section 7).
6. **Offline honesty.** Whole gate runs with embeddings off and
   network denied: every receipt shows `cloud_egress: 0` and
   `semantic: None`; results are identical to the embeddings-off
   control run of the existing section 13 tests.
7. **Interruption.** Kill the indexer mid-corpus; on restart the
   index is either at the old generation whole or completes to
   the new one — a query during the window reports
   `index_status: outdated`, never wrong results presented as
   current.
8. **Control group.** With the plugin disabled, nothing about
   stock Hermes changes; with the index deleted, the in-memory
   section 13 path still answers small-corpus queries exactly as
   today (the fallback is the incumbent, not a stub).

Performance evidence filed with the ticket: index build wall
time, query P50/P95 over the needle set, DB size vs corpus size,
peak RSS — numbers from logs, on this laptop, contention noted.

## 10. Build order for the W04 implementation run

Dependency note first: **steps 2+ consume W03 outputs** (manifest
schema, streamer byte ranges, source-byte hashes). If W03 has not
banked when W04 starts, step 1 proceeds and the rest wait — P2
does not grow interim parallel versions of W03 artefacts
(Team 04 draft section 4 made the same promise in the other
direction for subspans).

1. **P.006a — index skeleton + tokenizer measurement.**
   `sections.sqlite` DDL (section 3), meta/journal, manifest
   reader; a measurement harness comparing `unicode61` vs
   trigram recall on runes / diacritics / CJK / code before the
   tokenizer profile is frozen into `index_meta`. Exit: schema +
   layout-version discipline in place; tokenizer decision recorded
   with numbers.
2. **P.006b — incremental indexer.** Streamer feed → sections /
   subspans / search_rows in per-document transactions (section
   3.3); hash-record diff as the trigger; kill-mid-index tests.
   Exit: changed-file-only reindex proven (journal shows untouched
   documents untouched).
3. **P.006c — FTS query path under the section 13 scorer.**
   Candidate generation + fusion (section 3.4) behind the existing
   `PersonaRetriever` API, so router/budgeter/role retrievers gain
   scale without new call sites. Exit: section 1B test anchors
   green unchanged; determinism across rebuild asserted.
4. **P.006d — subspans + continuation handles.** Section 4,
   including stale-handle honesty and window-concatenation tests.
5. **P.006e — exact-citation mode + receipts.** Sections 5–6;
   receipts land in the same step because citation without a
   receipt would recreate the audit gap this wave exists to close.
6. **P.006f — paged full-fidelity read.** Section 8, CLI surface
   first (operator surface), TUI/Web wiring rides the same service
   when W05/W07 surfaces arrive — P2 does not build web UI.
7. **P.007 — embeddings consent gate.** Section 7: consent records,
   semantic store, fusion behind the gate, revocation deletion.
   Provider contract is stubbed against a local fake for tests;
   the real A.E.S.I.R./local-server contract lands with W08/E.02
   and must not block P.006 banking. Exit: gate tests prove
   off = absent (scores bit-identical), unconsented source never
   embedded, revoked source's vectors gone.
8. **P.016-style gate battery for W04.** Section 9 in full.
   Exit: the W04 gate line in CAMPAIGN_STATE_MODERNIZATION.md can
   be written with log-backed counts.

Banking note for the keeper: each step banks separately in this
order via the standard route (team worktree tests green via
`scripts/run_tests.sh` → `~/hermes-hack-forge` merge → fetch +
remote-diff → explicit refspec push → ls-remote verify →
campaign state update). No step touches README.md; every
intentional runtime difference gets its CUSTOMIZATIONS.md ledger
row; the index is a generated artefact and is never committed.

## 11. Risks and open questions

Risks:

- **W03 slip cascades.** P2's schema is honest only on top of
  byte-exact ingestion. Pressure to “just index what the compiler
  has today” would bake normalised text and a 512 KiB ceiling
  into citations — the exact failure the roadmap exists to end.
  The build order's dependency note is the guard; hold it.
- **Tokenizer truth.** `unicode61` handling of runes and combining
  diacritics is asserted by design, not yet measured on this
  corpus. Step 1 exists because a wrong tokenizer choice silently
  fails buried-needle recall for exactly the material Volmarr
  cares most about; the trigram fallback must be proven, not
  assumed.
- **Score-fusion drift.** Adding BM25 (and later semantic) to the
  section 13 total can silently re-order results the contract
  tests pin. Fusion weights are named constants, the no-FTS
  fallback is bit-identical to today, and any re-ordering in the
  roadmap-example test is a stop-and-review event.
- **Receipt volume.** One receipt per call on a busy gateway is
  real disk growth; retention/rotation is an operations setting
  with a sane default, decided in step 5 — but receipts are never
  silently dropped while debugging a recall failure.
- **Shared-laptop load.** The 100 MB battery is the heaviest W04
  artefact on a host shared with Samverk / Mythic Coder / Rúnmál.
  One-heavy-suite rule applies; a wall time under contention is
  not a baseline (campaign law).

Open questions (for Volmarr / keeper, none blocking this draft):

1. Branch naming: WAVE_PLAN's `team-05/w04-p2-retrieval` vs the
   on-disk `yrsa/hermes-team-05` used here and by Teams
   02/03/04/09 — keeper to reconcile once, campaign-wide.
2. Citation before W03? If Volmarr wants exact citation earlier
   than W03 banking, the only honest interim is citations over
   documents ≤512 KiB labelled `unverified` (normalised-text
   risk, section 1A). This draft recommends waiting; his word
   decides.
3. Receipt retention default: keep-all (disk grows) vs rolling
   window (e.g. last 10,000 per persona) — operator preference,
   needed by build step 5, not before.
4. Cloud embedding providers: P.007's gate is provider-agnostic;
   naming the first approved cloud provider (if any, ever) is
   Volmarr's decision and is NOT needed for P.006 or for the
   local-first gate tests.
5. Should the paged read serve *derived* artefacts (kernels,
   compiled IR) as well as canon, or canon only? This draft
   designs canon only; kernels already have their own surfaces.

## Appendix — method and evidence

- Worktree: pre-existing `~/hermes-team-05` at b5c6743a22 (banked
  W02 closure), branch `yrsa/hermes-team-05`, clean at audit
  start; this draft is the only new file.
- Source reads: `persona_runtime.py` targeted sections (`:720`,
  `:858–1050`, `:1212–1650`, `:5495–5950` summaries, `:8976–9100`,
  `:10800–10950`, `:13697–14100`), `context_packet.py` (full),
  `mempalace_retrieval.py` / `openviking_retrieval.py` (full),
  `ravens.py` (head), `hermes_state_common.py` (`:289–335`,
  `:935–1075`), `hermes_state_fts.py` (head), `hermes_state_search.py`
  (head), `tools/file_tools.py` (`:605–760`, schema `:1162–1168`);
  tree-wide greps for `FTS5`, `sections.sqlite`, `embedding`,
  `ChatIndex`, `subspan`, `citation`, `receipt` (the last four:
  no persona-side hits — the absence is the finding).
- Host checks this run: SQLite 3.46.1 with FTS5 enabled (scratch
  in-memory FTS5 table created), `uptime` / `free -m` snapshot;
  no test suites run (prep-only scope, shared laptop).
- Nothing in this draft was copied from the roadmap without a
  source check: every roadmap claim about current code (in-memory
  retrieval, unavailable semantics, artefact names, session FTS
  existence) was re-verified against the banked tree and matched.
