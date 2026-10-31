# Hermes Hack — Campaign State

Campaign: develop the four in-repo Volmarr roadmaps on the refreshed fork
(`hrabanazviking/hermes-agent-RuneForgeAI-hack`). This file is the campaign's
portable state: any agent (Muse or Hermes) resumes from here.

## Refresh outcome — 2026-10-30 (DONE, pushed, verified)

- Working tree: `~/workspace/hermes-hack-build/` (own clone, blob:none partial
  clone + on-demand backfill; never share this checkout between writers).
- Personal main before: `111f58aa7eff47660c1c7a5e4a414b7c9c4fcc5c`
  (last push 2026-10-22).
- Upstream taken in: NousResearch/hermes-agent `main` at
  `6bb377a51d5c8e279a7a5e34d717d653d421d064` — 20,485 commits past the
  merge-base `d3b25b52ad1318c526bdb259b600eeca3d5f38e6` (2026-09-22).
- Intake followed the fork's own law (`UPSTREAM_SYNC.md`): branch
  `integration/upstream-2026-10-30`, `scripts/sync_upstream.py`, no-commit
  no-fast-forward merge, reviewed and tested before committing.
- Merge commit: `f3271cb283e5a582cd152472b273ee13132f4ab5`
  (parents: personal `111f58aa` + upstream `6bb377a5`).
- README invariant: `README.md` sha256
  `4e022de70a1c02955412e22a70889bcd72f8dafbd7f711648278c855ea9c4910`
  before the merge and after — byte-identical.
- Push 1 verified: `git ls-remote origin refs/heads/main` ==
  `f3271cb283e5a582cd152472b273ee13132f4ab5`.
- Projects briefing filed at repo root:
  `HERMES_PROJECTS_UPDATE_2026-10-30.md` (byte-identical to the prepared
  briefing, sha256
  `0f4aac2af03e6ad2f2a30fa88ce58d7b71e50d771fe255857652ae78fc1adddb`),
  commit `9754aa239a8ecf01cd1821989f0f20dc8ef0b628`.
- Push 2 verified: `git ls-remote origin refs/heads/main` == local HEAD ==
  `9754aa239a8ecf01cd1821989f0f20dc8ef0b628`.
- Current position: local `main` == origin/main ==
  `9754aa239a8ecf01cd1821989f0f20dc8ef0b628`; fork is 0 commits behind
  upstream as of the intake.

### Conflicts and their fate (2, both minimal unions)

1. `agent/redact.py` — comment-only conflict. Union header covering both
   provenances (browser_vault fill and the Secret Source apply pass); no
   code lines changed.
2. `agent/secret_sources/registry.py` — kept the fork's
   `redaction_scope: str` applier (the Kista canary contract) with
   upstream's builtin `dict[str, str]` generics.

### Intake-caused breakage found and fixed (in the merge commit)

- PyYAML dropped by upstream's ruamel migration while `volmarr-core`
  imports `yaml` directly for its entity ledgers. Restored
  `pyyaml==6.0.3` to core dependencies (comment in `pyproject.toml`;
  `uv.lock` change is +2 lines). Ledger row in `CUSTOMIZATIONS.md`.
- OpenViking provider moved from `plugins/memory/` to the plugin catalog
  (upstream, Oct 2026), so the probe contract tests saw
  `provider_missing`. Runtime probe semantics unchanged (it attests the
  installed provider); `tests/plugins/test_volmarr_openviking.py` now
  stages an installed-provider stub per test profile home. 4/4 pass.

### Tests (real numbers)

- Command: `scripts/run_tests.sh` (never bare pytest), 49 files: all 37
  `tests/plugins/test_volmarr_*.py` / `test_kista_*.py` contract files plus
  the secret/redact area files the intake touched.
- Merged tree, final run: **572 passed, 7 failed, 1 skipped**.
- Baseline (pre-merge tree `111f58aa`, its own locked env): same 7
  failures — name-identical set: 5 in `test_volmarr_core_plugin.py` and 1
  in `test_volmarr_verdandi_stimuli.py` (Verðandi Unix-socket transport;
  needs a live Verðandi service) and 1 in
  `test_volmarr_voice_runner.py` (real loopback runner; connection
  refused in this sandbox). Pre-existing, environmental, NOT intake
  regressions — recorded here so the campaign does not re-chase them.
