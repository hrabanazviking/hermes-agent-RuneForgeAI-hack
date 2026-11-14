# E.09 Astrology Engine update — implementation record (Team 01, 2026-11-13)

**Outcome: PIN MOVED — all proofs pass, with two engine behaviour
changes named as tickets (a fail-closed timezone resolution and a
new known-birth-time requirement for predict and geoastrology).**
The fork surface is unchanged: the `volmarr-astrology 0.7.0` plugin,
a deterministic tool running fixed-argv bounded subprocess calls
against a local engine checkout. No Astrology Engine source was
copied into the fork.

## Target (re-measured, not inherited)

- Pin (before this slice): `1709fcfc1e00198ab0f25fe4889868a7245cf014`
  — COMPONENT_LICENSES.md, integration-lock.json, INTEGRATION_MATRIX
  row 12.
- Target: `bb4ede4fbb326d21df34a5ca0ca6e343f4f49fbe` — the lock had
  already recorded this SHA as `current_head` (measured 2026-11-08);
  the fresh clone directly under $HOME (`~/astrology-e09`, HEAD
  `bb4ede4f`) confirms it, and the pin is an ancestor of the target.
  A second clone at the pin lives at `~/astrology-e09-pin`.
- Delta shape: **149 commits, 277 files changed, +84,016 / −1,075**
  (log `~/team01-e09-delta.log`). This is a major engine expansion,
  not a patch: the commit subjects show new subsystems (cartomancy,
  Lenormand, Jaimini, Ashtakavarga, Shadbala, a yoga engine, the
  Oracles set O01–O06, extended vargas, daily forecast and remedial
  mantras, a self-healing pass) with a large new engine test tree.
  The fork only consumes the documented fixed-argv surface
  (lunar, planet-hours, natal, transit, predict, synastry,
  geoastrology), and that surface is exercised live in Proof 3.
- Package version at target: **4.0.0** — read in `pyproject.toml`
  (`version = "4.0.0"`) in the target clone.
- License: **Apache-2.0 — PASS, verified at the text level this
  slice.** `LICENSE` is byte-identical at pin and target (sha256
  `cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30`,
  Apache License Version 2.0, January 2004), verified by diffing
  `git show <pin>:LICENSE` against the target tree on disk.

## Proof 1 — the engine suite at target: PASS staged (634 / 0)

- First run, unstaged (log `~/team01-e09-proof1-main.log`):
  **598 passed / 5 failed** plus collection errors — every failure
  is a FileNotFoundError for a hardcoded data path from another
  machine (`/home/hatch/workspace/astrology-engine/data/runic.json`).
  A staging artifact, not an engine defect.
- Staged run, with the tree staged under $HOME the way the suite
  expects (log `~/team01-e09-proof1-staged.log`): **634 passed /
  0 failed** in 112.22s, suite_exit=0.

## Proof 2 — fork astrology contracts before the pin move: PASS

- `scripts/run_tests.sh` on `test_volmarr_astrology.py` and
  `test_volmarr_integration_ledger.py` on the unmodified team tree:
  **2 files, 37 tests passed / 0 failed** (astrology 20, ledger 17;
  log `~/team01-e09-baseline.log`).

## Proof 3 — live adapter calls against the target engine: PASS

- Harness `~/team01-e09-live.py` (log `~/team01-e09-live.log`,
  full result `~/team01-e09-live-result.json`) drives the fork
  adapter handlers in `plugins/volmarr-astrology/tools.py` against
  the real target engine (`~/astrology-e09/astrology_engine.py`)
  in a dedicated live venv. Every call was run twice and the two
  reports asserted byte-identical (determinism check).
- natal (2000-01-01 12:00, Stockholm 59.3293 / 18.0686): success,
  report sha256 `d5819ccd7f0204ad950ebe5a77c512317531972585a48d6ef0401a4f2a00f11a`.
- planetary hours (2026-05-03, Indianapolis 39.7684 / −86.1581):
  success, report sha256 `308f2e2f790dc405d189206d97c13dbb616b3a79b60248c6cfb6f57bf7072eb5`.
- predict (natal 2000-01-01 12:00, window 2026-05-01 → 2026-06-01,
  Stockholm): success, report sha256 `6d0c63e0a89d82e67f712625ef51fd5b9f89d575a88866833000b71302500ec1`.
- geoastrology (same natal data, query at the natal coordinates):
  success, report sha256 `92a0da929522b1d9eebec0bd97bea172abcfbfd4133fe74691751bf26dbfbc7a`.
  The report header shows the engine resolving the zone from the
  coordinates: 12:00 LT → 11:00 UTC (UTC+01:00 Europe/Stockholm).
- lunar (no arguments): success, report sha256
  `3ce9faf7d44eab683575b832060cce0ca225c77cdd51d45e442ecf523416c294`.

## Proof 4 — fork targeted batteries after the pin move: PASS

- Same two batteries as Proof 2, after the pin move:
  **2 files, 37 tests passed / 0 failed** (log
  `~/team01-e09-targeted.log`) — the ledger battery now carries
  the new pin-guard assertion (`engines show Astrology Engine`
  pinned == `bb4ede4fbb326d21df34a5ca0ca6e343f4f49fbe`). Counts
  identical to the pre-move baseline.

## Proof 5 — absent-engine probes fail truthfully: PASS

- In the same live harness (result JSON above): with the engine
  path pointed at a nonexistent checkout, both the natal and the
  lunar handlers return the truthful configuration error
  (Configure volmarr-astrology engine_path and a Python
  interpreter with pyswisseph installed). Nothing was installed
  or faked to produce these.

## Timezone and birth-time findings (judged, not worked around)

