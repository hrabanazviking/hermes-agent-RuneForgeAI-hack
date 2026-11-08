# P5 Design Draft — Phase P5: Truly Large MEMORY.md and USER.md

Team 07 (W06 prep), 2026-11-08. Status: DRAFT, uncommitted, in worktree
`~/hermes-team-07` (branch `yrsa/hermes-team-07`). This draft follows the
established prep pattern of Team 04's `P0P1_DESIGN_DRAFT.md`, Team 05's
`P2_DESIGN_DRAFT.md` and Team 06's `P3P4_DESIGN_DRAFT.md`.

Scope note: PREP / AUDIT / DESIGN only. No code was changed, nothing was
committed or pushed, and no test suite was run this run. W06 formally
follows W05 (Team 06, live persona); W05's implementation is in flight
and unbanked at audit time, so this draft notes what P5 will consume
from it but depends on none of its unbanked code.

Base verified this run: worktree fast-forwarded
`b5c6743a22..1558f55834` (clean fast-forward, no conflicts) to
`origin/main` = `1558f5583426efb7a465a344e4c700f5db38270d` (W04 banked;
W03 + W04 closures recorded in `CAMPAIGN_STATE_MODERNIZATION.md`).
README.md untouched; sha256 verified after the fast-forward:
`336813d11bbe5aa2ff745b4a4bc3abcf2a283cd13971c0c11d061377129db7f3`.

Governing texts read this run: `CAMPAIGN_STATE_MODERNIZATION.md`,
`WAVE_PLAN.md` (carried in the campaign record), the roadmap's ground
rules (§0.2), Phase P5 (§11), the wave table (§30), the shared persona
ticket list (§31) and the evidence policy (§28.2–28.3) of
`ROADMAP_HERMES_MODERNIZATION_UNBOUNDED_PERSONA_2026-11-07.md`;
`docs/modernization/W03_P0P1_IMPLEMENTATION.md`,
`docs/modernization/W04_P2_IMPLEMENTATION.md`, and Team 06's unbanked
`P3P4_DESIGN_DRAFT.md` in `~/hermes-team-06` (read as in-flight design,
not as banked fact). `docs/modernization/BASELINE_2026-11-07.md` and
`docs/modernization/integration-lock.json` exist only as untracked
files in the main forge checkout `~/hermes-hack-forge` (verified:
`git status` there shows both as `??`); they are not in any worktree
and this draft does not cite them as tree content.

Contract baseline at this base (keeper-verified at W04 banking, log
`~/team05-w04-contracts.log` on the laptop): **121 files = 976 passed /
7 failed / 1 skipped** via `scripts/run_tests.sh`; the 7 failures are
the known live-transport set, name-identical since the freeze. Every
W06 gate below is graded against this baseline.

## 0. Headline findings

1. **P5's problem is not a missing store — it is a missing bridge.**
   The stock curated store is small on purpose (2,200 / 1,375 chars),
   the W03 canonical library already ingests `MEMORY.md` / `USER.md`
   as first-class roles with byte-exact streaming, and the W04 persona
   index already retrieves over exactly that manifest. None of the
   three knows about the others at runtime: there is no code path
   that keeps a full `MEMORY.md` anywhere, and no caller connects the
   library/index to the memory tool. P.014 is a bridge ticket, and
   this draft designs it as one — no new store, no second index.

2. **The stock memory tool is live, capped, and frozen-snapshot by
   design — and P5 must not "fix" it by lying.** `tools/memory_tool.py`
   (477 lines) + `tools/memory_tool_store.py` (740 lines,
   `MemoryStore.__init__` defaults `memory_char_limit=2200`,
   `user_char_limit=1375` at :188) serve the live `memory` tool;
   both files enter the system prompt as a frozen snapshot at session
   start (module docstring, `memory_tool.py:1-5`). The roadmap §11
   distinction governs: the snapshot stays a snapshot. The adapter
   reports "full store" vs "hot digest" truthfully and never claims
   the 2,200-char snapshot contains 20 MB.

3. **Exactly one Volmarr turn path touches memory today, and it is
   not a memory system.** `PresentStateBridge`
   (`plugins/volmarr-core/present_state.py`, 467 lines) is registered
   unconditionally in `plugins/volmarr-core/__init__.py:register()`,
   owns the plugin's `pre_llm_call`, aggregates 31 `packet_items`
   sources plus its own store through
   `context_packet.ContextPacketBuilder` (default 6,000 chars, hard
   cap 16,000 — `plugin.yaml` `context_packet_max_chars`), and its
   `post_tool_call` already captures completed `memory` tool writes
   into present-state facts (`present_state.py`, `post_tool_call`,
   verified this run). W05 is formalising this bridge as the single
   prompt owner; P5 plugs into it as one more packet source, never
   as a second owner.

