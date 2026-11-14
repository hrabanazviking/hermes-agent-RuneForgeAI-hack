# E.13 Hamr update - audit record (Team 01, 2026-11-14)

**Outcome: PIN UNMOVED - audit executed, all proofs pass.** The
last partially verified row in the ledger closes: the Hamr
LICENSE at the pin is genuine MIT, verified at text level
this slice, superseding the GitHub API's NOASSERTION. The
fork surface is unchanged: the `volmarr-hamr 0.4.0` plugin,
read-only spec validation, budget preflight and artifact
probing via bounded subprocess against a local checkout.
No Hamr source was copied into the fork.

## Target (re-measured, not inherited)

- Pin (before and after this slice):
  `f77aa588601b38a69b6c1fc0a6733ed5e95dffa8` - the first pin
  established at E0 (2026-11-07, Team 09 ls-remote), recorded
  in integration-lock.json and INTEGRATION_MATRIX row 15.
  COMPONENT_LICENSES.md carried no Hamr row before this
  slice; the row is added here (see Pin status below).
- Re-measurement this slice: `git ls-remote` HEAD ==
  `Development` (the repo's default branch) at the pin.
  The tag `v0.7.0` peels to
  `45f6704fdd5230c086fe064b1e2ed0a677057df3`, an ancestor of
  the pin on the same line; the `main` branch
  (`fe70321a0735a0159a455ef4eb1f75e4f1d90721`) is a divergent
  line carrying Volmarr writings, not the engine (see
  remainder E13-T1). Tree staged directly under $HOME at
  `~/hamr-e13`, HEAD verified at the pin.
- License: **MIT - PASS, verified at the text level this
  slice.** The `LICENSE` at the pin carries sha256
  `063972d5e6f14517cdf6f074f5893e8c7fe1f4cdcd96f4a5852ae0ab1c8e1480`,
  Copyright (c) 2026 Runa Gridweaver Freyjasdottir &
  Volmarr; the standard MIT grant text, plus a closing
  colophon ("Every vertex, every slider, every algorithm
  is yours...") after the license body. The pyproject.toml
  at the pin agrees (`license = {text = "MIT"}`, MIT
  classifier). Before this slice the lock recorded the
  license as NOASSERTION (GitHub API - license file
  present, unclassified); it is now verified at text level.

## Proof 1 - engine own suite at the pin: PASS with named environment failures

- Staging: the engine uses a src layout
  (`packages.find where=["src"]`), and the system
  `python3` lacks pydantic, so the suite was run in a
  dedicated venv under $HOME (`~/hamr-e13-venv`, deps
  installed with uv) with `PYTHONPATH=~/hamr-e13/src`; the
  engine tree itself was not edited. First run (venv bin
  not yet on PATH): 2,187 passed / 13 failed / 33 skipped
  (log `~/team01-e13-engine-suite-run1.log`). Second run
  with the venv bin on PATH: **2,191 passed / 9 failed /
  33 skipped** of 2,233 (log
  `~/team01-e13-engine-suite.log`).
- The 9 remaining failures are author-Pi staging artifacts,
  not engine defects (ticket E13-T4): 3
  `TestCLIIntegration` tests hardcode `cwd="/home/pi/Hamr"`
  and `PYTHONPATH="/home/pi/Hamr/src"`; 4
  `TestBuildScriptInBlender` tests hardcode
  `sys.path.insert(0, '/home/pi/Hamr/src')` inside Blender;
  2 `TestBlenderEnvironment` tests require the VRM
  (io_scene_vrm) and MB-Lab Blender addons, which are not
  installed on this host (Blender 5.0.1 itself is present).
  The 4 `TestCLIDryRun` failures of the first run were the
  missing `python` executable name on PATH and pass once
  the venv bin is on PATH.

## Proof 2 - fork hamr contracts before the edits: PASS

- `scripts/run_tests.sh` on `test_volmarr_hamr.py` and
  `test_volmarr_integration_ledger.py` on the pre-edit team
  tree (at banked main `273cc97ab0`): **2 files, 23 tests
  passed / 0 failed** (hamr 6, ledger 17; log
  `~/team01-e13-baseline.log`).

## Proof 3 - live adapter calls against the staged engine: PASS

- Live harness (script `~/team01-e13-live.py`, log
  `~/team01-e13-live.log`, full result
  `~/team01-e13-live-result.json`) drives the fork adapter
  handlers directly against the real staged tree
  (`~/hamr-e13`, engine_python `/usr/bin/python3`):
  **LIVE_OK**. Every call was run twice and asserted
  byte-identical at the raw response level.
- Spec validate (`minimal.yaml`): success, `valid` true,
  summary {name: Quick Avatar, version: 1.0,
  export_format: vrm1}, source license MIT, response
  sha256
  `ae63c2c902de4f13e5ef9908f34248d854aafae7f8b6c64587c1d116131a7f5b`.
- Presets catalog: 8 body presets / 6 character presets,
  response sha256
  `ee7e8bb390513cd15d8abcd51dc47e37fd3b789d7d36d7191d0916b1d11d9ee9`.
- Budget check (balanced): the adapter relays the real
  engine verdict, `within_budget` **false** - estimates
  {build_time_seconds: 27.192, peak_memory_mb: 427.12,
  total_triangles: 25620, max_texture_resolution: 2048}
  against limits {45.0 s, 1500.0 MB, 50000 triangles,
  1024 texture}: the engine estimator assumes a 2048
  texture size, which exceeds the balanced tier's 1024
  limit (see remainder E13-T2). Response sha256
  `b2716c7691f7af0b9555dff27a357efb60468340bc5c18d99068548543321b94`.
- Budget check (minimal): `within_budget` false, response
  sha256
  `7eaf5439d3782b425e02035d51394ff759ee4abf2331ddcebabd2614652f1885`.
- Artifact probe: the pinned tree carries no real VRM/GLB
  file (see remainder E13-T3), so the harness created a
  minimal valid GLB (92 bytes, `glTF` magic, version 2,
  JSON-chunk asset 2.0; file sha256
  `0f3b47c85f4c839fbaebdf762f0594561133fe1ca4fd7123a6aa7d9c8813473d`)
  at `build_output/e13_probe.glb` inside the staged tree's
  output directory and probed it: success, `exists` true,
  size_mb 8.77e-05, targets [VRCHAT], checks [],
  `inspection_scope` metadata_only,
  `compliance_performed` false - the engine's
  `builder.inspect` at the pin returns metadata only.
  Response sha256
  `cad4920a9735168a42a3e7aa8fbf40946d93a3f01353511313be7d569e15759a`.
- Artifact directory case: probing `test.vrm` - a
  *directory* inside `build_output` holding only
  `.hamr_default_schoolgirl_preset.yaml` - returns the
  truthful refusal "artifact_path must name an existing
  VRM or GLB up to 512 MiB within artifact_root". The
  adapter correctly refuses it; it was not weakened.

## Proof 4 - fork targeted batteries after the edits: PASS

- Same two batteries as Proof 2, after the ledger edits:
  **2 files, 23 tests passed / 0 failed** (log
  `~/team01-e13-targeted.log`) - the ledger battery now
  carries the new pin-guard assertion for Hamr (CLI
  `engines show`, pinned ==
  `f77aa588601b38a69b6c1fc0a6733ed5e95dffa8`) and the
  updated verification counts. The pin-guard and count
  changes add assertions inside the existing ledger tests,
  so the count is unchanged.

## Proof 5 - absent engine root fails truthfully: PASS

- In the same live harness (result JSON above): with the
  engine root pointed at a nonexistent path
  (`~/hamr-e13-absent`), both the spec-validate and the
  presets handlers return the truthful configuration
  error: "Configure volmarr-hamr engine_root, spec_root,
  and a compatible Python interpreter." Nothing was
  installed or faked to produce this.

## Pin status

- Pin **unmoved** in this slice: `pinned` == `current_head`
  == `f77aa588601b38a69b6c1fc0a6733ed5e95dffa8` in
  integration-lock.json (Hamr row only: license MIT now
  text-verified, pin_source COMPONENT_LICENSES.md, verdict
  "current - E.13 executed 2026-11-14", `update_needed`
  false), INTEGRATION_MATRIX.md row 15, the new Hamr row
  in COMPONENT_LICENSES.md, and the pin-guard assertion in
  `tests/plugins/test_volmarr_integration_ledger.py`,
  following the E.05-E.12 pattern.
- The Hamr verification status moves `partially_verified`
  -> `verified`; the ledger counts move to **25 verified
  / 0 partially verified / 1 blocked (Sagnaskemma)** -
  the ledger test's count assertions are updated in this
  same slice. Hamr was the last partially verified row.
- No adapter change: no fork code was modified in this
  slice. No CUSTOMIZATIONS.md row: ledger state only
  (E.03 / E.05-E.12 precedent).
- README.md untouched (sha256
  `336813d11bbe5aa2ff745b4a4bc3abcf2a283cd13971c0c11d061377129db7f3`
  before and after).

## Gate evidence - full fork contracts

Full fork contracts on the edited team tree via
scripts/run_tests.sh = 137 files, 1,171 passed / 7 failed
/ 1 skipped - exactly the banked baseline, the 7
name-identical to the known live-transport set (5
test_volmarr_core_plugin.py + 1
test_volmarr_verdandi_stimuli.py + 1
test_volmarr_voice_runner.py); ZERO regressions (log
`~/team01-e13-fullcontracts.log`, run on the team tree via
the serialized gate waiter `~/team01-e13-gate-waiter.sh`).
Targeted batteries (hamr + integration ledger) 23 passed /
0 failed both pre-edit (`~/team01-e13-baseline.log`) and
post-edit (`~/team01-e13-targeted.log`). Engine own suite
at the pin: 2,191 passed / 9 failed / 33 skipped, the 9
all named author-Pi staging artifacts (E13-T4;
`~/team01-e13-engine-suite.log`).

## Honest remainders (named, not hidden)

- **E13-T1** (branch / tag / version split at the pin):
  the pin is the `Development` branch HEAD; tag `v0.7.0`
  peels to an ancestor commit
  (`45f6704fdd5230c086fe064b1e2ed0a677057df3`), the
  pyproject version at the pin reads **0.8.0**, and the
  repo `main` branch is a divergent writings line
  (`fe70321a0735a0159a455ef4eb1f75e4f1d90721`, "Create
  Volmarr_writings_philosophy.md"), not the engine line.
  Recorded, not resolved: the pin decision is unchanged
  because HEAD (the default branch) == the pin. A future
  engine update should first settle which line is
  canonical.
- **E13-T2** (live budget semantics): the real engine
  returns `within_budget` false for both the balanced and
  minimal tiers on `examples/minimal.yaml`, where the fork
  contract's fake engine returns true for balanced - the
  real estimator hardcodes a 2048 texture-size assumption
  (`hamr/core/perf.py`) against the tiers' lower texture
  limits. The adapter is faithful in both cases; aligning
  the fixture's expectations with real-engine semantics is
  future contract work, not an audit fix.
- **E13-T3** (no real artifact in the pinned tree):
  `build_output/test.vrm` at the pin is a directory
  holding only a preset YAML; no exported VRM/GLB file
  exists in the tree to probe. The live artifact proof
  therefore used a harness-created minimal valid GLB, and
  the engine's inspect at the pin is metadata-only in any
  case (checks []). A real-export artifact proof awaits
  a Blender build with the VRM/MB-Lab addons present
  (see E13-T4).
- **E13-T4** (engine suite host artifacts): 9 of the
  engine's 2,233 tests fail on purplelongship for
  staging reasons - 7 hardcode the engine author's Pi
  paths (`/home/pi/Hamr`, `/home/pi/Hamr/src`) and 2
  require the VRM and MB-Lab Blender addons, which are
  not installed on this host. Fixing them means editing
  the engine tree or staging `/home/pi`, both out of
  this audit's scope; the engine tree was left untouched
  and the remaining 2,191 tests pass.
- **E12-T2** (matrix tally drift) continues: the
  INTEGRATION_MATRIX "Verification tally" paragraph
  still carries its W08 promotion counts (21 verified /
  4 partially verified / 1 blocked). The lock and the
  ledger test are the enforced truth (25 / 0 / 1 after
  this slice); the tally paragraph wants a dedicated
  correction pass, out of this slice's rows-only scope.
- The section 32 release scorecard still reads NOT
  releasable; E.13 changes engine currency only, nothing
  else.
- Next in roadmap order: E.14.
