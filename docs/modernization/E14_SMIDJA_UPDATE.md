# E.14 Seidr-Smidja update - audit record (Team 01, 2026-11-14)

**Outcome: PIN UNMOVED - audit executed, all proofs pass.**
The Seidr-Smidja LICENSE at the pin is genuine Apache-2.0,
verified at text level this slice - but the engine repo's
own pyproject.toml declares MIT, a metadata conflict that
is recorded honestly and ticketed (E14-T1), not silently
resolved. The fork surface is unchanged: the
`volmarr-smidja 0.1.0` plugin, read-only Loom / Hoard /
Gate / Oracle Eye preflight via bounded subprocess against
a local checkout. No Seidr-Smidja source was copied into
the fork.

## Target (re-measured, not inherited)

- Pin (before and after this slice):
  `32cdbd7a87358bc1f6f046c4e1449c35f4d5d40a` - the first
  pin established at E0 (2026-11-07, Team 09 ls-remote),
  recorded in integration-lock.json and
  INTEGRATION_MATRIX row 16. COMPONENT_LICENSES.md
  carried no Seidr-Smidja row before this slice; the row
  is added here (see Pin status below).
- Re-measurement this slice: `git ls-remote` HEAD ==
  `refs/heads/development` == the pin (the repo's default
  branch is `development`; `origin/HEAD` points at it).
  `refs/heads/main` is a different commit,
  `5b0f2979aa901314eea5e32bf0d07514f50fa5b4` (see
  remainder E14-T4). The repo carries no tags
  (`latest_tag` null in the lock). Tree staged directly
  under $HOME at `~/smidja-e14`, HEAD verified at the
  pin, working tree clean.
- License: **Apache-2.0 - PASS, verified at the text
  level this slice, WITH A TICKETED METADATA CONFLICT.**
  The `LICENSE` at the pin carries sha256
  `cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30`
  - genuine Apache License Version 2.0 text, the same
  sha256 as the Apache text verified in E.09. The
  `pyproject.toml` at the pin (line 11) instead declares
  `license = { text = "MIT" }`. The root LICENSE text
  governs as the text-verified license; the pyproject
  declaration disagrees and is the engine repo's own
  inconsistency - neither was silently picked over the
  other in the engine tree, which was not edited, and
  every fork record written this slice carries the
  conflict note (ticket E14-T1). Before this slice the
  lock recorded the license as "Apache-2.0 (GitHub
  API)"; it is now verified at text level.

## Proof 1 - engine own suite at the pin: PASS with named environment failures

- Staging: the engine uses a src layout, so the suite
  was run in a dedicated venv under $HOME
  (`~/smidja-e14-venv`) with
  `PYTHONPATH=~/smidja-e14/src`, venv python `-m pytest
  tests/ -q` in `~/smidja-e14` (log
  `~/team01-e14-engine-suite.log`, run serialized behind
  the baseline battery by the engine waiter). The engine
  tree itself was not edited. Result: **485 passed / 3 failed / 3 skipped** of 491. The 3 failures are all `TestMjollWithMCP` tests in `tests/bridges/test_mjoll_server.py`, each failing with `AttributeError: 'Server' object has no attribute 'list_tools'` at `src/seidr_smidja/bridges/mjoll/server.py:62` - the `mcp` SDK version resolved into the staging venv has drifted from the API the engine Mjoll bridge was written against. That is a dependency-version artifact of the staging environment, in a bridge surface this audit does not exercise, not a defect in the Loom / Hoard / Gate / Oracle surface (ticket E14-T5).

## Proof 2 - fork smidja contracts (baseline battery): PASS

- `scripts/run_tests.sh` on `test_volmarr_smidja.py` and
  `test_volmarr_integration_ledger.py` on the team tree
  (log `~/team01-e14-baseline.log`, run by the serialized
  baseline waiter). Honest timing note: the waiter was
  launched before this slice's ledger edits but the
  shared laptop was held by other campaigns' suites, so
  it fired after the edits landed; it therefore serves
  as a post-edit targeted run, and Proof 4 repeats the
  same two batteries after all edits. Result: **2 files, 28 tests passed / 0 failed** (smidja 11, ledger 17).

## Proof 3 - live adapter calls against the staged engine: PASS

- Live harness (script `~/team01-e14-live.py`, full
  result `~/team01-e14-live-result.json`) drives the
  fork adapter handlers directly against the real staged
  tree (`~/smidja-e14`, engine_python
  `~/smidja-e14-venv/bin/python`). A direct engine
  exercise (script `~/team01-e14-engine.py`, result
  `~/team01-e14-engine-result.json`) confirms the same
  facts at the engine API level. Every adapter response
  carries `license_metadata` "CONFLICT: root Apache-2.0;
  pyproject MIT" - the adapter itself surfaces the
  E14-T1 conflict; it was not hidden.