4. **Every external memory engine is operator-live and turn-dead.**
   Bifröst/Mímir (`memory_fabric.py`), MemPalace (`mempalace.py`),
   OpenViking (`openviking.py`), SessionDB preservation
   (`sessiondb.py`) and the ravens binding (`ravens.py`) are health
   probes whose only live caller is the `hermes volmarr` CLI
   (`plugins/volmarr-core/cli.py`: `probe_bifrost` :448,
   `probe_bifrost_muninn` :402, `probe_ravens` :407,
   `probe_mempalace` :384, `probe_openviking` :390,
   `probe_sessiondb` :396 — line numbers at this base). The ravens
   writes (`ravens_writes.py`) are likewise CLI-invoked operator
   operations behind four per-operation flags, all default `false`
   in `plugin.yaml` (`bifrost_reinforcement_enabled`,
   `bifrost_decay_enabled`, `bifrost_consolidation_enabled`,
   `bifrost_ingestion_enabled`). None of this is §28.2 debt to be
   ashamed of — probes were the banked contract — but P5 must not
   re-declare any of it "integrated memory" without a turn-path
   caller.

5. **Two retrieval bridges are wired but dark, and their flags are
   undeclared.** `MemPalaceRetrievalBridge` and
   `OpenVikingRetrievalBridge` sit in the PresentState packet-source
   tuple (`__init__.py`), each self-gated by
   `get_config("mempalace_retrieval_enabled", False)`
   (`mempalace_retrieval.py:71`) /
   `get_config("openviking_retrieval_enabled", False)`
   (`openviking_retrieval.py:69`). Verified this run: **neither key
   exists in `plugin.yaml`'s config schema** (grep count 0 for both).
   They work only if an operator hand-writes the key into profile
   config. W06 should declare both keys (default `false`) as part of
   its flag hygiene, whichever wave touches the schema first.

6. **There is no Bifröst retrieval bridge.** `volmarr-core` has
   `mempalace_retrieval.py` and `openviking_retrieval.py` but no
   `bifrost_retrieval.py`; `build_bifrost_bridge`
   (`memory_fabric.py:54`) constructs a Mímir-only bridge with
   `enable_hebbian_reinforcement=False, auto_consolidate=False,
   auto_decay=False`, and its callers are probe/CLI paths. Whatever
   Mímir contributes to a live turn today arrives, if at all, through
   other bridges' packet items — not through a Bifröst read path.
   Whether P5 builds one is an open question (§8, Q7), not an
   assumption.

7. **The persona runtime's memory contracts are real, pure, and
   uncalled.** `persona_runtime.py` (15,408 lines) carries §39 mode
   routing + §40 persona-aware memory write (:4176+), §41 "memory
   must not override persona" (contract text at :461-489), and the
   §§42–44 role retrievers; test families exist for the memory
   router, multi-memory namespaces and the memory guard service
   (`tests/plugins/test_volmarr_persona_phase_memory_router.py`,
   `test_volmarr_persona_multi_memory_namespace.py`,
   `test_volmarr_persona_memory_guard_service.py`,
   `test_volmarr_persona_mode_routing_memory.py`,
   `test_volmarr_persona_memory_avatar_policy.py`). But
   `PersonaRuntimeBridge.hooks()` returns `()` — the module reaches
   a turn only as a gated packet item whose content is a description
   of the contract system, and `persona_runtime_enabled` defaults
   `false`. W05 gives §§13–15 their first live callers; the §40/§41
   memory contracts are W06's to wire, reusing — never re-deriving —
   their record shapes.

8. **W03 + W04 already solved P5's storage and retrieval mechanics.**
   `canonical_library.py` (1,124 lines): `_FILENAME_ROLES` (:124-132)
   already maps `MEMORY.md → memory` and `USER.md → user`;
   `DocumentRecord` carries `trust_class="authored-canon"` and
   `privacy_class="private"` defaults; `StreamingIngester` (:410),
   `ManifestStore` (:709, transactional journal + generation +
   rollback) and `CanonicalLibrary` (:928) are banked and
   gate-proven at 100 MB. `persona_index.py` (1,290 lines):
   `PersonaIndex` (:276) builds `generated/sections.sqlite` (:293)
   with receipts under `generated/receipts` (:294), and offers
   `sync()` (:362), `retrieve()` (:604), `continue_read()` (:801),
   `cite()` (:872), `read_page()` (:955) and consent-gated
   embeddings (`grant_consent` :1056, `embed_document` :1131).
   Verified this run: **neither module has any caller outside the
   test suite and each other** (repo-wide grep for
   `CanonicalLibrary` / `PersonaIndex` returns only their own files
   and `tests/plugins/test_volmarr_canonical_library*.py` /
   `test_volmarr_persona_index*.py`). P5's corpus is these two
   modules, rooted at the profile's memory files, finally called.

9. **Four things the roadmap names do not exist at all.**
   (a) An unbounded memory corpus — no module roots a canonical
   library at `memories/`. (b) A derived memory digest — nothing
   derives a bounded, source-linked digest from a full `MEMORY.md`;
   present-state facts are turn captures, not a digest. (c) ChatIndex
   — zero hits for `ChatIndex` / `chat_index` / `chatindex` across
   all `*.py` in the tree; §11's "optional ChatIndex hierarchical
   retrieval" names an absent component. (d) A full-file memory
   editor — the Desktop surface
   (`apps/desktop/src/app/settings/memory/memory-layers.tsx`) is a
   provider/layer configuration panel reading `GET /api/memory`
   status; it edits no Markdown. All four are build items, and (c)
   is questioned in §8 rather than silently scheduled.

