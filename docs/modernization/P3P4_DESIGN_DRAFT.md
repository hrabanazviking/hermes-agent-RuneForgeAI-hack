# P3/P4 Design Draft — W05 Live Persona (Team 06, PREP ONLY)

Status: DESIGN / AUDIT PREP ONLY. No implementation. Uncommitted draft,
matching the established prep pattern (cf. Team 04 P0P1_DESIGN_DRAFT.md,
Team 05 P2_DESIGN_DRAFT.md). Written 2026-11-07 by Team 06 lead against
tree `7ce3db56f08777e90c12eeb7a209c4508e1b7b11` (origin/main: W01/W02/W03
banked). Branch `yrsa/hermes-team-06` was fast-forwarded
`b5c6743a22..7ce3db56f0` (clean, no conflicts) before this audit.
README.md untouched: sha256
`336813d11bbe5aa2ff745b4a4bc3abcf2a283cd13971c0c11d061377129db7f3`
verified before and after the merge.

Scope: roadmap tickets **P.008, P.009, P.010, P.011, P.017** —
Phase P3 (§9: irreducible persona kernel + prompt assembler) and
Phase P4 (§10: live runtime integration across every surface).
Governing rule (§28.2 + WAVE_PLAN Team 06 entry): persona sections
banked as pure contracts with NO live caller get real callers here,
or an honest record of why not. Never re-declare complete without
live callers.

---

## 1. What the current tree actually does (verified, file evidence)

### 1.1 The one live prompt owner today

`plugins/volmarr-core/present_state.py` — `PresentStateBridge`:

- `hooks()` returns `on_session_start`, `pre_llm_call`, `post_llm_call`,
  `on_session_end`, `post_tool_call`; registered in
  `plugins/volmarr-core/__init__.py` (`register()`).
- Its `pre_llm_call` aggregates 31 `packet_items` sources (the
  `packet_sources` tuple in `__init__.py`, lines 116–147), builds one
  bounded packet via `context_packet.ContextPacketBuilder`
  (schema `runeforge.memory-packet` v2, default 6,000 chars, hard cap
  16,000), and returns `{"context": context}`.
- Core consumes that in `agent/turn_context.py`:
  `_collect_pre_llm_call_context()` → `invoke_hook("pre_llm_call", …)`
  → the returned context is injected **into the user message**
  (`plugin_user_context`, "never the system prompt" — turn_context.py
  docstring, line ~853). Oversized hook output is spilled to disk.

So the ONLY Volmarr prompt channel with a real gateway caller is a
per-turn, user-message-side, 6k-char bounded memory packet. It is the
de facto prompt owner W05 must formalise — not compete with.

### 1.2 What the persona packet item actually injects

`PersonaRuntimeBridge` (`persona_runtime.py`, 15,408 lines, §§3–94):

- `hooks()` returns `()` — it registers NO hook of its own.
- It reaches the turn path only indirectly: `__init__.py` line 144 puts
  `persona_runtime.packet_items` in the PresentState source tuple.
- `packet_items` is gated by config `persona_runtime_enabled`
  (default **False**). When enabled it compiles the persona and returns
  ONE `ContextItem(section="current_state", priority=0.4)` whose content
  is a long **prose description of the contract system itself** —
  persona id, version, document/section counts, kernel hash (12 chars),
  IR category counts, and a paragraph-per-section summary of §§3–94
  ending "Canonical document text is compiled, not injected by this
  layer."
- **The kernel text itself is never injected. No retrieved section text
  is ever injected.** Even with the flag on, the model learns that a
  persona system exists — not who the persona is. This is the central
  §28.2 debt W05 exists to close.

### 1.3 The legacy SOUL path (the duplicate P.010 must remove)

- `agent/system_prompt.py::_identity_parts()` → 
  `agent/prompt_builder.py::load_soul_md()` reads `$HERMES_HOME/SOUL.md`
  and passes it through `_truncate_content()` — the head/tail truncation
  path (kept head+tail, middle omitted with a marker). It lands in the
  **stable tier, identity slot #1** of `build_system_prompt_parts()`.
- `build_context_files_prompt(..., skip_soul=soul_loaded)` already
  dedupes SOUL against the context-files path — the only existing
  duplicate guard.
