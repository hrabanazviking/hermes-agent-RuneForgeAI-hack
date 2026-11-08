# W05 Implementation Record — Phase P3/P4: Live Persona Wiring (Kernel + Per-Turn Pipeline)

Team 06 (W05), 2026-11-08. Tickets P.008–P.011 and P.017 per
`docs/modernization/P3P4_DESIGN_DRAFT.md` (committed this branch),
built on the banked W04 retrieval tree (`plugins/volmarr-core/persona_index.py`;
contract baseline 976 passed). Roadmap section 28.2 law held: a
persona surface is declared live only where this wave gave it a
real caller on a real turn path — the surfaces this wave did NOT
wire are named as still contract-only below, never declared
complete. All personal code is plugin-side in
`plugins/volmarr-core/`; no Hermes core file is touched.

## What was built

New module `plugins/volmarr-core/persona_live.py`
(`PersonaLiveBridge`, 849 lines), registered in
`plugins/volmarr-core/__init__.py`, configured through five new
`plugin.yaml` keys (`persona_live_owner`,
`persona_live_kernel_tier`, `persona_live_context_class`,
`persona_live_legacy_soul_disabled`,
`persona_live_receipt_path`). Everything is opt-in per profile:
`persona_live_owner` defaults off, and a non-owner profile is
byte-for-byte stock Hermes, legacy SOUL path included.

- **Channel S — frozen kernel section (P.008/P.009).** Exactly
  one system-prompt section, id `volmarr.persona.kernel`, at the
  only legal position `after_memory`, rendered by
  `render_kernel_section` from the compiled kernel of the ACTIVE
  generation. The body carries the compiled kernel verbatim at
  the largest section 64 tier that fits the core caps: the core
  wraps a rendered section in a `## Plugin Context: <id>`
  heading, so the section cap is 4,000 chars and the body budget
  is 3,900. Tier-down is whole-section only
  (`kernel_text_for_tier`): the anchor block stands first,
  verbatim, and is never evicted; sections are taken whole, in
  kernel order — the compiler emits P0 first, so P0 sections are
  the last a tier ever drops — and any section that does not fit
  is excluded whole and reported through the excluded list,
  never silently dropped and never head/tail-truncated.
  Frozen-per-session semantics are the core's own; a new
  generation refreshes this channel at the core's rebuild
  boundaries, never mid-turn.
- **Channel T — per-turn pipeline (P.008/P.009, P.017
  substrate).** `PresentStateBridge` stays the sole
  `pre_llm_call` persona assembler. `PersonaLiveBridge.packet_items`
  replaces the retired descriptive `PersonaRuntimeBridge.packet_items`
  as the persona source in the PresentState composition tuple
  (`plugins/volmarr-core/__init__.py`: `persona_live.packet_items`
  first in the tuple, `persona_runtime.packet_items` removed),
  and instead of a prose description of the contract system it
  emits REAL content: a bounded kernel echo (tier per section 15
  context class: `small_local` → `kernel_micro`, `standard` →
  `kernel_medium`, `large` → `kernel_full`), routed + retrieved
  persona sections verbatim (stable-id named, source-hash
  provenanced), and a section 37 persona-state line. This gives
  the banked pure surfaces their first live callers: the
  section 20 reloader snapshot (`PersonaReloader`, via
  `PersonaLiveState`), the section 14 router (`route_sections` /
  `route_mode`), the section 13 retriever (`retrieve_sections`),
  and the section 15 budgeter (`budget_items`). All of it runs
  over ONE immutable per-turn generation snapshot (draft
  section 5): `PersonaGeneration` stores the compiled artefact
  privately and hands it out only as a deep copy; reload checks
  run at turn start BEFORE the turn captures its generation
  reference, and a validated new compile is published by a
  single reference swap under a lock — hash-checked next-turn
  activation, effective from the NEXT admitted turn, never
  mid-turn. A failed validation keeps the last known-good
  generation and records the error. A shared `turn_signals`
  holder lets the persona source route on the model / platform /
  parent signals core passes to `pre_llm_call`:
  `PresentStateBridge` now fills it from the hook kwargs before
  sources run (sole assembler unchanged).