- Runtime smoke: `hermes --version` runs on the merged tree;
  `hermes plugins list` discovers volmarr-core 0.26.0, volmarr-astrology
  0.7.0, volmarr-hamr 0.4.0, volmarr-rpg 0.8.0 as bundled.
- Test-env note: the canonical pm testenv could not stage in this sandbox
  (tar ownership on the pinned uv); tests ran via `uv sync --extra all
  --group dev --group test` into `.venv` + `HERMES_PYTHON`, which
  `run_tests.sh` honors. On Volmarr's own machines the pm path applies.

### Projects-doc inventory (Step 2)

- `HERMES_PROJECTS_UPDATE_2026-10-30.md` filed at root (above) — it is the
  current-facts briefing for all of Volmarr's other projects.
- `ARCHITECTURE_VOLMARR.md` (domain boundaries/laws) and
  `COMPAT_MANIFEST.md` (plugin compat pointers): no project-state facts;
  nothing stale to refresh.
- The four roadmaps' references to WYRD v1 / A.E.S.I.R. are
  integration-verification records of the plugin's own slices, not
  project-status claims; left as written.
- `VOLMARR_HERMES_PERSISTENT_ENTITY_ROADMAP.md` §2's "31 ahead / 27,746
  behind" is an explicitly dated 2026-09-18 record about the OLDER,
  separate `hrabanazviking/hermes-agent` fork; historical, left as
  written. This repo's §3 "re-root on current Hermes" move is what the
  2026-10-30 intake accomplished for this fork.

## Roadmap-development queue (resume points)

1. **VOLMARR_HERMES_PERSISTENT_ENTITY_ROADMAP.md** (2,423 lines) — the
   foundation road. Phases: 1 Cognition Router (§6), 2 Verðandi nervous
   system (§7), 3 Memory Fabric (§8), 4 Affective refactor (§9), 5 WYRD
   world model (§10), 6 Identity & continuity (§11), 7 Background life
   (§12), 8 Kista secret source (§13), 9 Spiritual/RPG suite (§14),
   10 Avatar & embodiment (§15), 11 Voice (§16), and beyond. Much of
   Phases 1–9 already stands implemented in the `volmarr-core` plugin
   (see `CUSTOMIZATIONS.md` ledger). Resume: verify each phase's
   acceptance against the refreshed upstream surfaces, then continue at
   the first phase whose acceptance is not met on the current tree.
2. **VOLMARR_HERMES_EMERGENT_AGENCY_ROADMAP.md** (2,590 lines) — Status:
   Design roadmap. Phases 0–12 (§7 Phase 0 Agency Contracts Before
   Intelligence → §19 Phase 12 Multi-Timescale Cognition). Resume at
   Phase 0: agency contracts before intelligence.
3. **VOLMARR_HERMES_SELF_AWARE_AGENCY_ROADMAP.md** (2,179 lines) —
   extends the persistent-entity runtime: five-layer self-model (§5),
   self-awareness layer (§6), metacognition (§9), curiosity (§10),
   Caducea-style persona files (§16). Resume at §5 (Persistent
   Self-Model) design/implementation.
4. **PERSONA_RUNTIME_ROADMAP.md** (3,236 lines) — Status: Architecture
   Roadmap; 95 numbered sections (three-layer persona model, persona
   compiler, section-aware parsing, retrieval, router, budgeter,
   anchors, persona hash, hot reload … §94 Essence). Resume at the
   foundations: §3–§6 (human-editable configuration, document
   extensions, three-layer model, persona compiler).

## Roadmap development progress

- 2026-10-30 22:01 EDT keeper tick: no live work found on this tree (no
  hermes-hack process; refresh commits landed 21:53–21:54 EDT and were
  already banked/pushed). Refresh confirmed DONE above, so the tick took
  roadmap queue item 1 (Persistent Entity) at its stated resume point.