10. **The laptop profile is an empty fixture today — say so.**
    Verified this run: `~/.hermes/memories/` exists and is **empty**
    (no `MEMORY.md`, no `USER.md`); `~/.hermes/SOUL.md` exists
    (667 bytes). P5's import path therefore has two honest cases —
    first-import-from-nothing and import-of-existing-files — and all
    W06 fixtures must be staged in disposable `$HOME`-level trees
    (the ravens relative-binding law from W02), never against the
    live `~/.hermes`.

## 1. Inventory — every memory surface, classified

Classification key (roadmap §28.3 evidence stages, applied strictly):
**LIVE** = a real caller exercises it in a turn, tool call or session
today. **CONDITIONAL** = wired into the turn path but gated by a
default-off flag. **OPERATOR** = live only through an explicit
operator action (CLI command or explicitly invoked tool); no turn
path. **CONTRACT** = module + deterministic tests, no live caller.
**ABSENT** = named by the roadmap, not present in the tree.

### 1A. Stock Hermes surfaces (upstream-owned; integrate, never fork)

| # | Surface | Evidence | Class |
|---|---------|----------|-------|
| S1 | Curated memory tool + store | `tools/memory_tool.py` (477 ln), `tools/memory_tool_store.py` (740 ln), `MemoryStore` defaults 2200/1375 (`memory_tool_store.py:188`); files under `get_memory_dir()` = profile `memories/` (`memory_tool.py`); frozen prompt snapshot (docstring :1-5); `load_on_disk_store()` serves gateway/Desktop/`/memory` with the same caps | LIVE |
| S2 | Provider fabric | `agent/memory_provider.py` (253 ln) `MemoryProvider` ABC (`prefetch`, `system_prompt_block`, `on_memory_write`, `backup_paths`, …); `agent/memory_manager.py` (935 ln) `MemoryManager`; `agent/memory_context.py` (185 ln) context block + scrubber | LIVE |
| S3 | ByteRover provider | `plugins/memory/byterover/__init__.py:149` `ByteRoverMemoryProvider(MemoryProvider)` | LIVE (when selected) |
| S4 | RetainDB provider | `plugins/memory/retaindb/__init__.py:304` `RetainDBMemoryProvider(MemoryProvider)` | LIVE (when selected) |
| S5 | SessionDB + session FTS | `hermes_state.py` + `hermes_state_fts.py` (FTS5, CJK-bigram/trigram); `tools/session_search_tool.py:603` `session_search()` | LIVE |
| S6 | Memory config / editor surfaces | Desktop `apps/desktop/src/app/settings/memory/` (`memory-layers.tsx` etc., provider + layer config over `GET /api/memory`); `hermes_cli` memory setup/migration modules | LIVE (config only — no full-file editing) |

### 1B. Volmarr plugin surfaces (`plugins/volmarr-core/`)

| # | Surface | Evidence | Class |
|---|---------|----------|-------|
| V1 | PresentState + context packet | `present_state.py` (467 ln), hooks incl. `pre_llm_call`/`post_tool_call`; registered unconditionally (`__init__.py`); `context_packet.py` `DEFAULT_MAX_CHARS=6000`; `post_tool_call` captures `memory` tool writes | LIVE |
| V2 | MemPalace retrieval bridge | `mempalace_retrieval.py` (167 ln), packet source, gate `mempalace_retrieval_enabled` default False (:71), key undeclared in `plugin.yaml` | CONDITIONAL |
| V3 | OpenViking retrieval bridge | `openviking_retrieval.py` (168 ln), packet source, gate default False (:69), key undeclared in `plugin.yaml` | CONDITIONAL |
| V4 | Bifröst/Mímir attachment | `memory_fabric.py` (244 ln): `probe_bifrost`, `probe_bifrost_muninn`, `build_bifrost_bridge` (auto-* all False); CLI-only callers (`cli.py:448`, :402) | OPERATOR |
| V5 | MemPalace attachment probe | `mempalace.py` (166 ln) `probe_mempalace`; CLI `cli.py:384` | OPERATOR |
| V6 | OpenViking attachment probe | `openviking.py` (213 ln) `probe_openviking`; CLI `cli.py:390` | OPERATOR |
| V7 | SessionDB preservation probe | `sessiondb.py` (145 ln) `probe_sessiondb` (read-only audit; Hermes owns the DB); CLI `cli.py:396` | OPERATOR |
| V8 | Ravens binding | `ravens.py` (203 ln) `probe_ravens` / `build_muninn_memory` / `build_huginn_memory`; CLI `cli.py:407`; laptop `~/ravens` HEAD `fc761f020b39f9be875310d271aac7423239d5f8` re-verified this run | OPERATOR |
| V9 | Ravens writes | `ravens_writes.py` (287 ln): reinforce / decay / consolidate / ingest, one default-`false` flag each (`plugin.yaml`); CLI-invoked | OPERATOR |
| V10 | Consolidation + sleep | `consolidation.py` (431 ln): `ConsolidationStore` (path default `entity/consolidation.json`), `ConsolidationService.run` (:228), `probe_consolidation` (CLI :592); `entity_sleep_cycle` tool registered in `register()` via `register_sleep_tool` — explicit invocation only, nothing automatic | OPERATOR |
| V11 | Persona-runtime memory contracts | `persona_runtime.py` §§39–41 + router/namespace/guard contracts; `hooks()` = `()`; packet item gated by `persona_runtime_enabled` (default `false`) and carries contract description, not memory content | CONTRACT |
| V12 | Canonical library (W03) | `canonical_library.py` (1,124 ln); roles for `MEMORY.md`/`USER.md` at :124-132; callers: tests + `persona_index.py` only | CONTRACT (library) |
| V13 | Persona index (W04) | `persona_index.py` (1,290 ln); FTS5 + receipts + consent-gated embeddings; callers: tests only | CONTRACT (library) |