- Callers: every surface that builds a system prompt (CLI/TUI, gateway
  via `gateway/session_execution.py` `load_soul_identity=…`, cron —
  "cron keeps the persona while skipping cwd instructions").
- Consequence: today a profile gets (a) truncated raw SOUL in the
  system prompt, AND (b) if `persona_runtime_enabled`, the contract
  description in the user message. W05 must make (b) carry the real
  kernel and turn (a) OFF — **opt-in profiles only** (P.010).

### 1.4 The official gateway extension surfaces (what we may use)

Two official plugin surfaces exist in the banked v0.23 tree. Neither is
a system-prompt position-1 slot. The design must be honest about this:

1. **`pre_llm_call` hook** (above): per-turn, dynamic, user-message
   injection. Official, supported, already ours via PresentState.
2. **`register_system_prompt_section`** (`hermes_cli/plugins.py`,
   `PluginContext.register_system_prompt_section`):
   - `SYSTEM_PROMPT_SECTION_POSITIONS = frozenset({"after_memory"})`
     (`hermes_cli/plugins_dispatch.py:98`) — the ONLY allowed position
     is `after_memory`, in the **volatile tier** of
     `agent/system_prompt.py::build_system_prompt_parts()`.
   - Sections are **rendered once per session and frozen**
     (`_frozen_plugin_prompt_sections`), persisted verbatim in the
     prompt, restored on resume; a failed re-render keeps previous
     bytes. Bounded: per-section `max_chars` ≤
     `MAX_SYSTEM_PROMPT_SECTION_CHARS`, plus a total cap.
   - Volmarr-core currently registers **zero** system-prompt sections
     (grep: no `register_system_prompt_section` call anywhere in
     `plugins/`).

There is NO official surface that inserts plugin text into the stable
tier ahead of identity, and NO surface that rewrites the system prompt
per turn. §9's canonical order ("runtime rules → kernel → state/memory
→ context → user turn") therefore cannot be realised literally inside
the system prompt from a plugin. See §3 for the two-channel plan that
gets as close as the official surfaces honestly allow, and §9/Q1 for
the open question this raises.

### 1.5 W03's canonical library has no live caller yet either

`plugins/volmarr-core/canonical_library.py` (banked W03, P.001–P.005):
no `packet_items`, no hooks, no production importer — only
`tests/plugins/test_volmarr_canonical_library*.py` import it, and it
imports section-id helpers FROM `persona_runtime`. W04 (P2 retrieval)
is its first planned consumer; W05 must consume W04's retrieval, not
build a second stack on the raw library (roadmap §33.4: no shadow
compiler, no second memory owner).

---

## 2. Live-caller inventory (the §28.2 audit)

Method: for each persona contract surface — grep for callers outside
its own module and outside `tests/`; check `__init__.py` registration;
check hook registration; check whether the caller is on a real turn
path (gateway/agent loop) or explicit-only. "Live" below means: a
real gateway turn can cause this code to affect a prompt or a
user-visible behaviour, with default config unless stated.