- **P.010 — duplicate legacy SOUL removal, opt-in refusal.**
  Per design draft option 2: while persona-live owns the
  prompt, a still-loaded legacy SOUL.md identity block would
  double-inject the persona, so ownership REFUSES (fail loud,
  stock fallback) unless the operator attests a supported core
  suppression was applied via
  `persona_live_legacy_soul_disabled` — set true only when the
  profile's legacy SOUL.md block is genuinely suppressed by a
  supported route (for example the gateway or CLI ignore-rules
  path that sets `load_soul_identity` off). When the attestation
  is false and a SOUL.md still exists in the profile home,
  persona-live refuses ownership and the profile stays stock.
- **Delegates — fragments only (P4 / section 36).** Delegated
  child sessions receive persona fragments only
  (`persona_live/fragment` source), never the kernel section
  and never the full persona: the section 36 separation
  contract gets its first live caller here, in-process (see
  the honest limit under ticketed remainders).
- **P.011 / P.017 — receipts, operator-side only.** Every turn
  the bridge records a receipt (schema
  `runeforge.persona-live-receipt`, version 1) to the bounded
  receipt store (default `memory/persona_live_receipts.json`
  under the active profile, 256 receipts max, written
  atomically with mode 0600; a configured path escaping the
  profile home falls back to the default). Receipts carry
  hashes, ids, budgets and decisions only — never persona
  text — and are operator-side evidence for W07/P6 surfacing;
  they never enter tool results or messages. Kernel hash
  stability is part of the record: a generation's
  `kernel_hash` is fixed at publish and receipts name the
  generation and hash each turn actually ran under.

## Gate

`tests/plugins/test_volmarr_persona_live_gate.py` (3 tests) —
no mocks of the surfaces under test:

- Real plugin-manager discovery: `PluginManager().discover_and_load()`
  loads the real `volmarr-core` plugin, and for an opt-in
  profile the kernel lands on BOTH channels (the registered
  `volmarr.persona.kernel` system-prompt section renders, and
  the per-turn packet carries persona-live items).
- Real AIAgent system-prompt build:
  `test_gate_opt_in_kernel_lands_in_real_system_prompt` builds
  a real `AIAgent` and calls the real
  `agent.system_prompt.build_system_prompt`, asserting the
  frozen kernel section is present in the built prompt.
- Stock proof: `test_gate_non_opt_in_profile_is_stock` asserts
  a non-opt-in profile discovers no persona-live system-prompt
  sections at all (`manager._system_prompt_sections == {}`).

PASSED as part of the 15 new tests below (log
`~/team06-w05-newtests3.log`).

## Verified results (2026-11-08, purplelongship, logs on the laptop)

- W05 tests: `tests/plugins/test_volmarr_persona_live.py` (12
  tests) + gate file (3 tests) = **15 passed / 0 failed**
  (log `~/team06-w05-newtests3.log`; earlier runs
  `~/team06-w05-newtests.log` 11 failed and
  `~/team06-w05-newtests2.log` 1 failed are the found-and-fixed
  evidence below).
- Neighbour suites: **34 passed / 0 failed**
  (log `~/team06-w05-neighbors.log`); present_state suite:
  **4 passed / 0 failed** (log `~/team06-w05-ps.log`).
- Contract baseline (`~/team06-w05-contracts.log`): **123
  files = 991 passed / 7 failed / 1 skipped**; 991 = 976 W04
  baseline + 15 new W05 tests. The 7 failures are
  name-identical to the grading baseline live-transport set
  (5 core-plugin Verdandi socket/discovery in
  `test_volmarr_core_plugin.py`, 1 Verdandi stimuli in
  `test_volmarr_verdandi_stimuli.py`, 1 voice-runner loopback
  in `test_volmarr_voice_runner.py`) — zero regressions, zero
  new failures.
- README.md sha256 unchanged:
  `336813d11bbe5aa2ff745b4a4bc3abcf2a283cd13971c0c11d061377129db7f3`.

