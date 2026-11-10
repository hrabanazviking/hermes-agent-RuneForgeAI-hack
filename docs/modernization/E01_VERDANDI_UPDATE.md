# E.01 Verdandi update — implementation record (Team 09, 2026-11-09)

**Outcome: PIN NOT MOVED — blocked at proof 1 of 5.** Verdandi's own
suite is not green in a clean environment at the target commit (one
non-isolated test, root-caused below). Under the E.01 gate ("only if
all five pass may the pin move") and the commission's instruction to
stop the pin move when the engine's own suite is not green, no pin
was moved and no engine code was touched. Proofs 2–5 were still run
and all pass; the live protocol surface the fork integrates with is
proven end to end. The blocker needs Volmarr's word: either rule the
single peripheral test defect acceptable for E.01, or commission the
engine-side test fix inside the Verdandi project first (ticket
E01-T1 below). This record is the only commit of this slice.

## Target (re-measured, not inherited)

- Pin (unchanged): `dc7139416ef4bb67c9ba29c1148615d0d259b7db`
  (COMPONENT_LICENSES.md, integration-lock.json, INTEGRATION_MATRIX row 1).
- Current HEAD re-measured 2026-11-09 ~21:05 EST by
  `git ls-remote https://github.com/hrabanazviking/Verdandi HEAD`:
  `2fc9db8bf555546ab96084f74b1d442b8e1c7a63` — identical to the W08
  lock measurement; the engine has not moved. Target = that commit.
- Delta verified in the cloned tree (`~/verdandi-e01`, directly under
  $HOME): `git rev-list --count dc713941..2fc9db8b` = **67 commits**,
  matching the W08 audit. Delta character (from the audit, confirmed
  in the log): nerve-hub hardening (over-limit structured rejects,
  subscriber keepalive, SIGTERM graceful shutdown, supervisor +
  PID-reuse-safe health), state honesty, CLI exit-2 domain errors,
  mood integration keys, Telegram bridge, WYRD mirror stack.
- License: MIT (pyproject `license = {text = "MIT"}`, LICENSE file in
  tree at target) — unchanged from the pinned record.

## Proof 1 — Verdandi's own suite at target: FAIL (1 test)

Run in its own tree at 2fc9db8b, venv with pytest 9.2.0 +
pytest-asyncio 1.4.1 + PyYAML 6.0.3 (the tree declares no runtime
deps; `yaml` is its only third-party import), disposable HOME
`~/team09-e01-home`, after other campaigns cleared (resource law).
Log: `~/team09-e01-verdandi-suite.log`.

**Result: 1,064 passed / 1 failed / 4 skipped in 52.29s.**

The one failure: `tests/test_context_injector.py::
TestContextGeneration::test_context_with_nerve_feed`.

Root cause (engine-side test-isolation defect, proven three ways):

- The code under test, `conversation_logger.py:540`
  (`get_context_for_cron`), reads the nerve feed from
  `Path.home() / ".hermes" / "state" / "nerve_feed.jsonl"` — the
  ambient home, not the module's `STATE_DIR`.
- The test's `isolate_paths` fixture patches `conversation_logger`'s
  STATE_DIR/CONV_DIR/CURRENT_FILE/CONV_LOG into a tmp dir and writes
  its five fixture events to the tmp feed — but never patches
  `Path.home()`, so the code never sees the fixture events.
- Pristine disposable HOME, single file: **1 failed, 17 passed**
  (reproduced). Same file after the full suite ran (later tests had
  created a real feed in the disposable HOME): **18 passed** — the
  test passes only by reading leftover ambient state, i.e. its
  result depends on test order and machine state. On a machine where
  Runa runs and a real feed exists it passes spuriously; in any
  clean environment it fails deterministically.
- The failing surface is peripheral to this fork's integration:
  context injection for cron sessions. Every nerve-hub test
  (`test_nervous_system.py`, `test_dawn_s3_nervous.py`, heartbeat
  suites) passed. No fix was attempted here: the engine's code stays
  in its own project (ticket E01-T1).

## Proof 2 — fork contract batteries: PASS (baseline-identical)

`scripts/run_tests.sh` (never bare pytest) on the team-09 tree at
banked main 773f34c5bc, log `~/team09-e01-batteries.log`:

| File | Tests | Result |
|---|---|---|
| test_volmarr_verdandi_stimuli.py | 3 | 2 passed, 1 failed (baseline name) |
| test_volmarr_verdandi_events.py | 7 | 7 passed |
| test_volmarr_core_plugin.py | 6 | 1 passed, 5 failed (baseline names) |
| test_volmarr_integration_ledger.py | 17 | 17 passed |

The 6 failures are name-identical to the banked baseline's
live-transport set in these files (5 core-plugin + 1 stimuli); the
7th baseline failure (voice runner) is outside this battery. Zero
new failures. Note, stated plainly: these batteries exercise the
fork's publisher/client code against protocol-faithful in-process
responders; the against-the-real-hub requirement is discharged by
proofs 3–5 below, which run the fork's real code against the real
hub binary from the target tree.

## Proof 3 — live socket round-trip (disposable profile): PASS

Hub: `nervous_system.py serve` from `~/verdandi-e01` at target,
disposable HOME `~/team09-e01-hubhome` (socket
`.hermes/state/runa.sock`). Fork side: the tree's own
`LifecycleBridge`, `VerdandiPublisher`, `probe_verdandi`,
`VerdandiRecentClient` loaded from the team-09 checkout — live
callers, no stubs. Script `~/team09-e01-live.py`, log
`~/team09-e01-live.log`, results `~/team09-e01-live-results.json`.

- Health: fork probe → healthy, seq 0, uptime 0.6s, latency 2 ms.
- Publish round-trip: session.started / tool.started / tool.failed /
  session.ended via the bridge + one direct publish all landed in
  the hub ring buffer in order (total 5, `_seq` monotone), envelope
  `runeforge.hermes.lifecycle` v1, source stamped.
- Over-limit reject: a 1 MiB+ frame drew the structured reply
  `{"nerve_type":"error","reason":"message_too_large"}` and the hub
  kept serving (pong, seq 5, immediately after).
- Stimuli catch-up: two raw `runa_reward` publishes read back via
  the fork's recent client (`_seq` 6, 7); a third publish was the
  single new event past the cursor (`_seq` 8) and mapped through
  `map_stimulus` to `response_completed`.

## Proof 4 — absent-service fail-open: PASS

After graceful hub stop (SIGTERM, exit 0, socket removed), with the
hub absent: fork publisher returns False (no raise), recent client
returns None, health probe reports `unreachable`
(FileNotFoundError) — absence is never confused with silence-as-data
— and `LifecycleBridge.on_session_start` completes without raising.

## Proof 5 — latency + metadata-only privacy (§13 step 7): PASS

- Privacy: the bridge was driven with tool args/result/error fields
  carrying a secret marker string; the hub's persisted feed
  (`nerve_feed.jsonl` in the disposable home) was then read whole:
  the marker appears nowhere, and every published `hermes.*`
  envelope's context keys are within the metadata allowlist
  (ids, tool name, duration, status, error type, model, platform,
  completed, exit reason) with the v1 lifecycle schema throughout.
- Latency (same run, laptop under shared load): health ping via the
  fork probe, n=30 — all sub-millisecond (probe reports integer ms:
  min/avg/max 0/0.0/0 ms; first cold probe 2 ms). Publish via the
  fork publisher, n=20 — min 0.11 ms, avg 0.12 ms, max 0.16 ms.

## Pin move: NOT MADE

Unchanged, verified on disk after the run: integration-lock.json
Verdandi row (pinned dc713941…, verdict "update — E.01"),
COMPONENT_LICENSES.md line 10, INTEGRATION_MATRIX.md row 1, and the
pin-guard assertion in test_volmarr_integration_ledger.py.
`hermes volmarr engines validate` surface is covered by the 17/17
ledger battery above on the unchanged lock. No CUSTOMIZATIONS.md
row: no intentional difference arose. README.md untouched (sha256
336813d11bbe5aa2ff745b4a4bc3abcf2a283cd13971c0c11d061377129db7f3).

Full contract set: not run — this slice changed no fork code or
governing record, so there is no regression surface beyond the
batteries above; the banked baseline (137 files = 1,171 passed /
7 failed / 1 skipped) stands as the tree's state, with the team-09
tree byte-identical to banked main apart from this record.

## Ticket E01-T1 (for Volmarr's word; engine project, not this fork)

Verdandi repo: make `test_context_with_nerve_feed` isolated —
either `conversation_logger.get_context_for_cron` reads the nerve
feed from the module `STATE_DIR` (consistent with its other paths),
or the test patches `Path.home()`. Until then the engine suite
cannot go green in a clean environment, and E.01's gate cannot be
satisfied as written. If Volmarr rules the defect acceptable for
E.01 (peripheral surface; hub protocol fully live-proven here), the
pin move itself is a small, fully prepared step: lock row +
COMPONENT_LICENSES + matrix row + pin-guard test, then engines
validate + full contracts at zero regressions.

## Execution — Volmarr ruling 2026-11-10 03:29 EST (ticket E01-T1 resolved)

Volmarr ruled: MOVE THE PIN NOW AND FIX THE TEST ALONGSIDE. Executed
2026-11-10 by the keeper:

- Pin moved in this banking: integration-lock.json Verdandi row,
  COMPONENT_LICENSES.md line 10, INTEGRATION_MATRIX.md row 1, and the
  pin-guard assertion in tests/plugins/test_volmarr_integration_ledger.py
  now read 2fc9db8bf555546ab96084f74b1d442b8e1c7a63; lock update_needed
  is false and the verdict reads current — E.01 executed.
- Verdandi-side fix (its own repo, hrabanazviking/Verdandi):
  conversation_logger.get_context_for_cron read the nerve feed from
  Path.home() and inserted Path.home() state dir for the reactor import;
  both now read from the module STATE_DIR, consistent with every other
  path in the module. The test fixture already isolates STATE_DIR, so
  the test is hermetic. Single-file check in a pristine disposable HOME:
  tests/test_context_injector.py 18 passed (previously 1 failed /
  17 passed). Fix banked in the Verdandi repo: commit
  3140de1095daf3d230336906b203b64fb6aa7c3d on main (explicit refspec
  push, ls-remote verified). Full Verdandi suite at that commit in a
  pristine disposable HOME: 1,065 passed / 0 failed / 4 skipped
  (log ~/team09-e01-verdandi-suite-fixed.log) - proof 1 now PASSES.
  Full fork contracts on the pin-moved tree: 137 files = 1,171 passed
  / 7 failed / 1 skipped, the 7 name-identical to the known
  live-transport set - zero regressions (log
  ~/team09-e01-contracts.log). Counts also recorded in the banking
  closure in CAMPAIGN_STATE_MODERNIZATION.md.
- Waiter note: the first suite waiter deadlocked on its own launcher
  (the launching shell's command line carried the pgrep patterns - the
  W13-recorded failure class); the launcher was killed, the waiter
  reparented and fired in the first clear window. No other campaign's
  work was touched.
- Proofs 2-5 from the blocked record above stand unchanged (they ran
  against the real hub binary from the target tree). No fork adapter
  code changed; README.md untouched.
