# X.12 Draupnir Forge — ecosystem workstream 12 of 15 (Team 01, 2026-11-14)

Roadmap section 47 executed: an opt-in, default-off, local-only
bounded delegated-workflow connector over the Hermes plugin
boundary, following the X.10/X.11 pattern. Slice discipline: a
new `draupnir` module + `hermes volmarr draupnir
{status|catalog|plan}` CLI family in volmarr-core, two
default-off `draupnir_*` config keys, one capability-bus seed
descriptor, exactly one CUSTOMIZATIONS.md ledger row, README.md
byte-identical (sha256
336813d11bbe5aa2ff745b4a4bc3abcf2a283cd13971c0c11d061377129db7f3,
verified before and after). NO integration-lock.json,
INTEGRATION_MATRIX.md or COMPONENT_LICENSES.md change: none
holds a Draupnir row (the pin 74cff6fb958f lives only in
docs/modernization/BASELINE_2026-11-07.md), and none was
invented (recorded honestly per the section 35 duty).
Commit-only on `yrsa/hermes-team-01`; the keeper banks serially.

## Audit (from source, not README)

- Source: `hrabanazviking/RuneForgeAI-Draupnir-Forge`, cloned
  fresh under $HOME at `~/draupnir-x12`; HEAD measured
  `74cff6fb958fe2470ba3e13125db871aea64933a` (identical to the
  `git ls-remote` HEAD at audit time and to the baseline pin).
- README vs source (section 47 item 1): the README badges the
  project "concept / future project" and calls it "a proposed
  ... system" — the roadmap's observed description matches the
  README. The SOURCE contradicts a design-only reading: the
  tree carries real executable code, verified by structure and
  an import smoke (`draupnir_forge` 0.1.0, `Orchestrator` and
  `Checkpointer` import cleanly), not by trusting the README
  in either direction.
- Executable surface at the audited HEAD: package
  `draupnir-forge` 0.1.0 (`pyproject.toml`, sole dependency
  pyyaml, console script `draupnir = draupnir_forge.cli:main`);
  `src/draupnir_forge` holds 47 Python modules (~15.9k lines):
  an `Orchestrator` class, the `ForgeTask` dataclass (canonical
  in `roles/planner.py`, re-exported by `tasks.py`), a
  `TaskGraph` in `roadmap.py` (cycle detection, critical path),
  role modules for all ten section 47 roles (watchman is the
  `heimdallr` role module), a git-backed `Checkpointer`
  (checkpoint / rollback / pause / resume), a
  `VerificationEngine` with timed gates, a default-deny
  `security` model, and budget / repair / reground / drift /
  escalation / sessions-replay subsystems. Recovery mechanisms
  therefore EXIST upstream (checkpointer + repair + reground).
  49 test files under `tests/`; 97 Python files in the tree.
- License text-verified at the audited HEAD: `LICENSE` is the
  full GNU AGPL v3 text (661 lines), sha256
  `8486a10c4393cee1c25392769ddd3b2d6c242d6ec7928e1414efff7dfb2f07ef`;
  pyproject declares AGPL-3.0-or-later. No Draupnir source is
  copied or vendored by this slice.
- Named gap: NO lease or one-writer mechanism exists in the
  audited source (no lease concept anywhere in `src/`). The
  section 47 item 5 one-writer invariant is enforced by THIS
  connector's planner and lease store, not claimed for the
  Forge itself (ticket X12-T2).

## Build (section 47 items 1-10)

`plugins/volmarr-core/draupnir.py` (new, original code):

- Status/catalog (items 1-2): `draupnir_status` reports
  unconfigured vs configured truthfully; when configured it
  measures the REAL staged tree's structure only — .git HEAD
  vs the audited HEAD, the package version in its pyproject,
  the LICENSE sha256, and Python module / src-module /
  test-file counts by filename. `role_catalog` maps the ten
  section 47 roles (skald, cartographer, architect, planner,
  forge worker, auditor, tester, verifier, scribe, watchman)
  to BOUNDED delegated jobs with their audited basis — never
  autonomous root agents; only the forge worker job may mutate
  a checkout, and only its own leased one.
- Workflow plans (items 3-4): `build_workflow_plan` is a pure
  deterministic plan over the seven stages (approved intent →
  architecture/invariants → worktree assignment →
  implementation → tests → independent verification →
  documented result). Jobs carry deterministic durable task
  IDs (same intent+role+title+path, same ID), per-stage
  idempotent step IDs, dependencies (unknown or cyclic
  dependencies refused by name), retry budgets (0-5, invalid
  refused), artifact hashes, checkpoint IDs and cancellation.
  No plan exists without approved intent
  (`intent_not_approved`).
- One-writer invariant (item 5): a second job on a checkout
  already leased in the plan is refused by name
  (`duplicate_lease_refused`, naming the lease owner); the
  durable lease store (`acquire_lease` / `lease_status` /
  `release_lease`) enforces the same rule across runs, and a
  stale heartbeat reports `worker_lost` with checkpoint
  recovery. `integrate_plan` refuses merge-conflicted
  checkouts by name, fail-closed.
- Authorization gates (item 6): repository push, release,
  package publication, shell escalation and remote changes
  are refused by name (`operator_authorization_required`,
  fail-closed) without explicit operator authorization; a
  denied publish therefore fails closed.
- Malicious handoff (test gates): a delegated task carrying
  instruction-bearing fields (instructions / override /
  system_prompt / shell / command / eval / exec) or arriving
  from an unlisted delegate is refused by name
  (`malicious_handoff_refused`) — bounded jobs take tasks,
  not instructions.
- Verifier (item 8): `verify_result` is source-linked and
  fails closed — unproven test output or exit status
  (`unproven_test_output`), a failed build (`failed_build`)
  or nonzero tests (`nonzero_tests`) are each refused by
  name; only a proven zero exit with a source link verifies.
