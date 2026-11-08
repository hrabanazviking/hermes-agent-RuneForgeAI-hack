# W10 / N2+N3 Implementation Record (Team 02, 2026-11-08)

Wave: W10 Productivity - N2 coding and project-management
ecosystem (roadmap section 21), N3 social communication and
planning (section 22), gate (section 30): permissioned,
replay-safe workflows.
Branch yrsa/hermes-team-02 in worktree ~/hermes-team-02 on
purplelongship, based on banked main
43199e2379ca037d76beb5b1f6e29cffb2e85d0c (W09 banking closure).
Commit-only: the keeper banks serially; nothing was pushed or
merged here. No Docker used. No core files touched - all code is
plugin-side (plugins/volmarr-core/), built ON the banked W09
capability bus (descriptors, permission policy and provenance
envelopes are consumed, not duplicated).

README.md untouched: sha256
336813d11bbe5aa2ff745b4a4bc3abcf2a283cd13971c0c11d061377129db7f3
verified before the work and at the end.

## What was delivered - N2 (contract+adapter level)

### 1. Project-context packets - plugins/volmarr-core/project_context.py (231 lines)
- build_project_packet(repo_path, recorded_at=...) measures a
  packet LIVE from a local repo: for each of README.md,
  ROADMAP*.md and CAMPAIGN_STATE*.md that exists at the repo
  root it records kind, name, repo-relative path, byte size and
  SHA-256 (streamed, chunked reads); kinds with no file are
  named in the packet's missing list - never invented, never
  defaulted from another project or a hardcoded fact.
- Commit HEAD is read from the target's own .git with pure file
  reads (plain .git dir, worktree .git file, loose refs,
  packed-refs, detached HEAD) - no subprocess, no staleness.
- The builder is read-only. Patch preparation is a separate
  explicit operation (write_patch_preparation): the
  caller-chosen output path must resolve OUTSIDE the target
  repository; an inside path is refused by name
  (patch_output_inside_target_repo) before anything is written,
  and the returned receipt carries output hash + target HEAD.
  A capability descriptor (volmarr-project-context 0.26.0,
  read/propose, contract-implemented) describes the service in
  the W09 bus vocabulary.

### 2. Task handoffs + publish guard - plugins/volmarr-core/task_handoff.py (210 lines)
- The Mythic Engineering handoff as data: schema
  runeforge.task-handoff.v1 with intent, invariants, tasks
  (id/title/status, ids unique, status in
  planned/running/done/blocked), evidence (kind + required ref)
  and ledger entries. validate_handoff refuses malformed
  records by name; new_handoff builds + validates in one step.
  This is the record Hermes and the Mythic Agent Coder CLI /
  future Draupnir share (section 49) - one schema, no competing
  write processes implied by it.
- A valid handoff travels only inside a capability-bus result
  envelope (handoff_envelope): provenance is mandatory.
- Publish guard: guard_publish / require_publish resolve any
  publish/push action through the W09 capability policy on the
  volmarr-task-handoff descriptor. Without the explicit
  approval flag the decision is a refusal naming
  write_action_requires_approval (plus the side-effect rule);
  approval does NOT override privacy travel - an approved
  local-private payload to a public destination is still
  refused (privacy_travel_refused:local-private->public).
  The guard decides only; no publish is performed anywhere.

## What was delivered - N3 (contract level, fake transports)

### 3. Samtal bridge + Samkoma - plugins/volmarr-core/samtal_bridge.py (441 lines)
- Identity: validate_identity requires an agent_id distinct
  from the human_owner_id (agent equals human is refused by
  name). The bridge seat carries both ids in every envelope's
  provenance: an agent is a participant, never the owner.
- Transport is an injected interface (send/fetch by cursor).
  InMemoryTransport is a FAKE for contract tests - it is not a
  Samtal client, opens no connection, and no live Samtal
  connection is claimed anywhere in this slice.
