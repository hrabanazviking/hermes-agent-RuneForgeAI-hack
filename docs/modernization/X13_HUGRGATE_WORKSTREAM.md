# X.13 HugrGate — ecosystem workstream 13 of 15 (Team 01, 2026-11-14)

Roadmap section 48 executed: an opt-in, default-off, local-only
structured-uncertainty connector over the Hermes plugin
boundary, following the X.10/X.11/X.12 pattern. Slice
discipline: a new `hugrgate` module + `hermes volmarr hugrgate
{status|catalog|evaluate}` CLI family in volmarr-core, two
default-off `hugrgate_*` config keys, one capability-bus seed
descriptor, exactly one CUSTOMIZATIONS.md ledger row, README.md
byte-identical (sha256
336813d11bbe5aa2ff745b4a4bc3abcf2a283cd13971c0c11d061377129db7f3,
verified before and after). NO integration-lock.json or
INTEGRATION_MATRIX.md change: neither holds a HugrGate row
(the X.06 record noted "no HugrGate code exists in this
tree"), and none was invented (recorded honestly per the
section 35 duty). Commit-only on `yrsa/hermes-team-01`; the
keeper banks serially.

## Audit (from source, not README)

- Source: `hrabanazviking/RuneForgeAI-HugrGate`, cloned fresh
  under $HOME at `~/hugrgate-x13`; HEAD measured
  `2aa74350fa76bc4a35a0841db4582d6fa8b12ae9` (identical to the
  `git ls-remote` HEAD at audit time).
- Version: package `hugrgate` **1.0.0** (`pyproject.toml` +
  `hugrgate/__init__.__version__`). The roadmap's Observed
  note ("active alpha v0.1.0") is stale: the README now
  reports a substantial working alpha implementation, still
  explicitly not production-hardened. Sole hard dependency
  pyyaml; optional extras declare the heavier rungs (ml /
  onnx / nli / llm / server / bench / vllm / mlx / openvino /
  tensorrt / npu / otel). Console scripts `hugrgate` and
  `hugrgate-server`.
- Structure at the audited HEAD: 468 Python modules under
  `hugrgate/`, 1,000 Python files in the tree, 499 test files
  under `tests/`, 8 example scripts under `examples/`, and a
  `benchmarks/` corpus (including `calibration_500.json`). An
  import smoke of the staged tree passes with the system
  interpreter (`hugrgate` 1.0.0 imports, `SPEC_TYPES` read
  back) — structural proof only, not a suite run (X13-T1).