| # | Contract surface (file) | Live caller? | Evidence |
|---|---|---|---|
| 1 | Legacy SOUL injection (`agent/system_prompt.py` + `prompt_builder.load_soul_md`) | **LIVE** | `_identity_parts` in every `build_system_prompt_parts`; stable tier slot 1; head/tail truncated |
| 2 | `PresentStateBridge.pre_llm_call` + `ContextPacketBuilder` (`present_state.py`, `context_packet.py`) | **LIVE** | Hook registered in `__init__.py`; core `turn_context._collect_pre_llm_call_context` invokes it every turn |
| 3 | `IdentityBridge.on_session_start` (`identity.py`) | **LIVE** (session init only) | Hook registered; `ensure()` initialises identity store; owns no persona text |
| 4 | `PersonaRuntimeBridge.packet_items` (`persona_runtime.py`) | **PARTIAL — metadata only, default OFF** | Source #31 in PresentState tuple (`__init__.py:144`); gated `persona_runtime_enabled=False`; injects contract description + hashes, NEVER kernel/section text |
| 5 | `PersonaCanonBridge.packet_items` (`persona_canon.py`) | **PARTIAL — count only, default OFF** | Source in PresentState tuple; gated `persona_canon_enabled=False`; injects only a contradiction COUNT, never canon prose; `hooks()` = `()` |
| 6 | `PersonaCompiler` + kernel generation (§§3–10) | **NONE on turn path** | Only caller is `PersonaRuntimeBridge.packet_items` (metadata use) + tests; `PersonaCompiler` has no importer outside `persona_runtime.py` |
| 7 | Hybrid retrieval (§13, `PersonaRetriever`, `retrieve_sections`) | **NONE** | Explicit call only (module docstring); no importer outside module/tests |
| 8 | Router (§14, `PersonaRouter`, `route_sections`) | **NONE** | Explicit only; no live task signal ever reaches it |
| 9 | Context budgeter (§15, `PersonaContextBudgeter`, `budget_items`) | **NONE** | Explicit only; the live packet budget is ContextPacketBuilder's unrelated 6k cap |
| 10 | Priority system (§16) | **NONE live** | Consumed only inside compile/retrieval/budget pure functions |
| 11 | Anchors / anti-anchors (§§17–18) | **NONE live** | Carried verbatim into the compiled kernel — which is never injected (row 4) |
| 12 | Hash record + hot reload (§§19–20, `PersonaReloader`) | **NONE** | Explicit check only; no watcher, no hook, no CLI caller |
| 13 | Change impact + versioning (§§21–22) | **NONE** | Pure functions; tests only |
| 14 | Drift defences / precedence / summary guard / trait-vs-state (§§23–26) | **NONE** | Contract rules; no conversation is read or monitored |
| 15 | Watchdog, drift score, repair (§§27–31, `PersonaWatchdog` et al.) | **NONE** | No draft ever reaches it; PresentState `post_llm_call` only captures the turn for state, never scores it |
| 16 | Refresh, periodic + event (§§32–33) | **NONE** | Pure due/plans; no session message counting, no compression/model-switch hook wired |
| 17 | Model-switch identity + handoff packet (§§34–35) | **NONE** | Pure; no model router or handoff consumer calls it |
| 18 | Subagent separation (§36) | **NONE** | Pure; core delegation (`agent/delegation_provider.py`) has no persona-fragment concept — a profile route gives a child the profile's whole SOUL.md |
| 19 | Persona state / modes / mode routing (§§37–39) | **NONE** | Pure builders; no live mode is ever selected or applied |
| 20 | Persona-aware memory write + memory guard (§§40–41) | **NONE** | PresentState `post_tool_call` captures memory writes WITHOUT persona classification |
| 21 | Service Bible / Relationship / Tool / Memory / Avatar retrievers (§§42–46) | **NONE** | Five explicit-only retriever classes; zero importers outside module/tests |
| 22 | Startup sequence + request pipeline (§§51–52) | **NONE** | Pure plans; no boot hook; pipeline stages name owners but nothing executes the pipeline |
| 23 | Prompt assembly order + order evaluation (§§53–54) | **NONE** | Docstring admits it: "assembles no prompt and is not wired into the turn path" |
| 24 | History compression + long-term placement (§§55–56) | **NONE** | Pure arithmetic/placement contracts; core compression is unrelated |
| 25 | Drift tests / golden / style + behaviour fingerprints / telemetry / model-quality router (§§57–63) | **NONE** | Evaluation artefacts; no live evaluation runs, no telemetry is recorded from live turns |
| 26 | Kernel tiers + micro-kernel (§§64–65) | **NONE** | Pure tier tables; no model-class selection on any live path |
| 27 | Persona CLI family (§§71–76: inspect/explain/reload/diff/export/import) | **NONE** | Pure record builders; `plugins/volmarr-core/cli.py` registers NO persona subcommand (health only) — real CLI wiring is W07/P6, but W05 must not fake it |
| 28 | Bootstrap + phase reconciliations + architecture audits (§§80–94) | **NONE** | Pure audit functions over supplied artefacts |
| 29 | Canonical library (W03, `canonical_library.py`) | **NONE** | Tests only; W04 is first planned consumer (see §1.5) |
| 30 | Affective bridge `pre_llm_call` (`affective_bridge.py`) | **LIVE** (adjacent) | Second registered `pre_llm_call` hook; PAD state — listed because prompt-owner consolidation must account for BOTH hook registrants |