- **Acceptance audit done** — filed at repo root:
  `PERSISTENT_ENTITY_ACCEPTANCE_AUDIT.md`. Fresh contract run on the
  refreshed tree (`scripts/run_tests.sh`, 37 volmarr/kista plugin files):
  212 passed, 7 failed, 1 skipped — the failures are the name-identical
  pre-existing environmental set recorded above (5 core-plugin + 1
  Verðandi-stimuli socket transport, 1 voice-runner loopback), i.e. no
  intake regressions. Phase verdicts: Phases 1, 4, 5, 6, 7, 8 complete;
  Phase 2 complete with live Verðandi transport NOT PROVEN in this
  sandbox; Phases 9, 10, 11, 14, 15, 16 partial; Phases 12, 17, 18, 19
  not started; Phase 13 opportunistic/partial.
- **First unmet phase: Phase 3 (Memory Fabric)** — retrieval is the gap:
  MemPalace/OpenViking retrieval and ingestion remain disabled by design,
  and Bifröst Huginn/Muninn/consolidation/decay have no contracts yet.
- **Next slice, specified implementation-ready in the audit file:
  Slice 83 — MemPalace bounded episodic retrieval** (Gate 0 = audit the
  official MemPalace ≥3.10 query API for a read-only-safe path before any
  code; then a `mempalace_retrieval.py` packet producer for the
  `relevant_episodes` section, opt-in default-off, fail-open, A→B→A
  isolated, byte-for-byte no-mutation proof, new contract test file).
  Implementation begins next tick. Banked locally only; no push.
- 2026-10-30 ~22:47 EDT keeper tick: **Slice 83 DONE, banked locally
  only, no push.** Gate 0 (official mempalace 3.11.0 wheel, scratch venv
  outside the tree): `search_memories` vector path is NOT read-only-safe
  — its ChromaDB open rewrote `chroma.sqlite3` on two consecutive calls
  and created migration marker files; the official sqlite-only BM25
  route (`vector_disabled=True`) returned the correct verbatim drawer
  from a populated palace with the palace tree sha256-identical
  before/after. Bridge implemented exactly on that route
  (`plugins/volmarr-core/mempalace_retrieval.py`, one added
  `packet_sources` producer, opt-in default-off, health-gated, bounded,
  fail-open). Tests: targeted 17/17 pass (9 new retrieval contracts);
  full volmarr/kista run (38 files) shows only the same 7 pre-existing
  environmental failures in the same 3 files — no new failures.
  Bookkeeping done: CUSTOMIZATIONS.md ledger row, roadmap §29 Milestone
  3 slice-83 paragraph, Gate 0 outcome appended to
  `PERSISTENT_ENTITY_ACCEPTANCE_AUDIT.md`. Retrieval is lexical BM25,
  not semantic — the honest scope of the read-only-safe surface.
- **Next resume point: Slice 84 — OpenViking retrieval audit** (Gate 0
  style: audit the official OpenViking retrieval surface for a
  read-only-safe path before any code), then the Bifröst
  Huginn/Muninn/consolidation/decay contracts. Banked locally only;
  pushes beyond the ordered refresh still await Volmarr's word.
