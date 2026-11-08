# Hermes Modernization - Wave Plan (9 teams x 6 roles)

Campaign: ROADMAP_HERMES_MODERNIZATION_UNBOUNDED_PERSONA_2026-11-07.md
State: CAMPAIGN_STATE_MODERNIZATION.md - Baseline: docs/modernization/
Host: purplelongship only. Canonical tree: ~/hermes-hack-forge (main).

## Muster law (learned 2026-11-06, do not relearn the hard way)

- 9 teams x 6 roles = 54 seats; coordinator is seat 54, 53 workers.
- NEVER spawn all teams at once (platform throttled a 60-agent spawn).
  Probe first (done: Phase 0 recon by coordinator), then muster 2-3
  teams at a time, staggered. The 10-minute keeper restarts stopped
  teams and advances banking in wave order.
- Each team works in its OWN worktree on its OWN branch; never share a
  checkout between writers. Banking is serialized by the coordinator/
  keeper in wave order: slice commit -> merge -> closure commit ->
  push -> git ls-remote verification (foreground git only).
- One heavy test suite at a time on the laptop (shared with Samverk,
  Mythic Coder, Runmal campaigns). Check load/free before heavy runs.
- Roles in every team: Scout (recon, source truth), Designer (slice
  design against roadmap + invariants), Builder-1, Builder-2,
  Builder-3 (implementation, split by file ownership), Tester
  (scripts/run_tests.sh batteries, evidence, counts from logs only).

## Team assignments - first wave (in roadmap order)

- Team 01 - Unit 1 - W00 / Phase U0 freeze completion
  Worktree ~/hermes-team-01, branch team-01/w00-u0-freeze
  Tickets W00.01-W00.07: re-pin fork/upstream SHAs at freeze moment,
  encrypted verified backup of ~/.hermes + persona corpus with restore
  drill, full service/plugin/version matrix (incl. laptop launch
  recipe, profiles), baseline suite run + reproduce the 7 named
  environment failures, fixture archive, repo-boundary review, offline
  install recipe, verify integration-lock.json rows, COMPAT_MANIFEST
  fate, ravens-tree blocker resolution path.
  Gate: reproducible baseline + rollback proven (roadmap W00 gate).
- Team 02 - Unit 2 - W01 / Phase U1 guarded upstream intake
  Worktree ~/hermes-team-02, branch integration/upstream-2026-11-07
  (the ONLY writer on the integration branch)
  Tickets W01.01-W01.09: pin v0.23.0 commit 2bd378ed1b (+ review newer
  main, do not chase it), named upstream remote per UPSTREAM_SYNC.md,
  sync_upstream.py guarded no-commit merge, README byte-proof against
  the NEW baseline sha 83a8c2b4..., upstream-changes.md, section 4.2
  compatibility work (single gateway session owner, bot/group routing,
  rewind/fork, plugin lifecycle, paid-tool gates), full Volmarr/Kista
  contracts + targeted upstream suites + native smoke, merge notes.
  Gate: selected upstream suite + Volmarr contracts pass.
- Team 03 - Unit 3 - W02 / Phase U2 dependency + deployment safety
  Worktree ~/hermes-team-03, branch team-03/w02-u2-deps
  pyyaml==6.0.3 reconciliation vs upstream YAML stack (x86_64 + ARM64
  wheels), Muninn/Huginn ravens lock problem (no PyPI fallback, ever;
  first-party publication route design), adapter compatibility matrix,
  SBOM/license/leak/audit tooling, native install + systemd + rollback
  recipes, cold-install reproduction in a throwaway profile.
  Gate: reproducible cold install (roadmap W02 gate).
- Team 04 - Unit 4 - W03 / Phases P0+P1 unbounded canon
  Worktree ~/hermes-team-04, branch team-04/w03-p0p1-canon
  Tickets P.001-P.005 (+ P.002/P.003/P.016 tests): end silent truncation
  for authored docs, canonical source library + manifest schema (NO
  max_chars anywhere), streaming byte-exact ingestion, SOUL.md + role
  docs migration dry-run, transactional manifest updates, Markdown AST
  + stable section identity. Corpus byte-identity is the invariant.
  Gate: 100 MB corpus byte-identical (roadmap W03 gate).
