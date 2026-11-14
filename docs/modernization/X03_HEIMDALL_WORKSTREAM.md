# X.03 Heimdall - ecosystem workstream 3 of 15 (Team 01, 2026-11-14)

**Outcome: AUDIT EXECUTED + REGISTRY ROW ADDED + READ-ONLY
PRESENCE PROTOTYPE BUILT. NO PIN TAKEN, NO EXISTING PIN
MOVED, NO LOGIN ATTEMPTED, NO LIVE GRID SESSION CLAIMED.**
Roadmap Part VII section 38, third of the fifteen ecosystem
workstreams, taken in roadmap order after X.02 (section 37)
banked. The fork gains, plugin-side in volmarr-core: a
read-only presence adapter over the Heimdall bridge's verified
Core IPC interface, the versioned presence/context contract
(qualified observations, never accepted world truth), an
action-permission gate that refuses every write by name, and
the live caller `hermes volmarr heimdall
{status|presence|permissions}`. Section 38 scopes the initial
stage as read-only presence/context only; this slice builds
exactly that stage and nothing beyond it.

## Audit (re-measured, not inherited)

- Source: `hrabanazviking/Heimdall-SL-Hermes-Agent`, branch
  `development` (the repo's default and only long-lived
  branch; there is no `main`). `git ls-remote` 2026-11-14:
  HEAD == `refs/heads/development` ==
  `cee7ce679b2070708cee59d476bdd9397dbd9f86`; **no tags**.
  Side branches `heimdall/core-legs-f1-f5` and
  `heimdall/f1..f7-*` exist and were not audited. Tree cloned
  under $HOME at `~/heimdall-audit`, HEAD verified. No
  repository was created.
- The local `~/heimdall` tree on purplelongship is **not** a
  clone of this repo (no `.git` anywhere in it): it is a
  deployment working directory holding an older heimdall-api
  snapshot (it lacks the audit HEAD's F1-F8 awareness
  modules), the built Core publish output, a WYRD sink
  factory (`heimdall_local_sink.py`) and operator login
  scripts. Its `heimdall-api.service` user unit is installed
  but, at audit time, **no bridge was running**: no
  `/tmp/heimdall.sock`, nothing listening on 8765. The fork
  adapter therefore reports the bridge **absent** on this
  host, truthfully (see Live caller).
