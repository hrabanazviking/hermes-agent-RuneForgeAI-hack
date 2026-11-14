# X.14 Mythic Agent Coder CLI — ecosystem workstream 14 of 15 (Team 01, 2026-11-14)

Roadmap section 49 executed: an opt-in, default-off, local-only
Mythic Engineering workflow connector over the Hermes plugin
boundary, following the X.10/X.11/X.12/X.13 pattern. Slice
discipline: a new `mythic_coder` module + `hermes volmarr
mythic {status|catalog|plan}` CLI family in volmarr-core, two
default-off `mythic_*` config keys, one capability-bus seed
descriptor, exactly one CUSTOMIZATIONS.md ledger row,
README.md byte-identical (sha256
336813d11bbe5aa2ff745b4a4bc3abcf2a283cd13971c0c11d061377129db7f3,
verified before and after). NO integration-lock.json or
INTEGRATION_MATRIX.md change: neither holds a Mythic Agent
Coder CLI row, and none was invented (recorded honestly per
the section 35 duty). Commit-only on `yrsa/hermes-team-01`;
the keeper banks serially.

## Audit (from source, not README)

- Source: `hrabanazviking/Mythic_Agent_Coder_CLI`, cloned
  fresh under $HOME at `~/mythic-x14` from the default
  `development` branch; HEAD measured
  `e991a526c412c3668016809be66dbf50148128c3` (identical to the
  `git ls-remote` HEAD for `development` at audit time; `main`
  sits separately at bc39d080df5e and was NOT audited).
- Version: package `mythic-agent` **0.1.0** (`pyproject.toml`,
  hatchling dynamic version from `mythic_agent/__version__.py`;
  console scripts `mythic` and `mythic-mcp`). Hard deps:
  openai / prompt_toolkit / rich / filelock / pyyaml / httpx +
  httpx2; optional extras for anthropic / google / the Textual
  TUI / MCP / tree-sitter code intelligence / knowledge /
  voice / voice-cloning. The roadmap's Observed note (default
  `development` branch, engineering status dated November 6
  in the README) matches the tree; the README's own 6 November
  audit count of 171 test modules in `tests/` is stale.
- Structure at the audited HEAD: 386 Python modules under
  `mythic_agent/`, 777 Python files in the tree, 358 test
  files under `tests/` (pytest, testpaths=[tests], per-test
  timeout in pyproject). An import smoke of the staged tree
  passes with the system interpreter for the package,
  `__version__` (0.1.0 read back) and
  `mythic_agent.workflow.slice_runner` (a SliceDefinition
  constructs); deeper provider imports need the declared
  distribution dependencies (httpx is not installed
  system-wide) — structural proof only, not a suite run
  (X14-T1).
- Method (item 1): `Mythic-Engineering/Mythic-Engineering_SKILL.md`
  defines the architecture-first workflow — six roles (Skald,
  Architect, Forge Worker, Auditor, Cartographer, Scribe), a
  five-layer operating model (Vision / Domain / Interface /
  Execution / Verification) and an eight-phase workflow — and
  it is executable as data in
  `mythic_agent/workflow/slice_runner.py`: `SliceDefinition`
  (name, description, work_order_path, acceptance_gates) whose
  gates run sequentially with a durable checkpoint per gate
  (`<MYTHIC_DIR>/slices/<name>.json`), resumable after
  interruption. `mythic_agent/core/acceptance_gates.py` pins
  the acceptance honesty mirrored below: held evidence
  (runner_output, compile_log, ledger_row, neighbour_log) is
  evidence; bare claims (feeling, memory, assertion, summary)
  are not; a slice banks only green.
- CLI/TUI (item 1): `mythic_agent/cli.py` offers run / chat /
  tui (each `--permission` in read-only / ask / trusted,
  mirroring `core/policy.py`, whose machine default is
  read-only), sessions, theme, tutorial, review (static,
  source-linked), doctor, cache, costs, metrics, testkit;
  the TUI is the optional Textual extra under `ui/`.
