# E.16 Identity / agency + prompt live-hook reconciliation - audit record (Team 01, 2026-11-14)

**Outcome: RECONCILIATION EXECUTED - no new wiring built, no
pin moved, no fork code changed.** Row 26 (persistent
identity / affect / goals / agency) is reconciled surface by
surface against the live composition: the prompt path has
exactly one owner (`PresentStateBridge`), the hook inventory
is proven two independent ways (recorder ctx + real
PluginManager), and a live harness drove the real turn path
end to end - session start, a completed turn, a goal tool
round-trip, and a REAL agency cycle whose journal record
reached the next turn's prompt packet. The family's one
large contract-only remainder is named plainly: the agency
orchestrator itself has NO production caller (ticket
E16-T1, design recorded below). Row 20 (ChatIndex) is
audited in the same slice: HEAD re-measured at its E0 first
pin, license verified at text level (Apache-2.0, with a
ticketed setup.py MIT-classifier conflict, E16-T5), kept
design-only - no adapter built, because the fork's P2 line
already carries a deterministic local retriever and
ChatIndex builds its tree with hosted-LLM calls.

## Scope and method

- Row 26 governing records: INTEGRATION_MATRIX.md row 26
  and the integration-lock.json row "Persistent identity /
  affect / goals / agency" (adapter paths identity.py,
  affective.py, goals.py, agency.py; plugin volmarr-core
  0.26.0). The inventory below covers those four modules
  plus every module that carries their live path:
  affective_bridge.py, pad.py, intrinsic_goals.py,
  agency_contracts.py, agency_routines.py (+ routines.py),
  agency_cycle_detail.py, context_packet.py,
  present_state.py, persona_live.py, persona_runtime.py,
  and the adjacent packet family wired in the same
  composition tuple. Tree: worktree ~/hermes-team-01 at
  banked main 404a97dba1 (E.15 closure), clean before edits.
- Classification law (roadmap section 28.2): a surface is
  declared live only where a real caller on a real path is
  named. Classes used: LIVE-DEFAULT (fires under banked
  plugin.yaml defaults), LIVE-OPT-IN (live code path gated
  by a default-off flag), LIVE-THROUGH-X (no surface of its
  own; reached through a named live consumer),
  CONTRACT-ONLY (contracts/tests only, no production
  caller). "Live" never means "enabled on Volmarr's own
  profile" - no profile on this laptop was reconfigured.

## The composition, counted (not asserted)

`plugins/volmarr-core/__init__.py::register(ctx)` is the
single composition root. Measured this slice:

- 78 modules in plugins/volmarr-core/; register()
  instantiates 39 bridges and wires them three ways:
  hooks, the PresentState packet tuple, and tool/CLI
  registrars.
- Hook registrations, counted by a recorder ctx passed to
  the real register() AND read back from a real
  PluginManager after discover_and_load() - identical both
  ways: on_session_start 14, on_session_end 3,
  on_session_finalize 1, pre_tool_call 1, post_tool_call 3,
  pre_llm_call 2, post_llm_call 2 (26 callbacks total).
- Packet sources: 32 named `packet_items` callables in the
  PresentState composition tuple, plus PresentStateStore's
  own - 33 sources feeding ONE ContextPacketBuilder.
- Tools registered: 11 (goal_get, goal_create, goal_update,
  relationship_get, relationship_upsert, entity_heartbeat,
  entity_sleep_cycle, world_get, world_query, world_set,
  world_observe). CLI: one root, `hermes volmarr`, whose
  subcommands include `identity health` and `agency
  {status|install|run|evaluation}` plus the section 21
  inspection family served by surface_reconciliation.py.