### 1C. Absent (roadmap-named, not in tree)

| # | Surface | Evidence | Class |
|---|---------|----------|-------|
| A1 | Unbounded memory corpus | No canonical library rooted at a profile's `memories/`; no import path for full `MEMORY.md`/`USER.md` | ABSENT |
| A2 | Derived memory digest | No digest generator exists; nothing derives a bounded digest from a full memory document | ABSENT |
| A3 | ChatIndex hierarchical retrieval | Zero grep hits (`ChatIndex`/`chat_index`/`chatindex`, all `*.py`) | ABSENT |
| A4 | Full-file memory editor | Desktop memory settings are provider/layer config (S6); no virtualised/paged Markdown editor for memory files | ABSENT |

**Headline count: 23 surfaces inventoried — 7 LIVE (S1–S6, V1),
2 CONDITIONAL default-off (V2–V3), 7 OPERATOR-only (V4–V10),
3 CONTRACT/library-only (V11–V13), 4 ABSENT (A1–A4).** Of the
Volmarr-side memory story the roadmap describes, the only component
that touches a live turn today is the bounded present-state packet
(V1) — everything else is a probe, a gated bridge, a contract, or a
library awaiting the caller W06 must write.

Test anchors already banked for these surfaces (all under
`tests/plugins/` unless noted): `test_volmarr_memory_fabric.py`,
`test_volmarr_bifrost_muninn.py`, `test_volmarr_mempalace.py`,
`test_volmarr_mempalace_retrieval.py`, `test_volmarr_openviking.py`,
`test_volmarr_openviking_retrieval.py`, `test_volmarr_sessiondb.py`,
`test_volmarr_ravens.py`, `test_volmarr_ravens_writes.py`,
`test_volmarr_consolidation.py`, `test_volmarr_present_state.py`,
`test_volmarr_context_packet.py`,
`test_volmarr_canonical_library.py` + `_scale.py`,
`test_volmarr_persona_index.py` + `_gate.py`, the five
persona-memory contract files listed in finding 7, upstream's
`tests/plugins/memory/` (10 files),
`tests/tools/test_memory_tool*.py` (4 files) and the
`tests/agent/test_memory_*.py` family. W06 adds to this estate; it
does not restart it.

## 2. What P5 is (and is not) in ticket terms

The §31 ticket list is shared across phases. W06's centre of gravity
is **P.014 — "Bridge large `MEMORY.md` / `USER.md` to full backing
stores"** — plus the memory-facing halves of tickets other waves
also touch:

- **P.014** (W06 core): the bridge itself — corpus, adapter, truthful
  full-store vs hot-digest reporting.
- **P.015** (shared; W03 owns the canon side): user-authored canon
  protection against generated summaries — for P5 this is the rule
  that no digest, consolidation or agent observation may overwrite
  or outrank an authored memory entry.
- **P.016** (shared; W03/W04 own their size gates): P5's acceptance
  sizes are §11's — 2 MB `USER.md`, 20 MB `MEMORY.md`, stored
  complete, indexed, exactly recallable — plus interrupted import
  and index repair on memory files specifically.
- **P.017** (shared; W05 owns drift): the memory half is restart and
  long-turn continuity of the corpus/digest across model switches.
- **P.018** (W06 core): private/public source filters before cloud
  inference, applied to memory retrieval and digest egress.
- **P.019** (shared): cross-machine backup/restore and schema
  migration for the memory corpus (inherits the open W00.03-ENC
  encryption question — see §8, Q6).
- **P.020** (shared): diagnostics + how-to docs for the memory
  fabric, including the full-vs-hot distinction in operator text.

Phase §11's remaining bullets map onto the design in §4: opt-in
corpus, verbatim import, derived-not-replacement digest, whole-file
UI, transactional scoped writes, old-tool compatibility, integration
by reference with session FTS / MemPalace / ravens / OpenViking,
authored-vs-observed distinction, reviewable consolidation, cold/
warm/hot tiers, WAL + multi-process concurrency, provider-contract
compatibility, and full disable-ability.

## 3. Inputs P5 consumes

### 3.1 From W03 (banked) — the corpus mechanics

- Ingestion: `StreamingIngester.ingest_file` with role from
  `_FILENAME_ROLES` (`memory` / `user`); sources read in place,
  never copied, rewritten or re-encoded (W03 implementation record).
- Identity: document ids minted once (`mint_document_id`), section
  identity via `persona_runtime.stable_section_id` — one scheme,
  already shared; P5 introduces no second identity.
- Transactions: `ManifestStore` journal + generation + rollback +
  torn-manifest quarantine/rebuild — P5's write model inherits this
  wholesale (§4.4).
- Migration discipline: P.003's dry-run (inventory, hashes,
  verify-only simulated ingest, per-file proof nothing moved) is
  the template for P5's first-import flow (§4.2).

### 3.2 From W04 (banked) — the retrieval mechanics