**Counts: 30 inventoried persona/prompt surfaces — 4 LIVE
(rows 1, 2, 3, 30; row 3 is session-init only), 2 PARTIAL
metadata/count-only and default-off (rows 4, 5), 24 with NO live
caller (rows 6–29 excluding the partials).** Of the persona-runtime
contract family proper (§§3–94), exactly **zero** surfaces inject
persona content into a live prompt today.

That is the honest baseline. W05's job is rows 4, 6–9, 11, 12, 16–19,
21, 23 — the kernel pipeline — plus the P.010 dedup against row 1.
Rows 13–15, 20, 22, 24–28 stay contract-only after W05 unless a step
below explicitly wires them; the wave record must say so per row,
not declare them complete (§28.2).

---

## 3. Design: kernel + prompt assembler on the official surfaces

### 3.1 Two channels, one owner

W05 uses BOTH official surfaces, each for what it actually is:

- **Channel S (stable, per-session): `register_system_prompt_section`.**
  Register exactly one section, id `volmarr.persona.kernel`, position
  `after_memory` (the only legal position), rendered from the compiled
  kernel of the ACTIVE generation (see §5). Content: anchors block
  verbatim (§§17–18) + kernel sections verbatim (§7 — never summarised),
  bounded by the section caps; if the kernel exceeds the cap, use the
  §64 tier selected for the profile's model class (micro/standard/large)
  and record the tier + truncation honestly in the receipt — never
  silently head/tail-truncate (that is the legacy disease).
  Frozen-per-session semantics are ACCEPTED for this channel: it is the
  session's pinned kernel fingerprint. Activation of a new generation
  mid-session does NOT rewrite it (see §5 — atomic NEXT-turn activation
  applies to Channel T; Channel S refreshes at the core's own rebuild
  boundaries: new session, resume, compression invalidation).
- **Channel T (per-turn, dynamic): the existing `pre_llm_call` packet.**
  PresentState remains the single assembler. The persona contribution
  changes from today's contract-description item to REAL content,
  produced by the pipeline in §3.2: routed + retrieved persona sections
  (verbatim, stable-id named), current persona state (§37 shape), and
  the packet receipt (§6). Still bounded by ContextPacketBuilder —
  W05 raises no cap silently; P.011 budgets (§7 below) allocate the
  6k across kernel-echo / retrieval / memory / project explicitly.

