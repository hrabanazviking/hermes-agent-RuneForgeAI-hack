# E.06 OpenViking (official) update — implementation record (Team 01, 2026-11-13)

**Outcome: PIN MOVED — all five proofs pass.** The official
engine has moved past the pin (v0.4.21 → v0.5.6.dev26 at HEAD,
26 commits past tag v0.5.5). The fork's surface is unchanged
and probe-only / read-only: an anonymous loopback `/health`
protocol attestation (`MINIMUM_SERVER_VERSION 0.4.21`) plus an
opt-in memories-only `/find` retrieval bridge. No OpenViking
source was copied into the fork; the existing Hermes provider
is reused. This slice also discharges the W08 ledger's
license-text assignment for row 9: the Volmarr mirror's
Apache-2.0 LICENSE text is now verified at the text level
(see License below), so the mirror row moves from partially
verified to verified (license text) and stays reference-only
with no pin taken.

## Target (re-measured, not inherited)

- Pin (before this slice): `3fca2577520f00b7f580d85d4ac6ae42bb9ba6f1`
  (v0.4.21) — COMPONENT_LICENSES.md, integration-lock.json,
  INTEGRATION_MATRIX row 8.
- Target: `90f4edcede4c6a665fccb747417ebe6c1db56f4d` —
  HEAD + tags re-measured 2026-11-13 by `git ls-remote`
  (latest tag v0.5.5; HEAD is 26 commits past it) and in the
  fresh clone directly under $HOME (`~/openviking-e06`,
  HEAD `90f4edce`, clean except the scratch live-proof test
  `tests/server/test_e06_live.py`, which is evidence, not an
  upstream test). The package version at HEAD, read from the
  installed package in the target venv, is **0.5.6.dev26**.
- Delta in the clone: `git log 3fca2577..90f4edce` =
  **866 commits**.
- Environment: clean Python 3.13 venv in the clone
  (`~/openviking-e06/.venv`, uv sync, 217 packages; log
  `~/team01-e06-uvsync.log`); the native vectordb runtime was
  built in place (ENGINE_VARIANT x86_avx2, with sse3/avx512
  targets also built; log `~/team01-e06-build.log`) and the
  package installed FROM THE LOCAL CLONE
  (`openviking==0.5.6.dev26 (from file:///home/volmarr/openviking-e06)`;
  log `~/team01-e06-install.log`). No PyPI pull of a different
  OpenViking version anywhere in this slice.
- Mirror row is NOT part of this pin move:
  `hrabanazviking/OpenViking` HEAD re-measured =
  `cbf8befcea5736f3b316a6c12e84ba11c40b31c4`, unchanged; it
  stays reference-only and unpinned, exactly as before.
- License: AGPL-3.0 — PASS, verified at the text level this
  slice: `LICENSE` at the pin and at the target are
  byte-identical (sha256 of both, read via
  `git show <commit>:LICENSE` in `~/openviking-e06`:
  `1bd87fa6d9a5c79daf0c2af042b6725c9773bf095cc3d1bdf3656e66d1c3e5b1`).
  The license does not change across the pin move.
  Mirror license — VERIFIED this slice (the lock's E.06
  assignment): in a fresh clone `~/openviking-mirror-e06` at
  `cbf8befcea57`, the mirror `LICENSE` is the genuine
  Apache-2.0 text (sha256
  `43070e2d4e532684de521b885f385d0841030efa2b1a20bafb76133a5e1379c1`),
  which genuinely differs from the official repo's AGPL-3.0.
  Both hashes were re-verified by the continuation lead from
  the on-disk trees before banking.

## Proof 1 — OpenViking's own suites at target: PASS

- Two suite runs in `~/openviking-e06` at the target, in the
  target venv: **112 passed / 0 failed** in 8.15s
  (log `~/team01-e06-proof1-lite.log`) and **124 passed /
  0 failed** in 36.06s (log `~/team01-e06-proof1-extra.log`).
  The logs record counts and warnings only (deprecation
  warnings from upstream dependencies; no failures), not the
  suite selections, and this record does not invent them.
- The live-proof harness file `tests/server/test_e06_live.py`
  in the clone is a scratch E.06 harness, not an upstream
  test; its runs are proof 2, not proof 1.

## Proof 2 — live server at target answers the fork contracts: PASS

- Harness `~/openviking-e06/tests/server/test_e06_live.py`
  (scratch, kept in the engine clone as evidence): it boots
  the REAL target server (dev auth) on an ephemeral loopback
  port, then runs the fork's real `probe_openviking` and
  `OpenVikingRetrievalBridge` from the team tree against it.
- First attempt, recorded honestly: **27 passed / 1 failed**
  (log `~/team01-e06-proof2-live.log`) — the one failure was
  the live test itself: the server's MCP lifespan prevented
  `/health` from answering in the harness. The harness fix
  was to no-op the MCP lifespan in the test only
  (`mcp_lifespan` monkeypatch); no engine or fork code was
  changed for this.
- Re-run after the harness fix: **1 passed** (log
  `~/team01-e06-live2.log`), and the combined server run is
  **28 passed / 0 failed** in 29.66s (log
  `~/team01-e06-proof2-combined.log`).
- Live result (log `~/team01-e06-live-result.json`, server at
  127.0.0.1:60765): `/health` answers status ok, healthy
  true, version **0.5.6.dev26**, auth_mode dev; the fork
  probe reports healthy / healthy, server_version
  0.5.6.dev26 against minimum 0.4.21, latency 3 ms.

