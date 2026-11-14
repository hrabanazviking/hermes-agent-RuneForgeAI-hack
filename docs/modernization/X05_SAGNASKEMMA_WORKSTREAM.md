# X.05 Sagnaskemma engine - ecosystem workstream 5 of 15 (Team 01, 2026-11-14)

**Outcome: STAGED-TREE PROOF DISCHARGED (E12-T1) + FIRST PIN
TAKEN + PRIVATE ADAPTER BUILT + LIVE CALLER ADDED.** Roadmap
Part VII section 40, fifth of the fifteen ecosystem
workstreams, taken in roadmap order after X.04 (section 39)
banked. This slice is DISTINCT from E.12: E.12 identified the
canonical repo and established the SRD pin while leaving
Sagnaskemma blocked on staged-tree proof; X.05 stages the
tree, proves the engine, takes the first pin, and builds the
section 40 adapter -- plugin-side only, no core edits, no
engine source incorporated, and NO private canon, scenario,
character or lore content copied into this fork anywhere
(interface facts only, per the section 40 boundary). The
pre-existing volmarr-rpg SRD adapter is a separate plugin
and is untouched.

## Audit (re-measured, not inherited)

- Source: hrabanazviking/Sagnaskemma-Volmarrs-D-and-D-Lore-
  Treasure-Trove, branch main. git ls-remote re-measured
  2026-11-14: HEAD == main at
  a1f474f4b8803b7003b35b09f486a53145545685 -- exactly the
  HEAD E.12 recorded. No repo was created.
- Staging (discharges the staging half of E12-T1): sparse
  clone directly under $HOME at ~/sagnaskemma-x05 with the
  laptop's own git credentials, non-interactive. Sparse
  set: engine + tests + scripts + docs + skills + root
  files (~27 MB). The repo's campaign/, canon/, lore/ and
  commercial/ trees were NEVER checked out. HEAD verified
  at a1f474f4b880 after checkout.
- Engine contract at the pin (engine/INTERFACE.md and
  engine/api.py, read at the staged tree):
  - Package sagnaskemma-engine, __version__ 0.2.0
    (pyproject.toml + engine/__init__.py agree);
    requires-python >=3.10; sole runtime dependency
    Avrae d20 (>=1.1.2,<2). Dev extras: pytest, build,
    setuptools, wheel.
  - engine.api: PROTOCOL_VERSION "1.0"; discover() returns
    the versioned catalogue (243 executable commands at
    this HEAD -- the engine has grown past the 90 commands
    the 2026-10 Samtal records saw), transports python /
    cli-json / ndjson-stdio, state root via the
    SAGNASKEMMA_STATE_DIR environment variable; execute(
    argv, request_id) returns one envelope (protocol
    version, id, ok, exit_code, output, rolls, warnings).
  - The engine's own stated invariants (INTERFACE.md):
    every mechanical random outcome flows through its
    dice module (single gateway over d20, with a seed()
    hook); static data is immutable at runtime; saves are
    atomic per file; there is NO distributed or cross-file
    rollback contract; a request id is NOT a persisted
    idempotency key; revision conflicts require reload and
    deliberate caller retry. These two absences are exactly
    why the transactional discipline in this slice lives
    in the adapter (compare X.04's adapter-side WYRD
    journal) -- and the record says so rather than dressing
    the engine contract up.
  - The Shared Table service (engine/service.py) hosts
    sessions, seats and per-seat filtered streams over the
    same envelope; the fork adapter does not drive it in
    this slice (ticket X05-T1).
- License: TEXT-READ at the staged tree in this slice.
  There is NO LICENSE file at the pinned HEAD (root or
  engine/). THIRD_PARTY_NOTICES.md section 3 records the
  position: the upstream systems repo is the owner's
  original creation, both repos are private, no open-
  source license file is required while the code stays
  non-public (owner decision 2026-10-02), and licensing is
  revisited if any part goes public; adapted slices are
  released under the project's license-to-be-decided. The
  sole runtime dependency d20 is MIT (its LICENSE file
  verified in the staged notices). Consequence for the
  fork: the pin is admissible for a PRIVATE adapter that
  incorporates no engine source and serves no canon
  content; nothing here creates a redistribution right,
  and none is exercised.
