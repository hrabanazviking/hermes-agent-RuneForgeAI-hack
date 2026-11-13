# E.07 WYRD Protocol update — implementation record (Team 01, 2026-11-13)

**Outcome: PIN MOVED — all contract proofs pass, with one root-caused
environment finding in the engine's own suite (Proof 1).** The official
engine has moved past the pin (package v1.0.0 at the pin → package
v1.5.0 at development HEAD, 75 commits). The fork's surface is
unchanged: a read-only `/health` probe
(`MINIMUM_SERVER_VERSION 1.0.0`, contract `wyrd-http-v1`) plus bounded
world get/query and confirmed set/observe through the same contract.
No WYRD source was copied into the fork. This slice also discharges
the W08 ledger's license-text assignment for row 10: the repo's
CC BY 4.0 declaration is now verified at the text level (see License
below), so row 10 moves from partially verified to verified.

## Target (re-measured, not inherited)

- Pin (before this slice): `9884ce8a9e683dc20f372a91eb66ba5b02561300`
  (package v1.0.0) — COMPONENT_LICENSES.md, integration-lock.json,
  INTEGRATION_MATRIX row 10.
- Target: `89ed09394c7e13b2e63f91e342fbab8ff9890cbc` — HEAD +
  branches re-measured 2026-11-13 by `git ls-remote`: HEAD ==
  `development` at that SHA; `main` is `7df509e9140793d8b7bae91bb1d35c466be1d887`;
  the only tag/release is v1.0.0 at `f3dfb1a27c0a2a1d1821a3320d38238633778f8f`.
  The pin is an ancestor of the target; the delta is **75 commits**
  to development (73 to main), measured in the fresh clone directly
  under $HOME (`~/wyrd-e07`, HEAD `89ed09394c`, clean except the
  scratch live-proof harness `tests/test_e07_live.py`, which is
  evidence, not an upstream test). The package version at HEAD, read
  in `pyproject.toml` and `src/wyrdforge/__init__.py` and from the
  installed distribution in the target venv, is **1.5.0**.
- Environment: clean Python 3.13.13 venv in the clone
  (`~/wyrd-e07/.venv`, `uv pip install -e '.[dev]'`, log
  `~/team01-e07-install.log`); the package was installed FROM THE
  LOCAL CLONE (`wyrdforge==1.5.0 (from file:///home/volmarr/wyrd-e07)`).
  No PyPI pull of a different WYRD version anywhere in this slice.
- License: **CC BY 4.0 — PASS, verified at the text level this
  slice, with the shape of the text named exactly.** The repo carries
  NO standalone LICENSE file: `find` over the target tree and
  `git ls-tree` at the pin and at main all find none, which is why
  GitHub detected NONE. The in-repo license text is the README
  `## License` section (CC BY 4.0 statement with the Share / Adapt /
  Attribution terms) plus the `pyproject.toml` declaration
  `license = { text = "CC BY 4.0" }`. Both are byte-identical at the
  pin, at the target, and at main: README license section sha256
  `33d69b9d1ecb52a38df53591719d3b8a69fe41b919be005578d004ac1eaebc44`,
  pyproject license line sha256
  `3d39ac301615342997408c03e9d5d532c03bcd482516f5bcb40372970c558732`,
  read via `git show <ref>:<path>` in `~/wyrd-e07`. The license does
  not change across the pin move, and the fork ledger's CC BY 4.0
  claim is verified as declared.

## Proof 1 — WYRD's own suite at target: PASS with a root-caused environment finding

- Full suite in `~/wyrd-e07` at the target, in the target venv
  (`pytest -q`, testpaths `tests`, 100 files): **2,284 passed /
  1 failed / 14 skipped / 6 xfailed** in 99.15s (log
  `~/team01-e07-proof1.log`). The scratch E.07 harness did not exist
  yet during this run; it is not counted here.