## Found and fixed in scope

1. **Render unpack bug.** The first W05 test run
   (`~/team06-w05-newtests.log`: 4 passed / 11 failed) included
   `ValueError: too many values to unpack (expected 3, got 4)`
   raised on the Channel S render path in `persona_live.py`:
   the kernel-section render unpacked a helper result with the
   wrong arity, so an opt-in profile got no kernel section at
   all (the gate asserted an empty section list). Fixed in
   scope: the render consumes the helper's full return shape;
   the same run's downstream `KeyError: 'persona_live/kernel'`
   and missing-generation failures cleared with it.
2. **Tier-down P0-order bug (Channel S).** The second run
   (`~/team06-w05-newtests2.log`: 14 passed / 1 failed) caught
   the tier-down violating its own bound and order: the
   rendered kernel text was 23,209 chars against the asserted
   `0 < len(text) <= 3900` budget — whole sections were being
   carried past the tier target instead of excluded whole, so
   the frozen section would have blown the core's per-section
   cap and the sections a tier drops were not the last-priority
   ones. Fixed in `kernel_text_for_tier`: sections are taken
   whole, in kernel order (P0 first, so P0 is dropped last),
   under the tier target as a hard bound; overflow sections are
   excluded whole and reported, the anchor block is never
   evicted, and nothing is truncated. Third run green: 15/15
   (`~/team06-w05-newtests3.log`).

## Deliberate deviations / ticketed remainders

- **Draft section 2 rows 13–15, 20, 22, 24–28 stay
  contract-only.** Change impact + versioning (row 13), drift
  defences / precedence / summary guard / trait-vs-state
  (row 14), watchdog / drift score / repair (row 15),
  persona-aware memory write + memory guard (row 20), startup
  sequence + request pipeline (row 22), history compression +
  long-term placement (row 24), drift tests / golden /
  fingerprints / telemetry / model-quality router (row 25),
  kernel tiers as a live model-class selection surface beyond
  the Channel T echo mapping (row 26), the persona CLI family
  (row 27 — real CLI wiring is W07/P6; W05 does not fake it),
  and bootstrap + phase reconciliations + architecture audits
  (row 28) received NO live caller in this wave and are NOT
  declared complete (roadmap section 28.2). W05 wired rows 4,
  6–9, 11, 12 (reloader only), 18 and 19's state line, plus the
  P.010 dedup against row 1, per the draft section 2 closing
  paragraph.
- **The descriptive `persona_runtime` packet item is
  retired** (draft section 3.3, one prompt owner): the
  PresentState composition tuple no longer includes
  `PersonaRuntimeBridge.packet_items`, so a profile with only
  `persona_runtime_enabled` set gets NO persona packet item
  now — metadata-only mode is gone by design, and the single
  opt-in is `persona_live_owner`. This is draft section 12
  open question Q4, proceeded on as below.
- **Draft section 12 open questions Q1–Q5 remain Volmarr's.**
  Q1 (two-channel reading of section 9 vs an authorised core
  patch), Q2 (P.010 route), Q3 (kernel tier defaults per model
  class + cap overflow policy), Q4 (`persona_runtime_enabled`
  retirement) and Q5 (delegate fragments: in-process-only
  coverage) are not decided by this wave. The two-channel plan
  proceeded under the roadmap section 0.2 ground rules
  (native-first, personal code in plugins not core, additive
  divergence) with the least-core reading: option 2 for P.010,
  automatic whole-section tier-down for Q3's overflow policy,
  retirement for Q4, in-process-only fragments for Q5. Any of
  these can be reversed by Volmarr's word without core changes.
- **The 7 live-transport failures remain environment-bound.**
  There is no live Verdandi service on the laptop; the
  failures are name-identical to the freeze/W04 baseline and
  are not W05 regressions. Real-socket diagnosis beyond
  name-identity stays open and is not claimed here.
- Delegate fragments are in-process only in this wave
  (draft section 7 honest limit); cross-process delegate
  coverage remains deferred to W09/N1 per draft Q5.