- Engine suite proof (the proof half of E12-T1): native
  venv at ~/sagnaskemma-venv (no Docker) with d20 +
  pytest + build + setuptools + wheel. Clean full run:
  **1739 passed / 1 skipped / 0 failed** (log
  ~/team01-x05-engine-suite2.log). The one skip is the
  engine's own network-gated live SRD test
  (SAGNASKEMMA_TEST_NETWORK unset). The first run (log
  ~/team01-x05-engine-suite.log) read 1736 passed / 1
  failed / 2 errors / 1 skipped; every non-pass was a
  staging artifact of THIS slice, proven so: the skald
  credential test needed the skills/ tree (added to the
  sparse set; test then passed) and the two packaging
  tests needed the build/setuptools dev tools in the
  venv (installed; the packaging file then passed 7/7).
- Seeded determinism against the real engine:
  dice.seed(42) + execute(['roll', '2d6+3']) twice yields
  byte-identical roll records (faces [6, 1], total 10);
  log ~/team01-x05-live.log.

## Registry (section 35 duty)

Sagnaskemma already has row 24 -- no new row. FIRST PIN
taken in this slice: pinned == current_head ==
a1f474f4b8803b7003b35b09f486a53145545685 in
docs/modernization/integration-lock.json (pin_source now
COMPONENT_LICENSES.md, license text-read as above,
update_needed false, verdict "current - X.05 executed"),
INTEGRATION_MATRIX.md row 24, the Sagnaskemma row in
COMPONENT_LICENSES.md, and the pin-guard assertion in
tests/plugins/test_volmarr_integration_ledger.py (CLI
engines show for the Sagnaskemma row, following the
E.05-E.12 pattern). The lock was edited in its established
compact format; a field-level diff confirms only the
Sagnaskemma entry changed. Verification counts move to
**29 verified / 0 partially verified / 0 blocked** -- the
last blocked row in the ledger is discharged; the ledger
test's count assertions are updated in this same slice.
CUSTOMIZATIONS.md gains exactly one ledger row for the
X.05 adapter.

## Build (plugin-side only - section 40 items 1-10)

All new code is plugins/volmarr-core/sagnaskemma.py
(original fork code against the audited contract), plus
the table family in the existing plugin CLI and five
default-off config keys in plugin.yaml
(sagnaskemma_enabled, sagnaskemma_engine_root,
sagnaskemma_python, sagnaskemma_session_db,
sagnaskemma_canon_access -- every one defaults to off /
empty / denied).

- **Adapter plan surface** (item 1): sagnaskemma_status()
  and capability_catalog() publish the plan as versioned
  records (runeforge.sagnaskemma.service.v1 /
  adapter-plan.v1) built from the audited API, version
  (0.2.0), protocol (1.0) and license scope above. The
  private SAGNASKEMMA_HERMES_ADAPTER_PLAN the roadmap
  names lives as these records plus this document -- all
  interface goals, no private content.
- **Mechanics vs narrative** (item 2): MECHANICS_
  CAPABILITIES = dice, checks, combat, inventory,
  initiative, tables, encounter_state; NARRATIVE_
  CAPABILITIES = session_description, npc_state,
  character_state, lore_retrieval. The two families are
  gated separately: mechanics and session narrative run
  through seat permissions in the session store; lore
  retrieval is in the canon gate below and never reaches
  the store.
- **One canonical dice owner** (item 3): each session's
  state carries exactly one DiceOwner, seeded at creation.
  Every roll/check in the session flows through it; the
  seed and every outcome (expression, faces, modifier,
  total, roller, purpose) are recorded in order in the
  session state, so the sequence is auditable and a fresh
  owner with the same seed replays it exactly (contract-
  proven; the adapter owner's seed-42 opening roll also
  matches the real engine's seeded opening roll, faces
  [6, 1] on 2d6+3).