An argv matrix run during this slice (log
`~/team01-e09-argv-matrix.log`, 20:40 EST) showed every timed
command failing at the target with rc=2 and the message
Timezone unresolved; supply --timezone with an IANA zone or
explicit UTC, while the same matrix at the pin returned rc=0
throughout. Judged from the code and re-probed under controlled
conditions, the finding has three parts:

- **The matrix failures were an environment artifact.** The
  matrix ran against the engine venv `~/astrology-e09/.venv-e09`
  before its geo dependencies finished installing: the install
  log (`~/team01-e09-geo-install.log`, 20:41 EST) records
  timezonefinder 9.2.0 and geopy 2.5.0 landing one minute after
  the matrix ran. The post-install matrix (log
  `~/team01-e09-argv-target-geo.log`, 20:43 EST) returns rc=0
  for natal, transit, synastry, predict with a time, and
  geoastrology with a time — with no explicit `--timezone`
  anywhere. The live proof (Proof 3) passes for the same reason.
- **The adapter is not the bug.** `plugins/volmarr-astrology/
  tools.py` has no timezone parameter in any tool schema and
  never passes `--timezone`; by design it delegates zone
  resolution to the engine, which resolves the IANA zone from
  the coordinates via timezonefinder (`resolve_timezone` in the
  engine). There is nothing in the adapter to fix, and no
  workaround was added in core or in the adapter.
- **The engine did change behaviour — fail-closed.** At the pin,
  `resolve_birth` fell back to treating local time as UTC when
  no zone resolved. At the target it raises CalculationError
  instead. So an engine Python without timezonefinder now fails
  every timed chart where the pin silently degraded. With the
  documented engine environment installed, all live paths pass.
  Named as remainder **E09-T1** (a deployment requirement, not
  an adapter defect).
- **A second, separate change: predict and geoastrology now
  require a known birth time.** Controlled re-probe this tick
  with the geo dependencies installed: target natal without a
  time rc=0; target predict without a time rc=2 (predict
  requires a known birth time; supply --time); target
  geoastrology without a time rc=2 (same shape); the pin
  returns rc=0 for both without a time. The adapter schemas
  still mark the time optional for predict (natal_time) and
  astrocartography (time), so a caller omitting it now receives
  a failure where the pin produced a report. Named as remainder
  **E09-T2** — the adapter schema decision (require the time
  for these two tools, matching the engine) belongs to a future
  slice; it is recorded here, not silently worked around.

## Pin move

- Pin moved in this slice: `1709fcfc1e00198ab0f25fe4889868a7245cf014`
  -> `bb4ede4fbb326d21df34a5ca0ca6e343f4f49fbe` (package v4.0.0)
  in integration-lock.json (Astrology Engine row: `pinned` =
  `current_head` = `bb4ede4f...`, `update_needed` false, verdict
  current — E.09 executed), COMPONENT_LICENSES.md,
  INTEGRATION_MATRIX.md row 12, and the pin-guard assertion in
  `tests/plugins/test_volmarr_integration_ledger.py` (`engines
  show Astrology Engine` assertion added, following the E.05–E.08
  pattern). The keeper verified the lock diff touches only the
  Astrology row.
- The Astrology verification status was already `verified` and
  stays `verified` — the ledger counts do not move (23 verified /
  2 partially verified / 1 blocked).
- No adapter change: no fork code was modified in this slice;
  the two engine behaviour changes above are recorded as
  tickets, not adapted to silently.
- No CUSTOMIZATIONS.md row: no adapter behaviour changed in
  this slice; a pin move is ledger state (E.03 / E.05–E.08
  precedent).
- `docs/modernization/ADAPTER_COMPATIBILITY_MATRIX.md` still
  shows the W08-era pin for Astrology: a dated audit snapshot
  that no E.05–E.08 slice updated, left untouched here for the
  same reason.
- README.md untouched (sha256
  `336813d11bbe5aa2ff745b4a4bc3abcf2a283cd13971c0c11d061377129db7f3`
  before and after).

## Gate evidence — full fork contracts

- Full fork contracts on the pin-moved team tree via
  scripts/run_tests.sh = 137 files, 1,171 passed / 7 failed /
  1 skipped - exactly the banked baseline, the 7 name-identical
  to the known live-transport set (5 core-plugin + 1 Verdandi
  stimuli + 1 voice runner); ZERO regressions (log
  ~/team01-e09-fullcontracts.log, finished 22:05 EST, 2026-11-13).
  The keeper completed this section at banking from the log,
  the E.07 precedent.

## Honest remainders (named, not hidden)

- **E09-T1** (engine behaviour change + deployment requirement):
  timezone resolution is fail-closed at the target. The engine
  Python must carry timezonefinder (and geopy for city lookup);
  without it, timed charts fail with Timezone unresolved where
  the pin silently treated local time as UTC. The adapter
  generic failure text does not surface the engine reason (the
  adapter returns its generic calculation-failure message on
  any nonzero engine exit — pre-existing adapter wording,
  unchanged by this slice).
- **E09-T2** (engine behaviour change, adapter decision owed):
  predict and geoastrology require a known birth time at the
  target; the adapter schemas still present the time as
  optional for both tools. A future slice should align the
  schemas with the engine contract.
- **E09-T3** (proof environment note): the ephemeris file
  `seas_18.se1` is absent in the proof environments, so the
  engine omits optional bodies (Chiron, Ceres, Pallas) with a
  warning while core calculations succeed (visible in
  `~/team01-e09-argv-target-geo.log` and the live reports).
- The section 32 release scorecard still reads NOT releasable;
  E.09 changes engine currency only, nothing else.
- Next in roadmap order: E.10.