- The one failure, root-caused: `tests/test_dusk_efficiency_b.py::
  test_slice3_kway_merge_benchmark` asserts the bus's attrgetter-key
  merge path beats the old lambda-key path on wall clock
  (`assert t_new < t_old`, min of 5 runs). It measured **0.99x** in
  the suite run and **0.96x / 0.97x / 0.96x / 0.93x** across four
  isolated reruns on a quiet machine (load 0.24; log
  `~/team01-e07-proof1-rerun.log` plus reruns) — the timing
  assumption does not hold for CPython 3.13.13 on this host. The
  test's correctness assertion (both paths produce identical
  ordering) passes; only the relative-speed inequality fails. The
  Dusk suite does not exist at the pin (no `tests/test_dusk_*` at
  `9884ce8a9e`; introduced 2026-10-11 in `0588006`, after the
  2026-09-17 pin), so this is not a regression against the pin, and
  it touches nothing in the fork's HTTP contract surface. It is
  named here as a remainder, not hidden and not rounded up to green.

## Proof 2 — live server at target answers the fork probe: PASS

- Harness `~/wyrd-e07/tests/test_e07_live.py` (scratch, kept in the
  engine clone as evidence): it boots the REAL target server
  (`WyrdHTTPServer` over a `PythonRPGBridge` world built with the
  engine's own test recipe — zone midgard / region fjords / location
  hall, entity `sigrid` placed in the hall, persistent memory store)
  on an ephemeral loopback port with no auth token, then runs the
  fork's real `probe_wyrd`, world tool handlers and telemetry chain
  from the team tree against it (Hermes-side `tools.registry` /
  `hermes_constants` are minimal stubs in the harness only; no fork
  or engine code was changed for this).
- Run: **1 passed** (log `~/team01-e07-live.log`; full result
  `~/team01-e07-live-result.json`, server at 127.0.0.1:43041 on the
  recorded run). Raw `/health` answers `{"status": "ok"}` — no
  version field, exactly as the adapter's contract anticipates. The
  fork probe reports healthy / healthy, `server_version` null
  against minimum 1.0.0, latency 5 ms.
- Combined run (same harness plus the upstream HTTP contract files
  `test_http_api_auth_versioning.py`, `test_phase19_api_contracts.py`,
  `test_exposure_probe.py`, `test_forge_bridge_contract.py`):
  **90 passed / 0 failed / 13 skipped** (log
  `~/team01-e07-combined.log`). First combined attempt, recorded
  honestly: 89 passed / 1 failed — the failure was the harness's own
  `tools` stub shadowing the engine repo's `tools/` package for a
  relay import inside `test_exposure_probe.py`; the fix was in the
  harness only (the stub's `__path__` now also carries the repo's
  tools directory), and the exposure probe alone is also clean
  (13 passed / 13 skipped).

## Proof 3 — live world get/query and confirmed writes at target: PASS

- In the same live harness (log `~/team01-e07-live.log`, full
  result `~/team01-e07-live-result.json`): the fork world
  snapshot answers success (world `probe_world`); the confirmed
  set writes the fact `sigrid.location = hall` (success, write
  `fact`); a following facts read returns exactly that fact
  from the canonical store; the world query for `sigrid`
  answers success with her focus at the hall and that fact in
  its canonical-facts section; the confirmed observe answers
  success (write `observation`). No fork or engine code was
  changed for this proof; the writes ran only against the
  harness world in the disposable engine clone.

## Proof 4 — fork contracts: PASS (baseline; gate run below)

- Before the pin move, on the unmodified team tree:
  `scripts/run_tests.sh` on `test_volmarr_wyrd.py`,
  `test_volmarr_world_bridge.py` and
  `test_volmarr_integration_ledger.py` = **3 files, 47 tests
  passed / 0 failed** (log `~/team01-e07-baseline.log`).
- After the pin move the same three batteries are the
  targeted run in the fork gate below.