- Real code on both sides of the seam (section 38 item 1):
  - `heimdall-core/` (C#, 861 LOC): a LibreMetaverse client
    (`SlSession`) plus an explicitly opted-in
    `SimulatedSession` fixture whose every event is stamped
    `simulated: true`. IPC is NDJSON over Unix sockets
    (`/tmp/heimdall.sock` commands, `.sock.events` push).
    The Core command set is: login, logout, say, chat, im,
    group_im, teleport, sit, stand, move_to (**refused**
    `not_implemented_in_minimal_client` -- teleport is the
    relocation path), ping/status/get_status, set_mode,
    rlv_status (honestly answers no RLV engine attached).
    Credentials reach the Core only through the
    operator-provisioned process environment; a command
    carrying a password is rejected over IPC by structure.
    Login/session: login failures surface the real
    LoginProgress reason (LibreMetaverse 2.6.4 masks it as
    "Canceled" for async callers; the Core works around it);
    disconnects emit `Disconnected`. There is **no**
    automatic reconnect logic in the Core at this HEAD --
    reconnect behavior is an open remainder (X03-T1).
  - `heimdall-api/` (Python, 16,330 LOC, 29 test files): the
    Bifrost seam. A WebSocket API on `ws://127.0.0.1:8765`
    with HMAC-SHA256 authentication (the server **refuses to
    start** without `HEIMDALL_WS_SECRET`; no unauthenticated
    mode). A safety governor enforces, body-side: at most
    5,000 outbound messages per UTC day (the Linden Lab
    scripted-agent operator cap), an operator-only kill
    switch, reflex tiers that may never speak, and payments
    default-deny without an explicit operator approval
    marker. Two-tier presence (awareness/presence.py):
    full-fidelity identified avatars and an anonymous coarse
    census are kept in separate stores and **never merged**
    (coarse dots are never presented as named people), with
    30 s staleness expiry. Chat classification
    (chat/classification.py): every IM is `direct`; local /
    group lines classify named / contextual / ambient via a
    per-(speaker, channel, group) exchange-state machine.
    The canonical event vocabulary (core/models.py) already
    settles F1-F8 contracts (offers, conversations,
    inventory, friends/groups, places, object interaction,
    appearance, money-as-a-sense with deliberately **no**
    spend vocabulary) ahead of their Core legs.
- **License: NONE -- verified absent.** There is no LICENSE
  or COPYING file at the audited development HEAD (tree root
  and full file search), and the README's own section reads
  "Open Source License Yet To Be Determined" (copyright 2026
  Volmarr Wyrd; no warranties; user assumes all liability).
  There is therefore **no license text to hash** -- the
  recorded verdict is the absence itself. Consequence,
  recorded plainly: with no license granted, **no Heimdall
  source is incorporated** into this fork (the X.01/X.02
  pattern is followed: original plugin-side code only,
  written against the section 38 contract); the bridge code
  below copies no Heimdall code, vocabulary beyond the
  verified IPC command names, or text.

## Registry (section 35 duty)

Heimdall had NO row in the ledger. Row 29 is added to
`docs/modernization/INTEGRATION_MATRIX.md` and a matching
entry to `docs/modernization/integration-lock.json` (compact
format preserved, byte-round-tripped). Adapter mode
`prototype`, evidence stage `contract implemented`,
verification `verified` (audit facts), **pinned: null -- no
pin taken** (Heimdall is a separate bridge service with no
installable Hermes-side package, and its license is
undetermined). No existing engine pin moved. Count
assertions in `test_volmarr_integration_ledger.py` /
`test_volmarr_production.py` updated 28 -> 29 rows (verified
27 -> 28) for the new row. The pre-existing
`world_bridge.py` HEIMDALL_DESCRIPTOR (service
`volmarr-heimdall-presence`, availability `design-only`) is
an earlier W-phase seam and is untouched; this slice's
adapter is the separate `volmarr-heimdall` service.

## Build (plugin-side only - section 38 items 3-5, 9, 10)

`plugins/volmarr-core/heimdall.py` (new, fork-only):

- **Read-only presence adapter** (items 3-4): the bridge is
  probed without sending it anything (operator disablement
  flag, Core IPC socket presence, Bifrost API TCP
  reachability). A present Core is asked exactly one command
  -- the read-only `status` -- over its verified NDJSON IPC;
  the transport itself refuses any non-read command by name
  before a socket is touched. The HMAC-authenticated
  WebSocket command channel is probed at TCP level only;
  speaking its authenticated protocol is a later,
  separately permitted stage. When no bridge runs, the
  adapter reports `absent` / `present-api-only` /
  `disabled` truthfully -- presence is never fabricated,
  and a Core error reply or a simulated session is recorded
  as exactly that (error state / `simulated: true`), never
  dressed up as a live session.
- **Presence/context contract** (item 5):
  `runeforge.heimdall.presence-context.v1` records bridge
  state, session state, agent name/UUID, region + position,
  mode and Core versions as a **qualified observation** with
  provenance (source, location, observed-at time) and
  `accepted_as_world_truth: false` -- validation rejects
  any record claiming world truth, any write performed, or
  a logged-in session for an absent/disabled bridge. A
  generic `runeforge.heimdall.observation.v1` carries the
  same qualification for chat/region/avatar/object/system
  observations feeding WYRD-style consumers.
- **Action-permission gate** (item 4): reads (status,
  presence, observe, login_status) are allowed; **every**
  write action -- say, chat, im, group_im, move, teleport,
  interact, spend, login, logout, set_mode -- is refused by
  name (`write_action_refused`), and unknown actions are
  refused too (`unknown_action_refused`). There is no code
  path in this module that can transmit a write, attempt a
  login, or spend anything.
- **Privacy by construction** (item 9): observation kinds
  `im` / `private_im` / `relationship` are refused by name
  (`private_content_refused`) -- private IM content can
  never become an observation, so it cannot leak into
  Verðandi telemetry or shared knowledge; presence records
  carrying private-IM fields fail validation; all recorded
  text passes the redaction rules (secret assignments,
  bearer tokens, token shapes, private keys, `/home/<user>`
  paths) before storage, and observations are
  `telemetry_shareable: false` by contract.
- **Complete disablement** (item 10):
  `HEIMDALL_BRIDGE_DISABLED=1` makes every surface report
  `disabled`; nothing else in the fork references the
  bridge state, so disablement has no effect on the
  companion's persistent identity or the rest of the fork.

No network beyond the local bridge probe, no credentials
read or stored, no mutation anywhere. No CUSTOMIZATIONS.md
row (fork-only code, E18-T1/X.01/X.02 precedent).

## Live caller (section 28.2)

`hermes volmarr heimdall {status|presence|permissions}` in a
disposable profile home (`/tmp/x03home`, log
`~/team01-x03-liveproof.log`): status reports
`contract-implemented` with bridge state **`absent`**
(command socket absent, API not listening -- the truth on
this laptop at proof time), `live_grid_session_claimed:
false`, `login_attempted: false` and the audited source
facts; `presence` emits a valid presence-context record with
session `unknown` and the detail "presence is not
fabricated"; `permissions` lists 4 reads allowed and all 11
writes REFUSED by name; the bare verb exits 2 with usage.

## Tests and gate

- Targeted: `tests/plugins/test_volmarr_heimdall.py` +
  `test_volmarr_integration_ledger.py` +
  `test_volmarr_production.py` via scripts/run_tests.sh =
  3 files, **54 passed / 0 failed** (log
  `~/team01-x03-targeted.log`). The heimdall contracts pin
  absent/disabled truthfulness, the present-bridge presence
  contract (exactly one read-only `status` transmitted),
  simulated/error honesty, write refusals by name, presence
  tamper refusal, and IM privacy + redaction.
- Full fork gate: 140 files, **1,201 passed / 7 failed /
  1 skipped** -- the X.02 baseline of 1,193 plus 8 new
  heimdall tests; the 7 failures are name-identical to the
  known live-transport set, ZERO regressions (log
  `~/team01-x03-fullcontracts.log`). A wider-scope run over
  all of tests/plugins (297 files, 3,241 passed, same 7
  named failures) is kept at `~/team01-x03-plugins-wide.log`.
- README untouched (sha256 336813d11bbe...).

## Honest remainders / tickets

- X03-T1: authorized live grid session proof -- start the
  deployed bridge (Core + Bifrost) under its operator
  provisioning, prove the read-only status path against a
  REAL logged-in session, plus disconnect/reconnect
  behavior (the Core at this HEAD has no automatic
  reconnect) and region-crossing / stale-handle behavior
  (section 38 item 7). Not claimed here: no bridge was
  running and no login was attempted.
- X03-T2: re-check the CURRENT Second Life bot /
  scripted-agent rules (Linden Lab policy, disclosures,
  rate limits) before ANY activation stage (section 38
  item 8) -- a pre-activation gate, not paperwork after
  the fact. The governor's 5,000/day cap is the bridge's
  own record of the operator cap, not a substitute for
  this re-check.
- X03-T3: write-stage permissions -- distinct, separately
  granted permissions for say / IM / move / interact /
  spend (section 38 item 4), each with its own slice,
  governor proof and wrong-account refusal tests
  (section 38 item 2 identity reconciliation: Helm/SL
  account vs Hermes entity_id / persona_id / Kista scopes).
  Until then every write stays refused by name.
- X03-T4: WYRD feed wiring -- hand validated presence /
  observation records to the WYRD sink as qualified
  observations in a Second Life namespace (the deployed
  tree already carries a WYRD sink factory); not wired in
  this slice, so nothing here writes world state anywhere.
- X03-T5: avatar presentation via the existing voice/VRM
  tools (section 38 item 6) and screenshot/media handling
  -- not built; no mic/camera assumptions are made.
- The source repo's license is Volmarr's own decision as
  its copyright holder; until a license is chosen and a
  LICENSE file lands at the development HEAD, the
  no-incorporation posture above stands unchanged.
