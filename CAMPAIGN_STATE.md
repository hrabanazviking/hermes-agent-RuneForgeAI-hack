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