- System-prompt sections at banked defaults: ZERO
  (PluginManager._system_prompt_sections == {} and the
  recorder saw no section registration) - persona-live is
  not owner by default, so a stock profile stays stock
  (the W05 gate's stock proof posture, re-measured here).

## Row 26 inventory - live vs contract-only, per surface

### The four lock-named modules

1. **identity.py - LIVE-DEFAULT (session + operator),
   prompt-silent by design.** IdentityBridge.hooks() is
   exactly (("on_session_start", on_session_start),),
   registered in the composition; identity_enabled
   defaults true. The hook ensures entity/entity.yaml
   (create-once, validate-thereafter, never silently
   replaced). There is NO packet_items and no tool: the
   identity document never enters the prompt - the module
   header's own words, "without owning persona text".
   The read surface is operator-side and live:
   probe_identity via `hermes volmarr identity health`.
   Harness: after one manager on_session_start the file
   exists and the probe reads healthy (name "undecided",
   the create-once default).
2. **affective.py - LIVE-THROUGH-BRIDGE, opt-in.** The
   2,073-line regulator (adapted-module provenance,
   matrix row 23) has no bridge, hook, or packet surface
   of its own. Its only consumers are affective_bridge.py
   (AffectiveNervousSystem, load_affective_config) and
   pad.py (PadEmotionalLayer). AffectiveBridge registers
   five hooks and IS in the packet tuple, but
   affective_enabled defaults FALSE: at defaults the
   bridge's pre_llm_call returns None (observer no-op),
   packet_items returns []. Harness contrast: default
   bridge enabled == False, packet []; an enabled bridge
   taken through a full turn returns 2 packet items,
   byte-identical across repeat calls. Verdict: live
   code path, operator opt-in (ticket E16-T3) - not
   declared live-on.
3. **goals.py - LIVE-DEFAULT (session + tools),
   packet-indirect.** GoalBridge ensures
   entity/goals.yaml at on_session_start (goals_enabled
   defaults true) and register_goal_tools registers
   goal_get / goal_create / goal_update (toolset
   volmarr_identity), model-callable on any turn. The
   bridge defines NO packet_items: user goals do not
   enter the prompt packet directly. They reach it only
   indirectly - as agency-cycle selection inputs and
   through intrinsic_goals arbitration tiers (whose
   packet line deliberately filters origin == intrinsic),
   plus PresentState's user-statement capture ("Current
   goal: ..." session facts). Harness: goal_create ->
   goal_get round-trip succeeds through the real
   handlers. The indirectness is a named design question,
   ticket E16-T2 - not silently "fixed" here.
4. **agency.py - packet LIVE-DEFAULT, orchestrator
   CONTRACT-ONLY (the slice's headline remainder).**
   AgencyBridge.hooks() returns () BY DESIGN ("cycles are
   invoked explicitly, never from a session hook") and
   its packet_items IS in the composition tuple with
   agency_enabled defaulting true: it offers the last
   journal cycle's content-free status line, and
   deliberately suppresses a completed cycle that
   executed nothing. BUT the journal's only writer,
   AgencyOrchestrator.run_cycle, has no production
   caller: a repo-wide grep finds it only in tests
   (test_volmarr_agency_cycle_detail.py) and in a
   surface_reconciliation note; `hermes volmarr agency
   run` runs the Phase 7 proposal-only routine service,
   which by its own header "never calls the agency
   orchestrator" and executes nothing. In production the
   packet line is therefore almost always absent - not
   because the bridge is dead, but because its journal is
   starved. Harness proof of the full path once a cycle
   exists: a real run_cycle (policy mode local, raised
   curiosity drive; 1 proposed / 1 allowed / 1 executed /
   0 failed, verification passed, journal length 1) made
   the bridge emit "Agency: last cycle completed - 1
   executed, 0 failed, verification passed", and the
   NEXT manager pre_llm_call context carried that line
   through PresentState. Reconciliation design + ticket:
   E16-T1.

### The extended family

5. **intrinsic_goals.py - LIVE-DEFAULT, narrow by
   design.** Session-start ensure + packet line for the
   top intrinsic goal only; promotion of new intrinsic
   goals is one explicit service call (module header: no
   hook, no turn-path caller) - that explicitness is the
   design, not a gap.
6. **agency_contracts.py - LIVE-THROUGH-CONSUMER.**
   Pure dataclasses (ActionProposal, ActionResult,
   AgencyCycleReport, Provenance, ReflectionRecord);
   consumed by agency.py and the harness-proven cycle.
   Infrastructure, correctly without its own surface.
7. **agency_routines.py + routines.py - LIVE-OPT-IN
   (operator).** The Phase 7 proposal-only routine:
   agency_routine_enabled defaults false; the cron job
   ("Volmarr Agency Review", 360 minutes) exists only
   after the explicit `hermes volmarr agency install`
   operator action; a run collects at most
   agency_routine_max_proposals proposals, makes zero
   model calls, executes nothing. Its packet source is
   in the tuple under the same default-off flag.
8. **present_state.py + context_packet.py -
   LIVE-DEFAULT, the sole prompt owner.**
   PresentStateBridge registers five hooks; its
   pre_llm_call fills the shared turn_signals holder from
   the hook kwargs, runs all 33 packet sources
   (fail-isolated per source), and returns the single
   {"context": ...} the core injects. Harness: a manager
   pre_llm_call invoke returned exactly 1 result and it
   was the context dict - of the 2 registered pre_llm_call
   callbacks, only PresentState returns context;
   AffectiveBridge's is an observer (stimuli sync +
   turn buffering, returns None). persona_live.py's only
   prompt surface is Channel S, a registered
   system-prompt section that exists solely for owner
   profiles (none at defaults); its Channel T content
   arrives THROUGH PresentState's tuple (first source),
   never around it. One owner, re-proven - not just
   re-asserted from the W05 record.
9. **persona_runtime.py - bridge CONTRACT-ONLY (retired
   at W05), pure surfaces LIVE-THROUGH-PERSONA-LIVE.**
   register() still instantiates PersonaRuntimeBridge,
   but its packet_items was removed from the composition
   tuple at W05 and its hooks() returns (): the wrapper
   has no live caller and E.16 does not pretend
   otherwise. The module's pure surfaces (PersonaCompiler,
   PersonaReloader, route_sections, retrieve_sections,
   budget_items, persona_state) DO have a live caller -
   persona_live imports and runs them per turn for owner
   profiles (W05). Classification is per-surface, not
   per-file.
10. **Adjacent packet family (same tuple).** Default-on
    and live: self_model, drives (motivation),
    metacognition, curiosity, autonomy, local_autonomy -
    each with an on_session_start ensure hook in the 14
    and a data-gated packet line. Default-off packet
    sources (16): agency_cycle_detail, autonomy_detail,
    background_life, background_research, blind_spots,
    curiosity_detail, epistemics, motivation_lifecycle,
    persona_canon, reflection_detail, self_improvement,
    self_state, subjective_report, timescales,
    verdandi_events, layered self_model - plus
    wyrd_context, mempalace_retrieval,
    openviking_retrieval, memory_bridge under their own
    flags. Each is a live code path through PresentState
    that returns [] until its flag is set and its store
    holds data (ticket E16-T4); none is declared live-on.
    Session-start in the harness created ten stores
    unprompted (autonomy policy+state, continuity,
    curiosity, entity, goals, metacognition, motivation,
    self_model, relationships + reflection log) - the
    default-on family's footprint, from disk.

## Gateway reconciliation

The brief's question - do these hooks reconcile with the
gateway, or only with the CLI? - answered from core code,
not from the plugin's own claims:

- **One dispatch, shared by every surface.**
  agent/turn_context.py::_collect_pre_llm_call_context
  runs pre_llm_call through hermes_cli.lifecycle
  invoke_hook (observers, then plugins) with session_id,
  task_id, turn_id, user_message, model, platform,
  parent_session_id and sender_id; returned context is
  injected into the USER message, never the system
  prompt. agent/conversation_loop.py fires
  on_session_start the same way for every persisted
  AIAgent conversation. There is no second, gateway-only
  prompt assembly anywhere in the tree.
- **Gateway turns traverse the identical path.** The
  gateway constructs and caches AIAgent instances
  (gateway/run_agent_cache.py, gateway/run_background.py)
  and drives run_conversation, so a messaging-platform
  turn receives the same session-start ensures, the same
  PresentState packet, and the same tool registrations
  as a CLI turn. The platform/model/parent signals
  persona_live routes on arrive from agent attributes on
  gateway turns exactly as on CLI turns, relayed through
  PresentStateBridge's turn_signals holder.
- **What is NOT consumed, honestly.** volmarr-core
  registers no gateway-native hook: pre_gateway_dispatch,
  post_gateway_admission, on_session_open and
  gateway_platform_event all exist in core (gateway/
  run_inbound_hooks.py, gateway/session_open.py,
  gateway/run_adapters.py) and a grep of the plugin
  finds zero registrations for any of them. The only
  gateway-named code in the plugin is
  persona_ops.probe_gateway - an operator-CLI pidfile
  probe, not a turn path. Consequences: identity/goals
  ensure happens at agent session start rather than at
  gateway session open (later, but on every turn path),
  and nothing volmarr-side observes admission or
  dispatch. Under the plugin-side-only law this is a
  coherent posture, not a turn-path defect; a
  gateway-native observer is a future design option
  (ticket E16-T6), not wiring this slice fabricates.
- **Core suppression note.** hermes_cli.lifecycle
  invoke_hook returns [] while safe_worker_enabled() -
  plugin hooks are suppressed for safe workers by core
  design, for every plugin. Recorded so a future
  silent-packet report checks that switch first.

## Row 20 - ChatIndex audit (same slice)

- Target: pin (E0 first pin) 7df2c9208db6f113f85a6c09295bec7f0f2114e7.
  Re-measurement this slice: `git ls-remote` HEAD ==
  refs/heads/main == the pin; NO other branches and NO
  tags. Tree staged directly under $HOME at
  ~/chatindex-e16, HEAD verified at the pin, clean.
- License: **Apache-2.0 - PASS, verified at text level.**
  LICENSE at the pin: sha256
  c71d239df91726fc519c6eb72d318ec65820627232b2f796219e87dcf35d0ab4,
  201 lines. Its body is whitespace-normalized IDENTICAL
  to the canonical Apache-2.0 text verified in E.14
  (sha256 cfc7749b96f6); the sole byte delta against
  that copy is a missing leading blank line, and the
  appendix is the UNFILLED template ("Copyright [yyyy]
  [name of copyright owner]") - the license's own
  boilerplate form, not a defect. One metadata conflict,
  ticketed not hidden: setup.py's trove classifier
  declares "License :: OSI Approved :: MIT License"
  against the root Apache-2.0 LICENSE (the E14-T1
  pattern; the root LICENSE governs). setup.py also
  carries placeholder author/url fields and claims
  modern installs should use a pyproject.toml that does
  not exist in the tree - scaffold state, recorded as
  found. Before this slice the row rested on the GitHub
  API reading alone ("Apache-2.0 (API)").
- Engine shape: package `ictree` 0.1.0 - ctree/
  (1,595-line tree builder), retrieval/llm_tools.py,
  demo.py; requirements are openai, anthropic,
  python-dotenv: tree construction and retrieval run
  through hosted-LLM calls. The tree carries NO test
  suite (zero test files in git ls-files) - there is
  nothing to execute for a proof 1 (ticket pattern
  E15-T2).
- Fork side: a fresh grep of plugins/, agent/,
  gateway/, hermes_cli/ finds ChatIndex named in
  exactly one Python file - integration_ledger.py's
  FIRST_PINS guard. No adapter code exists, and none
  was built: the P2 line already carries the fork's
  deterministic, local, FTS5 persona retriever
  (persona_index.py, W04), and an LLM-call-dependent
  indexer would be a second, weaker retrieval owner.
  ChatIndex stays a design-only concept reference -
  now with its license proven and its pin re-measured.

## Proofs

- **Proof 1 - engine/family suites at target.**
  ChatIndex carries no suite (above). Row 26 is
  fork-internal; its suites are the fork contracts
  (proofs 2 and 4). No engine source was copied into
  the fork in this slice.
- **Proof 2 - fork contracts BEFORE the ledger edits:
  PASS.** scripts/run_tests.sh on the six row-26 files
  (serialized baseline waiter, log
  ~/team01-e16-baseline.log): **6 files, 50 tests passed
  / 0 failed** - identity 5, goals 6, intrinsic_goals 9,
  context_packet 3, agency 10, integration_ledger 17.
- **Proof 3 - live harness: PASS.** Script
  ~/team01-e16-live.py, full result
  ~/team01-e16-live-result.json, run under the staged
  test-environment venv python against a disposable
  HERMES_HOME with only volmarr-core enabled. It proves,
  through the REAL PluginManager and the REAL register()
  (never mocks of the surfaces under test): plugin
  loads; hook inventory identical by recorder and by
  manager (14 on_session_start, 2 pre_llm_call owned by
  PresentStateBridge + AffectiveBridge); zero system-
  prompt sections at defaults; one on_session_start
  creates the ten default-on stores on disk; identity
  probe healthy; a completed turn ("Call me Volmarr.
  Current task is reconcile the agency hooks." /
  "Implemented the reconciliation audit.") makes the
  next turn's context carry both present-state facts
  inside the <memory-context> fence (604 chars, sha256
  11a98ebea0878dab2290fc57390f7476b77dfb2554961c343a643e47076de372),
  byte-identical on repeat (deterministic), with NO
  agency line (empty journal) and NO affective content
  (default-off) - the honest default surface; goal
  tool handlers round-trip a created goal; a real
  AgencyOrchestrator cycle (1 proposed / 1 executed /
  0 failed, verification passed) writes journal record
  1, the bridge emits its status line, and the next
  pre_llm_call context carries it (sha256
  bb77dc9dde631454120e3e859d18a30d4767811d46fb33efc7c25b00556bdab2);
  affective default bridge disabled with packet [],
  opt-in bridge yields 2 deterministic packet items
  after a full observed turn.
- **Proof 4 - fork contracts AFTER the edits + full
  gate: PENDING at commit, waiter-armed.** This slice
  changes no fork code, so the targeted set is the
  proof-2 six files (which include the ledger battery
  that validates the edited lock) and the full gate is
  the canonical 137-file contract set. Both are queued
  behind the laptop's shared-load waiter
  (~/team01-e16-gate-waiter.sh): targeted to
  ~/team01-e16-targeted.log, then the full set to
  ~/team01-e16-fullcontracts.log with a .done marker.
  Expected verdict line, to be verified by the keeper
  before banking: targeted 50 passed / 0 failed; full
  137 files = 1,171 passed / 7 failed / 1 skipped, the
  7 name-identical to the known live-transport set -
  zero regressions. This record is NOT amended after
  the fact; the keeper's banking closure carries the
  verified counts.

## Pin / record status

- Row 20 pin **unmoved**: pinned == current_head ==
  7df2c9208db6f113f85a6c09295bec7f0f2114e7 in
  integration-lock.json (license now text-verified,
  verdict "current - E.16 executed 2026-11-14"),
  INTEGRATION_MATRIX.md row 20, and the new
  COMPONENT_LICENSES.md identification row. The
  pin-guard needed no new test: FIRST_PINS in
  integration_ledger.py already enforces this pin and
  the ledger battery already names ChatIndex - both
  green in proof 2 and re-run in proof 4.
- Row 26 has no pin (fork-internal). Its lock row now
  reads update_needed false and verdict "current -
  E.16 executed 2026-11-14" with the E.16 method and
  remainders recorded; matrix row 26 updated to match.
- Verification tally does not move: **25 verified / 0
  partially verified / 1 blocked (Sagnaskemma)** - both
  rows were already verified; E.16 deepens evidence
  (one license text, one full live inventory) without
  changing statuses.
- No adapter or code change: no fork code was modified
  in this slice, so no CUSTOMIZATIONS.md row (E.03 /
  E.05-E.15 precedent: ledger state only).
- README.md untouched (sha256
  336813d11bbe5aa2ff745b4a4bc3abcf2a283cd13971c0c11d061377129db7f3
  before and after).

## Honest remainders (named, not hidden)

- **E16-T1** (agency orchestrator has no production
  caller): AgencyOrchestrator.run_cycle is exercised
  only by tests. The packet bridge is live and proven,
  but its journal is starved in production. Recorded
  reconciliation design (NOT built here - no existing
  seam, and a new invocation path is a behavior change
  beyond an audit slice): add an explicit operator
  verb `hermes volmarr agency cycle` beside the
  existing agency {status|install|run|evaluation}
  family, running ONE bounded cycle through the
  orchestrator with its existing policy gates and
  executors, and optionally a cron routine mirroring
  the Phase 7 install pattern (explicit install,
  paused unless --activate). The journal then feeds
  the already-live packet bridge unchanged. Until
  then, row 26's agency half stands at: packet live,
  cycle contract-only.
- **E16-T2** (user goals reach the packet only
  indirectly): GoalBridge has no packet_items. Design
  options for a future slice: (a) a GoalBridge packet
  line for active user goals in current_state, (b)
  leave goals to agency/intrinsic arbitration plus
  PresentState capture, as today. The trade-off is
  prompt budget against goal visibility and needs
  Volmarr's word; nothing was wired in E.16.
- **E16-T3** (affective + persona-live are opt-in):
  affective_enabled and persona_live_owner default
  false by standing design; E.16 confirms the defaults
  in plugin.yaml and the honest empty behavior under
  them. Revisit only on Volmarr's word.
- **E16-T4** (16+ detail packet sources default-off):
  each is a live path through PresentState gated by
  its own *_enabled flag and store contents; enabling
  any of them is a per-profile operator choice. Their
  contract suites are the evidence until then.
- **E16-T5** (ChatIndex license metadata conflict):
  the engine repo's setup.py trove classifier declares
  MIT against its root Apache-2.0 LICENSE. The root
  LICENSE text governs; the fork imports no ChatIndex
  material, so no reliance arises. Any future import
  must re-check the exact files taken.
- **E16-T6** (gateway-native hooks unconsumed):
  pre_gateway_dispatch, post_gateway_admission,
  on_session_open, gateway_platform_event have no
  volmarr consumer. A future observer (e.g. identity
  ensure at on_session_open) is design-only until a
  need is shown; pre_gateway_dispatch is a policy
  surface and any use needs Volmarr's word.
- **E12-T2** (matrix tally drift) continues: the
  INTEGRATION_MATRIX "Verification tally" paragraph
  still carries its W08 promotion counts. The lock and
  the ledger test are the enforced truth (25 / 0 / 1);
  the tally paragraph wants a dedicated correction
  pass, out of this slice's rows-only scope.
- The section 32 release scorecard still reads NOT
  releasable; E.16 changes reconciliation evidence
  only, nothing else.
- Next in roadmap order: E.17.