- Index: `PersonaIndex.sync()` diffing the W03 manifest by source
  hash; one transaction per changed document; honest `outdated`
  state on crash.
- Reads: `retrieve()` under the untouched §13 scorer, `cite()`
  slicing from canonical source at serve time with hash
  verification, `read_page()` byte-cursor paging whose concatenation
  reproduces the source byte-for-byte — the editor's read path
  (§4.6) is this, not a new pager.
- Receipts: every retrieval/citation/read appends a receipt with
  chosen/omitted + named reasons and `cloud_egress` — P5's P.018
  filter evidence rides on this field.
- Embeddings: consent-gated per document (`grant_consent` /
  `embed_document`); P5 inherits the gate unchanged — no memory
  document is embedded without the same explicit consent.

### 3.3 From W05 (in flight, unbanked — consume at banking, not before)

Per Team 06's draft (read this run; implementation in progress in
`~/hermes-team-06`): a new plugin-side `persona_live.py` pipeline
inside `PresentStateBridge.pre_llm_call`; Channel S (one registered
system-prompt section, `after_memory`) + Channel T (the existing
packet); P.011 per-model packet budgets allocating explicit shares
across kernel / retrieval / memory / project; per-turn immutable
generation snapshots. **P5 consumes exactly three things from W05:**
(1) the single-prompt-owner ruling — memory content reaches a turn
only as PresentState packet items; (2) the P.011 budget allocation
for the memory share — P5 does not set its own packet cap; (3) the
generation/snapshot discipline, so a mid-turn memory write activates
next turn, mirroring persona semantics. P5's slices M1–M4 (§5) do
not depend on W05 code; slice M5 does, and is ordered after W05
banks. If W05's final shape differs from the draft, M5 is re-planned
against the banked record — this draft does not pre-wire against an
unbanked API.

### 3.4 From the stock tree (upstream-owned, live)

- The `memory` tool schema and `MemoryStore` semantics (S1) — the
  compatibility contract for the adapter (§4.5).
- The `MemoryProvider` ABC (S2) — the corpus must remain a
  *personal-plugin* concern; stock agents with the plugin disabled
  keep stock behaviour exactly, and provider selection
  (ByteRover/RetainDB) is neither replaced nor hidden by P5.