- Schemas (section 48 item 1): `DecisionSpec`
  (`hugrgate/spec.py`) declares `SPEC_TYPES = (categorical,
  binary, ordinal, numeric, multilabel)` with per-type
  validation; `DecisionResult` (`hugrgate/result.py`) carries
  value / probability / distribution / uncertainty / accepted
  / backend / model / latency / calibration profile / fallback
  flag with enforced invariants (distribution sums to 1, the
  chosen value's mass equals the reported probability);
  `hugrgate/validation.py` enforces result invariants for all
  five types; `hugrgate/abstain.py` makes abstention a typed
  outcome and `hugrgate/fallback.py` an ordered failover chain
  whose total failure abstains or escalates.
- Contract types — only what the installed engine verifies
  (item 3): the deterministic `RuleBackend`
  (`hugrgate/backends/rules.py`) supports categorical /
  binary / ordinal; the scikit-learn backends (logreg /
  forest / boosting) categorical / binary; the embedding
  prototype categorical / binary; NLI binary only; the
  local-LLM backend categorical / ordinal / binary. **No
  bundled backend claims numeric or multilabel** in its
  `capabilities()` — those two carry schema + validation +
  contract-constraint support only. This slice therefore
  offers binary / categorical / ordinal and refuses numeric /
  multilabel by name as unverified.
- Inference ladder (item 4): `hugrgate/ladder.py` orders pure
  rules → classical statistics/ML → embeddings/ONNX → tiny
  local LLM → larger local models, with min-confidence gates,
  latency-budget pruning and a privacy gate (remote rungs
  require `policy.remote_inference=True`). **No cloud adapter
  ships at the audited HEAD** — the authorized-cloud rung
  exists only as that policy concept.
- Calibration (item 7): `hugrgate/calibration/metrics.py`
  provides `brier_score`, `log_loss` and
  `expected_calibration_error`, with a large calibration
  package (isotonic / Platt / temperature / conformal /
  selective abstention and more).
- License text-verified at the audited HEAD: `LICENSE` is the
  full Apache License 2.0 text (201 lines), sha256
  `c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4`;
  pyproject declares Apache-2.0. No HugrGate source is copied
  or vendored by this slice.

## Build (section 48 items 1-10)

`plugins/volmarr-core/hugrgate.py` (new, original code):

- Status/catalog (items 1-2): `hugrgate_status` reports
  unconfigured vs configured truthfully; when configured it
  measures the REAL staged tree's structure only — .git HEAD
  vs the audited HEAD, the package version in its pyproject,
  the LICENSE sha256, and Python module / package-module /
  test-file counts by filename. `decision_catalog` carries
  the section 48 contract catalog (declared vs verified per
  type, with the audited basis for each row) and the
  configurable inference ladder represented honestly: only
  rungs that exist in the engine are catalogued as existing,
  only the pure-rules rung is offered/bound by the connector,
  and the cloud rung is marked non-existent as an adapter,
  never offered, authorization-gated as a concept.
- decision.evaluate (items 2, 5-6, 9-10): `evaluate_decision`
  is a bounded, deterministic pure-rules evaluation. Input is
  bounded (feature count, text length, total request size —
  excess refused as `input_too_large`); the typed result
  carries decision type, value, confidence, a distribution
  that sums to 1 with the chosen value's mass equal to the
  reported probability, uncertainty, calibration profile,
  source revision (the audited HEAD), backend/model identity,
  latency, the preserved privacy label and full provenance.
  Abstain/unknown is a first-class outcome (`no_rule_matched`)
  whose task-control effect is stated in the result: hold and
  use the deterministic default. Uncertainty outputs are
  advisory for candidate routing, relevance classification
  and observational prioritization only.
- Refusals by name, all fail-closed: structurally invalid
  specs (schema conformance: unknown type, missing binary
  statement, invalid options/levels/bounds/labels),
  `contract_type_unverified` for numeric/multilabel,
  `decision_subject_refused` for secrets access and
  destructive-action authorization as decision subjects (a
  Boolean permission rule is never turned into a model
  gamble), `use_not_allowed` for any other use,
  `cyclic_route_refused` for routes via HugrGate / A.E.S.I.R.
  / ThoughtForge / MindSpark (item 8), `unknown_rung`,
  `cloud_not_authorized` without explicit authorization and
  `cloud_adapter_unavailable` with it (no adapter ships;
  never an unannounced cloud fallback), `malformed_rule`,
  `features_not_mapping`, and `timeout` past the budget.
  A request for an engine rung this connector does not bind
  is answered by the deterministic rules rung with the
  fallback announced (`fallback_used` + `rung_not_bound:<rung>`
  + provenance rung fields) — deterministic fallback, never
  silent substitution (item 9).
- Calibration surface (item 7): `calibration_metrics`
  computes Brier score (with standard error), log loss and
  abstention rate under the versioned schema
  `runeforge.hugrgate.calibration.v1`, ONLY from the evaluated
  examples supplied — empty input computes nothing and says
  so, malformed examples fail closed by name, synthetic
  fixtures are labelled as such, and production calibration
  is recorded as unproven (the roadmap's Observed note).
- Wiring: capability-bus seed descriptor `volmarr-hugrgate`
  0.1.0 (in-process transport, local-private only, adapter at
  the volmarr-core plugin.yaml; the two `service_count == 6`
  assertions in `test_volmarr_capability_bus.py` move to 7
  with a version assertion added — the X.10–X.12-style
  genuine-change update); CLI family `hermes volmarr hugrgate
  {status|catalog|evaluate}` mirroring the sibling verbs
  (evaluate runs two labelled SYNTHETIC requests: one
  deterministic decision, one abstention); `hugrgate_enabled`
  / `hugrgate_root` config keys, both default-off/empty.

## Live caller (section 28.2)

`hermes volmarr hugrgate {status|catalog|evaluate}` proven in
disposable HERMES_HOME homes on disk (log
`~/team01-x13-liveproof.log`), using the team-01 checkout's
own `hermes` binary via `scripts/run-in-hermes-env`:

- Unconfigured home: status truthful (`enabled: false`,
  `configured: false`, tree `not_configured`,
  `production_ready: false`); catalog lists the five contract
  types with only binary/categorical/ordinal verified and the
  cloud rung not offered; evaluate returns the deterministic
  synthetic decision (`true`, probability 0.9) and the
  abstention case (`no_rule_matched`); bare verb rc 2. All
  other verbs rc 0.
- Configured home (`hugrgate_enabled: true`,
  `hugrgate_root: ~/hugrgate-x13` under
  `plugins.entries.volmarr-core.settings`): status measures
  the REAL staged tree — `head_matches_audited: true` at
  2aa74350fa76, `package_version: 1.0.0` read from the tree's
  own pyproject, `license_matches_audited: true` (sha256
  c71d239df917...), `module_count: 1000` Python files,
  `package_module_count: 468`, `test_file_count: 499`.

## Tests and gate

- New contracts: `tests/plugins/test_volmarr_hugrgate_x13.py`
  (14 tests) pinning the section 48 test gates — schema
  conformance (valid binary/categorical/ordinal evaluations
  plus nine invalid-spec refusals by name), calibrated
  examples (exact Brier 0.01 / log loss −ln 0.9 on labelled
  synthetic examples, abstention rate, no fabricated metrics
  on empty input), deterministic fallback (announced
  rung fallback, malformed-rule fail-closed, cloud refused
  unauthorized and unavailable when authorized), abstention
  with its task-control effect, offline/no-egress on every
  surface, timeout, cyclic route refusal, refused decision
  subjects, bounded input + performance budget, unverified
  contract types refused by name, and the CLI family.
- Targeted (log `~/team01-x13-targeted.log`): 4 files
  (hugrgate_x13 + capability_bus + draupnir_x12 +
  aurelia_x11) = **51 passed / 0 failed** (14 new X.13
  contracts; capability_bus carries the seed-count update).
- Full contract gate (log `~/team01-x13-fullcontracts.log`),
  run serialized on an idle laptop: in the canonical scope
  (test_volmarr_*.py + the two kista files): **150 files =
  1,318 passed / 7 failed / 1 skipped** — the X.12 baseline
  (149 files = 1,304 / 7 / 1) plus exactly the 14 new X.13
  contracts, the 7 failures name-identical to the known
  live-transport set (5x test_volmarr_core_plugin.py, 1x
  test_volmarr_verdandi_stimuli.py, 1x
  test_volmarr_voice_runner.py), ZERO regressions.

## Honest remainders / tickets

- X13-T1 (engine suite): the connector binds NO live
  transport and runs NO engine code. The HugrGate tree's own
  499-file test suite was not run by this slice — the audit
  was structural plus an import smoke of the package and
  `SPEC_TYPES`. A suite run is the natural next maturity
  proof.
- X13-T2 (unverified types): numeric and multilabel contracts
  are schema-declared and validation-enforced upstream but no
  bundled backend verifies them at the audited HEAD; they
  stay refused by name here until an audited engine update
  ships a backend that claims them.
- X13-T3 (unbound rungs + cloud): the classical-ML,
  embeddings/ONNX, tiny-local-LLM and larger-local rungs exist
  in the engine but are not bound by this connector (requests
  for them receive the announced deterministic fallback).
  No cloud adapter exists upstream; the authorized-cloud rung
  remains a policy concept requiring explicit authorization
  and a future audited adapter — it is never a fallback.
- X13-T4 (calibration): production calibration and
  cross-device performance remain unproven per the roadmap's
  Observed note; the metrics surface computes only from
  supplied examples and claims nothing about production
  workloads. Latency/cost comparisons on representative
  workloads (section 48 item 7) are not yet measured.
- X13-T5 (registry): no integration-lock or
  INTEGRATION_MATRIX row exists for HugrGate; none was
  invented. The audited HEAD 2aa74350fa76 is recorded only in
  this workstream record and the connector.
- The section 32 release scorecard still reads NOT
  releasable (0 met / 10 unmet / 5 deferred);
  `production_ready` stays False in every X.13 record.
