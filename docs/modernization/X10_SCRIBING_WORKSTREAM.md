# X.10 Mythic Scribing Foundry — ecosystem workstream 10 of 15 (Team 01, 2026-11-14)

Roadmap section 45 executed: an opt-in, default-off, local-only
private writing-workflow connector over the Hermes plugin
boundary, following the X.08/X.09 pattern. Slice discipline: a
new `scribing` module + `hermes volmarr scribing
{status|catalog|plan}` CLI family in volmarr-core, two
default-off `scribing_*` config keys, one capability-bus seed
descriptor, exactly one CUSTOMIZATIONS.md ledger row, README.md
byte-identical (sha256
336813d11bbe5aa2ff745b4a4bc3abcf2a283cd13971c0c11d061377129db7f3,
verified before and after). NO integration-lock.json or
INTEGRATION_MATRIX.md change: neither holds a Foundry row, and
none was invented (recorded honestly per the section 35 duty).
Commit-only on `yrsa/hermes-team-01`; the keeper banks serially.

PRIVACY LAW (section 45): the Foundry is private. This record,
the connector and its tests carry interfaces and integration
facts only — no manuscript text, private author notes, corpus
content, or Foundry test output appears anywhere in this repo.

## Audit (from source, not README)

- Source: `hrabanazviking/Mythic-Scribing-Foundry` (PRIVATE),
  cloned fresh under $HOME at `~/scribing-x10`; HEAD measured
  `9da00e5ba77c39a43c670e9e2f7398dbeaa4c594` (identical to the
  `git ls-remote` HEAD at audit time). Package `mythscribe`
  version 0.1.0 in `pyproject.toml` and `mythscribe/__init__.py`.
- License: Proprietary — declared as license text in
  `pyproject.toml` only; the tree carries NO LICENSE file.
  No Foundry source is copied or vendored by this slice.
- Real CLI surface at the audited HEAD (click group
  `mythscribe`, pipeline INGEST -> ... -> PUBLISH): the
  `ingest`, `concepts`, `create-book`, `outline`, `draft`,
  `draft-status` and `draft-retry` commands carry real logic;
  worker groups add real `propose-books`/`book-candidate`
  (pathfinder), council review commands, keeper `test` /
  `analyze` commands, publisher `build-book` and models `cost`
  commands. The main `verify` and `revise` commands are still
  S03 stubs announcing NOT_IMPLEMENTED — so claim verification
  and revision are UNSUPPORTED in this connector, by audit.
- Module facts the build rests on: `well/ingest` +
  `well/search` SemanticIndex (research indexing); `architect`
  package + outline CLI (outlining/planning); `scribe/jobs`
  JobStore with per-book draft jobs and retry (drafting +
  resume shape); `scribe/voice` + `scribe/rules` (style
  consistency, module-level, no dedicated CLI verb); `council`
  editors/framework (critique); `publisher/exporters` with
  Epub/Pdf/Docx exporters + build-book (publication
  PREPARATION); `models/cost` CostLedger (cost receipts). The
  Foundry's own publisher `publish` command exists upstream;
  this connector never exposes it (section 45 item 10).

## Build (section 45 items 1-10)

`plugins/volmarr-core/scribing.py` (new, original code):

- Status/catalog (items 1-2): `scribing_status` reports
  unconfigured vs configured truthfully; when configured it
  measures the REAL staged tree's structure only — .git HEAD
  vs the audited HEAD, package version from its pyproject,
  Python module count by filename. Manuscript/corpus files are
  never opened, so private content cannot egress via status.
  `steps_catalog` lists the nine section 45 step kinds with
  their audited basis; supported: research indexing, outlining,
  planning, drafting, style consistency, critique, publication
  preparation. Unsupported, by name: claim verification and
  revision (stub CLIs at the audited HEAD).
- Namespace separation (item 3): `assign_namespace` defaults
  to `author_work`; a manuscript-kind item requested into
  `persona_core` is refused by name
  (`manuscript_not_persona_instruction`) — a manuscript is
  never a persona instruction by default.
- Job planning (items 4, 7, 9): `build_job_plan` is a pure
  deterministic plan: unknown kinds, unsupported kinds and
  every publish verb are refused by name; planned steps carry
  provenance (creator, book ref, audited HEAD, audited basis),
  a chapter checkpoint id, and a cost-receipt requirement
  (mirroring the Foundry CostLedger; `cost_receipt` issues
  local-only receipts). Plans run no Foundry code and read no
  manuscript; bounded section retrieval against a live Foundry
  is NOT built (ticket X10-T3).
- Suggestions (item 5): `draft_suggestion` stores suggestions
  ONLY in a local store's `suggestions/` area, status
  `proposed`, idempotent by content key; acceptance is a
  separate explicit act (`accept_suggestion`) and
  `rollback_suggestion` restores the exact previous text
  (editorial rollback).