- Checkpoint resume (item 9): `write_checkpoint` /
  `cancel_job` / `resume_plan` persist completed and
  cancelled task IDs durably; resume returns exactly the
  remaining jobs by their idempotent step IDs, so completed
  side effects are never duplicated.
- Recursive subtasks (item 10): subtasks flatten with depth
  stamps; depth beyond 3 is refused
  (`recursion_depth_exceeded`) and a plan over its task
  budget is refused (`task_budget_exceeded`). Document limits
  are not imposed — only task count / depth / retry safety
  controls are kept.
- Wiring: capability-bus seed descriptor `volmarr-draupnir`
  0.1.0 (in-process transport, local-private only, adapter at
  the volmarr-core plugin.yaml; the two `service_count == 5`
  assertions in `test_volmarr_capability_bus.py` move to 6
  with a version assertion added — the X.10/X.11-style
  genuine-change update); CLI family `hermes volmarr draupnir
  {status|catalog|plan}` mirroring the aurelia verbs (plan
  runs the labelled SYNTHETIC_TASKS set: 2 planned, 1
  duplicate-lease refusal, 1 denied-publish refusal, 1
  malicious-handoff refusal); `draupnir_enabled` /
  `draupnir_root` config keys, both default-off/empty.

## Live caller (section 28.2)

`hermes volmarr draupnir {status|catalog|plan}` proven in
disposable HERMES_HOME homes on disk (log
`~/team01-x12-liveproof.log`; homes under $HOME after a first
attempt in /tmp hit the tmpfs size limit during runtime
install — an environment fact, not a connector defect),
using the team-01 checkout's own `hermes` binary via
`scripts/run-in-hermes-env`:

- Unconfigured home: status truthful (`enabled: false`,
  `configured: false`, tree `not_configured`,
  `production_ready: false`); catalog lists the ten bounded
  roles and the five authorization gates; plan plans the
  labelled synthetic set (2 planned, 1
  `duplicate_lease_refused`, 1
  `operator_authorization_required`, 1
  `malicious_handoff_refused`); bare verb rc 2. All other
  verbs rc 0.
- Configured home (`draupnir_enabled: true`,
  `draupnir_root: ~/draupnir-x12` under
  `plugins.entries.volmarr-core.settings`): status measures
  the REAL staged tree — `head_matches_audited: true` at
  74cff6fb958f, `package_version: 0.1.0` read from the tree's
  own pyproject, `license_matches_audited: true` (sha256
  8486a10c4393...), `module_count: 97` Python files,
  `src_module_count: 47`, `test_file_count: 49`.

## Tests and gate

- New contracts: `tests/plugins/test_volmarr_draupnir_x12.py`
  (12 tests) pinning the section 47 gates — unconfigured
  truthfulness, configured structural measurement, the
  bounded role catalog, approved-intent + deterministic plan
  shape, duplicate lease in plan and lease store, lost-worker
  detection, all five authorization gates refused by name
  (and allowed only with explicit authorization), malicious
  handoff / unknown role / unknown + cyclic dependency /
  invalid retry refusals, fail-closed verification (failed
  build, nonzero tests, unproven output) + merge-conflict
  refusal, exact checkpoint resume with cancellation, and
  budgeted depth-limited recursion, plus the CLI family.
- Targeted (log `~/team01-x12-targeted.log`): 4 files
  (draupnir_x12 + capability_bus + aurelia_x11 +
  scribing_x10) = **45 passed / 0 failed** (12 new X.12
  contracts; capability_bus carries the seed-count update).
- Full contract gate (log `~/team01-x12-fullcontracts.log`),
  run serialized on an idle laptop: in the canonical scope
  (test_volmarr_*.py + the two kista files): **149 files =
  1,304 passed / 7 failed / 1 skipped** — the X.11 baseline
  (148 files = 1,292 / 7 / 1) plus exactly the 12 new X.12
  contracts, the 7 failures name-identical to the known
  live-transport set (5x test_volmarr_core_plugin.py, 1x
  test_volmarr_verdandi_stimuli.py, 1x
  test_volmarr_voice_runner.py), ZERO regressions.

## Honest remainders / tickets

- X12-T1 (live transport): the connector plans and records
  locally; it binds NO live transport and runs NO Forge code.
  Executing a Hermes plan through a real Draupnir
  Orchestrator run is future work.
- X12-T2 (upstream lease gap): the audited Forge has no lease
  or one-writer mechanism; the invariant is enforced
  connector-side only. If the Forge grows native leases, a
  future audited update should reconcile the two.
- X12-T3 (registry): no integration-lock, INTEGRATION_MATRIX
  or COMPONENT_LICENSES row exists for Draupnir; none was
  invented. The only pin on record is BASELINE_2026-11-07.md's
  74cff6fb958f, which the audited HEAD still matches.
- X12-T4 (engine suite): the Draupnir tree's own 49-file test
  suite was not run by this slice — the audit was structural
  plus an import smoke of the package, Orchestrator and
  Checkpointer. A suite run is the natural next maturity
  proof (see X12-T5).
- X12-T5 (maturity + cross-tool help): the README's
  concept-stage self-description and the source's real code
  disagree; this slice treats the source as truth for
  structure only and claims no production maturity.
  Section 47 item 7's targeted help from Mythic Agent CLI,
  Samverk/GitHub, MindSpark and HugrGate is likewise not
  wired — the planner records bounded jobs only, with no
  cross-tool model/provider state entangled.
- The section 32 release scorecard still reads NOT
  releasable (0 met / 10 unmet / 5 deferred);
  `production_ready` stays False in every X.12 record.