- **Transactional persistence** (item 4): TableSessionStore
  (SQLite, WAL, synchronous FULL). apply() takes a
  caller-supplied transaction id: same id + same payload
  returns the recorded result WITHOUT re-executing (no
  duplicated roll or state change); same id + different
  payload is idempotency_conflict. Each commit stores the
  full prior state; undo() is a savepoint restore with
  stack discipline (latest committed first, else
  undo_not_latest). State and ledger land in one database
  transaction, so an interrupted action (mutator raises)
  leaves no trace, no revision bump and no dice spent --
  reopening the store is the crash recovery, and turn /
  session ownership is explicit: the acting seat must
  hold a seat in THIS session with the needed permission.
- **Versioned private local tool service** (item 5):
  EngineClient calls the engine ONLY through engine.api
  discover()/execute() at protocol 1.0, in a bounded
  subprocess rooted at the staged tree with the engine
  state dir pointed at a caller-named private directory;
  a protocol mismatch raises version_mismatch (no silent
  adaptation). With no engine root configured, status
  reports "not configured", authorize_capability raises
  not_configured for every capability, and
  hidden_content_served is False in every record.
- **Samtal link** (item 6): link_samtal() records a
  distinct Samtal room id (room == session is refused by
  name as conflated), GM-seat only, and returns the
  per-seat permission map with the privacy boundary
  stated in the record (the room carries seat-filtered
  views only, never the session ledger). The live Samtal
  bridge itself is not built (ticket X05-T1).
- **WYRD campaign namespace** (item 7): every session
  mints wyrd_namespace sagnaskemma-<session_id> at
  creation; wyrd_campaign_record() emits reality
  "fictional" / truth_class "fictional_state" only --
  the namespace X.04's consumer seam authorizes for
  Sagnaskemma. Roleplay state has no path into real-world
  observation records through this adapter.
- **Canon boundary** (item 8): lore_retrieval raises
  canon_denied unless sagnaskemma_canon_access is
  explicitly enabled, and canon_store_not_configured even
  then (no approved store is configured in this slice);
  no capability in this adapter returns rule text,
  homebrew or campaign content, and the tests and this
  record use synthetic fixtures only.