- Provider registry (items 1, 3):
  `mythic_agent/providers/registry.py` holds 16 provider
  classes behind `get_provider` with friendly aliases.
  Credentials resolve from each provider's environment
  variable or through Kista references (`kista:<name>`,
  `mythic_agent/core/key_custody.py` — config files hold
  references, never secrets; a legacy plaintext `api_keys`
  road still exists upstream and is named as such).
- Subagent support (item 1) is REAL: `AgentManager`
  (`mythic_agent/agents/llm.py`) spawns the six named role
  subagents via the `delegate_task` tool;
  `mythic_agent/agents/parallel.py` is a dependency-aware
  parallel TOOL-call executor — parallel tool calls, not
  parallel writers.
- Checkout lease (item 5) — GAP: no lease or runtime
  one-writer mechanism exists in the audited source. The law
  exists as validated plan DATA in
  `mythic_agent/core/worktrees.py` ("never two writers in one
  tree": a plan refuses a duplicated worktree path, a
  duplicated branch, and a member holding two assignments;
  the module runs no git command and enforces nothing at
  runtime). The lease enforced by this connector is its own
  surface, shaped after the X.12 Draupnir lease.
- GitHub integration (item 6) — GAP: `mythic_agent/integrations/github.py`
  provides create_pr / add_pr_comment / list_issues /
  view_issue / get_actions_status over the user's own `gh`
  binary (auth stays with gh; no credentials pass through
  Mythic), but its `register_cli` is called NOWHERE in the
  audited tree — no `mythic gh` verb ships at the audited
  HEAD. The Samverk bridge
  (`mythic_agent/core/samverk_bridge.py`) is a data-only
  exchange book: no socket to the forge, nothing filed live.
- Platforms (item 8): `mythic_agent/core/platform_truth.py`
  is an honest truth table — Linux / Windows / macOS x
  install / run / TUI / voice, PROVEN only on local-measured
  evidence, voice NOT PROVEN everywhere, hosted CI
  manual-dispatch only and not green at the README's audit.
  NO ARM64 cell and no Termux path exists in the audited
  source; the POSIX-only `fcntl` import that failed Windows
  collection is still in the reviewed source. ARM64
  evaluation is therefore recorded unproven upstream, never
  assumed equivalent.
- License text-verified at the audited HEAD: `LICENSE` is
  the full Apache License 2.0 text (201 lines), sha256
  `c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4`;
  pyproject declares Apache-2.0. No Mythic source is copied
  or vendored by this slice.

## Build (section 49 items 1-10)

`plugins/volmarr-core/mythic_coder.py` (new, original code):

- Status/catalog (items 1-2): `mythic_status` reports
  unconfigured vs configured truthfully; when configured it
  measures the REAL staged tree's structure only — .git HEAD
  vs the audited HEAD, the package name in its pyproject, the
  version in `mythic_agent/__version__.py`, the LICENSE
  sha256, and Python module / package-module / test-file
  counts by filename. `workflow_catalog` carries the section
  49 catalog: the versioned workflow schema
  `runeforge.mythic.workflow.v1` (six roles with forge_worker
  the ONLY writing role; five stages orient / architect /
  forge / audit / bank; executable form = slice definitions
  with sequential acceptance gates and per-gate checkpoints,
  which Hermes can call through this schema and Mythic CLI
  can independently execute), the read-only operations, the
  per-operation permission gates, the refused operations,
  the provider-registry facts (16 providers, credentials in
  environment/Kista references, never read here), and the
  audited GitHub / Samverk / subagent / lease / platform
  findings above, each with its basis.
- Read-only planning (items 2, 4, 7): `plan_research` shapes
  bounded requests for repo_research, architecture_mapping,
  roadmap_construction, test_discovery, diff_proposal and
  source_linked_review into staged, read-only plans with a
  deterministic plan key. A private repository is denied by
  name (`private_repo_denied`) without operator
  authorization. The subagent context is an approved subset
  only (persona_role, project_facts, coding_conventions,
  roadmap_excerpt, slice_definition): any private key
  (companion_data, author_data, private_memory, credentials)
  refuses the whole request by name (`private_context_refused`),
  and any other unapproved key is refused by name. Write
  stages cannot enter a read-only plan.