- Team 05 - Unit 5 - W04 / Phase P2 retrieval
  Worktree ~/hermes-team-05, branch team-05/w04-p2-retrieval
  Tickets P.006, P.007: incremental SQLite FTS5 section index with
  subspans + continuation handles, exact-citation mode, retrieval
  receipts, optional embeddings behind local/cloud consent gate only,
  paged full-fidelity read. Builds on persona_runtime.py - no second
  compiler (roadmap section 8 law).
  Gate: buried-section recall in 100 MB corpus, zero source loss.
- Team 06 - Unit 6 - W05 / Phases P3+P4 live persona (OLD-ROADMAP GAP)
  Worktree ~/hermes-team-06, branch team-06/w05-p3p4-live
  Tickets P.008-P.011, P.017: kernel + prompt assembler on the official
  gateway extension surface, ONE prompt owner, duplicate legacy SOUL
  injection removed on opt-in profiles only, per-turn immutable
  persona snapshot, atomic next-turn activation, delegates inherit
  fragments only. This unit carries the older Persona Runtime
  roadmaps' central unmet debt: sections banked as pure contracts
  with no live caller get real callers here, or an honest record of
  why not (roadmap sections 0, 9, 10 + section 28.2 regressions).
  Gate: real conversations across surfaces, A/B profile isolation.
- Team 07 - Unit 7 - W06 / Phase P5 large MEMORY.md / USER.md
  Worktree ~/hermes-team-07, branch team-07/w06-p5-memory
  Ticket P.014 (+ P.015 canon protection): unbounded backing corpus,
  verbatim import, derived digest honestly labelled, old memory-tool
  compatibility adapter, transactional audited writes, WAL/concurrency
  + crash recovery tests.
  Gate: 2 MB USER.md + 20 MB MEMORY.md complete, indexed, exact recall.
- Team 08 - Unit 8 - W07 / Phase P6 persona operations
  Worktree ~/hermes-team-08, branch team-08/w07-p6-controls
  Tickets P.012, P.013, P.018, P.020: the section 12 command table for
  real (status/files/search/inspect/explain/validate/diff/reload
  dry-run + activate/export/import/backup-restore/test) against a
  live temporary gateway profile - no stub dictionaries; huge-file
  editor/pager; drift watchdog as bounded diagnostics (never rewrites
  canon); private/public filters before any cloud inference.
  Gate: no stub command or invented result (roadmap W07 gate).
- Team 09 - Unit 9 - W08 opens / Phase E0 ledger + first engine audits
  Worktree ~/hermes-team-09, branch team-09/w08-e0-ledger
  Phase E0: promote docs/modernization/integration-lock.json (DRAFT
  from Phase 0) into docs/modernization/INTEGRATION_MATRIX.md +
  verified lock, one row per section 13 engine with adapter mode
  classified honestly (probe-only / read-only / tool / read-write /
  realtime / prototype / design-only). Then start the E.01-E.03
  audits (Verdandi, A.E.S.I.R., Bifrost/Mimir) under the section 13
  per-engine protocol: engine's own tests in its own tree FIRST,
  Hermes adapter second, one engine promoted at a time.
  Gate: installed real engine for every row later claimed green.

## After the first wave (same 9 teams, next units in order)

W08 continues E.04-E.18 + Phases E1-E5 - W09 N0/N1 (N.01-N.16 audits +
capability bus, 3 live heterogeneous tools) - W10 N2/N3 - W11 N4 -
W12 N5 - W13 Q0-Q4 + release scorecard (roadmap section 32).
Old-roadmap remainder rule: any Persistent Entity / Emergent Agency /
Self-Aware Agency item the E/P phases surface as contract-only or
preflight-only is finished inside the phase that owns it (chiefly
Team 06's live-wiring unit and Team 09's engine units), recorded in
CAMPAIGN_STATE_MODERNIZATION.md - never silently re-declared complete.