- 2026-10-30 ~22:42 EDT keeper tick: **Slice 84 DONE (audit only, no
  code), banked locally only, no push.** Gate 0 against the
  catalog-pinned official source (`volcengine/OpenViking` at
  `e855796c83f9eb575d9b0f3082926660730f6a63`, Hermes plugin 2.1.2,
  server 0.5.x; latest PyPI 0.5.2.1), audited in a scratch clone
  outside the tree. **Verdict: CONDITIONAL PASS** for
  `POST /api/v1/search/find` only — its call chain (router →
  SearchService → VikingFS → HierarchicalRetriever → vector search)
  contains no corpus writes, loads no session, and runs no intent
  analysis; `/search` (session load, LLM intent pass, context-mode
  dedup state) and deprecated `/recall` are excluded as stateful, and
  a plain hit carries `abstract` only (full text arrives via the
  router's own `read_content=true` visible-content read). Conditions
  recorded in full in `PERSISTENT_ENTITY_ACCEPTANCE_AUDIT.md`: (1) the
  server's usage-audit store records search calls by default —
  server-owned accounting identical to what the official provider's
  prefetch already triggers, disclosed, not a corpus mutation; (2)
  credential-free retrieval exists only when `/health` reports
  `auth_mode == "dev"` (api_key/trusted require a key even on
  localhost; this attachment never carries credentials, so the bridge
  fails closed otherwise); (3) the server embeds the query with its
  own configured embedder, whose locality health cannot attest —
  enablement stays opt-in; (4) live-server byte measurement is NOT
  PROVEN in this sandbox (no embedding provider configured there) —
  the verdict rests on the pinned-source audit. Roadmap §29
  Milestone 3 gained the slice-84 paragraph.
- **Next resume point: Slice 85 — OpenViking bounded retrieval
  bridge**, specified implementation-ready at the end of
  `PERSISTENT_ENTITY_ACCEPTANCE_AUDIT.md` (opt-in default-off,
  health- + dev-mode-gated, `/find` only, memories only, ≤5 items at
  800 chars, fail-open, stub-server contract tests). After Slice 85:
  the Bifröst Huginn/Muninn/consolidation/decay contracts. Banked
  locally only; pushes beyond the ordered refresh still await
  Volmarr's word.
- 2026-10-30 ~23:20 EDT keeper tick: **Slice 85 DONE, banked locally
  only, no push.** Implemented exactly per the Slice 84 spec:
  `plugins/volmarr-core/openviking_retrieval.py`
  (`OpenVikingRetrievalBridge`, one added `packet_sources` producer),
  opt-in `openviking_retrieval_enabled` default off, gated in order on
  `probe_openviking` healthy and `/health` `auth_mode == "dev"` (the
  probe additively exposes `auth_mode`; api_key/trusted/unreported
  modes never receive the query; no credentials anywhere). Only the
  audited `/find` body is sent; query cap 2,000 chars; ≤5 memory hits
  at 800 chars (content, abstract fallback); bounded timeout;
  fail-open. Tests: targeted 21/21 pass (8 new stub-server contracts);
  full volmarr/kista run (39 files): **229 passed, 7 failed,
  1 skipped** — the failures are the same name-identical pre-existing
  environmental set in the same 3 files; no new failures.
  Bookkeeping done: CUSTOMIZATIONS.md ledger row, roadmap §29
  Milestone 3 slice-85 paragraph, Slice 85 outcome appended to
  `PERSISTENT_ENTITY_ACCEPTANCE_AUDIT.md`. Live-server measurement
  remains NOT PROVEN (Slice 84 honesty class).
- **Next resume point: the Bifröst Huginn/Muninn/consolidation/decay
  contracts** — Milestone 3's last remaining item (Slice 86: begin
  with a Gate-0-style audit of the existing Bifröst attachment surface
  in this tree before specifying/enabling any of Huginn ingestion,
  Muninn reinforcement, consolidation, or decay). Banked locally
  only; pushes beyond the ordered refresh still await Volmarr's word.