- Send path: sender must be the bridge's own agent identity -
  sending as the human owner is refused
  (impersonation_refused:human_owner_identity), as is any other
  sender; the send then resolves through the capability policy
  (approval required; room scope maps to the bus destination
  vocabulary public/shared/local, so a local-private payload
  addressed to a public room is refused by name with the bus
  privacy-travel reason, and a shared payload to a public room
  likewise).
- Receive path: poll() accepts messages after the cursor in
  order; duplicate deliveries are suppressed by message id
  (counted, cursor still advances); a cursor gap refuses by
  name (cursor_gap:expected N got M) and leaves the cursor at
  the last good message so the missing range can still arrive;
  an incoming agent-kind message bearing the human owner's id
  is refused and recorded, never delivered. recover() is the
  missing-cursor path: replay from the room start through the
  same dedupe rebuilds the inbox with no gaps and no dupes.
- Samkoma candidate flow (SamkomaPipeline): input receipt
  (idempotent per candidate id) -> candidate -> evidence
  (one or more cited refs; empty refs refused) -> operator
  approval (only from the evidence state, only with an
  operator and an explicit grant) -> published event.
  publish from received/candidate/evidence is refused by name
  (transition_refused:unapproved_cannot_publish:<state>->
  published): an unapproved candidate can NEVER reach the
  published state. Publishing is idempotent - one candidate,
  one event, retries return the same event record (section
  43's duplicate-submission rule).
- Section 22 acceptance topics are each pinned by a named
  test: impersonation refusal (send-side and incoming),
  duplicate delivery, missing-cursor recovery, cursor gap,
  private-to-public leak prevention, unapproved planning
  proposal refusal.

### 4. CLI - plugins/volmarr-core/cli.py (+58/-1)
New read-only/inspection family following the capabilities
precedent: hermes volmarr productivity {packet|publish-check|
bridge-status}. packet builds a live project packet for a
--repo path; publish-check runs the publish guard and exits 0
only when allowed; bridge-status reports both N3 descriptors
with live_connection "not-claimed". The usage line gains the
productivity family name.

### 5. Tests (25 new)
- tests/plugins/test_volmarr_productivity.py (12 tests): live
  packet measurement (sizes/SHA-256/HEAD), packed-refs and
  detached HEAD, missing files named, missing repo refused,
  patch output inside refused + outside receipt with target
  untouched, handoff validation by name, envelope provenance,
  publish guard matrix, CLI packet/publish-check/bridge-status
  end to end through the real argparse registration.
- tests/plugins/test_volmarr_samtal_bridge.py (13 tests):
  identity distinctness, send happy path, impersonation
  refusals, send approval, leak refusals by name, duplicate
  suppression, cursor recovery after disconnect, cursor gap
  refusal + recovery, incoming impersonation refusal, Samkoma
  full flow + idempotent publish, unapproved publish refusals
  from every pre-approval state, approval guards, receipt
  idempotency.

## Verified counts (from log files on purplelongship)

- New tests only (~/team02-w10-newtests.log): 2 files,
  25 tests passed / 0 failed. Exit summary: "2 files, 25 tests
  passed, 0 failed".
- Full Volmarr/Kista contract set (~/team02-w10-contracts.log):
  134 files, 1,104 passed / 7 failed / 1 skipped. That is the
  W09 banked baseline (132 files, 1,079 passed) plus exactly
  the 25 new W10 tests - zero regressions.
- The 7 failures were name-checked and are exactly the known
  live-transport set: 5 in test_volmarr_core_plugin.py
  (test_missing_unix_socket_support_is_fail_open,
  test_real_discovery_publishes_versioned_metadata_without_
  sensitive_content, test_registered_health_cli_requires_a_
  valid_verdandi_pong, test_relative_socket_path_cannot_
  escape_the_active_profile, test_transport_failure_is_fail_
  open_for_the_pre_tool_policy_hook), 1 in
  test_volmarr_verdandi_stimuli.py
  (test_real_plugin_applies_only_unseen_allowlisted_metadata),
  1 in test_volmarr_voice_runner.py
  (test_real_loopback_runner_delivers_canonical_stdin_event_
  then_eof). No live Verdandi service runs on this laptop;
  these failures pre-date W10 and are identical in kind to
  every prior wave baseline.
- Test-runner note, recorded honestly: both runs used
  scripts/run_tests.sh with its documented HERMES_PYTHON path
  pointing at the already-staged test environment
  (/home/volmarr/.hermes/installs/c14cbec0f92aa34b/test-
  environment/gen-f5677ed9a97c4319bc70520e5564c140/venv/bin/
  python, the same env the W09 runs used). This worktree's
  uv.lock is byte-identical to the banked tree's (sha256
  584af160f498fef2c47a1d8b3ea6a2dd8c3189286c5d3e1a08d646608f65c296
  in hermes-team-02, hermes-team-01 and hermes-hack-forge
  alike) and pyproject.toml matches the banked tree (sha256
  5f0fbe11bebcc0f2a7063c6a19b4a9ce051de3c9ae445f5ce8a72c98b
  cddc7f). The runner, its per-file isolation and its counts
  are unchanged; only the interpreter source differs, per the
  accepted W09 fallback for the staging-download failure mode.

