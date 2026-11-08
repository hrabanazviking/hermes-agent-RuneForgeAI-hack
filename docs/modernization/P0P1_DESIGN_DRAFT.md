# P0/P1 Design Draft — Phases P0+P1: Unbounded Canon

Team 04 (W03 prep), 2026-11-07. Status: DRAFT, uncommitted, in worktree
`~/hermes-team-04` (branch `yrsa/hermes-team-04`; WAVE_PLAN.md names the
branch `team-04/w03-p0p1-canon` — the on-disk precedent of Teams 02/03/09
is the `yrsa/hermes-team-NN` form, and this draft follows that precedent;
the keeper should reconcile the naming once).

Scope note: PREP / AUDIT / DESIGN only. No code was changed, nothing was
committed or pushed this run. W03 formally follows W02 (Team 03, U2);
its base is the banked W01 tree. All findings below were verified from
source on purplelongship on 2026-11-07 unless marked otherwise.

Base verified this run: worktree created fresh from the main checkout —
`git worktree add ~/hermes-team-04 -b yrsa/hermes-team-04 origin/main`;
HEAD = `1cd7d59015cb46775cc666655a99a44b9b0a1aa3` (W01 banking closure),
matching `origin/main` in `~/hermes-hack-forge`. README.md untouched
(never touched by this team; main's sha256 stands at
336813d11bbe5aa2ff745b4a4bc3abcf2a283cd13971c0c11d061377129db7f3).

Governing texts read this run: CAMPAIGN_STATE_MODERNIZATION.md,
WAVE_PLAN.md (Team 04 section), docs/modernization/BASELINE_2026-11-07.md,
docs/modernization/integration-lock.json, and the roadmap's Parts I–II
(sections 0–8), the wave table (section 30) and the persona ticket list
(section 31) of ROADMAP_HERMES_MODERNIZATION_UNBOUNDED_PERSONA_2026-11-07.md.

## 0. Headline findings

1. **The truncation that matters lives in one upstream-owned file.**
   Every authored-document prompt path (SOUL.md, .hermes.md/HERMES.md,
   the AGENTS.md directory chain, CLAUDE.md, .cursorrules) funnels
   through a single function, `_truncate_content`, in
   `agent/prompt_builder.py`. That is good news for design: one seam,
   not five. It is also the central constraint: `prompt_builder.py` is
   core Hermes, and ground rule 3 keeps personal code in plugins — so
   W03 must NOT fork this function. The canonical library is a new
   plugin-side path (volmarr-core / persona_runtime), and the stock
   path stays byte-for-byte upstream behaviour when the plugin is off
   (roadmap sections 9 and 28 make that an acceptance test, and P.010
   in W05 owns removing the duplicate legacy injection on opt-in
   profiles — W03 does not pre-wire the live prompt).
2. **Ingestion today is read-all-then-cut, never streaming.** Both the
   stock loader and the persona compiler read whole files into memory
   (`_read_text_with_timeout`, `path.read_text`). A 100 MB SOUL.md
   would be fully resident before a single byte is truncated or
   compiled. The P.002 streamer is therefore a new ingestion front
   door, not a tweak of the existing reads.
3. **The persona compiler already owns section identity and per-document
   hashes — build on it, never beside it.** `persona_runtime.py`
   (15,408 lines) already has `stable_section_id` and a cache-manifest
   discipline. Roadmap section 8's law ("no second compiler") applies
   to the manifest too: the P1 manifest extends the compiler's
   document records; it is not a parallel registry.
4. **Not every `max_chars` in the tree is a defect.** The repo carries
   dozens of caps that are execution, transport or display bounds
   (gateway message chunking, untrusted-metadata neutralisation,
   history storage). Section 1 classifies them. The W03 invariant is
   narrow and precise: no cap on the **storage, import, export, edit,
   hash, backup or indexing** of canonical authored documents
   (roadmap section 6, guarantee 1). Bounded *retrieval packets*
   remain lawful (Invariant D).