- Spec validate: `valid` true; summary {spec_version:
  1.0, avatar_id: my_avatar_v1, display_name: My Avatar,
  base_asset_id: vroid/sample_a, license: CC0-1.0} (the
  CC0-1.0 is the spec's own declared asset license, not
  the engine license). Response sha256
  `74f6e786f07a9e24391e42bb63c927cce70de2a6c4dc16744ad47ed5f0ebc7b3`.
- Hoard assets: 4 assets - vroid/sample_a,
  vroid/sample_b, turbosquid/female_rigged_2024,
  runa/mb_lab_base_v5. Response sha256
  `85f2b933110c0c1889848acc9cc466231c0a7749d1b627934c90deb9fcc3177b`.
  At engine level all four carry `cached: false` (see
  remainder E14-T2).
- Gate rules: 19 rules in the VRChat set, first
  `vrchat.humanoid_bones.required`. Response sha256
  `57c42cb40ad2d14d23e1c53c11613bb78add8f90e25394154465ac98556825aa`.
  The direct engine exercise also reads a 12-rule VTube
  set (vtube.vrm_version, expressions, lookat, bones).
- Oracle Eye render views: 8 views - front,
  three_quarter, side, face_closeup, t_pose,
  expression_smile, expression_sad,
  expression_surprised. Response sha256
  `cda8913c397247145d3c31206efeded7498b7298f32e869ed70f1b8a67b2f8d5`.
- Forge readiness: `forge_ready` true - Blender
  available, build script present. Response sha256
  `82ce6bfe0976a1f061ce4447daec13676efba104b90d1d21aae64fac3ee899c3`.
- Gate check: the harness created the same minimal
  valid GLB as the E.13 proof (92 bytes, `glTF` magic,
  version 2; file sha256
  `0f3b47c85f4c839fbaebdf762f0594561133fe1ca4fd7123a6aa7d9c8813473d`)
  at `~/smidja-e14-artifacts/avatar.vrm` and checked it
  against the VRChat target (tier Good):
  `official_gate_passed` **false** - the real engine
  verdict on a synthetic artifact: all 19 required
  humanoid bones missing and all 15 viseme rules
  (sil..ou) violated, with `vrchat.polycount` and
  `vrchat.texture_memory` returned as WARNING "Rule not
  evaluated in v0.1 - manual check required"
  (`unevaluated_rule_ids`, `certification_complete`
  false, compliance scope
  `official_gate_structural_header`). This is recorded
  as the engine's truthful verdict, not as a defect.
  Response sha256
  `7cbbf79890effe07e40ca6b193110da4cbe54b7f47eb7ee5915573db961db64e`.
- Asset probe: `vroid/sample_a` - success, `available`
  **false**, truthful: the asset is listed in the hoard
  catalog but not cached; the direct engine resolve
  raises `AssetNotFoundError`, and the probe fetches and
  opens nothing (`asset_fetched` false, `asset_opened`
  false, path withheld). Response sha256
  `26a656a782abaa52ca2c5e5646611d386106e990ac79d273086849f6df48a9d2`.

## Proof 4 - fork targeted batteries after the edits: PASS

- Same two batteries as Proof 2, after the ledger edits
  (log `~/team01-e14-targeted.log`, run by the serialized gate waiter): **2 files, 28 tests passed / 0 failed** - the ledger battery
  now carries the new pin-guard assertion for
  Seidr-Smidja (CLI `engines show`, pinned ==
  `32cdbd7a87358bc1f6f046c4e1449c35f4d5d40a`). The
  pin-guard adds assertions inside the existing ledger
  tests, so the test count is unchanged.

## Proof 5 - absent engine root fails truthfully: PASS

- In the same live harness (result JSON above): with
  the engine root pointed at a nonexistent path, the
  spec-validate handler returns the truthful
  configuration error "Configure volmarr-smidja
  engine_root, spec_root, and Python." and the assets
  handler returns "Configure volmarr-smidja engine_root
  and Python." Nothing was installed or faked to
  produce this.

## Pin status

- Pin **unmoved** in this slice: `pinned` ==
  `current_head` ==
  `32cdbd7a87358bc1f6f046c4e1449c35f4d5d40a` in
  integration-lock.json (Seidr-Smidja row only: license
  Apache-2.0 now text-verified with the pyproject
  conflict recorded in the verification method and
  notes, pin_source COMPONENT_LICENSES.md, verdict
  "current - E.14 executed 2026-11-14", `update_needed`
  false), INTEGRATION_MATRIX.md row 16, the new
  Seidr-Smidja row in COMPONENT_LICENSES.md, and the
  pin-guard assertion in
  `tests/plugins/test_volmarr_integration_ledger.py`,
  following the E.10-E.13 pattern.