## Code review and bugs

The three new modules and the CLI diff were reviewed as they
were written (descriptor shapes checked against the W09 bus
validator, room-scope mapping checked against the bus privacy
travel table, Samkoma transition table checked against the
section 43 flow). All 25 new tests passed on the first run and
the full set showed zero regressions, so no defect in the new
code was found to fix. Bugs fixed in W10: none, because none
were found in scope - recorded plainly rather than padded.
One authoring slip in a test helper (a dead conditional line)
was caught and removed before the first test run; it never
reached a run.

## Honest remainders (NOT done, NOT claimed)

1. Live Samtal connection: NOT attempted and NOT claimed. No
   credentials exist for this slice; Samtal's own auth,
   encryption and key rotation remain the security boundary
   (section 22). The bridge is a contract over an injected
   transport with a fake in-memory implementation; a real
   Samtal adapter (N.03 audit first) is future work.
2. Live Samkoma connection: NOT claimed. The pipeline is the
   record-level flow in this repo; no Samkoma service was
   contacted, and its current API/models were not re-verified
   here (section 43 asks for that inspection before any
   adapter is called production ready).
3. GitHub / Samverk live adapters (N.02, section 21 repo
   inventory, issues, PRs, reviews, releases): NOT built and
   NOT claimed. The N2 slice is the local packet + handoff +
   publish-guard contract those adapters must consume.
4. Multi-project dashboard (section 21): NOT built. The
   productivity packet CLI is the per-repo inspection surface
   a dashboard would aggregate; no dashboard is claimed.
5. Detached asynchronous jobs with on-disk checkpoints
   (section 21), doc import/export adapters, Google Drive/
   Docs integration, checkout leases (section 49.5) and
   Draupnir delegate jobs (N.06): NOT built in this slice.
6. Notification/availability policy and group feedback-loop
   protection (section 22), Samtal file sharing, voice/3D
   rooms: NOT built; voice/3D stay deferred per section 22
   until the upstream services have tested interfaces.
7. W10 gate wording - "permissioned, replay-safe workflows":
   the permission half is proven at contract level (publish
   guard + send approval + Samkoma approval gate); the
   replay-safe half is proven for message delivery and
   Samkoma publishing (dedupe, cursor recovery, idempotent
   publish). End-to-end proof against live services is NOT
   claimed.

## Files in this wave

- plugins/volmarr-core/project_context.py (new, 231 lines)
- plugins/volmarr-core/task_handoff.py (new, 210 lines)
- plugins/volmarr-core/samtal_bridge.py (new, 441 lines)
- plugins/volmarr-core/cli.py (+58/-1)
- tests/plugins/test_volmarr_productivity.py (new, 270 lines)
- tests/plugins/test_volmarr_samtal_bridge.py (new, 279 lines)
- docs/modernization/W10_N2N3_IMPLEMENTATION.md (this record)
- CUSTOMIZATIONS.md (one W10 ledger row added)