5. **The live corpus is tiny today; the 100 MB gate is synthetic.**
   Measured this run: repo-root `SOUL.md` = 667 bytes;
   `~/.hermes/SOUL.md` = 667 bytes (the laptop deployment is dormant —
   baseline finding — and must never be a migration test target).
   The W03 gate corpus must be generated deterministically (section 6).

## 1. Truncation-site inventory (file:line evidence)

All line numbers measured on the banked tree at 1cd7d59015,
2026-11-07 ~22:15 EST.

### 1A. Authored-document prompt path — the W03 target seam

`agent/prompt_builder.py`:

| Site | Evidence | Behaviour |
|---|---|---|
| Cap constant | `:1033` `CONTEXT_FILE_MAX_CHARS = 20_000` | Floor for every context file |
| Head/tail ratios | `:1034–1035` head 0.7 / tail 0.2 | Kept fraction when truncating |
| Dynamic cap | `:1040–1048` `_CONTEXT_FILE_WINDOW_FRACTION = 0.06`, `_CONTEXT_FILE_DYNAMIC_CEILING = 500_000`, `_dynamic_context_file_max_chars()` | Cap = 6% of model window, clamped to [20K, 500K] |
| Config override | `:1051–1054` `_get_context_file_max_chars()` | `context_file_max_chars` in config wins; still a cap |
| Truncator | `:1462` `_truncate_content(content, filename, max_chars=None, ...)` | Head+tail kept, middle replaced by a marker listing omitted headings (`_omitted_headings`, `:1497`); queues a user-visible warning via `drain_truncation_warnings` |
| SOUL.md | `:1512` `load_soul_md()` → `:1556` returns `_truncate_content(_scan_context_content(...), "SOUL.md", ...)` | The persona file itself is truncated on the live path |
| Project files | `:1577` `_context_section()` (used by .hermes.md, CLAUDE.md loaders); `:1696` AGENTS.md directory chain; `:1716` .cursorrules | Same truncator for every project context type |
| Assembly | `:1724` `build_context_files_prompt()` | One project type wins; SOUL.md appended unless `skip_soul` |

Whole-file read feeding the truncator: `_read_text_with_timeout`
defined `:53`, used at `:1536` (SOUL.md) and `:1568` (context files).
Nothing streams; the cap is applied *after* a full in-memory read.

Related fixed cap on the same surface: `agent/subdirectory_hints.py:26`
`_MAX_HINT_CHARS = 32_000`, applied at `:307–308` via the same
`_truncate_content` with `queue_warning=False` (silent by design —
log + marker only). Classification: project-context hint, not persona
canon; W03 records it, W05/P4 decides if hints join the canonical
library. Not a W03 build item.

### 1B. Curated memory caps — adjacent, owned by W06, not W03

- `tools/memory_tool.py:56`: `MemoryStore(int(mem_cfg.get(
  "memory_char_limit", 2200)), int(mem_cfg.get("user_char_limit",
  1375)))` — the built-in curated MEMORY/USER store defaults the
  roadmap cites (section 0.1). These cap the *curated store*, a
  distinct thing from a full historical corpus. P.014 (W06, Team 07)
  owns bridging these files to an unbounded backing store. W03's
  design must keep the two concepts separate in the manifest: a
  document's `role` may be `memory`/`user`, but W03 ingestion never
  routes canonical bytes through `MemoryStore` limits.

### 1C. Plugin-side bounded packet — lawful, not a storage cap

- `plugins/volmarr-core/context_packet.py:13` `DEFAULT_MAX_CHARS =
  6000`; `:73–80` `_max_chars()` clamps the configured
  `context_packet_max_chars` between MIN/MAX bounds. This bounds a
  *retrieval/active-context packet* — exactly the execution-side
  bound Invariant D permits and section 6 guarantee 5 requires.
  W03 leaves it alone; the manifest design (section 2) keeps packet
  budgets out of document records entirely.