## Proof 3 — read-only /find retrieval at target: PASS

- Against the same live target server, `POST
  /api/v1/search/find` (query "JWT authentication tokens",
  memories only) answers 200 / status ok with 1 memory, and
  the fork bridge returns exactly that 1 item in
  `relevant_episodes`: the memories `.abstract.md` abstract
  ("User's long-term memory storage. Contains memory types
  like preferences, entities, events, managed hierarchically
  by type."), source `openviking/memories`, score 1.0
  (log `~/team01-e06-live-result.json`).

## Proof 4 — fork contracts: PASS (baseline; gate run below)

- Before the pin move, on the unmodified team tree:
  `scripts/run_tests.sh` on `test_volmarr_openviking.py`,
  `test_volmarr_openviking_retrieval.py` and
  `test_volmarr_integration_ledger.py` = **3 files, 29 tests
  passed / 0 failed** (4 + 8 + 17;
  log `~/team01-e06-baseline.log`).
- After the pin move the same batteries plus the full
  contract set are the fork gate, recorded at the end of
  this file.

## Proof 5 — absent server behaviour stays truthful: PASS

- Absent: in the same live harness, the fork probe against
  `http://127.0.0.1:9` (nothing listening) answers
  **healthy false, status unreachable, error_type URLError**,
  server_version null (log `~/team01-e06-live-result.json`).
  Nothing was installed or faked to produce this.
- Outdated: the fork contract tests covering a server below
  the 0.4.21 floor pass inside proof 4's baseline run and
  the gate run below; the floor itself is unchanged.

## Pin move and MINIMUM_SERVER_VERSION

- Pin moved in this slice: `3fca2577520f00b7f580d85d4ac6ae42bb9ba6f1`
  → `90f4edcede4c6a665fccb747417ebe6c1db56f4d` (v0.5.6.dev26)
  in integration-lock.json (OpenViking row: `current_head` =
  `90f4edcede…`, `latest_tag` v0.5.5, `update_needed` false,
  verdict "current — E.06 executed"; mirror row:
  `update_needed` false, license now "Apache-2.0 (LICENSE
  text verified in E.06)"), COMPONENT_LICENSES.md,
  INTEGRATION_MATRIX.md rows 8–9 (and row 9 removed from the
  §-list of unverified license texts), and the pin-guard
  assertions in `tests/plugins/test_volmarr_integration_ledger.py`
  (`engines show OpenViking` pin assertion added, following
  the E.01–E.05 pattern; verified counts move 21 → 22 and
  partially_verified 4 → 3 because the mirror license text
  is now verified).
- `MINIMUM_SERVER_VERSION` stays **"0.4.21"**, unchanged in
  `plugins/volmarr-core/openviking.py`: the pin records the
  verified current version, the minimum is the adapter's
  accepted floor, and proof 2 shows the target answering
  the probe built for that floor — no proof gives a reason
  to raise it.
- No CUSTOMIZATIONS.md row: no adapter behaviour changed in
  this slice; a pin move is ledger state, already carried by
  the records above (E.03 / E.05 precedent).
- README.md untouched (sha256
  `336813d11bbe5aa2ff745b4a4bc3abcf2a283cd13971c0c11d061377129db7f3`
  before and after).

## Honest remainders (named, not hidden)

- Proof 1's logs do not name the two suite selections (see
  Proof 1); the counts stand as recorded in the logs, and
  the live proofs (2, 3, 5) plus the fork gate below are
  the load-bearing evidence for this pin move.
- The first live attempt failed on the harness's MCP
  lifespan handling (proof 2); the fix lives only in the
  scratch harness in the engine clone, which is evidence,
  not shipped code.
- The §32 release scorecard still reads NOT releasable;
  E.06 changes engine currency only, nothing else.
- Next in roadmap order: E.07 (WYRD Protocol update).

## Fork gate — full contract set on this tree: PASS

- Targeted batteries after the pin move (`test_volmarr_openviking.py`,
  `test_volmarr_openviking_retrieval.py`,
  `test_volmarr_integration_ledger.py`): **3 files, 29 tests
  passed / 0 failed** — the ledger battery carries the new
  `engines show OpenViking` pin-guard assertion and the
  verified-count move (22 verified / 3 partially verified).
- Full contract set via `scripts/run_tests.sh`
  (`tests/plugins/test_volmarr_*.py` + `tests/plugins/test_kista_*.py`)
  on this tree: **137 files = 1,171 passed / 7 failed /
  1 skipped** — the 7 failures are exactly the known
  live-transport set (5x test_volmarr_core_plugin.py, 1x
  test_volmarr_verdandi_stimuli.py, 1x
  test_volmarr_voice_runner.py), name-identical to the banked
  baseline; zero regressions (log
  `~/team01-e06-fullcontracts.log`, which also carries the
  targeted run above; the runner's exit 1 is those 7 named
  failures, as in every prior slice's gate log). Scheduling
  note, honestly recorded: the gate launched at 17:28 EST
  after the Samverk team-08 suite then running on the shared
  laptop finished; load average at launch was 3.45 and its
  counts are baseline-exact.
- Worktree clean at the end; README sha256 unchanged before
  and after (`336813d11bbe…`).