- 2026-10-30 ~23:09 EDT keeper tick: **Slice 86 DONE (Gate 0 audit
  only, no code), banked locally only, no push.** In-tree surface
  verified: the whole Bifröst attachment is `memory_fabric.py`
  (construct-only bridge, Mímir default, all enable flags forced
  off; read-only Mímir probe that never calls the bridge), the
  `memory health` CLI action, two `plugin.yaml` path keys, and 3
  stub-package contracts — no caller of any bridge method exists,
  and `bifrost` is not a dependency of this tree (absent from
  pyproject/uv.lock, not installed; `package_missing` is the stock
  status). External package audited in a scratch clone:
  `hrabanazviking/bifrost` at `b66e98cc` (v1.0.0;
  `COMPONENT_LICENSES.md` pins exactly that commit as provenance —
  a same-tick correction to this entry's first draft, which wrongly
  said no pin exists — but the package is not a dependency in
  pyproject/uv.lock and `huginn`/`muninn` have no pins anywhere).
  **Verdict: NO-GO for every Bifröst write path**, on
  three independent grounds: (1) `decay()`/`consolidate()` delegate
  entirely to an external `muninn` package and Huginn
  ingestion/search to an external `huginn` package, but both are
  bare unpinned extras whose PyPI names are unrelated projects, no
  public repo exists under those names, and no copy is in this
  tree — mutation semantics NOT PROVEN, and installing the extras
  by name would pull wrong software (name-collision defect recorded
  in the audit); (2) bridge reads write — `recall()` always logs a
  Muninn activation, `search()` reinforces when enabled, every
  method (health included) lazily constructs both write backends,
  and the bridge's Mímir open is read-write + WAL pragma; (3) the
  auto flags are dead — `auto_consolidate`/`auto_decay`/
  `consolidation_threshold`/`decay_interval_hours` are declared
  and never read; consolidation/decay run only via explicit calls.
  The entity consolidation checkpoint (Phase 7) is separate and
  does not discharge this item. Full audit appended to
  `PERSISTENT_ENTITY_ACCEPTANCE_AUDIT.md`; roadmap §29 Milestone 3
  gained the slice-86 paragraph. Verification: memory-fabric
  contracts 3/3 pass (docs-only slice; no code changed).
- **Next resume point: Slice 87 — Muninn read-only
  association-store probe**, specified implementation-ready at the
  end of `PERSISTENT_ENTITY_ACCEPTANCE_AUDIT.md` (`probe_bifrost_muninn`
  + `hermes volmarr memory muninn health`, read-only sqlite,
  `hebbian_connections`/`activation_log` schema + counts, no
  package import, no bridge construction, profile-isolated).
- **BLOCKER needing Volmarr's word (name once, plainly): the
  canonical `muninn` and `huginn` package sources.** The Bifröst
  write paths (Huginn ingestion, Muninn reinforcement, Bifröst
  consolidation/decay) cannot be specified or enabled until
  Volmarr supplies where those packages canonically live (repo or
  pin); Gate 0 reopens on them when supplied. After Slice 87 the
  write paths stay parked on this blocker and the campaign moves
  to roadmap queue item 2 (Emergent Agency, Phase 0). Banked
  locally only; pushes beyond the ordered refresh still await
  Volmarr's word.
- 2026-10-30 ~23:11 EDT keeper tick: **Slice 87 DONE, banked locally
  only, no push.** Implemented exactly per the Slice 86 spec:
  `probe_bifrost_muninn` in `plugins/volmarr-core/memory_fabric.py`
  (frozen `BifrostMuninnHealth`), exposed as `hermes volmarr memory
  muninn health [--json]` (label "Bifröst Muninn"). Read-only sqlite
  (`mode=ro`, 1 s timeout), both `hebbian_connections` and
  `activation_log` required, both row counts reported; imports
  neither `bifrost` nor `muninn`, constructs no bridge, works on a
  stock tree. One strengthening found by the slice's own symlink
  contract: path resolution hides symlinks, so the probe checks the
  lexical configured path before resolution and refuses a symlinked
  store as `storage_missing` (recorded in the audit; the check is
  local to this probe). Tests: targeted 11/11 pass (8 new Muninn
  contracts + 3 memory-fabric); full volmarr/kista run (40 files):
  **237 passed, 7 failed, 1 skipped** — the failures are the same
  name-identical pre-existing environmental set in the same 3 files;
  no new failures. Bookkeeping done: CUSTOMIZATIONS.md ledger row,
  roadmap §29 Milestone 3 slice-87 paragraph, Slice 87 outcome
  appended to `PERSISTENT_ENTITY_ACCEPTANCE_AUDIT.md`. **Milestone
  3's safe work is now complete.**
- **Next resume point: roadmap queue item 2 —
  VOLMARR_HERMES_EMERGENT_AGENCY_ROADMAP.md, Phase 0 (§7, Agency
  Contracts Before Intelligence)**, per the queue above. The Bifröst
  write paths stay parked on the Slice 86 blocker (canonical
  `muninn`/`huginn` sources) and Gate 0 reopens on them when
  Volmarr supplies them. Banked locally only; pushes beyond the
  ordered refresh still await Volmarr's word.