If Channel S registration fails or the plugin is disabled, behaviour
falls back to stock Hermes exactly (roadmap §9: "explicit fallback to
unchanged Hermes behavior when the plugin is disabled") — including
legacy SOUL (see §4: dedup applies only while W05 owns the prompt).

### 3.2 The per-turn pipeline (P.008 + P.009)

One new module, plugin-side only (ground rule: personal code in
plugins, not core): `plugins/volmarr-core/persona_live.py`, owned by
Team 06. It does NOT re-implement compile/retrieval/routing/budget —
it CALLS the banked pure surfaces, finally giving them live callers:

```
turn start (inside PresentStateBridge.pre_llm_call, persona source)
  1. resolve active generation snapshot (§5)         [PersonaReloader.check at most once per turn, hash-cheap]
  2. PersonaRouter.route_sections(snapshot.index,     [§14 — first live caller]
        user_message, task signals from hook kwargs: model, platform, parent_session_id, sender_id)
  3. PersonaRetriever / role retrievers (§§42–44)     [§13 — first live caller]
        fill/adjust the routed set from the user message
  4. PersonaContextBudgeter.budget_items(             [§15 — first live caller]
        kernel_echo + retrieved + state, model context class from agent model kwarg)
  5. emit ContextItems (section=current_state / self_state per
     ContextPacketBuilder SECTION_ORDER) + receipt (§6)
```

P.008 (protected source provenance) is satisfied structurally: every
emitted item names its §12 stable id + document role + source hash
from the W03 manifest / §19 hash record; the kernel compile consumes
the W03 canonical library's manifest where roles overlap — ONE source
identity scheme (`canonical_library.py` already reuses
`persona_runtime` section ids; W05 keeps that direction, never forks
it). Kernel profile selection (micro/standard/large, §64) is a
per-profile config, defaulting by model context class, operator
overridable; the core identity checksum (kernel sha256) must be
identical across model switches (§34 contract becomes testable).

### 3.3 ONE prompt owner (P.009)

- `PresentStateBridge` stays the sole `pre_llm_call` persona assembler;
  `AffectiveBridge.pre_llm_call` stays a separate, pre-existing hook
  (PAD only) and is explicitly OUT of persona ownership — the design
  records it so "one owner" is a checked fact, not a slogan: exactly
  two `pre_llm_call` registrants exist in the plugin, one owns persona.
- `PersonaRuntimeBridge.packet_items` is REPLACED as a packet source:
  `persona_live` becomes the persona source in the `__init__.py`
  tuple; the old descriptive item is retired (its compile/metadata
  content moves into the receipt, §6, where it belongs). No turn may
  ever receive both the old description item and live persona content.
- Channel S has exactly one registrant: `persona_live.register(ctx)`
  called once from `volmarr-core/__init__.py::register()`.

---

## 4. Duplicate legacy SOUL removal — opt-in profiles only (P.010)

- New per-profile opt-in flag (profile `config.yaml`, RuneForge
  namespace): `persona_live_owner: true`. Default absent/false =
  stock behaviour, byte-for-byte.
- Problem: `load_soul_md` is CORE code; the ground rules forbid
  forking core behaviour from a plugin, and no official surface
  suppresses identity slot #1. Honest options, in preference order:
  1. **Config-native:** check whether the banked tree already exposes
     a supported switch (`load_soul_identity` / `skip_context_files`
     plumbing exists in `gateway/session_execution.py` and
     `agent/system_prompt.py::_identity_parts` via
     `agent.load_soul_identity or not agent.skip_context_files`).
     Step 0 of implementation is a spike to find the narrowest
     SUPPORTED way a profile config reaches that flag; if a profile
     config key already maps to it, P.010 is config + tests only.
  2. If no supported route exists, P.010 ships as: W05 owns Channel
     S+T, and the opt-in profile ALSO sets the existing core option
     by hand (documented operator step), with a startup validation
     that REFUSES persona-live ownership when legacy SOUL is still
     loaded for that profile (fail loud, never double-inject).
  3. A core patch is OUT of W05 scope without Volmarr's explicit
     word — it would be a CUSTOMIZATIONS.md divergence beyond the
     additive-plugin rule. Recorded as open question Q2.
- Acceptance evidence: prompt trace on an opt-in profile shows the
  SOUL text exactly once (as kernel, Channel S/T) and the truncated
  legacy block absent; on a non-opt-in profile the prompt is
  byte-identical to the pre-W05 baseline.

---

## 5. Per-turn immutable snapshot + atomic next-turn activation (P4)

- `PersonaLiveState` (in `persona_live.py`): holds the ACTIVE
  generation = {compiled artefact, kernel hash, persona hash,
  generation number, activated_at_turn}. Immutable once published
  (frozen dataclass / mapping copy; the compiled artefact is already
  treated as immutable by §§6/19).
- Turn flow: `pre_llm_call` captures the current generation reference
  ONCE at turn start and uses it for every stage of that turn.
  Reload checks (`PersonaReloader.check`, §20 — first live caller)
  run at turn start BEFORE capture; a validated new compile is
  published by a single reference swap (lock-protected), so it takes
  effect from the NEXT admitted turn — never mid-turn, never
  mid-stream. A failed validation keeps last known-good (§10/P4:
  "refuse partial generations; retain last known-good hash").
- File-change detection is the §20 explicit hash check at turn start
  (cheap: config + per-document hashes), NOT a watcher thread — the
  plugin owns no watcher (§20's own honesty rule).
- Restart: generation rebuilt at plugin registration / first turn
  from sources; hash equality with the pre-restart generation is the
  restoration proof (P4 acceptance: correct restart restoration).
- Rewind/fork: the receipt (§6) is stored per turn with the session's
  turn record by PresentState's existing capture path, so a forked
  branch carries the generation that actually served each turn;
  obsolete branch receipts are never committed to the parent branch
  (P4 requirement; implementation detail = receipt keyed by
  (session_id, turn_id), which PresentState already uses).

## 6. Packet receipts (P.011)

Per turn, for the operator only (never to untrusted tools or remote
participants — roadmap §9): {generation, kernel sha256, persona hash,
model context class, per-category budget allocation + used (§15
categories), stable ids included / excluded-with-reason, channel S
tier, legacy_soul_present: bool}. Stored beside PresentState's turn
capture; surfaced later by W07/P6 `persona explain` — W05 builds the
receipt, W07 builds the command. Budget rule: on context pressure,
expire retrieved context first (lowest §16 priority, §15 order);
the kernel is never evicted (P0 rule, §§15–16 — first live test of
that rule).

## 7. Delegates inherit fragments only (P4 / §36)

- Core delegation today: a child either inherits the parent session
  wholesale or takes a `profile` route (whole profile incl. its
  SOUL.md) — `agent/delegation_provider.py`. There is no fragment
  channel in core, and W05 adds none to core.
- Plugin-side design: `persona_live.delegate_fragment(persona_id,
  stable_ids, authority_ceiling)` builds a bounded fragment packet
  (named sections verbatim + mode + task authority), delivered to a
  child ONLY through the child's own `pre_llm_call` turn when the
  child session carries a delegate marker (parent_session_id +
  fragment id in hook kwargs — both already passed by core's
  `_collect_pre_llm_call_context`). The child NEVER receives: kernel
  anchors wholesale, private memory sections, or credentials; its
  own identity (profile/persona) stays primary (§36 contract — first
  live caller). Default (no marker) = no fragment, stock delegation.
- Honest limit: a delegate launched as a separate PROCESS/profile
  with no shared plugin state receives nothing — recorded, not
  papered over; cross-process fragment transport is W09/N1 bus work.

## 8. Surfaces matrix (P4 acceptance mapping)

| Surface | Turn path | W05 coverage |
|---|---|---|
| CLI / TUI | agent loop → `pre_llm_call` + system prompt | Channels S+T |
| Gateway chat (incl. bots/group) | same loop; `sender_id`/`platform` kwargs present | T (+S per session); persona resolution is per PROFILE, never per remote sender — `persona_id` ≠ `user_id` (P4 separation, enforced in resolve step) |
| Web / Desktop | same loop | S+T |
| Cron | agent loop, SOUL kept by core | T; cron sessions get the active generation like any turn |
| Voice calls | voice runner → agent loop | T per spoken turn; long-running voice session transitions validated at turn boundaries only (no mid-utterance swap) |
| Delegated / background | child sessions (see §7) | fragments only |
| API runs | agent loop | S+T |

## 9. Build order (implementation waves within W05, later — NOT this prep)

0. Spike: supported legacy-SOUL suppression route (§4 option 1 vs 2);
   Channel S cap measurement (max kernel tier that fits
   `MAX_SYSTEM_PROMPT_SECTION_CHARS`); confirm hook kwargs on every
   surface in §8 with a throwaway trace profile.
1. `persona_live` snapshot/generation core (§5) + Reloader wiring;
   unit contracts: immutability, atomic swap, last-known-good.
2. Channel S registration (§3.1) behind `persona_live_owner` opt-in;
   fallback-off = stock bytes proof.
3. Pipeline stages 2–4 (§3.2): Router → Retriever → Budgeter live;
   retire the descriptive packet item (§3.3).
4. P.010 dedup + startup double-injection refusal (§4).
5. Receipts (§6) + PresentState turn-capture integration.
6. Delegate fragments (§7).
7. Surface sweep + gates (§10). only then the wave record, per-row
   §28.2 verdicts for ALL 30 inventory rows.

Dependencies: W04 (P2 retrieval over the W03 library) must bank
before step 3 consumes retrieval at scale — step 3 may start against
the §13 index (compiled artefact) and adopt W04's FTS ranking behind
the same `PersonaRetriever` seam when it lands. W05 does NOT wait for
W07: no CLI work here beyond receipts on disk.

## 10. Test / gate plan

Via `scripts/run_tests.sh` only; counts from log files; one heavy
suite at a time on the shared laptop (resource law).

- Contract suites: existing 48 `test_volmarr_persona_*.py` files must
  stay green unchanged (the pure surfaces do not move); new
  `test_volmarr_persona_live_*.py` for snapshot/swap/dedup/fragments.
- Regression gate: full Volmarr/Kista contract set = banked baseline
  957 passed / 7 failed / 1 skipped at W03 banking — the 7 are the
  known live-transport set, name-identical; zero new failures.
- **Real-conversation gate (WAVE_PLAN):** scripted real gateway turns
  (not stubs) on CLI + gateway chat + one delegated session, with
  prompt tracing proving: kernel hash present and identical at turn 1
  and turn N; retrieved stable ids match the receipt; mid-session
  persona edit activates on the NEXT turn only.
- **A/B profile isolation (WAVE_PLAN):** profiles A and B with
  distinct persona docs run interleaved (A→B→A); assert zero
  cross-contamination of kernel hash, retrieved ids, receipts;
  non-opt-in profile C proves byte-identical stock prompts.
- P.017 hooks (full P.017 belongs to the persona ticket set; W05
  provides its live substrate): 1,000-turn drift run is a W07/Q3
  gate, but W05 must land the kernel-fingerprint stability evidence
  (same pinned hash across model switch — §34) and the multi-persona
  + subagent isolation cases from §8/§7.
- Disabled-plugin proof: plugin off ⇒ official Hermes output
  unchanged (roadmap §9 acceptance), incl. legacy SOUL present.

## 11. Risks

- R1. Channel S is volatile-tier + frozen: positioning purists may
  read §9's order as unmet. Mitigation: this draft states the limit
  plainly; Channel T carries per-turn order discipline within the
  packet (kernel echo first). If Volmarr wants true stable-tier
  placement, that is a core change needing his word (Q1/Q2).
- R2. Double injection during transition (legacy SOUL + kernel) —
  the exact failure P.010 names. Mitigation: §4 fail-loud validation.
- R3. Packet budget contention: real persona content now competes
  with 30 other packet sources in 6k chars. Mitigation: §15 budgets
  made explicit in receipts; any cap change is a named decision,
  not a silent constant bump.
- R4. Compile cost per turn: Reloader check must stay hash-cheap;
  full compile only on hash change (§48 cache contract — first live
  use; the cache itself is in-process only in W05, no new on-disk
  generated dir without a W03-manifest decision).
- R5. Privacy: receipts and retrieved sections are operator-only;
  group-chat surfaces must never leak persona internals to remote
  participants (receipts never enter tool results or messages).

## 12. Open questions (for Volmarr / coordinator — prep does not decide)

- Q1. Accept the two-channel reading of §9 (frozen system-prompt
  section + per-turn packet), or is a core patch for stable-tier
  kernel placement authorised as a CUSTOMIZATIONS divergence?
- Q2. P.010 route: supported config suppression if the spike finds
  one; if not, operator-step + fail-loud validation (option 2), or
  hold P.010 for an explicit core-change decision?
- Q3. Kernel tier default per model class (§64 micro/standard/large)
  and the Channel S cap overflow policy: tier-down automatically, or
  refuse ownership until the operator picks a tier?
- Q4. Should `persona_runtime_enabled` be retired in favour of the
  single `persona_live_owner` opt-in (cleaner), or kept as a second
  gate for metadata-only mode?
- Q5. Delegate fragments: is in-process-only coverage (§7 honest
  limit) acceptable for W05's gate, with cross-process deferred to
  W09/N1?

---

*Prep record: audit read on the merged tree (roadmap §§9–10, tickets
P.008–P.011/P.017; CAMPAIGN_STATE_MODERNIZATION.md through the W03
banking closure; WAVE_PLAN.md Team 06 entry in ~/hermes-hack-forge;
persona_runtime.py docstring §§3–94 + bridge; present_state.py;
context_packet.py; identity.py; persona_canon.py; __init__.py
registration; core turn_context.py / system_prompt.py /
prompt_builder.py / plugins.py extension surfaces). No code changed,
no tests run (light read-only inspection only, per prep brief —
a Rúnmál suite shares the laptop).*
