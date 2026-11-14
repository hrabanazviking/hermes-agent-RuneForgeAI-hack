# X.04 WYRD Protocol - ecosystem workstream 4 of 15 (Team 01, 2026-11-14)

**Outcome: AUDIT EXECUTED + EXISTING ADAPTER UPGRADED IN
PLACE + LIVE CALLER EXTENDED. NO PIN TAKEN, NO EXISTING PIN
MOVED, NO SECOND WORLD CONNECTOR CREATED.** Roadmap Part VII
section 39, fourth of the fifteen ecosystem workstreams,
taken in roadmap order after X.03 (section 38) banked. This
slice is DISTINCT from E.07: E.07 moved the WYRD pin to
package v1.5.0 and verified the then-existing adapter;
X.04 upgrades that same adapter (plugins/volmarr-core/
wyrd.py, wyrd_tools.py, wyrd_context.py, world_telemetry.py)
to the section 39 semantics: capability negotiation, truth
classes, transactional idempotent writes, conflict
resolution, bounded provenance packets, subscriptions /
streaming, and consumer seams -- plugin-side only, no core
edits, no WYRD source incorporated.

## Audit (re-measured, not inherited)

- Source: hrabanazviking/WYRD-Protocol-World-Yielding-Real-
  time-Data-AI-world-model, branch development. git ls-remote
  re-measured 2026-11-14: HEAD == refs/heads/development ==
  89ed09394c7e13b2e63f91e342fbab8ff9890cbc -- EXACTLY the
  E.07 pin. The engine has NOT moved past the pin, so this
  slice builds against the pinned contract and no pin-move
  ticket arises. main is 7df509e9140793d8b7bae91bb1d35c466be1d887;
  the only tag is v1.0.0 at f3dfb1a27c0a. The staged engine
  tree is the pre-existing clone directly under $HOME at
  ~/wyrd-e07 (HEAD verified at the pin, clean except the
  E.07/X.04 scratch live harnesses in its tests/). No PyPI
  wyrd package was installed anywhere in this slice.
- Package version at the pin: 1.5.0 (pyproject.toml, read at
  the pinned commit). License: CC BY 4.0 -- re-verified at
  text level at the pin in this slice: the README License
  section (CC BY 4.0 statement with Share / Adapt /
  Attribution terms; section sha256 over the heading-to-next-
  heading window 71a743a211d44d..., the window differs from
  E.07's extraction so the hashes are not comparable, the
  declaration text is the same) plus the pyproject
  declaration license = { text = "CC BY 4.0" }, whose line
  sha256 3d39ac301615342997408c... is byte-identical to
  E.07's measurement. There is still NO standalone LICENSE
  file at the pin (GitHub NONE explained, E.07). Unchanged.