### 1D. Persona compiler ingestion — non-streaming today

`plugins/volmarr-core/persona_runtime.py` (15,408 lines):

- `:13592` `payload = yaml.safe_load(path.read_text(encoding="utf-8"))`
  and `:13735` `text = path.read_text(encoding="utf-8")` — whole-file
  reads on the compile path. No truncation was found in the compiler
  (its `context_truncation` mentions, `:2258`/`:2296`, are drift-danger
  classifications *against* truncation, not truncators), but there is
  no streaming and no byte-offset discipline: P.002's streamer must
  feed this compiler without changing its IR contracts.
- Existing assets to reuse: `stable_section_id(role, section_id)` at
  `:904`; per-document sha256 carried in the IR (see `:1842–1872`);
  the section-48 cache manifest (`:5495+`, `cache_manifest` at
  `:5767`, `_validate_cache_manifest` at `:5795`) — a generated,
  deletable artefact discipline the P1 manifest mirrors.

### 1E. Out of scope — execution/transport/display caps (do not touch)

Verified present and explicitly NOT W03 defects: gateway message
chunking (`gateway/platforms/helpers.py:454+` paragraph splitting for
platform message limits); untrusted sender/metadata neutralisation
caps (`gateway/session.py:274`, `:283`); hosted-room identifier
validation caps (`gateway/hosted_rooms_common.py:24` and siblings);
API-server stored-history tool-output cap, opt-in and default **0 =
store verbatim** (`gateway/platforms/api_server.py:1047–1048`,
`api_server_openai_routes.py:182+`); display label caps
(`agent/display.py:344`). Changing any of these is scope creep and
risks the 929/7/1 contract baseline.

### 1F. Existing test anchors

`tests/agent/test_prompt_builder.py` (58 test functions; truncation
section opens at line 107, importing `_truncate_content` and
`drain_truncation_warnings`) and `tests/agent/test_context_file_sources.py`
pin the stock behaviour. W03 acceptance includes these passing
unchanged with the plugin disabled — the stock path is the control
group for every W03 experiment.


## 2. Manifest schema design (P.001 + P.003 foundation)

Storage: `generated/manifest.json` inside the per-persona library
(roadmap section 7.1 layout: `HERMES_HOME/personas/<persona-id>/`,
`canonical/` for sources, `generated/` for manifest + indexes,
`backups/` for snapshots). The manifest is **derived and rebuildable**:
deleting it and re-ingesting must reproduce it exactly (modulo
timestamps). Canonical bytes never live in the manifest.

One record per source document. Fields (roadmap section 7.2, made
concrete):

