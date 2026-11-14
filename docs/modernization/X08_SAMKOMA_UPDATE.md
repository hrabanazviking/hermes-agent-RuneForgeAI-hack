# X.08 Samkoma — ecosystem workstream 8 of 15 (Team 01, 2026-11-14)

Roadmap section 43 executed: Samkoma as evidence-aware planning —
a Hermes tool, not unapproved event publication. Slice discipline:
plugin-side only in `plugins/volmarr-core` (new `samkoma.py`,
original code, nothing vendored), registry in place (new lock
entry + INTEGRATION_MATRIX row 30; no Samkoma row existed before
this slice — grep-verified), exactly one CUSTOMIZATIONS.md ledger
row, README.md byte-identical (sha256
336813d11bbe5aa2ff745b4a4bc3abcf2a283cd13971c0c11d061377129db7f3,
verified before and after). Commit-only on
`yrsa/hermes-team-01`; the keeper banks serially.

## Audit (re-measured, not inherited)

- Source: `hrabanazviking/RuneForgeAI-Samkoma`, main HEAD
  re-measured by `git ls-remote` 2026-11-14:
  `aa84ad3308b1b95b0c98ac572587b5bf9a573224` (no tags). Tree cloned
  under $HOME at `~/samkoma-x08`, HEAD verified identical.
- License text-verified at the tree: `LICENSE` is the full
  GPL-3.0 text (sha256
  3972dc9744f6499f0f9b2dbf76696f2ae7ad8af9b23dde66d6af86c9dfb36986);
  pyproject declares SPDX `GPL-3.0-only` and records the history:
  GPL-2.0 by Volmarr's 2026-10-24 decision, relicensed to GPL-3.0
  by his explicit ruling 2026-10-29 (commit `078fec5`). No Samkoma
  source is incorporated into this fork, so no license conflict
  arises; the adapter is original code against the section 43
  contract.
- Real API/models read at the audited HEAD (src/gpa):
  - Frozen contract: OPENAPI.json counted at the tree — 202 paths
    / 230 schemas; candidate and source routes live under
    `/api/v1/groups/{group_id}/candidates|sources` (list, status,
    detail, approve, merge, merge-event, reject; sources include
    paste/upload/link/newsletter/voice/live ingest, extract,
    calendar-sync, restore).
  - Candidate (`models/groups.py`): a draft in a review queue
    (status pending/approved/rejected/merged) whose per-field
    provenance rows carry value, confidence, quote and a
    `supported` verdict; approval mints the resulting entity in
    the same transaction (`resulting_entity_type/id`).
  - Source (`models/sources.py`): carries the permission record
    (`granted_by`, `granted_scope`), ordered chunks with raw +
    parsed timestamps, and tombstone/restore — a deleted source
    keeps its provenance trail.
  - Lifecycles: Event (+ Recurrence, CalendarFeed, Announcement-
    Draft, EventChange) in `models/events.py`; Task / Decision
    (supersede chains) / OpenQuestion / Poll in
    `models/planning.py`. Notifications travel by outbox only
    (`models/notifications.py`: queued → held → sent), never
    inline. Google Calendar is a one-way-out connector service
    (`services/google_calendar.py`) behind a sealed per-group
    integration — connector-specific, exactly as item 6 requires.
  - Approval law at the audited HEAD is B-203 (Phase 18/19): one
    approval law for every principal — an approver-role seat may
    approve through the same operation; a default seat key cannot
    (`errors.py: seat_cannot_approve`, 403). The README's older
    "a seat can never approve" line is superseded by B-203 in
    code; this record follows the code.
  - Architecture laws verified in code: routers thin (a test
    verifies no router imports a model), rules in services,
    `deps.py` the only auth door, one AI adapter with live /
    fixture / mock drivers (the demo runs fully offline).
- Samkoma's own suite re-run at the audited HEAD on
  purplelongship (uv sync + pytest, log `~/samkoma-x08-suite.log`):
  **1,128 passed / 96 failed / 8 skipped / 3 errors** in 339 s.
  Root-caused, not waved away:
  - 89 of the 96 failures (and the 3 signed-release errors) share
    ONE root: `ValueError: internal operation 'test.echo' has no
    MCP tool annotation` — in full-suite runs a test-fixture
    operation leaks into the real MCP registry and every MCP
    surface refuses to build. Proven an isolation artifact of the
    full-suite ordering in this environment: the same files pass
    standalone (`tests/test_mcp_candidates.py` green in a
    3-file run). Ticket X08-T1 for the Samkoma line.
  - 6 reminder failures + 1 task failure reproduce standalone and
    are date-sensitive fixtures: a directly created task reads
    `overdue: True` against the run date, and reminder
    materialisation finds no rows for fixture events whose dates
    have passed. Ticket X08-T1.
  - The README claims 1,056 passing at the Phase 18 gate and
    states plainly that Phase 19's closing full-suite proof is
    still owed. Both numbers are recorded as claimed vs measured;
    neither is dressed up. `production_ready` stays False.

## Registry (section 35 duty)

- `integration-lock.json`: NEW Samkoma entry appended (engines
  29 → 30), field-diff asserted: every prior entry and every
  other top-level key is unchanged. No pin taken (`pinned: null`)
  — a separate FastAPI service with no installable Hermes-side
  package; the audited HEAD is recorded, no source incorporated.
  Adapter mode recorded as the ledger-classified `prototype`.
- `INTEGRATION_MATRIX.md`: NEW row 30 added in place (diff is
  exactly +1 line; no other row changed).