- **Frontend handoff** (item 9): export_session() /
  import_session() move the full session -- state
  (including the dice owner's RNG state), seats, and the
  whole transaction ledger. Re-import is a no-op
  (already_present); a replayed transaction id on the
  receiving frontend returns its recorded result; both
  frontends continue with the identical next roll
  (contract-proven).
- **No production claim** (item 10): every status record
  carries production_ready False with its reason.

## Live caller (section 28.2)

New CLI family beside the existing volmarr verbs:
hermes volmarr table {status|capabilities} (read-focused,
X.04 pattern). Real proof in disposable profile homes
(log ~/team01-x05-liveproof.log): with no engine
configured, status answers availability "not configured"
with configured false and rc 0; capabilities lists the
mechanics/narrative split with the canon gate, rc 0; the
bare verb exits 2 with usage. With the staged engine
configured (sagnaskemma_engine_root = ~/sagnaskemma-x05),
status answers availability "contract-implemented" with
configured true, engine_version 0.2.0, protocol 1.0, rc 0.

Staged-engine proof (harnesses in /tmp, scratch evidence
only; log ~/team01-x05-live.log): the adapter's
EngineClient drives the REAL staged engine in its d20
venv -- discover() answers protocol 1.0 with 243 commands
and the three audited transports; execute(['roll',
'2d6+3'], request_id='x05-live-1') answers ok with the
recorded roll; the seeded determinism proof above passes;
an adapter session roll and its WYRD campaign record
(fictional namespace) are produced against the same
store code the contracts pin.

## Tests and gate

- Targeted: tests/plugins/test_volmarr_sagnaskemma_x05.py
  (11 new contracts) + test_volmarr_rpg.py +
  test_volmarr_wyrd_x04.py +
  test_volmarr_integration_ledger.py +
  test_volmarr_production.py via scripts/run_tests.sh =
  5 files, **90 passed / 0 failed** (log
  ~/team01-x05-targeted.log); after the registry edits,
  the sagnaskemma + ledger + rpg subset re-ran clean at
  44 passed / 0 failed (log ~/team01-x05-targeted2.log).
  The 11 X.05 contracts pin every section 40 gate:
  seeded determinism (owner-level and session-level,
  recorded outcomes), multi-user seat isolation (cross-
  session seats hold nothing; spectator read-only; player
  refused combat/undo), interrupted action rollback
  (failed inventory take and malformed roll leave state,
  dice and revision untouched; the next roll continues
  the seeded sequence), serialization round trip (export
  -> JSON -> import is byte-stable; reopening the store
  file recovers the exact committed state), source-canon
  denial (canon_denied by default, canon_store_not_
  configured when flagged, not_configured without an
  engine, hidden_content_served False), and optional
  game session continuity (handoff import, re-import
  no-op, replayed transaction returns its recorded roll,
  both frontends continue with the identical next roll).
- Full fork gate (the campaign contract set: all
  tests/plugins/test_volmarr_*.py + the two kista files,
  the X.04 gate shape): **142 files, 1,229 passed / 7
  failed / 1 skipped** -- the X.04 baseline of 1,218 plus
  the 11 new X.05 tests; the 7 failures are NAME-IDENTICAL
  to the known live-transport set (diffed against the
  X.04 log: 5x test_volmarr_core_plugin.py, 1x
  test_volmarr_verdandi_stimuli.py, 1x
  test_volmarr_voice_runner.py), ZERO regressions (log
  ~/team01-x05-fullcontracts.log). A wider run over all
  299 files under tests/plugins/ (log
  ~/team01-x05-widegate.log) also showed only the same 7
  failures (3,269 passed / 5 skipped).
- No bug was found in pre-existing fork code in this
  slice. One harness artifact of this slice is recorded
  for honesty: an unscoped full-repo test run was started
  by mistake, was stopped, and its scratch fixture dirs
  were removed; the banking gate above is the scoped
  campaign set, exactly as X.04 ran it.
- README untouched (sha256 336813d11bbe... before and
  after).

## Honest remainders / tickets

- X05-T1: the engine's own Shared Table service
  (hosted sessions / seats / per-seat streams in
  engine/service.py) is not driven end-to-end from
  Hermes, and the Samtal link is a record, not a live
  Samtal bridge. The adapter's session store is the
  Hermes-side table in this slice; wiring the live
  service and a real Samtal room are future work with
  their own proofs.
- X05-T2: lore retrieval has no approved-store
  implementation -- by design. Until Volmarr names an
  approved private canon store surface, canon_denied /
  canon_store_not_configured are the only answers, and
  no canon content moves.
- X05-T3: session mechanics rolls use the adapter-side
  seeded DiceOwner (needed for multi-seat idempotency
  and handoff); engine-native rolls through execute()
  are proven available but are not the session dice
  owner. A future slice could route session rolls
  through the staged engine per session (its own state
  dir) and prove sequence equivalence, if that trade is
  ever wanted.
- X05-T4: engine calls are one bounded subprocess per
  call; no persistent engine service process, streaming
  (engine stream surface) or agent-stdio session is
  integrated.
- X05-T5 (carried from E.12 as E12-T2): the
  INTEGRATION_MATRIX "Verification tally" paragraph
  still carries its W08 promotion counts; the lock and
  the ledger test are the enforced truth (now 29
  verified / 0 partially verified / 0 blocked). The
  tally paragraph wants its dedicated correction pass,
  out of this slice's rows-only scope.
- E12-T1 is DISCHARGED by this slice (sparse stage +
  d20 venv + engine suite + discover proof + license
  position read + pin decision taken).
- The section 32 release scorecard still reads NOT
  releasable; X.05 changes the Sagnaskemma adapter and
  its ledger row only, and production_ready stays False
  in every X.05 record (section 40 item 10).