- Checkout lease (item 5): `acquire_lease` / `lease_status` /
  `release_lease` enforce ONE write owner per checkout on
  disk — a second owner is refused by name
  (`duplicate_lease_refused`, holder named), the holder may
  refresh its heartbeat, a stale heartbeat reads
  `worker_lost` with `recoverable_via_checkpoint`, and only
  the owner may release. Parallel architects/auditors need
  no lease: they work read-only on immutable copies.
- Permission gates (items 3, 5-6): `gate_operation` decides
  per operation — checkout_write and commit require a lease;
  push and create_pr additionally require operator
  authorization; release and publication require operator
  authorization; secrets_access, credential_read,
  private_companion_data_access and
  private_author_data_access are refused by name in EVERY
  case. A passed gate is a shaped authorization record only:
  `executed` is False everywhere — this connector performs
  no push, no PR, no release, and reads no credential.
  Branch strategies (team_branch / feature_branch /
  slice_branch) and PR receipts ride the recovery record.
- Failed-push recovery (item 6, test gate):
  `recovery_record` validates the recovery log shape — push
  operation, named failure, known branch strategy, known
  recovery action (retry_after_fetch / rebase_then_retry /
  abort_and_report), explicit resolved flag — and receipts
  it with a record key; anything malformed fails closed by
  name. It performs no push and no recovery.