## Proof 5 — absent server behaviour stays truthful: PASS

- Absent: in the same live harness, the fork probe against
  `http://127.0.0.1:9` (nothing listening) answers
  **healthy false, status unreachable, error_type URLError**,
  server_version null, and the world get answers the error
  `WYRD service is unreachable` (full result
  `~/team01-e07-live-result.json`). Nothing was installed or
  faked to produce this.

## Pin move and MINIMUM_SERVER_VERSION

- Pin moved in this slice: `9884ce8a9e683dc20f372a91eb66ba5b02561300`
  -> `89ed09394c7e13b2e63f91e342fbab8ff9890cbc` (package
  v1.5.0, development HEAD) in integration-lock.json (WYRD
  rowz `current_head` = `89ed09394c...`, `update_needed`
  false, verdict "current - E.07 executed", license now the
  verified CC BY 4.0 declaration), COMPONENT_LICENSES.md,
  INTEGRATION_MATRIX.md row 10 (verification moves from
  partially verified to verified), and the pin-guard
  assertions in `tests/plugins/test_volmarr_integration_ledger.py`
  (`engines show WYRD Protocol` pin assertion added, following
  the E.01-E.06 pattern; verified counts move 22 -> 23 and
  partially_verified 3 -> 2 because the WYRD license
  declaration is now verified at text level).
- `MINIMUM_SERVER_VERSION` stays **"1.0.0"**, unchanged in
  `plugins/volmarr-core/wyrd.py`: the pin records the verified
  current version, the minimum is the adapter accepted floor,
  and proof 2 shows the target answering the probe built for
  that floor - no proof gives a reason to raise it.
- No CUSTOMIZATIONS.md row: no adapter behaviour changed in
  this slice; a pin move is ledger state, already carried by
  the records above (E.03 / E.05 / E.06 precedent).
- README.md untouched (sha256
  `336813d11bbe5aa2ff745b4a4bc3abcf2a283cd13971c0c11d061377129db7f3`
  before and after).

## Honest remainders (named, not hidden)

- Proof 1 carries one root-caused environment finding: the
  Dusk kway-merge timing benchmark
  (`test_slice3_kway_merge_benchmark`) fails its relative-speed
  inequality on this host under CPython 3.13.13 (0.93x-0.99x
  across reruns, correctness assertion passes). The Dusk suite
  does not exist at the pin, so this is not a regression
  against the pin, and it touches nothing in the fork HTTP
  contract surface. It is named here as remainder E07-T1, not
  hidden and not rounded up to green.
- The section 32 release scorecard still reads NOT
  releasable; E.07 changes engine currency only, nothing else.
- Next in roadmap order: E.08.

## Fork gate — full contract set on this tree: PASS

- Targeted batteries after the pin move (`test_volmarr_wyrd.py`,
  `test_volmarr_world_bridge.py`,
  `test_volmarr_integration_ledger.py`): **3 files, 47 tests
  passed / 0 failed** - the ledger battery carries the new
  WYRD pin-guard assertion and the verified-count move
  (23 verified / 2 partially verified) (log
  `~/team01-e07-targeted.log`).
- Full contract set via `scripts/run_tests.sh`
  (`tests/plugins/test_volmarr_*.py` + `tests/plugins/test_kista_*.py`)
  on this tree: **137 files = 1,171 passed / 7 failed /
  1 skipped** - the 7 failures are exactly the known
  live-transport set (5x test_volmarr_core_plugin.py, 1x
  test_volmarr_verdandi_stimuli.py, 1x
  test_volmarr_voice_runner.py), name-identical to the banked
  baseline; zero regressions (log
  `~/team01-e07-fullcontracts.log`; gate start 18:11:50 EST,
  load at launch 1.49 / 6.34 / 6.67 recorded in that log).
- README sha256 unchanged before and after (`336813d11bbe...`).
  Worktree banking is the keeper step that follows this record.
