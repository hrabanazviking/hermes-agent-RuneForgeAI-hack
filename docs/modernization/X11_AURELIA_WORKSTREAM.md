# X.11 Aurelia Sensations Server — ecosystem workstream 11 of 15 (Team 01, 2026-11-14)

Roadmap section 46 executed: an opt-in, default-off, local-only
private state-simulation connector over the Hermes plugin
boundary, following the X.09/X.10 pattern. Slice discipline: a
new `aurelia` module + `hermes volmarr aurelia
{status|catalog|plan}` CLI family in volmarr-core, two
default-off `aurelia_*` config keys, one capability-bus seed
descriptor, exactly one CUSTOMIZATIONS.md ledger row, README.md
byte-identical (sha256
336813d11bbe5aa2ff745b4a4bc3abcf2a283cd13971c0c11d061377129db7f3,
verified before and after). NO integration-lock.json or
INTEGRATION_MATRIX.md change: neither holds an Aurelia row, and
none was invented (recorded honestly per the section 35 duty).
Commit-only on `yrsa/hermes-team-01`; the keeper banks serially.

PRIVACY LAW (section 46): Aurelia data is intimate and private.
This record, the connector and its tests carry interfaces and
integration facts only — no sensation data, private
configuration values, character data or interaction history
appears anywhere in this repo. The staged tree's `data/` and
`config/` contents were never opened during the audit or by
the connector.

## Audit (from source structure, not README)

- Source: `hrabanazviking/RuneForgeAI-Aurelia-Sensations-Server`
  (PRIVATE), cloned fresh under $HOME at `~/aurelia-x11`; HEAD
  measured `d6c2632435bd3034dfcd34df1ba1e9a7a799e947`
  (identical to the `git ls-remote` HEAD at audit time).
- Server: `aurelia_agent_server.py` (2,200 lines) — a
  long-running FastAPI application, title "Aurelia Agent
  Server", version **1.0.0**, keeping one agent alive over the
  `female_motivation` package. The audited tree carries **303
  Python modules**; requirements pin fastapi / pydantic /
  uvicorn / numpy / scipy / pyyaml / httpx / websockets.
- License text-verified at the audited HEAD: `LICENSE` is the
  full Apache-2.0 text (201 lines), sha256
  `c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4`.
  No Aurelia source is copied or vendored by this slice.
- Deployment: the tree's own systemd template
  (`deploy/aurelia-agent.service.in`, rendered by
  `deploy/render_unit.py`, default port 8001) targets **Mimir**
  — the live server lives on the Pi, not on this laptop. No
  Aurelia process or listener was found on purplelongship, and
  no live server was contacted by this slice (ticket X11-T1).
- Real endpoint surface at the audited HEAD (route decorators
  only): `GET /health`, `GET /metrics`, `GET /stability`,
  `GET /state`, `GET /senses`, `GET /config` + `POST /config`,
  `POST /pause`, `POST /resume`, `POST /degrade` + `GET`,
  `POST /tick`, `POST /stimulation`, `GET /attire` + `POST`,
  `GET /dialogue`, `POST /enact`, `POST /orgasm`,
  `POST /penetrate`, `POST /event`, `POST /save`,
  `GET /report`, `GET /dashboard`, `GET /audit`, interview and
  profile families, `GET /utterance`, `GET /traces`,
  `GET /slo`. The section 46 illustrative contract
  (`state.snapshot`, `state.event`, `simulation.step`,
  `simulation.pause`, `health`) maps onto real endpoints:
  /state, /event, /tick, /pause + /resume, /health.
- Auth: no API-key or bearer check was found in the server
  module's route layer at the audited HEAD; the deployment
  model is a private-network service behind the owner's
  machine accounts (ticket X11-T2). This connector therefore
  binds no transport at all.

## Build (section 46 items 1-10)

`plugins/volmarr-core/aurelia.py` (new, original code):

- Status/catalog (items 1-2, 4): `aurelia_status` reports
  unconfigured vs configured truthfully; when configured it
  measures the REAL staged tree's structure only — .git HEAD
  vs the audited HEAD, the FastAPI version string in
  `aurelia_agent_server.py`, the LICENSE sha256, and the
  Python module count by filename. `data/` and `config/`
  files are never opened, so intimate content cannot egress
  via status. `contract_catalog` lists the nine section 46
  contract kinds with their audited endpoint basis; supported:
  health, state snapshot, state event, simulation step,
  simulation pause, state save. Refused, by name and by
  design: direct device control, canon edit, external egress.
- Identity separation (item 3): authored identity stays
  human-edited canon; `check_scope` refuses any simulated
  state targeted at `authored_identity`/`canon`/`soul`
  (`simulated_state_not_canon`) — this connector never edits
  SOUL.md or any canonical identity file.
- Per-persona scopes (item 5): a persona may access only its
  own simulated-state namespace; cross-persona access is
  refused by name (`cross_persona_scope_refused`).
- Content-free lifecycle metadata (item 6): `lifecycle_record`
  carries only persona scope, contract kind and a truncated
  hash of the event id — safe for Verdandi-style lifecycle
  records and audit receipts; intimate contents never appear.
- Local-only routing (item 7): no network, no subprocess, no
  external path exists in the connector; every egress verb
  (publish/upload/share/broadcast/sync_cloud) is refused by
  name in catalog and planner alike.