- Session FTS (S5) — integrated by reference for episode recall;
  Hermes owns transcripts; P5 builds no second session index
  (the P2 draft's §1C ruling, applied to memory).

## 4. Design

### 4.1 Ownership model — three named things, never blurred

1. **Full store**: the profile's `MEMORY.md` + `USER.md` as complete
   authored documents, ingested into a `CanonicalLibrary` rooted at
   the profile (new module `plugins/volmarr-core/memory_corpus.py`,
   plugin-side per ground rule 3). The files on disk remain the
   canonical bytes; the manifest + index are generated, deletable,
   rebuildable artefacts — the W03/W04 discipline verbatim.
2. **Hot digest**: a *derived*, bounded, source-linked digest (see
   §4.3), stored only as generated data. It is what a small-context
   model receives by default. It never writes back over the source.
3. **Stock snapshot**: the existing 2,200/1,375-char curated store,
   untouched, still owned by `MemoryStore`. Where the digest and
   the snapshot coexist, UI and tool text name which one a given
   surface shows. The adapter (§4.5) is the only place the three
   meet, and it reports all three sizes honestly.

Namespace ruling (design decision, flagged for confirmation in
§8 Q1): `CanonicalLibrary` is keyed by `persona_id`, but
`MEMORY.md`/`USER.md` belong to the *profile/user* namespace, not
to a persona (ground rule 5: profiles, users and entities are
separate namespaces). The corpus therefore roots its library with
the profile's identity and records `persona_id` only as a consumer
label on receipts — memory is not owned by the persona that reads
it. Persona-scoped memory *views* (§§39–40 contracts) filter by
namespace at retrieval time; they do not partition the store.

### 4.2 Import — verbatim, dry-run first, two honest cases

- First import runs P.003-style: inventory the profile's
  `memories/` (files, sizes, streaming hashes), propose roles
  (`memory`/`user` from `_FILENAME_ROLES`; anything else is
  reported unmapped, never guessed), simulate ingestion
  verify-only, and print per-file proof that nothing moved. Only
  an explicit operator confirmation performs the real ingest.
- Empty case (this laptop today, §0 finding 10): import of an
  empty `memories/` produces an empty corpus + a recorded
  no-op receipt — not an error, and not a silently created pair
  of stub files.
- Import is byte-exact and truncation-free by construction
  (W03 streamer); a file that fails UTF-8 or hash verification
  refuses with the W03 named errors, leaving the stock store
  untouched and fully usable.
- After import, the on-disk files remain where Hermes expects
  them; the corpus adds manifest + `generated/` beside the
  library root, never inside `memories/` itself, so stock tooling
  sees an unchanged directory.

### 4.3 Digest — derived, reviewable, optional, source-linked

- The digest is generated from the full store by deterministic
  selection (pinned/essential sections + most-relevant sections
  under the §13 scorer), each digest entry carrying its stable
  section id + source hash, so every digest line is traceable to
  exact source bytes via `PersonaIndex.cite()`.
- No generated summary text: following the persona runtime's §7
  law, digest entries are *verbatim source sections*, selected —
  never paraphrased. Consolidation metadata (§4.7) may *link*
  sections; it may not rewrite them.
- The operator may disable digest generation entirely and run
  retrieval-only (roadmap §11 explicit option). Default posture is
  an open question (§8 Q2).
- Digest regeneration is transactional with the manifest
  generation: a digest always names the corpus generation it was
  derived from; a stale digest is labelled stale, never silently
  served as current.
- P.015 protection: authored entries outrank agent observations.
  Observations (e.g. present-state captures of memory writes,
  §40-shaped records) are stored as separate, clearly-typed
  records with provenance `agent-observed`; they can be proposed
  for promotion into the authored file only through the editor /
  tool path a human (or an explicitly authorised flow) confirms.
  Adversarial-conversation overwrite of canonical preference is
  refused by the §41 memory-guard contract, which M4 wires to its
  first live caller here.

### 4.4 Writes — transactional, scoped, audited

- All corpus writes go through `ManifestStore` transactions
  (flock single-writer, journal entry per change with old/new
  hashes, generation bump once per transaction) — the same
  guarantees W03 proved, reused, not reimplemented.
- Two write shapes, per §11: *current-fact updates* (replace a
  section's content, provenance recorded, prior revision retained
  in the journal) and *episode appends* (append-only where
  practical; no in-place rewrite of history).
- Every write is scoped: profile, persona-view, entity, user and
  project labels travel with the journal record (Invariant E), so
  a later audit can answer "who wrote this, in which scope, from
  which surface" without guessing.
- Crash behaviour inherits W03: torn state quarantines and rebuilds
  from the journal; the stock snapshot is never a casualty of a
  corpus failure (separate files, separate store).

### 4.5 The old-tool adapter (P.014 core)

- The adapter is a plugin-side module
  (`plugins/volmarr-core/memory_adapter.py`) interposed at the
  *tool-result* level, not by patching `tools/memory_tool.py`
  (core stays upstream-clean; ground rule 3).
- Reads through the stock `memory` tool keep stock semantics
  against the hot snapshot. The adapter adds a truthful status
  block to memory-tool results where the plugin owns the turn:
  full-store bytes, digest bytes, snapshot bytes, corpus
  generation, and whether the last write landed in full store,
  digest, or both.
- Writes: a stock-shaped `add`/`patch`/`remove` that fits the hot
  caps behaves exactly as today (and is mirrored into the corpus
  transactionally). A write that would overflow the hot caps
  **succeeds in the full store**, is journaled, and the tool
  result says plainly that it is not in the hot snapshot and why —
  replacing today's silent-truncation / hard-refusal cliff with
  an honest two-store answer. It never reports the snapshot as
  containing what it does not.
- Batch operations preserve the stock pinned-entry approval
  semantics (`_pin_matched_entries` behaviour): the adapter
  refuses a staged write whose matched entry changed, exactly as
  the stock gate does.
- With the plugin disabled or `memory_corpus_enabled` false
  (new flag, default `false`, declared in `plugin.yaml` — see
  §4.8), every path above vanishes and stock behaviour is
  byte-identical: the W03/W04 stock-path control discipline.

### 4.6 Editor and API — whole-file, paged, honest about limits

- Read path: `PersonaIndex.read_page()` byte-cursor paging over
  the canonical files (concatenation = source bytes, already
  contract-proven in W04). The editor never loads a 20 MB file
  into a single DOM textbox; it pages.
- Write path: section-scoped edits submitted as adapter writes
  (§4.5), so editor, tool and CLI share one transactional door.
- API audit owed at implementation time (not assumed here): the
  `GET /api/memory` surface behind the Desktop panel (S6) — its
  payload limits, and whether a paged companion endpoint belongs
  to the plugin or to a reviewed core interface. This draft does
  not invent endpoint shapes; M6 (§5) opens with that audit.
- Autosave, if offered, is debounced adapter writes with journal
  receipts — never direct file writes from the frontend.

### 4.7 Integration by reference — one owner per store

| External store | Owner | P5's use |
|---|---|---|
| Session transcripts + FTS | Hermes (S5) | Reference by session/message id for episode recall; no copy |
| MemPalace episodes | MemPalace (V5/V2) | Existing probe + gated retrieval bridge; P5 declares its flag (§4.8) and consumes its packet items; no duplicate episodic store |
| Ravens (Muninn/Huginn) | Ravens packages (V8/V9) | Associations/consolidation stay operator-invoked; P5 records corpus↔association links as derived metadata only |
| OpenViking | Bundled provider (V6/V3) | Existing probe + gated bridge; provider ownership is not duplicated (P2 §1D ruling) |
| Consolidation | `consolidation.py` (V10) | Reviewable derived metadata with source links; consolidation never deletes source history (§11); the sleep tool stays explicit |
| Persona index | W04 (V13) | The corpus's only index; no memory-specific second FTS |

Consolidation design note: `ConsolidationStore` today checkpoints
aggregate entity state counts, not memory documents. M7 extends
its *pattern* (versioned JSON, monotonic checkpoint, digests) to a
memory-consolidation record that links source sections to derived
groupings; it does not overload the entity checkpoint file.

### 4.8 Flags and configuration (all default-off, all declared)

New keys for `plugin.yaml` (W06 adds; names follow existing
convention): `memory_corpus_enabled` (bool, `false`),
`memory_corpus_digest_enabled` (bool, `false` — digest is a
second, separate opt-in), `memory_corpus_root` (str, default
profile-relative, resolved with the `memory_fabric._profile_path`
escape-refusal discipline). Hygiene fix in the same slice:
declare `mempalace_retrieval_enabled` and
`openviking_retrieval_enabled` (bool, `false`) which the bridges
already read (finding 5). No existing default changes anywhere.

### 4.9 Tiers, concurrency, backup

- Tiers: hot = digest + stock snapshot (prompt-facing); warm =
  FTS index + receipts (local, rebuildable); cold = the canonical
  files + journal + backups (the only tier that is irreplaceable).
  "Cold archive" in §11 terms = journal + manifest history kept
  with the profile backups; no separate archive format is
  invented in W06.
- Concurrency: index is SQLite WAL (W04 schema discipline);
  writes serialise on the manifest flock. The §11 multi-process
  test is scoped honestly in §6 — v0.23 has a single gateway
  owner, so the test is gateway + CLI + editor concurrency
  against one profile, not multiple gateways (see §8 Q8).
- Backup/restore: corpus backup = canonical files + manifest +
  journal (index excluded — rebuildable, and restore must prove
  that by rebuilding it). Encryption inherits W00.03-ENC, which
  is **open and unanswered**; W06 neither invents a key nor
  blocks on it — backups are produced unencrypted-local with the
  same explicit warning the W00 backup carries, until Volmarr
  rules (§8 Q6).
- Migration: manifest/index layout versions are recorded
  (W03/W04 precedent); a future layout bump ships a dry-run
  migration with rollback, per ground rule 10.

## 5. Build order for the W06 implementation run

Ordered slices; each is independently bankable, tests via
`scripts/run_tests.sh` only, counts from log files. M1–M4 have no
W05 dependency. M5 waits for W05 to bank.

- **M1 — Corpus foundation (P.014a).** `memory_corpus.py`:
  profile-rooted `CanonicalLibrary` over `MEMORY.md`/`USER.md`,
  import dry-run + confirmed import (§4.2), empty-profile case,
  `memory_corpus_enabled` flag declared. No tool or turn wiring.
- **M2 — Index wiring (P.014b).** `PersonaIndex` rooted at the
  corpus; sync-on-change driven by manifest generation; receipts
  verified; index-repair path (delete `generated/`, resync,
  byte-identical results). Declares the two retrieval-bridge
  flags (finding 5 hygiene).
- **M3 — Digest (P.014c, P.015).** Deterministic verbatim-section
  digest with provenance + generation binding; digest opt-in
  flag; authored-vs-observed record typing and the §41 guard's
  first live caller (refuse observation-overwrites-canon).
- **M4 — Tool adapter (P.014d).** `memory_adapter.py` per §4.5:
  truthful status block, overflow-to-full-store writes,
  pinned-entry approval semantics preserved, plugin-off control
  tests proving stock byte-identity.
- **M5 — Packet integration (after W05 banks).** Digest +
  retrieval as PresentState packet sources under W05's P.011
  memory budget share; generation-snapshot discipline; P.018
  private/public filter enforced on this egress (and on any
  cloud-bound retrieval), evidenced by receipt `cloud_egress`.
- **M6 — Editor/API (P.014e).** §4.6 API audit first, then paged
  read + section-scoped write endpoints and the minimal Desktop
  hookup (a "Full store" view beside the existing layers panel,
  naming hot vs full honestly).
- **M7 — Consolidation links (P.015 tail).** Memory-consolidation
  derived-metadata record per §4.7; review surface in the
  `hermes volmarr memory` CLI family; source history untouched.
- **M8 — Gates + docs (P.016/P.017/P.019/P.020 memory halves).**
  The §6 gate suite, diagnostics (`hermes volmarr memory corpus
  status` showing sizes/generation/index state/digest state),
  and operator how-to documentation.

## 6. Test and gate plan (implementation time)

Baseline discipline: full contract set via `scripts/run_tests.sh`
after every slice; the result must remain **976 passed / 7 failed
/ 1 skipped plus the slice's new tests**, the 7 failures
name-identical to the known live-transport set. New tests live in
`tests/plugins/test_volmarr_memory_corpus.py`,
`test_volmarr_memory_adapter.py`, `test_volmarr_memory_digest.py`
and a gate file `test_volmarr_memory_corpus_gate.py`.

W06 acceptance gate (roadmap §11, made measurable):

1. **Size + completeness**: staged `$HOME`-level fixture profile
   with a 2 MB `USER.md` and a 20 MB `MEMORY.md` (deterministic
   generated fixtures, W04 gate pattern): import byte-identical
   (hash proof per document), index complete, exact-phrase recall
   of buried sections in both files with hash-verified citations,
   zero source loss across reindex cycles.
2. **Small-model truthfulness**: with a bounded packet budget,
   the turn receives digest/retrieval only; the tool status block
   reports full ≠ hot honestly; a normal memory-tool write that
   exceeds hot caps lands in the full store and is reported as
   such — no silent truncation anywhere in the matrix.
3. **Restart + repair**: corpus survives process restart with
   generation intact; deleted index rebuilds to identical
   retrieval results; interrupted import (kill mid-ingest)
   leaves either the old generation or a quarantined torn state
   that repairs from the journal — never a half-visible corpus.
4. **Concurrency**: gateway turn + CLI status + editor read
   against one profile concurrently; manifest flock contention
   surfaces the named lock-timeout error, not corruption.
5. **Privacy (P.018)**: private-labelled sections never appear in
   a cloud-egress receipt path; filter test runs before any
   M5 wiring is declared live.
6. **Stock control**: plugin disabled → `tests/tools/
   test_memory_tool*.py`, `tests/agent/test_memory_*.py` and the
   full contract set pass unchanged; stock snapshot behaviour is
   byte-identical.
7. **Backup/restore (P.019)**: corpus backup from fixture
   profile A restores into fresh profile B; retrieval results
   and citations identical; index rebuilt, not copied.

Evidence staging (§28.3): M1–M4 bank as *contract implemented*;
M5 + gate items 1–3 promote the corpus to *end-to-end working*;
nothing is called *production qualified* in W06.

## 7. Risks

- **Two-store confusion is the top product risk.** If any surface
  (UI, tool text, docs) blurs full store vs hot digest, P5 will
  have recreated the exact dishonesty §11 forbids. Mitigation:
  the naming in §4.1 is normative for every string W06 ships.
- **PresentState contention.** V1 already aggregates 32 packet
  sources with per-source exception swallowing; adding memory
  sources must not slow or destabilise the one live turn path.
  M5 budgets retrieval time and fails silent-to-absent (receipt
  records the omission), never blocks the turn.
- **Persona/profile namespace bleed.** Rooting a persona-keyed
  library at profile memory is a category error if done naively
  (§4.1 ruling); multi-persona profiles (P.017) are where this
  would bite — the gate includes an A→B→A persona-view test over
  one shared corpus.
- **W05 shape drift.** M5 depends on W05's banked form, not its
  draft; if W05's budget or snapshot design changes, M5 replans.
  M1–M4 are insulated.
- **Laptop contention.** The 20 MB gate is small next to W03's
  100 MB gate, but the laptop is shared with three other
  campaigns: gates run one heavy suite at a time, in uncontended
  windows, per campaign resource law.
- **The dormant-profile trap.** All fixtures are staged trees;
  running any W06 test against the real `~/.hermes` would
  manufacture state Volmarr never made. Forbidden, as in W03.

## 8. Open questions (for Volmarr / coordinator — prep does not decide)

- **Q1 — Corpus root identity.** §4.1 rules the corpus is rooted
  in the profile/user namespace with persona as a consumer label.
  Confirm, or rule that each persona gets its own memory corpus
  (with the cross-persona sharing cost that implies)?
- **Q2 — Digest default.** Digest generation is a separate
  opt-in flag in this design (`memory_corpus_digest_enabled`,
  default `false`). Should a profile that enables the corpus get
  the digest by default, or is explicit second opt-in right?
- **Q3 — Hot snapshot future.** Once the digest exists, should
  the stock 2,200/1,375 snapshot remain independently curated
  (this draft's assumption), or should a later wave derive the
  snapshot from the digest — a core-adjacent change this draft
  deliberately does not propose?
- **Q4 — Sequencing vs W05.** M1–M4 can start the moment W06 is
  called, in parallel with W05's implementation; M5 cannot.
  Confirm Team 07 should proceed M1–M4 on that basis when the
  wave opens, rather than waiting for W05 to bank first.
- **Q5 — ChatIndex.** The component §11 names is absent from the
  tree (finding 9c). Build it in W06, defer it to the W08 engine
  pass as an E-phase audit item (this draft's recommendation),
  or drop the name from the roadmap?
- **Q6 — Backup encryption.** W00.03-ENC is already asked and
  unanswered; memory-corpus backups inherit it. W06 proceeds
  unencrypted-local with the W00 warning until you rule — no
  re-ask is intended by recording it here; it is listed only so
  the dependency is not lost.
- **Q7 — Bifröst read path.** No Bifröst retrieval bridge exists
  (finding 6). Is a Mímir read path expected inside P5's packet,
  or does Bifröst stay health/operator-only until the W08
  Bifröst/Mímir upgrade row?
- **Q8 — Concurrency scope.** §6 gate item 4 scopes concurrency
  to gateway + CLI + editor on one profile (v0.23's single
  gateway ownership). If true multi-process gateway concurrency
  is required, that is an upstream-behaviour question beyond
  W06's plugin-side remit — coordinator to confirm scope.

## Appendix — method and evidence

Audit method: light read-only inspection on purplelongship
(`git` state, `grep`/`sed` source reads, `wc -l` counts) against
the fast-forwarded tree at `1558f55834`; no test suites run, no
files modified except this draft, left uncommitted in
`~/hermes-team-07/docs/modernization/P5_DESIGN_DRAFT.md`.
Cross-checks: caller analysis by repo-wide grep for
`CanonicalLibrary`, `PersonaIndex`, `memory_fabric`/`probe_bifrost`
and `context_packet`; flag defaults read from
`plugins/volmarr-core/plugin.yaml` (144 config keys parsed) and
from bridge code where keys were undeclared; laptop state
(`~/ravens` HEAD, `~/.hermes/memories/` listing) read directly
this run. Line numbers cite the tree at `1558f55834` and will
drift as W05 lands; symbols, not lines, are the durable reference.