- Citations (item 6): `verify_citation` — a citation is
  supported ONLY when its quote is a verbatim substring of the
  source text within the 250-char quote-length policy;
  fabrication, over-length and missing quotes are refused by
  name. Image/alt-text records, translation lineage and
  document-format validation are NOT built (ticket X10-T4).
- Checkpoints (item 7): `write_checkpoint` / `resume_plan`
  persist a plan's completed step indexes locally; resume
  returns exactly the uncompleted steps.
- Privacy (items 2, 10): local-only by construction — no
  network, no subprocess, no publish/upload/distribute/release
  path exists; `PUBLISH_VERBS_REFUSED` names them in the
  catalog and the planner refuses them.
- Wiring: capability-bus seed descriptor `volmarr-scribing`
  0.1.0 (in-process transport, local-private only, adapter at
  the volmarr-core plugin.yaml where this connector lives;
  the two `service_count == 3` assertions in
  `test_volmarr_capability_bus.py` move to 4 with a version
  assertion added — the X.09-style genuine-change update);
  CLI family `hermes volmarr scribing {status|catalog|plan}`
  mirroring the astrology verbs (plan runs the labelled
  SYNTHETIC_STEPS set: 2 planned, 1 unsupported refusal,
  1 publish refusal); `scribing_enabled` / `scribing_root`
  config keys, both default-off/empty.

## Live caller (section 28.2)

`hermes volmarr scribing {status|catalog|plan}` proven in
disposable HERMES_HOME homes on disk (log
`~/team01-x10-liveproof.log`), using the team-01 checkout's own
`hermes` binary (the `~/.local/bin/hermes` shim points at
another team's checkout and was not used):

- Unconfigured home: status truthful (`enabled: false`,
  `configured: false`, tree `not_configured`,
  `production_ready: false`); catalog lists the nine step
  kinds with claim verification + revision unsupported; plan
  plans the labelled synthetic set (2 planned, 1 refused
  `step_unsupported`, 1 refused `publish_refused`); bare verb
  rc 2. All other verbs rc 0.
- Configured home (`scribing_enabled: true`,
  `scribing_root: ~/scribing-x10`): status measures the REAL
  staged tree — `head_matches_audited: true` at
  9da00e5ba77c, `package_version: 0.1.0` read from the tree's
  own pyproject, `module_count: 70` Python modules.

## Tests and gate

- New contracts: `tests/plugins/test_volmarr_scribing_x10.py`
  (8 tests) pinning the section 45 gates — unconfigured
  truthfulness, configured structural measurement with the
  private-source egress canary (a canary manuscript staged in
  a fake tree never appears in status/catalog/plan output),
  namespace separation, citation fabrication + quote-policy
  refusal, unsupported steps and publish refusal by name,
  checkpoint resume after interruption, suggestion separation
  + idempotence + editorial rollback, and the CLI family.
- Targeted (log `~/team01-x10-targeted.log`): 4 files
  (scribing_x10 + capability_bus + astrology_x09 +
  samkoma_x08) = **50 passed / 0 failed** (8 new X.10
  contracts; capability_bus carries the seed-count update).
- Full contract gate (log `~/team01-x10-fullcontracts.log`),
  run serialized on an idle laptop (load 0.22 at launch, no
  other campaign suite running): in the X.09-canonical scope
  (test_volmarr_*.py + the two kista files): **147 files =
  1,283 passed / 7 failed / 1 skipped** — the X.09 baseline
  (146 files = 1,275 / 7 / 1) plus exactly the 8 new X.10
  contracts, the 7 failures name-identical to the known
  live-transport set (5x test_volmarr_core_plugin.py, 1x
  test_volmarr_verdandi_stimuli.py, 1x
  test_volmarr_voice_runner.py), ZERO regressions.

## Honest remainders / tickets

- X10-T1 (Foundry line): the `verify` and `revise` CLIs are
  stubs at the audited HEAD, so claim verification and
  revision stay unsupported here until the Foundry wires them
  to its contradictions/terminology and reforger modules.
- X10-T2 (licensing): the Foundry declares Proprietary in
  pyproject only, with no LICENSE file and no integration-lock
  or matrix row; a pin/license row should be taken only by a
  future E-series-style audited update, not invented here.
- X10-T3 (live binding): the connector plans and stores
  locally; it does not yet invoke a live Foundry (bounded
  section retrieval, real JobStore resume and CostLedger
  receipts against a running mythscribe are future work).
- X10-T4 (section 45 item 6 remainders): image/alt-text
  records, translation lineage and EPUB/print format
  validation are not built; the Foundry exporters exist but
  no Hermes-side validation surface does.
- X10-T5 (scale gate): the roadmap's 100 MB source-corpus
  indexing gate is a Foundry-side property and was not
  exercised by this connector slice.
- The section 32 release scorecard still reads NOT
  releasable (0 met / 10 unmet / 5 deferred);
  `production_ready` stays False in every X.10 record.
