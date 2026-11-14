# X.01 Yggdrasil Distributed Inference System - ecosystem workstream 1 of 15 (Team 01, 2026-11-14)

**Outcome: AUDIT EXECUTED + REGISTRY ROW ADDED + LOCAL-HOST
PROTOTYPE BUILT. NO PIN TAKEN, NO EXISTING PIN MOVED, NO MESH
CLAIMED.** Roadmap Part VII section 36, first of the fifteen
ecosystem workstreams, taken in roadmap order after the W08
ledger E.01-E.18 closed. The fork gains, plugin-side in
volmarr-core: versioned Yggdrasil envelopes, a read-only
local-host discovery prototype, and pure local placement
records behind `hermes volmarr yggdrasil {status|discover|place}`.
Section 36 deliverable 10 governs the claim level: host-to-host
live proof does not exist, so nothing here is promoted past
"contract implemented".

## Audit (deliverable 1 - re-measured, not inherited)

- Source: `hrabanazviking/Yggdrasil-Distributed-Inference-System`,
  branch `main`. `git ls-remote` 2026-11-14: HEAD ==
  `refs/heads/main` == `1af750f1ad2fb7b3f39776f7cefb56a68359772a`;
  **no tags**. Tree cloned under $HOME at `~/yggdrasil-audit`,
  HEAD verified, working tree clean. No repository was created.
- README self-describes **Design Phase**, Version 3.1 "Advanced
  Formal Specification". That label is now stale in the
  conservative direction: the tree carries REAL executable code,
  not only pseudocode/proposals:
  - `src/yggdrasil/` - 64 Python modules, ~35,757 LOC total,
    including `node_agent.py` (identity-verified lifecycle +
    lease gates), `discovery.py` (DiscoveryService +
    SimulatedLan), `registry_service.py`, `gossip.py`,
    `lan_fabric.py`, `tls_channels.py`, `crdt_stores.py`,
    `task_channel.py` / `task_security.py`, `census.py`,
    `aesir_adapter.py` / `ollama_adapter.py` /
    `openai_compat_adapter.py` (model adapters), `cli.py`,
    `__main__.py`, plus `deploy/yggdrasil-node.service`
    (a systemd unit pointing at the node agent).
  - `tests/` - 64 test files mirroring the modules;
    `contracts/schemas/` - ~190 versioned JSON schemas
    (task_envelope, queued_task, discovery_*, registry,
    capability census, and per-slice policy/record/report
    triples).
  - Its own CAMPAIGN_STATE.md: campaign "The Growing of the
    Tree", 72/244 slices banked, Parts I-II COMPLETE, suite
    evidence 1,029 passed across all 64 files at Y-072.
    Package version in pyproject.toml: 0.0.1. No CHANGELOG
    file; the campaign state + git log are its changelog.
- The honesty boundary inside that code is explicit and is
  preserved here: mesh behaviour is proven **in-process /
  simulated only**. Its modules carry `simulated: true` as
  schema constants; `lan_fabric.py` states in its own header
  that it opens no socket and crosses no network (its tests
  ride socketpairs and judge `simulated_only`); the real
  three-host run is named there as future work. A Pi citizen
  was measured live on Mimir (hardware census facts), but no
  host-to-host inference or authenticated two-node handshake
  proof exists anywhere in the tree.
- **License: MIT - verified at text level.** `LICENSE` at the
  audited HEAD is the canonical MIT text, Copyright (c) 2026
  Volmarr Wyrd, sha256
  `c006b7010fa0c6dc396e405025475c03352effe1495e67e0f9d9a11f427b0383`;
  pyproject.toml declares `license = { text = "MIT" }` - agrees.

## Registry (section 35 duty)

Yggdrasil had NO row in the ledger. Row 27 is added to
`docs/modernization/INTEGRATION_MATRIX.md` and a matching entry
to `docs/modernization/integration-lock.json` (compact format
preserved; every pre-existing row verified byte-identical in
parsed form). Adapter mode `prototype`, evidence stage
`contract implemented`, verification `verified` (audit facts),
**pinned: null - no pin taken**: no Yggdrasil code is
incorporated into the fork; the fork-side prototype is original
volmarr-core code written against the section 36 contract.
No existing engine pin moved. Count assertions in
`test_volmarr_integration_ledger.py` / `test_volmarr_production.py`
updated 26 -> 27 rows (verified 25 -> 26) for the new row.

## Build (plugin-side only - deliverables 2, 3, 4, 6 scoped local)

`plugins/volmarr-core/yggdrasil_local.py` (new, fork-only):

- (a) Envelopes `runeforge.yggdrasil.*.v1`: NodeCapability,
  TaskRequest, PlacementDecision, TaskLease, TaskOutcome,
  EvidenceReceipt - each carries `source_project`
  (Yggdrasil-Distributed-Inference-System) and a classified
  `privacy_zone`; strict validation, named refusals
  (`envelope_malformed`). EvidenceReceipt hashes the canonical
  outcome record and carries `live_mesh_proof: False`.
- (b) `discover_local_node()` - READ-ONLY, local host only.
  Measured: processor/architecture/cores (stdlib platform),
  RAM total/available (/proc/meminfo), disk free, load.
  Probe-only, else the literal string "unknown": accelerator,
  available models, per-model context lengths, peer topology.
  No peer discovery, no socket, no subprocess, no network.