## Standing bounds for this campaign

- No Docker, ever. Never touch any `README.md`. Never force-push.
- Runtime divergence stays additive through the `volmarr-core` plugin
  (see `CUSTOMIZATIONS.md`); every intentional difference gets a ledger
  row. Hermes core must not import Volmarr-specific packages.
- Tests always via `scripts/run_tests.sh`; file-level verdicts come from
  real runs, and pre-existing failures are named, never absorbed.
- Pushes to origin only per Volmarr's word for that line of work.
- Current facts about Volmarr's other projects live in
  `HERMES_PROJECTS_UPDATE_2026-10-30.md` at repo root.

## BLOCKER RESOLUTION — muninn/huginn sources (main session, 2026-10-30 ~23:33 EDT, at Volmarr's word "look in the project records to find them")

- Bifröst canonical source: `hrabanazviking/bifrost` at `b66e98cc8a79d4dede22ba11d68a1a5ecd22ebd6` (v1.0.0, MIT) per `COMPONENT_LICENSES.md`; verified 2026-10-30 as that repo's live HEAD via `git ls-remote`.
- Bifröst's pyproject declares the extras bare (`huginn = ["huginn"]`, `muninn = ["muninn"]`); its `core.py` expects `huginn.HuginnMemory` (Qdrant) and `muninn.HebbianMemory` + `muninn.config.MuninnConfig` (Hebbian).
- Workspace-wide content sweep (2026-10-30) for `HebbianMemory|HuginnMemory|MuninnConfig`: NO standalone `huginn`/`muninn` packages exist in any of Volmarr's trees — the names occur only in Bifröst's own code (GitHub repo + the Ember monorepo's `bifrost/` copy), Verdandi's `eir/core.py` references, docs, and this campaign's audit.
- The ravens' canonical ancestors ARE in the records: NorseSagaEngine `yggdrasil/ravens/huginn.py` (`class Huginn`) and `yggdrasil/ravens/muninn.py` (`class Muninn`), with interface/test docs, ingested at `~/workspace/your_files/repos-ingest/NorseSagaEngine/` (a second copy in the Viking-Code-Mythic-Engineering ingest). Different class names — ancestors, not drop-ins.
- Consequence for the Slice 86 Gate 0: the write paths stay NO-GO until either (a) Volmarr points to copies elsewhere, or (b) the campaign builds the two thin packages to Bifröst's expected interface from his own ravens code. Slice 87 (read-only Muninn association-store probe) is unaffected and proceeds.

## Roadmap progress (continued)

- 2026-10-30 ~23:5x EDT keeper tick: **Slice 88 DONE — Emergent
  Agency Phase 0 (Agency Contracts Before Intelligence) complete,
  banked locally only, no push.** `plugins/volmarr-core/agency_contracts.py`:
  all eight roadmap contracts as frozen dataclasses over the shared
  `Provenance` model (12 source types), canonical-UUID owner on every
  record, bounded text, unit-interval scores, risk classes 0–5,
  timezone-aware timestamps, strict round-trip parsing that rejects
  unknown fields (a reflection record therefore has no field that
  could carry raw chain-of-thought). Contracts only — no stores, no
  behavior. The slice's owner test caught a real validator bug
  (uppercase UUIDs accepted as canonical) — fixed in scope, exact
  canonical form now required. Tests: targeted 7/7 pass; full
  volmarr/kista run (41 files): **244 passed, 7 failed, 1 skipped** —
  the same name-identical pre-existing environmental set; no new
  failures. Bookkeeping: CUSTOMIZATIONS.md ledger row, Phase 0
  completion note in the Emergent Agency roadmap §7.
- **Next resume point: Slice 89 — Emergent Agency Phase 1 (§8,
  Persistent Self-Model)**: `plugins/volmarr-core/self_model.py` +
  `entity/self_model.yaml` store on the Slice 88 `SelfClaim`
  contract (create-once, owner/symlink/size validation in the
  established GoalStore pattern, deterministic evidence merge —
  the LLM may propose, the merge layer decides — bounded packet
  contribution, contract tests incl. A→B→A isolation and no
  identity rewrite). The Bifröst write paths stay parked until the
  main session's commissioned ravens build (`~/workspace/ravens/`)
  reports done + verified, per Volmarr's ruling above. Banked
  locally only; pushes beyond the ordered refresh still await
  Volmarr's word.
- **VOLMARR'S RULING (2026-10-30 ~23:37 EDT, main chat): option (b), in his words: "Look at the ancestors and the glossary and what they are supposed to be, and build them true, as robust, self healing, error correcting, threaded, crash-proof, very efficient modules that can be useful in all my projects for their functions."** A dedicated build is commissioned in the main session (tree `~/workspace/ravens/`: two standalone packages, `muninn` + `huginn`, Bifröst-interface-compatible, grown from the NorseSagaEngine ravens + the Bifröst contract). When that build reports done + verified, this blocker clears and Gate 0 for the Bifröst write paths can be re-audited against the real packages.
- **RAVENS BUILD COMPLETE + VERIFIED (2026-10-30 ~23:59 EDT):** `~/workspace/ravens/` holds muninn 1.0.0 (36/36 tests) + huginn 1.0.0 (27/27), Bifröst-contract-exact; Bifröst's own suites pass 25/25 against the real packages and the end-to-end `BifrostBridge` verification passed (store/search/recall/decay/consolidate; Huginn honestly "degraded" to its local backend when qdrant-client is absent). NOT PROVEN: live Qdrant server round-trip, sentence-transformers embedder path. Detail: `~/workspace/ravens/BUILD_NOTES.md`. The Hermes integration slice (installing/binding the ravens + Gate 0 re-audit of the write paths) awaits Volmarr's word — it has NOT been started.
- 2026-10-31 ~00:0x EDT keeper tick: **Slice 89 DONE — Emergent
  Agency Phase 1 (§8, Persistent Self-Model) complete, banked locally
  only, no push.** `plugins/volmarr-core/self_model.py`:
  versioned `entity/self_model.yaml` store on the Slice 88
  `SelfClaim` contract (six domains; create-once; owner/symlink/size
  validation in the GoalStore pattern; identity read for ownership
  only, never written), plus a bounded `packet_items` producer wired
  into the PresentState packet sources (quotas: 3 capability,
  2 limitation, 2 commitment, 2 uncertainty, CURRENT STATE section).
  The deterministic merge layer decides all confidence changes:
  new-claim caps by provenance strength (strong 0.95 / medium 0.65 /
  weak 0.35 — weak evidence cannot create high-confidence beliefs),
  confirming deltas +0.15/+0.08/+0.03, contradiction deltas
  −0.20/−0.10/−0.04 with the conflicting statement recorded, and only
  strong evidence may restate a claim. Config keys
  `self_model_enabled`/`self_model_path`/`self_model_evidence_limit`
  added to `plugin.yaml`. Tests: targeted 8/8 pass; full
  volmarr/kista run (42 files): **251 passed, 7 failed, 1 skipped**
  — the failures verified as the same name-identical pre-existing
  environmental set by rerunning their 3 files (5 core-plugin, 1
  Verðandi-stimuli, 1 voice-runner). Bookkeeping: CUSTOMIZATIONS.md
  ledger row, Phase 1 completion note in the Emergent Agency
  roadmap §8. Honest gaps: Verðandi self-model events (§8 metadata
  types) are NOT yet emitted — deferred to a later telemetry slice,
  recorded in both bookkeeping spots.
- **Next resume point: Slice 90 — Emergent Agency Phase 2 (§9,
  Intrinsic Motivation)**: drive store on the Slice 88 `DriveState`
  contract (per the §9 spec when read at slice start). The Bifröst
  write-path integration stays parked — per the ravens entry above
  it awaits Volmarr's word and has NOT been started. Banked locally
  only; pushes beyond the ordered refresh still await Volmarr's
  word.
