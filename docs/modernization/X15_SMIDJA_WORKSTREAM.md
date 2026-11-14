# X.15 Seidr-Smidja — ecosystem workstream 15 of 15 (Team 01, 2026-11-14)

Roadmap section 50 executed: an opt-in, default-off, local-only
forge connector over the Hermes plugin boundary, following the
X.10–X.14 pattern, extending the preserved read-only
`volmarr-smidja 0.1.0` preflight toward CONTROLLED production
at the record level only. Slice discipline: a new
`smidja_forge` module + `hermes volmarr smidja-forge
{status|catalog|plan}` CLI family in volmarr-core, two
default-off `smidja_forge_*` config keys, one capability-bus
seed descriptor, exactly one CUSTOMIZATIONS.md ledger row,
README.md byte-identical (sha256
336813d11bbe5aa2ff745b4a4bc3abcf2a283cd13971c0c11d061377129db7f3,
verified before and after). Registry choice (section 35 duty,
X.09 precedent): a Seidr-Smidja row EXISTS in both registries,
so — exactly as X.09 did for Astrology — the integration-lock
Seidr-Smidja verdict and INTEGRATION_MATRIX row 16 gain the
X.15 execution note in place; the pin
`32cdbd7a87358bc1f6f046c4e1449c35f4d5d40a` is NOT moved,
license and verification status are unchanged, and no other
entry or row was touched. Commit-only on
`yrsa/hermes-team-01`; the keeper banks serially.

## Audit (from source, not README)

- Source: `hrabanazviking/Seidr-Smidja`, default branch
  `development`; development HEAD == the E.14 audited pin
  `32cdbd7a87358bc1f6f046c4e1449c35f4d5d40a` (keeper
  re-verified by ls-remote this tick — UNCHANGED since E.14).
  Staged tree `~/smidja-e14` sits clean at the pin.
- Structure at the pin (src layout): package `seidr-smidja`
  **0.1.0.dev0** (pyproject) with modules loom / hoard / gate /
  oracle_eye / forge / brunhand under `src/seidr_smidja/`;
  the Loom `AvatarSpec` (spec_version 1.0, avatar_id slug,
  base_asset_id into the Hoard catalog, body/face/hair/outfit/
  expressions, metadata, opaque extensions) is the engine's
  parametric spec the forge spec below is shaped to sit
  beside, not replace.
- License — the E14-T1 conflict, carried not resolved: root
  `LICENSE` is genuine Apache-2.0 text (sha256
  cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30,
  re-measured this slice) while `pyproject.toml` declares
  `license = { text = "MIT" }`. Every record this connector
  writes carries the conflict string; neither text was
  silently picked over the other and the engine tree was not
  edited.
- Existing fork surface (section 50 items 1–2):
  `volmarr-smidja 0.1.0` — read-only Loom spec validation,
  Hoard asset discovery, Gate rules/checks, Oracle Eye views
  and Forge readiness via bounded subprocess. It is
  PRESERVED untouched by this slice (no file modified, its
  tests unmodified) and stays the only live engine surface.
- Hamr interface (item 7, from the E.13 audit at pin
  f77aa588601b): `CharacterSpec` (name, version, body / face /
  hair / clothing / expressions / physics, `ExportSpec`
  {format vrm1|glb|blend, license}) plus the
  `hamr/core/perf.py` PerformanceBudget tiers — minimal
  (60 s / 1000 MB / 30 000 tris / 512 px / 180 s timeout),
  balanced (45 s / 1500 MB / 50 000 / 1024 / 120 s), high
  (30 s / 2500 MB / 80 000 / 2048 / 90 s). The translation
  below is built on exactly those fields.
- Scenario 6 posture: no remote VRoid desktop, webcam,
  microphone, GPU job or external account activates without
  appropriate permission — here, none activates at all.

## Build (section 50 items 1–10)

`plugins/volmarr-core/smidja_forge.py` (new, original code):

- Status (items 1–2): `smidja_forge_status` reports
  unconfigured vs configured truthfully — unconfigured
  returns the configuration error naming the two
  `smidja_forge_*` keys, like its sibling connectors; when
  configured it measures the REAL staged tree only: .git HEAD
  vs the audited pin, pyproject package name/version and its
  declared license, the LICENSE sha256, the E14-T1 conflict
  string, and Loom/Hoard/Gate/Oracle Eye/Forge/Brunhand
  module presence.