- (c) `place_task()` - a pure function over the capability +
  request + caller-supplied measured latency: wrong-owner
  raises `wrong_owner`; over-budget estimates, token-limit
  overflow, insufficient memory, unavailable model,
  accelerator requirement against an unknown/absent
  accelerator (never guessed), and latency over budget each
  produce a named refusal reason. **Any non-local destination
  is refused** (`egress_not_authorized`; for local-private
  data also `cloud_egress_refused`) - no accidental cloud
  egress is constructible through this surface.
- Deliverable 4 mapping: PlacementDecision and TaskLease
  record `scheduler_owner: hermes-cron-gateway`. Hermes cron /
  gateway session ownership remains the only scheduler; a
  lease here is a local record, execution is not started by
  this slice, and no second scheduler is introduced.
- Not built, by audit honesty: the section 36 A.E.S.I.R.
  worker adapter (deliverable 8 - the Yggdrasil tree's own
  `aesir_adapter.py` is part of its simulated fabric, and
  binding it needs its API proven live, ticket X01-T3),
  cancellation/idempotency/replay machinery beyond envelope
  identity (deliverable 7 - meaningful only with execution,
  ticket X01-T4), WYRD/Verðandi wiring (deliverable 9 - no
  genuine protocol fit proven, ticket X01-T5).

## Live caller (section 28.2)

`hermes volmarr yggdrasil {status|discover|place}` in
`plugins/volmarr-core/cli.py`, in the established volmarr verb
style (not config-gated: the surface is read-only/local and
makes no external call, like `edge-research meter`). Proof run
recorded in Test evidence below.

## CUSTOMIZATIONS.md

No row added. The ledger records intentional divergences from
stock upstream Hermes; volmarr-core is fork-only code with no
upstream counterpart, and this slice adds fork-only code
without touching any upstream surface - not a new divergence
(E18-T1/T2 precedent).

## Test evidence

- Targeted: `scripts/run_tests.sh
  tests/plugins/test_volmarr_yggdrasil_local.py
  tests/plugins/test_volmarr_integration_ledger.py
  tests/plugins/test_volmarr_production.py` = 3 files,
  58 passed / 0 failed (12 new X.01 + 17 ledger + 29
  production). Log: `~/team01-x01-targeted.log`. (First run
  showed 12 passed + 1 teardown ERROR from this slice's own
  fixture calling a nonexistent `PluginManager.shutdown()`;
  fixed to the established `manager.unload()` pattern and
  re-run clean - the defect was in the new test file, never
  in banked code.)
- Live caller proof: in a disposable profile home with
  volmarr-core enabled, `hermes volmarr yggdrasil status
  --json` returned the status record (mesh_claimed false,
  live_peers 0, audited HEAD 1af750f1) and `discover --json`
  returned a real NodeCapability for purplelongship
  (x86_64, 16 cores, RAM total 41,437,048,832 B measured from
  /proc/meminfo; accelerator "unknown", models "unknown",
  context_lengths "unknown", peers "unknown"). Log:
  `~/team01-x01-liveproof.log`.
- Full fork contract gate: `scripts/run_tests.sh
  tests/plugins/test_volmarr_*.py tests/plugins/test_kista_*.py`
  = 138 files, 1,186 passed / 7 failed / 1 skipped. The
  passed count is the E18-T1/T2 baseline 1,174 + the 12 new
  X.01 tests; the 7 failures are name-identical to the known
  live-transport set (5x test_volmarr_core_plugin.py, 1x
  test_volmarr_verdandi_stimuli.py
  ::test_real_plugin_applies_only_unseen_allowlisted_metadata,
  1x test_volmarr_voice_runner.py loopback) - ZERO
  regressions. Log: `~/team01-x01-fullcontracts.log`, marker
  `~/team01-x01-gate.done`.

## Remaining tickets

- X01-T1: peer discovery (separately authorized step,
  section 36 deliverable 5) - not implemented; discovery
  reports peers "unknown" until then.
- X01-T2: host-to-host live proof (deliverable 10) - the gate
  for any promotion past "contract implemented" / any mesh
  claim: authenticated two-node handshake, forced node loss
  mid-task, deterministic replay, measured cross-host
  inference. None exists yet, in either repo.
- X01-T3: A.E.S.I.R. worker adapter (deliverable 8) - only
  after the Yggdrasil Aesir adapter API is proven live
  host-to-host; its current form rides the simulated fabric.
- X01-T4: task cancellation, idempotency, replay prevention,
  outage recovery, checkpoint handoff (deliverable 7) -
  meaningful only once leases execute; envelopes carry the
  identities they will key on.
- X01-T5: WYRD world-state / Verðandi event wiring
  (deliverable 9) - only where protocol contracts genuinely
  fit; the existing Verðandi software is not the Norn of the
  Yggdrasil diagram and is not conflated with it.
- X01-T6: energy/cost placement inputs (deliverable 6
  remainder) - placement today uses latency, memory,
  accelerator, token limits and egress policy; energy/cost
  need measured sources that do not exist on this host yet.