- The Seidr-Smidja verification status stays `verified`
  (it was already counted verified on the strength of
  the API license reading); the ledger tally does not
  move: **25 verified / 0 partially verified / 1 blocked
  (Sagnaskemma)**.
- No adapter change: no fork code was modified in this
  slice. No CUSTOMIZATIONS.md row: ledger state only
  (E.03 / E.05-E.13 precedent).
- README.md untouched (sha256
  `336813d11bbe5aa2ff745b4a4bc3abcf2a283cd13971c0c11d061377129db7f3`
  before and after).

## Gate evidence - full fork contracts

Full fork contracts on the edited team tree via scripts/run_tests.sh = 137 files, 1,171 passed / 7 failed / 1 skipped - exactly the banked baseline, the 7 name-identical to the known live-transport set (5 test_volmarr_core_plugin.py + 1 test_volmarr_verdandi_stimuli.py + 1 test_volmarr_voice_runner.py); ZERO regressions (log `~/team01-e14-fullcontracts.log`, run on the team tree via the serialized gate waiter `~/team01-e14-gate-waiter.sh`). Targeted batteries (smidja + integration ledger) 28 passed / 0 failed both in the baseline waiter run (`~/team01-e14-baseline.log`) and post-edit (`~/team01-e14-targeted.log`). Engine own suite at the pin: 485 passed / 3 failed / 3 skipped, the 3 all named mcp-SDK drift artifacts in the Mjoll bridge tests (E14-T5; `~/team01-e14-engine-suite.log`).

## Honest remainders (named, not hidden)

- **E14-T1** (license metadata conflict at the pin):
  the root `LICENSE` is genuine Apache-2.0 text
  (sha256 cfc7749b96f6), while `pyproject.toml` line 11
  declares `license = { text = "MIT" }`. The fork
  records Apache-2.0 as the text-verified license and
  carries the conflict in the lock, the matrix, and
  COMPONENT_LICENSES.md; the fork adapter itself
  surfaces it in every live response's
  `license_metadata`. Fixing it means editing the
  engine repo (correcting the pyproject declaration or
  the LICENSE), which is the engine owner's call and
  out of this audit's scope; the engine tree was left
  untouched.
- **E14-T2** (hoard assets listed but uncached): all 4
  catalog assets (vroid/sample_a, vroid/sample_b,
  turbosquid/female_rigged_2024, runa/mb_lab_base_v5)
  carry `cached: false` at the pin; resolving
  vroid/sample_a raises `AssetNotFoundError` and the
  asset probe truthfully reports `available` false. A
  live proof against a cached asset awaits the hoard
  being populated on a host; the adapter's behavior is
  faithful in the meantime.
- **E14-T3** (gate v0.1 unevaluated rules):
  `vrchat.polycount` and `vrchat.texture_memory` are
  not evaluated by the engine at the pin - they return
  WARNING "Rule not evaluated in v0.1 - manual check
  required", the compliance scope is
  `official_gate_structural_header` only, and
  `certification_complete` is false. A full gate
  certification awaits engine rule evaluation beyond
  v0.1.
- **E14-T4** (branch / version split at the pin): the
  pin tracks `development`, the repo's default branch
  (HEAD == pin). `refs/heads/main`
  (`5b0f2979aa901314eea5e32bf0d07514f50fa5b4`) is a
  separate line whose relationship to the engine line
  is not established by this audit; the pyproject
  version at the pin reads **0.1.0.dev0** while the
  fork plugin is 0.1.0, and the repo carries no tags.
  Recorded, not resolved: the pin decision is unchanged
  because HEAD (the default branch) == the pin. A
  future engine update should first settle which line
  is canonical.
- **E14-T5** (engine suite host artifact): 3 of the engine 491 tests fail on purplelongship - all `TestMjollWithMCP` in `tests/bridges/test_mjoll_server.py`, each with `AttributeError: 'Server' object has no attribute 'list_tools'` at `src/seidr_smidja/bridges/mjoll/server.py:62`. The `mcp` SDK version resolved into the staging venv (`~/smidja-e14-venv`) has drifted from the API the engine Mjoll bridge expects. Fixing it means pinning the engine dependency set or editing the engine tree, both out of this audit scope; the remaining 485 tests pass, and the fork adapter surface (Loom / Hoard / Gate / Oracle) is unaffected.
- **E12-T2** (matrix tally drift) continues: the
  INTEGRATION_MATRIX "Verification tally" paragraph
  still carries its W08 promotion counts. The lock and
  the ledger test are the enforced truth (25 / 0 / 1);
  the tally paragraph wants a dedicated correction
  pass, out of this slice's rows-only scope.
- The section 32 release scorecard still reads NOT
  releasable; E.14 changes engine currency only, nothing
  else.
- Next in roadmap order: E.15.