- Forge spec schema (item 4): `runeforge.smidja.forge.v1`
  in the catalog — structured job ID
  (`forge-<slug>`), safe paths (spec/output/asset/cleanup
  paths must resolve under approved roots; traversal refused
  by name), versioned metadata, blender version, export
  format + VRM version + exporter compatibility fields,
  CPU/GPU budget, timeout, log-capture plan, cancellation
  plan and cleanup plan. Invalid specs are rejected by name
  (`spec_version_unsupported`, `job_id_invalid`,
  `path_traversal_refused`, `metadata_version_missing`,
  `budget_field_invalid`, …).
- Dry-run build plan (item 3): validated spec → licensed
  asset inventory → dry-run plan with a deterministic plan
  key and `job_state: planned`. The plan EXECUTES NOTHING:
  no Blender, no subprocess render, no file writes outside
  the job record (`writes_files: False`). A failed render
  prerequisite (fake or real) fails the plan by name
  (`render_prerequisite_failed`).
- License/provenance gate (item 6): every asset must carry
  provenance (missing provenance refused by name); an
  unknown/unset license is REJECTED by name when
  redistribution is requested
  (`asset_license_unknown_redistribution_refused`) and the
  gap is named in the plan's inventory otherwise — never
  hidden.
- Approval gate (items 3, 5): `approve_job` moves a record
  planned → approved only with explicit operator
  authorization recorded (operator named); without it,
  refused by name
  (`approval_refused_operator_authorization_required`). A
  passed gate EXECUTES NOTHING — no Blender build, no GPU
  job, no remote VRoid/Brúarhönd control, no GUI, no
  webcam/mic, no external account. Wrong-host refusal: a
  spec naming a different host than the local staged host is
  refused by name (`wrong_host_refused`).
- Job lifecycle (item 4): planned / approved / cancelled
  states; `cancel_job` produces a cleanup record listing
  the job's declared artifact paths, each validated under
  the approved roots — record-level cleanup only, nothing
  real is deleted (`deleted: False`).
- VRM inspection record (test gate): metadata-only
  inspection (`inspection_scope: metadata_only`,
  `compliance_performed: False`,
  `visual_validation_performed: False`) — Gate compliance
  stays with the read-only preflight; nothing here claims
  certification.
- Hamr reconciliation (item 7): `translate_hamr_to_forge`
  / `translate_forge_to_hamr` map the Hamr ExportSpec
  formats (vrm1 → vrm/1.0, glb → glb) and the exact Hamr
  budget tiers, with EXPLICIT incompatibility errors named
  per field and no silent coercion: Hamr `blend` export,
  Hamr physics/expressions/clothing payloads, unknown Hamr
  budget tiers and off-tier forge budgets all fail closed
  by name; forge-required fields Hamr cannot supply
  (job_id, host, log capture, cancellation, cleanup,
  assets, redistribution) are named as missing, never
  invented. One avatar standard, not two.
- Presentation-only routing (item 8): finished-artifact
  records route to voice/avatar/VRM clients as
  presentation-only consumers (`secret_access: False`,
  `cognitive_control: False`); payloads requesting secrets,
  credentials, cognitive/GUI control, webcam or microphone
  are refused by name.
- Privacy (item 9): private assets are refused by name for
  every egress destination (public README, training,
  telemetry, publication, external account, remote host);
  build artifacts are refused for public README / training /
  telemetry destinations outright
  (`artifact_egress_refused`).
- Capability matrix (item 10): read-only preflight LIVE
  (the preserved adapter), dry-run planning live at record
  level; live remote control, Blender build, VRM export and
  visual validation each marked separately and honestly
  NOT live. `production_ready` stays False.
- Wiring: capability-bus seed descriptor
  `volmarr-smidja-forge` 0.1.0 (in-process transport,
  local-private only, adapter at the volmarr-core
  plugin.yaml; the two `service_count == 8` assertions in
  `test_volmarr_capability_bus.py` move to 9 with a version
  assertion added — the X.10–X.14-style genuine-change
  update); CLI family `hermes volmarr smidja-forge
  {status|catalog|plan}` mirroring the sibling verbs (plan
  runs one labelled SYNTHETIC spec under the configured
  root); `smidja_forge_enabled` / `smidja_forge_root`
  config keys, both default-off/empty.

## Live caller (section 28.2)

`hermes volmarr smidja-forge {status|catalog|plan}` proven in
disposable HERMES_HOME homes on disk (log
`~/team01-x15-liveproof.log`), using the team-01 checkout's
own `hermes` binary via `scripts/run-in-hermes-env`:

- Unconfigured home (plugin enabled, no forge settings):
  status truthful (`enabled: false`, `configured: false`,
  configuration error "Configure smidja_forge_enabled and
  smidja_forge_root.", tree `not_configured`,
  `production_ready: false`); catalog carries the forge spec
  v1 schema with the capability matrix (Blender build and
  live remote control NOT live); plan returns the labelled
  synthetic dry-run plan (`job_state: planned`,
  `executes_operations: false`); bare verb rc 2. All other
  verbs rc 0.
- Configured home (`smidja_forge_enabled: true`,
  `smidja_forge_root: ~/smidja-e14` under
  `plugins.entries.volmarr-core.settings`): status measures
  the REAL staged tree — `head_matches_pin: true` at
  32cdbd7a8735, `package_name: seidr-smidja`,
  `package_version: 0.1.0.dev0` read from the tree's own
  pyproject, `pyproject_license_declared: MIT` beside
  `license_matches_audited: true` (sha256 cfc7749b96f6...)
  with the E14-T1 conflict string carried in the record,
  all six modules present (loom, hoard, gate, oracle_eye,
  forge, brunhand); plan returns the synthetic dry-run plan
  against the staged root, rc 0.

## Tests and gate

- New contracts: `tests/plugins/test_volmarr_smidja_x15.py`
  (16 tests) pinning the section 50 test gates at record
  level with fakes — fake render prerequisite fail, invalid
  spec rejection by name (version, job ID, path traversal,
  metadata), asset license gate (redistribution refusal +
  named gap + provenance refusal), VRM inspection record
  (metadata-only, no compliance claim), cancellation
  cleanup (record-level, nothing deleted), wrong-host
  refusal, approval refusal and pass-executes-nothing, Hamr
  incompatibility errors in both directions (blend export,
  physics payload, unknown tier, off-tier budget — no
  silent coercion), privacy refusals (private assets to
  public README/training/telemetry/publication; artifacts
  to training), presentation-only routing refusals, bounded
  input + performance budget, offline/no-egress on every
  surface, and the CLI family.
- Targeted (log `~/team01-x15-targeted.log`): 4 files
  (smidja_x15 + capability_bus + mythic_x14 + the preserved
  volmarr-smidja preflight battery) = **57 passed /
  0 failed** (16 new X.15 contracts; capability_bus carries
  the seed-count update; the volmarr-smidja battery passes
  unmodified, proving the preserved surface).
- Full contract gate (log `~/team01-x15-fullcontracts.log`),
  run serialized on an idle laptop: in the canonical scope
  (test_volmarr_*.py + the two kista files): **152 files =
  1,348 passed / 7 failed / 1 skipped** — the X.14 baseline
  (151 files = 1,332 / 7 / 1) plus exactly the 16 new X.15
  contracts, the 7 failures name-identical to the known
  live-transport set (5x test_volmarr_core_plugin.py, 1x
  test_volmarr_verdandi_stimuli.py, 1x
  test_volmarr_voice_runner.py), ZERO regressions.

## Honest remainders / tickets

- X15-T1 (nothing builds): the connector binds NO live
  transport and runs NO Seidr-Smidja code. Real Blender
  builds, VRM export, visual validation and live Brúarhönd
  remote VRoid control are NOT live and are marked as such
  in the capability matrix; the only live engine surface
  remains the read-only volmarr-smidja preflight. A real
  approved native forge job belongs to a future audited
  run with its own host-consent proof (Scenario 6).
- X15-T2 (carried E14-T1): the license metadata conflict at
  the pin stands — root LICENSE Apache-2.0 (text-verified)
  vs pyproject MIT. The connector carries the conflict in
  every record; fixing it is the engine owner's call.
- X15-T3 (carried E14-T2/T3): Hoard assets at the pin are
  listed but uncached, and Gate v0.1 leaves
  vrchat.polycount / vrchat.texture_memory unevaluated — a
  dry-run plan therefore inventories catalog metadata and
  cannot promise a cached-asset build or a full Gate
  certification.
- X15-T4 (carried E14-T4): the pin tracks `development`;
  `main` is a separate line, the engine version reads
  0.1.0.dev0 and no tags exist. A future engine update
  should first settle which line is canonical.
- X15-T5 (carried E14-T5): the engine's own suite carries
  3 Mjoll-bridge failures from `mcp` SDK drift in the
  staging venv; the forge surface is unaffected.
- X15-T6 (Hamr lineage): Hamr translation is record-level
  schema mapping only — no Hamr or Smiðja build is invoked
  through it, and durable cross-engine avatar job lineage
  does not exist yet.
- The section 32 release scorecard still reads NOT
  releasable (0 met / 10 unmet / 5 deferred);
  `production_ready` stays False in every X.15 record.
- This is workstream 15 of 15 — the last of the fifteen
  ecosystem workstreams in the governing roadmap.