- The audited engine contract at the pin (src/wyrdforge):
  - HTTP surface (bridges/http_api.py): exactly five routes,
    versioned /v1/* with unversioned aliases -- GET /health,
    GET /world, GET /facts, POST /query, POST /event;
    responses carry X-Wyrd-API-Version: 1. Optional bearer
    auth when a token is configured (the fork adapter stays
    loopback-only and credential-free, as before). There is
    NO subscription, streaming, or push endpoint at the pin.
  - Schemas (schemas/): canonical_fact_record (store
    mimir_canonical_store; payload fact_subject_id / fact_key
    / fact_value / domain / support_record_ids /
    supersedes_record_id; TruthMeta support_class /
    confidence / contradiction_status / approval_state;
    Provenance source_type / source_ref / source_hash;
    EntityScope carries world_id), observation_record (store
    hugin_observation_store; kinds utterance / action /
    tool_result / world_event / code_event / emotion_signal),
    contradiction_record, micro_context_packet. Record
    schema_version defaults to "1.0.0".
  - ECS (ecs/): World holds entities/components under one
    re-entrant lock, emits world.entity_created / removed and
    world.component_added / removed on its EventBus;
    World.identify() declares a heimr-* id plus a reality tag
    ("manifest" only for real worlds, else "potential") --
    the engine's own fact-vs-fiction firewall (MTOM zero-
    bleed) matches section 39 item 4's separation.
  - Multi-world (services/multi_world.py): MultiWorldHost
    serves several fully-isolated worlds in one process with
    a READ-ONLY cross-world query allowlist; cross-world
    writes are absent by construction; answers are never
    merged across worlds without their world_id + reality.
  - Event log (persistence/event_journal.py): opt-in durable
    append-only SQLite journal of EventBus envelopes
    (journal_seq is the replay order), plus the in-memory bus
    replay rings. Snapshot API: GET /world returns the
    WorldContextPacket (world_id, formatted_for_llm,
    focus_entities, present_entities, canonical_facts,
    recent_observations, open_contradiction_count).
  - Passive Oracle policy (oracle/passive_oracle.py): pure
    structured-data context builder over the memory store;
    the fork has always pinned use_turn_loop False (no LLM
    generation, no memory writeback) and still does.
  - Storage migrations (persistence/): world_store
    CURRENT_SCHEMA_VERSION 2 with forward migrations keyed by
    PRAGMA user_version and quarantine (never silent
    rewrite) of components stored under a NEWER schema;
    memory_store schema 1; event_journal schema 1.
- No WYRD server was running on purplelongship at audit or
  proof time (nothing listening on the configured loopback
  port 8765). The live proofs below therefore report the
  absence truthfully on the real CLI, and exercise the new
  adapter end-to-end against a staged instance of the real
  pinned engine under $HOME (~/wyrd-e07) -- never a fabricated
  presence.

## Diff against the pre-X.04 adapter (section 39 item 2)

The pre-X.04 surface was: a read-only /health probe
(MINIMUM_SERVER_VERSION 1.0.0, contract wyrd-http-v1), four
tools (world_get snapshot/facts, world_query with the turn
loop pinned off, world_set / world_observe posting /event
and signalling Verðandi content-free metadata only after an
ok confirmation), and an opt-in context bridge rendering one
bounded Passive Oracle item. Missing against section 39:
capability negotiation as a distinct step, namespaced
multi-world references, explicit truth classes, idempotency
/ revision / stale-write discipline, conflict resolution,
source-linked retrieval references, subscriptions /
streaming, and consumer seams. All of those are added below
IN the same four modules; the pre-existing behavior is
preserved (the whole pre-existing wyrd battery passes
unchanged).

## Registry (section 35 duty)

WYRD already has row 10 -- no new row. Because the build
changes the truth of the adapter description, row 10's
adapter cell in docs/modernization/INTEGRATION_MATRIX.md and
the WYRD entry in docs/modernization/integration-lock.json
are updated in place: adapter mode read-only -> full
read-write (the section 13 vocabulary; the journaled
confirmed write paths are real), adapter paths widened to
the four upgraded modules, verdict and verification notes
carry the X.04 execution. Pin, license, evidence stage and
verification status are unchanged; ledger counts are
unchanged (29 rows), so no count assertions move. The lock
was edited with its established compact format
(separators (',', ': '), ensure_ascii False) and the
pre-edit file byte-round-tripped under that format before
the edit; a field-level diff confirms only the WYRD entry's
adapter / verdict / verification fields changed.
CUSTOMIZATIONS.md gains one ledger row for the X.04 upgrade
(the tasking for this slice directs the row).

## Build (plugin-side only - section 39 items 3-10)

All in plugins/volmarr-core/wyrd.py unless noted; original
fork code written against the audited pinned contract.

- **Distinct adapter methods** (item 3): WyrdAdapter exposes
  liveness() (the pre-existing probe), capabilities()
  (negotiation, below), snapshot() / facts() / query()
  (read-only; query pins the Passive Oracle policy
  use_turn_loop False), subscribe() / poll_once() / stream()
  (subscriptions and streaming), and write_fact() /
  write_observation() (writes). The transport is injectable
  for contract proofs; the default is the pre-existing
  bounded loopback HTTP transport.
- **Capability negotiation + version truth** (items 3, 10):
  negotiate_capabilities() returns a versioned record
  (runeforge.wyrd.capabilities.v1) carrying the supported
  API versions, the minimum server version, the record
  schema 1.0.0, and the audited engine store schemas
  (world 2 / memory 1 / journal 1). An unreachable server
  yields compatible: null (unknown -- never dressed up); a
  reachable but incompatible server yields named mismatches
  and require_compatible() raises version_mismatch.
  check_record_schema_version() fails truthfully on a major
  record-schema mismatch: canonical data is never silently
  migrated between incompatible revisions.
- **Namespaces + source-linked references** (items 4, 6):
  make_ref() / parse_ref() mint and parse
  wyrd://<namespace>/<entity>#<component> references.
  snapshot() validates a caller-named namespace against the
  server-reported world_id and refuses a mismatch by name
  (namespace_mismatch) -- worlds are never silently mixed;
  snapshot and facts results carry the references alongside
  the data (wyrd_tools.py enriches world_get the same way,
  and world_query now returns its Passive Oracle
  provenance block).
- **Truth classes** (item 4): build_world_record() /
  validate_world_record() enforce exactly one of
  canonical_fact (durable; requires key, value, and a
  durable provenance source_ref), tentative_observation
  (never durable), quoted_evidence (must name the source it
  quotes), fictional_state (must carry reality "fictional";
  fictional records can never validate as canonical facts).
  Identity and private-relationship material is refused by
  name (private_memory_refused) at record build and at
  journal commit (item 9).
- **Transactional idempotent writes** (item 5): WyrdJournal,
  a durable SQLite (WAL, synchronous FULL) adapter-side
  journal -- the pinned /event contract confirms writes but
  exposes no transaction/idempotency surface, so the
  discipline lives in the adapter and says so. Commit order:
  private-kind refusal, idempotency (same key + same payload
  = duplicate, sender NOT called again; same key + different
  payload = idempotency_conflict), revision check (a stale
  expected revision is stale_write_rejected BEFORE any
  traffic), then the sender; the journal row lands only on
  server confirmation, in the same step that reports the new
  revision. An unconfirmed write leaves no trace and bumps
  no revision. replay() folds committed events in sequence
  order and is idempotent; a fresh journal over the same
  file (a restart) replays the identical state; journals at
  different paths are fully isolated (profile isolation).
  Verðandi is signalled from exactly one place -- after a
  confirmed journal commit -- through the pre-existing
  WorldChangeTelemetry seam (world_telemetry.py gains
  record_write(): change kind + journal revision only,
  content-free). Duplicates and unconfirmed writes never
  signal.
- **Conflict resolution** (item 7): resolve_conflict() takes
  competing records for one (namespace, entity, key) slot
  and resolves deterministically: truth-class rank
  (canonical > quoted evidence > tentative observation >
  fictional), then confidence, then later observed_at, then
  smallest record_id. Every competitor is returned in
  superseded with the full causal provenance list -- nothing
  is silently dropped.
- **Bounded prompt packets** (item 6): build_prompt_packet()
  carries at most max_items items and max_chars of text,
  priority-first, each item keeping its ref, provenance, and
  truth class; overflow is reported (truncated / omitted),
  never silent, and the whole world DB can never be dumped
  into a prompt through it. wyrd_context.py now routes its
  bounding through this builder (the historical render
  budget semantics are preserved exactly), so the opt-in
  context item's provenance travels with the text it bounds.
- **Subscriptions / streaming** (item 3): the pinned server
  exposes no push endpoint, so subscriptions are served by
  bounded polling over the verified /world snapshot:
  poll_once() diffs the canonical snapshot (fact keys whose
  values changed are named) and notifies state / facts
  subscribers; stream() yields change events across bounded
  polls. This is recorded as polling, never claimed as
  server push (ticket X04-T1).
- **Consumer seams** (item 8): CONSUMER_SEAMS +
  authorize_consumer() gate four seams -- heimdall
  (qualified observations in, canonical writes refused),
  sagnaskemma (fictional namespace only), voice_avatar
  (read-only), local_sensors (observations only WITH an
  uncertainty value, else uncertainty_required). Unknown
  consumers and unlisted operations are refused by name.
  The consumers themselves are not built.

## Live caller (section 28.2)

The existing hermes volmarr world family is extended
(health unchanged): world {status|capabilities|snapshot|
facts|packet|consumers}, all read-focused. Real proof in a
disposable profile home (/tmp/x04home, log
~/team01-x04-liveproof.log): status reports the audited pin
facts with server_present: false and capabilities
compatible: null -- no WYRD server is running on this
laptop and none is claimed; capabilities agrees; consumers
lists the four seams with their refusals; health keeps its
pre-existing truthful unreachable result (rc 1); snapshot
against the absent server fails truthfully (rc 1,
wyrd_protocol_error); the bare verb exits 2 with usage.

Staged-engine proof (harness ~/wyrd-e07/tests/
test_x04_live.py, scratch evidence in the engine clone,
E.07 precedent; log ~/team01-x04-live.log, full result
~/team01-x04-live-result.json): the REAL pinned server
(WyrdHTTPServer over a PythonRPGBridge world, ephemeral
loopback port, no auth) answers the new adapter end-to-end:
liveness healthy; capabilities compatible true; a
journal-backed write_fact commits at revision 1 and signals
Verðandi exactly once with content-free metadata (the
written value appears nowhere in the signal); the duplicate
write is a duplicate (no second signal); facts read-back
returns the written fact as the engine's own canonical
record (store mimir_canonical_store, schema_version 1.0.0);
the read-only query answers with writeback false and its
provenance block; replay after a journal restart reproduces
the state; an absent server reports liveness false and
capabilities compatible null. 1 passed.

## Tests and gate

- Targeted: tests/plugins/test_volmarr_wyrd_x04.py (17 new
  contracts) + test_volmarr_wyrd.py +
  test_volmarr_world_bridge.py +
  test_volmarr_integration_ledger.py +
  test_volmarr_production.py + test_volmarr_heimdall.py via
  scripts/run_tests.sh = 6 files, **101 passed / 0 failed**
  (log ~/team01-x04-targeted.log). The X.04 contracts pin
  every section 39 gate: version mismatch (API, server, and
  record-schema), fact/observation distinction (including
  tamper and fiction-dressing refusals), persistence across
  restart, idempotent event replay (duplicate commit calls
  the sender once; replay folds identically twice and after
  restart), stale write rejection before any traffic,
  profile isolation (separate journals), and agent prompt
  provenance (packet items carry refs + provenance; the
  Verðandi signal carries neither entity nor value).
- Full fork gate: **141 files, 1,218 passed / 7 failed /
  1 skipped** -- the X.03 baseline of 1,201 plus the 17 new
  X.04 tests; the 7 failures are name-identical to the known
  live-transport set (5x test_volmarr_core_plugin.py
  Verðandi socket, 1x test_volmarr_verdandi_stimuli.py,
  1x test_volmarr_voice_runner.py), ZERO regressions (log
  ~/team01-x04-fullcontracts.log; gate start 2026-11-14
  10:11:45 EST, load 1.75 / 1.49 / 2.02 at launch, no other
  campaign suite running).
- Bug fixed in scope: the first streaming diff compared
  canonical-fact KEY SETS, so a value change under an
  existing key emitted no changed_fact_keys; the diff now
  compares values per key (caught by the new contracts
  before banking).
- README untouched (sha256 336813d11bbe... before and
  after).

## Honest remainders / tickets

- X04-T1: server-push subscriptions. The pinned HTTP
  surface has no subscribe/stream endpoint, so X.04
  subscriptions are bounded polling over /world -- honest,
  but not push. If the engine grows an SSE/WebSocket change
  surface, re-point subscribe/stream at it and re-prove.
- X04-T2: staged-bridge packet shape. Against the staged
  PythonRPGBridge world, the /world packet carried an empty
  present_entities and did NOT change after a memory-store
  fact write (the write IS read back through /facts as a
  canonical record, and the query grounds in it), so live
  polling observed no packet change for that write
  (poll_after_write: [] in ~/team01-x04-live-result.json).
  Change detection is proven against the documented packet
  shape in the fork contracts; packet enrichment is the
  engine project's own line, not something this adapter may
  fake.
- X04-T3: the write journal is adapter-side because the
  pinned /event contract has no idempotency-key or revision
  surface. If the engine grows native idempotency, fold the
  journal semantics into the server contract and retire the
  duplication deliberately, with proofs.
- X04-T4: fictional-state writes to a LIVE server are not
  offered: fictional records validate and resolve locally
  and the Sagnaskemma seam owns its namespace, but writing
  game state into a real-world server would mix realities.
  A dedicated fictional-namespace world/server pairing is
  future work (with section 40).
- X04-T5: the engine's own suite was not re-run in this
  slice (no pin movement -- HEAD re-measured AT the pin;
  E.07's suite proof at this same HEAD stands, including
  its named remainder E07-T1, the Dusk kway-merge timing
  benchmark). The X.04 live harness proves the fork-facing
  contracts against the real pinned server.
- The section 32 release scorecard still reads NOT
  releasable; X.04 changes the WYRD adapter only.