- Independent patch verification (item 10, test gate):
  `verify_patch` re-parses a supplied unified diff itself
  (malformed diffs fail by name) and verifies it ONLY on
  held evidence (runner_output / compile_log / ledger_row /
  neighbour_log — the engine's own acceptance vocabulary);
  bare claims leave it `unverified_claim`, and unknown
  evidence kinds fail closed. `parse_build_output` parses
  compiler-style build output strictly — one malformed line
  makes the whole record `malformed_build_output`.
- Outcome metrics (item 10): `outcome_metrics` computes,
  under `runeforge.mythic.outcomes.v1`, ONLY from the job
  records supplied: patch test pass rate, review resolution
  rate, clean diff rate, recovered sessions, and true
  acceptance kept strictly apart from claimed done — a
  record is truly accepted only when independently verified
  AND all its patch tests pass; claimed-done records failing
  that bar are counted as `inflated_done`. Empty input
  computes nothing and says so; malformed records fail
  closed by name; synthetic fixtures are labelled.
- Draupnir coordination (item 9): X.12 is banked with its
  own plan + lease machinery and durable plan keys, so the
  precondition exists at the record level. This connector
  coordinates at that level only — a Draupnir plan key may
  be cited as job lineage — and binds NO cross-engine
  execution; durable cross-engine job lineage does not
  exist yet (X14-T4).
- Wiring: capability-bus seed descriptor `volmarr-mythic`
  0.1.0 (in-process transport, local-private only, adapter
  at the volmarr-core plugin.yaml; the two `service_count ==
  7` assertions in `test_volmarr_capability_bus.py` move to
  8 with a version assertion added — the X.10–X.13-style
  genuine-change update); CLI family `hermes volmarr mythic
  {status|catalog|plan}` mirroring the sibling verbs (plan
  runs one labelled SYNTHETIC architecture-mapping request);
  `mythic_enabled` / `mythic_root` config keys, both
  default-off/empty.

## Live caller (section 28.2)

`hermes volmarr mythic {status|catalog|plan}` proven in
disposable HERMES_HOME homes on disk (log
`~/team01-x14-liveproof.log`), using the team-01 checkout's
own `hermes` binary via `scripts/run-in-hermes-env`:

- Unconfigured home: status truthful (`enabled: false`,
  `configured: false`, tree `not_configured`,
  `production_ready: false`); catalog carries the workflow
  schema with forge_worker the only writing role and the
  GitHub module recorded as not wired into the CLI; plan
  returns the labelled synthetic read-only plan
  (`architecture_mapping`, 2 steps, `executes_operations:
  false`); bare verb rc 2. All other verbs rc 0.
- Configured home (`mythic_enabled: true`, `mythic_root:
  ~/mythic-x14` under `plugins.entries.volmarr-core.settings`):
  status measures the REAL staged tree —
  `head_matches_audited: true` at e991a526c412,
  `package_name: mythic-agent`, `package_version: 0.1.0`
  read from the tree's own `__version__.py`,
  `license_matches_audited: true` (sha256 c71d239df917...),
  `module_count: 777` Python files, `package_module_count:
  386`, `test_file_count: 358`.

## Tests and gate

- New contracts: `tests/plugins/test_volmarr_mythic_x14.py`
  (14 tests) pinning the section 49 test gates —
  one-leased-writer invariant (duplicate lease refused by
  name, holder refresh, stale heartbeat = worker_lost,
  owner-only release), failed push recovery (valid log shape
  receipted; wrong operation / unknown action / unknown
  strategy / missing outcome refused by name), private repo
  denial (denied unauthorized, planned when authorized),
  malformed build output (one garbage line fails the whole
  record closed), profile isolation (private context keys
  refused by name; unapproved keys refused), independent
  verification of generated patches (held evidence verifies;
  bare claims do not; malformed diffs fail by name), the
  permission gates, the workflow catalog's honest findings,
  outcome metrics that never inflate done, bounded input +
  performance budget, offline/no-egress on every surface,
  and the CLI family.
- Targeted (log `~/team01-x14-targeted.log`): 4 files
  (mythic_x14 + capability_bus + hugrgate_x13 + draupnir_x12)
  = **56 passed / 0 failed** (14 new X.14 contracts;
  capability_bus carries the seed-count update).
- Full contract gate (log `~/team01-x14-fullcontracts.log`),
  run serialized on an idle laptop: in the canonical scope
  (test_volmarr_*.py + the two kista files): **151 files =
  1,332 passed / 7 failed / 1 skipped** — the X.13 baseline
  (150 files = 1,318 / 7 / 1) plus exactly the 14 new X.14
  contracts, the 7 failures name-identical to the known
  live-transport set (5x test_volmarr_core_plugin.py, 1x
  test_volmarr_verdandi_stimuli.py, 1x
  test_volmarr_voice_runner.py), ZERO regressions.

## Honest remainders / tickets

- X14-T1 (engine suite): the connector binds NO live
  transport and runs NO Mythic code. The Mythic tree's own
  358-file test suite was not run by this slice — the audit
  was structural plus import smokes of the package,
  `__version__` and the slice runner (deeper imports need
  the declared dependencies installed). A suite run in a
  staged environment is the natural next maturity proof.
- X14-T2 (GitHub wiring): the audited GitHub module is not
  wired into the Mythic CLI (`register_cli` called nowhere).
  Until an audited upstream update wires it, no `mythic gh`
  verb exists and this connector's GitHub surface stays
  gate-records only — no PR is created, no push performed.
- X14-T3 (lease enforcement point): the lease here is the
  connector's own record surface, shaped after X.12. Mythic
  itself still holds the one-writer law as plan data only
  (core/worktrees.py runs no git); nothing in either tree
  yet makes a real checkout refuse a second writer at write
  time.
- X14-T4 (Draupnir lineage): coordination with Draupnir is
  record-level only (plan keys citable as lineage). Durable
  cross-engine job lineage — one job ID followed across
  Draupnir plans and Mythic slices — does not exist yet.
- X14-T5 (platforms): ARM64 evaluation is unproven upstream
  (no ARM64 cell in platform_truth) and no Termux path
  exists; this connector names only the native
  Ubuntu/Kubuntu road and records the rest honestly. A
  local-measured ARM64 proof (e.g. on Mimir) belongs to a
  future audited run, not to this slice's claims.
- X14-T6 (registry): no integration-lock or
  INTEGRATION_MATRIX row exists for Mythic Agent Coder CLI;
  none was invented. The audited HEAD e991a526c412 is
  recorded only in this workstream record and the connector.
- The section 32 release scorecard still reads NOT
  releasable (0 met / 10 unmet / 5 deferred);
  `production_ready` stays False in every X.14 record.