- `COMPONENT_LICENSES.md`: unchanged — no pin taken and no source
  incorporated (the X.01–X.03 no-pin precedent).
- Ledger guard updated per precedent: `tests/plugins/
  test_volmarr_integration_ledger.py` counts 29 → 30 (names,
  engine_count, verified count, CLI payload).

## Build (plugin-side only — section 43 items 1–10)

`plugins/volmarr-core/samkoma.py` (original code):

- `source.search` (read-only): substring search over source
  receipts; returns receipts, never derived facts.
- `candidate.extract` (proposal-only): builds a candidate whose
  fields are citation-verified — a field is `supported` ONLY when
  its quote is a non-empty verbatim substring of the cited source
  text; a datetime field without a timezone marker is marked
  unsupported (`timezone_missing`) — time zones are handled,
  never guessed (item 7).
- `candidate.preview` (read-only): shows the draft AS a draft
  (`is_fact: False`, `published: False`, status stays pending),
  flags possible duplicates against existing candidates and
  names every unsupported field (items 3, 7).
- `review.status` gate (item 4): manual approval is EVALUATED
  with refusals by name — `wrong_account` (acting account is not
  the configured account), `role_not_authorized`,
  `seat_cannot_approve_own_draft`. A passing approval converts
  NOTHING in this slice (`conversion_performed: False`,
  `published: False`) and unsupported fields stay unsupported in
  the record — approval never launders a claim into a fact.
- `proposal.draft` (items 8–9): fully offline drafting into a
  local store with a deterministic idempotency key (sha256 of the
  candidate's canonical form); a retry returns the same receipt
  with `duplicate: True` and writes no second record.
- Source deletion (item 10): `respect_source_deletion` removes
  every local proposal citing a deleted source (the same call
  serves a room-consent withdrawal).
- Items 5–6 by recorded gate, not by transport: Samtal room
  context stays behind the default-off `samkoma_room_consent`
  key and connector replication behind the default-off
  `samkoma_connector_authorized` key; the adapter reads no room
  and performs no sync in this slice, and says so in its status.
- Five new config keys in `plugin.yaml`, all default-off/empty:
  `samkoma_enabled`, `samkoma_root`, `samkoma_account`,
  `samkoma_room_consent`, `samkoma_connector_authorized`.
- Publish verbs refused by name in the catalog: event.publish,
  calendar.create, reminder.create, task.create,
  announcement.publish, connector.sync. There is no code path in
  this adapter that creates a calendar event, reminder, task or
  announcement.

## Live caller (section 28.2)

`hermes volmarr samkoma {status|catalog|preview}` — proven in
disposable HERMES_HOME homes (log `~/team01-x08-liveproof.log`):

- Unconfigured home: status truthful (`enabled: false`,
  `configured: false`, tree `not_configured`,
  `production_ready: false`, `publishes_anything: false`);
  catalog lists the five operations with modes and the six
  refused publish verbs; preview on the labelled synthetic
  receipt shows `unsupported_fields: ["place"]`,
  `is_fact: false`, `published: false`; bare verb rc 2.
- Configured home (`samkoma_enabled: true`,
  `samkoma_root: ~/samkoma-x08`, `samkoma_account` set): status
  measures the REAL staged tree — head == audited HEAD
  (`head_matches_audited: true`), LICENSE sha256 matches the
  audited text, OPENAPI counted live at 202 paths / 230 schemas.
- No verb creates or publishes anything: the family's only
  outputs are status records, the catalog, and a preview of a
  labelled synthetic candidate.

## Tests and gate

- New contracts: `tests/plugins/test_volmarr_samkoma_x08.py`
  (12 tests) pinning the section 43 gates — citation integrity,
  unsupported-stays-unsupported, timezone refusal, duplicate
  flagging, wrong-account / role / seat-self-approval refusals,
  approval-converts-nothing, idempotent receipts, source-deletion
  respect, registry entry, CLI family.
- Targeted (log `~/team01-x08-targeted.log`): 3 files
  (x08 + integration_ledger + ravens_x07) = 37 passed / 0 failed.
- Full contract gate: see the banking note appended by the
  keeper; run on the committed tree via `scripts/run_tests.sh`
  (log `~/team01-x08-fullcontracts.log`) against the X.07 baseline
  of 144 files = 1,249 passed / 7 failed / 1 skipped, the 7 being
  exactly the known live-transport set.

## Honest remainders / tickets

- X08-T1 (Samkoma project line): the audited HEAD's own suite is
  not clean in this environment — the full-suite `test.echo` MCP
  registry leak (89 failures, one root; files pass standalone)
  and date-sensitive reminder/task fixtures (7 failures). The
  Phase 19 closing full-suite proof the README says is owed
  belongs to the same line. Until then `production_ready` stays
  False everywhere in this slice's records.
- X08-T2: conversion — an approved candidate becoming a real
  event/task/decision through Samkoma's API — is NOT built. It
  needs its own separately authorized slice with the service
  running and account-scoped credentials.
- X08-T3: no live Samkoma service is bound; the adapter measures
  a staged checkout for status and works on receipts/candidates
  as data. A running-service (HTTP or MCP) proof is future work.
- X08-T4: Samtal room transport and connector replication
  (Google Calendar et al.) are recorded gates only — consent and
  authorization keys exist, no transport is wired, no sync is
  performed or inferred.
- X08-T5: item 7 depth — partial approvals, owner changes,
  cancellation and recurrence-conflict handling exist in
  Samkoma's own lifecycles (audited above); the adapter surfaces
  duplicates/timezones as preview flags only and models none of
  those transitions itself.