| Field | Type | Rule |
|---|---|---|
| `schema_version` | int | Manifest format version; migrations are explicit, dry-runnable |
| `generation` | int | Monotonic; bumped once per committed transaction (section 5) |
| `document_id` | string | Stable, path-independent: minted at first ingestion as `doc_<sha256-of-canonical-relpath + persona-id>` truncated to 16 hex chars, recorded forever; a rename keeps the id and updates `path` (see Open Questions) |
| `role` | string | Open vocabulary from `persona.yaml` role map (soul, identity, service_bible, relationships, memory_policy, tool_policy, avatar, worldview, knowledge/*, custom roles) — new roles need metadata, never code edits (roadmap 7.1) |
| `path` | string | Path relative to the persona library root; absolute paths forbidden in records |
| `namespace` | string | Storage namespace / profile scope; cross-profile references are rejected at validation |
| `sha256` | hex | SHA-256 of the **original bytes**, computed streaming at ingestion |
| `byte_length` | int | Diagnostics only. Its field description in the schema must state: never an admission ceiling |
| `revision` | int | Per-document monotonic counter, +1 per committed content change |
| `external_revision` | string? | Optional upstream/git revision for mirrored sources |
| `label`, `locale`, `dialect`, `tags`, `category` | strings | Operator-facing metadata; `dialect` = Markdown flavour note, informational |
| `priority` | enum P0–P4 | Retrieval/kernel priority (roadmap 7.2); does not affect storage completeness |
| `trust_class` | enum | From P.001 policy: authored-canon / operator / imported-trusted / imported-untrusted |
| `privacy_class` | enum | private / shared / public — feeds the P.018 cloud-egress filters (W07) |
| `destinations` | list | Tool/destination restrictions per source (roadmap 7.2) |
| `persona_id` | string | Owning persona; shared-vs-personal scope flag beside it |
| `anchors` | list | Optional chapter/section anchors declared by the operator |
| `include_rules` | list | Include/glob rules that admitted this file (folder-tree ingestion) |
| `status` | enum | `complete` / `unindexed` / `indexing` / `indexed` / `outdated` / `unreadable` / `corrupt` (roadmap section 6 guarantee 4 — "not in this prompt" is never a status) |
| `conflict_policy` | enum | How a changed-on-disk source reconciles (hash-is-authority; see section 3 watch strategy) |
| `state` | enum | `active` / `archived` |
| `first_seen_at`, `last_verified_at`, `last_compiled_at` | timestamps | UTC ISO-8601 |
| `provenance` | object | Source kind (`local-file`, `local-tree`, `git-checkout`, `connector`), origin locator, read-only-mirror flag |

**The no-cap clause, enforced mechanically:** the JSON Schema for the
manifest declares `additionalProperties: false` on document records,
and the forbidden key set — `max_chars`, `max_tokens`, `max_bytes`,
`char_limit`, `token_limit`, any key matching `^max_` or `_limit$` on
a document record — is rejected by the validator with a named error.
A contract test greps the schema and the ingestion code path for
these keys (P.002/P.016 test family). Operational quotas (import
pacing, parser work-unit size, indexing concurrency) live in a
separate `operations` config object, never on document records —
this is the roadmap's "operational import pacing and indexing work
quotas live elsewhere" (7.2) made structural.

Validation rules beyond shape: `sha256` must verify against the file
at `path` for status to be `indexed`; a record whose file vanished
becomes `unreadable` with the last known hash retained (never silently
dropped from the manifest — absence is a state, not a deletion).

## 3. Streaming byte-exact ingestion design (P.002)

Principles: the canonical store **is** the operator's files, in place.
Ingestion reads; it never copies, rewrites, normalises or re-encodes
canonical bytes. All derived data (manifest, section index, kernels)
is regenerable.

Pipeline per document:

1. **Open + stat.** Record `byte_length` from stat as a diagnostic;
   never compare it against any admission limit (there is none).
2. **Chunked read.** Fixed work units (design value 1 MiB, an
   *operations* quota, tunable) via a buffered binary reader. Peak
   memory is a function of the work unit, not the file size — this
   is the property the 100 MB test asserts (section 6).
3. **Incremental hash.** SHA-256 updated per chunk over raw bytes;
   the digest at EOF is the manifest `sha256`. No decode happens
   before the hash — bytes first, interpretation second.
4. **Streaming UTF-8 validation.** An incremental decoder validates
   without materialising the whole text; invalid sequences set
   status `unreadable` with the byte offset of the first failure.
   No lossy replacement characters are ever written anywhere.
   Non-UTF-8 encodings are out of scope unless the operator consents
   per-source with round-trip verification (roadmap 7.3).
5. **Parse feed.** Decoded text is fed to the Markdown parser as
   line/AST events carrying **byte ranges** (start/end offsets into
   the original bytes). The parser's work units are bounded the same
   way as the reader's; an enormous single paragraph is a stream of
   events, not one allocation (roadmap 7.3 edge-case list).
6. **Section extraction.** AST events drive section segmentation
   under the identity rules of section 4; each section record stores
   its exact byte range so P2 can later serve whole sections or
   extract windows without re-reading semantics into the bytes.
7. **Checkpointing.** After each work unit the ingester may persist a
   resume checkpoint: `{document_id, byte_offset, hash_state,
   parser_state_ref}`. Checkpoints are serialised hash state, never
   partial text. An interrupted import resumes from the checkpoint
   or restarts the document cleanly; a half-ingested document is
   status `indexing`/`unindexed`, never `complete`.
8. **Commit.** On EOF: hash finalises, section set finalises, and the
   manifest update commits transactionally (section 5). Until commit,
   the previous manifest generation remains the truth.

Concurrency/watch: concurrent safe reads (readers never block the
operator's editor); change detection is mtime-as-hint, hash-as-
authority (roadmap 7.3) with debounced re-ingestion of changed files
only. The watcher must exclude `generated/` to avoid recursive
self-triggering. Include expansion is cycle-safe and path-safe:
symlink escapes rejected by default with a precise diagnostic
(roadmap 7.3); path traversal outside the persona library root is a
hard validation error.

Failure honesty: any I/O error mid-stream aborts that document's
transaction, keeps the prior generation, and records the failure in
the ingestion receipt (path, offset, error) — surfaced to the
operator, never swallowed into a "complete" status.

## 4. Markdown AST + stable section identity (P.005)

Build on the compiler, per section 1D: section identity reuses
`persona_runtime.stable_section_id(role, section_id)` (`:904`) and the
compiler's slug rules; W03 specifies the AST-facing rules the streamer
needs and files any gap as a compiler ticket rather than growing a
second parser identity scheme.

- **Heading sections.** A section begins at an ATX/Setext heading and
  runs to the next heading of equal-or-higher level. Its slug is the
  compiler's existing normalisation of the heading text.
- **Duplicate headings.** Deterministic ordinal disambiguation: the
  second identical slug in a document gains a stable suffix derived
  from its ordinal among duplicates (the compiler already renames
  deterministically — roadmap 7.3 names "deterministic renamed
  headings" as a required case); ordinals are document-order, so an
  unrelated edit elsewhere never renumbers them.
- **No-heading files.** One root section spanning the document; its
  identity is the document id itself.
- **Preamble.** Content before the first heading is a section with a
  reserved slug (`_preamble`), so front matter, comments and verse
  are addressable, never dropped (roadmap section 6 guarantee 6).
- **Fences and tables.** `#` lines inside fenced code are not
  headings (the stock `_omitted_headings` at `prompt_builder.py:1497`
  already implements this distinction — reuse the rule); tables,
  code and long sections are preserved as section content verbatim.
- **Byte ranges, not offsets-in-text.** Every section records raw
  byte start/end into the source file, so CRLF files and multibyte
  Unicode keep exact ranges; identity is independent of byte offset
  (a section keeps its id when an earlier section grows — the
  property P2's index depends on, roadmap section 8).
- **Subspans are P2.** A giant section stays one section in W03.
  Logical subspans with continuation handles are Team 05's P.006
  work; W03's byte ranges are designed so subspans can be derived
  later without re-ingestion.

## 5. Transactional manifest updates (P.004)

- **Write pattern.** Serialise the new manifest to
  `generated/manifest.json.tmp-<generation>`, fsync the file, atomic
  rename over `generated/manifest.json`, fsync the directory. A crash
  at any point leaves either the old or the new complete manifest —
  never a torn one.
- **Generation discipline.** `generation` increments exactly once per
  committed transaction; a transaction may carry many document
  changes (a folder-tree import is one transaction). Readers pin the
  generation they opened; a mid-read generation change is detectable
  and re-readable, never a mixed view.
- **Journal.** Each commit appends one line to
  `generated/manifest.journal.jsonl`: generation, timestamp, per-doc
  `{document_id, old_sha256, new_sha256, old_revision,
  new_revision, change_kind}`. The journal is the audit spine for
  P.012 diff/explain (W07) and for migration rollback (section 6 of
  this draft, plan step 5).
- **Locking.** A single-writer advisory lock on the library
  (`generated/.manifest.lock`, flock) serialises committers;
  ingestion workers prepare changes lock-free and take the lock only
  to commit. Lock timeout is an operator-visible error, not a retry
  loop.
- **Recovery.** On open, a manifest whose `generation` disagrees with
  the journal tail, or whose JSON fails validation, is quarantined
  to `generated/manifest.corrupt-<ts>.json` and rebuilt from sources
  + journal; sources are never touched by recovery. This mirrors the
  compiler's cache-manifest validation discipline (section 1D).


## 6. SOUL.md + role-doc migration dry-run plan (P.003)

Hard safety frame first: the laptop's `~/.hermes` is a **dormant**
deployment (baseline: SOUL.md + logs only, last written 2026-05-24;
W00 backup at `~/hermes-backups/2026-11-07-w00/`). Migration tests
never run against it. All dry-runs and the eventual real migration
use a disposable profile staged under `$HOME` (the ravens lesson:
staging outside `$HOME` breaks relative bindings — stage test trees
directly under `$HOME`).

Dry-run procedure (produces a report, writes nothing to any live
profile):

1. **Inventory.** Enumerate candidate sources in two distinct sets,
   never conflated (roadmap 0.1 warning): (a) repo-root example files
   in the worktree — `SOUL.md` (667 B, measured this run),
   `IDENTITY.md`, `AGENTS.md`, `USER.md`, `MEMORY.md` and kin as
   present in the tree; (b) the selected profile's effective files
   under its `HERMES_HOME`. Each set is reported separately with
   per-file sha256 + byte length.
2. **Role mapping proposal.** For each file, propose `role`,
   `trust_class`, `privacy_class`, `priority` per the P.001 policy;
   unmapped files are listed as unmapped — the dry-run never guesses
   a role silently.
3. **Simulated ingestion.** Run the P.002 streamer in verify-only
   mode over the set: streaming hash vs on-disk hash per file,
   section segmentation preview (section ids + byte ranges), status
   per file. No manifest is committed; the simulated manifest is
   part of the report.
4. **Provenance report.** One report per run: source set, per-file
   hashes before/after (identical — the dry-run must prove it moved
   nothing), proposed manifest, section map, warnings (symlinks,
   unreadable files, duplicate roles). Stored as a dated artefact
   under the persona's `generated/receipts/` in the disposable
   profile only.
5. **Idempotence check.** Dry-run twice over the same set: the two
   reports must be identical except timestamps. Any diff fails the
   ticket's dry-run gate.
6. **Rollback rehearsal.** In the disposable profile only: perform
   the real migration, then roll back via journal generations to the
   pre-migration manifest and verify every source hash matches the
   step-1 inventory. Rollback never edits sources — it only rewinds
   derived state, because migration itself never edits sources.

Acceptance for P.003 (per roadmap 7.3): 100 import/export/reindex
cycles byte-for-byte on the migrated set (section 7 test plan), the
persona can list every source and its origin, no cross-profile file
is reachable.

## 7. 100 MB byte-identity test plan (P.016, W03 gate)

Gate (roadmap section 30, W03): **100 MB corpus byte-identical.**
Runner discipline: `scripts/run_tests.sh` only, counts from log
files, one heavy suite at a time on the shared laptop, test trees
staged directly under `$HOME`.

Corpus: a deterministic generator (fixed seed, checked in with the
tests) producing:

- Size ladder (roadmap section 6 tests): single files at 1 KB,
  20 KB (just under the old floor), 20,001 chars (the first size the
  stock path truncates), 501 KB (past the old ceiling), 5 MB;
  plus a many-file tree whose total is ≥100 MB.
- Adversaries: one giant single section (no internal headings) of
  ≥10 MB; a no-heading file; duplicate headings; `#` lines inside
  fenced code; CRLF line endings throughout one file; Unicode —
  runes, Old Norse diacritics, combining characters, emoji; YAML
  front matter; HTML comments; tables wider than any sane wrap;
  a file that is exactly a work-unit multiple and one that is one
  byte over.

Invariants asserted per file and for the corpus:

1. sha256 of original bytes == sha256 after ingestion == after
   reindex == after export, across **100 cycles** (roadmap 7.3
   acceptance). Export must reproduce the original byte stream, not
   a re-serialisation.
2. Every section's byte range, sliced from the original file,
   hashes to the section digest recorded at ingestion.
3. Manifest contains no forbidden key anywhere (schema scan, section
   2 of this draft); a canary document record *with* a `max_chars`
   key is rejected by the validator.
4. Peak RSS during the 100 MB ingestion stays within an operations
   bound independent of corpus size (assert with a generous ceiling
   measured on this laptop; the assertion is "does not grow with the
   file", tested by comparing 5 MB vs 100 MB runs).
5. Interruption: kill the ingester mid-file (SIGKILL at a randomised
   offset); on restart the document is `indexing`/`unindexed` or
   resumes from checkpoint to the identical final hash — never
   `complete` with a wrong hash, never a torn manifest (kill during
   the commit window included).
6. Stock-path control: with the plugin disabled, `load_soul_md` on
   the 501 KB file still truncates exactly as upstream does, and
   `tests/agent/test_prompt_builder.py` passes unchanged — proof
   W03 added a path instead of mutating the old one.
7. Low-memory/restart behaviour (roadmap section 6 tests): ingest
   under a constrained `ulimit -v` in the disposable profile fails
   honestly (status + receipt), sources untouched.

Performance evidence, not vibes: the test log records wall time,
peak RSS and per-file hashes for the 100 MB run on purplelongship,
filed with the ticket. Numbers from the log or they did not happen.

## 8. Ticket-by-ticket build order for W03

Dependency order within the wave (WAVE_PLAN assigns Team 04 tickets
P.001–P.005 plus the P.002/P.003/P.016 test families; P.016 is the
wave gate and lands last, with its harness grown per-ticket):

1. **P.001 — source roles / trust / authority / secret policy.**
   Pure policy + enums first: role vocabulary, trust classes,
   privacy classes, destination restrictions, the manifest field
   contract of section 2. No code paths change. Exit: policy doc +
   schema skeleton reviewed against roadmap sections 6–7.
2. **P.002 — streamer + byte-exact ingestion.** The pipeline of
   section 3 feeding the existing compiler. Includes the forbidden-
   key schema validator and the P.002 test family (size ladder,
   Unicode/CRLF/fence adversaries, hash identity). Exit: single-file
   and tree ingestion proven on the disposable profile; compiler IR
   unchanged in shape.
3. **P.004 — transactional manifest updates.** Section 5's write
   pattern, generation discipline, journal and recovery. Lands
   before P.003 because migration safety *is* rollback safety;
   P.002 may land with in-memory manifest state behind the same
   interface so this ticket swaps the store, not the callers.
   Exit: kill-during-commit tests green.
4. **P.003 — SOUL.md + role-doc migration dry-run, then migration.**
   Section 6's plan exactly: dry-run report, idempotence, rollback
   rehearsal in the disposable profile, and only then the real
   migration of the selected profile — never the dormant laptop
   deployment as a test subject. Exit: provenance report + 100-cycle
   identity on the migrated set.
5. **P.005 — Markdown AST + stable section identity completion.**
   Section 4's rules hardened against the full roadmap 7.3 edge-case
   list, reconciled with `stable_section_id` and the compiler's
   existing renaming behaviour; any compiler gap is a compiler patch
   with its own contract tests, not a wrapper. Exit: section ids
   stable across unrelated edits (move a paragraph in section 1;
   section 9's id and byte-range *content* hash are unchanged).
6. **P.016 — scale + interruption battery (wave gate).** Section 7
   in full: 100 MB corpus byte-identical, interrupted import, index
   repair. Exit: the W03 gate line in CAMPAIGN_STATE_MODERNIZATION.md
   can be written with log-backed counts.

Banking note for the keeper: each ticket banks separately in this
order via the standard route (team worktree tests green →
`~/hermes-hack-forge` merge → fetch + remote-diff → explicit refspec
push → ls-remote verify → campaign state update). No ticket touches
README.md; every intentional runtime difference gets its
CUSTOMIZATIONS.md ledger row.

## 9. Risks and open questions

Risks:

- **Core-file gravity.** The obvious "fix" — raising or removing the
  cap in `prompt_builder.py` — violates ground rule 3, breaks the
  stock-behaviour control tests, and would be overwritten by the
  next upstream intake. The design's plugin-side path is slower to
  build and is the only durable one. Flagged so no builder takes the
  shortcut.
- **15,408-line compiler.** `persona_runtime.py` is the single most
  contract-dense file in the fork (117 Volmarr/Kista contract files
  grade this tree at 929/7/1). Streaming changes must stay behind
  its existing IR boundary; a refactor-shaped P.002 is a stop-and-
  redesign event, not a bigger commit.
- **Shared-laptop load.** The 100 MB battery is the heaviest W03
  artefact on a host shared with Samverk / Mythic Coder / Rúnmál.
  Schedule it under the one-heavy-suite rule; a wall time measured
  under contention is not a baseline (campaign law).
- **Watch-loop self-triggering.** If `generated/` is ever inside a
  watched tree, manifest commits retrigger ingestion forever. The
  exclusion is in the design (section 3); it needs a test, not just
  this sentence.
- **Encoding pressure.** Real corpora will eventually contain a
  non-UTF-8 authored file. The design refuses it honestly
  (`unreadable` + offset). Whether Volmarr wants a per-source
  encoding-consent flow in W03 or deferred is his call — see below.

Open questions (for Volmarr / keeper, none blocking this draft):

1. `document_id` on rename: this draft keeps the id and updates
   `path` (identity follows the document, not the filename). If he
   prefers rename = new document, P.001's policy changes before any
   builder mints ids.
2. Does the dormant `~/.hermes` SOUL.md (667 B) enter the first real
   migration set at all, or does W03 migrate only a fresh disposable
   profile and leave the dormant deployment to U2's launch-recipe
   work? This draft assumes disposable-only.
3. Non-UTF-8 authored files: refuse-and-report in W03 (this draft),
   or build the consent + round-trip flow now?
4. Branch naming: WAVE_PLAN's `team-04/w03-p0p1-canon` vs the on-disk
   `yrsa/hermes-team-04` used here and by Teams 02/03/09 — keeper to
   reconcile once, campaign-wide (Teams 03/09 flagged the same).

## Appendix — method and evidence

- Worktree: created this run from `origin/main` at 1cd7d59015;
  `git status` clean at creation; this draft is the only new file.
- Truncation inventory: `grep -rn max_chars` over the tree plus
  targeted reads of `agent/prompt_builder.py` (:53, :1033–1054,
  :1462–1510, :1512–1560, :1700–1800), `agent/subdirectory_hints.py`
  (:26, :295–320), `tools/memory_tool.py` (:40–70),
  `plugins/volmarr-core/context_packet.py` (:60–90) and
  `plugins/volmarr-core/persona_runtime.py` (targeted greps; the file
  was not read end-to-end — section-identity and manifest line cites
  are grep-verified).
- Corpus sizes: `wc -c SOUL.md ~/.hermes/SOUL.md` on the laptop this
  run — 667 bytes each.
- Nothing in this draft was copied from the roadmap without a source
  check: every roadmap claim about current code (20K floor, 500K
  ceiling, 2200/1375 memory defaults, head/tail retention) was
  re-verified against the banked tree and matched.