- Guarded transitions (item 8): `build_event_plan` is a pure
  deterministic plan over {kind, event_id, scope} ONLY — any
  content field (payload/content/sensation/...) is refused by
  name (`intimate_content_not_accepted`). Events require an
  idempotent event id and a consent scope the persona holds;
  duplicate ids are refused as idempotent duplicates; planned
  events carry provenance (audited HEAD + endpoint basis),
  a bounds-checked flag and a content-free audit receipt.
  Consent is explicit and revocable (`grant_consent` /
  `revoke_consent` local store; revocation makes later plans
  refuse the scope). `write_checkpoint` / `resume_plan`
  persist a plan's completed indexes locally for replay and
  exact restore.
- Output consumers only (item 9): presentation/voice are not
  granted any control surface here; `direct_device_control`
  is a refused contract kind — no microphone, avatar,
  messaging or device control exists in this connector.
- Experimental honesty (item 10): every record carries
  `experimental: true` and `production_ready: false`; no
  claims about real human psychology are made anywhere.
- Wiring: capability-bus seed descriptor `volmarr-aurelia`
  0.1.0 (in-process transport, local-private only, adapter at
  the volmarr-core plugin.yaml where this connector lives;
  the two `service_count == 4` assertions in
  `test_volmarr_capability_bus.py` move to 5 with a version
  assertion added — the X.09/X.10-style genuine-change
  update); CLI family `hermes volmarr aurelia
  {status|catalog|plan}` mirroring the scribing verbs (plan
  runs the labelled SYNTHETIC_EVENTS set: 2 planned,
  1 consent refusal, 1 contract refusal, 1 egress refusal);
  `aurelia_enabled` / `aurelia_root` config keys, both
  default-off/empty.

## Live caller (section 28.2)

`hermes volmarr aurelia {status|catalog|plan}` proven in
disposable HERMES_HOME homes on disk (log
`~/team01-x11-liveproof.log`), using the team-01 checkout's own
`hermes` binary via `scripts/run-in-hermes-env`:

- Unconfigured home: status truthful (`enabled: false`,
  `configured: false`, tree `not_configured`,
  `production_ready: false`); catalog lists the nine contract
  kinds with device control / canon edit / egress refused;
  plan plans the labelled synthetic set (2 planned,
  1 `consent_scope_required`, 1 `contract_refused`,
  1 `egress_refused`); bare verb rc 2. All other verbs rc 0.
- Configured home (`aurelia_enabled: true`,
  `aurelia_root: ~/aurelia-x11` under
  `plugins.entries.volmarr-core.settings`): status measures
  the REAL staged tree — `head_matches_audited: true` at
  d6c2632435bd, `server_version: 1.0.0` read from the tree's
  own server module, `license_matches_audited: true`
  (sha256 c71d239df917...), `module_count: 303` Python
  modules.

## Tests and gate

- New contracts: `tests/plugins/test_volmarr_aurelia_x11.py`
  (9 tests) pinning the section 46 gates — unconfigured
  truthfulness, configured structural measurement with the
  privacy canary (a canary sensation file staged under a fake
  tree's `data/` never appears in status/catalog/plan
  output), catalog refusals, per-persona scope isolation +
  canon separation, guarded event plans (idempotency, consent,
  content-field, cross-persona and egress refusals by name),
  content-free lifecycle records, consent grant/revoke,
  checkpoint resume after interruption, and the CLI family.
- Targeted (log `~/team01-x11-targeted.log`): 4 files
  (aurelia_x11 + capability_bus + scribing_x10 +
  astrology_x09) = **47 passed / 0 failed** (9 new X.11
  contracts; capability_bus carries the seed-count update).
- Full contract gate (log `~/team01-x11-fullcontracts.log`),
  run serialized on an idle laptop: in the canonical scope
  (test_volmarr_*.py + the two kista files): **148 files =
  1,292 passed / 7 failed / 1 skipped** — the X.10 baseline
  (147 files = 1,283 / 7 / 1) plus exactly the 9 new X.11
  contracts, the 7 failures name-identical to the known
  live-transport set (5x test_volmarr_core_plugin.py, 1x
  test_volmarr_verdandi_stimuli.py, 1x
  test_volmarr_voice_runner.py), ZERO regressions.

## Honest remainders / tickets

- X11-T1 (live transport): the connector plans and records
  locally; it binds NO live transport. The real server runs
  on Mimir (port 8001 by its systemd template); a loopback
  health/snapshot binding from Hermes on that device is
  future work and was not audited live from this laptop.
- X11-T2 (server auth): no API-key/bearer check was found in
  the audited server module's route layer; the service's
  protection is its private-network deployment. Any future
  live binding must re-audit auth before use.
- X11-T3 (registry): no integration-lock or INTEGRATION_MATRIX
  row exists for Aurelia; none was invented. A pin row should
  be taken only by a future audited update that binds a real
  runtime interface.
- X11-T4 (engine suite): the Aurelia tree's own test suite
  (female_motivation/tests) was not run by this slice — the
  audit was structural/interface-level per the section 46
  privacy law, and the suite exercises simulation internals
  outside this connector's scope.
- X11-T5 (presentation consumers): voice/avatar presentation
  consumers of Aurelia state are named in section 46 item 9
  but no consumer binding is built here; only the refusal of
  direct control is enforced.
- The section 32 release scorecard still reads NOT
  releasable (0 met / 10 unmet / 5 deferred);
  `production_ready` stays False in every X.11 record.
