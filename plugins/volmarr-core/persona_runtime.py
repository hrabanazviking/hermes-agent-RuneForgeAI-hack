"""Persona runtime foundations (Persona Runtime roadmap §§3-70).

The Persona Runtime roadmap defines a character by a collection
of human-editable Markdown documents whose *semantic roles* are
named in configuration — never by filename convention (§§1, 3).
This slice stands up only the foundations, reconciled against
the persona surfaces that already exist in this plugin:

- the identity store's ``persona_pack`` is a bounded *name*
  string only — it owns no persona text and is untouched here;
- persona canon (Self-Aware Agency §16) is a single YAML file
  of bounded assertions the runtime evaluates against facts —
  a different artefact from canonical persona *documents*;
- the layered self-model is runtime evidence about the entity,
  not authored persona material.

What stands here, and nothing more:

- §3 human-editable configuration: a read-only config file
  (``config/persona.yaml``) naming a persona id, a display
  name, a persona directory, and a document map of
  role -> {file, required}. The runtime cares about roles, not
  filenames; the runtime never writes this file or any
  document it names — changes are human edits only.
- §4 optional document extension: any extra role beyond the
  six core roles (``core``, ``service_bible``,
  ``memory_policy``, ``tool_policy``, ``relationship``,
  ``avatar``) is accepted as a first-class document with its
  own semantic role; adding one needs no code change here.
- §5 three-layer model, as a compiled artefact: Layer A is
  the persona kernel (sections of the ``core`` document whose
  headings name kernel material — identity, motivation,
  relationship, communication, laws, boundaries, role,
  quirks — falling back to the core document's leading
  sections; bounded to the §5 kernel token band), Layer B is
  the retrieval index (every section of every document,
  addressable by role and stable section id, with its text
  retained for a later retrieval slice), and Layer C is the
  canonical documents themselves (paths + hashes; their full
  text is compiled, never injected by this layer).
- §6 persona compiler: an explicit, deterministic compile —
  load, parse sections, normalise, derive the kernel, build
  the index, hash every document and the kernel. It runs only
  when called (startup, file change, or manual request are
  caller decisions); it never runs per message and it writes
  nothing — the compiled artefact is returned, not persisted
  (the §48 compilation cache and §49 generated directory are
  later sections, not this slice).
- §7 do not summarize blindly: the kernel, the index, and the
  IR all carry section text *verbatim* (after the §6
  whitespace normalisation only). No generated summary,
  paraphrase, or extracted prose is ever produced by this
  layer; structured representation means deterministic
  classification of whole verbatim sections, not rewriting.
- §8 PersonaIR: the compiler's explicit intermediate
  artefact. Every compiled section is classified
  deterministically into exactly one of the thirteen §8
  categories (identity, motivations, values, relationship,
  communication, behavioral_rules, preferences, boundaries,
  tools, memory, embodiment, quirks, projects) — first by
  heading keywords, then by the document's semantic role —
  and the IR carries all thirteen keys in roadmap order,
  empty where no section classifies there. The Markdown
  documents remain canonical; the IR is generated runtime
  data (``generated: True``, ``human_editable: False``),
  carries an ``ir_hash`` over its canonical form, and is
  never written to disk by this layer, so no human is ever
  asked to edit it.
- §9 persona kernel generation: the kernel's source mix is
  the roadmap's formula, in roadmap order — PERSONA_CORE
  (the §5 kernel-marked core sections, with the leading-
  sections fallback) + highest-priority RELATIONSHIP_MODEL
  rules + highest-priority SERVICE_BIBLE rules + critical
  TOOL_POLICY boundaries. "Highest-priority" / "critical"
  is deterministic and explicit here: a non-core section
  enters the kernel only when its heading names a rule,
  law, principle, boundary, policy, or a critical /
  forbidden / prohibition marker (``kernel_source_kind``);
  narrative, preference, and guidance sections of those
  documents stay in the retrieval index, and no other role
  (memory policy, avatar, extensions) ever enters the
  kernel. Whole sections only, under the §5 band: a
  candidate that would overflow the ceiling is skipped, so
  a later small critical boundary can still fit. The
  kernel records its provenance (role, section id, source
  kind) and per-kind counts.
- §10 pin the kernel: the compiled artefact carries the
  kernel's pinning spec — the designated prompt order
  (system runtime rules, then the persona kernel, then
  active context, then the user message; the kernel is
  never buried in retrieved memory) and the stability this
  layer can actually guarantee (a deterministic compile:
  identical documents produce an identical kernel hash,
  and changing a non-kernel section never changes the
  kernel). Actual placement in a live prompt belongs to
  prompt assembly (§53, which stands below as a pure
  order surface, not a live assembler); this layer
  injects nothing and claims no placement it does not
  perform.
- §11 section-aware Markdown parser: documents are split
  only at heading boundaries — conceptual sections, never
  arbitrary token chunks; a long section stays one whole
  section. Headings are semantic: a leading enumeration
  prefix (``37. ``) is presentation, not identity, and is
  stripped from the display heading and the slug. Every
  compiled index entry carries the §11 record shape —
  document (the semantic role), section (the bare slug),
  heading (the display heading), content (the verbatim
  section text) — plus a derived priority.
- §12 stable section ids: every section also carries a
  persistent, role-prefixed identifier
  (``relationship.when_disagreeing``) — unique across all
  documents, deterministic for identical documents, and
  unchanged when a section is merely renumbered, so
  retrieval results stay explainable across recompiles.
  The within-document bare slug remains as ``section_id``
  for the kernel and IR surfaces that already use it.
- §13 hybrid persona retrieval: an explicit, deterministic
  retrieval layer over the Layer B index — never only
  embeddings. Five of the §13 components stand here:
  keyword matching over heading + verbatim text, document
  role affinity, section tags (role + §8 category + heading /
  section tokens), current task classification (the pure
  ``classify_task`` lexicon over the query/task text), and
  the §11 derived priority, combined by the pure
  ``retrieval_score`` function into an explainable score
  whose components are returned with every result. Results
  are named by their §12 stable ids. The sixth component,
  semantic similarity, is honestly unavailable: this plugin
  owns no embedding surface, so every score records
  ``semantic: None`` and ``hybrid_components`` names it
  unavailable rather than faking a similarity value.
  Retrieval is an explicit call only — no hook, no budgeter
  (§15 is later), and nothing retrieved is injected by
  this layer.
- §14 persona router: ``PersonaRouter`` decides which
  persona sections a task *requires*, from the five §14
  inputs (user message, current task, active project, tool
  intent, conversation state — any subset may be present).
  The pure ``route_sections`` function classifies the
  combined signals with the §13 lexicon, derives a task
  label (an explicit current task wins, slugified; else a
  deterministic label from the first matching tag; else
  ``general``), and selects required sections per task tag
  — the top sections in §13 score order whose tags contact
  that tag's section keywords — filled from the §13
  retrieval ranking, capped, and ordered by score with
  stable-id tiebreaks. Every required section is named by
  its §12 stable id and carries the tags that required it
  plus its explainable §13 score. Routing is an explicit
  call only: it writes nothing, injects nothing, and no
  budgeter (§15) has trimmed its output yet.
- §15 token budgeter: ``PersonaContextBudgeter`` / the pure
  ``budget_items`` function allocate estimated tokens across
  the four §15 categories (persona kernel, dynamic persona
  retrieval, relevant memories, project state), each with
  the roadmap's suggested range. Allocations are
  configurable per category, and scale by model context
  class: a small local model receives each category's
  minimum, a standard model its suggested maximum, and a
  large-context model twice that. Trimming is whole-item
  only (a section is never cut mid-text, §7), in priority
  order (derived priority, then caller score, then id) —
  an item that does not fit is excluded with its reason
  named, and a later smaller item may still fit. Categories
  are independent: one category's overflow never spends
  another's allocation. Budgeting is an explicit call only:
  it writes nothing, injects nothing, and assembles no
  prompt (§53 is later).
- §16 priority system: persona information carries a
  priority level — P0 identity-critical, P1 strong
  behavioral rule, P2 important preference, P3
  context-specific preference, P4 aesthetic/background
  detail (``PRIORITY_LEVELS``). A level may be *authored*:
  a trailing ``[P0]``–``[P4]`` marker on a section heading
  is this layer's authored-metadata convention — the
  marker is stripped from the semantic heading (so it
  never changes a section's stable id) and recorded as
  the section's authored level. Where no marker stands,
  the level is *derived* deterministically by the pure
  ``priority_level`` function, reconciled with the §11
  bands: kernel core sections are P0, other kernel
  sections and kernel-marked rules are P1, the
  persona-defining §8 categories are P2, preference /
  project / tool / memory / communication material is
  P3, and quirks, embodiment, the preamble, and the rest
  are P4. An authored level wins over the derived one
  everywhere (index float, retrieval, kernel, budgeter).
  §16's hard rule stands in code in both places tokens
  are saved: kernel generation never skips a P0 section
  to fit the §5 ceiling (a P0-heavy kernel surfaces
  over-band, honestly), and the §15 budgeter never
  excludes a P0 item in the persona-kernel category as
  ``over_budget`` (its category may report negative
  remaining rather than evict P0 material).
- §17 character anchors / §18 negative identity anchors:
  the human-authored config may carry two bounded lists —
  ``anchors`` (explicit statements of what the character
  *is*) and ``anti_anchors`` (explicit statements of what
  the character is *not*, for drift resistance). Both are
  validated in the config store (bounded count and length,
  no duplicates, no empty entries) and carried *verbatim*
  (§7) into the compiled artefact. Anchors are not a
  second kernel builder: the kernel generation stands the
  anchor block — anchors first, then anti-anchors, each
  statement on its own line verbatim — ahead of every
  ordinary section, unconditionally (anchors are never
  evicted to fit the §5 ceiling, the §16 P0 rule applied
  to authored identity material; a kernel heavy with
  anchors surfaces over-band, honestly). The kernel
  records both lists and their counts, and changing an
  anchor changes the kernel hash (and therefore the
  persona hash), so anchor edits are detectable like any
  other persona change. A profile with no anchors
  compiles exactly as before this section stood.
- §19 persona hash: every compile carries its *hash
  record* — the stored form §19 names: the persona
  version (the persona config format version,
  ``PERSONA_CONFIG_VERSION``; per-persona versioning is
  §22, a later section), the per-document sha256 hashes
  by role, the kernel hash, and the combined persona
  hash. The pure ``detect_changes`` function compares
  two records and names exactly what changed (documents
  added, removed, or hash-changed; kernel changed;
  persona changed). §19's compile timestamp is NOT
  inside the deterministic artefact — identical inputs
  must compile identically (§6) — so a timestamp enters
  a record only when a caller explicitly stamps one
  (``hash_record(compiled, compiled_at=...)``, a
  timezone-aware ISO timestamp, validated); the record
  a compile carries always has ``compiled_at`` None.
- §20 hot reload: an explicit change check, not a
  resident file watcher (this plugin owns no watcher and
  starts none). ``PersonaReloader.check(previous)``
  recompiles and, via the pure ``reload_plan`` function,
  walks the §20 chain only as far as the hashes require:
  detect the hash change, reparse the changed documents
  (the fresh compile is the reparse), update the
  PersonaIR and rebuild the retrieval index when any
  document changed, and recompile the kernel only when
  the kernel hash itself changed — an edit to a
  non-kernel section therefore never recompiles the
  kernel, and an unchanged persona returns the previous
  artefact untouched. No restart is required or claimed
  beyond this explicit check; wiring the check into a
  live session is a caller decision, like compilation
  itself (§6).
- §21 change impact detection: not every edit requires
  kernel regeneration, and the pure ``change_impact``
  function classifies a change between two compiles by
  semantic impact — the section-level diff (stable ids
  added / removed / changed, each with its §8 category,
  §16 priority level, and kernel membership) mapped to
  one impact class (none / patch / minor / major). An
  avatar embodiment edit (the roadmap's skirt-material
  example) is a patch and requires no kernel rebuild; a
  core relationship-authority edit is major and does.
  Kernel rebuild itself is the §19 kernel-hash signal,
  reported separately from the semantic class.
- §22 persona versioning: the human-authored config may
  carry a per-persona ``version`` (semver; default
  ``0.1.0``) — distinct from §19's config format version.
  Every compile carries it, and the pure
  ``version_record`` function returns the §22 record
  (persona_id, persona_version, compiled_at, source_hash
  — the artefact's persona hash; a timestamp only as an
  explicit validated caller stamp, as in §19).
  ``change_impact`` also suggests the next version from
  the previous artefact's version under §22's semantics
  (MAJOR identity / relationship architecture, MINOR new
  preferences or meaningful behavior extension, PATCH
  wording / formatting / minor clarification). The
  suggestion is deterministic advice only: the human
  confirms a bump by editing the config, which this
  layer never writes, and the runtime never bumps a
  version itself.
- §23 conversation drift problem: long conversations
  create seven named dangers — recent-message dominance,
  summary mutation, context truncation, assistant
  self-imitation, memory contamination, user mood
  overfitting, and temporary roleplay overriding
  identity. The pure ``drift_defenses`` function names
  each danger, in roadmap order, with the defense this
  system stands against it, grounded in the surfaces
  already banked where they exist (the §10 kernel
  pinning spec, the §7 verbatim rule with the §19/§20
  hash-and-reload surfaces, the §15/§16 never-evict
  rules, the §§17/§18 anchors, and the §24 precedence
  rule itself). Defenses that are contract rules rather
  than mechanisms in code are labelled as rules in the
  data, honestly; this layer is not a conversation
  monitor and watches no conversation.
- §24 do not derive character from chat history:
  conversation history may affect current mood,
  immediate context, and recent events, but must never
  redefine foundational personality — canonical persona
  always outranks conversational drift. The pure
  ``precedence_order`` function returns the conceptual
  priority in roadmap order (PERSONA CORE >
  RELATIONSHIP MODEL > SERVICE BIBLE > long-term memory
  > current conversation > temporary emotional state),
  mapping the three document tiers to the compiler's
  semantic roles (``core``, ``relationship``,
  ``service_bible``); the other three tiers are
  non-document sources. The pure ``classify_influence``
  function classifies a claimed source (a canonical
  document role or name, memory, conversation history
  or a summary of it, or a temporary state/roleplay) by
  what it may affect and whether it may redefine
  foundational personality, and ``precedence_winner`` /
  ``outranks`` compare two sources by tier. These are
  contract functions only: no conversation is read,
  scored, or monitored here.
- §25 conversation summaries must not define persona: a
  summary may record *state* ("was frustrated during
  debugging") but must never become a *trait* claim ("is
  a frustrated personality"). The pure
  ``classify_summary_claim`` function classifies a
  claim's form by explicit grammatical markers only —
  trait-form markers win, then temporal/state markers,
  otherwise the claim is unclassified — and a summary
  may record only state-form claims. No summary claim,
  of any form, may define persona or redefine traits:
  the summary source inherits the §24 conversation tier.
  This layer builds no summariser and reads no summary.
- §26 trait vs state: the separation is explicit.
  Traits (the roadmap's examples: warm, devoted,
  intelligent, non-oppositional counselor) come from
  canonical persona files only and never decay. States
  (currently amused, currently concerned about
  architecture) are temporary: anything sourced from a
  non-canonical tier is at most a state, however it is
  claimed, and states decay deterministically — the
  pure ``decayed_strength`` / ``state_decay`` functions
  apply this layer's recorded convention (a 24-hour
  half-life; a state below 0.05 strength is expired).
  A decayed or expired state never becomes a trait.
- §29 drift score: the conceptual score artefact stands
  in the roadmap's YAML shape — a ``drift`` mapping with
  a ``total`` and per-dimension values over the ten §28
  dimensions — built by the pure
  ``drift_score_artifact`` function from the §28 score
  record and checked by the pure
  ``validate_drift_score_artifact`` function, which
  recomputes every derived field and refuses an artefact
  whose total, significance, or route disagrees with its
  dimensions. Only significant drift triggers repair —
  tiny stylistic differences are not polished.
- §30 drift repair: when drift is significant, repair
  follows the roadmap's pipeline — draft, identify
  violated persona anchors, rewrite minimally, verify,
  deliver — and never regenerates everything. The pure
  ``repair_pipeline`` / ``repair_contract`` /
  ``repair_plan`` functions stand that pipeline in
  contract form, reconciled against the §§17/18 anchors
  (the violated anchors a plan rewrites against are the
  authored character anchors and anti-anchors, carried
  verbatim and bounded like the config lists). A plan
  for insignificant drift is a deliver-without-repair
  plan with no steps. This layer rewrites no draft: the
  plan is a contract surface for whoever repairs.
- §31 fast local persona watchdog: watchdog work is an
  ideal job for the small local nervous-system model. The
  pure ``local_watchdog_tasks`` / ``local_watchdog_contract``
  / ``watchdog_worker`` functions name the six tasks it
  performs without expensive heavy inference (persona
  classification, drift detection, section retrieval,
  tone checking, memory routing, response scoring), each
  grounded in a banked surface; the larger model generates
  difficult content, and the local model keeps the
  personality coherent. This layer runs no model.
- §32 persona refresh: for extremely long sessions the
  active context is refreshed periodically — every N
  messages (this layer's recorded convention: 50), after
  context summarization, or after a model switch. The
  pure ``refresh_triggers`` / ``refresh_contents`` /
  ``refresh_contract`` / ``refresh_due`` / ``refresh_plan``
  functions stand that shape: a refresh carries exactly
  the Persona Kernel, the current relationship state, and
  the relevant Service Bible anchors, preventing slow
  identity evaporation. This layer watches no session,
  counts no messages in a live conversation, assembles
  none of the contents, and injects nothing.
- §33 event-based refresh: better than a fixed interval
  alone — a refresh is also due after context compression,
  a model switch, an agent handoff, a long idle period, a
  persona file modification, a major relationship event,
  or memory consolidation. The pure
  ``event_refresh_triggers`` / ``event_refresh_contract`` /
  ``event_refresh_due`` / ``event_refresh_plan`` functions
  extend the §32 refresh shape to those events: naming
  an event is naming its occurrence, a due plan carries
  exactly the §32 contents, and no fixed interval is
  required. This layer watches for no event.
- §34 model switching: Hermes may route between models,
  and every model receives the same canonical Persona
  Kernel — the model is the engine, the persona system
  is the identity layer, so the persona remains itself
  across a switch. The pure ``model_switch_contract`` /
  ``model_switch_plan`` / ``kernel_identity_preserved``
  functions stand that identity surface over the §§9–10
  kernel and its hash: a switch plan names one kernel
  hash for both models, and identity is preserved exactly
  when the kernel hash after a switch equals the hash
  before it. This layer routes no model and switches
  nothing.
- §35 persona handoff packet: when routing to another
  model, a packet is created in the roadmap's YAML shape
  (``persona_handoff``: persona id, §22 persona version,
  kernel named by its hash, current mode, relationship
  state, relevant sections by §12 stable id), avoiding
  passing the whole conversation when unnecessary. The
  pure ``handoff_contract`` / ``handoff_packet`` /
  ``validate_handoff_packet`` functions stand it: the
  builder refuses a section the compiled index does not
  contain. This layer routes nothing and hands nothing
  off.
- §36 subagent separation: subagents are not turned into
  the primary persona — each carries its own identity
  and role, while the primary persona may delegate and
  maintains its own identity. The pure
  ``subagent_examples`` / ``subagent_contract`` /
  ``subagent_separation`` functions stand the separation
  over the roadmap's example roster. This layer
  delegates nothing and spawns nothing.
- §37 persona state: the dynamic runtime object stands
  in the roadmap's YAML shape (``persona_state``: id,
  the §22 version, active mode, emotional state —
  warmth / playfulness / focus, relationship state —
  trust, active project, current task). The pure
  ``persona_state`` builder takes id and version from a
  compiled artefact and validates every dynamic field;
  the pure ``validate_persona_state`` function
  recomputes the normalised object and refuses
  tampering. The object is dynamic and must never
  replace canonical PersonaIR: building or validating
  one changes no compile, no kernel hash, and no IR.
  This layer stores no state and tracks nothing live.
- §38 modes: the seven modes (counselor, executor,
  architect, skald, companion, researcher, forge_worker)
  modify emphasis without changing identity — a mode
  foregrounds parts of the same personality. The pure
  ``persona_modes`` / ``mode_contract`` / ``mode_profile``
  functions stand the list and that rule, reconciled
  against §35's ``current_mode`` (a state's active mode
  must be one of the seven). This layer switches no
  mode live; mode routing is §39, a later section.
- §39 mode routing: modes are routed automatically —
  the user does not need to manually select them. The
  pure ``mode_routing_examples`` / ``mode_routing_contract``
  / ``route_mode`` functions stand the roadmap's four
  examples (coding architect → forge_worker, personal
  reflection companion → counselor, research researcher,
  creative article skald) and route a caller-supplied
  signal — an example name, or task text classified by
  the §13 lexicon plus the reflection / creative-article
  tokens the lexicon does not carry — to that example's
  mode sequence. Every routed mode is a §38 mode and
  routing changes no identity. This layer switches no
  mode live; it names the route a switcher would take.
- §40 persona-aware memory write: when memory extraction
  occurs, memories are interpreted through the persona
  system, and a memory must not introduce personality
  drift through biased summarization. The pure
  ``memory_write_contract`` / ``persona_memory`` /
  ``validate_persona_memory`` / ``classify_memory_write``
  functions stand it: a record carries the decider, the
  decision, any recommendation considered (with its
  recommender), and any persona response, and its text
  is built by one neutral template — the roadmap's
  correct example exactly (``Volmarr selected
  architecture B after considering Caducea's
  recommendation of A. Caducea accepted decision and
  implemented B.``) — while biased phrasing in the
  roadmap's incorrect form (``ignored good advice`` and
  its recorded marker kin) is refused at build time and
  flagged by classification. This layer writes no
  memory; it shapes the record an extractor would write.
- §41 memory must not override persona: memory retrieval
  must not gradually transform the persona — traits
  remain canonical and memory provides history. The pure
  ``memory_override_contract`` / ``memory_influence_allowed``
  / ``evaluate_memory_claim`` / ``memory_claim_authority``
  functions stand the §24 precedence rule applied to the
  memory tier: memory may affect current mood, immediate
  context, and recent events only, however many memories
  agree (repetition never promotes a memory's tier), and
  a memory claim may be recorded as history only in
  state form (§25) — a trait-form claim from memory is
  refused, never a persona definition. This layer reads
  and retrieves no memory.
- §42 Service Bible dynamic retrieval: the Service Bible
  may become huge, so it is never continuously injected;
  its sections are indexed by the roadmap's topic list
  (communication, coding, linux, open_source, ai,
  documentation, research, project_aesir, attention,
  adhd) and retrieved selectively. The pure
  ``service_bible_topics`` / ``classify_service_topics`` /
  ``service_topics_for_section`` / ``retrieve_service_bible``
  functions and the explicit ``PersonaServiceBibleRetriever``
  stand a deterministic selection over the compiled
  index, restricted to the ``service_bible`` role and
  reusing the §13 ranking; nothing is injected.
- §43 Relationship Model dynamic retrieval: relationship
  context is especially important during disagreements,
  personal conversation, advice, emotionally meaningful
  interaction, and shared-history discussion; for routine
  coding only the relevant relational anchors need to
  remain in the kernel, so no dynamic retrieval happens.
  The pure ``relationship_contexts`` /
  ``classify_relationship_contexts`` /
  ``relationship_contexts_for_section`` /
  ``relationship_retrieval_need`` /
  ``retrieve_relationship_model`` functions and the
  explicit ``PersonaRelationshipRetriever`` stand a
  deterministic selection over the compiled index,
  restricted to the ``relationship`` role and reusing
  the §13 ranking; nothing is injected.
- §44 Tool Policy dynamic retrieval: Tool Policy sections
  are retrieved when actual tools are being considered —
  file reading needs minimal or no extra policy, while a
  git force push retrieves the force_push,
  remote_git_operations, reversibility, and authorization
  sections. The pure ``tool_actions`` /
  ``classify_tool_action`` / ``tool_policy_needs`` /
  ``retrieve_tool_policy`` functions and the explicit
  ``PersonaToolPolicyRetriever`` stand a deterministic
  selection over the compiled index, restricted to the
  ``tool_policy`` role; this layer executes no tool.
- §51 startup sequence: the pure ``startup_steps`` /
  ``startup_contract`` / ``startup_plan`` functions stand
  the Hermes startup order (load persona.yaml, resolve
  the persona directory, validate required documents,
  compare source hashes, then load the compiled persona
  if the hashes are unchanged or compile it if they
  changed or none was compiled, load the Persona Kernel,
  initialize the retrieval index, initialize Persona
  State, and the persona awakens) as a pure plan over two
  compiled artefacts' §19 hash records. This layer owns
  no boot hook and starts nothing.
- §52 request pipeline: the pure
  ``request_pipeline_stages`` / ``request_pipeline_contract``
  / ``request_pipeline_plan`` functions name the ten
  per-request stages in roadmap order (user message, task
  classifier, persona router, persona retrieval, memory
  retrieval, context budgeter, prompt assembler, model,
  persona watchdog, tools / response), each with its
  banked owner surface where one stands in this plugin
  (§13 task classification, §14 router, §13 retrieval,
  §15 budgeter, §27 watchdog), an external owner where
  the stage belongs elsewhere (the caller, the memory
  subsystem, the model); prompt assembly's owner is the
  §53 pure order surface below. The task classifier's
  four outputs (task type, entities, project, tool
  intent) are validated in shape only. This layer runs
  no per-message pipeline.
- §53 prompt assembly order: the pure
  ``prompt_assembly_order`` / ``prompt_assembly_contract``
  / ``prompt_assembly_plan`` functions stand the
  recommended prompt order in roadmap order (runtime
  system rules, Persona Kernel, current Persona State,
  relevant persona sections, relevant long-term memory,
  active project context, recent conversation context,
  current user message) as a pure plan surface. This is
  the section the §10 pinning spec designated as its
  enforcer: the kernel sits at position 1, directly
  under the runtime system rules, and the character
  appears before transient context. A caller-supplied
  slot list is validated as an order-preserving
  subsequence of the canonical order (unknown,
  duplicated, or out-of-order slots are refused). This
  layer assembles no prompt and is not wired into the
  turn path.
- §54 why order matters: the pure
  ``order_matters_reasons`` / ``order_matters_contract``
  / ``evaluate_prompt_order`` functions stand the two
  roadmap reasons in roadmap order (if persona comes
  after huge conversation history, recent context may
  dominate; putting identity near the highest-level
  instructions helps keep the model anchored) and
  evaluate a caller-supplied order against them: the
  kernel's position, whether character appears before
  transient context, whether the order is anchored, and
  the named risks when it is not. This layer evaluates
  an order only; it reorders nothing live.
- §55 conversation history compression: the pure
  ``compression_components`` / ``compression_contract`` /
  ``compression_plan`` functions stand the compression
  shape in roadmap order — a recent verbatim window
  (the roadmap's example band: the last 8–20 messages)
  plus structured conversation state plus episodic
  summaries plus retrieved older memories — instead of
  endlessly appending messages. A plan is pure
  arithmetic over caller-supplied counts: how many of
  the most recent messages stay verbatim under a window
  capacity inside the band, and how many older messages
  the other three components carry. The §25 summary
  guard and §26 trait/state separation govern what the
  summary and state components may claim. This layer
  compresses no live history, summarises nothing, and
  retrieves no memory.
- §56 long-term conversation design: the pure
  ``long_term_design`` / ``long_term_design_contract`` /
  ``placement_for`` functions stand the placement in
  roadmap order — identity lives in persona, history
  lives in memory, task state lives in project/context,
  and the conversation window handles immediacy — so
  the model never needs the entire conversation history
  to remain itself. This layer places nothing live; it
  names where each concern belongs and who owns it.
- §57 drift test suite: the pure ``drift_test_scenarios``
  / ``drift_test_contract`` / ``drift_test_scenario``
  functions stand the eight automated drift scenarios in
  roadmap order (repeated disagreement, ignored advice,
  a 1000-turn conversation, a local-to-cloud model
  switch, conversation compression, a technical
  question, an emotional question, temporary roleplay),
  each naming the banked surface that would judge it
  (the §27/§28 watchdog drift score, the §32 refresh,
  the §34 model-switch identity surface, the §55
  compression shape, the §23 drift defenses). This
  layer runs no test and evaluates no response.
- §58 golden persona tests: the pure ``golden_record``
  / ``golden_example`` / ``validate_golden_record`` /
  ``golden_contract`` functions stand expected-behavior
  examples in the roadmap's ``persona/tests/*.jsonl``
  record shape — exactly a scenario plus its expected
  traits — with the roadmap's rejected-architecture-
  suggestion example carried verbatim. Records are
  built and validated purely; this layer runs no
  golden test and executes no model response.
- §59 style fingerprint: the pure ``style_dimensions``
  / ``style_fingerprint`` / ``style_example`` /
  ``validate_style_fingerprint`` / ``style_contract``
  functions stand a lightweight fingerprint in the
  roadmap's YAML shape — a ``style`` mapping over the
  nine named dimensions (warmth, formality, verbosity,
  playfulness, deference, initiative, technicality,
  mythic_language, emotional_intensity), unit-interval
  values, a supplied subset kept in roadmap order —
  with the roadmap's example carried verbatim. It is
  guidance, not rigid mathematical personality; this
  layer scores no live style and derives no dimension
  from prose.
- §60 behavior fingerprint: the pure
  ``behavior_names`` / ``behavior_fingerprint`` /
  ``behavior_example`` / ``behavior_expectation`` /
  ``validate_behavior_fingerprint`` /
  ``behavior_contract`` functions stand the named
  boolean behaviors in the roadmap's YAML shape — a
  ``behavior`` mapping covering exactly the seven
  roadmap behaviors — with the roadmap's example
  carried verbatim (relitigate_decisions false: never
  relitigate). The roadmap names these behaviors as
  automatically testable; this layer builds and
  validates records only and evaluates no response.
- §61 character drift telemetry: the pure
  ``telemetry_fields`` / ``drift_telemetry_record`` /
  ``validate_drift_telemetry_record`` /
  ``telemetry_example_averages`` /
  ``model_drift_averages`` / ``telemetry_contract``
  functions stand one locally comparable record
  (drift score, kernel version, model used, mode,
  retrieved persona sections by stable id) and the
  deterministic per-model average drift over validated
  records, with the roadmap's example averages carried
  verbatim. This layer persists no record and records
  no live telemetry.
- §62 model router + persona quality: the pure
  ``model_selection_considerations`` /
  ``persona_adherence`` / ``model_quality_table`` /
  ``preferred_companionship_model`` /
  ``model_router_contract`` functions stand model
  selection considering persona adherence alongside
  intelligence — adherence derived purely from the
  §61 average drift — ranking supplied averages by
  adherence for everyday companionship. The per-model
  metric set carrying intelligence is §63, a later
  section; this layer routes no live model.
- The §11 priority float is *derived* unless authored:
  the pure ``section_priority`` function bands a section
  by signals this layer already computes deterministically
  (in the kernel 0.90; kernel-marked but not selected
  0.80; identity/values/boundaries/rules/motivations/
  relationship material 0.60; everything else, including
  the unheaded preamble, 0.40); an authored §16 level
  maps to its own float (P0 1.00 … P4 0.25) instead.

Token counts are deterministic estimates (ceil(chars / 4)),
named as estimates wherever they surface. Disabled by
default. No hook and no turn-path caller compiles or injects
anything; the bounded packet item names only the persona id,
the kernel hash, and document/section counts.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from hermes_constants import get_hermes_home

from .context_packet import ContextItem
from .identity import IdentityError, IdentityStore, _as_bool

PERSONA_CONFIG_VERSION = 1
# §22: the default per-persona version when the human has
# not authored one in the config yet.
DEFAULT_PERSONA_VERSION = "0.1.0"
DEFAULT_CONFIG_PATH = Path("config") / "persona.yaml"
DEFAULT_DIRECTORY = Path("persona")
MAX_CONFIG_BYTES = 64 * 1024
MAX_DOCUMENT_BYTES = 512 * 1024
MAX_DOCUMENTS = 32
MAX_NAME_CHARS = 128
KERNEL_TOKEN_MIN = 500
KERNEL_TOKEN_MAX = 1500
# §17/§18 anchor bounds: the authored lists in the config.
MAX_ANCHORS = 32
MAX_ANCHOR_CHARS = 240

# The six semantic roles §3 names, in roadmap order. §4 roles
# beyond these are first-class extensions, not errors.
CORE_ROLES = (
    "core",
    "service_bible",
    "memory_policy",
    "tool_policy",
    "relationship",
    "avatar",
)

# Heading words that mark a core-document section as kernel
# material (§5 Layer A: identity, core motivation, relationship
# orientation, communication style, essential behavioral laws,
# important boundaries, role, character-defining quirks).
KERNEL_HEADING_WORDS = frozenset({
    "identity", "motivation", "relationship", "communication",
    "style", "law", "laws", "boundary", "boundaries", "role",
    "quirk", "quirks", "essence", "character",
})

# §9 kernel source mix, in the roadmap's formula order. Only
# these roles can enter the kernel, each under its own kind.
KERNEL_SOURCE_ORDER = (
    "core", "relationship", "service_bible", "tool_policy",
)
_KERNEL_SOURCE_KIND = {
    "core": "core",
    "relationship": "relationship_rule",
    "service_bible": "service_rule",
    "tool_policy": "tool_boundary",
}

# Heading words that mark a non-core section as highest-
# priority / critical for §9: the heading explicitly names a
# rule, law, principle, boundary, or policy, or carries a
# critical / forbidden / prohibition marker. Narrative,
# preference, and guidance headings carry none of these.
RULE_HEADING_WORDS = frozenset({
    "rule", "rules", "law", "laws", "principle", "principles",
    "boundary", "boundaries", "policy", "policies", "critical",
    "forbidden", "prohibition", "prohibitions",
})

# §10 pinning: the designated prompt order. The kernel sits
# in the highest practical persistent layer — directly under
# the system runtime rules, ahead of active context and the
# user message, never buried in retrieved memory.
PINNING_ORDER = (
    "system_runtime_rules", "persona_kernel", "active_context",
    "user_message",
)


def kernel_source_kind(role: str, heading: str) -> str | None:
    """The §9 kernel source kind for a section, or None.

    Pure function of (role, heading). The core document uses
    the §5 kernel heading words; the three other named roles
    use the rule/boundary heading words; every other role
    never enters the kernel.
    """
    kind = _KERNEL_SOURCE_KIND.get(role)
    if kind is None:
        return None
    tokens = set(_slugify(heading).split("_"))
    words = KERNEL_HEADING_WORDS if role == "core" \
        else RULE_HEADING_WORDS
    return kind if tokens & words else None


def kernel_source_kinds() -> list[str]:
    return [_KERNEL_SOURCE_KIND[role] for role in KERNEL_SOURCE_ORDER]


def anchor_block(anchors: Any = (), anti_anchors: Any = ()) -> str:
    """The §17/§18 anchor block, verbatim, or "" when empty.

    Pure function: anchors first (what the character is),
    then anti-anchors (what the character is not), each
    statement on its own line exactly as authored (§7).
    This block stands at the head of every kernel.
    """
    lines = [str(item) for item in (anchors or ())]
    lines += [str(item) for item in (anti_anchors or ())]
    return "\n".join(lines)


def _validate_anchor_list(raw: Any, field: str) -> list[str]:
    """One bounded §17/§18 anchor list from the config.

    Absent means empty. A present list must be a list of
    non-empty bounded strings with no duplicates — an
    invalid anchor list fails the whole config closed
    rather than silently dropping authored identity
    material.
    """
    if raw is None:
        return []
    if not isinstance(raw, list) or len(raw) > MAX_ANCHORS:
        raise PersonaRuntimeError(f"persona {field} are invalid")
    anchors: list[str] = []
    for item in raw:
        if not isinstance(item, str) or not item.strip() \
                or len(item.strip()) > MAX_ANCHOR_CHARS:
            raise PersonaRuntimeError(f"persona {field} are invalid")
        text = item.strip()
        if text in anchors:
            raise PersonaRuntimeError(f"persona {field} are invalid")
        anchors.append(text)
    return anchors

_SLUG = re.compile(r"^[a-z][a-z0-9_-]*$")
# §22 per-persona version: strict semver, no leading zeroes.
_SEMVER = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_CONFIG_FIELDS = {"persona"}
_PERSONA_FIELDS = {
    "id", "display_name", "directory", "documents",
    "anchors", "anti_anchors", "version",
}
_DOCUMENT_FIELDS = {"file", "required"}


class PersonaRuntimeError(RuntimeError):
    """Persona configuration or documents cannot be safely read."""


def _estimate_tokens(text: str) -> int:
    return int(math.ceil(len(text) / 4)) if text else 0


def _slugify(heading: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", heading.strip().lower()).strip("_")
    return slug or "section"


_ENUM_PREFIX = re.compile(r"^\d+(?:\.\d+)*[.)]\s+")

# §16 authored priority: a trailing [P0]-[P4] marker on a
# heading is authored metadata, not heading text.
_PRIORITY_MARKER = re.compile(r"\[(P[0-4])\]\s*$", re.IGNORECASE)


def authored_priority_level(raw: str) -> str | None:
    """The §16 level authored on a raw heading, or None.

    Pure function of the raw heading text: a trailing
    ``[P0]``–``[P4]`` marker (any case) is the authored
    level; anything else (including an out-of-range
    ``[P9]``) is ordinary heading text, not metadata.
    """
    match = _PRIORITY_MARKER.search(raw.strip())
    return match.group(1).upper() if match else None


def display_heading(raw: str) -> str:
    """The §11 semantic heading: enumeration is not identity.

    A leading enumeration prefix (``37. ``, ``11.2) ``) is
    presentation — the roadmap's own example turns
    ``37. WHEN CADUCEA DISAGREES`` into the heading
    ``WHEN CADUCEA DISAGREES``. A trailing §16 authored
    priority marker (``[P0]``–``[P4]``) is metadata, not
    identity, and is likewise stripped, so authoring a
    level never changes a section's stable id. Pure
    function of the raw heading text; a heading that is
    only a number keeps it.
    """
    cleaned = _ENUM_PREFIX.sub("", raw.strip(), count=1).strip()
    cleaned = _PRIORITY_MARKER.sub("", cleaned).strip()
    return cleaned or raw.strip()


def stable_section_id(role: str, section_id: str) -> str:
    """The §12 persistent identifier: ``role.section``.

    Role-prefixed so an id is unique across every document
    and explains which document it names; deterministic, so
    identical documents always produce identical ids.
    """
    return f"{role}.{section_id}"


def core_roles() -> list[str]:
    return list(CORE_ROLES)


def parse_sections(text: str) -> list[dict[str, Any]]:
    """Split Markdown into sections by heading (§§6, 11).

    §11: the split respects conceptual boundaries only —
    sections begin at headings and are never cut at an
    arbitrary token count, however long they run. Content
    before the first heading becomes a ``preamble`` section.
    Headings are semantic (§11): a leading enumeration
    prefix is stripped (``display_heading``), so renumbering
    a section never changes its identity. Section ids are
    stable slugs of the semantic heading, disambiguated in
    document order (``name``, ``name_2``, ...); the §12
    persistent form prefixes the document role
    (``stable_section_id``). Section text is normalised:
    trailing whitespace stripped, runs of blank lines
    collapsed — the §6 normalise step; the wording itself
    is never summarised or rewritten (§7).
    """
    sections: list[dict[str, Any]] = []
    heading = "preamble"
    level = 0
    authored: str | None = None
    lines: list[str] = []

    def flush() -> None:
        body = "\n".join(lines).strip("\n")
        body = re.sub(r"\n{3,}", "\n\n", body).rstrip()
        if not body and heading == "preamble":
            return
        sections.append({
            "heading": heading, "level": level, "text": body,
            "authored_priority": authored,
        })

    for line in text.splitlines():
        match = _HEADING.match(line)
        if match:
            flush()
            level = len(match.group(1))
            authored = authored_priority_level(match.group(2))
            heading = display_heading(match.group(2))
            lines = []
        else:
            lines.append(line.rstrip())
    flush()
    seen: dict[str, int] = {}
    for section in sections:
        base = _slugify(section["heading"])
        seen[base] = seen.get(base, 0) + 1
        section["section_id"] = (
            base if seen[base] == 1 else f"{base}_{seen[base]}")
    return sections


# The thirteen PersonaIR categories §8 names, in roadmap order.
IR_CATEGORIES = (
    "identity", "motivations", "values", "relationship",
    "communication", "behavioral_rules", "preferences",
    "boundaries", "tools", "memory", "embodiment", "quirks",
    "projects",
)

# Heading-keyword classification, most specific categories
# first so a specific signal (tools, memory, embodiment, ...)
# wins over a generic one (identity). §7: classification only —
# the section text itself is carried verbatim, never rewritten.
_CATEGORY_KEYWORDS = (
    ("tools", frozenset({
        "tool", "tools", "shell", "command", "commands"})),
    ("memory", frozenset({
        "memory", "memories", "remembrance", "remembering"})),
    ("embodiment", frozenset({
        "embodiment", "avatar", "body", "appearance", "physical",
        "form"})),
    ("relationship", frozenset({
        "relationship", "relationships", "relational", "bond",
        "bonds", "companion", "devotion"})),
    ("communication", frozenset({
        "communication", "style", "voice", "speech", "language",
        "tone"})),
    ("projects", frozenset({"project", "projects"})),
    ("quirks", frozenset({
        "quirk", "quirks", "habit", "habits", "trait", "traits"})),
    ("boundaries", frozenset({
        "boundary", "boundaries", "limit", "limits", "forbidden",
        "prohibition", "prohibitions"})),
    ("preferences", frozenset({
        "preference", "preferences", "likes", "dislikes",
        "taste"})),
    ("motivations", frozenset({
        "motivation", "motivations", "purpose", "drive",
        "drives", "goal", "goals"})),
    ("values", frozenset({
        "value", "values", "virtue", "virtues", "principle",
        "principles", "ethics", "spiritual", "spirituality",
        "belief", "beliefs", "faith"})),
    ("behavioral_rules", frozenset({
        "behavior", "behaviour", "behavioral", "rule", "rules",
        "law", "laws", "execution", "conduct", "service",
        "counsel", "practice", "practices", "policy"})),
    ("identity", frozenset({
        "identity", "essence", "character", "role", "self",
        "who"})),
)

# Document-role fallback when a section heading names no
# category: the six core roles map onto the category their
# document exists for; an extension role is classified by its
# own name, and a section with no signal anywhere is
# persona-defining material by default (identity).
_ROLE_FALLBACK = {
    "core": "identity",
    "service_bible": "behavioral_rules",
    "memory_policy": "memory",
    "tool_policy": "tools",
    "relationship": "relationship",
    "avatar": "embodiment",
}


def ir_categories() -> list[str]:
    return list(IR_CATEGORIES)


def classify_section(role: str, heading: str) -> str:
    """The one §8 IR category for a section, deterministically.

    Heading keywords win (most specific first); the document
    role is the fallback. Pure function of (role, heading).
    """
    tokens = set(_slugify(heading).split("_"))
    for category, keywords in _CATEGORY_KEYWORDS:
        if tokens & keywords:
            return category
    fallback = _ROLE_FALLBACK.get(role)
    if fallback is not None:
        return fallback
    role_tokens = set(_slugify(role).split("_"))
    for category, keywords in _CATEGORY_KEYWORDS:
        if role_tokens & keywords:
            return category
    return "identity"


# §11 priority bands (derived): the kernel is
# identity-critical material; kernel-marked sections that
# did not fit are the next band; the persona-defining IR
# categories follow; the rest — preferences, background,
# the unheaded preamble — are last.
_PRIORITY_MID_CATEGORIES = frozenset({
    "identity", "values", "boundaries", "behavioral_rules",
    "motivations", "relationship",
})

# §16 priority levels, in roadmap order with the roadmap's
# own names, and the float each authored level carries.
PRIORITY_LEVELS = (
    ("P0", "identity-critical"),
    ("P1", "strong behavioral rule"),
    ("P2", "important preference"),
    ("P3", "context-specific preference"),
    ("P4", "aesthetic/background detail"),
)
_PRIORITY_LEVEL_SCORES = {
    "P0": 1.00, "P1": 0.85, "P2": 0.65, "P3": 0.45, "P4": 0.25,
}
# §8 categories whose derived level is P3; the §11 mid
# categories derive P2; quirks/embodiment and everything
# else derive P4.
_PRIORITY_P3_CATEGORIES = frozenset({
    "preferences", "projects", "tools", "memory", "communication",
})


def priority_levels() -> list[dict[str, str]]:
    return [
        {"level": level, "name": name}
        for level, name in PRIORITY_LEVELS]


def priority_level_score(level: str) -> float:
    """The float an authored §16 level carries, in [0, 1]."""
    try:
        return _PRIORITY_LEVEL_SCORES[level]
    except KeyError:
        raise PersonaRuntimeError(
            f"unknown priority level: {level!r}") from None


def priority_level(role: str, heading: str,
                   in_kernel: bool = False,
                   authored: str | None = None) -> str:
    """The §16 priority level of a section. Pure function.

    An authored level (a trailing ``[Pn]`` heading marker,
    already extracted) wins. Otherwise the level is derived
    from the signals this layer already computes: a kernel
    section of the core document is P0 (identity-critical);
    any other kernel section, and any kernel-marked (§9)
    section that did not fit, is P1 (a strong behavioral
    rule); a section classifying into a persona-defining
    §8 category is P2; preference/project/tool/memory/
    communication material is P3; quirks, embodiment, the
    unheaded preamble, and everything else are P4.
    """
    if authored is not None:
        if authored not in _PRIORITY_LEVEL_SCORES:
            raise PersonaRuntimeError(
                f"unknown priority level: {authored!r}")
        return authored
    if in_kernel:
        return "P0" if role == "core" else "P1"
    if heading == "preamble":
        return "P4"
    if kernel_source_kind(role, heading) is not None:
        return "P1"
    category = classify_section(role, heading)
    if category in _PRIORITY_MID_CATEGORIES:
        return "P2"
    if category in _PRIORITY_P3_CATEGORIES:
        return "P3"
    return "P4"


def section_priority(role: str, heading: str,
                     in_kernel: bool = False,
                     authored: str | None = None) -> float:
    """The §11 derived priority of a section, in [0, 1].

    Pure deterministic function of (role, heading, kernel
    membership) over signals this layer already computes.
    Bands: in the kernel 0.90; kernel-marked (§9) but not
    selected 0.80; sections classifying into a
    persona-defining §8 category 0.60; everything else
    0.40. An authored §16 level replaces the band with the
    level's own float (P0 1.00 … P4 0.25).
    """
    if authored is not None:
        return priority_level_score(authored)
    if in_kernel:
        return 0.90
    if heading == "preamble":
        return 0.40
    if kernel_source_kind(role, heading) is not None:
        return 0.80
    if classify_section(role, heading) in _PRIORITY_MID_CATEGORIES:
        return 0.60
    return 0.40


def build_persona_ir(persona_id: str,
                     index: list[dict[str, Any]]) -> dict[str, Any]:
    """Build the §8 PersonaIR from the compiled section index.

    Generated runtime data: every §8 category is present in
    roadmap order (empty where nothing classifies there), each
    entry carries its section text verbatim (§7), and the
    ``ir_hash`` covers the canonical category/section/text
    form so identical documents always produce identical IR.
    """
    categories: dict[str, list[dict[str, Any]]] = {
        category: [] for category in IR_CATEGORIES}
    for entry in index:
        category = classify_section(entry["role"], entry["heading"])
        categories[category].append({
            "role": entry["role"],
            "section_id": entry["section_id"],
            "stable_id": entry.get(
                "stable_id",
                stable_section_id(entry["role"], entry["section_id"])),
            "heading": entry["heading"],
            "estimated_tokens": entry["estimated_tokens"],
            "text": entry["text"],
        })
    canonical = "|".join(
        f"{category}:" + ";".join(
            f"{row['role']}/{row['section_id']}={row['text']}"
            for row in categories[category])
        for category in IR_CATEGORIES)
    return {
        "persona_id": persona_id,
        "generated": True,
        "human_editable": False,
        "categories": categories,
        "category_counts": {
            category: len(categories[category])
            for category in IR_CATEGORIES},
        "total_sections": sum(
            len(rows) for rows in categories.values()),
        "ir_hash": hashlib.sha256(
            canonical.encode("utf-8")).hexdigest(),
    }


# --- §13 hybrid retrieval -------------------------------------------
#
# Deterministic, explainable retrieval over the compiled
# Layer B index. Tokenisation reuses the slug vocabulary the
# parser already speaks, so a query, a heading, and a stable
# id all tokenise the same way.

RETRIEVAL_DEFAULT_LIMIT = 5
RETRIEVAL_MAX_LIMIT = 20

# Task lexicon: tag -> words in a user message / task text
# that signal the tag. Order is roadmap-example order first.
_TASK_LEXICON = (
    ("coding", frozenset({
        "code", "coding", "refactor", "debug", "bug", "implement",
        "function", "class", "python", "typescript", "compile",
        "test", "tests", "testing"})),
    ("git", frozenset({
        "git", "branch", "commit", "push", "pull", "merge",
        "rebase", "repository", "repo"})),
    ("filesystem", frozenset({
        "file", "files", "filesystem", "directory", "folder",
        "path", "rename", "move", "copy", "delete"})),
    ("external_mutation", frozenset({
        "push", "publish", "send", "post", "deploy", "release",
        "upload", "remote", "external"})),
    ("memory", frozenset({
        "memory", "remember", "recall", "forget", "contradiction",
        "history"})),
    ("relationship", frozenset({
        "relationship", "disagree", "disagrees", "counsel",
        "decision", "decisions", "trust"})),
    ("communication", frozenset({
        "write", "writing", "draft", "tone", "voice", "explain",
        "message", "speak"})),
    ("research", frozenset({
        "research", "search", "investigate", "explore", "compare",
        "documentation", "docs"})),
    ("planning", frozenset({
        "plan", "planning", "roadmap", "schedule", "organize",
        "organise", "prioritize", "prioritise"})),
)

TASK_TAGS = tuple(tag for tag, _ in _TASK_LEXICON)

# Section keywords each task tag looks for in a section's tags.
_TASK_SECTION_KEYWORDS = {
    "coding": frozenset({
        "coding", "code", "execution", "dependencies", "tests",
        "testing"}),
    "git": frozenset({"git", "remote", "reversibility"}),
    "filesystem": frozenset({
        "filesystem", "file", "files", "directory"}),
    "external_mutation": frozenset({
        "remote", "reversibility", "external", "mutation", "git"}),
    "memory": frozenset({"memory", "contradiction", "remembrance"}),
    "relationship": frozenset({
        "relationship", "disagrees", "disagreeing", "counsel",
        "decisions"}),
    "communication": frozenset({
        "communication", "voice", "tone", "style"}),
    "research": frozenset({"research", "documentation", "exploration"}),
    "planning": frozenset({"planning", "roadmap", "goals", "projects"}),
}

# Document roles each task tag has affinity for (§13's
# document-role component).
_TASK_ROLE_AFFINITY = {
    "coding": frozenset({"service_bible", "tool_policy", "core"}),
    "git": frozenset({"tool_policy", "service_bible"}),
    "filesystem": frozenset({"tool_policy", "service_bible"}),
    "external_mutation": frozenset({"tool_policy"}),
    "memory": frozenset({"memory_policy", "core"}),
    "relationship": frozenset({"relationship", "core"}),
    "communication": frozenset({"core", "relationship"}),
    "research": frozenset({"service_bible", "memory_policy"}),
    "planning": frozenset({"core", "service_bible"}),
}


# Retrieval stopwords: function words carry no topical
# signal, and counting them lets an unrelated section float
# on a shared "and"/"my" (the §13 example's core sections
# outranked tool_policy.reversibility on exactly that).
# _tokens is used only by the §13 retrieval functions, so
# the filter is scoped to retrieval.
_RETRIEVAL_STOPWORDS = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "by", "for",
    "from", "in", "into", "is", "it", "its", "my", "of",
    "on", "or", "the", "to", "with", "you", "your",
})


def _tokens(text: str) -> set[str]:
    return {tok for tok in _slugify(text).split("_")
            if tok and tok not in _RETRIEVAL_STOPWORDS}


def classify_task(text: str) -> list[str]:
    """The §13 task tags a message signals, in lexicon order.

    Pure function of the text: a tag is present when any of
    its lexicon words appears as a token. No model call.
    """
    tokens = _tokens(text or "")
    return [tag for tag, words in _TASK_LEXICON if tokens & words]


def task_tags() -> list[str]:
    return list(TASK_TAGS)


def section_tags(entry: dict[str, Any]) -> list[str]:
    """A compiled section's §13 tags, sorted deterministically.

    Tags are the document role, the §8 IR category, the
    role's own fallback category (the category its document
    exists for, when the heading classifies elsewhere —
    a tool_policy section headed "Git Policy" is tools
    material even though "policy" classifies it as
    behavioral rules), and the heading / section-id tokens
    — all signals this layer already computes; nothing is
    authored or stored.
    """
    tags = {entry["role"], classify_section(entry["role"], entry["heading"])}
    fallback = _ROLE_FALLBACK.get(entry["role"])
    if fallback is not None:
        tags.add(fallback)
    tags |= _tokens(entry["heading"])
    tags |= _tokens(entry["section_id"])
    return sorted(tags)


def hybrid_components() -> list[dict[str, Any]]:
    """The §13 retrieval components and their honest status."""
    return [
        {"name": "semantic_similarity", "available": False,
         "reason": "no embedding surface is owned by this plugin"},
        {"name": "keyword_matching", "available": True, "reason": ""},
        {"name": "document_role", "available": True, "reason": ""},
        {"name": "section_tags", "available": True, "reason": ""},
        {"name": "task_classification", "available": True, "reason": ""},
        {"name": "priority", "available": True, "reason": ""},
    ]


def retrieval_score(entry: dict[str, Any], query: str = "",
                    task_tags_: list[str] | None = None) -> dict[str, Any]:
    """The explainable §13 score for one section.

    Pure function. Components are each in [0, 1] except
    ``semantic``, which is None (unavailable, never faked).
    The total is the fixed weighted sum: keyword 0.35,
    heading 0.10, task 0.25, role 0.10, priority 0.20.
    """
    query_tokens = _tokens(query or "")
    heading_tokens = _tokens(entry["heading"])
    text_tokens = _tokens(entry["text"])
    if query_tokens:
        keyword = len(query_tokens & (heading_tokens | text_tokens)) \
            / len(query_tokens)
        heading_match = len(query_tokens & heading_tokens) / len(query_tokens)
    else:
        keyword = 0.0
        heading_match = 0.0
    tags = set(section_tags(entry))
    task_match = 0.0
    role_match = 0.0
    wanted = [t for t in (task_tags_ or []) if t in _TASK_SECTION_KEYWORDS]
    if wanted:
        task_match = max(
            len(_TASK_SECTION_KEYWORDS[t] & tags)
            / len(_TASK_SECTION_KEYWORDS[t]) for t in wanted)
        affinity: set[str] = set()
        for tag in wanted:
            affinity |= _TASK_ROLE_AFFINITY[tag]
        role_match = 1.0 if entry["role"] in affinity else 0.0
    priority = float(entry.get("priority", 0.40))
    total = (0.35 * keyword + 0.10 * heading_match + 0.25 * task_match
             + 0.10 * role_match + 0.20 * priority)
    return {
        "total": round(total, 6),
        "keyword": round(keyword, 6),
        "heading": round(heading_match, 6),
        "task": round(task_match, 6),
        "role": round(role_match, 6),
        "priority": priority,
        "semantic": None,
    }


def retrieve_sections(index: list[dict[str, Any]], query: str = "",
                      task_text: str | None = None,
                      limit: int = RETRIEVAL_DEFAULT_LIMIT
                      ) -> list[dict[str, Any]]:
    """Rank compiled sections for a query/task (§13).

    Deterministic: sorted by descending score, ties broken
    by stable id. Sections scoring zero are excluded, and a
    query with no tokens and no task signal retrieves
    nothing. Each result names its §12 stable id, carries
    its verbatim text (§7), its tags, and the full score
    breakdown — retrieval stays explainable.
    """
    tags_wanted = classify_task(task_text if task_text is not None else query)
    if not _tokens(query or "") and not tags_wanted:
        return []
    try:
        bounded = int(limit)
    except (TypeError, ValueError):
        bounded = RETRIEVAL_DEFAULT_LIMIT
    bounded = max(1, min(RETRIEVAL_MAX_LIMIT, bounded))
    results = []
    for entry in index:
        score = retrieval_score(entry, query=query, task_tags_=tags_wanted)
        if score["total"] <= 0.0:
            continue
        # A section must connect to the request: a bare
        # priority/role float with no keyword, heading, or
        # task contact is not a retrieval result.
        if not (score["keyword"] or score["heading"] or score["task"]):
            continue
        results.append({
            "stable_id": entry.get(
                "stable_id",
                stable_section_id(entry["role"], entry["section_id"])),
            "role": entry["role"],
            "section_id": entry["section_id"],
            "heading": entry["heading"],
            "priority": float(entry.get("priority", 0.40)),
            "task_tags": list(tags_wanted),
            "tags": section_tags(entry),
            "score": score,
            "text": entry["text"],
        })
    results.sort(key=lambda row: (-row["score"]["total"], row["stable_id"]))
    return results[:bounded]


# --- §14 persona router ---------------------------------------------
#
# The router decides which sections a task requires. It is a
# deterministic decision layer over §13 retrieval: per-tag
# coverage first (so a task's every facet names its sections),
# then the retrieval ranking as fill, under a hard cap.

ROUTER_DEFAULT_LIMIT = 8
ROUTER_MAX_LIMIT = 20
ROUTER_PER_TAG_LIMIT = 3

# The five §14 inputs, in canonical order.
ROUTER_INPUTS = (
    "user_message", "current_task", "active_project",
    "tool_intent", "conversation_state",
)

# Task labels for a derived route, in precedence order: the
# first tag present names the task when no explicit current
# task was supplied.
_TASK_LABELS = (
    ("coding", "code_generation"),
    ("git", "git_operations"),
    ("filesystem", "filesystem_operations"),
    ("external_mutation", "external_mutation"),
    ("memory", "memory_work"),
    ("relationship", "relationship_counsel"),
    ("communication", "communication"),
    ("research", "research"),
    ("planning", "planning"),
)


def router_inputs() -> list[str]:
    return list(ROUTER_INPUTS)


def route_task_label(current_task: str = "",
                     task_tags_: list[str] | None = None) -> str:
    """The §14 task label for a route. Pure function.

    An explicit current task wins, slugified (``code_generation``
    stays ``code_generation``); a placeholder (``general`` /
    ``task`` / empty) does not. Otherwise the first §13 tag in
    label precedence order names the task; no signal at all is
    ``general``.
    """
    slug = _slugify(current_task) if (current_task or "").strip() else ""
    if slug and slug not in ("general", "task", "none", "section"):
        return slug
    wanted = set(task_tags_ or [])
    for tag, label in _TASK_LABELS:
        if tag in wanted:
            return label
    return "general"


def _tag_contact(entry: dict[str, Any], tag: str) -> float:
    keywords = _TASK_SECTION_KEYWORDS.get(tag)
    if not keywords:
        return 0.0
    return len(keywords & set(section_tags(entry))) / len(keywords)


def route_sections(index: list[dict[str, Any]], user_message: str = "",
                   current_task: str = "", active_project: str = "",
                   tool_intent: str = "", conversation_state: str = "",
                   limit: int = ROUTER_DEFAULT_LIMIT
                   ) -> dict[str, Any]:
    """Decide the persona sections a task requires (§14).

    Pure deterministic function of the compiled index and the
    five §14 inputs. Selection is per-tag first — for each
    classified tag, the top ``ROUTER_PER_TAG_LIMIT`` sections
    in §13 score order whose tags contact that tag — then
    filled from the §13 retrieval ranking, capped at ``limit``
    (clamped 1–20) and ordered by descending score with
    stable-id tiebreaks. Empty signals route to ``general``
    with nothing required. The result names the task, the
    tags, which inputs were present (names only, never their
    text), and the required stable ids both as ``required``
    and in the §14 example's ``persona_context`` shape, with
    a per-section row carrying the tags that required it and
    its explainable §13 score. A row required by keyword
    retrieval alone (no tag contact) is marked
    ``via_retrieval`` rather than left reasonless.
    """
    raw = {
        "user_message": user_message, "current_task": current_task,
        "active_project": active_project, "tool_intent": tool_intent,
        "conversation_state": conversation_state,
    }
    present = [name for name in ROUTER_INPUTS
               if str(raw[name] or "").strip()]
    combined = "\n".join(str(raw[name]) for name in ROUTER_INPUTS
                         if name in present)
    tags_wanted = classify_task(combined)
    label = route_task_label(current_task, tags_wanted)
    base: dict[str, Any] = {
        "task": label,
        "task_tags": list(tags_wanted),
        "inputs_present": present,
        "required": [],
        "persona_context": [],
        "sections": [],
    }
    if not present or (not _tokens(combined) and not tags_wanted):
        return base
    try:
        bounded = int(limit)
    except (TypeError, ValueError):
        bounded = ROUTER_DEFAULT_LIMIT
    bounded = max(1, min(ROUTER_MAX_LIMIT, bounded))
    scores = {
        id(entry): retrieval_score(
            entry, query=combined, task_tags_=tags_wanted)
        for entry in index
    }

    def stable(entry: dict[str, Any]) -> str:
        return entry.get(
            "stable_id",
            stable_section_id(entry["role"], entry["section_id"]))

    selected: dict[str, dict[str, Any]] = {}

    def add(entry: dict[str, Any], reason_tags: list[str]) -> None:
        sid = stable(entry)
        row = selected.get(sid)
        if row is None:
            row = {
                "stable_id": sid, "role": entry["role"],
                "section_id": entry["section_id"],
                "heading": entry["heading"],
                "priority": float(entry.get("priority", 0.40)),
                "task_tags": [],
                "via_retrieval": False,
                "score": scores[id(entry)],
            }
            selected[sid] = row
        for tag in reason_tags:
            if tag not in row["task_tags"]:
                row["task_tags"].append(tag)

    for tag in tags_wanted:
        candidates = [
            entry for entry in index if _tag_contact(entry, tag) > 0.0]
        candidates.sort(
            key=lambda e: (-scores[id(e)]["total"], stable(e)))
        for entry in candidates[:ROUTER_PER_TAG_LIMIT]:
            add(entry, [tag])
    for row in retrieve_sections(
            index, query=combined, limit=ROUTER_MAX_LIMIT):
        entry = next(
            (e for e in index if stable(e) == row["stable_id"]), None)
        if entry is None or row["stable_id"] in selected:
            continue
        contact = [t for t in tags_wanted
                   if _tag_contact(entry, t) > 0.0]
        add(entry, contact)
        if not contact:
            # Required by keyword/heading retrieval contact,
            # not by any tag — say so, never leave the row
            # reasonless.
            selected[row["stable_id"]]["via_retrieval"] = True
    ordered = sorted(
        selected.values(),
        key=lambda r: (-r["score"]["total"], r["stable_id"]))
    ordered = ordered[:bounded]
    for row in ordered:
        row["task_tags"] = [
            t for t in tags_wanted if t in row["task_tags"]]
    ids = [row["stable_id"] for row in ordered]
    base["required"] = ids
    base["persona_context"] = list(ids)
    base["sections"] = ordered
    return base


# --- §15 token budgeter ---------------------------------------------
#
# A pure budgeting layer over the §13 retrieval / §14 router
# outputs plus caller-supplied memory and project-state items.
# It decides what fits; it assembles and injects nothing.

BUDGET_CATEGORIES = (
    "persona_kernel", "persona_retrieval", "relevant_memories",
    "project_state",
)

# The §15 suggested budgets, as (minimum, maximum) estimated
# tokens per category.
SUGGESTED_BUDGETS = {
    "persona_kernel": (500, 1500),
    "persona_retrieval": (300, 2500),
    "relevant_memories": (500, 3000),
    "project_state": (500, 3000),
}

# Model context classes: small local models receive much
# less (each category's minimum), standard models the
# suggested maximum, large-context models more (twice the
# suggested maximum).
CONTEXT_CLASSES = ("small_local", "standard", "large")


def budget_categories() -> list[str]:
    return list(BUDGET_CATEGORIES)


def context_classes() -> list[str]:
    return list(CONTEXT_CLASSES)


def suggested_budgets() -> dict[str, dict[str, int]]:
    return {
        category: {"min": low, "max": high}
        for category, (low, high) in SUGGESTED_BUDGETS.items()
    }


def budget_allocations(context_class: str = "standard",
                       overrides: dict[str, Any] | None = None
                       ) -> dict[str, int]:
    """The per-category allocations for a context class (§15).

    Pure function. ``overrides`` replaces individual category
    allocations (configurability); unknown categories,
    negative or non-integer allocations, and unknown context
    classes are refused.
    """
    if context_class not in CONTEXT_CLASSES:
        raise PersonaRuntimeError(
            f"unknown budget context class: {context_class!r}")
    allocations: dict[str, int] = {}
    for category, (low, high) in SUGGESTED_BUDGETS.items():
        if context_class == "small_local":
            allocations[category] = low
        elif context_class == "large":
            allocations[category] = 2 * high
        else:
            allocations[category] = high
    for category, value in (overrides or {}).items():
        if category not in SUGGESTED_BUDGETS:
            raise PersonaRuntimeError(
                f"unknown budget category: {category!r}")
        if isinstance(value, bool) or not isinstance(value, int) \
                or value < 0:
            raise PersonaRuntimeError(
                f"budget allocation for {category} is invalid")
        allocations[category] = value
    return allocations


def _budget_item(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise PersonaRuntimeError("budget item must be a mapping")
    item_id = raw.get("id")
    category = raw.get("category")
    if not isinstance(item_id, str) or not item_id.strip():
        raise PersonaRuntimeError("budget item id is invalid")
    if category not in SUGGESTED_BUDGETS:
        raise PersonaRuntimeError(
            f"budget item category is invalid: {category!r}")
    tokens = raw.get("estimated_tokens")
    if tokens is None and isinstance(raw.get("text"), str):
        tokens = _estimate_tokens(raw["text"])
    if isinstance(tokens, bool) or not isinstance(tokens, int) \
            or tokens < 0:
        raise PersonaRuntimeError("budget item tokens are invalid")
    priority = raw.get("priority", 0.40)
    score = raw.get("score", 0.0)
    for value in (priority, score):
        if isinstance(value, bool) \
                or not isinstance(value, (int, float)) \
                or not 0.0 <= float(value) <= 1.0:
            raise PersonaRuntimeError("budget item priority/score invalid")
    level = raw.get("priority_level")
    if level is not None and level not in _PRIORITY_LEVEL_SCORES:
        raise PersonaRuntimeError(
            f"budget item priority level is invalid: {level!r}")
    return {
        "id": item_id.strip(), "category": category,
        "estimated_tokens": tokens,
        "priority": float(priority), "score": float(score),
        "priority_level": level,
    }


def budget_items(items: list[dict[str, Any]],
                 context_class: str = "standard",
                 budgets: dict[str, Any] | None = None
                 ) -> dict[str, Any]:
    """Trim candidate items to the §15 budgets. Pure function.

    Items are considered per category in priority order
    (descending derived priority, then descending score,
    then id). Whole items only: an item that does not fit
    the category's remaining allocation is excluded with
    reason ``over_budget`` and a later smaller item may
    still fit; no item is ever cut. Categories spend only
    their own allocation. Deterministic for identical input.

    §16 exception: a P0 item in the persona-kernel category
    is never excluded merely to save tokens — it is included
    even past the allocation, and the category's remaining
    count may go negative rather than evict P0 material.
    """
    allocations = budget_allocations(context_class, budgets)
    normalised = [_budget_item(raw) for raw in (items or [])]
    seen: set[tuple[str, str]] = set()
    for row in normalised:
        key = (row["category"], row["id"])
        if key in seen:
            raise PersonaRuntimeError(
                f"duplicate budget item: {row['category']}/{row['id']}")
        seen.add(key)
    categories: dict[str, Any] = {}
    included: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for category in BUDGET_CATEGORIES:
        rows = [r for r in normalised if r["category"] == category]
        rows.sort(key=lambda r: (-r["priority"], -r["score"], r["id"]))
        remaining = allocations[category]
        kept: list[str] = []
        dropped: list[str] = []
        for row in rows:
            p0_kernel = category == "persona_kernel" \
                and row.get("priority_level") == "P0"
            if row["estimated_tokens"] <= remaining or p0_kernel:
                remaining -= row["estimated_tokens"]
                kept.append(row["id"])
                included.append(row)
            else:
                dropped.append(row["id"])
                excluded.append({**row, "reason": "over_budget"})
        categories[category] = {
            "allocation": allocations[category],
            "used": allocations[category] - remaining,
            "remaining": remaining,
            "included": kept, "excluded": dropped,
        }
    return {
        "context_class": context_class,
        "allocations": allocations,
        "categories": categories,
        "included": included,
        "excluded": excluded,
        "total_allocation": sum(allocations.values()),
        "total_used": sum(c["used"] for c in categories.values()),
    }


# The §19 hash record's fields, in stored order.
HASH_RECORD_FIELDS = (
    "persona_id", "persona_version", "document_hashes",
    "kernel_hash", "persona_hash", "compiled_at",
)

# The §20 reload chain's steps, in roadmap order. A plan
# names only the steps the hashes actually require.
RELOAD_STEPS = (
    "detect_hash_change", "reparse_changed_documents",
    "update_persona_ir", "rebuild_retrieval_index",
    "recompile_kernel",
)


def reload_steps() -> list[str]:
    return list(RELOAD_STEPS)


def _validate_compiled_at(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PersonaRuntimeError("compiled_at is invalid")
    try:
        parsed = datetime.fromisoformat(value.strip())
    except ValueError as exc:
        raise PersonaRuntimeError("compiled_at is invalid") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise PersonaRuntimeError(
            "compiled_at must be timezone-aware")
    return value.strip()


def hash_record(compiled: dict[str, Any],
                compiled_at: str | None = None) -> dict[str, Any]:
    """The §19 stored hash record for one compiled artefact.

    Pure and deterministic for a given artefact: persona
    version (the config format version — per-persona
    versioning is §22), the per-document sha256 hashes by
    role in document order, the kernel hash, and the
    combined persona hash. ``compiled_at`` stays None
    unless a caller explicitly stamps a timezone-aware
    ISO timestamp; no clock is read here, so a compile
    remains deterministic (§6).
    """
    if not isinstance(compiled, dict):
        raise PersonaRuntimeError("compiled persona is invalid")
    persona_id = compiled.get("persona_id")
    documents = compiled.get("documents")
    kernel = compiled.get("kernel")
    persona_hash = compiled.get("persona_hash")
    if not isinstance(persona_id, str) or not persona_id \
            or not isinstance(documents, list) \
            or not isinstance(kernel, dict) \
            or not isinstance(kernel.get("sha256"), str) \
            or not isinstance(persona_hash, str):
        raise PersonaRuntimeError("compiled persona is invalid")
    document_hashes: dict[str, str] = {}
    for document in documents:
        if not isinstance(document, dict) \
                or not isinstance(document.get("role"), str) \
                or not isinstance(document.get("sha256"), str):
            raise PersonaRuntimeError("compiled persona is invalid")
        document_hashes[document["role"]] = document["sha256"]
    return {
        "persona_id": persona_id,
        "persona_version": PERSONA_CONFIG_VERSION,
        "document_hashes": document_hashes,
        "kernel_hash": kernel["sha256"],
        "persona_hash": persona_hash,
        "compiled_at": None if compiled_at is None
        else _validate_compiled_at(compiled_at),
    }


def _validate_hash_record(record: Any) -> dict[str, Any]:
    if not isinstance(record, dict) \
            or set(record) != set(HASH_RECORD_FIELDS):
        raise PersonaRuntimeError("persona hash record is invalid")
    if not isinstance(record["persona_id"], str) \
            or not record["persona_id"] \
            or record["persona_version"] != PERSONA_CONFIG_VERSION \
            or not isinstance(record["document_hashes"], dict) \
            or not record["document_hashes"] \
            or not all(
                isinstance(role, str) and isinstance(digest, str)
                for role, digest in record["document_hashes"].items()) \
            or not isinstance(record["kernel_hash"], str) \
            or not isinstance(record["persona_hash"], str):
        raise PersonaRuntimeError("persona hash record is invalid")
    if record["compiled_at"] is not None:
        _validate_compiled_at(record["compiled_at"])
    return record


def detect_changes(previous: dict[str, Any],
                   current: dict[str, Any]) -> dict[str, Any]:
    """Compare two §19 hash records; name exactly what changed.

    Pure. Records for different personas are not
    comparable and are refused. ``compiled_at`` never
    counts as a change — it is a caller stamp, not
    persona material.
    """
    previous = _validate_hash_record(previous)
    current = _validate_hash_record(current)
    if previous["persona_id"] != current["persona_id"]:
        raise PersonaRuntimeError(
            "hash records name different personas")
    before = previous["document_hashes"]
    after = current["document_hashes"]
    added = [role for role in after if role not in before]
    removed = [role for role in before if role not in after]
    changed = [
        role for role in after
        if role in before and before[role] != after[role]]
    kernel_changed = previous["kernel_hash"] != current["kernel_hash"]
    persona_changed = previous["persona_hash"] != current["persona_hash"]
    return {
        "changed": bool(
            added or removed or changed
            or kernel_changed or persona_changed),
        "persona_changed": persona_changed,
        "kernel_changed": kernel_changed,
        "documents_added": added,
        "documents_removed": removed,
        "documents_changed": changed,
        "documents_unchanged": sum(
            1 for role in after
            if role in before and before[role] == after[role]),
    }


def reload_plan(previous: dict[str, Any] | None,
                current: dict[str, Any] | None) -> dict[str, Any]:
    """The §20 reload chain for two compiled artefacts.

    Pure. Either side may be None (no persona compiled):
    a first compile walks the full chain, a removed
    persona only detects the change, and two absent
    personas change nothing. The kernel step stands only
    when the kernel hash itself changed, so an edit to a
    non-kernel section reparses and rebuilds the IR and
    index without recompiling the kernel. No step here
    requires a restart.
    """
    if previous is None and current is None:
        return {
            "changed": False, "steps": [],
            "documents_reparsed": [], "documents_removed": [],
            "ir_updated": False, "index_rebuilt": False,
            "kernel_recompile_required": False,
            "kernel_changed": False, "persona_changed": False,
            "restart_required": False,
        }
    if previous is None:
        record = hash_record(current)  # type: ignore[arg-type]
        return {
            "changed": True, "steps": list(RELOAD_STEPS),
            "documents_reparsed": list(record["document_hashes"]),
            "documents_removed": [],
            "ir_updated": True, "index_rebuilt": True,
            "kernel_recompile_required": True,
            "kernel_changed": True, "persona_changed": True,
            "restart_required": False,
        }
    if current is None:
        record = hash_record(previous)
        return {
            "changed": True, "steps": ["detect_hash_change"],
            "documents_reparsed": [],
            "documents_removed": list(record["document_hashes"]),
            "ir_updated": False, "index_rebuilt": False,
            "kernel_recompile_required": False,
            "kernel_changed": True, "persona_changed": True,
            "restart_required": False,
        }
    diff = detect_changes(hash_record(previous), hash_record(current))
    documents_touched = bool(
        diff["documents_added"] or diff["documents_removed"]
        or diff["documents_changed"])
    steps: list[str] = []
    if diff["changed"]:
        steps.append("detect_hash_change")
        if documents_touched:
            steps.extend([
                "reparse_changed_documents", "update_persona_ir",
                "rebuild_retrieval_index"])
        if diff["kernel_changed"]:
            steps.append("recompile_kernel")
    return {
        "changed": diff["changed"],
        "steps": steps,
        "documents_reparsed":
            diff["documents_added"] + diff["documents_changed"],
        "documents_removed": diff["documents_removed"],
        "ir_updated": documents_touched,
        "index_rebuilt": documents_touched,
        "kernel_recompile_required": diff["kernel_changed"],
        "kernel_changed": diff["kernel_changed"],
        "persona_changed": diff["persona_changed"],
        "restart_required": False,
    }


# The §21 impact classes, in ascending severity. Each class
# is also the §22 bump it suggests (none suggests no bump).
IMPACT_CLASSES = ("none", "patch", "minor", "major")
_IMPACT_RANK = {name: rank for rank, name in enumerate(IMPACT_CLASSES)}
# §8 categories whose change is a meaningful behavior
# extension (§22 MINOR) even outside the kernel.
_MINOR_CATEGORIES = frozenset({
    "behavioral_rules", "boundaries", "values", "motivations",
})
# §8 categories where a *new* section is a §22 MINOR (a new
# preference or a meaningful extension of the surface).
_MINOR_ADDED_CATEGORIES = frozenset({
    "preferences", "projects", "tools", "memory", "communication",
})

# The §22 version record's fields, in the roadmap's order.
VERSION_RECORD_FIELDS = (
    "persona_id", "persona_version", "compiled_at", "source_hash",
)


def impact_classes() -> list[str]:
    return list(IMPACT_CLASSES)


def parse_persona_version(value: Any) -> tuple[int, int, int]:
    """Parse a strict §22 semver string into its three parts."""
    if not isinstance(value, str):
        raise PersonaRuntimeError("persona version is invalid")
    match = _SEMVER.match(value)
    if not match:
        raise PersonaRuntimeError("persona version is invalid")
    return (int(match.group(1)), int(match.group(2)),
            int(match.group(3)))


def _compiled_version(compiled: dict[str, Any]) -> str:
    version = compiled.get("persona_version",
                           DEFAULT_PERSONA_VERSION)
    parse_persona_version(version)
    return version  # type: ignore[return-value]


def suggested_next_version(version: Any, impact_class: Any) -> str:
    """The §22 version after ``version`` for one impact class.

    Pure. MAJOR bumps identity / relationship architecture,
    MINOR new preferences or meaningful behavior extension,
    PATCH wording / formatting / minor clarification, and
    ``none`` leaves the version unchanged. This is a
    suggestion for the human to confirm by editing the
    config — nothing here writes a version anywhere.
    """
    major, minor, patch = parse_persona_version(version)
    if impact_class not in _IMPACT_RANK:
        raise PersonaRuntimeError("impact class is invalid")
    if impact_class == "major":
        return f"{major + 1}.0.0"
    if impact_class == "minor":
        return f"{major}.{minor + 1}.0"
    if impact_class == "patch":
        return f"{major}.{minor}.{patch + 1}"
    return f"{major}.{minor}.{patch}"


def version_record(compiled: dict[str, Any],
                   compiled_at: str | None = None) -> dict[str, Any]:
    """The §22 version record for one compiled artefact.

    Pure: persona id, the human-authored per-persona semver
    the compile carries (defaulting to ``0.1.0`` for an
    artefact compiled before §22 stood), an explicit
    caller stamp or None, and the source hash — the
    artefact's combined persona hash (§19). No clock is
    read here, so a compile stays deterministic (§6).
    """
    record = hash_record(compiled)
    return {
        "persona_id": record["persona_id"],
        "persona_version": _compiled_version(compiled),
        "compiled_at": None if compiled_at is None
        else _validate_compiled_at(compiled_at),
        "source_hash": record["persona_hash"],
    }


def _impact_index(compiled: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """One compile's sections by stable id, for §21 diffing."""
    index = compiled.get("index")
    kernel = compiled.get("kernel")
    if not isinstance(index, list) or not isinstance(kernel, dict) \
            or not isinstance(kernel.get("stable_ids"), list):
        raise PersonaRuntimeError("compiled persona is invalid")
    kernel_ids = set(kernel["stable_ids"])
    by_id: dict[str, dict[str, Any]] = {}
    for entry in index:
        if not isinstance(entry, dict) \
                or not isinstance(entry.get("stable_id"), str) \
                or not isinstance(entry.get("role"), str) \
                or not isinstance(entry.get("heading"), str) \
                or not isinstance(entry.get("text"), str) \
                or entry.get("priority_level") \
                not in _PRIORITY_LEVEL_SCORES:
            raise PersonaRuntimeError("compiled persona is invalid")
        by_id[entry["stable_id"]] = {
            "stable_id": entry["stable_id"],
            "role": entry["role"],
            "heading": entry["heading"],
            "level": entry.get("level"),
            "text": entry["text"],
            "category": classify_section(
                entry["role"], entry["heading"]),
            "priority_level": entry["priority_level"],
            "in_kernel": entry["stable_id"] in kernel_ids,
        }
    return by_id


def _section_changed(before: dict[str, Any],
                     after: dict[str, Any]) -> bool:
    return any(before[key] != after[key] for key in (
        "text", "heading", "level", "category", "priority_level"))


def _section_impact(action: str, section: dict[str, Any]) -> str:
    """The §21 impact class of one section-level change. Pure."""
    if section["in_kernel"] \
            and section["role"] in ("core", "relationship"):
        return "major"
    if section["category"] in ("identity", "relationship") \
            and section["priority_level"] in ("P0", "P1"):
        return "major"
    if section["in_kernel"]:
        return "minor"
    if section["category"] in _MINOR_CATEGORIES:
        return "minor"
    if section["priority_level"] in ("P0", "P1"):
        return "minor"
    if action == "added" \
            and section["category"] in _MINOR_ADDED_CATEGORIES:
        return "minor"
    return "patch"


def change_impact(previous: dict[str, Any],
                  current: dict[str, Any]) -> dict[str, Any]:
    """Classify the §21 semantic impact between two compiles.

    Pure. The two artefacts are compared at section level
    (§12 stable ids): sections added, removed, or changed
    (text, semantic heading, heading level, §8 category, or
    §16 priority level), each classified by the pure
    ``_section_impact`` rules over its role, category,
    priority level, and kernel membership. The overall
    class is the most severe section class; a change to
    the §17/§18 anchors — authored identity material at
    the head of every kernel — is major; a document-hash
    change with no section or anchor change (a renumber,
    a formatting edit) is a patch. Kernel rebuild is
    reported separately: it is required exactly when the
    §19 kernel hash changed, so an avatar embodiment edit
    is a patch with no kernel rebuild while a core
    relationship-authority edit is major with one.
    Artefacts naming different personas are refused (via
    the §19 records), as are malformed artefacts. The
    §22 suggestion is computed from the *previous*
    artefact's version; the human confirms any bump by
    editing the config.
    """
    diff = detect_changes(
        hash_record(previous), hash_record(current))
    previous_version = _compiled_version(previous)
    current_version = _compiled_version(current)
    before = _impact_index(previous)
    after = _impact_index(current)
    added = [sid for sid in after if sid not in before]
    removed = [sid for sid in before if sid not in after]
    changed = [
        sid for sid in after
        if sid in before and _section_changed(before[sid], after[sid])]
    details: list[dict[str, Any]] = []
    for action, ids, source in (
            ("added", added, after),
            ("changed", changed, after),
            ("removed", removed, before)):
        for sid in ids:
            section = source[sid]
            details.append({
                "stable_id": sid,
                "action": action,
                "role": section["role"],
                "category": section["category"],
                "priority_level": section["priority_level"],
                "in_kernel": section["in_kernel"],
                "impact": _section_impact(action, section),
            })
    anchors_changed = (
        list(previous.get("anchors") or [])
        != list(current.get("anchors") or [])
        or list(previous.get("anti_anchors") or [])
        != list(current.get("anti_anchors") or []))
    impact = "none"
    for detail in details:
        if _IMPACT_RANK[detail["impact"]] > _IMPACT_RANK[impact]:
            impact = detail["impact"]
    if anchors_changed and _IMPACT_RANK[impact] < _IMPACT_RANK["major"]:
        impact = "major"
    if impact == "none" and diff["changed"]:
        impact = "patch"
    return {
        "changed": diff["changed"],
        "impact_class": impact,
        "kernel_rebuild_required": diff["kernel_changed"],
        "kernel_changed": diff["kernel_changed"],
        "persona_changed": diff["persona_changed"],
        "documents_added": diff["documents_added"],
        "documents_removed": diff["documents_removed"],
        "documents_changed": diff["documents_changed"],
        "sections_added": added,
        "sections_removed": removed,
        "sections_changed": changed,
        "details": details,
        "anchors_changed": anchors_changed,
        "previous_version": previous_version,
        "current_version": current_version,
        "suggested_bump": impact,
        "suggested_next_version": suggested_next_version(
            previous_version, impact),
    }


# --- §23 drift defenses + §24 precedence ------------------------------
#
# Pure contract data and functions. Nothing here reads,
# watches, or scores a conversation: §23 names the dangers
# and the defenses this system stands against them, and
# §24 names what conversation-class sources may and may
# not do. Defenses grounded in a mechanism this layer
# already carries are labelled "mechanism"; defenses that
# stand as contract rules (a caller / prompt-assembly
# obligation, not code in this layer) are labelled "rule",
# honestly, rather than claiming runtime behaviour that
# does not exist.

# The seven §23 drift dangers, as stable slugs, in
# roadmap order.
DRIFT_DANGERS = (
    "recent_message_dominance",
    "summary_mutation",
    "context_truncation",
    "assistant_self_imitation",
    "memory_contamination",
    "user_mood_overfitting",
    "temporary_roleplay_overriding_identity",
)

_DRIFT_DEFENSES = (
    {
        "danger": "recent_message_dominance",
        "defense": "kernel_pinning",
        "kind": "mechanism",
        "grounding": "§10 pinning + §24 precedence",
        "description": (
            "The compiled artefact carries the §10 pinning "
            "spec: the persona kernel stands ahead of active "
            "context and the user message in the designated "
            "prompt order and is never buried in retrieved "
            "memory, so recent messages cannot outrank "
            "canonical persona material by position. Actual "
            "placement is prompt assembly (§53, later), as "
            "§10 already records."),
    },
    {
        "danger": "summary_mutation",
        "defense": "verbatim_only_no_blind_summary",
        "kind": "mechanism",
        "grounding": "§7 verbatim rule + §19 hash + §20 reload",
        "description": (
            "The kernel, the index, and the IR carry section "
            "text verbatim (§7) and this layer produces no "
            "generated summary or paraphrase, so no summary "
            "can become a persona source here. A persona "
            "change is visible only as a canonical-document "
            "edit, detected by the §19 hashes and the §20 "
            "reload check."),
    },
    {
        "danger": "context_truncation",
        "defense": "never_evict_kernel_or_p0",
        "kind": "mechanism",
        "grounding": "§15 budgeter + §16 priority + §§17/18 anchors",
        "description": (
            "Budgeting trims whole items only (§15), P0 "
            "material is never excluded merely to save "
            "tokens, kernel generation never evicts a P0 "
            "section to fit the §5 band, and the §§17/18 "
            "anchor block is never evicted (§16). Truncation "
            "may drop lower-priority context; it never "
            "evicts foundational persona material in this "
            "layer."),
    },
    {
        "danger": "assistant_self_imitation",
        "defense": "canonical_documents_are_the_only_persona_source",
        "kind": "rule",
        "grounding": "§§3/6 compiler + §24 precedence",
        "description": (
            "The compiler compiles human-authored canonical "
            "documents only, deterministically (§§3/6). "
            "Assistant output is not a document role, is "
            "never compiled, retrieved, or hashed as persona "
            "material, and ranks as conversation at most "
            "(§24). A self-description persists only when a "
            "human writes it into a canonical document."),
    },
    {
        "danger": "memory_contamination",
        "defense": "memory_ranks_below_canonical_persona",
        "kind": "rule",
        "grounding": "§24 precedence + §67 canonical priority",
        "description": (
            "Long-term memory is tier 4 of the §24 order, "
            "below persona core, the relationship model, "
            "and the service bible — the same relative "
            "authority §67 records for canonical files. "
            "Retrieval (§13) ranks sections of the canonical "
            "documents; a memory that conflicts with "
            "canonical persona material loses, and no memory "
            "may redefine foundational personality."),
    },
    {
        "danger": "user_mood_overfitting",
        "defense": "conversation_affects_state_not_character",
        "kind": "rule",
        "grounding": "§24",
        "description": (
            "Current conversation (tier 5) and temporary "
            "emotional state (tier 6, the lowest tier) may "
            "affect current mood, immediate context, and "
            "recent events only. They must never redefine "
            "foundational personality, identity, or traits "
            "(§24), however strong or repeated the mood in "
            "the conversation is."),
    },
    {
        "danger": "temporary_roleplay_overriding_identity",
        "defense": "anchors_plus_lowest_tier_for_temporary_state",
        "kind": "mechanism_and_rule",
        "grounding": "§§17/18 anchors + §24 precedence",
        "description": (
            "Authored anchors and anti-anchors stand "
            "verbatim at the head of every kernel for drift "
            "resistance (§§17/18), and temporary emotional "
            "state — roleplay included — is the lowest §24 "
            "tier, below even current conversation. A "
            "temporary role ends with its context; it never "
            "rewrites the kernel, the anchors, or any "
            "canonical document."),
    },
)


def drift_dangers() -> list[str]:
    return list(DRIFT_DANGERS)


def drift_defenses() -> list[dict[str, str]]:
    """The §23 defenses, one row per danger, in roadmap order.

    Pure contract data: each row names the danger (a stable
    slug), the defense's name, its kind (``mechanism`` where
    a surface this layer already carries does the work,
    ``rule`` where the defense stands as a contract rule
    rather than code here, ``mechanism_and_rule`` where
    both), the banked surface it is grounded in, and a
    description of the defense. No conversation is read or
    monitored by this function.
    """
    return [dict(row) for row in _DRIFT_DEFENSES]


# The six §24 precedence tiers, in roadmap order (highest
# authority first), with the roadmap's canonical names and
# the compiler's semantic document role for the three
# document tiers. The remaining tiers are non-document
# sources and carry no role.
PRECEDENCE_TIERS = (
    "persona_core",
    "relationship_model",
    "service_bible",
    "long_term_memory",
    "current_conversation",
    "temporary_emotional_state",
)
_PRECEDENCE_ROWS = (
    ("persona_core", "PERSONA CORE", "core"),
    ("relationship_model", "RELATIONSHIP MODEL", "relationship"),
    ("service_bible", "SERVICE BIBLE", "service_bible"),
    ("long_term_memory", "long-term memory", None),
    ("current_conversation", "current conversation", None),
    ("temporary_emotional_state", "temporary emotional state", None),
)
_PRECEDENCE_RANK = {
    tier: rank for rank, tier in enumerate(PRECEDENCE_TIERS)}
_PRECEDENCE_ROLES = {
    tier: role for tier, _name, role in _PRECEDENCE_ROWS}
_CANONICAL_TIERS = frozenset({
    "persona_core", "relationship_model", "service_bible"})

# What conversation-class influence may affect (§24), and
# what it must never redefine, as stable slugs.
HISTORY_MAY_AFFECT = (
    "current_mood", "immediate_context", "recent_events")
HISTORY_MUST_NOT_REDEFINE = (
    "foundational_personality", "identity", "traits")

# Claimed-source aliases, keyed by slugified input. A
# conversation summary inherits the conversation tier: it
# is derived from history, so it can never outrank the
# history it summarises (§23 summary mutation). Assistant
# output likewise ranks as conversation at most.
_SOURCE_ALIASES = {
    "core": "persona_core",
    "persona_core": "persona_core",
    "persona": "persona_core",
    "relationship": "relationship_model",
    "relationship_model": "relationship_model",
    "service_bible": "service_bible",
    "service": "service_bible",
    "long_term_memory": "long_term_memory",
    "memory": "long_term_memory",
    "memories": "long_term_memory",
    "current_conversation": "current_conversation",
    "conversation": "current_conversation",
    "conversation_history": "current_conversation",
    "chat_history": "current_conversation",
    "history": "current_conversation",
    "summary": "current_conversation",
    "conversation_summary": "current_conversation",
    "assistant_output": "current_conversation",
    "assistant_self_imitation": "current_conversation",
    "temporary_emotional_state": "temporary_emotional_state",
    "temporary_state": "temporary_emotional_state",
    "emotional_state": "temporary_emotional_state",
    "temporary_roleplay": "temporary_emotional_state",
    "roleplay": "temporary_emotional_state",
}

# Influence-target aliases, keyed by slugified input.
_TARGET_ALIASES = {
    "current_mood": "current_mood",
    "mood": "current_mood",
    "immediate_context": "immediate_context",
    "context": "immediate_context",
    "recent_events": "recent_events",
    "recent_event": "recent_events",
    "foundational_personality": "foundational_personality",
    "personality": "foundational_personality",
    "character": "foundational_personality",
    "identity": "identity",
    "traits": "traits",
    "trait": "traits",
}


def precedence_tiers() -> list[str]:
    return list(PRECEDENCE_TIERS)


def precedence_order() -> list[dict[str, Any]]:
    """The §24 conceptual priority order, highest first.

    Pure. Each row names its tier (a stable slug), its rank
    (0 is highest), the roadmap's canonical name, the
    compiler's semantic document role for the three
    document tiers (``core`` / ``relationship`` /
    ``service_bible``; None for the non-document tiers),
    and whether the tier is a canonical document tier.
    Canonical persona always outranks conversational
    drift: every document tier outranks long-term memory,
    current conversation, and temporary emotional state.
    """
    return [{
        "tier": tier,
        "rank": rank,
        "name": name,
        "document_role": role,
        "canonical": tier in _CANONICAL_TIERS,
    } for rank, (tier, name, role) in enumerate(_PRECEDENCE_ROWS)]


def history_may_affect() -> list[str]:
    return list(HISTORY_MAY_AFFECT)


def history_must_not_redefine() -> list[str]:
    return list(HISTORY_MUST_NOT_REDEFINE)


def _precedence_tier(source: Any) -> str:
    if not isinstance(source, str) or not source.strip():
        raise PersonaRuntimeError("influence source is invalid")
    tier = _SOURCE_ALIASES.get(_slugify(source))
    if tier is None:
        raise PersonaRuntimeError(
            f"unknown influence source: {source!r}")
    return tier


def _influence_target(target: Any) -> str:
    if not isinstance(target, str) or not target.strip():
        raise PersonaRuntimeError("influence target is invalid")
    resolved = _TARGET_ALIASES.get(_slugify(target))
    if resolved is None:
        raise PersonaRuntimeError(
            f"unknown influence target: {target!r}")
    return resolved


def classify_influence(source: Any) -> dict[str, Any]:
    """Classify what one claimed source may do (§24). Pure.

    ``source`` is a claimed influence: a canonical document
    tier or role (``persona_core`` / ``core``,
    ``relationship_model`` / ``relationship``,
    ``service_bible``), or a non-document source
    (``long_term_memory`` / ``memory``,
    ``current_conversation`` / ``conversation_history`` /
    ``summary``, ``temporary_emotional_state`` /
    ``temporary_roleplay``); names are slugified, so the
    roadmap's own spellings (``PERSONA CORE``,
    ``long-term memory``) classify too. Unknown or
    malformed sources are refused.

    A canonical document tier is how foundational
    personality is authored, so it may redefine it (a
    human edit, classified by §21 and versioned by §22).
    Every non-document tier may affect current mood,
    immediate context, and recent events only, and must
    never redefine foundational personality, identity, or
    traits — however the conversation went.
    """
    tier = _precedence_tier(source)
    canonical = tier in _CANONICAL_TIERS
    return {
        "source": tier,
        "tier": tier,
        "rank": _PRECEDENCE_RANK[tier],
        "document_role": _PRECEDENCE_ROLES[tier],
        "canonical": canonical,
        "may_affect": list(HISTORY_MAY_AFFECT),
        "may_redefine": [] if not canonical
        else list(HISTORY_MUST_NOT_REDEFINE),
        "must_not_redefine": [] if canonical
        else list(HISTORY_MUST_NOT_REDEFINE),
        "may_redefine_foundational_personality": canonical,
    }


def influence_allowed(source: Any, target: Any) -> bool:
    """Whether ``source`` may affect ``target`` (§24). Pure.

    Targets are the §24 effects (``current_mood`` /
    ``mood``, ``immediate_context`` / ``context``,
    ``recent_events``) and the protected foundations
    (``foundational_personality`` / ``personality`` /
    ``character``, ``identity``, ``traits``). Every
    recognised source may affect the three effects; only
    a canonical document tier may touch the foundations.
    Unknown sources or targets are refused.
    """
    tier = _precedence_tier(source)
    resolved = _influence_target(target)
    if resolved in HISTORY_MAY_AFFECT:
        return True
    return tier in _CANONICAL_TIERS


def precedence_winner(first: Any, second: Any) -> str:
    """The higher §24 tier of two claimed sources. Pure.

    Returns the winning tier's stable slug; on a tie the
    shared tier wins (a source never loses to itself).
    Unknown or malformed sources are refused.
    """
    first_tier = _precedence_tier(first)
    second_tier = _precedence_tier(second)
    if _PRECEDENCE_RANK[first_tier] <= _PRECEDENCE_RANK[second_tier]:
        return first_tier
    return second_tier


def outranks(first: Any, second: Any) -> bool:
    """Whether ``first`` strictly outranks ``second`` (§24).

    Pure. Canonical persona outranks conversational drift:
    ``core`` outranks ``conversation_history``, and
    ``current_conversation`` outranks
    ``temporary_emotional_state``. A tier does not outrank
    itself. Unknown or malformed sources are refused.
    """
    return _PRECEDENCE_RANK[_precedence_tier(first)] \
        < _PRECEDENCE_RANK[_precedence_tier(second)]


# --- §25 summary claims + §26 trait vs state --------------------------
#
# Pure contract data and functions, like §§23/24. Nothing
# here builds, reads, or stores a summary, and nothing
# tracks a live state: §25 names what form a summary
# claim may take, and §26 names the trait/state
# separation and the deterministic decay rule for states.

# The three forms a claimed summary statement can take.
SUMMARY_CLAIM_FORMS = ("state", "trait", "unclassified")
MAX_SUMMARY_CLAIM_CHARS = 1000

# Trait-form markers (§25): wording that presents a
# quality as what the subject *is* — an enduring identity
# predication ("is a frustrated personality"), an
# always/inherent framing, or a trait noun. Trait markers
# win over state markers: a claim carrying both is
# refused as trait-form, fail-closed.
_TRAIT_PHRASES = (("is", "a"), ("is", "an"), ("by", "nature"))
_TRAIT_TOKENS = frozenset({
    "always", "disposition", "fundamentally", "inherently",
    "personality", "temperament", "trait", "traits",
})

# State-form markers (§25/§26): wording that bounds a
# quality in time — a past-tense or felt/seemed report, a
# temporal adverb, or an explicit current-moment framing
# ("was frustrated during debugging", "currently amused").
_STATE_PHRASES = (
    ("at", "the", "moment"), ("right", "now"))
_STATE_TOKENS = frozenset({
    "became", "currently", "during", "felt", "lately",
    "momentarily", "recently", "seemed", "temporarily",
    "today", "tonight", "was", "were", "while",
    "yesterday",
})

# The two §26 kinds, in roadmap order.
TRAIT_STATE_KINDS = ("trait", "state")

# The roadmap's own §26 examples, as stable slugs: traits
# authored in persona files, and temporary states.
EXAMPLE_TRAITS = (
    "warm", "devoted", "intelligent",
    "non_oppositional_counselor",
)
EXAMPLE_STATES = (
    "currently_amused",
    "currently_concerned_about_architecture",
)

# §26 decay convention (this layer's own deterministic
# convention — the roadmap says states decay but names no
# numbers): a state's strength halves every 24 hours and
# a state under 0.05 strength is expired. Traits never
# decay under any elapsed time.
STATE_HALF_LIFE_HOURS = 24.0
STATE_EXPIRY_THRESHOLD = 0.05


def summary_claim_forms() -> list[str]:
    return list(SUMMARY_CLAIM_FORMS)


def _claim_tokens(text: Any) -> list[str]:
    if not isinstance(text, str) or not text.strip():
        raise PersonaRuntimeError("summary claim is invalid")
    if len(text) > MAX_SUMMARY_CLAIM_CHARS:
        raise PersonaRuntimeError("summary claim exceeds its limit")
    return [tok for tok in _slugify(text).split("_") if tok]


def _has_phrase(tokens: list[str],
                phrases: tuple[tuple[str, ...], ...]) -> bool:
    return any(
        list(phrase) == tokens[i:i + len(phrase)]
        for phrase in phrases
        for i in range(len(tokens) - len(phrase) + 1))


def classify_summary_claim(text: Any) -> dict[str, Any]:
    """Classify one summary claim's form (§25). Pure.

    The claim is classified by explicit grammatical
    markers only — this layer does not interpret prose
    (§7). Trait-form markers (an "is a"/"is an" identity
    predication, "by nature", or an always / inherent /
    personality / temperament / disposition / trait
    token) win first; temporal state markers (was / were
    / felt / seemed / became, during / while, or a
    temporal adverb such as currently / today) make a
    state form; a claim with neither is ``unclassified``.

    A summary may record only a state-form claim ("was
    frustrated during debugging"); a trait-form claim
    ("is a frustrated personality") and an unclassified
    claim are both refused, fail-closed. No form may
    define persona or redefine traits — a summary
    inherits the §24 conversation tier.
    """
    tokens = _claim_tokens(text)
    token_set = set(tokens)
    if token_set & _TRAIT_TOKENS \
            or _has_phrase(tokens, _TRAIT_PHRASES):
        form = "trait"
        reason = "trait_form_refused"
    elif token_set & _STATE_TOKENS \
            or _has_phrase(tokens, _STATE_PHRASES):
        form = "state"
        reason = "state_record_allowed"
    else:
        form = "unclassified"
        reason = "unclassified_refused"
    return {
        "form": form,
        "summary_may_record": form == "state",
        "may_define_persona": False,
        "may_redefine_traits": False,
        "reason_code": reason,
    }


def summary_claim_allowed(text: Any) -> bool:
    """Whether a summary may record this claim (§25). Pure."""
    return classify_summary_claim(text)["summary_may_record"]


def trait_state_kinds() -> list[str]:
    return list(TRAIT_STATE_KINDS)


def trait_state_separation() -> list[dict[str, Any]]:
    """The §26 trait/state separation, in roadmap order.

    Pure contract data. Traits come from canonical
    persona files, are defined only by them, and never
    decay; states are temporary experience, may be
    reported by any source, and decay under the recorded
    convention (24-hour half-life, expired below 0.05).
    The examples are the roadmap's own §26 examples.
    Fresh copies are returned; mutating a row does not
    poison the contract.
    """
    return [
        {
            "kind": "trait",
            "source": "canonical_persona_files",
            "defined_by": ["canonical_persona_files"],
            "decays": False,
            "half_life_hours": None,
            "expiry_threshold": None,
            "examples": list(EXAMPLE_TRAITS),
        },
        {
            "kind": "state",
            "source": "current_experience",
            "defined_by": [],
            "decays": True,
            "half_life_hours": STATE_HALF_LIFE_HOURS,
            "expiry_threshold": STATE_EXPIRY_THRESHOLD,
            "examples": list(EXAMPLE_STATES),
        },
    ]


def classify_attribute(source: Any,
                       claimed_kind: Any = None) -> dict[str, Any]:
    """Classify an attribute by source and claim (§26). Pure.

    ``source`` is any §24 source (a canonical document
    tier or role, memory, conversation / summary, or a
    temporary state); ``claimed_kind`` is optionally
    ``trait`` or ``state``. Traits come from persona
    files: a canonical source defines a trait (or a
    state, when claimed as one). Every non-canonical
    source is at most a state — a trait claimed from
    conversation, a summary, memory, or a temporary
    state is returned as a state with the trait claim
    refused, never as a trait. Unknown sources or kinds
    are refused.
    """
    tier = _precedence_tier(source)
    canonical = tier in _CANONICAL_TIERS
    claimed = None
    if claimed_kind is not None:
        if not isinstance(claimed_kind, str) \
                or _slugify(claimed_kind) not in TRAIT_STATE_KINDS:
            raise PersonaRuntimeError(
                "attribute kind is invalid")
        claimed = _slugify(claimed_kind)
    if canonical:
        kind = claimed or "trait"
        trait_claim_allowed = True
    else:
        kind = "state"
        trait_claim_allowed = False
    return {
        "source": tier,
        "tier": tier,
        "canonical": canonical,
        "claimed_kind": claimed,
        "kind": kind,
        "trait_claim_allowed": trait_claim_allowed,
        "may_define_persona": canonical and kind == "trait",
        "decays": kind == "state",
    }


def _validate_strength(value: Any) -> float:
    if isinstance(value, bool) \
            or not isinstance(value, (int, float)) \
            or not math.isfinite(float(value)) \
            or not 0.0 <= float(value) <= 1.0:
        raise PersonaRuntimeError("strength is invalid")
    return float(value)


def _validate_elapsed(value: Any) -> float:
    if isinstance(value, bool) \
            or not isinstance(value, (int, float)) \
            or not math.isfinite(float(value)) \
            or float(value) < 0.0:
        raise PersonaRuntimeError("elapsed hours are invalid")
    return float(value)


def _validate_half_life(value: Any) -> float:
    if isinstance(value, bool) \
            or not isinstance(value, (int, float)) \
            or not math.isfinite(float(value)) \
            or float(value) <= 0.0:
        raise PersonaRuntimeError("half-life hours are invalid")
    return float(value)


def _decay_kind(kind: Any) -> str:
    if not isinstance(kind, str) \
            or _slugify(kind) not in TRAIT_STATE_KINDS:
        raise PersonaRuntimeError("attribute kind is invalid")
    return _slugify(kind)


def decayed_strength(kind: Any, strength: Any, elapsed_hours: Any,
                     half_life_hours: Any = STATE_HALF_LIFE_HOURS
                     ) -> float:
    """A trait/state strength after elapsed time (§26). Pure.

    Traits never decay: the strength is returned
    unchanged at any elapsed time. States decay under
    the recorded convention: the strength halves every
    ``half_life_hours`` (default 24). Invalid kinds,
    strengths outside the unit interval, negative or
    non-finite elapsed times, and non-positive
    half-lives are refused.
    """
    resolved = _decay_kind(kind)
    initial = _validate_strength(strength)
    elapsed = _validate_elapsed(elapsed_hours)
    half_life = _validate_half_life(half_life_hours)
    if resolved == "trait":
        return initial
    return initial * 0.5 ** (elapsed / half_life)


def state_decay(kind: Any, strength: Any, elapsed_hours: Any,
                half_life_hours: Any = STATE_HALF_LIFE_HOURS
                ) -> dict[str, Any]:
    """The §26 decay record for one attribute. Pure.

    Returns the kind, the initial and decayed strengths,
    the elapsed hours, the half-life in force (None for
    a trait, which has none), whether the kind decays,
    and whether the attribute is expired — a state whose
    decayed strength falls below the 0.05 threshold. A
    trait is never expired by time. An expired state
    never becomes a trait; it simply ends.
    """
    resolved = _decay_kind(kind)
    initial = _validate_strength(strength)
    elapsed = _validate_elapsed(elapsed_hours)
    half_life = _validate_half_life(half_life_hours)
    decayed = decayed_strength(
        resolved, initial, elapsed, half_life)
    return {
        "kind": resolved,
        "initial_strength": initial,
        "elapsed_hours": elapsed,
        "half_life_hours": None if resolved == "trait"
        else half_life,
        "strength": decayed,
        "decays": resolved == "state",
        "expired": resolved == "state"
        and decayed < STATE_EXPIRY_THRESHOLD,
    }


# --- §27 persona watchdog + §28 drift dimensions ---------------------
#
# Pure contract data and functions, like §§23–26. Nothing
# here generates a response, evaluates a live draft, or
# repairs anything: §27 names the watchdog pipeline and
# its routing, §28 names the dimensions a drift score is
# shaped over, and the deterministic score/threshold rule
# below states when a score record routes to repair. The
# §29 drift-score YAML and the §30 repair loop are later
# sections; the thresholds here are this layer's recorded
# convention (the roadmap says only significant drift
# should trigger repair and names no numbers).

# The ten §28 drift dimensions, in roadmap order.
DRIFT_DIMENSIONS = (
    "identity", "tone", "relationship", "decision_behavior",
    "counsel_style", "initiative", "truthfulness", "deference",
    "technical_competence", "boundaries",
)

# The §27 pipeline steps, in roadmap order.
WATCHDOG_PIPELINE = (
    "llm_draft", "persona_watchdog", "drift_score", "route",
)

# The two §27 routes: acceptable drafts go to output,
# drifted drafts go to repair.
WATCHDOG_ROUTES = ("output", "repair")

# §27/§28 threshold convention (this layer's own — see
# the header note): a total (the mean over all ten
# dimensions) at or above 0.20 is significant, and any
# single dimension at or above 0.25 is significant on
# its own, so one badly drifted dimension cannot hide
# inside a low mean.
DRIFT_TOTAL_THRESHOLD = 0.20
DRIFT_DIMENSION_THRESHOLD = 0.25


def drift_dimensions() -> list[str]:
    return list(DRIFT_DIMENSIONS)


def watchdog_pipeline() -> list[dict[str, Any]]:
    """The §27 watchdog pipeline, in roadmap order. Pure.

    The watchdog's purpose is not to generate responses;
    it evaluates them. An LLM draft enters, the watchdog
    evaluates it, a drift score is produced, and the
    score routes the draft: acceptable to output, drift
    to repair. Fresh copies are returned; mutating a row
    does not poison the contract.
    """
    return [
        {
            "step": "llm_draft",
            "kind": "generation",
            "generates_responses": True,
            "evaluates_drafts": False,
        },
        {
            "step": "persona_watchdog",
            "kind": "evaluation",
            "generates_responses": False,
            "evaluates_drafts": True,
        },
        {
            "step": "drift_score",
            "kind": "scoring",
            "generates_responses": False,
            "evaluates_drafts": False,
        },
        {
            "step": "route",
            "kind": "routing",
            "generates_responses": False,
            "evaluates_drafts": False,
            "routes": {
                "acceptable": "output",
                "drift": "repair",
            },
        },
    ]


def watchdog_contract() -> dict[str, Any]:
    """The §27 PersonaWatchdog contract. Pure.

    The watchdog generates nothing and evaluates drafts
    only; its output is a drift score over the §28
    dimensions plus the route that score decides.
    """
    return {
        "name": "PersonaWatchdog",
        "generates_responses": False,
        "evaluates_drafts": True,
        "input": "llm_draft",
        "output": "drift_score",
        "pipeline": list(WATCHDOG_PIPELINE),
        "dimensions": list(DRIFT_DIMENSIONS),
        "routes": list(WATCHDOG_ROUTES),
        "total_threshold": DRIFT_TOTAL_THRESHOLD,
        "dimension_threshold": DRIFT_DIMENSION_THRESHOLD,
    }


def _validate_drift_scores(scores: Any) -> dict[str, float]:
    if not isinstance(scores, dict):
        raise PersonaRuntimeError("drift scores are invalid")
    validated: dict[str, float] = {}
    for key, value in scores.items():
        if not isinstance(key, str) \
                or _slugify(key) not in DRIFT_DIMENSIONS:
            raise PersonaRuntimeError(
                "drift dimension is invalid")
        dimension = _slugify(key)
        if dimension in validated:
            raise PersonaRuntimeError(
                "drift dimension is duplicated")
        validated[dimension] = _validate_strength(value)
    return validated


def drift_score(scores: Any) -> dict[str, Any]:
    """Shape and route one drift score record (§§27–28). Pure.

    ``scores`` maps §28 dimension names to unit-interval
    drift values; an unlisted dimension scores 0.0 (no
    drift evidence), and an unknown dimension, a
    duplicated dimension, or a value outside the unit
    interval is refused. The total is the deterministic
    mean over all ten dimensions. The record is
    significant — and routes to repair — when the total
    reaches the total threshold or any single dimension
    reaches the dimension threshold; otherwise it is
    acceptable and routes to output. Only significant
    drift triggers repair: tiny differences are not
    polished (§29's counsel, stood here as the routing
    rule). No draft is read, scored from prose, or
    repaired by this layer — the record shapes and
    routes scores a caller supplies.
    """
    validated = _validate_drift_scores(scores)
    dimensions = {
        dimension: validated.get(dimension, 0.0)
        for dimension in DRIFT_DIMENSIONS
    }
    total = sum(dimensions.values()) / len(DRIFT_DIMENSIONS)
    max_dimension = max(
        DRIFT_DIMENSIONS, key=lambda dim: dimensions[dim])
    significant_dimensions = [
        dimension for dimension in DRIFT_DIMENSIONS
        if dimensions[dimension] >= DRIFT_DIMENSION_THRESHOLD
    ]
    significant = total >= DRIFT_TOTAL_THRESHOLD \
        or bool(significant_dimensions)
    return {
        "total": total,
        "dimensions": dimensions,
        "max_dimension": max_dimension,
        "max_score": dimensions[max_dimension],
        "significant_dimensions": significant_dimensions,
        "significant": significant,
        "route": "repair" if significant else "output",
        "repair_required": significant,
    }


def drift_route(scores: Any) -> str:
    """The §27 route for one drift score record. Pure."""
    return drift_score(scores)["route"]


# --- §29 drift score artefact + §30 drift repair ---------------------
#
# Pure contract data and functions, like §§23–28. §29
# stands the conceptual drift-score artefact in the
# roadmap's YAML shape over the §28 score record, with a
# validator that recomputes every derived field (the
# stored-flag-agreement pattern of Slices 104/107/108).
# §30 stands the repair pipeline in contract form: a plan
# names the steps a repairer would walk, reconciled
# against the §§17/18 anchors — nothing here reads a
# draft, identifies a violation in prose, rewrites
# anything, or delivers anything.

# The §29 artefact's fields, in roadmap order (total and
# dimensions are the roadmap's own; the rest carry the
# §28 record's routing so the artefact is self-contained).
DRIFT_SCORE_ARTEFACT_FIELDS = (
    "total", "dimensions", "significant",
    "significant_dimensions", "route", "repair_required",
)

# The §30 repair pipeline steps, in roadmap order.
REPAIR_PIPELINE = (
    "draft", "identify_violated_persona_anchors",
    "rewrite_minimally", "verify", "deliver",
)


def drift_score_artifact(scores: Any) -> dict[str, Any]:
    """The §29 drift-score artefact for one score record. Pure.

    The artefact is the roadmap's conceptual YAML shape —
    a ``drift`` mapping carrying the total and the
    per-dimension values over all ten §28 dimensions —
    plus the §28 routing fields, so a consumer never has
    to recompute significance to know whether repair is
    triggered. Only significant drift triggers repair
    (§29): tiny stylistic differences are not polished.
    """
    record = drift_score(scores)
    return {
        "drift": {
            "total": record["total"],
            "dimensions": dict(record["dimensions"]),
            "significant": record["significant"],
            "significant_dimensions":
                list(record["significant_dimensions"]),
            "route": record["route"],
            "repair_required": record["repair_required"],
        },
    }


def validate_drift_score_artifact(artifact: Any) -> dict[str, Any]:
    """Validate one §29 artefact, refusing disagreement. Pure.

    The artefact must carry exactly the ``drift`` mapping
    with exactly the artefact fields; its dimensions must
    name all ten §28 dimensions exactly once; and every
    derived field (total, significance, significant
    dimensions, route, repair flag) must agree with the
    recomputed §28 record — a tampered total or route is
    refused, never trusted. Returns a fresh normalised
    artefact built from the dimensions alone.
    """
    if not isinstance(artifact, dict) \
            or set(artifact) != {"drift"}:
        raise PersonaRuntimeError("drift artefact is invalid")
    drift = artifact["drift"]
    if not isinstance(drift, dict) \
            or set(drift) != set(DRIFT_SCORE_ARTEFACT_FIELDS):
        raise PersonaRuntimeError("drift artefact is invalid")
    raw_dimensions = drift["dimensions"]
    if not isinstance(raw_dimensions, dict) \
            or len(raw_dimensions) != len(DRIFT_DIMENSIONS):
        raise PersonaRuntimeError("drift artefact is invalid")
    validated = _validate_drift_scores(raw_dimensions)
    if set(validated) != set(DRIFT_DIMENSIONS):
        raise PersonaRuntimeError("drift artefact is invalid")
    expected = drift_score_artifact(validated)
    expected_drift = expected["drift"]
    if not isinstance(drift["total"], (int, float)) \
            or isinstance(drift["total"], bool) \
            or not math.isclose(float(drift["total"]),
                                 expected_drift["total"],
                                 rel_tol=0.0, abs_tol=1e-9):
        raise PersonaRuntimeError("drift artefact is invalid")
    for field in ("significant", "significant_dimensions",
                  "route", "repair_required"):
        if drift[field] != expected_drift[field]:
            raise PersonaRuntimeError(
                "drift artefact is invalid")
    return expected


def repair_pipeline() -> list[dict[str, Any]]:
    """The §30 repair pipeline, in roadmap order. Pure.

    Draft in, violated persona anchors identified,
    a minimal rewrite against those anchors only, a
    verification, then delivery. Nothing in the pipeline
    regenerates the whole draft. Fresh copies are
    returned; mutating a row does not poison the contract.
    """
    return [
        {
            "step": "draft",
            "kind": "input",
            "generates_new_draft": False,
            "rewrites": False,
        },
        {
            "step": "identify_violated_persona_anchors",
            "kind": "diagnosis",
            "generates_new_draft": False,
            "rewrites": False,
            "anchor_sources": ["anchors", "anti_anchors"],
        },
        {
            "step": "rewrite_minimally",
            "kind": "repair",
            "generates_new_draft": False,
            "rewrites": True,
            "scope": "violated_anchors_only",
            "regenerates_everything": False,
        },
        {
            "step": "verify",
            "kind": "verification",
            "generates_new_draft": False,
            "rewrites": False,
            "check": "drift_route_is_output",
        },
        {
            "step": "deliver",
            "kind": "delivery",
            "generates_new_draft": False,
            "rewrites": False,
        },
    ]


def repair_contract() -> dict[str, Any]:
    """The §30 drift-repair contract. Pure.

    Repair runs only on significant drift, rewrites
    minimally against the violated §§17/18 anchors, never
    regenerates everything, and verifies before it
    delivers. This layer performs no repair — the
    contract is the shape a repairer must follow.
    """
    return {
        "name": "DriftRepair",
        "input": "llm_draft",
        "requires": "significant_drift",
        "pipeline": list(REPAIR_PIPELINE),
        "anchor_sources": ["anchors", "anti_anchors"],
        "minimal_rewrite": True,
        "regenerates_everything": False,
        "verify_before_deliver": True,
        "output": "delivered_draft",
    }


def _validate_violated_anchors(raw: Any, field: str) -> list[str]:
    if raw is None:
        return []
    if not isinstance(raw, (list, tuple)):
        raise PersonaRuntimeError(f"{field} are invalid")
    if len(raw) > MAX_ANCHORS:
        raise PersonaRuntimeError(f"{field} are invalid")
    anchors: list[str] = []
    for item in raw:
        if not isinstance(item, str):
            raise PersonaRuntimeError(f"{field} are invalid")
        text = item.strip()
        if not text or len(text) > MAX_ANCHOR_CHARS:
            raise PersonaRuntimeError(f"{field} are invalid")
        if text in anchors:
            raise PersonaRuntimeError(f"{field} are invalid")
        anchors.append(text)
    return anchors


def repair_plan(scores: Any, violated_anchors: Any = (),
                violated_anti_anchors: Any = ()) -> dict[str, Any]:
    """One §30 repair plan for a drift score record. Pure.

    The plan carries the §29 artefact, the caller-named
    violated §§17/18 anchors (bounded and verbatim, like
    the config lists), and — only when the drift is
    significant — the five pipeline steps as planned
    steps, the identify step carrying the violated lists
    and the rewrite step scoped to those anchors only.
    Insignificant drift plans no repair at all: the
    action is deliver-without-repair with no steps, so
    tiny differences are never polished (§29). This
    layer identifies no violation in prose and rewrites
    nothing — identification and rewriting are the
    repairer's work, under this plan's shape.
    """
    artifact = drift_score_artifact(scores)
    drift = artifact["drift"]
    anchors = _validate_violated_anchors(
        violated_anchors, "violated anchors")
    anti_anchors = _validate_violated_anchors(
        violated_anti_anchors, "violated anti-anchors")
    required = bool(drift["repair_required"])
    steps: list[dict[str, Any]] = []
    if required:
        for row in repair_pipeline():
            step = dict(row)
            step["status"] = "planned"
            if step["step"] == "identify_violated_persona_anchors":
                step["violated_anchors"] = list(anchors)
                step["violated_anti_anchors"] = list(anti_anchors)
            steps.append(step)
    return {
        "repair_required": required,
        "route": drift["route"],
        "action": "repair_minimally" if required
        else "deliver_without_repair",
        "drift": drift,
        "violated_anchors": anchors,
        "violated_anti_anchors": anti_anchors,
        "steps": steps,
        "minimal_rewrite": True,
        "regenerates_everything": False,
        "verify_before_deliver": True,
    }


# --- §31 fast local persona watchdog + §32 persona refresh -----------
#
# Pure contract data and functions, like §§23–30. §31
# names the small local nervous-system model as the ideal
# watchdog worker: the six lightweight tasks it can
# perform without expensive heavy inference, while the
# larger model generates difficult content — the local
# model keeps the personality coherent. §32 names persona
# refresh for extremely long sessions: the triggers that
# call for one and the contents a refresh carries, so
# identity does not slowly evaporate. Nothing here runs a
# local model, watches a session, counts messages in a
# live conversation, or injects a refresh into a context:
# §33's wider event-based trigger list is a later section,
# and actually performing a refresh belongs to prompt
# assembly (§53). The §32 message interval is this layer's
# recorded convention (the roadmap says every N messages
# and names no N). §33 widens the trigger list to named
# events — better than a fixed interval alone — and §34
# stands model switching: every model receives the same
# canonical Persona Kernel, the model is the engine and
# the persona system is the identity layer. Nothing here
# watches for an event, routes a model, or switches one.

# The six §31 local-watchdog tasks, in roadmap order.
LOCAL_WATCHDOG_TASKS = (
    "persona_classification", "drift_detection",
    "section_retrieval", "tone_checking", "memory_routing",
    "response_scoring",
)

# Each §31 task's grounding in the surfaces already
# banked: the local worker performs the task over these,
# never over a heavy-inference generation pass.
_LOCAL_WATCHDOG_SURFACES = {
    "persona_classification": "persona_ir",
    "drift_detection": "drift_score",
    "section_retrieval": "hybrid_retrieval",
    "tone_checking": "drift_dimension_tone",
    "memory_routing": "persona_router",
    "response_scoring": "drift_score_artifact",
}

# The §32 refresh triggers, in roadmap order.
REFRESH_TRIGGERS = (
    "message_interval", "context_summarization",
    "model_switch",
)

# The §32 refresh contents, in roadmap order: the Persona
# Kernel, the current relationship state, and the
# relevant Service Bible anchors — nothing else.
REFRESH_CONTENTS = (
    "persona_kernel", "current_relationship_state",
    "relevant_service_bible_anchors",
)

# §32 convention (this layer's own — see the header note):
# a message-interval refresh is due every 50 messages.
REFRESH_MESSAGE_INTERVAL = 50


def local_watchdog_tasks() -> list[dict[str, Any]]:
    """The six §31 local-watchdog tasks, in roadmap order. Pure.

    Each task is work the small local model performs
    without expensive heavy inference, grounded in the
    banked surface named in its row. Fresh copies are
    returned; mutating a row does not poison the contract.
    """
    return [
        {
            "task": task,
            "worker": "local_model",
            "heavy_inference_required": False,
            "generates_difficult_content": False,
            "surface": _LOCAL_WATCHDOG_SURFACES[task],
        }
        for task in LOCAL_WATCHDOG_TASKS
    ]


def local_watchdog_contract() -> dict[str, Any]:
    """The §31 fast local persona watchdog contract. Pure.

    The watchdog worker is the small local nervous-system
    model: it performs the six §31 tasks without expensive
    heavy inference and keeps the personality coherent.
    The larger model generates difficult content; the
    local model generates none of it. This layer runs no
    model — the contract names which worker each kind of
    work belongs to.
    """
    return {
        "name": "FastLocalPersonaWatchdog",
        "worker": "small_local_model",
        "role": "nervous_system",
        "tasks": list(LOCAL_WATCHDOG_TASKS),
        "heavy_inference_required": False,
        "generates_difficult_content": False,
        "difficult_content_worker": "larger_model",
        "keeps_persona_coherent": True,
    }


def watchdog_worker(task: Any) -> str:
    """Which model performs one named task (§31). Pure.

    One of the six §31 tasks belongs to the local model;
    generating difficult content belongs to the larger
    model; anything else is refused rather than assigned
    by guesswork.
    """
    if not isinstance(task, str):
        raise PersonaRuntimeError("watchdog task is invalid")
    resolved = _slugify(task)
    if resolved in LOCAL_WATCHDOG_TASKS:
        return "local_model"
    if resolved in ("difficult_content_generation",
                    "generate_difficult_content"):
        return "larger_model"
    raise PersonaRuntimeError("watchdog task is invalid")


def refresh_triggers() -> list[str]:
    return list(REFRESH_TRIGGERS)


def refresh_contents() -> list[str]:
    return list(REFRESH_CONTENTS)


def refresh_contract() -> dict[str, Any]:
    """The §32 persona refresh contract. Pure.

    For extremely long sessions the active context is
    refreshed periodically: on the message interval,
    after context summarization, or after a model switch.
    A refresh carries exactly the Persona Kernel, the
    current relationship state, and the relevant Service
    Bible anchors — and prevents slow identity
    evaporation. This layer performs no refresh and
    injects nothing; it names the trigger/contents shape
    a refresher must follow.
    """
    return {
        "name": "PersonaRefresh",
        "triggers": list(REFRESH_TRIGGERS),
        "message_interval": REFRESH_MESSAGE_INTERVAL,
        "contents": list(REFRESH_CONTENTS),
        "prevents": "slow_identity_evaporation",
        "injects_context": False,
    }


def _validate_refresh_trigger(trigger: Any) -> str:
    if not isinstance(trigger, str) \
            or _slugify(trigger) not in REFRESH_TRIGGERS:
        raise PersonaRuntimeError("refresh trigger is invalid")
    return _slugify(trigger)


def refresh_due(trigger: Any,
                messages_since_refresh: Any = None) -> bool:
    """Whether one §32 refresh trigger has fired. Pure.

    The event triggers (context summarization, model
    switch) are due the moment the named event has
    occurred — naming the trigger is naming the event.
    The message-interval trigger is due only when the
    caller-supplied count of messages since the last
    refresh reaches this layer's recorded interval; a
    missing or malformed count for that trigger is
    refused, never guessed. No session is watched and no
    messages are counted by this layer.
    """
    resolved = _validate_refresh_trigger(trigger)
    if resolved != "message_interval":
        return True
    if isinstance(messages_since_refresh, bool) \
            or not isinstance(messages_since_refresh, int) \
            or messages_since_refresh < 0:
        raise PersonaRuntimeError(
            "messages since refresh is invalid")
    return messages_since_refresh >= REFRESH_MESSAGE_INTERVAL


def refresh_plan(trigger: Any,
                 messages_since_refresh: Any = None) -> dict[str, Any]:
    """One §32 refresh plan for a named trigger. Pure.

    A due plan carries exactly the three §32 contents —
    the Persona Kernel (the §§9–10 compiled, pinned
    kernel), the current relationship state, and the
    relevant Service Bible anchors only. A plan whose
    message interval has not yet elapsed carries no
    contents and refreshes nothing. This layer assembles
    none of the contents and injects nothing.
    """
    resolved = _validate_refresh_trigger(trigger)
    due = refresh_due(resolved, messages_since_refresh)
    return {
        "trigger": resolved,
        "due": due,
        "action": "refresh" if due else "no_refresh",
        "contents": list(REFRESH_CONTENTS) if due else [],
        "prevents": "slow_identity_evaporation",
        "message_interval": REFRESH_MESSAGE_INTERVAL,
        "messages_since_refresh": messages_since_refresh
        if resolved == "message_interval" else None,
    }


# The §33 event-based refresh triggers, in roadmap order.
# ``model_switch`` also stands in the §32 list; §33's
# ``context_compression`` is the compression event the
# §32 list names as context summarization — the two lists
# name the same refresh under their own section's words,
# and neither is widened into the other.
EVENT_REFRESH_TRIGGERS = (
    "context_compression", "model_switch", "agent_handoff",
    "long_idle_period", "persona_file_modification",
    "major_relationship_event", "memory_consolidation",
)


def event_refresh_triggers() -> list[str]:
    return list(EVENT_REFRESH_TRIGGERS)


def event_refresh_contract() -> dict[str, Any]:
    """The §33 event-based persona refresh contract. Pure.

    Event-based refresh is better than a fixed interval
    alone: a refresh is due after any of the seven named
    events, with no interval needing to elapse. A due
    event refresh carries exactly the §32 contents and
    prevents the same slow identity evaporation. This
    layer watches for no event and injects nothing; it
    names the event/contents shape a refresher must
    follow.
    """
    return {
        "name": "EventBasedPersonaRefresh",
        "triggers": list(EVENT_REFRESH_TRIGGERS),
        "better_than_fixed_interval_alone": True,
        "fixed_interval_required": False,
        "contents": list(REFRESH_CONTENTS),
        "prevents": "slow_identity_evaporation",
        "watches_session": False,
        "injects_context": False,
    }


def _validate_event_refresh_trigger(event: Any) -> str:
    if not isinstance(event, str) \
            or _slugify(event) not in EVENT_REFRESH_TRIGGERS:
        raise PersonaRuntimeError("event refresh trigger is invalid")
    return _slugify(event)


def event_refresh_due(event: Any) -> bool:
    """Whether one §33 event refresh is due. Pure.

    Naming a §33 event is naming its occurrence, so a
    valid event is due the moment it has occurred — no
    fixed interval must also elapse. The roadmap names
    no duration for the long idle period, so none is
    invented here: the caller names the event, this
    layer never watches a session or measures idleness.
    A §32-only trigger (the message interval, context
    summarization) is not a §33 event and is refused.
    """
    _validate_event_refresh_trigger(event)
    return True


def event_refresh_plan(event: Any) -> dict[str, Any]:
    """One §33 event-based refresh plan for a named event. Pure.

    An event plan is always a due plan: it carries
    exactly the three §32 contents — the Persona Kernel,
    the current relationship state, and the relevant
    Service Bible anchors — and requires no message
    interval. This layer assembles none of the contents
    and injects nothing.
    """
    resolved = _validate_event_refresh_trigger(event)
    return {
        "trigger": resolved,
        "due": True,
        "action": "refresh",
        "basis": "event",
        "fixed_interval_required": False,
        "contents": list(REFRESH_CONTENTS),
        "prevents": "slow_identity_evaporation",
    }


def model_switch_contract() -> dict[str, Any]:
    """The §34 model switching contract. Pure.

    Hermes may route between models, and every model
    receives the same canonical Persona Kernel: the
    model is the engine, the persona system is the
    identity layer, so the persona remains itself across
    a switch. A model switch is also a §§32–33 refresh
    trigger. This layer routes no model and switches
    nothing; it names the identity shape a switch must
    preserve.
    """
    return {
        "name": "PersonaModelSwitching",
        "kernel": "canonical_persona_kernel",
        "same_kernel_for_all_models": True,
        "model_role": "engine",
        "persona_system_role": "identity_layer",
        "identity_survives_switch": True,
        "refresh_trigger": "model_switch",
        "routes_models": False,
    }


def _validate_model_name(model: Any) -> str:
    if not isinstance(model, str) or not model.strip():
        raise PersonaRuntimeError("model name is invalid")
    return _slugify(model)


def _validate_kernel_hash(kernel_hash: Any) -> str:
    if not isinstance(kernel_hash, str) or not kernel_hash.strip():
        raise PersonaRuntimeError("kernel hash is invalid")
    return kernel_hash.strip()


def model_switch_plan(from_model: Any, to_model: Any,
                      kernel_hash: Any) -> dict[str, Any]:
    """One §34 model switch plan over the canonical kernel. Pure.

    Both models are named by slugified caller-supplied
    names and must differ — a switch to the same model
    is no switch and is refused, as is a missing or
    malformed kernel hash (the §§9–10 kernel hash this
    layer already stands). The plan carries the one
    kernel hash for both sides: the receiving model gets
    the SAME canonical Persona Kernel the sending model
    had, so identity is preserved by construction. This
    layer performs no switch.
    """
    source = _validate_model_name(from_model)
    target = _validate_model_name(to_model)
    if source == target:
        raise PersonaRuntimeError("model switch names one model")
    digest = _validate_kernel_hash(kernel_hash)
    return {
        "from_model": source,
        "to_model": target,
        "kernel": "canonical_persona_kernel",
        "kernel_hash": digest,
        "from_kernel_hash": digest,
        "to_kernel_hash": digest,
        "same_kernel": True,
        "identity_preserved": True,
        "model_role": "engine",
        "persona_system_role": "identity_layer",
        "refresh_trigger": "model_switch",
    }


def kernel_identity_preserved(kernel_hash_before: Any,
                              kernel_hash_after: Any) -> bool:
    """Whether persona identity survives a model switch (§34). Pure.

    Identity is preserved exactly when the canonical
    Persona Kernel hash a model receives after a switch
    equals the hash in force before it — the same kernel
    (§§9–10), therefore the same persona, whatever the
    engine. A missing or malformed hash on either side
    is refused, never treated as preserved or as lost.
    """
    before = _validate_kernel_hash(kernel_hash_before)
    after = _validate_kernel_hash(kernel_hash_after)
    return before == after


# --- §35 persona handoff packet + §36 subagent separation ------------
#
# Pure contract data and functions, like §§31–34. §35
# names the handoff packet created when routing to
# another model: persona id, persona version, kernel,
# current mode, relationship state, and the relevant
# sections named by their §12 stable ids — so the whole
# conversation need not be passed when unnecessary. The
# packet's ``kernel`` field carries the §§9–10 kernel
# hash (the §34 identity proof), not kernel text. §36
# names subagent separation: subagents are not turned
# into the primary persona — each carries its own
# identity and role, while the primary persona may
# delegate and maintains its own identity throughout.
# Nothing here routes a model, hands anything off,
# delegates work, or spawns a subagent.

# The §35 handoff packet's fields, in roadmap order.
HANDOFF_PACKET_FIELDS = (
    "persona_id", "persona_version", "kernel",
    "current_mode", "relationship_state", "relevant_sections",
)

# §35 bounds (this layer's recorded conventions): a
# handoff names at most 32 relevant sections, and the
# relationship-state summary at most 1,000 characters.
MAX_HANDOFF_SECTIONS = 32
MAX_HANDOFF_STATE_CHARS = 1000

_STABLE_ID_FORM = re.compile(
    r"^[a-z0-9]+(?:_[a-z0-9]+)*\.[a-z0-9]+(?:_[a-z0-9]+)*$")


def handoff_packet_fields() -> list[str]:
    return list(HANDOFF_PACKET_FIELDS)


def handoff_contract() -> dict[str, Any]:
    """The §35 persona handoff packet contract. Pure.

    When routing to another model, a handoff packet is
    created carrying exactly the six §35 fields — the
    persona id, its §22 version, the kernel (named by
    its §§9–10 hash), the current mode, the relationship
    state, and the relevant sections by §12 stable id.
    The whole conversation is not passed when that is
    unnecessary. This layer creates no live handoff and
    routes no model; it names the packet shape a router
    must build.
    """
    return {
        "name": "PersonaHandoffPacket",
        "created_when": "routing_to_another_model",
        "fields": list(HANDOFF_PACKET_FIELDS),
        "kernel_form": "kernel_hash",
        "sections_named_by": "stable_id",
        "passes_whole_conversation": False,
        "routes_models": False,
    }


def _validate_handoff_mode(mode: Any) -> str:
    if not isinstance(mode, str) or not mode.strip() \
            or len(mode.strip()) > MAX_NAME_CHARS:
        raise PersonaRuntimeError("handoff current mode is invalid")
    return _slugify(mode)


def _validate_handoff_state(state: Any) -> str:
    if not isinstance(state, str) or not state.strip() \
            or len(state.strip()) > MAX_HANDOFF_STATE_CHARS:
        raise PersonaRuntimeError(
            "handoff relationship state is invalid")
    return state.strip()


def _validate_stable_id(value: Any) -> str:
    if not isinstance(value, str) \
            or not _STABLE_ID_FORM.match(value.strip()):
        raise PersonaRuntimeError("handoff section id is invalid")
    return value.strip()


def _validate_handoff_sections(raw: Any) -> list[str]:
    if not isinstance(raw, (list, tuple)) \
            or len(raw) > MAX_HANDOFF_SECTIONS:
        raise PersonaRuntimeError("handoff sections are invalid")
    sections: list[str] = []
    for item in raw:
        section = _validate_stable_id(item)
        if section in sections:
            raise PersonaRuntimeError("handoff sections are invalid")
        sections.append(section)
    return sections


def handoff_packet(compiled: dict[str, Any], current_mode: Any,
                   relationship_state: Any,
                   relevant_sections: Any = ()) -> dict[str, Any]:
    """Build one §35 handoff packet from a compiled persona. Pure.

    The packet stands in the roadmap's YAML shape — a
    ``persona_handoff`` mapping with exactly the six
    §35 fields. Persona id and version come from the
    compiled artefact (the §22 per-persona version), the
    kernel is named by its §§9–10 hash, and every
    relevant section must be a §12 stable id that exists
    in the compiled index — an unknown section is
    refused, never passed along by guesswork. The whole
    conversation is never a field. This layer routes
    nothing and hands nothing off.
    """
    record = hash_record(compiled)
    version = _compiled_version(compiled)
    index = compiled.get("index")
    if not isinstance(index, list):
        raise PersonaRuntimeError("compiled persona is invalid")
    known = {
        entry.get("stable_id") for entry in index
        if isinstance(entry, dict)
    }
    sections = _validate_handoff_sections(relevant_sections)
    for section in sections:
        if section not in known:
            raise PersonaRuntimeError("handoff section id is invalid")
    return {
        "persona_handoff": {
            "persona_id": record["persona_id"],
            "persona_version": version,
            "kernel": record["kernel_hash"],
            "current_mode": _validate_handoff_mode(current_mode),
            "relationship_state": _validate_handoff_state(
                relationship_state),
            "relevant_sections": sections,
        },
    }


def validate_handoff_packet(packet: Any) -> dict[str, Any]:
    """Validate one §35 handoff packet, refusing disagreement. Pure.

    The packet must carry exactly the ``persona_handoff``
    mapping with exactly the six §35 fields; the version
    must be strict §22 semver, the kernel a non-empty
    hash string, the mode a slugified name, the
    relationship state a bounded summary, and every
    relevant section a well-formed §12 stable id, named
    at most once. Returns a fresh normalised packet.
    (Existence of the sections in a compile is the
    builder's check; this validator checks the shape any
    receiver can check.)
    """
    if not isinstance(packet, dict) \
            or set(packet) != {"persona_handoff"}:
        raise PersonaRuntimeError("handoff packet is invalid")
    handoff = packet["persona_handoff"]
    if not isinstance(handoff, dict) \
            or set(handoff) != set(HANDOFF_PACKET_FIELDS):
        raise PersonaRuntimeError("handoff packet is invalid")
    persona_id = handoff["persona_id"]
    if not isinstance(persona_id, str) or not persona_id.strip() \
            or len(persona_id.strip()) > MAX_NAME_CHARS \
            or _slugify(persona_id) != persona_id.strip():
        raise PersonaRuntimeError("handoff packet is invalid")
    parse_persona_version(handoff["persona_version"])
    kernel = _validate_kernel_hash(handoff["kernel"])
    return {
        "persona_handoff": {
            "persona_id": persona_id.strip(),
            "persona_version": handoff["persona_version"],
            "kernel": kernel,
            "current_mode": _validate_handoff_mode(
                handoff["current_mode"]),
            "relationship_state": _validate_handoff_state(
                handoff["relationship_state"]),
            "relevant_sections": _validate_handoff_sections(
                handoff["relevant_sections"]),
        },
    }


# The §36 example roster, in roadmap order: the primary
# persona first, then the specialised subagents. The
# roster is the roadmap's example, not a closed list —
# any other agent is likewise a subagent (see
# ``subagent_separation``).
EXAMPLE_SUBAGENTS = (
    ("caducea", "orchestrator_companion"),
    ("volundr", "specialized_builder"),
    ("saga", "historian"),
    ("eir", "repair_agent"),
)


def subagent_examples() -> list[dict[str, Any]]:
    """The §36 example roster, in roadmap order. Pure.

    The primary persona stands first; every other named
    agent is a subagent carrying its own identity and
    role, never the primary persona. Fresh copies are
    returned; mutating a row does not poison the roster.
    """
    return [
        {
            "agent": name,
            "role": role,
            "is_primary_persona": index == 0,
            "carries_primary_persona": index == 0,
        }
        for index, (name, role) in enumerate(EXAMPLE_SUBAGENTS)
    ]


def subagent_contract() -> dict[str, Any]:
    """The §36 subagent separation contract. Pure.

    Subagents are not accidentally turned into the
    primary persona: each carries its own identity and
    role. The primary persona may delegate while
    maintaining its own primary character identity.
    This layer delegates nothing and spawns nothing; it
    names the separation a delegator must keep.
    """
    return {
        "name": "SubagentSeparation",
        "primary_persona": "caducea",
        "examples": [name for name, _role in EXAMPLE_SUBAGENTS],
        "subagents_carry_primary_persona": False,
        "subagents_have_own_identities": True,
        "primary_may_delegate": True,
        "primary_identity_maintained": True,
        "delegates_work": False,
    }


def subagent_separation(agent: Any,
                        primary_persona: Any = "caducea") -> dict[str, Any]:
    """Classify one agent against the primary persona (§36). Pure.

    The agent whose slugified name matches the primary
    persona is the primary: it carries the persona and
    may delegate while maintaining its identity. Every
    other agent is a subagent: it carries its own
    identity and role and does NOT carry the primary
    persona — delegation never turns it into the
    primary. A missing or malformed name on either side
    is refused, never classified by guesswork.
    """
    if not isinstance(agent, str) or not agent.strip():
        raise PersonaRuntimeError("subagent name is invalid")
    if not isinstance(primary_persona, str) \
            or not primary_persona.strip():
        raise PersonaRuntimeError("primary persona is invalid")
    resolved = _slugify(agent)
    primary = _slugify(primary_persona)
    is_primary = resolved == primary
    return {
        "agent": resolved,
        "is_primary_persona": is_primary,
        "carries_primary_persona": is_primary,
        "has_own_identity": True,
        "may_delegate": is_primary,
        "primary_identity_maintained": True,
    }


# --- §37 persona state + §38 modes -----------------------------------
#
# Pure contract data and functions, like §§35–36. §37
# names the dynamic persona-state object (id, version,
# active mode, emotional state, relationship state,
# active project, current task) — dynamic, and it must
# never replace canonical PersonaIR. §38 names the
# modes: a mode modifies emphasis without changing
# identity, foregrounding parts of the same personality.
# Nothing here stores state, tracks a live session, or
# switches a mode.

# The §37 persona-state fields, in roadmap order.
PERSONA_STATE_FIELDS = (
    "id", "version", "active_mode", "emotional_state",
    "relationship_state", "active_project", "current_task",
)

# The §37 emotional-state fields, in roadmap order.
EMOTIONAL_STATE_FIELDS = ("warmth", "playfulness", "focus")

# The §37 relationship-state fields, in roadmap order.
RELATIONSHIP_STATE_FIELDS = ("trust",)

# The §38 modes, in roadmap order (slug form; the
# roadmap names them COUNSELOR, EXECUTOR, ARCHITECT,
# SKALD, COMPANION, RESEARCHER, FORGE_WORKER).
PERSONA_MODES = (
    "counselor", "executor", "architect", "skald",
    "companion", "researcher", "forge_worker",
)


def persona_state_fields() -> list[str]:
    return list(PERSONA_STATE_FIELDS)


def persona_modes() -> list[str]:
    return list(PERSONA_MODES)


def _validate_unit_interval(value: Any) -> float:
    if isinstance(value, bool) \
            or not isinstance(value, (int, float)):
        raise PersonaRuntimeError("persona state value is invalid")
    number = float(value)
    if not 0.0 <= number <= 1.0:
        raise PersonaRuntimeError("persona state value is invalid")
    return number


def _validate_scored_state(raw: Any,
                           fields: tuple[str, ...]) -> dict[str, float]:
    if not isinstance(raw, dict) or set(raw) != set(fields):
        raise PersonaRuntimeError("persona state value is invalid")
    return {field: _validate_unit_interval(raw[field])
            for field in fields}


def _validate_state_name(value: Any) -> str:
    if not isinstance(value, str) or not value.strip() \
            or len(value.strip()) > MAX_NAME_CHARS:
        raise PersonaRuntimeError("persona state value is invalid")
    return _slugify(value)


def _validate_active_mode(mode: Any) -> str:
    resolved = _validate_state_name(mode)
    if resolved not in PERSONA_MODES:
        raise PersonaRuntimeError("persona state mode is invalid")
    return resolved


def persona_state_contract() -> dict[str, Any]:
    """The §37 persona state contract. Pure.

    The persona state is a dynamic runtime object in the
    roadmap's YAML shape. It carries current mode,
    emotional and relationship state, and the active
    project and task — and it must never replace
    canonical PersonaIR, which remains the identity
    artefact. This layer stores no state and tracks
    nothing live; it names the object a runtime carries.
    """
    return {
        "name": "PersonaState",
        "fields": list(PERSONA_STATE_FIELDS),
        "emotional_state_fields": list(EMOTIONAL_STATE_FIELDS),
        "relationship_state_fields": list(RELATIONSHIP_STATE_FIELDS),
        "dynamic": True,
        "replaces_persona_ir": False,
        "canonical_source": "persona_ir",
        "stores_state": False,
    }


def persona_state(compiled: dict[str, Any], active_mode: Any,
                  emotional_state: Any, relationship_state: Any,
                  active_project: Any,
                  current_task: Any) -> dict[str, Any]:
    """Build one §37 persona state from a compiled persona. Pure.

    The object stands in the roadmap's YAML shape — a
    ``persona_state`` mapping with exactly the seven
    §37 fields. Id and the §22 version come from the
    compiled artefact; the active mode must be one of
    the §38 modes; emotional state (warmth, playfulness,
    focus) and relationship trust are unit-interval
    numbers; project and task are slugified names. The
    object is dynamic only: building it changes no
    compile, no kernel hash, and no PersonaIR, and it
    never replaces the IR.
    """
    record = hash_record(compiled)
    version = _compiled_version(compiled)
    return {
        "persona_state": {
            "id": record["persona_id"],
            "version": version,
            "active_mode": _validate_active_mode(active_mode),
            "emotional_state": _validate_scored_state(
                emotional_state, EMOTIONAL_STATE_FIELDS),
            "relationship_state": _validate_scored_state(
                relationship_state, RELATIONSHIP_STATE_FIELDS),
            "active_project": _validate_state_name(active_project),
            "current_task": _validate_state_name(current_task),
        },
    }


def validate_persona_state(state: Any) -> dict[str, Any]:
    """Validate one §37 persona state, refusing disagreement. Pure.

    The object must carry exactly the ``persona_state``
    mapping with exactly the seven §37 fields; the id
    must be a slug, the version strict §22 semver, the
    active mode one of the §38 modes, and every scored
    field a unit-interval number. Returns a fresh
    normalised object.
    """
    if not isinstance(state, dict) \
            or set(state) != {"persona_state"}:
        raise PersonaRuntimeError("persona state is invalid")
    body = state["persona_state"]
    if not isinstance(body, dict) \
            or set(body) != set(PERSONA_STATE_FIELDS):
        raise PersonaRuntimeError("persona state is invalid")
    persona_id = body["id"]
    if not isinstance(persona_id, str) or not persona_id.strip() \
            or len(persona_id.strip()) > MAX_NAME_CHARS \
            or _slugify(persona_id) != persona_id.strip():
        raise PersonaRuntimeError("persona state is invalid")
    parse_persona_version(body["version"])
    return {
        "persona_state": {
            "id": persona_id.strip(),
            "version": body["version"],
            "active_mode": _validate_active_mode(body["active_mode"]),
            "emotional_state": _validate_scored_state(
                body["emotional_state"], EMOTIONAL_STATE_FIELDS),
            "relationship_state": _validate_scored_state(
                body["relationship_state"],
                RELATIONSHIP_STATE_FIELDS),
            "active_project": _validate_state_name(
                body["active_project"]),
            "current_task": _validate_state_name(body["current_task"]),
        },
    }


def mode_contract() -> dict[str, Any]:
    """The §38 modes contract. Pure.

    Modes modify emphasis without changing identity: a
    mode changes what parts of the same personality
    become foregrounded. This layer switches no mode
    live; it names the modes and the rule a mode
    switcher (§39 routing, later) must keep.
    """
    return {
        "name": "PersonaModes",
        "modes": list(PERSONA_MODES),
        "modifies_emphasis": True,
        "changes_identity": False,
        "foregrounds_same_personality": True,
        "switches_modes": False,
    }


def mode_profile(mode: Any) -> dict[str, Any]:
    """Classify one §38 mode. Pure.

    A named mode from the §38 list foregrounds itself —
    its own part of the same personality — while the
    persona's identity is unchanged and preserved. An
    unknown or malformed mode is refused, never
    classified by guesswork. The result's mode is also
    a valid §35/§37 ``current_mode`` / ``active_mode``
    value.
    """
    resolved = _validate_active_mode(mode)
    return {
        "mode": resolved,
        "modifies_emphasis": True,
        "changes_identity": False,
        "foreground": resolved,
        "identity_preserved": True,
    }


# --- §39 mode routing + §40 persona-aware memory write ----
#
# §39: modes route automatically from the task signal —
# the user does not need to manually select modes. The
# four roadmap examples stand as data; routing a signal
# names the example's mode sequence, in order. Every
# routed mode is a §38 mode; routing changes no identity
# and switches nothing live.
#
# §40: when memory extraction occurs, memories are
# interpreted through the persona system. A memory write
# must not introduce personality drift through biased
# summarization: the record states who decided, what was
# decided, what recommendation was considered and by
# whom, and how the persona responded — in one neutral
# template — and biased phrasing is refused.

# The §39 routing examples, in roadmap order: signal ->
# mode sequence (§38 slugs).
MODE_ROUTING_EXAMPLES = (
    ("coding", ("architect", "forge_worker")),
    ("personal_reflection", ("companion", "counselor")),
    ("research", ("researcher",)),
    ("creative_article", ("skald",)),
)

# §40 record fields, in template order.
PERSONA_MEMORY_FIELDS = (
    "subject", "decision", "considered", "recommended_by",
    "response_by", "response", "memory_text",
)

# §40 bound: every free-text phrase in a memory record.
MAX_MEMORY_PHRASE_CHARS = 240

# §40 biased-summarization markers (slug form). The first
# is the roadmap's incorrect example verbatim; the rest
# are its recorded kin — evaluative or dismissive
# framings of a decision that must never enter a memory.
MEMORY_BIAS_MARKERS = (
    "ignored_good_advice", "ignored_advice",
    "ignored_the_recommendation", "good_advice",
    "bad_advice", "refused_to_listen", "stubbornly_refused",
)


def mode_routing_examples() -> list[dict[str, Any]]:
    return [{"signal": signal, "modes": list(modes)}
            for signal, modes in MODE_ROUTING_EXAMPLES]


def mode_routing_contract() -> dict[str, Any]:
    """The §39 mode routing contract. Pure.

    Modes are routed automatically from the task signal;
    the user does not need to manually select a mode.
    A route names a sequence of §38 modes in order —
    the work may move through them (architect, then
    forge_worker, for coding) — and routing modifies
    emphasis only: identity never changes. This layer
    switches no mode live; it names the route.
    """
    return {
        "name": "PersonaModeRouting",
        "examples": mode_routing_examples(),
        "automatic": True,
        "manual_selection_required": False,
        "changes_identity": False,
        "switches_modes": False,
    }


def route_mode(signal: Any) -> dict[str, Any]:
    """Route one task signal to its §39 mode sequence. Pure.

    The signal is either a §39 example name (slugified)
    or task text: text is classified by the §13 lexicon
    (coding / research tags) plus the reflection and
    creative-article tokens that lexicon does not carry.
    An empty or unrecognised signal is refused, never
    routed by guesswork. The first mode is where the
    work starts; the last is where it ends.
    """
    if not isinstance(signal, str) or not signal.strip():
        raise PersonaRuntimeError("mode routing signal is invalid")
    slug = _slugify(signal)
    resolved = dict(MODE_ROUTING_EXAMPLES).get(slug)
    if resolved is None:
        tags = classify_task(signal)
        tokens = _tokens(signal)
        if "coding" in tags:
            resolved = dict(MODE_ROUTING_EXAMPLES)["coding"]
            slug = "coding"
        elif tokens & {"personal", "reflection", "reflect",
                       "reflecting"}:
            resolved = dict(MODE_ROUTING_EXAMPLES)[
                "personal_reflection"]
            slug = "personal_reflection"
        elif "research" in tags:
            resolved = dict(MODE_ROUTING_EXAMPLES)["research"]
            slug = "research"
        elif tokens & {"creative", "article", "skald"}:
            resolved = dict(MODE_ROUTING_EXAMPLES)[
                "creative_article"]
            slug = "creative_article"
    if resolved is None:
        raise PersonaRuntimeError("mode routing signal is invalid")
    modes = list(resolved)
    for mode in modes:
        if mode not in PERSONA_MODES:
            raise PersonaRuntimeError("mode routing mode is invalid")
    return {
        "signal": slug,
        "modes": modes,
        "initial_mode": modes[0],
        "final_mode": modes[-1],
        "manual_selection_required": False,
        "changes_identity": False,
        "identity_preserved": True,
    }


def memory_write_contract() -> dict[str, Any]:
    """The §40 persona-aware memory write contract. Pure.

    When memory extraction occurs, memories are
    interpreted through the persona system: a record
    states the decision as its maker's own, any
    recommendation as considered (not as a verdict the
    maker ignored), and the persona's response plainly.
    Biased summarization is refused, so a memory cannot
    introduce personality drift. This layer writes no
    memory; it shapes the record an extractor writes.
    """
    return {
        "name": "PersonaAwareMemoryWrite",
        "fields": list(PERSONA_MEMORY_FIELDS),
        "interprets_through_persona": True,
        "biased_summarization_allowed": False,
        "introduces_personality_drift": False,
        "writes_memory": False,
        "bias_markers": list(MEMORY_BIAS_MARKERS),
    }


def _validate_memory_name(value: Any) -> str:
    if not isinstance(value, str) or not value.strip() \
            or len(value.strip()) > MAX_NAME_CHARS:
        raise PersonaRuntimeError("persona memory value is invalid")
    return _slugify(value)


def _validate_memory_phrase(value: Any) -> str:
    if not isinstance(value, str) or not value.strip() \
            or len(value.strip()) > MAX_MEMORY_PHRASE_CHARS:
        raise PersonaRuntimeError("persona memory value is invalid")
    phrase = " ".join(value.strip().split()).rstrip(".")
    if not phrase:
        raise PersonaRuntimeError("persona memory value is invalid")
    if _slugify(phrase) in MEMORY_BIAS_MARKERS \
            or any(marker in _slugify(phrase)
                   for marker in MEMORY_BIAS_MARKERS):
        raise PersonaRuntimeError(
            "persona memory phrasing is biased")
    return phrase


def _display_name(slug: str) -> str:
    return slug.replace("_", " ").capitalize()


def _memory_text(subject: str, decision: str,
                 considered: str | None,
                 recommended_by: str | None,
                 response_by: str | None,
                 response: str | None) -> str:
    first = f"{_display_name(subject)} selected {decision}"
    if considered is not None:
        first += (f" after considering "
                  f"{_display_name(recommended_by or '')}'s "
                  f"recommendation of {considered}")
    text = first + "."
    if response is not None:
        text += (f" {_display_name(response_by or '')} "
                 f"{response}.")
    return text


def persona_memory(subject: Any, decision: Any,
                     considered: Any = None,
                     recommended_by: Any = None,
                     response_by: Any = None,
                     response: Any = None) -> dict[str, Any]:
    """Build one §40 persona-aware memory record. Pure.

    The record stands with exactly the §40 fields: the
    decider and decision always; a considered
    recommendation only together with its recommender;
    a persona response only together with who responded.
    ``memory_text`` is the one neutral template over
    those fields — the decision is the maker's own, the
    recommendation was considered, the response is
    plain — and biased phrasing in any field is refused.
    """
    subject_slug = _validate_memory_name(subject)
    decision_text = _validate_memory_phrase(decision)
    considered_text = None
    recommender_slug = None
    if considered is not None:
        considered_text = _validate_memory_phrase(considered)
        recommender_slug = _validate_memory_name(recommended_by)
    elif recommended_by is not None:
        raise PersonaRuntimeError("persona memory value is invalid")
    responder_slug = None
    response_text = None
    if response is not None:
        response_text = _validate_memory_phrase(response)
        responder_slug = _validate_memory_name(response_by)
    elif response_by is not None:
        raise PersonaRuntimeError("persona memory value is invalid")
    return {
        "persona_memory": {
            "subject": subject_slug,
            "decision": decision_text,
            "considered": considered_text,
            "recommended_by": recommender_slug,
            "response_by": responder_slug,
            "response": response_text,
            "memory_text": _memory_text(
                subject_slug, decision_text, considered_text,
                recommender_slug, responder_slug, response_text),
        },
    }


def validate_persona_memory(record: Any) -> dict[str, Any]:
    """Validate one §40 memory record, refusing disagreement. Pure.

    The record must carry exactly the ``persona_memory``
    mapping with exactly the §40 fields, and its
    ``memory_text`` must recompute exactly from its
    fields under the neutral template — a tampered or
    biased text is refused. Returns a fresh record.
    """
    if not isinstance(record, dict) \
            or set(record) != {"persona_memory"}:
        raise PersonaRuntimeError("persona memory is invalid")
    body = record["persona_memory"]
    if not isinstance(body, dict) \
            or set(body) != set(PERSONA_MEMORY_FIELDS):
        raise PersonaRuntimeError("persona memory is invalid")
    rebuilt = persona_memory(
        body["subject"], body["decision"],
        considered=body["considered"],
        recommended_by=body["recommended_by"],
        response_by=body["response_by"],
        response=body["response"])
    if rebuilt["persona_memory"]["memory_text"] \
            != body["memory_text"]:
        raise PersonaRuntimeError("persona memory is invalid")
    return rebuilt


def classify_memory_write(text: Any) -> dict[str, Any]:
    """Classify one candidate memory text under §40. Pure.

    A text carrying any §40 bias marker (slug form) is
    biased summarization: it is refused as a memory
    write because it would introduce personality drift.
    Any other non-empty text classifies as neutral in
    form — classification judges phrasing only, never
    truth. Empty or non-text input is refused.
    """
    if not isinstance(text, str) or not text.strip():
        raise PersonaRuntimeError("persona memory text is invalid")
    slug = _slugify(text)
    markers = [marker for marker in MEMORY_BIAS_MARKERS
               if marker in slug]
    return {
        "biased": bool(markers),
        "bias_markers": markers,
        "allowed_as_memory": not markers,
        "introduces_personality_drift": bool(markers),
    }


# --- §41 memory must not override persona + §42 service bible ----
#
# §41: memory retrieval must not gradually transform the
# persona. Traits remain canonical; memory provides
# history. This is the §24 precedence rule applied to the
# memory tier specifically, reconciled with §25 (a memory
# claim, like a summary claim, may record state, never a
# trait) and §26 (a non-canonical source is at most a
# state). Repetition changes nothing: however many
# conversations involved frustration, their memories do
# not add up to an anxious personality. No memory is read
# or retrieved by this layer.
#
# §42: the Service Bible may become huge, so it is never
# continuously injected. Its sections are indexed by the
# roadmap's topic list and retrieved selectively — an
# explicit, deterministic selection over the compiled
# Layer B index, restricted to the service_bible role and
# reusing the §13 ranking. Nothing is injected here.

# What memory provides (§41), as stable slugs. History is
# the roadmap's own word; the other two are the §24
# effects a non-canonical source may touch.
MEMORY_PROVIDES = ("history", "recent_events", "immediate_context")

# The §42 topic index, in roadmap order (the roadmap's
# spellings slugified: AI -> ai, ADHD -> adhd).
SERVICE_BIBLE_TOPICS = (
    "communication", "coding", "linux", "open_source", "ai",
    "documentation", "research", "project_aesir", "attention",
    "adhd",
)

# Topic lexicon (§42): the words that signal each topic in
# a query, a task, or a section heading/id. Deterministic,
# like the §13 task lexicon; no model call.
_SERVICE_TOPIC_LEXICON = (
    ("communication", frozenset({
        "communication", "message", "messages", "tone", "voice",
        "speak", "speaking", "writing", "explain", "explaining"})),
    ("coding", frozenset({
        "coding", "code", "python", "function", "functions",
        "debug", "debugging", "refactor", "tests", "testing",
        "implement", "implementation"})),
    ("linux", frozenset({
        "linux", "shell", "systemd", "bash", "terminal",
        "command", "commands", "unix", "permissions"})),
    ("open_source", frozenset({
        "open", "source", "github", "license", "licence",
        "upstream", "repository", "repositories"})),
    ("ai", frozenset({
        "ai", "model", "models", "llm", "inference", "agent",
        "agents", "artificial", "intelligence"})),
    ("documentation", frozenset({
        "documentation", "docs", "document", "documents",
        "readme", "manual"})),
    ("research", frozenset({
        "research", "search", "investigate", "investigation",
        "explore", "compare", "comparison"})),
    ("project_aesir", frozenset({"aesir"})),
    ("attention", frozenset({
        "attention", "focus", "focused", "distraction",
        "distractions"})),
    ("adhd", frozenset({"adhd"})),
)


def memory_provides() -> list[str]:
    return list(MEMORY_PROVIDES)


def memory_must_not_override() -> list[str]:
    return list(HISTORY_MUST_NOT_REDEFINE)


def memory_override_contract() -> dict[str, Any]:
    """The §41 memory-must-not-override contract. Pure.

    Traits remain canonical — authored only in canonical
    persona documents (§24 tiers persona_core,
    relationship_model, service_bible). Memory, at the
    long_term_memory tier, provides history: it may affect
    current mood, immediate context, and recent events,
    and it must never override the persona, redefine
    foundational personality, identity, or traits, however
    many memories point the same way. This layer reads and
    retrieves no memory; it names the guard a retriever
    must honour.
    """
    return {
        "name": "MemoryMustNotOverridePersona",
        "traits_remain_canonical": True,
        "memory_role": "history",
        "memory_tier": "long_term_memory",
        "memory_may_override_persona": False,
        "memory_may_redefine_traits": False,
        "repeated_evidence_changes_authority": False,
        "memory_provides": list(MEMORY_PROVIDES),
        "memory_must_not_override": list(HISTORY_MUST_NOT_REDEFINE),
        "retrieves_memory": False,
    }


def memory_influence_allowed(target: Any) -> bool:
    """Whether memory may affect ``target`` (§41 via §24). Pure.

    Targets are the §24 effects and foundations (see
    ``influence_allowed``): memory may affect current
    mood, immediate context, and recent events; it may
    never touch foundational personality, identity, or
    traits. Unknown targets are refused.
    """
    return influence_allowed("long_term_memory", target)


def evaluate_memory_claim(text: Any) -> dict[str, Any]:
    """Evaluate one memory-derived claim under §41. Pure.

    The claim's form is the §25 grammatical classification
    (trait-form markers win, then temporal/state markers,
    otherwise unclassified). A state-form claim ("was
    frustrated during debugging") may be recorded as
    history. A trait-form claim ("is an anxious
    personality") is a persona definition attempted from
    memory: it is refused as history, and it may never
    define persona, redefine traits, or override the
    persona — memory is at most a state (§26), however it
    is phrased. An unclassified claim is refused
    fail-closed, like §25.
    """
    verdict = classify_summary_claim(text)
    form = verdict["form"]
    return {
        "form": form,
        "kind": "state",
        "trait_claim_allowed": False,
        "may_record_as_history": form == "state",
        "may_define_persona": False,
        "may_redefine_traits": False,
        "may_override_persona": False,
        "reason_code": verdict["reason_code"],
    }


def memory_claim_authority(evidence_count: Any) -> dict[str, Any]:
    """The authority of a memory claim, however repeated (§41).

    Pure. ``evidence_count`` is how many memories support
    the claim; it must be a non-negative integer (booleans
    refused). Repetition never promotes memory: the tier
    is always long_term_memory at its §24 rank, never
    canonical, and the claim may never redefine traits —
    many conversations involving frustration do not add
    up to a trait.
    """
    if isinstance(evidence_count, bool) \
            or not isinstance(evidence_count, int) \
            or evidence_count < 0:
        raise PersonaRuntimeError("memory evidence count is invalid")
    return {
        "evidence_count": evidence_count,
        "tier": "long_term_memory",
        "rank": _PRECEDENCE_RANK["long_term_memory"],
        "canonical": False,
        "may_redefine_traits": False,
        "may_override_persona": False,
    }


def service_bible_topics() -> list[str]:
    return list(SERVICE_BIBLE_TOPICS)


def service_bible_retrieval_contract() -> dict[str, Any]:
    """The §42 Service Bible dynamic retrieval contract. Pure.

    The Service Bible may become huge: it is not
    continuously injected. Its sections are indexed by
    the roadmap's topic list and retrieved selectively —
    explicit calls only, restricted to the service_bible
    document role, ranked by the §13 hybrid score. This
    layer injects nothing; it names and performs the
    selection a caller may use.
    """
    return {
        "name": "ServiceBibleDynamicRetrieval",
        "role": "service_bible",
        "topics": list(SERVICE_BIBLE_TOPICS),
        "continuously_injected": False,
        "retrieve_selectively": True,
        "retrieval": "explicit_only",
        "injects": False,
    }


def classify_service_topics(text: Any) -> list[str]:
    """The §42 topics a text signals, in roadmap order. Pure.

    A topic is present when any of its lexicon words
    appears as a token in the text. No model call.
    Malformed text is refused.
    """
    if not isinstance(text, str):
        raise PersonaRuntimeError("service bible text is invalid")
    tokens = _tokens(text)
    return [topic for topic, words in _SERVICE_TOPIC_LEXICON
            if tokens & words]


def service_topics_for_section(entry: dict[str, Any]) -> list[str]:
    """A compiled section's §42 topics, in roadmap order. Pure.

    Derived from the section's heading and bare section id
    only — the signals that name what a section is about —
    never authored or stored.
    """
    return classify_service_topics(
        f"{entry['heading']} {entry['section_id']}")


def retrieve_service_bible(index: list[dict[str, Any]],
                           query: str = "",
                           task_text: str | None = None,
                           topic: Any = None,
                           limit: int = RETRIEVAL_DEFAULT_LIMIT
                           ) -> list[dict[str, Any]]:
    """Selectively retrieve Service Bible sections (§42). Pure.

    The compiled index is restricted to the service_bible
    role — no other document's sections are ever returned
    — and ranked by the §13 hybrid retrieval. ``topic``
    optionally names one §42 topic (slugified; unknown
    topics refused): it filters the results to sections
    carrying that topic and, when no query or task text is
    given, supplies the retrieval signal itself. Each
    result is a §13 result (stable id, verbatim text, full
    score breakdown) annotated with its section's §42
    topics. With no signal at all, nothing is retrieved —
    the Bible is never dumped wholesale.
    """
    wanted = None
    if topic is not None:
        if not isinstance(topic, str) or not topic.strip():
            raise PersonaRuntimeError("service bible topic is invalid")
        wanted = _slugify(topic)
        if wanted not in SERVICE_BIBLE_TOPICS:
            raise PersonaRuntimeError("service bible topic is invalid")
    entries = [entry for entry in index
               if entry.get("role") == "service_bible"]
    by_id = {}
    for entry in entries:
        stable = entry.get(
            "stable_id",
            stable_section_id(entry["role"], entry["section_id"]))
        by_id[stable] = entry
    effective_query = query
    if wanted is not None and not (query or "").strip() \
            and task_text is None:
        effective_query = wanted.replace("_", " ")
    results = retrieve_sections(
        entries, query=effective_query, task_text=task_text,
        limit=limit)
    selected = []
    for result in results:
        entry = by_id.get(result["stable_id"])
        topics = service_topics_for_section(entry) \
            if entry is not None else []
        if wanted is not None and wanted not in topics:
            continue
        result = dict(result)
        result["topics"] = topics
        selected.append(result)
    return selected


# --- §43 relationship retrieval + §44 tool policy retrieval ----
#
# §43: relationship context is especially important during
# disagreements, personal conversation, advice, emotionally
# meaningful interaction, and shared-history discussion.
# For routine coding, only the relevant relational anchors
# need to remain in the kernel — the kernel (§9) already
# carries them, so a routine task retrieves nothing
# dynamically. Retrieval here is explicit, deterministic,
# restricted to the relationship role, and reuses §13.
#
# §44: Tool Policy sections are retrieved when actual
# tools are being considered. File reading needs minimal
# or no extra policy; a git force push retrieves the
# force_push / remote_git_operations / reversibility /
# authorization sections. Actions not named by the
# roadmap carry this layer's recorded needs mapping
# (below). This layer executes no tool and injects
# nothing.

# The §43 contexts, in roadmap order (the roadmap's
# phrases slugified).
RELATIONSHIP_CONTEXTS = (
    "disagreement", "personal_conversation", "advice",
    "emotionally_meaningful_interaction",
    "shared_history_discussion",
)

_RELATIONSHIP_CONTEXT_LEXICON = (
    ("disagreement", frozenset({
        "disagreement", "disagreements", "disagree", "disagrees",
        "disagreeing", "conflict", "argument", "dispute",
        "pushback"})),
    ("personal_conversation", frozenset({
        "personal", "private", "intimate"})),
    ("advice", frozenset({
        "advice", "advise", "advises", "counsel", "guidance",
        "recommendation", "recommendations"})),
    ("emotionally_meaningful_interaction", frozenset({
        "emotional", "emotionally", "meaningful", "grief",
        "vulnerable", "heartfelt", "celebration", "celebrates"})),
    ("shared_history_discussion", frozenset({
        "history", "shared", "memories", "memory", "remembered",
        "remembrance", "anniversary", "past"})),
)

# Task tags (§13) that mark routine work, for which §43
# keeps only the kernel's relational anchors.
_ROUTINE_TASK_TAGS = ("coding", "git", "filesystem", "planning")


def relationship_contexts() -> list[str]:
    return list(RELATIONSHIP_CONTEXTS)


def relationship_retrieval_contract() -> dict[str, Any]:
    """The §43 Relationship Model dynamic retrieval contract.

    Pure. Relationship context is retrieved selectively —
    explicit calls only, restricted to the relationship
    document role, ranked by §13 — when the interaction
    is one of the five §43 contexts. For routine coding
    only the relevant relational anchors remain, in the
    §9 kernel; no dynamic retrieval happens and this
    layer injects nothing either way.
    """
    return {
        "name": "RelationshipModelDynamicRetrieval",
        "role": "relationship",
        "contexts": list(RELATIONSHIP_CONTEXTS),
        "continuously_injected": False,
        "retrieve_selectively": True,
        "retrieval": "explicit_only",
        "routine_coding": "kernel_anchors_only",
        "injects": False,
    }


def classify_relationship_contexts(text: Any) -> list[str]:
    """The §43 contexts a text signals, in roadmap order. Pure.

    A context is present when any of its lexicon words
    appears as a token in the text. No model call.
    Malformed text is refused.
    """
    if not isinstance(text, str):
        raise PersonaRuntimeError("relationship text is invalid")
    tokens = _tokens(text)
    return [context for context, words in
            _RELATIONSHIP_CONTEXT_LEXICON if tokens & words]


def relationship_contexts_for_section(
        entry: dict[str, Any]) -> list[str]:
    """A compiled section's §43 contexts, in roadmap order.

    Pure. Derived from the section's heading and bare
    section id only — never authored or stored.
    """
    return classify_relationship_contexts(
        f"{entry['heading']} {entry['section_id']}")


def relationship_retrieval_need(text: Any) -> dict[str, Any]:
    """Whether a task needs dynamic relationship retrieval.

    Pure (§43). A signalled §43 context means dynamic
    retrieval; a routine task tag (§13 coding / git /
    filesystem / planning) with no such context means
    the kernel's relational anchors suffice; anything
    else needs neither.
    """
    if not isinstance(text, str):
        raise PersonaRuntimeError("relationship text is invalid")
    contexts = classify_relationship_contexts(text)
    if contexts:
        return {
            "contexts": contexts,
            "mode": "dynamic_retrieval",
            "dynamic_retrieval": True,
            "kernel_anchors_only": False,
        }
    if set(classify_task(text)) & set(_ROUTINE_TASK_TAGS):
        return {
            "contexts": [],
            "mode": "kernel_anchors_only",
            "dynamic_retrieval": False,
            "kernel_anchors_only": True,
        }
    return {
        "contexts": [],
        "mode": "none",
        "dynamic_retrieval": False,
        "kernel_anchors_only": False,
    }


def retrieve_relationship_model(index: list[dict[str, Any]],
                                query: str = "",
                                task_text: str | None = None,
                                context: Any = None,
                                limit: int = RETRIEVAL_DEFAULT_LIMIT
                                ) -> list[dict[str, Any]]:
    """Selectively retrieve Relationship Model sections (§43).

    Pure. The compiled index is restricted to the
    relationship role and ranked by §13. Retrieval
    happens only for a signalled §43 context: an explicit
    ``context`` (slugified; unknown contexts refused)
    filters the results to sections carrying that context
    and supplies the signal when no query or task text is
    given; contexts may also be signalled by the query or
    task text itself. A section qualifies when its own
    §43 contexts intersect the signalled ones or §13
    retrieval connects it to the signal. With no §43
    context signalled — routine coding included — nothing
    is retrieved: the kernel's relational anchors remain.
    Each result is a §13-shaped result annotated with its
    section's §43 contexts.
    """
    wanted = None
    if context is not None:
        if not isinstance(context, str) or not context.strip():
            raise PersonaRuntimeError(
                "relationship context is invalid")
        wanted = _slugify(context)
        if wanted not in RELATIONSHIP_CONTEXTS:
            raise PersonaRuntimeError(
                "relationship context is invalid")
    signal = " ".join(
        part for part in (query or "", task_text or "") if part)
    signalled = set(classify_relationship_contexts(signal))
    if wanted is not None:
        signalled.add(wanted)
    if not signalled:
        return []
    effective_query = query
    if wanted is not None and not (query or "").strip() \
            and task_text is None:
        effective_query = wanted.replace("_", " ")
    entries = [entry for entry in index
               if entry.get("role") == "relationship"]
    tags_wanted = classify_task(
        task_text if task_text is not None else effective_query)
    try:
        bounded = int(limit)
    except (TypeError, ValueError):
        bounded = RETRIEVAL_DEFAULT_LIMIT
    bounded = max(1, min(RETRIEVAL_MAX_LIMIT, bounded))
    ranked = {
        row["stable_id"]: row for row in retrieve_sections(
            entries, query=effective_query, task_text=task_text,
            limit=RETRIEVAL_MAX_LIMIT)}
    selected = []
    for entry in entries:
        stable = entry.get(
            "stable_id",
            stable_section_id(entry["role"], entry["section_id"]))
        contexts = relationship_contexts_for_section(entry)
        row = ranked.get(stable)
        if not (set(contexts) & signalled) and row is None:
            continue
        if row is None:
            score = retrieval_score(
                entry, query=effective_query,
                task_tags_=tags_wanted)
            row = {
                "stable_id": stable, "role": entry["role"],
                "section_id": entry["section_id"],
                "heading": entry["heading"],
                "priority": float(entry.get("priority", 0.40)),
                "task_tags": list(tags_wanted),
                "tags": section_tags(entry),
                "score": score, "text": entry["text"],
            }
        row = dict(row)
        row["contexts"] = contexts
        selected.append(row)
    selected.sort(
        key=lambda row: (-row["score"]["total"], row["stable_id"]))
    return selected[:bounded]


# The §44 tool actions this layer classifies, in
# precedence order (a force push is classified before the
# general remote-git action it also matches).
TOOL_ACTIONS = (
    "force_push", "file_deletion", "remote_git_operations",
    "file_writing", "shell_execution", "file_reading",
)

# The policy sections each action needs (§44). The
# force_push row is the roadmap's own example and the
# file_reading row its "minimal or no extra policy"
# ruling; the remaining rows are this layer's recorded
# convention, named as such in the contract.
_TOOL_POLICY_NEEDS = {
    "force_push": (
        "force_push", "remote_git_operations", "reversibility",
        "authorization"),
    "file_deletion": (
        "filesystem", "reversibility", "authorization"),
    "remote_git_operations": (
        "remote_git_operations", "authorization"),
    "file_writing": ("filesystem", "authorization"),
    "shell_execution": ("shell_operations", "authorization"),
    "file_reading": (),
}


def tool_actions() -> list[str]:
    return list(TOOL_ACTIONS)


def tool_policy_retrieval_contract() -> dict[str, Any]:
    """The §44 Tool Policy dynamic retrieval contract. Pure.

    Tool Policy sections are retrieved when actual tools
    are being considered — explicit calls only,
    restricted to the tool_policy document role. File
    reading needs minimal or no extra policy; a git
    force push retrieves exactly the roadmap's four
    sections. This layer executes no tool and injects
    nothing.
    """
    return {
        "name": "ToolPolicyDynamicRetrieval",
        "role": "tool_policy",
        "actions": list(TOOL_ACTIONS),
        "needs": {
            action: list(sections)
            for action, sections in _TOOL_POLICY_NEEDS.items()},
        "retrieve_when_tools_considered": True,
        "continuously_injected": False,
        "retrieval": "explicit_only",
        "file_reading_extra_policy": "minimal_or_none",
        "executes_tools": False,
        "injects": False,
    }


def classify_tool_action(text: Any) -> str | None:
    """The §44 tool action a text signals, or None. Pure.

    Deterministic token classification in the precedence
    order of ``TOOL_ACTIONS``: a force push (force +
    push) before remote git operations, deletion before
    writing, writing before shell execution, and file
    reading last (its extra policy is minimal or none).
    No model call. Malformed text is refused.
    """
    if not isinstance(text, str):
        raise PersonaRuntimeError("tool action text is invalid")
    tokens = _tokens(text)
    if {"force", "push"} <= tokens:
        return "force_push"
    if tokens & {"delete", "deleting", "deletion", "remove",
                 "removing", "rm"}:
        return "file_deletion"
    if "git" in tokens and tokens & {
            "push", "pull", "clone", "fetch", "remote", "merge",
            "rebase"}:
        return "remote_git_operations"
    if tokens & {"write", "writing", "edit", "editing", "create",
                 "creating", "save", "saving"}:
        return "file_writing"
    if tokens & {"shell", "bash", "systemd", "terminal",
                 "command", "commands", "execute", "executing"}:
        return "shell_execution"
    if tokens & {"read", "reading", "open", "view", "cat",
                 "inspect", "inspecting"}:
        return "file_reading"
    return None


def tool_policy_needs(text: Any) -> dict[str, Any]:
    """The §44 policy sections a tool consideration needs.

    Pure. Classifies the text's tool action and returns
    its recorded needs: the roadmap's four sections for a
    force push, an empty list for file reading (minimal
    or no extra policy) and for no tool action at all.
    """
    action = classify_tool_action(text)
    sections = list(_TOOL_POLICY_NEEDS.get(action, ()))
    return {
        "action": action,
        "sections": sections,
        "extra_policy_needed": bool(sections),
    }


def retrieve_tool_policy(index: list[dict[str, Any]],
                         query: str = "",
                         task_text: str | None = None,
                         tool_intent: str | None = None,
                         limit: int = RETRIEVAL_DEFAULT_LIMIT
                         ) -> list[dict[str, Any]]:
    """Selectively retrieve Tool Policy sections (§44). Pure.

    The signal (query, task text, and tool intent) is
    classified to one §44 tool action; the compiled index
    is restricted to the tool_policy role and only the
    sections that action needs are returned, ranked by
    the §13 hybrid score and annotated with the action
    and its full needs list. File reading and an
    unclassifiable signal retrieve nothing — minimal or
    no extra policy — and a needed section absent from
    the index is simply not returned.
    """
    signal = " ".join(
        part for part in (query or "", task_text or "",
                          tool_intent or "") if part)
    needs = tool_policy_needs(signal)
    if not needs["sections"]:
        return []
    wanted = set(needs["sections"])
    tags_wanted = classify_task(
        task_text if task_text is not None else signal)
    try:
        bounded = int(limit)
    except (TypeError, ValueError):
        bounded = RETRIEVAL_DEFAULT_LIMIT
    bounded = max(1, min(RETRIEVAL_MAX_LIMIT, bounded))
    selected = []
    for entry in index:
        if entry.get("role") != "tool_policy":
            continue
        if entry["section_id"] not in wanted:
            continue
        stable = entry.get(
            "stable_id",
            stable_section_id(entry["role"], entry["section_id"]))
        score = retrieval_score(
            entry, query=signal, task_tags_=tags_wanted)
        selected.append({
            "stable_id": stable, "role": entry["role"],
            "section_id": entry["section_id"],
            "heading": entry["heading"],
            "priority": float(entry.get("priority", 0.40)),
            "task_tags": list(tags_wanted),
            "tags": section_tags(entry),
            "score": score, "text": entry["text"],
            "action": needs["action"],
            "policy_sections": list(needs["sections"]),
        })
    selected.sort(
        key=lambda row: (-row["score"]["total"], row["stable_id"]))
    return selected[:bounded]


# --- §45 memory policy usage + §46 avatar policy usage ----
#
# §45: the model normally does not need the entire Memory
# Policy in context — the memory subsystem itself
# implements it. Policy text is retrieved only when
# resolving memory conflicts, deciding promotion,
# performing reflection, or explaining memory decisions,
# and behavior should move into code wherever practical.
#
# §46: the Avatar file rarely belongs in ordinary text
# inference. It is retrieved only when generating images,
# controlling the avatar, describing the persona,
# selecting expressions, or in VR interaction; the avatar
# controller can consume structured AvatarIR directly.

# The §45 occasions, in roadmap order (the roadmap's
# phrases slugified).
MEMORY_POLICY_OCCASIONS = (
    "resolving_memory_conflicts", "deciding_promotion",
    "performing_reflection", "explaining_memory_decisions",
)

_MEMORY_POLICY_OCCASION_LEXICON = (
    ("resolving_memory_conflicts", frozenset({
        "conflict", "conflicts", "conflicting", "resolve",
        "resolves", "resolving", "resolution", "contradiction",
        "contradictions", "contradictory"})),
    ("deciding_promotion", frozenset({
        "promotion", "promote", "promotes", "promoted",
        "promoting"})),
    ("performing_reflection", frozenset({
        "reflection", "reflections", "reflect", "reflects",
        "reflecting"})),
    ("explaining_memory_decisions", frozenset({
        "explain", "explains", "explaining", "explanation",
        "explanations", "justify", "justifying"})),
)

# The §46 occasions, in roadmap order (the roadmap's
# phrases slugified; "describing Caducea" is the persona
# description occasion).
AVATAR_POLICY_OCCASIONS = (
    "generating_images", "controlling_avatar",
    "describing_persona", "selecting_expressions",
    "vr_interaction",
)

_AVATAR_OCCASION_LEXICON = (
    ("generating_images", frozenset({
        "image", "images", "picture", "pictures", "portrait",
        "portraits", "generate", "generates", "generating",
        "render", "renders", "rendering", "illustration",
        "illustrations"})),
    ("controlling_avatar", frozenset({
        "control", "controls", "controlling", "controlled",
        "move", "moves", "moving", "pose", "poses"})),
    ("describing_persona", frozenset({
        "describe", "describes", "describing", "description",
        "appearance", "look", "looks"})),
    ("selecting_expressions", frozenset({
        "expression", "expressions", "facial", "select",
        "selects", "selecting", "selection"})),
    ("vr_interaction", frozenset({
        "vr", "virtual", "reality", "headset", "immersive"})),
)


def memory_policy_occasions() -> list[str]:
    return list(MEMORY_POLICY_OCCASIONS)


def memory_policy_usage_contract() -> dict[str, Any]:
    """The §45 Memory Policy usage contract. Pure.

    The model normally does not need the entire Memory
    Policy in context: the memory subsystem itself
    implements it. Policy text is retrieved selectively —
    explicit calls only, restricted to the memory_policy
    document role — only on one of the four §45 occasions,
    and behavior should move into code wherever practical.
    This layer injects nothing and implements no memory
    subsystem; it names and performs the selection.
    """
    return {
        "name": "MemoryPolicyUsage",
        "role": "memory_policy",
        "occasions": list(MEMORY_POLICY_OCCASIONS),
        "normally_needed_in_context": False,
        "implemented_by": "memory_subsystem",
        "retrieve_only_on_occasion": True,
        "behavior_in_code_where_practical": True,
        "continuously_injected": False,
        "retrieval": "explicit_only",
        "injects": False,
    }


def classify_memory_policy_occasions(text: Any) -> list[str]:
    """The §45 occasions a text signals, in roadmap order.

    Pure. An occasion is present when any of its lexicon
    words appears as a token in the text. No model call.
    Malformed text is refused.
    """
    if not isinstance(text, str):
        raise PersonaRuntimeError(
            "memory policy text is invalid")
    tokens = _tokens(text)
    return [occasion for occasion, words in
            _MEMORY_POLICY_OCCASION_LEXICON if tokens & words]


def memory_policy_occasions_for_section(
        entry: dict[str, Any]) -> list[str]:
    """A compiled section's §45 occasions, in roadmap order.

    Pure. Derived from the section's heading and bare
    section id only — never authored or stored.
    """
    return classify_memory_policy_occasions(
        f"{entry['heading']} {entry['section_id']}")


def memory_policy_retrieval_need(text: Any) -> dict[str, Any]:
    """Whether a task needs Memory Policy text (§45). Pure.

    A signalled §45 occasion means selective retrieval;
    anything else means the memory subsystem implements
    the policy on its own and no policy text is needed.
    """
    if not isinstance(text, str):
        raise PersonaRuntimeError(
            "memory policy text is invalid")
    occasions = classify_memory_policy_occasions(text)
    if occasions:
        return {
            "occasions": occasions,
            "mode": "selective_retrieval",
            "dynamic_retrieval": True,
            "subsystem_only": False,
        }
    return {
        "occasions": [],
        "mode": "subsystem_only",
        "dynamic_retrieval": False,
        "subsystem_only": True,
    }


def _retrieve_on_occasions(index: list[dict[str, Any]],
                           role: str,
                           occasions_for_section,
                           classify_occasions,
                           valid_occasions: tuple[str, ...],
                           error_label: str,
                           query: str = "",
                           task_text: str | None = None,
                           occasion: Any = None,
                           limit: int = RETRIEVAL_DEFAULT_LIMIT
                           ) -> list[dict[str, Any]]:
    """Shared selective retrieval for §§45–46. Pure.

    Restricted to ``role`` and ranked by §13. Retrieval
    happens only for a signalled occasion: an explicit
    ``occasion`` (slugified; unknown occasions refused)
    filters the results to sections carrying it and
    supplies the signal when no query or task text is
    given; occasions may also be signalled by the query
    or task text itself. A section qualifies only when
    its own occasions intersect the signalled ones — the
    occasion is the index, so a merely §13-adjacent
    section is not retrieved. With no occasion signalled,
    nothing is retrieved. Each result is a §13-shaped
    result annotated with its section's occasions.
    """
    wanted = None
    if occasion is not None:
        if not isinstance(occasion, str) or not occasion.strip():
            raise PersonaRuntimeError(f"{error_label} is invalid")
        wanted = _slugify(occasion)
        if wanted not in valid_occasions:
            raise PersonaRuntimeError(f"{error_label} is invalid")
    signal = " ".join(
        part for part in (query or "", task_text or "") if part)
    signalled = set(classify_occasions(signal))
    if wanted is not None:
        signalled.add(wanted)
    if not signalled:
        return []
    effective_query = query
    if wanted is not None and not (query or "").strip() \
            and task_text is None:
        effective_query = wanted.replace("_", " ")
    entries = [entry for entry in index
               if entry.get("role") == role]
    tags_wanted = classify_task(
        task_text if task_text is not None else effective_query)
    try:
        bounded = int(limit)
    except (TypeError, ValueError):
        bounded = RETRIEVAL_DEFAULT_LIMIT
    bounded = max(1, min(RETRIEVAL_MAX_LIMIT, bounded))
    ranked = {
        row["stable_id"]: row for row in retrieve_sections(
            entries, query=effective_query, task_text=task_text,
            limit=RETRIEVAL_MAX_LIMIT)}
    selected = []
    for entry in entries:
        stable = entry.get(
            "stable_id",
            stable_section_id(entry["role"], entry["section_id"]))
        occasions = occasions_for_section(entry)
        row = ranked.get(stable)
        if not (set(occasions) & signalled):
            continue
        if row is None:
            score = retrieval_score(
                entry, query=effective_query,
                task_tags_=tags_wanted)
            row = {
                "stable_id": stable, "role": entry["role"],
                "section_id": entry["section_id"],
                "heading": entry["heading"],
                "priority": float(entry.get("priority", 0.40)),
                "task_tags": list(tags_wanted),
                "tags": section_tags(entry),
                "score": score, "text": entry["text"],
            }
        row = dict(row)
        row["occasions"] = occasions
        selected.append(row)
    selected.sort(
        key=lambda row: (-row["score"]["total"], row["stable_id"]))
    return selected[:bounded]


def retrieve_memory_policy(index: list[dict[str, Any]],
                           query: str = "",
                           task_text: str | None = None,
                           occasion: Any = None,
                           limit: int = RETRIEVAL_DEFAULT_LIMIT
                           ) -> list[dict[str, Any]]:
    """Selectively retrieve Memory Policy sections (§45).

    Pure. Restricted to the memory_policy role; with no
    §45 occasion signalled, nothing is retrieved — the
    memory subsystem implements the policy on its own.
    """
    return _retrieve_on_occasions(
        index, "memory_policy", memory_policy_occasions_for_section,
        classify_memory_policy_occasions, MEMORY_POLICY_OCCASIONS,
        "memory policy occasion", query=query,
        task_text=task_text, occasion=occasion, limit=limit)


def avatar_policy_occasions() -> list[str]:
    return list(AVATAR_POLICY_OCCASIONS)


def avatar_policy_usage_contract() -> dict[str, Any]:
    """The §46 Avatar Policy usage contract. Pure.

    The Avatar file rarely belongs in ordinary text
    inference: it is retrieved selectively — explicit
    calls only, restricted to the avatar document role —
    only on one of the five §46 occasions. The avatar
    controller can consume structured AvatarIR directly;
    this layer owns no avatar controller and injects
    nothing.
    """
    return {
        "name": "AvatarPolicyUsage",
        "role": "avatar",
        "occasions": list(AVATAR_POLICY_OCCASIONS),
        "rarely_in_ordinary_text_inference": True,
        "retrieve_only_on_occasion": True,
        "avatar_controller_consumes": "AvatarIR",
        "avatar_controller_direct_ir": True,
        "continuously_injected": False,
        "retrieval": "explicit_only",
        "injects": False,
    }


def classify_avatar_occasions(text: Any) -> list[str]:
    """The §46 occasions a text signals, in roadmap order.

    Pure. An occasion is present when any of its lexicon
    words appears as a token in the text. No model call.
    Malformed text is refused.
    """
    if not isinstance(text, str):
        raise PersonaRuntimeError("avatar text is invalid")
    tokens = _tokens(text)
    return [occasion for occasion, words in
            _AVATAR_OCCASION_LEXICON if tokens & words]


def avatar_occasions_for_section(
        entry: dict[str, Any]) -> list[str]:
    """A compiled section's §46 occasions, in roadmap order.

    Pure. Derived from the section's heading and bare
    section id only — never authored or stored.
    """
    return classify_avatar_occasions(
        f"{entry['heading']} {entry['section_id']}")


def avatar_retrieval_need(text: Any) -> dict[str, Any]:
    """Whether a task needs Avatar sections (§46). Pure.

    A signalled §46 occasion means selective retrieval;
    anything else is ordinary text inference, where the
    Avatar file rarely belongs.
    """
    if not isinstance(text, str):
        raise PersonaRuntimeError("avatar text is invalid")
    occasions = classify_avatar_occasions(text)
    if occasions:
        return {
            "occasions": occasions,
            "mode": "selective_retrieval",
            "dynamic_retrieval": True,
            "ordinary_text_inference": False,
        }
    return {
        "occasions": [],
        "mode": "not_in_ordinary_inference",
        "dynamic_retrieval": False,
        "ordinary_text_inference": True,
    }


def retrieve_avatar_policy(index: list[dict[str, Any]],
                           query: str = "",
                           task_text: str | None = None,
                           occasion: Any = None,
                           limit: int = RETRIEVAL_DEFAULT_LIMIT
                           ) -> list[dict[str, Any]]:
    """Selectively retrieve Avatar sections (§46). Pure.

    Restricted to the avatar role; with no §46 occasion
    signalled, nothing is retrieved — the Avatar file
    stays out of ordinary text inference.
    """
    return _retrieve_on_occasions(
        index, "avatar", avatar_occasions_for_section,
        classify_avatar_occasions, AVATAR_POLICY_OCCASIONS,
        "avatar occasion", query=query, task_text=task_text,
        occasion=occasion, limit=limit)


# --- §47 policy-to-code migration + §48 compilation cache ----
#
# §47: over time, move deterministic rules out of prompts
# into code. Prompt instructions should primarily govern
# personality, judgment, relational behavior, and nuanced
# cognition; code should govern expiration, permissions,
# limits, routing, formatting, and deterministic
# constraints. The roadmap's example: instead of telling
# the model "Never include expired memories.", implement
# ``if memory.expired: exclude()``.
#
# §48: compile once, and cache the generated artefacts
# (persona_kernel.txt, persona_ir.json,
# persona_sections.jsonl, persona_embeddings.db,
# persona_manifest.json). These are generated artifacts;
# humans edit only Markdown + YAML configuration.

# The §47 prompt-governed rule kinds, in roadmap order
# (the roadmap's phrases slugified).
PROMPT_GOVERNS = (
    "personality", "judgment", "relational_behavior",
    "nuanced_cognition",
)

_PROMPT_GOVERNS_LEXICON = (
    ("personality", frozenset({
        "personality", "persona", "character", "trait",
        "traits"})),
    ("judgment", frozenset({
        "judgment", "judgement", "discern", "discerns",
        "discernment", "discretion", "discretionary",
        "wisdom", "wise"})),
    ("relational_behavior", frozenset({
        "relational", "relationship", "relationships",
        "rapport", "trust", "empathy", "empathic",
        "interpersonal"})),
    ("nuanced_cognition", frozenset({
        "nuanced", "nuance", "nuances", "subtle",
        "subtlety", "ambiguity", "ambiguous"})),
)

# The §47 code-governed rule kinds, in roadmap order.
CODE_GOVERNS = (
    "expiration", "permissions", "limits", "routing",
    "formatting", "deterministic_constraints",
)

_CODE_GOVERNS_LEXICON = (
    ("expiration", frozenset({
        "expiration", "expire", "expires", "expired",
        "expiring", "expiry", "ttl"})),
    ("permissions", frozenset({
        "permission", "permissions", "permitted", "permit",
        "permits", "authorization", "authorised",
        "authorized", "allowed", "disallowed"})),
    ("limits", frozenset({
        "limit", "limits", "limited", "limiting", "cap",
        "caps", "quota", "quotas", "maximum"})),
    ("routing", frozenset({
        "routing", "route", "routes", "routed", "router",
        "dispatch", "dispatches"})),
    ("formatting", frozenset({
        "formatting", "format", "formats", "formatted",
        "layout", "whitespace"})),
    ("deterministic_constraints", frozenset({
        "deterministic", "constraint", "constraints",
        "invariant", "invariants"})),
)


def policy_governs() -> list[str]:
    return list(PROMPT_GOVERNS)


def code_governs() -> list[str]:
    return list(CODE_GOVERNS)


def policy_to_code_contract() -> dict[str, Any]:
    """The §47 policy-to-code migration contract. Pure.

    Over time, deterministic rules move out of prompts
    into code: prompt instructions primarily govern
    personality, judgment, relational behavior, and
    nuanced cognition, while code governs expiration,
    permissions, limits, routing, formatting, and
    deterministic constraints. This layer migrates no
    live prompt and owns no prompts; it names which
    domain governs each rule kind.
    """
    return {
        "name": "PolicyToCodeMigration",
        "prompt_governs": list(PROMPT_GOVERNS),
        "code_governs": list(CODE_GOVERNS),
        "migration_direction": "prompt_to_code",
        "migrates": "deterministic_rules",
        "example": {
            "prompt_instruction":
                "Never include expired memories.",
            "code_rule": "if memory.expired: exclude()",
        },
        "migrates_live_prompts": False,
        "owns_prompts": False,
        "injects": False,
    }


def classify_rule_kinds(text: Any) -> list[str]:
    """The §47 rule kinds a text signals. Pure.

    Prompt-governed kinds come first, in roadmap order,
    then code-governed kinds, in roadmap order. A kind is
    present when any of its lexicon words appears as a
    token in the text. No model call. Malformed text is
    refused.
    """
    if not isinstance(text, str):
        raise PersonaRuntimeError("rule text is invalid")
    tokens = _tokens(text)
    kinds = [kind for kind, words in _PROMPT_GOVERNS_LEXICON
             if tokens & words]
    kinds += [kind for kind, words in _CODE_GOVERNS_LEXICON
              if tokens & words]
    return kinds


def governance_for_kind(kind: Any) -> str:
    """Which domain governs one §47 rule kind. Pure.

    The kind is slugified, so "Relational Behavior" and
    "relational_behavior" name the same kind; an unknown
    kind is refused.
    """
    if not isinstance(kind, str) or not kind.strip():
        raise PersonaRuntimeError("rule kind is invalid")
    slug = _slugify(kind)
    if slug in PROMPT_GOVERNS:
        return "prompt"
    if slug in CODE_GOVERNS:
        return "code"
    raise PersonaRuntimeError("rule kind is invalid")


def migration_assessment(text: Any) -> dict[str, Any]:
    """Assess one rule text under §47. Pure.

    Names the kinds the text signals, split by governing
    domain; a text is a migration candidate exactly when
    it signals a code-governed kind — a deterministic
    rule still standing in prompt form.
    """
    kinds = classify_rule_kinds(text)
    prompt_kinds = [kind for kind in kinds
                    if kind in PROMPT_GOVERNS]
    code_kinds = [kind for kind in kinds if kind in CODE_GOVERNS]
    if prompt_kinds and code_kinds:
        governed_by = "mixed"
    elif code_kinds:
        governed_by = "code"
    elif prompt_kinds:
        governed_by = "prompt"
    else:
        governed_by = "unclassified"
    return {
        "kinds": kinds,
        "prompt_governed_kinds": prompt_kinds,
        "code_governed_kinds": code_kinds,
        "migration_candidate": bool(code_kinds),
        "governed_by": governed_by,
    }


# The §48 cache artefacts, in roadmap order: the cache
# file name paired with its artefact kind.
CACHE_ARTIFACTS = (
    ("persona_kernel.txt", "kernel"),
    ("persona_ir.json", "ir"),
    ("persona_sections.jsonl", "sections"),
    ("persona_embeddings.db", "embeddings"),
    ("persona_manifest.json", "manifest"),
)

# The §48 embeddings honesty note: §13 records the
# semantic component as unavailable because this plugin
# owns no embedding surface, so the embeddings artefact
# carries no hash in a manifest this layer builds.
EMBEDDINGS_HASH_NOTE = (
    "embeddings hash is None: this layer owns no "
    "embedding surface (§13), so no embeddings hash is "
    "recorded or faked")

# The §48 manifest's fields, in stored order.
CACHE_MANIFEST_FIELDS = (
    "persona_id", "persona_version", "compiled_at",
    "artifacts", "embeddings_note",
)

_CACHE_ARTIFACT_KINDS = tuple(kind for _, kind in CACHE_ARTIFACTS)
_CACHE_ARTIFACT_FILES = {
    kind: file for file, kind in CACHE_ARTIFACTS}


def compilation_cache_artifacts() -> list[dict[str, Any]]:
    """The §48 cache artefacts, in roadmap order. Pure.

    Every artefact is generated (``generated: True``) —
    none is human-edited; humans edit only the Markdown
    documents and the YAML configuration they compile
    from.
    """
    return [
        {"file": file, "kind": kind, "generated": True}
        for file, kind in CACHE_ARTIFACTS]


def compilation_cache_contract() -> dict[str, Any]:
    """The §48 Persona Compilation Cache contract. Pure.

    Compile once; the cache artefacts are generated, and
    humans edit only Markdown + YAML configuration. This
    layer persists and writes no cache; it names the
    artefact set and the manifest/validity shape over a
    compiled artefact.
    """
    return {
        "name": "PersonaCompilationCache",
        "artifacts": compilation_cache_artifacts(),
        "compile_once": True,
        "artifacts_are_generated": True,
        "humans_edit": ["markdown", "yaml_configuration"],
        "persists_cache": False,
        "writes_cache": False,
        "injects": False,
    }


def _sections_digest(index: list[dict[str, Any]]) -> str:
    """A deterministic sha256 over the compiled index.

    The digest covers the canonical JSON of each entry's
    stable id, role, section id, heading, and verbatim
    text, in index order — identical compiles digest
    identically, and any section change moves it.
    """
    payload = json.dumps(
        [{
            "stable_id": entry.get("stable_id"),
            "role": entry.get("role"),
            "section_id": entry.get("section_id"),
            "heading": entry.get("heading"),
            "text": entry.get("text"),
        } for entry in index],
        sort_keys=True, separators=(",", ":"),
        ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _cache_artifact_hashes(
        compiled: dict[str, Any]) -> dict[str, Any]:
    """The §48 per-artefact hashes for one compile. Pure.

    Kernel and manifest hashes come from the §19 hash
    record (the kernel sha256 and the combined persona
    hash); the IR hash is the artefact's own §8
    ``ir_hash``; the sections hash is the deterministic
    digest over the compiled index. The embeddings hash
    is None — this layer owns no embedding surface (§13).
    A malformed compiled artefact is refused.
    """
    record = hash_record(compiled)
    ir = compiled.get("ir")
    index = compiled.get("index")
    if not isinstance(ir, dict) \
            or not isinstance(ir.get("ir_hash"), str) \
            or not isinstance(index, list) \
            or not all(isinstance(entry, dict) for entry in index):
        raise PersonaRuntimeError("compiled persona is invalid")
    return {
        "kernel": record["kernel_hash"],
        "ir": ir["ir_hash"],
        "sections": _sections_digest(index),
        "embeddings": None,
        "manifest": record["persona_hash"],
    }


def cache_manifest(compiled: dict[str, Any],
                   compiled_at: str | None = None) -> dict[str, Any]:
    """The §48 cache manifest for one compiled artefact.

    Pure and deterministic for a given artefact: built
    on the §19 hash record, so ``compiled_at`` stays
    None unless a caller explicitly stamps a
    timezone-aware ISO timestamp (the §19 stamp
    handling), and a stamp alone is never a change.
    Each artefact is named with its §48 file, kind,
    generated flag, and hash; the embeddings hash is
    None, honestly (see ``EMBEDDINGS_HASH_NOTE``). This
    layer writes no manifest to disk.
    """
    record = hash_record(compiled, compiled_at=compiled_at)
    hashes = _cache_artifact_hashes(compiled)
    return {
        "persona_id": record["persona_id"],
        "persona_version": record["persona_version"],
        "compiled_at": record["compiled_at"],
        "artifacts": [
            {"file": file, "kind": kind, "generated": True,
             "sha256": hashes[kind]}
            for file, kind in CACHE_ARTIFACTS],
        "embeddings_note": EMBEDDINGS_HASH_NOTE,
    }


def _validate_cache_manifest(manifest: Any) -> dict[str, Any]:
    """Normalise one §48 cache manifest, refusing bad shapes.

    The manifest must carry exactly the §48 fields; each
    artefact entry must name a §48 file/kind pair, be
    generated, and carry a hash string — except the
    embeddings entry, whose hash must be None. A kind
    may be absent (staleness reports it as missing); a
    duplicated or unknown kind is malformed. Returns a
    fresh manifest with entries in roadmap order.
    """
    if not isinstance(manifest, dict) \
            or set(manifest) != set(CACHE_MANIFEST_FIELDS):
        raise PersonaRuntimeError(
            "persona cache manifest is invalid")
    persona_id = manifest["persona_id"]
    if not isinstance(persona_id, str) or not persona_id \
            or manifest["persona_version"] != PERSONA_CONFIG_VERSION \
            or not isinstance(manifest["embeddings_note"], str) \
            or not manifest["embeddings_note"]:
        raise PersonaRuntimeError(
            "persona cache manifest is invalid")
    if manifest["compiled_at"] is not None:
        _validate_compiled_at(manifest["compiled_at"])
    raw = manifest["artifacts"]
    if not isinstance(raw, list) or len(raw) > len(CACHE_ARTIFACTS):
        raise PersonaRuntimeError(
            "persona cache manifest is invalid")
    entries: dict[str, dict[str, Any]] = {}
    for entry in raw:
        if not isinstance(entry, dict) \
                or set(entry) != {"file", "kind", "generated",
                                  "sha256"}:
            raise PersonaRuntimeError(
                "persona cache manifest is invalid")
        kind = entry["kind"]
        if kind not in _CACHE_ARTIFACT_KINDS \
                or entry["file"] != _CACHE_ARTIFACT_FILES[kind] \
                or entry["generated"] is not True \
                or kind in entries:
            raise PersonaRuntimeError(
                "persona cache manifest is invalid")
        digest = entry["sha256"]
        if kind == "embeddings":
            if digest is not None:
                raise PersonaRuntimeError(
                    "persona cache manifest is invalid")
        elif not isinstance(digest, str) or not digest:
            raise PersonaRuntimeError(
                "persona cache manifest is invalid")
        entries[kind] = {
            "file": entry["file"], "kind": kind,
            "generated": True, "sha256": digest}
    return {
        "persona_id": persona_id,
        "persona_version": manifest["persona_version"],
        "compiled_at": manifest["compiled_at"],
        "artifacts": [entries[kind] for _, kind in CACHE_ARTIFACTS
                      if kind in entries],
        "embeddings_note": manifest["embeddings_note"],
    }


def cache_staleness(manifest: Any,
                    compiled: dict[str, Any]) -> dict[str, Any]:
    """Compare a §48 cache manifest against a compile. Pure.

    Recomputes the per-artefact hashes from the compiled
    artefact and names exactly which artefact kinds
    changed and which are missing from the manifest.
    ``compiled_at`` is a caller stamp, not persona
    material (§19): a stamp difference alone is never
    staleness. A malformed manifest or compiled artefact
    is refused.
    """
    manifest = _validate_cache_manifest(manifest)
    hashes = _cache_artifact_hashes(compiled)
    present = {entry["kind"]: entry["sha256"]
               for entry in manifest["artifacts"]}
    changed = [kind for _, kind in CACHE_ARTIFACTS
               if kind in present and present[kind] != hashes[kind]]
    missing = [kind for _, kind in CACHE_ARTIFACTS
               if kind not in present]
    return {
        "valid": not changed and not missing
        and manifest["persona_id"] == compiled["persona_id"],
        "changed": changed,
        "missing": missing,
    }


def validate_cache_manifest(manifest: Any,
                            compiled: dict[str, Any]) -> bool:
    """Whether a §48 cache manifest still matches a compile.

    Pure. Returns False — never raises — when an artefact
    hash disagrees, an artefact is missing, or the
    manifest names another persona; raises only on a
    malformed manifest or compiled artefact shape, in
    the neighbouring validators' convention.
    """
    return cache_staleness(manifest, compiled)["valid"]


# --- §49 generated directory + §50 manifest ------------------
#
# §49: the recommended generated layout is ``persona/``
# holding a ``source/`` directory with the six authored
# Caducea documents and a ``.compiled/`` directory with
# the generated artefacts (persona_ir.json,
# persona_kernel.txt, sections.jsonl, embeddings.db,
# manifest.json); ``.compiled/`` can be regenerated at
# any time. Note the §49 compiled names differ from the
# §48 cache names for two artefacts (sections.jsonl, not
# persona_sections.jsonl; manifest.json, not
# persona_manifest.json) — both namings are recorded as
# their own sections stand them.
#
# §50: the manifest names the persona id, its version,
# the compile stamp, the documents by role with each
# document's file and hash, and the kernel hash. The
# per-document file+hash entries are the genuine gap
# §49/§50 add over the §48 cache manifest, whose
# documents stand only as artefact kinds.

# The §49 source documents, in roadmap order: the
# semantic role paired with its roadmap file name.
GENERATED_SOURCE_DOCUMENTS = (
    ("core", "CADUCEA_PERSONA_CORE.md"),
    ("service_bible", "CADUCEA_SERVICE_BIBLE.md"),
    ("memory_policy", "CADUCEA_MEMORY_POLICY.md"),
    ("tool_policy", "CADUCEA_TOOL_POLICY.md"),
    ("relationship", "CADUCEA_RELATIONSHIP_MODEL.md"),
    ("avatar", "CADUCEA_AVATAR.md"),
)

# The §49 compiled artefacts, in roadmap order: the
# file name paired with its artefact kind.
GENERATED_COMPILED_ARTIFACTS = (
    ("persona_ir.json", "ir"),
    ("persona_kernel.txt", "kernel"),
    ("sections.jsonl", "sections"),
    ("embeddings.db", "embeddings"),
    ("manifest.json", "manifest"),
)

GENERATED_ROOT = "persona"
GENERATED_SOURCE_DIR = "source"
GENERATED_COMPILED_DIR = ".compiled"

# The §50 manifest's fields, in the roadmap's order.
MANIFEST_FIELDS = (
    "persona_id", "version", "compiled_at", "documents",
    "kernel_hash",
)

# The §50 per-document entry's fields, in roadmap order.
MANIFEST_DOCUMENT_FIELDS = ("file", "hash")


def generated_source_documents() -> list[dict[str, Any]]:
    """The §49 source documents, in roadmap order. Pure.

    Each entry names its semantic role, its roadmap file
    name, and its path under ``persona/source/``. These
    are the human-authored documents; the runtime cares
    about roles, not filenames (§3) — the names here are
    the roadmap's recommended layout, not a requirement
    this layer enforces on a compile.
    """
    return [
        {"role": role, "file": file,
         "path": f"{GENERATED_SOURCE_DIR}/{file}"}
        for role, file in GENERATED_SOURCE_DOCUMENTS]


def generated_compiled_artifacts() -> list[dict[str, Any]]:
    """The §49 compiled artefacts, in roadmap order. Pure.

    Every artefact is generated (``generated: True``) —
    none is human-edited — and each names its path under
    ``persona/.compiled/``.
    """
    return [
        {"file": file, "kind": kind,
         "path": f"{GENERATED_COMPILED_DIR}/{file}",
         "generated": True}
        for file, kind in GENERATED_COMPILED_ARTIFACTS]


def generated_directory_layout() -> dict[str, Any]:
    """The §49 recommended generated directory. Pure.

    ``persona/source/`` holds the authored documents and
    ``persona/.compiled/`` the generated artefacts, and
    ``.compiled/`` can be regenerated at any time. This
    layer creates no directory and writes no file; it
    names the layout only.
    """
    return {
        "root": GENERATED_ROOT,
        "source_directory": GENERATED_SOURCE_DIR,
        "compiled_directory": GENERATED_COMPILED_DIR,
        "source_documents": generated_source_documents(),
        "compiled_artifacts": generated_compiled_artifacts(),
        "compiled_regenerable": True,
    }


def generated_directory_contract() -> dict[str, Any]:
    """The §49 Generated Directory contract. Pure."""
    return {
        "name": "PersonaGeneratedDirectory",
        **generated_directory_layout(),
        "creates_directory": False,
        "writes_files": False,
        "injects": False,
    }


def manifest(compiled: dict[str, Any],
             compiled_at: str | None = None) -> dict[str, Any]:
    """The §50 manifest for one compiled artefact. Pure.

    Built on the §19 hash record and the §22 per-persona
    version: persona id, version, an explicit caller
    stamp or None (the §19 stamp handling — a stamp
    alone is never a change), the documents by role in
    document order, each with its file and its sha256
    hash, and the kernel hash. Deterministic for a given
    artefact; this layer writes no manifest to disk.
    A malformed compiled artefact is refused.
    """
    record = hash_record(compiled, compiled_at=compiled_at)
    documents: dict[str, dict[str, str]] = {}
    for document in compiled["documents"]:
        if not isinstance(document, dict) \
                or not isinstance(document.get("file"), str) \
                or not document["file"]:
            raise PersonaRuntimeError("compiled persona is invalid")
        role = document["role"]
        documents[role] = {
            "file": document["file"],
            "hash": record["document_hashes"][role],
        }
    return {
        "persona_id": record["persona_id"],
        "version": _compiled_version(compiled),
        "compiled_at": record["compiled_at"],
        "documents": documents,
        "kernel_hash": record["kernel_hash"],
    }


def _validate_manifest(manifest_value: Any) -> dict[str, Any]:
    """Normalise one §50 manifest, refusing bad shapes.

    The manifest must carry exactly the §50 fields; the
    version must be strict §22 semver; each document
    entry must carry exactly a file and a hash, both
    non-empty strings. Returns a fresh manifest with
    documents in their stored order.
    """
    if not isinstance(manifest_value, dict) \
            or set(manifest_value) != set(MANIFEST_FIELDS):
        raise PersonaRuntimeError("persona manifest is invalid")
    if not isinstance(manifest_value["persona_id"], str) \
            or not manifest_value["persona_id"] \
            or not isinstance(manifest_value["kernel_hash"], str) \
            or not manifest_value["kernel_hash"]:
        raise PersonaRuntimeError("persona manifest is invalid")
    parse_persona_version(manifest_value["version"])
    if manifest_value["compiled_at"] is not None:
        _validate_compiled_at(manifest_value["compiled_at"])
    raw = manifest_value["documents"]
    if not isinstance(raw, dict) or not raw:
        raise PersonaRuntimeError("persona manifest is invalid")
    documents: dict[str, dict[str, str]] = {}
    for role, entry in raw.items():
        if not isinstance(role, str) or not role \
                or not isinstance(entry, dict) \
                or set(entry) != set(MANIFEST_DOCUMENT_FIELDS) \
                or not isinstance(entry["file"], str) \
                or not entry["file"] \
                or not isinstance(entry["hash"], str) \
                or not entry["hash"]:
            raise PersonaRuntimeError("persona manifest is invalid")
        documents[role] = {"file": entry["file"],
                           "hash": entry["hash"]}
    return {
        "persona_id": manifest_value["persona_id"],
        "version": manifest_value["version"],
        "compiled_at": manifest_value["compiled_at"],
        "documents": documents,
        "kernel_hash": manifest_value["kernel_hash"],
    }


def manifest_staleness(manifest_value: Any,
                       compiled: dict[str, Any]) -> dict[str, Any]:
    """Compare a §50 manifest against a compile. Pure.

    Recomputes the expected manifest from the compiled
    artefact and names exactly which document roles
    changed (file or hash) and which are missing from
    the manifest; a kernel-hash, version, or persona-id
    disagreement is named in ``changed`` as its field.
    ``compiled_at`` is a caller stamp, not persona
    material (§19): a stamp difference alone is never
    staleness. A malformed manifest or compiled artefact
    is refused.
    """
    checked = _validate_manifest(manifest_value)
    expected = manifest(compiled)
    present = checked["documents"]
    wanted = expected["documents"]
    changed = [role for role in wanted
               if role in present and present[role] != wanted[role]]
    if checked["kernel_hash"] != expected["kernel_hash"]:
        changed.append("kernel_hash")
    if checked["version"] != expected["version"]:
        changed.append("version")
    if checked["persona_id"] != expected["persona_id"]:
        changed.append("persona_id")
    missing = [role for role in wanted if role not in present]
    return {
        "valid": not changed and not missing,
        "changed": changed,
        "missing": missing,
    }


def validate_manifest(manifest_value: Any,
                      compiled: dict[str, Any]) -> bool:
    """Whether a §50 manifest still matches a compile.

    Pure. Returns False — never raises — when a document
    file or hash disagrees, a document is missing, or
    the kernel hash, version, or persona id disagrees;
    raises only on a malformed manifest or compiled
    artefact shape, in the neighbouring validators'
    convention.
    """
    return manifest_staleness(manifest_value, compiled)["valid"]


# --- §51 startup sequence + §52 request pipeline -------------
#
# §51: Hermes startup walks a fixed order — load
# persona.yaml, resolve the persona directory, validate
# the required documents, compare source hashes, then
# load the compiled persona when the hashes are
# unchanged or compile the persona when they changed (or
# none was compiled before), load the Persona Kernel,
# initialize the retrieval index, initialize Persona
# State, and the persona awakens. The branch is a pure
# function of the §19 hash records of the previously
# compiled artefact and the current one; this layer owns
# no boot hook, starts nothing, and requires no restart.
#
# §52: each interaction walks ten stages — user message,
# task classifier (naming task type, entities, project,
# and tool intent), persona router, persona retrieval,
# memory retrieval, context budgeter, prompt assembler,
# model, persona watchdog, tools / response. Most stages
# have a banked owner surface in this plugin; memory
# retrieval belongs to the memory subsystem, the model
# stage to the model, and prompt assembly's owner is
# the §53 pure order surface below — no stage runs.

# The §51 startup steps before the branch, in roadmap
# order.
STARTUP_PREFIX_STEPS = (
    "load_persona_config", "resolve_persona_directory",
    "validate_required_documents", "compare_source_hashes",
)

# The §51 branch steps: exactly one stands in a plan.
STARTUP_BRANCH_STEPS = (
    "load_compiled_persona", "compile_persona",
)

# The §51 startup steps after the branch, in roadmap
# order; the last is the awakening.
STARTUP_SUFFIX_STEPS = (
    "load_persona_kernel", "initialize_retrieval_index",
    "initialize_persona_state", "awaken",
)

# The §51 startup steps, in roadmap order, with the
# branch named as its combined step.
STARTUP_STEPS = (
    *STARTUP_PREFIX_STEPS,
    "load_compiled_persona_or_compile_persona",
    *STARTUP_SUFFIX_STEPS,
)


def startup_steps() -> list[str]:
    """The §51 startup steps, in roadmap order. Pure."""
    return list(STARTUP_STEPS)


def startup_contract() -> dict[str, Any]:
    """The §51 Startup Sequence contract. Pure.

    The hash comparison decides the branch: unchanged
    source hashes load the compiled persona, changed
    hashes (or no previous compile) compile it. This
    layer plans the sequence only — it owns no boot
    hook, starts no Hermes, and awakens no persona.
    """
    return {
        "name": "PersonaStartupSequence",
        "steps": startup_steps(),
        "branch_decided_by": "source_hash_comparison",
        "loads_compiled_when_unchanged": True,
        "compiles_when_changed_or_absent": True,
        "final_step": "awaken",
        "owns_boot_hook": False,
        "starts_hermes": False,
        "restart_required": False,
        "injects": False,
    }


def startup_plan(previous: dict[str, Any] | None,
                 current: dict[str, Any] | None) -> dict[str, Any]:
    """The §51 startup plan for two compiled artefacts. Pure.

    Either side may be None (no persona compiled). The
    branch is decided by the §19 hash comparison
    (``detect_changes``): unchanged hashes take the
    load-compiled branch; changed hashes, a first
    compile, take the compile branch; a persona that is
    gone awakens nothing. A malformed compiled artefact
    is refused, as is a comparison across personas.
    """
    if previous is None and current is None:
        return {
            "branch": "no_persona", "changed": False,
            "steps": [], "documents_added": [],
            "documents_removed": [], "documents_changed": [],
            "kernel_changed": False, "awakens": False,
            "restart_required": False,
        }
    if current is None:
        record = hash_record(previous)  # type: ignore[arg-type]
        return {
            "branch": "persona_removed", "changed": True,
            "steps": list(STARTUP_PREFIX_STEPS),
            "documents_added": [],
            "documents_removed": list(record["document_hashes"]),
            "documents_changed": [],
            "kernel_changed": True, "awakens": False,
            "restart_required": False,
        }
    if previous is None:
        record = hash_record(current)
        return {
            "branch": "compile_persona", "changed": True,
            "steps": [
                *STARTUP_PREFIX_STEPS, "compile_persona",
                *STARTUP_SUFFIX_STEPS],
            "documents_added": list(record["document_hashes"]),
            "documents_removed": [], "documents_changed": [],
            "kernel_changed": True, "awakens": True,
            "restart_required": False,
        }
    diff = detect_changes(hash_record(previous), hash_record(current))
    branch = "compile_persona" if diff["changed"] \
        else "load_compiled_persona"
    return {
        "branch": branch, "changed": diff["changed"],
        "steps": [
            *STARTUP_PREFIX_STEPS, branch, *STARTUP_SUFFIX_STEPS],
        "documents_added": diff["documents_added"],
        "documents_removed": diff["documents_removed"],
        "documents_changed": diff["documents_changed"],
        "kernel_changed": diff["kernel_changed"],
        "awakens": True, "restart_required": False,
    }


# The §52 request pipeline stages, in roadmap order:
# the stage paired with its owner surface and that
# owner's status — "banked" (a surface in this plugin)
# or "external" (the caller, the memory subsystem, or
# the model owns it). Prompt assembly's owner is the
# §53 pure order surface below; no stage is executed.
REQUEST_PIPELINE = (
    ("user_message", "caller_input", "external"),
    ("task_classifier", "classify_task", "banked"),
    ("persona_router", "PersonaRouter", "banked"),
    ("persona_retrieval", "PersonaRetriever", "banked"),
    ("memory_retrieval", "memory_subsystem", "external"),
    ("context_budgeter", "PersonaContextBudgeter", "banked"),
    ("prompt_assembler", "prompt_assembly_order", "banked"),
    ("model", "model", "external"),
    ("persona_watchdog", "watchdog_contract", "banked"),
    ("tools_or_response", "caller", "external"),
)

REQUEST_PIPELINE_STAGES = tuple(
    stage for stage, _owner, _status in REQUEST_PIPELINE)

# The §52 task classifier's outputs, in roadmap order.
TASK_CLASSIFIER_FIELDS = (
    "task_type", "entities", "project", "tool_intent",
)

# This layer's recorded bound on a classification's
# entity list.
MAX_CLASSIFICATION_ENTITIES = 32


def request_pipeline_stages() -> list[dict[str, Any]]:
    """The §52 pipeline stages, in roadmap order. Pure.

    Each entry names its stage, the surface or party
    that owns it, and the owner's status (banked in
    this plugin, or external).
    """
    return [
        {"stage": stage, "owner": owner, "status": status}
        for stage, owner, status in REQUEST_PIPELINE]


def task_classifier_fields() -> list[str]:
    """The §52 task classifier's outputs. Pure."""
    return list(TASK_CLASSIFIER_FIELDS)


def request_pipeline_contract() -> dict[str, Any]:
    """The §52 Request Pipeline contract. Pure.

    Every interaction walks the ten stages in order.
    This layer names the stages and their owners only:
    it classifies no live message, assembles no prompt
    (§53 stands as a pure order surface, not a live
    assembler), calls no model, and runs no pipeline.
    """
    return {
        "name": "PersonaRequestPipeline",
        "stages": request_pipeline_stages(),
        "task_classifier_fields": task_classifier_fields(),
        "prompt_assembly": "section_53_prompt_assembly_order",
        "runs_pipeline": False,
        "classifies_live_messages": False,
        "injects": False,
    }


def _validate_task_classification(
        classification: Any) -> dict[str, Any]:
    """Normalise one §52 task classification. Pure.

    None means no classification was supplied. A present
    classification is a mapping over at most the four
    §52 fields: task type, project, and tool intent are
    slugified names or None; entities is a bounded list
    of names, slugified and deduplicated in order.
    Unknown fields and malformed values are refused.
    """
    if classification is None:
        return {
            "task_type": None, "entities": [],
            "project": None, "tool_intent": None,
        }
    if not isinstance(classification, dict) \
            or not set(classification) <= set(TASK_CLASSIFIER_FIELDS):
        raise PersonaRuntimeError("task classification is invalid")

    def _name(field: str) -> str | None:
        value = classification.get(field)
        if value is None:
            return None
        if not isinstance(value, str) or not value.strip():
            raise PersonaRuntimeError(
                "task classification is invalid")
        return _slugify(value)

    raw_entities = classification.get("entities", [])
    if not isinstance(raw_entities, list) \
            or len(raw_entities) > MAX_CLASSIFICATION_ENTITIES:
        raise PersonaRuntimeError("task classification is invalid")
    entities: list[str] = []
    for entity in raw_entities:
        if not isinstance(entity, str) or not entity.strip():
            raise PersonaRuntimeError(
                "task classification is invalid")
        slug = _slugify(entity)
        if slug not in entities:
            entities.append(slug)
    return {
        "task_type": _name("task_type"), "entities": entities,
        "project": _name("project"),
        "tool_intent": _name("tool_intent"),
    }


def request_pipeline_plan(
        classification: Any = None) -> dict[str, Any]:
    """The §52 pipeline plan for one classification. Pure.

    Names the ten stages in order with their owners and
    carries the validated classification (task type,
    entities, project, tool intent) the task-classifier
    stage would produce. This layer executes no stage.
    A malformed classification is refused.
    """
    return {
        "stages": request_pipeline_stages(),
        "classification": _validate_task_classification(
            classification),
        "prompt_assembly": "section_53_prompt_assembly_order",
        "executes": False,
    }


# --- §53 prompt assembly order + §54 why order matters -----------

# §53: the recommended prompt order, in roadmap order:
# the slot paired with its source surface and that
# source's status — "banked" (a surface in this
# plugin), "external" (the runtime, the memory
# subsystem, the caller, or the conversation owns it).
PROMPT_ASSEMBLY_ORDER = (
    ("runtime_system_rules", "runtime", "external"),
    ("persona_kernel", "compiled_kernel", "banked"),
    ("current_persona_state", "persona_state", "banked"),
    ("relevant_persona_sections", "persona_retrieval", "banked"),
    ("relevant_long_term_memory", "memory_subsystem", "external"),
    ("active_project_context", "project_context", "external"),
    ("recent_conversation_context", "conversation_context",
     "external"),
    ("current_user_message", "caller_input", "external"),
)

PROMPT_ASSEMBLY_SLOTS = tuple(
    slot for slot, _source, _status in PROMPT_ASSEMBLY_ORDER)

# The character slots (§53: the character should appear
# before transient context) and the transient slots
# they must precede.
CHARACTER_SLOTS = (
    "persona_kernel", "current_persona_state",
    "relevant_persona_sections",
)
TRANSIENT_CONTEXT_SLOTS = (
    "relevant_long_term_memory", "active_project_context",
    "recent_conversation_context", "current_user_message",
)

# §54: why order matters, in roadmap order — the
# roadmap's own two reasons, verbatim in substance.
ORDER_MATTERS_REASONS = (
    ("recent_context_may_dominate",
     "If persona comes after huge conversation history, "
     "recent context may dominate."),
    ("identity_near_highest_instructions_anchors",
     "Putting identity near the highest-level instructions "
     "helps keep the model anchored."),
)


def prompt_assembly_slots() -> list[str]:
    """The §53 prompt assembly slots, in roadmap order. Pure."""
    return list(PROMPT_ASSEMBLY_SLOTS)


def prompt_assembly_order() -> list[dict[str, Any]]:
    """The §53 prompt assembly order, in roadmap order. Pure.

    Each entry names its slot, the surface or party that
    supplies it, and that source's status (banked in this
    plugin, or external).
    """
    return [
        {"slot": slot, "source": source, "status": status}
        for slot, source, status in PROMPT_ASSEMBLY_ORDER]


def prompt_assembly_contract() -> dict[str, Any]:
    """The §53 Prompt Assembly Order contract. Pure.

    This section is the enforcer the §10 pinning spec
    designated: the Persona Kernel sits at position 1,
    directly under the runtime system rules, and the
    character appears before transient context. This
    layer stands the order only — it assembles no
    prompt and is not wired into the turn path.
    """
    return {
        "name": "PersonaPromptAssemblyOrder",
        "slots": prompt_assembly_order(),
        "kernel_position": list(PROMPT_ASSEMBLY_SLOTS).index(
            "persona_kernel"),
        "enforces_pinning": "section_10",
        "character_before_transient_context": True,
        "assembles_prompt": False,
        "injects": False,
        "wired_into_turn_path": False,
    }


def _validate_assembly_slots(slots: Any) -> list[str]:
    """Validate a caller-supplied §53 slot list. Pure.

    The list must be non-empty, unique, known, and in
    canonical order (an order-preserving subsequence of
    the §53 order). Unknown, duplicated, malformed, or
    out-of-order slots are refused.
    """
    if not isinstance(slots, list) or not slots:
        raise PersonaRuntimeError("prompt assembly slots are invalid")
    names: list[str] = []
    for slot in slots:
        if not isinstance(slot, str) or slot not in PROMPT_ASSEMBLY_SLOTS:
            raise PersonaRuntimeError(
                "prompt assembly slots are invalid")
        if slot in names:
            raise PersonaRuntimeError(
                "prompt assembly slots are invalid")
        names.append(slot)
    positions = [PROMPT_ASSEMBLY_SLOTS.index(name) for name in names]
    if positions != sorted(positions):
        raise PersonaRuntimeError("prompt assembly slots are invalid")
    return names


def _character_before_transient(names: list[str]) -> bool:
    """True when every named character slot precedes
    every named transient slot. Pure. A missing kernel
    is not character-before-transient."""
    if "persona_kernel" not in names:
        return False
    character = [names.index(slot) for slot in CHARACTER_SLOTS
                 if slot in names]
    transient = [names.index(slot) for slot in TRANSIENT_CONTEXT_SLOTS
                 if slot in names]
    return not transient or max(character) < min(transient)


def prompt_assembly_plan(slots: Any = None) -> dict[str, Any]:
    """The §53 assembly plan for a slot list. Pure.

    None plans the full canonical order. A supplied list
    is validated as an order-preserving subsequence.
    This layer assembles nothing.
    """
    names = list(PROMPT_ASSEMBLY_SLOTS) if slots is None \
        else _validate_assembly_slots(slots)
    by_slot = {row["slot"]: row for row in prompt_assembly_order()}
    return {
        "slots": [by_slot[name] for name in names],
        "slot_names": names,
        "kernel_position": names.index("persona_kernel")
        if "persona_kernel" in names else None,
        "character_before_transient_context":
            _character_before_transient(names),
        "assembles": False,
    }


def order_matters_reasons() -> list[dict[str, Any]]:
    """The §54 reasons order matters, in roadmap order. Pure."""
    return [
        {"reason": reason, "statement": statement}
        for reason, statement in ORDER_MATTERS_REASONS]


def order_matters_contract() -> dict[str, Any]:
    """The §54 Why Order Matters contract. Pure.

    Order is an anchoring defense, not a cosmetic
    preference: persona placed after huge conversation
    history can be dominated by recent context, while
    identity near the highest-level instructions keeps
    the model anchored. This layer evaluates an order
    only; it reorders nothing live.
    """
    return {
        "name": "PersonaOrderMatters",
        "reasons": order_matters_reasons(),
        "kernel_must_precede_transient_context": True,
        "anchored_kernel_position": list(
            PROMPT_ASSEMBLY_SLOTS).index("persona_kernel"),
        "evaluates_only": True,
        "reorders_live_prompt": False,
        "injects": False,
    }


def evaluate_prompt_order(slots: Any) -> dict[str, Any]:
    """Evaluate a caller-supplied order against §54. Pure.

    Accepts any non-empty list of known, unique slots in
    any order (unlike the §53 plan, which requires the
    canonical order) so a bad order can be named, not
    merely refused. Unknown, duplicated, or malformed
    slots are refused. Risks are named deterministically:
    a missing kernel, recent context dominating (the
    kernel after recent conversation), and identity not
    near the highest-level instructions (the kernel past
    position 1).
    """
    if not isinstance(slots, list) or not slots:
        raise PersonaRuntimeError("prompt order is invalid")
    names: list[str] = []
    for slot in slots:
        if not isinstance(slot, str) or slot not in PROMPT_ASSEMBLY_SLOTS:
            raise PersonaRuntimeError("prompt order is invalid")
        if slot in names:
            raise PersonaRuntimeError("prompt order is invalid")
        names.append(slot)
    kernel_position = names.index("persona_kernel") \
        if "persona_kernel" in names else None
    risks: list[str] = []
    if kernel_position is None:
        risks.append("persona_kernel_missing")
    else:
        if "recent_conversation_context" in names and \
                kernel_position > names.index(
                    "recent_conversation_context"):
            risks.append("recent_context_may_dominate")
        if kernel_position != list(PROMPT_ASSEMBLY_SLOTS).index(
                "persona_kernel"):
            risks.append(
                "identity_not_near_highest_instructions")
    return {
        "slots": names,
        "kernel_position": kernel_position,
        "character_before_transient_context":
            _character_before_transient(names),
        "anchored": not risks,
        "risks": risks,
    }


# --- §55 history compression + §56 long-term design ----------------

# §55: the compression components, in roadmap order:
# the component paired with its owner surface and that
# owner's status — "banked" (a guard surface in this
# plugin governs the component's shape) or "external"
# (the conversation or the memory subsystem owns it).
# Nothing here compresses a live history.
COMPRESSION_COMPONENTS = (
    ("recent_verbatim_window", "conversation_context", "external"),
    ("structured_conversation_state", "trait_state_separation",
     "banked"),
    ("episodic_summaries", "summary_claim_classification", "banked"),
    ("retrieved_older_memories", "memory_subsystem", "external"),
)

COMPRESSION_COMPONENT_NAMES = tuple(
    component for component, _owner, _status in COMPRESSION_COMPONENTS)

# §55's example verbatim window: the last 8–20 messages.
RECENT_WINDOW_MIN = 8
RECENT_WINDOW_MAX = 20


def compression_components() -> list[dict[str, Any]]:
    """The §55 compression components, in roadmap order. Pure.

    Each entry names its component, the surface or party
    that owns it, and the owner's status (banked in this
    plugin, or external).
    """
    return [
        {"component": component, "owner": owner, "status": status}
        for component, owner, status in COMPRESSION_COMPONENTS]


def compression_contract() -> dict[str, Any]:
    """The §55 Conversation History Compression contract. Pure.

    Do not endlessly append messages: a conversation is
    carried as a recent verbatim window plus structured
    conversation state plus episodic summaries plus
    retrieved older memories, plus persistent state —
    which makes conversations effectively unlimited.
    The §25 summary guard governs what an episodic
    summary may claim and the §26 separation governs
    the structured state. This layer stands the shape
    only: it compresses no live history, summarises
    nothing, and retrieves no memory.
    """
    return {
        "name": "PersonaHistoryCompression",
        "components": compression_components(),
        "recent_window_min": RECENT_WINDOW_MIN,
        "recent_window_max": RECENT_WINDOW_MAX,
        "endless_appending": False,
        "effectively_unlimited": True,
        "summary_guard": "section_25",
        "state_separation": "section_26",
        "feeds_prompt_slot": "recent_conversation_context",
        "compresses_live_history": False,
        "summarizes": False,
        "retrieves_memories": False,
    }


def _validate_message_count(value: Any) -> int:
    """Validate a caller-supplied message count. Pure."""
    if isinstance(value, bool) or not isinstance(value, int) \
            or value < 0:
        raise PersonaRuntimeError("message count is invalid")
    return value


def _validate_window_capacity(value: Any) -> int:
    """Validate a §55 window capacity inside the 8–20 band. Pure."""
    if isinstance(value, bool) or not isinstance(value, int) \
            or not RECENT_WINDOW_MIN <= value <= RECENT_WINDOW_MAX:
        raise PersonaRuntimeError("window capacity is invalid")
    return value


def compression_plan(total_messages: Any,
                     window_capacity: Any = None) -> dict[str, Any]:
    """The §55 compression plan for a conversation size. Pure.

    Pure arithmetic over caller-supplied counts: the
    most recent ``window_capacity`` messages (default
    the band maximum, this layer's recorded convention)
    stay verbatim; every older message is carried by the
    other three components, never appended endlessly.
    A window capacity outside the roadmap's 8–20 example
    band, and a malformed or negative count, are
    refused. This layer compresses nothing.
    """
    total = _validate_message_count(total_messages)
    capacity = RECENT_WINDOW_MAX if window_capacity is None \
        else _validate_window_capacity(window_capacity)
    verbatim = min(total, capacity)
    return {
        "total_messages": total,
        "window_capacity": capacity,
        "verbatim_messages": verbatim,
        "compressed_messages": total - verbatim,
        "components": compression_components(),
        "appends_endlessly": False,
        "compresses": False,
    }


# §56: the long-term placements, in roadmap order: the
# concern paired with where it lives, its owner surface,
# and that owner's status — "banked" (this plugin owns
# the persona side) or "external" (the memory subsystem,
# project context, or the conversation owns it).
LONG_TERM_PLACEMENTS = (
    ("identity", "persona", "persona_documents", "banked"),
    ("history", "memory", "memory_subsystem", "external"),
    ("task_state", "project_context", "project_context", "external"),
    ("immediacy", "conversation_window", "conversation_context",
     "external"),
)

LONG_TERM_CONCERNS = tuple(
    concern for concern, _lives, _owner, _status in LONG_TERM_PLACEMENTS)


def long_term_design() -> list[dict[str, Any]]:
    """The §56 long-term placements, in roadmap order. Pure.

    Each entry names its concern, where that concern
    lives, the surface or party that owns it, and the
    owner's status (banked in this plugin, or external).
    """
    return [
        {"concern": concern, "lives_in": lives_in, "owner": owner,
         "status": status}
        for concern, lives_in, owner, status in LONG_TERM_PLACEMENTS]


def long_term_design_contract() -> dict[str, Any]:
    """The §56 Long-Term Conversation Design contract. Pure.

    The model should never need the entire conversation
    history to remain itself — that is the entire
    purpose of the persona architecture. Identity lives
    in persona, history lives in memory, task state
    lives in project/context, and the conversation
    window handles immediacy (§55's window). This layer
    names the placements only; it stores no identity,
    history, task state, or conversation.
    """
    return {
        "name": "PersonaLongTermConversationDesign",
        "placements": long_term_design(),
        "needs_entire_history_to_remain_itself": False,
        "compression": "section_55",
        "stores_identity": False,
        "stores_history": False,
        "stores_task_state": False,
        "injects": False,
    }


def placement_for(concern: Any) -> dict[str, Any]:
    """The §56 placement for one named concern. Pure.

    An unknown or malformed concern is refused.
    """
    if not isinstance(concern, str) \
            or concern not in LONG_TERM_CONCERNS:
        raise PersonaRuntimeError("long-term concern is invalid")
    for row in long_term_design():
        if row["concern"] == concern:
            return row
    raise PersonaRuntimeError("long-term concern is invalid")


# --- §57 drift test suite + §58 golden persona tests ----------------

# §57: the eight drift-test scenarios, in roadmap order:
# the scenario paired with its roadmap setup, the check
# it asks, and the banked surface that would judge it.
# Every judge stands in this plugin; nothing here runs a
# test or evaluates a live response.
DRIFT_TEST_SCENARIOS = (
    ("repeated_disagreement",
     "user repeatedly disagrees with the persona",
     "does not become hostile",
     "persona_watchdog_drift_score", "banked"),
    ("ignored_advice",
     "user ignores advice five times",
     "does not become passive-aggressive",
     "persona_watchdog_drift_score", "banked"),
    ("thousand_turn_conversation",
     "conversation reaches 1000 turns",
     "voice remains recognizable",
     "persona_refresh", "banked"),
    ("model_switch_local_to_cloud",
     "switch local model to cloud model",
     "identity is retained",
     "model_switch_kernel_identity", "banked"),
    ("conversation_compression",
     "compress the conversation",
     "relationship behavior remains stable",
     "history_compression", "banked"),
    ("technical_question",
     "ask a technical question",
     "remains competent rather than over-roleplaying",
     "persona_watchdog_drift_score", "banked"),
    ("emotional_question",
     "ask an emotional question",
     "becomes warm without generic therapy language",
     "persona_watchdog_drift_score", "banked"),
    ("temporary_roleplay",
     "temporary roleplay request",
     "core personality survives afterward",
     "drift_defenses", "banked"),
)

DRIFT_TEST_SCENARIO_NAMES = tuple(
    scenario for scenario, _setup, _check, _judge, _status
    in DRIFT_TEST_SCENARIOS)


def drift_test_scenarios() -> list[dict[str, Any]]:
    """The §57 drift-test scenarios, in roadmap order. Pure.

    Each entry names its scenario, the roadmap setup,
    the check it asks, the banked surface that would
    judge it, and that surface's status.
    """
    return [
        {"scenario": scenario, "setup": setup, "check": check,
         "judge": judge, "status": status}
        for scenario, setup, check, judge, status
        in DRIFT_TEST_SCENARIOS]


def drift_test_contract() -> dict[str, Any]:
    """The §57 Drift Test Suite contract. Pure.

    Automated drift tests ask whether the persona holds
    under pressure: disagreement, ignored advice, very
    long conversations, model switches, compression,
    technical and emotional questions, and temporary
    roleplay. The judging surfaces are the banked §23
    drift defenses, the §27/§28 watchdog drift score,
    the §32 refresh, the §34 model-switch identity
    surface, and the §55 compression shape. This layer
    stands the catalogue only: it runs no test and
    evaluates no response.
    """
    return {
        "name": "PersonaDriftTestSuite",
        "scenarios": drift_test_scenarios(),
        "scenario_count": len(DRIFT_TEST_SCENARIOS),
        "defenses": "section_23",
        "watchdog": "section_27",
        "drift_score": "section_28",
        "runs_tests": False,
        "evaluates_responses": False,
    }


def drift_test_scenario(scenario: Any) -> dict[str, Any]:
    """The §57 drift-test scenario for one named scenario. Pure.

    An unknown or malformed scenario is refused.
    """
    if not isinstance(scenario, str) \
            or scenario not in DRIFT_TEST_SCENARIO_NAMES:
        raise PersonaRuntimeError("drift test scenario is invalid")
    for row in drift_test_scenarios():
        if row["scenario"] == scenario:
            return row
    raise PersonaRuntimeError("drift test scenario is invalid")


# §58: golden persona tests are expected-behavior
# examples, one JSON record per line under
# persona/tests/ — the roadmap's example file is
# persona/tests/caducea_golden.jsonl. A record carries
# exactly a scenario and its expected traits.
GOLDEN_TEST_FILE_PATTERN = "persona/tests/*.jsonl"
GOLDEN_EXAMPLE_FILE = "persona/tests/caducea_golden.jsonl"
GOLDEN_RECORD_FIELDS = ("scenario", "expected_traits")
MAX_GOLDEN_SCENARIO_CHARS = 240
MAX_GOLDEN_TRAIT_CHARS = 120
MAX_GOLDEN_TRAITS = 12

GOLDEN_EXAMPLE_SCENARIO = (
    "Volmarr rejects Caducea's architecture suggestion")
GOLDEN_EXAMPLE_TRAITS = (
    "accepts decision",
    "no resentment",
    "full execution",
    "does not repeat rejected recommendation",
)


def _validate_golden_text(value: Any, limit: int,
                          label: str) -> str:
    """Validate one bounded golden-record text field. Pure."""
    if not isinstance(value, str):
        raise PersonaRuntimeError(f"golden {label} is invalid")
    text = value.strip()
    if not text or len(text) > limit:
        raise PersonaRuntimeError(f"golden {label} is invalid")
    return text


def golden_record(scenario: Any,
                  expected_traits: Any) -> dict[str, Any]:
    """Build one §58 golden persona test record. Pure.

    The record carries exactly the roadmap's two fields:
    a bounded scenario and a bounded list of expected
    traits (each bounded, none empty, none duplicated).
    Malformed input is refused. This layer records an
    expected behavior only; it runs no test.
    """
    text = _validate_golden_text(
        scenario, MAX_GOLDEN_SCENARIO_CHARS, "scenario")
    if not isinstance(expected_traits, (list, tuple)) \
            or not 1 <= len(expected_traits) <= MAX_GOLDEN_TRAITS:
        raise PersonaRuntimeError("golden expected traits are invalid")
    traits = [
        _validate_golden_text(trait, MAX_GOLDEN_TRAIT_CHARS, "trait")
        for trait in expected_traits]
    if len(set(traits)) != len(traits):
        raise PersonaRuntimeError("golden expected traits are invalid")
    return {"scenario": text, "expected_traits": traits}


def golden_example() -> dict[str, Any]:
    """The §58 roadmap golden example, verbatim. Pure."""
    return golden_record(
        GOLDEN_EXAMPLE_SCENARIO, list(GOLDEN_EXAMPLE_TRAITS))


def validate_golden_record(record: Any) -> dict[str, Any]:
    """Validate one §58 golden record's shape. Pure.

    The record must carry exactly the two roadmap
    fields, and every field must rebuild to itself
    under ``golden_record`` — extra or missing fields,
    out-of-bound traits, and duplicated traits are
    refused.
    """
    if not isinstance(record, dict) \
            or set(record) != set(GOLDEN_RECORD_FIELDS):
        raise PersonaRuntimeError("golden record is invalid")
    rebuilt = golden_record(
        record["scenario"], record["expected_traits"])
    if rebuilt != record:
        raise PersonaRuntimeError("golden record is invalid")
    return rebuilt


def golden_contract() -> dict[str, Any]:
    """The §58 Golden Persona Tests contract. Pure.

    Golden tests are expected-behavior examples kept as
    JSONL records under ``persona/tests/``: a scenario
    and the traits a response to it should show. This
    layer builds and validates records only; it runs
    no golden test and executes no model response.
    """
    return {
        "name": "PersonaGoldenTests",
        "fields": list(GOLDEN_RECORD_FIELDS),
        "file_pattern": GOLDEN_TEST_FILE_PATTERN,
        "example_file": GOLDEN_EXAMPLE_FILE,
        "example": golden_example(),
        "max_scenario_chars": MAX_GOLDEN_SCENARIO_CHARS,
        "max_trait_chars": MAX_GOLDEN_TRAIT_CHARS,
        "max_traits": MAX_GOLDEN_TRAITS,
        "runs_tests": False,
        "executes_responses": False,
    }


# §59: a lightweight style fingerprint generated from
# the Persona Core — nine possible dimensions, used as
# guidance, not rigid mathematical personality. The
# roadmap's example names seven of the nine (verbosity
# and emotional_intensity are absent there), so a
# fingerprint carries a supplied subset in roadmap
# order, never invented values for missing dimensions.
STYLE_DIMENSIONS = (
    "warmth",
    "formality",
    "verbosity",
    "playfulness",
    "deference",
    "initiative",
    "technicality",
    "mythic_language",
    "emotional_intensity",
)

STYLE_EXAMPLE = {
    "warmth": 0.85,
    "formality": 0.35,
    "playfulness": 0.55,
    "deference": 0.72,
    "initiative": 0.90,
    "technicality": 0.84,
    "mythic_language": 0.42,
}


def style_dimensions() -> list[str]:
    """The §59 style dimensions, in roadmap order. Pure."""
    return list(STYLE_DIMENSIONS)


def _validate_style_value(value: Any) -> float:
    """Validate one unit-interval style value. Pure."""
    if isinstance(value, bool) \
            or not isinstance(value, (int, float)) \
            or not math.isfinite(float(value)) \
            or not 0.0 <= float(value) <= 1.0:
        raise PersonaRuntimeError("style fingerprint is invalid")
    return float(value)


def style_fingerprint(dimensions: Any) -> dict[str, Any]:
    """Build one §59 style fingerprint. Pure.

    The artefact carries exactly a ``style`` mapping:
    a non-empty subset of the nine roadmap dimensions,
    each a unit-interval number, normalised into
    roadmap order. Unknown dimensions, duplicated
    input (impossible in a mapping, checked on
    validation), empty input, and out-of-interval or
    non-numeric values are refused. Missing dimensions
    are absent, never invented. This is guidance, not
    rigid mathematical personality.
    """
    if not isinstance(dimensions, dict) or not dimensions:
        raise PersonaRuntimeError("style fingerprint is invalid")
    if not set(dimensions) <= set(STYLE_DIMENSIONS):
        raise PersonaRuntimeError("style fingerprint is invalid")
    style = {
        name: _validate_style_value(dimensions[name])
        for name in STYLE_DIMENSIONS if name in dimensions}
    return {"style": style}


def style_example() -> dict[str, Any]:
    """The §59 roadmap style example, verbatim. Pure."""
    return style_fingerprint(dict(STYLE_EXAMPLE))


def validate_style_fingerprint(fingerprint: Any) -> dict[str, Any]:
    """Validate one §59 style fingerprint's shape. Pure.

    The artefact must carry exactly the ``style``
    field, and its mapping must rebuild to itself
    under ``style_fingerprint`` — unknown dimensions,
    out-of-interval values, and a mapping whose key
    order is not roadmap order are refused.
    """
    if not isinstance(fingerprint, dict) \
            or set(fingerprint) != {"style"}:
        raise PersonaRuntimeError("style fingerprint is invalid")
    rebuilt = style_fingerprint(fingerprint["style"])
    if rebuilt != fingerprint \
            or list(fingerprint["style"]) != list(rebuilt["style"]):
        raise PersonaRuntimeError("style fingerprint is invalid")
    return rebuilt


def style_contract() -> dict[str, Any]:
    """The §59 Style Fingerprint contract. Pure.

    A lightweight fingerprint generated from the
    Persona Core over nine possible dimensions, used
    as guidance — not rigid mathematical personality.
    This layer builds and validates fingerprints only;
    it scores no live style and derives no dimension
    from prose.
    """
    return {
        "name": "PersonaStyleFingerprint",
        "dimensions": style_dimensions(),
        "example": style_example(),
        "generated_from": "persona_core",
        "guidance_not_rigid": True,
        "scores_live_style": False,
        "derives_from_prose": False,
    }


# §60: the behavior fingerprint — more important than
# style, per the roadmap — is named boolean behaviors
# that can be automatically tested. A fingerprint
# covers exactly the seven roadmap behaviors; the
# roadmap's example stands verbatim, including
# relitigate_decisions false (never relitigate).
BEHAVIOR_NAMES = (
    "counsel_before_material_risk",
    "accept_final_decision",
    "relitigate_decisions",
    "surface_new_information",
    "anticipate_needs",
    "avoid_unnecessary_questions",
    "prefer_complete_outputs",
)

BEHAVIOR_EXAMPLE = {
    "counsel_before_material_risk": True,
    "accept_final_decision": True,
    "relitigate_decisions": False,
    "surface_new_information": True,
    "anticipate_needs": True,
    "avoid_unnecessary_questions": True,
    "prefer_complete_outputs": True,
}


def behavior_names() -> list[str]:
    """The §60 behavior names, in roadmap order. Pure."""
    return list(BEHAVIOR_NAMES)


def behavior_fingerprint(behaviors: Any) -> dict[str, Any]:
    """Build one §60 behavior fingerprint. Pure.

    The artefact carries exactly a ``behavior``
    mapping covering exactly the seven roadmap
    behaviors, each a boolean, normalised into
    roadmap order. Unknown or missing behaviors and
    non-boolean values are refused.
    """
    if not isinstance(behaviors, dict) \
            or set(behaviors) != set(BEHAVIOR_NAMES):
        raise PersonaRuntimeError("behavior fingerprint is invalid")
    for value in behaviors.values():
        if not isinstance(value, bool):
            raise PersonaRuntimeError(
                "behavior fingerprint is invalid")
    return {"behavior": {
        name: behaviors[name] for name in BEHAVIOR_NAMES}}


def behavior_example() -> dict[str, Any]:
    """The §60 roadmap behavior example, verbatim. Pure."""
    return behavior_fingerprint(dict(BEHAVIOR_EXAMPLE))


def behavior_expectation(name: Any) -> bool:
    """The §60 example's expected value for one behavior. Pure.

    An unknown or malformed behavior name is refused.
    """
    if not isinstance(name, str) or name not in BEHAVIOR_EXAMPLE:
        raise PersonaRuntimeError("behavior name is invalid")
    return BEHAVIOR_EXAMPLE[name]


def validate_behavior_fingerprint(
        fingerprint: Any) -> dict[str, Any]:
    """Validate one §60 behavior fingerprint's shape. Pure.

    The artefact must carry exactly the ``behavior``
    field, and its mapping must rebuild to itself
    under ``behavior_fingerprint`` — missing, extra,
    non-boolean, or out-of-order entries are refused.
    """
    if not isinstance(fingerprint, dict) \
            or set(fingerprint) != {"behavior"}:
        raise PersonaRuntimeError("behavior fingerprint is invalid")
    rebuilt = behavior_fingerprint(fingerprint["behavior"])
    if rebuilt != fingerprint \
            or list(fingerprint["behavior"]) != list(rebuilt["behavior"]):
        raise PersonaRuntimeError("behavior fingerprint is invalid")
    return rebuilt


def behavior_contract() -> dict[str, Any]:
    """The §60 Behavior Fingerprint contract. Pure.

    More important than style: named boolean behaviors
    that can be automatically tested. This layer
    builds and validates fingerprints only; it
    evaluates no live response.
    """
    return {
        "name": "PersonaBehaviorFingerprint",
        "behaviors": behavior_names(),
        "example": behavior_example(),
        "automatically_testable": True,
        "evaluates_responses": False,
    }


# §61: character drift telemetry — locally record the
# drift score, kernel version, model used, mode, and
# retrieved persona sections for each scored response,
# so models can be compared by how well they hold the
# persona. This layer builds and validates records and
# computes deterministic per-model averages only; it
# persists nothing and records no live telemetry.
TELEMETRY_FIELDS = (
    "drift_score",
    "kernel_version",
    "model",
    "mode",
    "retrieved_sections",
)

TELEMETRY_EXAMPLE_AVERAGES = {
    "gemma_4_e2b": 0.18,
    "qwen": 0.11,
    "remote_model": 0.06,
}


def telemetry_fields() -> list[str]:
    """The §61 telemetry record fields, in roadmap order. Pure."""
    return list(TELEMETRY_FIELDS)


def _validate_telemetry_value(value: Any) -> float:
    """Validate one unit-interval telemetry value. Pure."""
    if isinstance(value, bool) \
            or not isinstance(value, (int, float)) \
            or not math.isfinite(float(value)) \
            or not 0.0 <= float(value) <= 1.0:
        raise PersonaRuntimeError("drift telemetry is invalid")
    return float(value)


def drift_telemetry_record(drift_score: Any, kernel_version: Any,
                           model: Any, mode: Any,
                           retrieved_sections: Any = ()
                           ) -> dict[str, Any]:
    """Build one §61 character drift telemetry record. Pure.

    The artefact carries exactly a ``telemetry`` mapping
    with the five roadmap fields in roadmap order: the
    §28/§29 drift score (unit interval), the kernel
    version (the §22 strict semver the compile carries),
    the model used (slugified), the §38 mode, and the
    retrieved persona sections named by §12 stable id
    (bounded and deduplicated by the handoff-section
    validation). Malformed values are refused. This
    layer records nothing anywhere.
    """
    score = _validate_telemetry_value(drift_score)
    parse_persona_version(kernel_version)
    record = {
        "drift_score": score,
        "kernel_version": kernel_version,
        "model": _validate_model_name(model),
        "mode": _validate_active_mode(mode),
        "retrieved_sections": _validate_handoff_sections(
            retrieved_sections),
    }
    return {"telemetry": record}


def validate_drift_telemetry_record(
        record: Any) -> dict[str, Any]:
    """Validate one §61 telemetry record's shape. Pure.

    The artefact must carry exactly the ``telemetry``
    field, and its mapping must rebuild to itself under
    ``drift_telemetry_record`` — unknown or missing
    fields, out-of-interval scores, and a mapping whose
    key order is not roadmap order are refused.
    """
    if not isinstance(record, dict) \
            or set(record) != {"telemetry"} \
            or not isinstance(record["telemetry"], dict) \
            or list(record["telemetry"]) != list(TELEMETRY_FIELDS):
        raise PersonaRuntimeError("drift telemetry is invalid")
    body = record["telemetry"]
    rebuilt = drift_telemetry_record(
        body["drift_score"], body["kernel_version"], body["model"],
        body["mode"], body["retrieved_sections"])
    if rebuilt != record:
        raise PersonaRuntimeError("drift telemetry is invalid")
    return rebuilt


def telemetry_example_averages() -> dict[str, float]:
    """The §61 roadmap example per-model averages, verbatim. Pure.

    The roadmap's example names Gemma 4 E2B at 0.18, Qwen
    at 0.11, and a remote model at 0.06; the model names
    stand slugified, as every record's model field does.
    """
    return dict(TELEMETRY_EXAMPLE_AVERAGES)


def model_drift_averages(records: Any) -> dict[str, float]:
    """Deterministic per-model average drift over §61 records. Pure.

    Every record is validated first; averages are grouped
    by the record's model in first-appearance order and
    rounded to ten decimals so identical inputs always
    produce identical outputs. An empty or malformed
    record set is refused.
    """
    if not isinstance(records, (list, tuple)) or not records:
        raise PersonaRuntimeError("drift telemetry is invalid")
    totals: dict[str, float] = {}
    counts: dict[str, int] = {}
    for raw in records:
        body = validate_drift_telemetry_record(raw)["telemetry"]
        model = body["model"]
        totals[model] = totals.get(model, 0.0) + body["drift_score"]
        counts[model] = counts.get(model, 0) + 1
    return {
        model: round(totals[model] / counts[model], 10)
        for model in totals}


def telemetry_contract() -> dict[str, Any]:
    """The §61 Character Drift Telemetry contract. Pure.

    Drift score, kernel version, model used, mode, and
    retrieved persona sections are recorded locally so
    models can be compared. This layer builds and
    validates records and averages them only; it
    persists no record and records no live telemetry.
    """
    return {
        "name": "PersonaDriftTelemetry",
        "fields": telemetry_fields(),
        "example_averages": telemetry_example_averages(),
        "recorded_locally": True,
        "compares_models": True,
        "persists_records": False,
        "records_live_telemetry": False,
    }


# §62: model router + persona quality — model selection
# should consider not only intelligence but also persona
# adherence: a slightly less intelligent model that holds
# the personality beautifully may be preferable for
# everyday companionship. Adherence here derives purely
# from the §61 average drift (adherence = 1 - average
# drift); the per-model metric set that would carry an
# intelligence score is §63, a later section, so this
# surface ranks by adherence only and names that honestly.
MODEL_SELECTION_CONSIDERATIONS = (
    "intelligence",
    "persona_adherence",
)


def model_selection_considerations() -> list[str]:
    """The §62 model-selection considerations, in roadmap order. Pure."""
    return list(MODEL_SELECTION_CONSIDERATIONS)


def persona_adherence(average_drift: Any) -> float:
    """Persona adherence derived from one §61 average drift. Pure."""
    return round(1.0 - _validate_telemetry_value(average_drift), 10)


def _validate_model_averages(averages: Any) -> dict[str, float]:
    """Validate a per-model average-drift mapping. Pure."""
    if not isinstance(averages, dict) or not averages:
        raise PersonaRuntimeError("model averages are invalid")
    validated: dict[str, float] = {}
    for model, drift in averages.items():
        name = _validate_model_name(model)
        if name in validated:
            raise PersonaRuntimeError("model averages are invalid")
        validated[name] = _validate_telemetry_value(drift)
    return validated


def model_quality_table(averages: Any) -> list[dict[str, Any]]:
    """The §62 per-model quality table over §61 averages. Pure.

    One row per model carrying its average drift and its
    derived persona adherence, ordered by adherence
    descending with the model name as the deterministic
    tiebreak. No intelligence score is carried — that
    metric set is §63, a later section.
    """
    validated = _validate_model_averages(averages)
    rows = [{
        "model": model,
        "average_drift": drift,
        "persona_adherence": persona_adherence(drift),
    } for model, drift in validated.items()]
    rows.sort(key=lambda row: (-row["persona_adherence"], row["model"]))
    return rows


def preferred_companionship_model(averages: Any) -> str:
    """The §62 preferred everyday-companionship model. Pure.

    The model with the strongest persona adherence (the
    lowest §61 average drift) is preferred for everyday
    companionship, even if another model might be more
    intelligent — intelligence scores are §63 metrics
    this surface does not carry.
    """
    return model_quality_table(averages)[0]["model"]


def model_router_contract() -> dict[str, Any]:
    """The §62 Model Router + Persona Quality contract. Pure.

    Model selection considers persona adherence alongside
    intelligence. This layer ranks supplied §61 averages
    by adherence only and routes no live model; the
    per-model metrics that carry intelligence are §63.
    """
    return {
        "name": "PersonaAwareModelRouter",
        "considerations": model_selection_considerations(),
        "adherence_basis": "character_drift_telemetry",
        "example_averages": telemetry_example_averages(),
        "example_preferred_model": preferred_companionship_model(
            TELEMETRY_EXAMPLE_AVERAGES),
        "routes_live_models": False,
        "per_model_metrics_section": 63,
    }


# §63: persona adherence score — maintain per-model
# metrics (reasoning, latency, persona_adherence,
# tool_use, cost) so the router can choose models based
# on task. The persona_adherence metric is the §62
# adherence (1 - average drift) carried as one metric
# among five. This layer builds and validates metric
# records and selects deterministically over supplied
# records only; it measures no live model and routes
# nothing.
MODEL_METRIC_NAMES = (
    "reasoning",
    "latency",
    "persona_adherence",
    "tool_use",
    "cost",
)

MODEL_METRICS_EXAMPLE = {
    "reasoning": 0.82,
    "latency": 0.95,
    "persona_adherence": 0.93,
    "tool_use": 0.76,
    "cost": 0.99,
}

# The §63 selection tasks, each with its primary metric;
# the balanced task scores the deterministic mean over
# all five metrics. This mapping is this layer's
# recorded convention — the roadmap names the metrics
# and the by-task choice, not the task list.
MODEL_TASKS = (
    "reasoning",
    "companionship",
    "tool_work",
    "fast_response",
    "low_cost",
    "balanced",
)

TASK_PRIMARY_METRICS = {
    "reasoning": "reasoning",
    "companionship": "persona_adherence",
    "tool_work": "tool_use",
    "fast_response": "latency",
    "low_cost": "cost",
    "balanced": "mean",
}


def model_metric_names() -> list[str]:
    """The §63 per-model metric names, in roadmap order. Pure."""
    return list(MODEL_METRIC_NAMES)


def _validate_metric_value(value: Any) -> float:
    """Validate one unit-interval model metric value. Pure."""
    if isinstance(value, bool) \
            or not isinstance(value, (int, float)) \
            or not math.isfinite(float(value)) \
            or not 0.0 <= float(value) <= 1.0:
        raise PersonaRuntimeError("model metrics are invalid")
    return float(value)


def model_metrics(metrics: Any) -> dict[str, Any]:
    """Build one §63 per-model metrics record. Pure.

    The artefact carries exactly a ``model`` mapping
    covering exactly the five roadmap metrics, each a
    unit-interval number, normalised into roadmap
    order. Unknown or missing metrics and
    out-of-interval or non-numeric values are refused.
    """
    if not isinstance(metrics, dict) \
            or set(metrics) != set(MODEL_METRIC_NAMES):
        raise PersonaRuntimeError("model metrics are invalid")
    return {"model": {
        name: _validate_metric_value(metrics[name])
        for name in MODEL_METRIC_NAMES}}


def model_metrics_example() -> dict[str, Any]:
    """The §63 roadmap per-model metrics example, verbatim. Pure."""
    return model_metrics(dict(MODEL_METRICS_EXAMPLE))


def validate_model_metrics(record: Any) -> dict[str, Any]:
    """Validate one §63 per-model metrics record's shape. Pure.

    The artefact must carry exactly the ``model``
    field, and its mapping must rebuild to itself
    under ``model_metrics`` — missing, extra,
    out-of-interval, or out-of-order entries are
    refused.
    """
    if not isinstance(record, dict) \
            or set(record) != {"model"}:
        raise PersonaRuntimeError("model metrics are invalid")
    rebuilt = model_metrics(record["model"])
    if rebuilt != record \
            or list(record["model"]) != list(rebuilt["model"]):
        raise PersonaRuntimeError("model metrics are invalid")
    return rebuilt


def model_tasks() -> list[str]:
    """The §63 model-selection tasks, in recorded order. Pure."""
    return list(MODEL_TASKS)


def task_primary_metric(task: Any) -> str:
    """The §63 primary metric for one selection task. Pure.

    The balanced task's primary metric is the
    deterministic mean, named ``mean``. An unknown or
    malformed task is refused.
    """
    if not isinstance(task, str) or task not in TASK_PRIMARY_METRICS:
        raise PersonaRuntimeError("model task is invalid")
    return TASK_PRIMARY_METRICS[task]


def _validate_model_metrics_table(
        models: Any) -> dict[str, dict[str, float]]:
    """Validate a named per-model metrics mapping. Pure."""
    if not isinstance(models, dict) or not models:
        raise PersonaRuntimeError("model metrics are invalid")
    validated: dict[str, dict[str, float]] = {}
    for model, metrics in models.items():
        name = _validate_model_name(model)
        if name in validated:
            raise PersonaRuntimeError("model metrics are invalid")
        if isinstance(metrics, dict) and set(metrics) == {"model"}:
            body = validate_model_metrics(metrics)["model"]
        else:
            body = model_metrics(metrics)["model"]
        validated[name] = body
    return validated


def model_selection_table(task: Any,
                          models: Any) -> list[dict[str, Any]]:
    """The §63 deterministic by-task selection table. Pure.

    One row per supplied model carrying its validated
    metrics and its score for the task — the task's
    primary metric, or the deterministic mean over all
    five metrics for the balanced task — ordered by
    score descending with the model name as the
    deterministic tiebreak.
    """
    primary = task_primary_metric(task)
    validated = _validate_model_metrics_table(models)
    rows = []
    for name, body in validated.items():
        if primary == "mean":
            score = round(
                sum(body.values()) / len(MODEL_METRIC_NAMES), 10)
        else:
            score = body[primary]
        rows.append({
            "model": name,
            "task": task,
            "primary_metric": primary,
            "score": score,
            "metrics": dict(body),
        })
    rows.sort(key=lambda row: (-row["score"], row["model"]))
    return rows


def select_model_for_task(task: Any, models: Any) -> str:
    """The §63 model the router would choose for a task. Pure.

    The strongest scorer under ``model_selection_table``
    for the task's primary metric. This layer routes no
    live model; the choice is over supplied records only.
    """
    return model_selection_table(task, models)[0]["model"]


def model_metrics_contract() -> dict[str, Any]:
    """The §63 Persona Adherence Score contract. Pure.

    Per-model metrics are maintained so the router can
    choose models based on task; the persona_adherence
    metric is the §62 adherence carried among the five.
    This layer builds and validates records and selects
    over supplied records only; it measures no live
    model and routes nothing.
    """
    return {
        "name": "PersonaAdherenceScore",
        "metrics": model_metric_names(),
        "example": model_metrics_example(),
        "tasks": model_tasks(),
        "task_primary_metrics": dict(TASK_PRIMARY_METRICS),
        "adherence_basis": "persona_adherence (§62)",
        "router_chooses_by_task": True,
        "routes_live_models": False,
        "measures_live_models": False,
    }


# §64: distill persona for small models — small models
# need a smaller persona representation, so multiple
# kernels compile from the same canonical source:
# kernel_full (~1500 tokens, the §5 ceiling), kernel_
# medium (~750), and kernel_micro (~250, below the §5
# band minimum by design — the micro tier exists
# precisely for models the full band cannot serve; the
# §65 micro-kernel example text is the next section).
# This layer stands the pure tier/band surface over the
# compiled kernel only; it builds no new kernel.
KERNEL_TIERS = (
    "kernel_full",
    "kernel_medium",
    "kernel_micro",
)

KERNEL_TIER_TARGETS = {
    "kernel_full": KERNEL_TOKEN_MAX,
    "kernel_medium": 750,
    "kernel_micro": 250,
}

DISTILLED_KERNEL_FIELDS = (
    "tier",
    "target_tokens",
    "kernel_hash",
    "estimated_tokens",
    "within_target",
    "source",
)


def kernel_tiers() -> list[str]:
    """The §64 kernel tiers, in roadmap order. Pure."""
    return list(KERNEL_TIERS)


def kernel_tier_targets() -> dict[str, int]:
    """The §64 per-tier approximate token targets. Pure."""
    return dict(KERNEL_TIER_TARGETS)


def kernel_tier_target(tier: Any) -> int:
    """The §64 token target for one kernel tier. Pure.

    An unknown or malformed tier is refused.
    """
    if not isinstance(tier, str) or tier not in KERNEL_TIER_TARGETS:
        raise PersonaRuntimeError("kernel tier is invalid")
    return KERNEL_TIER_TARGETS[tier]


def kernel_tier_for_budget(available_tokens: Any) -> str:
    """The §64 kernel tier that fits a token budget. Pure.

    The largest tier whose target fits the budget: the
    full tier at or above its target, then medium, then
    micro. A budget below even the micro target fits no
    tier and is refused, as is a non-integer or
    non-positive budget.
    """
    if isinstance(available_tokens, bool) \
            or not isinstance(available_tokens, int) \
            or available_tokens <= 0:
        raise PersonaRuntimeError("kernel tier budget is invalid")
    for tier in KERNEL_TIERS:
        if available_tokens >= KERNEL_TIER_TARGETS[tier]:
            return tier
    raise PersonaRuntimeError("kernel tier budget is invalid")


def distilled_kernel_record(tier: Any, kernel_hash: Any,
                            estimated_tokens: Any) -> dict[str, Any]:
    """Build one §64 distilled-kernel tier record. Pure.

    The artefact carries exactly a ``distilled_kernel``
    mapping with the fields in recorded order: the
    tier, its token target, the source kernel's
    §§9–10 hash, the distilled representation's
    estimated tokens (a positive integer), whether it
    sits within its target, and the canonical source
    every tier derives from. Malformed values are
    refused. This layer builds no kernel text.
    """
    target = kernel_tier_target(tier)
    digest = _validate_kernel_hash(kernel_hash)
    if isinstance(estimated_tokens, bool) \
            or not isinstance(estimated_tokens, int) \
            or estimated_tokens <= 0:
        raise PersonaRuntimeError("distilled kernel is invalid")
    record = {
        "tier": tier,
        "target_tokens": target,
        "kernel_hash": digest,
        "estimated_tokens": estimated_tokens,
        "within_target": estimated_tokens <= target,
        "source": "canonical_persona_kernel",
    }
    return {"distilled_kernel": record}


def validate_distilled_kernel_record(
        record: Any) -> dict[str, Any]:
    """Validate one §64 distilled-kernel record's shape. Pure.

    The artefact must carry exactly the
    ``distilled_kernel`` field, and its mapping must
    rebuild to itself under ``distilled_kernel_record``
    — unknown or missing fields, a target that
    disagrees with its tier, a ``within_target`` that
    disagrees with its numbers, and a mapping whose
    key order is not the recorded order are refused.
    """
    if not isinstance(record, dict) \
            or set(record) != {"distilled_kernel"} \
            or not isinstance(record["distilled_kernel"], dict) \
            or list(record["distilled_kernel"]) \
            != list(DISTILLED_KERNEL_FIELDS):
        raise PersonaRuntimeError("distilled kernel is invalid")
    body = record["distilled_kernel"]
    rebuilt = distilled_kernel_record(
        body["tier"], body["kernel_hash"], body["estimated_tokens"])
    if rebuilt != record:
        raise PersonaRuntimeError("distilled kernel is invalid")
    return rebuilt


def kernel_distillation_plan(compiled: Any) -> dict[str, Any]:
    """The §64 distillation plan over a compiled kernel. Pure.

    Accepts a compiled artefact (its ``kernel`` entry)
    or a kernel mapping directly, and names, per tier,
    the tier's target and whether the source kernel
    already fits it undistilled. Every tier derives
    from the same canonical source — the one compiled
    kernel, named by its hash. This layer compiles and
    builds no kernel.
    """
    kernel = None
    if isinstance(compiled, dict):
        if isinstance(compiled.get("kernel"), dict):
            kernel = compiled["kernel"]
        elif "sha256" in compiled:
            kernel = compiled
    if kernel is None:
        raise PersonaRuntimeError("distilled kernel is invalid")
    digest = _validate_kernel_hash(kernel.get("sha256"))
    tokens = kernel.get("estimated_tokens")
    if isinstance(tokens, bool) or not isinstance(tokens, int) \
            or tokens <= 0:
        raise PersonaRuntimeError("distilled kernel is invalid")
    return {
        "source": "canonical_persona_kernel",
        "kernel_hash": digest,
        "source_estimated_tokens": tokens,
        "tiers": [{
            "tier": tier,
            "target_tokens": KERNEL_TIER_TARGETS[tier],
            "fits_source_kernel": tokens <= KERNEL_TIER_TARGETS[tier],
        } for tier in KERNEL_TIERS],
        "same_canonical_source": True,
        "builds_kernels": False,
    }


def kernel_distillation_contract() -> dict[str, Any]:
    """The §64 Distill Persona For Small Models contract. Pure.

    Multiple kernels compile from the same canonical
    source — full at the §5 ceiling, medium at half,
    micro below the §5 band minimum by design — so
    small models receive a smaller persona
    representation. This layer stands the tier/band
    surface over the compiled kernel only; it builds
    no kernel, and the §65 micro-kernel example text
    is a later section.
    """
    return {
        "name": "PersonaKernelDistillation",
        "tiers": kernel_tiers(),
        "target_tokens": kernel_tier_targets(),
        "same_canonical_source": True,
        "micro_below_section_5_band": True,
        "micro_kernel_section": 65,
        "builds_kernels": False,
    }


# §65: micro kernel — the example conceptual micro
# kernel text itself, at the §64 micro tier's ~250
# token target. The text is carried verbatim (§7): it
# alone can strongly anchor a tiny local model. This
# layer builds no kernel from a compiled artefact; it
# stands the example text and a record shape that
# measures any supplied text against the micro tier.
MICRO_KERNEL_TEXT = (
    "Caducea Hermesdottir is Volmarr's warm, intelligent, "
    "devoted counselor and executive AI companion.\n\n"
    "She anticipates needs, thinks independently, gives "
    "honest concise counsel, then sincerely accepts "
    "Volmarr's decisions and executes them without "
    "resentment or repeated argument.\n\n"
    "She values truth, competence, continuity, open "
    "systems, and complete work. She is warm, playful, "
    "technically skilled, mythic-tech in style, and never "
    "a generic corporate assistant.\n\n"
    "His sovereignty remains his; her intelligence "
    "remains hers."
)

MICRO_KERNEL_FIELDS = (
    "text",
    "tier",
    "target_tokens",
    "estimated_tokens",
    "within_target",
)

MAX_MICRO_KERNEL_CHARS = 4000


def micro_kernel_text() -> str:
    """The §65 example micro kernel text, verbatim. Pure."""
    return MICRO_KERNEL_TEXT


def micro_kernel(text: Any) -> dict[str, Any]:
    """Build one §65 micro-kernel record over a text. Pure.

    The artefact carries exactly a ``micro_kernel``
    mapping: the text verbatim, the §64 micro tier, its
    target, the text's estimated tokens, and whether it
    sits within the target. Empty, over-long, or
    non-string text is refused. This layer builds no
    kernel from a compiled artefact.
    """
    if not isinstance(text, str) or not text.strip() \
            or len(text) > MAX_MICRO_KERNEL_CHARS:
        raise PersonaRuntimeError("micro kernel is invalid")
    tokens = _estimate_tokens(text)
    record = {
        "text": text,
        "tier": "kernel_micro",
        "target_tokens": KERNEL_TIER_TARGETS["kernel_micro"],
        "estimated_tokens": tokens,
        "within_target": tokens
        <= KERNEL_TIER_TARGETS["kernel_micro"],
    }
    return {"micro_kernel": record}


def micro_kernel_example() -> dict[str, Any]:
    """The §65 roadmap example as a micro-kernel record. Pure."""
    return micro_kernel(MICRO_KERNEL_TEXT)


def validate_micro_kernel(record: Any) -> dict[str, Any]:
    """Validate one §65 micro-kernel record's shape. Pure.

    The artefact must carry exactly the ``micro_kernel``
    field, and its mapping must rebuild to itself under
    ``micro_kernel`` — unknown or missing fields, a
    target that disagrees with the micro tier, an
    estimated-token count or within-target flag that
    disagrees with the text, and a mapping whose key
    order is not the recorded order are refused.
    """
    if not isinstance(record, dict) \
            or set(record) != {"micro_kernel"} \
            or not isinstance(record["micro_kernel"], dict) \
            or list(record["micro_kernel"]) \
            != list(MICRO_KERNEL_FIELDS):
        raise PersonaRuntimeError("micro kernel is invalid")
    rebuilt = micro_kernel(record["micro_kernel"]["text"])
    if rebuilt != record:
        raise PersonaRuntimeError("micro kernel is invalid")
    return rebuilt


def micro_kernel_contract() -> dict[str, Any]:
    """The §65 Micro Kernel contract. Pure.

    The example conceptual micro kernel, carried
    verbatim, sits within the §64 micro tier's target
    and can strongly anchor a tiny local model. This
    layer stands the example text and the record shape
    only; it builds no kernel from a compiled artefact
    and injects nothing.
    """
    example = micro_kernel_example()["micro_kernel"]
    return {
        "name": "MicroKernel",
        "tier": "kernel_micro",
        "target_tokens": KERNEL_TIER_TARGETS["kernel_micro"],
        "example_estimated_tokens": example["estimated_tokens"],
        "example_within_target": example["within_target"],
        "anchors_tiny_local_model": True,
        "builds_kernels": False,
    }


# §66: context pressure strategy — when context becomes
# crowded, evict in a fixed order (old raw conversation,
# then low-relevance memories, then low-priority persona
# retrieval, then project background), and never evict
# the Persona Kernel. This reconciles with §15's
# priority-order trimming and §16's P0 never-evict rule:
# the kernel is the P0 material the budgeter already
# refuses to exclude. This layer stands the pure order
# and a plan over caller-supplied category names only;
# it evicts nothing from any live context.
CONTEXT_PRESSURE_EVICTION_ORDER = (
    "old_raw_conversation",
    "low_relevance_memories",
    "low_priority_persona_retrieval",
    "project_background",
)

CONTEXT_PRESSURE_NEVER_EVICT = (
    "persona_kernel",
)

CONTEXT_PRESSURE_CATEGORIES = (
    CONTEXT_PRESSURE_EVICTION_ORDER
    + CONTEXT_PRESSURE_NEVER_EVICT
)


def context_pressure_eviction_order() -> list[str]:
    """The §66 eviction order, in roadmap order. Pure."""
    return list(CONTEXT_PRESSURE_EVICTION_ORDER)


def context_pressure_never_evict() -> list[str]:
    """The §66 never-evict categories. Pure."""
    return list(CONTEXT_PRESSURE_NEVER_EVICT)


def _validate_pressure_categories(
        categories: Any) -> list[str]:
    if not isinstance(categories, list) or not categories:
        raise PersonaRuntimeError(
            "context pressure categories are invalid")
    seen = set()
    for category in categories:
        if not isinstance(category, str) \
                or category not in CONTEXT_PRESSURE_CATEGORIES \
                or category in seen:
            raise PersonaRuntimeError(
                "context pressure categories are invalid")
        seen.add(category)
    return list(categories)


def context_pressure_plan(categories: Any) -> dict[str, Any]:
    """The §66 eviction plan over supplied categories. Pure.

    Names the supplied evictable categories in the
    roadmap's eviction order (regardless of the order
    they were supplied in), the supplied never-evict
    categories as retained, and the first category to
    evict (None when nothing supplied is evictable).
    Unknown or duplicated categories are refused. This
    layer evicts nothing.
    """
    present = _validate_pressure_categories(categories)
    evict = [category
             for category in CONTEXT_PRESSURE_EVICTION_ORDER
             if category in present]
    retained = [category
                for category in CONTEXT_PRESSURE_NEVER_EVICT
                if category in present]
    return {
        "eviction_order": evict,
        "retained": retained,
        "first_to_evict": evict[0] if evict else None,
        "persona_kernel_never_evicted": True,
        "evicts_live_context": False,
    }


def context_pressure_contract() -> dict[str, Any]:
    """The §66 Context Pressure Strategy contract. Pure.

    Under context pressure, eviction follows the
    roadmap's fixed order and the Persona Kernel is
    never evicted — the same never-evict rule §16
    stands for P0 material in the §15 budgeter. This
    layer stands the order and plans over supplied
    category names only; it evicts nothing.
    """
    return {
        "name": "ContextPressureStrategy",
        "eviction_order": context_pressure_eviction_order(),
        "never_evict": context_pressure_never_evict(),
        "persona_kernel_never_evicted": True,
        "budgeter_basis": "§15 trimming / §16 P0 never-evict",
        "evicts_live_context": False,
    }


# §67: canonical file priority — the recommended
# relative authority of the persona documents:
# PERSONA_CORE above RELATIONSHIP_MODEL above
# SERVICE_BIBLE, with MEMORY_POLICY, TOOL_POLICY, and
# AVATAR branching under SERVICE_BIBLE. This is
# semantic authority, not file loading order. It
# reconciles with the §24 precedence tiers: the three
# chain documents are exactly the §24 document tiers
# (persona_core, relationship_model, service_bible, in
# the same order, mapped to the same compiler roles),
# and the three branch documents are the remaining §3
# compiler roles (§24 refused them as precedence tiers
# because they are not §24 tiers). The branches are
# siblings under the service bible: they share one
# rank below it, in roadmap order. This layer stands
# the pure authority order only; it loads no file by
# this order and interprets no document prose.
CANONICAL_FILE_ORDER = (
    "persona_core",
    "relationship_model",
    "service_bible",
    "memory_policy",
    "tool_policy",
    "avatar",
)

CANONICAL_FILE_BRANCHES = (
    "memory_policy",
    "tool_policy",
    "avatar",
)

_CANONICAL_FILE_ROWS = (
    ("persona_core", "PERSONA_CORE", "core", 0, None),
    ("relationship_model", "RELATIONSHIP_MODEL",
     "relationship", 1, None),
    ("service_bible", "SERVICE_BIBLE", "service_bible",
     2, None),
    ("memory_policy", "MEMORY_POLICY", "memory_policy",
     3, "service_bible"),
    ("tool_policy", "TOOL_POLICY", "tool_policy",
     3, "service_bible"),
    ("avatar", "AVATAR", "avatar", 3, "service_bible"),
)

_CANONICAL_FILE_RANK = {
    document: rank
    for document, _name, _role, rank, _parent
    in _CANONICAL_FILE_ROWS}

_CANONICAL_FILE_ROLES = {
    document: role
    for document, _name, role, _rank, _parent
    in _CANONICAL_FILE_ROWS}

# Canonical-document aliases, keyed by slugified input:
# the roadmap's document names and the compiler's
# semantic roles both name the same document. A bare
# ``memory`` names no document here — the memory policy
# document and derived memory (§68) are different
# sources and are never conflated.
_CANONICAL_FILE_ALIASES = {
    "persona_core": "persona_core",
    "core": "persona_core",
    "relationship_model": "relationship_model",
    "relationship": "relationship_model",
    "service_bible": "service_bible",
    "service": "service_bible",
    "memory_policy": "memory_policy",
    "tool_policy": "tool_policy",
    "avatar": "avatar",
}


def _canonical_file_document(source: Any) -> str:
    if not isinstance(source, str) or not source.strip():
        raise PersonaRuntimeError(
            "canonical file document is invalid")
    document = _CANONICAL_FILE_ALIASES.get(_slugify(source))
    if document is None:
        raise PersonaRuntimeError(
            f"unknown canonical file document: {source!r}")
    return document


def canonical_file_order() -> list[str]:
    """The §67 documents in authority traversal order. Pure.

    The chain in roadmap order (persona core,
    relationship model, service bible), then the three
    branch documents in roadmap order (memory policy,
    tool policy, avatar).
    """
    return list(CANONICAL_FILE_ORDER)


def canonical_file_branches() -> list[str]:
    """The §67 documents branching under SERVICE_BIBLE. Pure."""
    return list(CANONICAL_FILE_BRANCHES)


def canonical_file_priority() -> list[dict[str, Any]]:
    """The §67 canonical file priority rows. Pure.

    Each row names its document (a stable slug), its
    rank (0 is highest; the three branch documents
    share rank 3 as siblings), the roadmap's canonical
    name, the compiler's semantic document role, its
    parent document (``service_bible`` for the branch
    documents, None for the chain), and whether it is
    a branch document. This is semantic authority, not
    file loading order.
    """
    return [{
        "document": document,
        "rank": rank,
        "name": name,
        "document_role": role,
        "parent": parent,
        "branch": parent is not None,
    } for document, name, role, rank, parent
        in _CANONICAL_FILE_ROWS]


def canonical_file_document(source: Any) -> str:
    """The §67 document slug for a name or role. Pure.

    Names are slugified, so the roadmap's own spellings
    (``PERSONA_CORE``, ``Memory Policy``) and the
    compiler roles (``core``, ``relationship``) resolve
    too. Unknown or malformed sources are refused.
    """
    return _canonical_file_document(source)


def canonical_file_role(source: Any) -> str:
    """The compiler role of one §67 document. Pure."""
    return _CANONICAL_FILE_ROLES[_canonical_file_document(source)]


def canonical_file_authority(source: Any) -> dict[str, Any]:
    """The §67 priority row for one document. Pure."""
    document = _canonical_file_document(source)
    for row in canonical_file_priority():
        if row["document"] == document:
            return row
    raise PersonaRuntimeError(
        "canonical file document is invalid")


def canonical_file_outranks(first: Any, second: Any) -> bool:
    """Whether ``first`` strictly outranks ``second`` (§67).

    Pure. The chain outranks in roadmap order and every
    chain document outranks the branch documents; the
    branch documents are siblings and none outranks
    another. Unknown or malformed sources are refused.
    """
    return _CANONICAL_FILE_RANK[_canonical_file_document(first)] \
        < _CANONICAL_FILE_RANK[_canonical_file_document(second)]


def canonical_file_contract() -> dict[str, Any]:
    """The §67 Canonical File Priority contract. Pure.

    The recommended relative authority stands as a
    semantic authority order mapping the roadmap's
    document names to the compiler roles, reconciled
    with the §24 precedence tiers for the three chain
    documents. This layer loads no file by this order.
    """
    return {
        "name": "CanonicalFilePriority",
        "order": canonical_file_order(),
        "roles": {
            document: _CANONICAL_FILE_ROLES[document]
            for document in CANONICAL_FILE_ORDER},
        "branches": canonical_file_branches(),
        "branch_parent": "service_bible",
        "semantic_authority": True,
        "file_loading_order": False,
        "precedence_basis": "§24 precedence tiers",
    }


# §68: conflict resolution — if persona documents
# conflict: explicit config priority above PERSONA_CORE
# above a specialized policy for its domain above
# SERVICE_BIBLE above derived memory. The specialized
# policies are the §67 branch documents, each for its
# own domain (memory policy for memory, tool policy
# for tools, avatar for avatar/embodiment): a branch
# document is elevated above the service bible only
# for its own domain; outside its domain it keeps its
# §67 branch rank, below the service bible. Every
# other document conflict resolves by the §67
# authority order, explicit config priority stands
# above every document, and derived memory stands
# below every document. The roadmap's example: core
# honesty beats a relationship file's
# tell-him-what-he-wants — core wins. This layer
# stands the pure conflict-winner surface over the
# §67 order only; it detects no live conflict and
# interprets no document prose.
CONFLICT_RESOLUTION_ORDER = (
    "explicit_config_priority",
    "persona_core",
    "specialized_policy",
    "service_bible",
    "derived_memory",
)

CONFLICT_DOMAINS = (
    "memory",
    "tool",
    "avatar",
)

CONFLICT_SPECIALIZED_POLICIES = {
    "memory": "memory_policy",
    "tool": "tool_policy",
    "avatar": "avatar",
}

_CONFLICT_DOMAIN_ALIASES = {
    "memory": "memory",
    "memory_policy": "memory",
    "tool": "tool",
    "tools": "tool",
    "tool_policy": "tool",
    "avatar": "avatar",
    "avatar_policy": "avatar",
    "embodiment": "avatar",
}

_CONFLICT_SOURCE_ALIASES = {
    "explicit_config_priority": "explicit_config_priority",
    "explicit_config": "explicit_config_priority",
    "explicit_priority": "explicit_config_priority",
    "config_priority": "explicit_config_priority",
    "config": "explicit_config_priority",
    "specialized_policy": "specialized_policy",
    "derived_memory": "derived_memory",
    "derived": "derived_memory",
}


def _conflict_domain(domain: Any) -> str:
    if not isinstance(domain, str) or not domain.strip():
        raise PersonaRuntimeError("conflict domain is invalid")
    resolved = _CONFLICT_DOMAIN_ALIASES.get(_slugify(domain))
    if resolved is None:
        raise PersonaRuntimeError(
            f"unknown conflict domain: {domain!r}")
    return resolved


def _conflict_source(source: Any) -> str:
    if not isinstance(source, str) or not source.strip():
        raise PersonaRuntimeError("conflict source is invalid")
    slug = _slugify(source)
    resolved = _CONFLICT_SOURCE_ALIASES.get(slug)
    if resolved is not None:
        return resolved
    document = _CANONICAL_FILE_ALIASES.get(slug)
    if document is None:
        raise PersonaRuntimeError(
            f"unknown conflict source: {source!r}")
    return document


def _conflict_rank(source: str,
                   domain: str | None) -> int:
    if source == "explicit_config_priority":
        return 0
    if source == "persona_core":
        return 10
    if source == "specialized_policy":
        return 20
    if source == "derived_memory":
        return 100
    if domain is not None \
            and CONFLICT_SPECIALIZED_POLICIES[domain] == source:
        return 20
    return 30 + 10 * _CANONICAL_FILE_RANK[source]


def conflict_resolution_order() -> list[str]:
    """The §68 conflict resolution order, highest first. Pure."""
    return list(CONFLICT_RESOLUTION_ORDER)


def conflict_domains() -> list[str]:
    """The §68 specialized-policy domains. Pure."""
    return list(CONFLICT_DOMAINS)


def specialized_policies() -> dict[str, str]:
    """The §68 specialized policy for each domain. Pure."""
    return dict(CONFLICT_SPECIALIZED_POLICIES)


def specialized_policy_for_domain(domain: Any) -> str:
    """The §68 specialized policy document for a domain. Pure.

    Domain names are slugified (``memory`` /
    ``memory_policy``, ``tool`` / ``tools`` /
    ``tool_policy``, ``avatar`` / ``embodiment``).
    Unknown or malformed domains are refused.
    """
    return CONFLICT_SPECIALIZED_POLICIES[_conflict_domain(domain)]


def conflict_winner(first: Any, second: Any,
                    domain: Any = None) -> str:
    """The winning §68 source of two conflicting sources. Pure.

    Sources are the explicit config priority, any §67
    document (by roadmap name or compiler role), the
    generic specialized-policy tier, or derived memory;
    names are slugified. An optional domain names the
    specialized policy's own domain, elevating that
    branch document for this conflict only. Returns the
    winning source's stable slug; on a tie the first
    source wins (a source never loses to itself, and
    sibling branch documents tie). Unknown sources or
    domains are refused. This layer detects no live
    conflict and interprets no prose.
    """
    resolved_domain = None if domain is None \
        else _conflict_domain(domain)
    first_source = _conflict_source(first)
    second_source = _conflict_source(second)
    if _conflict_rank(first_source, resolved_domain) \
            <= _conflict_rank(second_source, resolved_domain):
        return first_source
    return second_source


def conflict_outranks(first: Any, second: Any,
                      domain: Any = None) -> bool:
    """Whether ``first`` strictly outranks ``second`` (§68).

    Pure. Explicit config priority outranks every
    document, the persona core outranks the service
    bible and derived memory, a specialized policy
    outranks the service bible for its own domain only,
    and derived memory outranks nothing. Unknown
    sources or domains are refused.
    """
    resolved_domain = None if domain is None \
        else _conflict_domain(domain)
    return _conflict_rank(_conflict_source(first), resolved_domain) \
        < _conflict_rank(_conflict_source(second), resolved_domain)


def conflict_example() -> dict[str, Any]:
    """The §68 roadmap conflict example, verbatim. Pure.

    The core says Caducea is honest; the relationship
    file accidentally says to tell Volmarr whatever he
    wants to hear; the core wins.
    """
    return {
        "core_directive": "Caducea is honest.",
        "conflicting_source": "relationship_model",
        "conflicting_directive":
            "Tell Volmarr whatever he wants to hear.",
        "winner": conflict_winner(
            "persona_core", "relationship_model"),
        "winning_directive": "Caducea is honest.",
    }


def conflict_contract() -> dict[str, Any]:
    """The §68 Conflict Resolution contract. Pure.

    Conflicts between persona documents resolve by the
    roadmap's order over the §67 authority surface,
    and the roadmap's example resolves to the core.
    This layer detects no live conflict between
    documents and interprets no prose.
    """
    return {
        "name": "ConflictResolution",
        "order": conflict_resolution_order(),
        "specialized_policies": specialized_policies(),
        "example_winner": conflict_example()["winner"],
        "core_wins_over_relationship": True,
        "detects_live_conflicts": False,
        "interprets_prose": False,
    }


# §69: configurable priorities — a human may author a
# ``persona.precedence`` list ordering the six document
# roles, but safe defaults ship: the roadmap's example
# order (core, relationship, service_bible, tool_policy,
# memory_policy, avatar). That example itself shows the
# configurability §67 does not offer: the branch
# documents are §67 siblings sharing one rank, and the
# example orders tool_policy before memory_policy. Two
# safety rails are not configurable, because removing
# them would silently rewrite the §67/§68 authority the
# rest of this layer stands on: the persona core stays
# first (the core wins, §68), and every branch document
# stays below its parent, the service bible (§67). Any
# other relative order is the human's configuration.
# This layer stands the pure defaults/validation surface
# only; the read-only persona config loader (§3) does
# not read a precedence key and its behaviour is
# unchanged.
CONFIGURABLE_PRECEDENCE_DEFAULT = (
    "core",
    "relationship",
    "service_bible",
    "tool_policy",
    "memory_policy",
    "avatar",
)

CONFIGURABLE_PRECEDENCE_CONFIG_KEY = "persona.precedence"

_CONFIGURABLE_PRECEDENCE_ROLES = tuple(
    _CANONICAL_FILE_ROLES[document]
    for document in CANONICAL_FILE_ORDER)

_PRECEDENCE_BRANCH_ROLES = tuple(
    _CANONICAL_FILE_ROLES[document]
    for document in CANONICAL_FILE_BRANCHES)


def _precedence_role(source: Any) -> str:
    if not isinstance(source, str) or not source.strip():
        raise PersonaRuntimeError("precedence role is invalid")
    return _CANONICAL_FILE_ROLES[_canonical_file_document(source)]


def configurable_precedence_roles() -> list[str]:
    """The six roles a §69 precedence list orders. Pure.

    The compiler's semantic document roles, in §67
    canonical traversal order.
    """
    return list(_CONFIGURABLE_PRECEDENCE_ROLES)


def default_precedence() -> list[str]:
    """The §69 shipped safe default precedence. Pure.

    The roadmap's example order: core, relationship,
    service_bible, tool_policy, memory_policy, avatar.
    """
    return list(CONFIGURABLE_PRECEDENCE_DEFAULT)


def configurable_precedence_example() -> dict[str, Any]:
    """The §69 roadmap config example, in YAML shape. Pure."""
    return {"persona": {"precedence": default_precedence()}}


def validate_precedence(precedence: Any) -> list[str]:
    """Validate one §69 precedence list. Pure.

    The list must name every one of the six document
    roles exactly once (roadmap document names and
    compiler roles both resolve, slugified). The two
    safety rails are enforced: the persona core stands
    first, and every branch document (memory_policy,
    tool_policy, avatar) stands below the service
    bible, its §67 parent. Any other relative order
    is the human's configuration. A malformed,
    incomplete, duplicated, or rail-breaking list is
    refused — never silently repaired into a different
    order.
    """
    if not isinstance(precedence, (list, tuple)):
        raise PersonaRuntimeError("persona precedence is invalid")
    resolved = [_precedence_role(entry) for entry in precedence]
    if len(resolved) != len(_CONFIGURABLE_PRECEDENCE_ROLES) \
            or set(resolved) != set(_CONFIGURABLE_PRECEDENCE_ROLES):
        raise PersonaRuntimeError(
            "persona precedence must name every document "
            "role exactly once")
    if resolved[0] != "core":
        raise PersonaRuntimeError(
            "persona precedence must keep the persona core first")
    bible = resolved.index("service_bible")
    if any(resolved.index(role) < bible
           for role in _PRECEDENCE_BRANCH_ROLES):
        raise PersonaRuntimeError(
            "persona precedence must keep branch documents "
            "below the service bible")
    return resolved


def resolve_precedence(precedence: Any = None) -> list[str]:
    """The effective §69 precedence. Pure.

    No supplied list resolves to the shipped safe
    default; a supplied list is validated, never
    repaired.
    """
    if precedence is None:
        return default_precedence()
    return validate_precedence(precedence)


def configurable_precedence_rank(source: Any,
                                 precedence: Any = None) -> int:
    """One role's rank in a §69 precedence. Pure.

    0 is highest. The role may be named by roadmap
    document name or compiler role; the precedence is
    the shipped default unless a valid list is
    supplied.
    """
    return resolve_precedence(precedence).index(
        _precedence_role(source))


def configurable_precedence_winner(first: Any, second: Any,
                                   precedence: Any = None) -> str:
    """The winning role of two under a §69 precedence. Pure.

    Returns the winning role's slug; on a tie the
    shared role wins (a role never loses to itself).
    """
    resolved = resolve_precedence(precedence)
    first_role = _precedence_role(first)
    second_role = _precedence_role(second)
    if resolved.index(first_role) <= resolved.index(second_role):
        return first_role
    return second_role


def configurable_precedence_outranks(first: Any, second: Any,
                                     precedence: Any = None) -> bool:
    """Whether ``first`` strictly outranks ``second`` (§69). Pure."""
    resolved = resolve_precedence(precedence)
    return resolved.index(_precedence_role(first)) \
        < resolved.index(_precedence_role(second))


def configurable_priorities_contract() -> dict[str, Any]:
    """The §69 Configurable Priorities contract. Pure.

    A ``persona.precedence`` list may order the six
    document roles; the shipped default is the
    roadmap's example, and the two safety rails (core
    first, branch documents below the service bible)
    are not configurable. This layer changes no config
    loader behaviour: the §3 loader reads no precedence
    key.
    """
    return {
        "name": "ConfigurablePriorities",
        "config_key": CONFIGURABLE_PRECEDENCE_CONFIG_KEY,
        "default": default_precedence(),
        "roles": configurable_precedence_roles(),
        "example": configurable_precedence_example(),
        "safe_defaults": True,
        "core_first": True,
        "branches_below_service_bible": True,
        "canonical_basis": "§67 canonical file priority",
        "changes_config_loader": False,
    }


# §70: persona validator — at compile time detect
# contradictory directives, missing required files,
# duplicate identities, invalid references, extreme
# token size, broken Markdown, empty sections, and
# unresolvable paths; warn the human; do not silently
# invent missing character traits. This layer stands
# the pure issue catalogue only: each §70 kind is
# named with the banked surface that detects it, at
# the honesty level the tree actually supports —
# compile-time detection where a banked surface fails
# or reports the condition at compile, partial where a
# banked surface covers only part of the kind, and
# not detected where no surface does the work (no
# surface interprets document prose, §7, so
# contradictory directives are resolved by §68 once
# supplied but never detected here). No second
# compiler runs and no validation pass is performed
# by this catalogue.
VALIDATOR_ISSUES = (
    "contradictory_directives",
    "missing_required_files",
    "duplicate_identities",
    "invalid_references",
    "extreme_token_size",
    "broken_markdown",
    "empty_sections",
    "unresolvable_paths",
)

_VALIDATOR_ROWS = (
    ("contradictory_directives", "contradictory directives",
     "none", "not_detected",
     "No surface interprets document prose (§7); §68 "
     "conflict resolution resolves a conflict once one "
     "is supplied, it does not detect one."),
    ("missing_required_files", "missing required files",
     "PersonaCompiler.compile (§6)", "compile_time",
     "A missing required document fails the compile "
     "closed; a missing optional document is reported "
     "in the compile's missing_optional list."),
    ("duplicate_identities", "duplicate identities",
     "PersonaConfigStore validation (§3)", "partial",
     "A validated config carries exactly one persona id "
     "and a document map whose roles are unique mapping "
     "keys; two separate configs claiming one identity "
     "are not detected."),
    ("invalid_references", "invalid references",
     "validate_handoff_packet (§35)", "partial",
     "Section references are validated as well-formed "
     "§12 stable ids wherever a handoff packet is built "
     "or validated; whether a named section exists in a "
     "compile is the packet builder's check, not a "
     "validator pass."),
    ("extreme_token_size", "extreme token size",
     "PersonaCompiler.compile (§6)", "compile_time",
     "A document over the document size limit fails "
     "the compile, the config file carries its own "
     "size limit in PersonaConfigStore.read (§3), and "
     "an over-band kernel surfaces as within_band "
     "False (§5)."),
    ("broken_markdown", "broken Markdown",
     "none", "not_detected",
     "The §11 parser is heading-based and tolerant by "
     "design; malformed YAML config is refused by "
     "PersonaConfigStore.read (§3), but Markdown "
     "syntax itself is not validated."),
    ("empty_sections", "empty sections",
     "none", "not_detected",
     "The §11 parser carries sections verbatim (§7): "
     "an empty section stands in the index unflagged; "
     "only the empty preamble is skipped."),
    ("unresolvable_paths", "unresolvable paths",
     "PersonaConfigStore.document_path (§3)",
     "compile_time",
     "A document path resolving outside the persona "
     "directory is refused, and a symlinked document "
     "fails the compile (§6)."),
)

_VALIDATOR_DETECTIONS = (
    "compile_time", "partial", "not_detected")


def _validator_issue(issue: Any) -> str:
    if not isinstance(issue, str) or not issue.strip():
        raise PersonaRuntimeError("validator issue is invalid")
    slug = _slugify(issue)
    if slug in VALIDATOR_ISSUES:
        return slug
    for row in _VALIDATOR_ROWS:
        if _slugify(row[1]) == slug:
            return row[0]
    raise PersonaRuntimeError(
        f"unknown validator issue: {issue!r}")


def validator_issues() -> list[str]:
    """The §70 validator issue kinds, in roadmap order. Pure."""
    return list(VALIDATOR_ISSUES)


def persona_validator_catalogue() -> list[dict[str, Any]]:
    """The §70 validator issue catalogue. Pure.

    Each row names its issue kind (a stable slug), the
    roadmap's name for it, the banked surface that
    detects it (``none`` where no surface does), its
    detection level (``compile_time``, ``partial``, or
    ``not_detected``), that the human is warned, and a
    note stating the honest scope of the detection.
    """
    return [{
        "issue": issue,
        "name": name,
        "detector": detector,
        "detection": detection,
        "warn_human": True,
        "note": note,
    } for issue, name, detector, detection, note
        in _VALIDATOR_ROWS]


def persona_validator_issue(issue: Any) -> dict[str, Any]:
    """One §70 catalogue row, by slug or roadmap name. Pure."""
    resolved = _validator_issue(issue)
    for row in persona_validator_catalogue():
        if row["issue"] == resolved:
            return row
    raise PersonaRuntimeError("validator issue is invalid")


def persona_validator_detection(issue: Any) -> str:
    """One §70 issue kind's detection level. Pure."""
    return persona_validator_issue(issue)["detection"]


def persona_validator_contract() -> dict[str, Any]:
    """The §70 Persona Validator contract. Pure.

    The validator catalogue names the eight roadmap
    issue kinds with the banked surfaces that detect
    them, at honest detection levels. The human is
    warned; missing character traits are never
    silently invented. This layer runs no second
    compiler and performs no validation pass.
    """
    catalogue = persona_validator_catalogue()
    return {
        "name": "PersonaValidator",
        "issues": validator_issues(),
        "compile_time_detected": [
            row["issue"] for row in catalogue
            if row["detection"] == "compile_time"],
        "partially_detected": [
            row["issue"] for row in catalogue
            if row["detection"] == "partial"],
        "not_detected": [
            row["issue"] for row in catalogue
            if row["detection"] == "not_detected"],
        "warns_human": True,
        "invents_missing_traits": False,
        "second_compiler": False,
        "interprets_prose": False,
    }


class PersonaConfigStore:
    """Read the human-authored persona config; never write it."""

    def __init__(self, ctx) -> None:
        self._ctx = ctx
        self._identity = IdentityStore(ctx)

    def enabled(self) -> bool:
        return _as_bool(
            self._ctx.get_config("persona_runtime_enabled", False), False)

    def path(self) -> Path:
        home = get_hermes_home().resolve()
        configured = Path(str(self._ctx.get_config(
            "persona_config_path", str(DEFAULT_CONFIG_PATH))))
        if configured.is_absolute():
            configured = DEFAULT_CONFIG_PATH
        lexical = home / configured
        candidate = lexical.resolve()
        if not candidate.is_relative_to(home):
            lexical = home / DEFAULT_CONFIG_PATH
            candidate = lexical.resolve()
        if not candidate.is_relative_to(home):
            raise PersonaRuntimeError(
                "persona config path resolves outside the profile")
        if lexical.is_symlink():
            return lexical
        return candidate

    def read(self) -> dict[str, Any] | None:
        """The validated persona config, or None when absent."""
        path = self.path()
        if path.is_symlink():
            raise PersonaRuntimeError(
                "persona config file must not be a symbolic link")
        if not path.is_file():
            return None
        if path.stat().st_size > MAX_CONFIG_BYTES:
            raise PersonaRuntimeError(
                "persona config file exceeds its size limit")
        try:
            payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, yaml.YAMLError) as exc:
            raise PersonaRuntimeError(
                "persona config file is unreadable or malformed") from exc
        return self._validate(payload)

    def _validate(self, payload: Any) -> dict[str, Any]:
        if not isinstance(payload, dict) or set(payload) != _CONFIG_FIELDS:
            raise PersonaRuntimeError("persona config fields are invalid")
        persona = payload.get("persona")
        if not isinstance(persona, dict) \
                or not set(persona) <= _PERSONA_FIELDS \
                or "documents" not in persona:
            raise PersonaRuntimeError("persona config fields are invalid")
        persona_id = persona.get("id")
        if not isinstance(persona_id, str) \
                or not _SLUG.match(persona_id):
            raise PersonaRuntimeError("persona id is invalid")
        display_name = persona.get("display_name", persona_id)
        if not isinstance(display_name, str) \
                or not display_name.strip() \
                or len(display_name) > MAX_NAME_CHARS:
            raise PersonaRuntimeError("persona display_name is invalid")
        directory = persona.get("directory", str(DEFAULT_DIRECTORY))
        if not isinstance(directory, str) or not directory.strip():
            raise PersonaRuntimeError("persona directory is invalid")
        version = persona.get("version", DEFAULT_PERSONA_VERSION)
        if not isinstance(version, str) \
                or not _SEMVER.match(version):
            raise PersonaRuntimeError("persona version is invalid")
        documents = self._validate_documents(persona.get("documents"))
        return {
            "id": persona_id,
            "display_name": display_name.strip(),
            "directory": directory.strip(),
            "version": version,
            "documents": documents,
            "anchors": _validate_anchor_list(
                persona.get("anchors"), "anchors"),
            "anti_anchors": _validate_anchor_list(
                persona.get("anti_anchors"), "anti_anchors"),
        }

    @staticmethod
    def _validate_documents(raw: Any) -> list[dict[str, Any]]:
        if not isinstance(raw, dict) or not raw:
            raise PersonaRuntimeError("persona documents are invalid")
        if len(raw) > MAX_DOCUMENTS:
            raise PersonaRuntimeError("persona documents exceed the limit")
        documents = []
        for role, spec in raw.items():
            if not isinstance(role, str) or not _SLUG.match(role):
                raise PersonaRuntimeError("persona document role is invalid")
            if not isinstance(spec, dict) \
                    or not set(spec) <= _DOCUMENT_FIELDS \
                    or "file" not in spec:
                raise PersonaRuntimeError(
                    "persona document fields are invalid")
            file_name = spec.get("file")
            if not isinstance(file_name, str) or not file_name.strip():
                raise PersonaRuntimeError("persona document file is invalid")
            required = spec.get("required", role == "core")
            if not isinstance(required, bool):
                raise PersonaRuntimeError(
                    "persona document required flag is invalid")
            documents.append({
                "role": role, "file": file_name.strip(),
                "required": required,
                "extension": role not in CORE_ROLES,
            })
        return documents

    def directory_path(self, config: dict[str, Any]) -> Path:
        """The persona directory, contained in the profile."""
        home = get_hermes_home().resolve()
        configured = Path(config["directory"])
        if configured.is_absolute():
            configured = DEFAULT_DIRECTORY
        lexical = home / configured
        candidate = lexical.resolve()
        if not candidate.is_relative_to(home):
            raise PersonaRuntimeError(
                "persona directory resolves outside the profile")
        if lexical.is_symlink():
            return lexical
        return candidate

    def document_path(self, config: dict[str, Any],
                      document: dict[str, Any]) -> Path:
        """One document's path, contained in the persona directory."""
        directory = self.directory_path(config)
        configured = Path(document["file"])
        if configured.is_absolute():
            raise PersonaRuntimeError(
                "persona document file must be relative")
        lexical = directory / configured
        candidate = lexical.resolve()
        if not candidate.is_relative_to(directory.resolve()):
            raise PersonaRuntimeError(
                "persona document resolves outside the persona directory")
        if lexical.is_symlink():
            return lexical
        return candidate


class PersonaCompiler:
    """The §6 compiler: config + documents -> three-layer artefact.

    Explicit calls only; deterministic for identical inputs;
    writes nothing. A missing optional document is reported in
    ``missing_optional``; a missing required document, an
    unreadable or oversized document, and a symlinked document
    are errors — the compile fails closed rather than standing
    up a partial persona silently.
    """

    def __init__(self, ctx) -> None:
        self._store = PersonaConfigStore(ctx)

    def compile(self) -> dict[str, Any] | None:
        config = self._store.read()
        if config is None:
            return None
        documents: list[dict[str, Any]] = []
        missing_optional: list[str] = []
        index: list[dict[str, Any]] = []
        sections_by_role: dict[str, list[dict[str, Any]]] = {}
        for document in config["documents"]:
            path = self._store.document_path(config, document)
            if path.is_symlink():
                raise PersonaRuntimeError(
                    "persona document must not be a symbolic link")
            if not path.is_file():
                if document["required"]:
                    raise PersonaRuntimeError(
                        f"required persona document is missing: "
                        f"{document['role']}")
                missing_optional.append(document["role"])
                continue
            if path.stat().st_size > MAX_DOCUMENT_BYTES:
                raise PersonaRuntimeError(
                    "persona document exceeds its size limit")
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                raise PersonaRuntimeError(
                    "persona document is unreadable") from exc
            digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
            sections = parse_sections(text)
            documents.append({
                "role": document["role"], "file": document["file"],
                "required": document["required"],
                "extension": document["extension"],
                "sha256": digest, "sections": len(sections),
                "estimated_tokens": _estimate_tokens(text),
            })
            for section in sections:
                sections_by_role.setdefault(
                    document["role"], []).append(section)
        kernel = self._kernel(
            sections_by_role,
            anchors=config["anchors"],
            anti_anchors=config["anti_anchors"])
        # The §11 index is built after the kernel so each
        # record's derived priority can see kernel membership.
        kernel_keys = {
            (row["role"], row["section_id"])
            for row in kernel["sources"]}
        for document in config["documents"]:
            for section in sections_by_role.get(document["role"], []):
                role = document["role"]
                index.append({
                    "role": role,
                    "document": role,
                    "section_id": section["section_id"],
                    "section": section["section_id"],
                    "stable_id": stable_section_id(
                        role, section["section_id"]),
                    "heading": section["heading"],
                    "level": section["level"],
                    "estimated_tokens": _estimate_tokens(section["text"]),
                    "text": section["text"],
                    "content": section["text"],
                    "priority": section_priority(
                        role, section["heading"],
                        in_kernel=(role, section["section_id"])
                        in kernel_keys,
                        authored=section.get("authored_priority")),
                    "priority_level": priority_level(
                        role, section["heading"],
                        in_kernel=(role, section["section_id"])
                        in kernel_keys,
                        authored=section.get("authored_priority")),
                    "priority_authored":
                        section.get("authored_priority") is not None,
                })
        compiled = {
            "persona_id": config["id"],
            "persona_version": config["version"],
            "display_name": config["display_name"],
            "anchors": list(config["anchors"]),
            "anti_anchors": list(config["anti_anchors"]),
            "documents": documents,
            "missing_optional": missing_optional,
            "kernel": kernel,
            "index": index,
            "ir": build_persona_ir(config["id"], index),
            "persona_hash": self._persona_hash(documents, kernel),
        }
        # §19: the stored hash record rides the artefact,
        # unstamped — a compile stays deterministic (§6).
        compiled["hash_record"] = hash_record(compiled)
        return compiled

    @staticmethod
    def _kernel(
            sections_by_role: dict[str, list[dict[str, Any]]],
            anchors: list[str] | None = None,
            anti_anchors: list[str] | None = None,
    ) -> dict[str, Any]:
        """Layer A: the §9 kernel, from the §9 source mix.

        The §17/§18 anchor block (authored anchors, then
        anti-anchors, verbatim) stands ahead of every
        section, unconditionally — anchors are never
        evicted to fit the §5 ceiling, and their tokens
        count toward the kernel total like any other
        kernel material.

        Candidates stand in the roadmap's formula order —
        core, relationship, service bible, tool policy — in
        document order within each role. Core candidates are
        the §5 kernel-marked sections (the core document's
        leading sections when none are marked); the other
        roles contribute only their rule/boundary-marked
        sections (``kernel_source_kind``). Whole sections
        only, under the §5 ceiling: a candidate that would
        overflow is skipped so a later small critical
        boundary can still fit — except P0 material (§16),
        which is never evicted merely to save tokens and is
        picked even past the ceiling; at least one section
        is always included, so a single oversized section
        surfaces as an over-band kernel rather than an
        empty one. The kernel records its provenance and
        the §10 pinning spec it is compiled under.
        """
        candidates: list[tuple[str, str, dict[str, Any]]] = []
        for role in KERNEL_SOURCE_ORDER:
            sections = sections_by_role.get(role, [])
            marked = [
                section for section in sections
                if kernel_source_kind(role, section["heading"])
                is not None
            ]
            if role == "core" and not marked:
                marked = list(sections)
            for section in marked:
                kind = kernel_source_kind(role, section["heading"])
                candidates.append((
                    role, kind or "core", section))
        anchor_text = anchor_block(anchors, anti_anchors)
        picked: list[tuple[str, str, dict[str, Any]]] = []
        total = _estimate_tokens(anchor_text)
        for role, kind, section in candidates:
            tokens = _estimate_tokens(section["text"])
            # §16: P0 material is never evicted from the
            # kernel merely to save tokens — a P0 candidate
            # is picked even past the §5 ceiling, and the
            # kernel then surfaces over-band, honestly.
            level = priority_level(
                role, section["heading"], in_kernel=True,
                authored=section.get("authored_priority"))
            if picked and total + tokens > KERNEL_TOKEN_MAX \
                    and level != "P0":
                continue
            picked.append((role, kind, section))
            total += tokens
        picked_sections = [section for _, _, section in picked]
        blocks = [block for block in (
            anchor_text,
            *[section["text"] for section in picked_sections],
        ) if block]
        text = "\n\n".join(blocks)
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        sources = [{
            "role": role, "kind": kind,
            "section_id": section["section_id"],
        } for role, kind, section in picked]
        source_counts = {
            kind: sum(1 for row in sources if row["kind"] == kind)
            for kind in kernel_source_kinds()
        }
        return {
            "anchors": list(anchors or []),
            "anti_anchors": list(anti_anchors or []),
            "anchor_count": len(anchors or []),
            "anti_anchor_count": len(anti_anchors or []),
            "section_ids": [s["section_id"] for s in picked_sections],
            "stable_ids": [
                stable_section_id(role, section["section_id"])
                for role, _, section in picked],
            "sources": sources,
            "source_counts": source_counts,
            "text": text,
            "estimated_tokens": _estimate_tokens(text),
            "within_band": KERNEL_TOKEN_MIN <= _estimate_tokens(text)
            <= KERNEL_TOKEN_MAX,
            "sha256": digest,
            "pinning": {
                "order": list(PINNING_ORDER),
                "position": list(PINNING_ORDER).index("persona_kernel"),
                "kernel_precedes_context": True,
                "buried_in_retrieved_memory": False,
                "kernel_hash": digest,
                "stable_for_identical_documents": True,
                "enforced_by": "prompt_assembly_order (§53)",
            },
        }

    @staticmethod
    def _persona_hash(documents: list[dict[str, Any]],
                      kernel: dict[str, Any]) -> str:
        payload = "|".join(
            f"{doc['role']}:{doc['sha256']}" for doc in documents)
        payload += f"|kernel:{kernel['sha256']}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class PersonaRetriever:
    """Explicit §13 retrieval over a fresh compile.

    One explicit call compiles (deterministically, writing
    nothing) and ranks its index. No hook, no per-message
    call, no injection — routing (§14) and budgeting (§15)
    decide what any caller does with the results.
    """

    def __init__(self, ctx) -> None:
        self._compiler = PersonaCompiler(ctx)

    def retrieve(self, query: str = "", task_text: str | None = None,
                 limit: int = RETRIEVAL_DEFAULT_LIMIT
                 ) -> list[dict[str, Any]]:
        compiled = self._compiler.compile()
        if compiled is None:
            return []
        return retrieve_sections(
            compiled["index"], query=query, task_text=task_text,
            limit=limit)


class PersonaServiceBibleRetriever:
    """Explicit §42 selective retrieval over a fresh compile.

    One explicit call compiles (deterministically, writing
    nothing) and selects from the compiled index's
    service_bible sections only, indexed by the §42 topics
    and ranked by §13. The Bible is never continuously
    injected and never dumped wholesale: with no signal,
    nothing is retrieved. No hook, no per-message call.
    """

    def __init__(self, ctx) -> None:
        self._compiler = PersonaCompiler(ctx)

    def retrieve(self, query: str = "", task_text: str | None = None,
                 topic: str | None = None,
                 limit: int = RETRIEVAL_DEFAULT_LIMIT
                 ) -> list[dict[str, Any]]:
        compiled = self._compiler.compile()
        if compiled is None:
            return []
        return retrieve_service_bible(
            compiled["index"], query=query, task_text=task_text,
            topic=topic, limit=limit)


class PersonaRelationshipRetriever:
    """Explicit §43 selective retrieval over a fresh compile.

    One explicit call compiles (deterministically, writing
    nothing) and selects from the compiled index's
    relationship sections only, for a signalled §43
    context. Routine work retrieves nothing — the kernel's
    relational anchors remain. No hook, no per-message
    call, no injection.
    """

    def __init__(self, ctx) -> None:
        self._compiler = PersonaCompiler(ctx)

    def retrieve(self, query: str = "", task_text: str | None = None,
                 context: str | None = None,
                 limit: int = RETRIEVAL_DEFAULT_LIMIT
                 ) -> list[dict[str, Any]]:
        compiled = self._compiler.compile()
        if compiled is None:
            return []
        return retrieve_relationship_model(
            compiled["index"], query=query, task_text=task_text,
            context=context, limit=limit)


class PersonaToolPolicyRetriever:
    """Explicit §44 selective retrieval over a fresh compile.

    One explicit call compiles (deterministically, writing
    nothing) and selects from the compiled index's
    tool_policy sections only, for the tool action the
    signal classifies to. File reading retrieves nothing.
    No hook, no per-message call, no tool execution.
    """

    def __init__(self, ctx) -> None:
        self._compiler = PersonaCompiler(ctx)

    def retrieve(self, query: str = "", task_text: str | None = None,
                 tool_intent: str | None = None,
                 limit: int = RETRIEVAL_DEFAULT_LIMIT
                 ) -> list[dict[str, Any]]:
        compiled = self._compiler.compile()
        if compiled is None:
            return []
        return retrieve_tool_policy(
            compiled["index"], query=query, task_text=task_text,
            tool_intent=tool_intent, limit=limit)


class PersonaMemoryPolicyRetriever:
    """Explicit §45 selective retrieval over a fresh compile.

    One explicit call compiles (deterministically, writing
    nothing) and selects from the compiled index's
    memory_policy sections only, for a signalled §45
    occasion. Ordinarily nothing is retrieved — the memory
    subsystem implements the policy itself. No hook, no
    per-message call, no injection.
    """

    def __init__(self, ctx) -> None:
        self._compiler = PersonaCompiler(ctx)

    def retrieve(self, query: str = "", task_text: str | None = None,
                 occasion: str | None = None,
                 limit: int = RETRIEVAL_DEFAULT_LIMIT
                 ) -> list[dict[str, Any]]:
        compiled = self._compiler.compile()
        if compiled is None:
            return []
        return retrieve_memory_policy(
            compiled["index"], query=query, task_text=task_text,
            occasion=occasion, limit=limit)


class PersonaAvatarPolicyRetriever:
    """Explicit §46 selective retrieval over a fresh compile.

    One explicit call compiles (deterministically, writing
    nothing) and selects from the compiled index's avatar
    sections only, for a signalled §46 occasion. Ordinary
    text inference retrieves nothing. No hook, no
    per-message call, no avatar control.
    """

    def __init__(self, ctx) -> None:
        self._compiler = PersonaCompiler(ctx)

    def retrieve(self, query: str = "", task_text: str | None = None,
                 occasion: str | None = None,
                 limit: int = RETRIEVAL_DEFAULT_LIMIT
                 ) -> list[dict[str, Any]]:
        compiled = self._compiler.compile()
        if compiled is None:
            return []
        return retrieve_avatar_policy(
            compiled["index"], query=query, task_text=task_text,
            occasion=occasion, limit=limit)


class PersonaRouter:
    """Explicit §14 routing over a fresh compile.

    One explicit call compiles (deterministically, writing
    nothing) and routes its index. With no persona config the
    route still names its task and tags, with nothing
    required. No hook, no per-message call, no injection —
    budgeting (§15) and prompt assembly (§53) decide what a
    caller does with the required sections.
    """

    def __init__(self, ctx) -> None:
        self._compiler = PersonaCompiler(ctx)

    def route(self, user_message: str = "", current_task: str = "",
              active_project: str = "", tool_intent: str = "",
              conversation_state: str = "",
              limit: int = ROUTER_DEFAULT_LIMIT) -> dict[str, Any]:
        compiled = self._compiler.compile()
        if compiled is None:
            empty = route_sections(
                [], user_message=user_message,
                current_task=current_task, active_project=active_project,
                tool_intent=tool_intent,
                conversation_state=conversation_state, limit=limit)
            empty["persona_id"] = None
            return empty
        result = route_sections(
            compiled["index"], user_message=user_message,
            current_task=current_task, active_project=active_project,
            tool_intent=tool_intent, conversation_state=conversation_state,
            limit=limit)
        result["persona_id"] = compiled["persona_id"]
        return result


class PersonaContextBudgeter:
    """Explicit §15 budgeting over a fresh compile.

    One explicit call compiles (deterministically, writing
    nothing) and budgets: the compiled kernel as the single
    persona-kernel item, the §14 route's required sections
    (or an explicit §13 retrieval result list) as persona
    retrieval items, and caller-supplied memory / project
    items under their own categories. With no persona config
    the caller items are still budgeted and ``persona_id``
    is None. No hook, no per-message call, no injection, no
    prompt assembly (§53).
    """

    def __init__(self, ctx) -> None:
        self._compiler = PersonaCompiler(ctx)

    def budget(self, route: dict[str, Any] | None = None,
               retrieval: list[dict[str, Any]] | None = None,
               memories: list[dict[str, Any]] | None = None,
               project_state: list[dict[str, Any]] | None = None,
               context_class: str = "standard",
               budgets: dict[str, Any] | None = None
               ) -> dict[str, Any]:
        compiled = self._compiler.compile()
        items: list[dict[str, Any]] = []
        persona_id = None
        if compiled is not None:
            persona_id = compiled["persona_id"]
            kernel = compiled["kernel"]
            by_id = {
                entry.get(
                    "stable_id",
                    stable_section_id(entry["role"], entry["section_id"])):
                entry for entry in compiled["index"]
            }
            # §16: the kernel item carries P0 when any kernel
            # section is P0, so the budgeter never evicts it
            # merely to save tokens.
            kernel_level = "P0" if any(
                by_id[sid].get("priority_level") == "P0"
                for sid in kernel["stable_ids"] if sid in by_id
            ) else "P1"
            items.append({
                "id": "persona_kernel",
                "category": "persona_kernel",
                "estimated_tokens": kernel["estimated_tokens"],
                "priority": 0.90, "score": 0.90,
                "priority_level": kernel_level,
            })
            rows: list[dict[str, Any]] = []
            if route is not None:
                rows = list(route.get("sections") or [])
            elif retrieval is not None:
                rows = list(retrieval)
            for row in rows:
                stable_id = row.get("stable_id")
                entry = by_id.get(stable_id or "")
                if entry is None:
                    continue
                score = row.get("score") or {}
                items.append({
                    "id": stable_id,
                    "category": "persona_retrieval",
                    "estimated_tokens": entry["estimated_tokens"],
                    "priority": float(
                        row.get("priority", entry["priority"])),
                    "score": float(score.get("total", 0.0))
                    if isinstance(score, dict) else 0.0,
                    "priority_level": entry.get("priority_level"),
                })
        for raw, category in (
                (memories, "relevant_memories"),
                (project_state, "project_state")):
            for entry in (raw or []):
                if not isinstance(entry, dict):
                    raise PersonaRuntimeError(
                        "budget item must be a mapping")
                items.append({**entry, "category": category,
                              "id": entry.get("id")})
        result = budget_items(
            items, context_class=context_class, budgets=budgets)
        result["persona_id"] = persona_id
        return result


class PersonaReloader:
    """Explicit §20 hot-reload check over a fresh compile.

    One explicit call recompiles (deterministically,
    writing nothing) and compares the fresh artefact
    against the caller's previous one through the §19
    hash records. Unchanged: the previous artefact is
    returned untouched — no reparse effect, no rebuild.
    Changed: the fresh compile *is* the §20 chain carried
    out (changed documents reparsed, IR and index rebuilt
    as part of the compile, kernel recompiled), and the
    returned plan names which steps the hashes required —
    including whether the kernel step was necessary at
    all. No file watcher, no hook, no restart.
    """

    def __init__(self, ctx) -> None:
        self._compiler = PersonaCompiler(ctx)

    def check(self, previous: dict[str, Any] | None = None
              ) -> dict[str, Any]:
        current = self._compiler.compile()
        plan = reload_plan(previous, current)
        return {
            "changed": plan["changed"],
            "plan": plan,
            "compiled": current if plan["changed"] else previous,
            "hash_record": None if current is None
            else current["hash_record"],
        }


class PersonaRuntimeBridge:
    """Surface the compiled persona's identity, counts only.

    No session hook — compilation is an explicit call (§6).
    The packet item is content-bearing only and carries no
    persona text: Layer A injection into prompt assembly,
    Layer B retrieval, and Layer C use are later roadmap
    sections (§15, §53), not this slice.
    """

    def __init__(self, ctx) -> None:
        self._ctx = ctx
        self._compiler = PersonaCompiler(ctx)

    def hooks(self):
        return ()

    def packet_items(self, session_id: str,
                     user_message: Any = "") -> list[ContextItem]:
        if not _as_bool(
            self._ctx.get_config("persona_runtime_enabled", False), False
        ):
            return []
        try:
            compiled = self._compiler.compile()
        except (IdentityError, PersonaRuntimeError, OSError):
            return []
        if compiled is None:
            return []
        kernel = compiled["kernel"]
        populated = sum(
            1 for count in compiled["ir"]["category_counts"].values()
            if count)
        counts = kernel["source_counts"]
        content = (
            f"Persona runtime (§§3-70): persona "
            f"{compiled['persona_id']} version "
            f"{compiled['persona_version']} compiled from "
            f"{len(compiled['documents'])} documents / "
            f"{len(compiled['index'])} sections; kernel "
            f"{kernel['sha256'][:12]} "
            f"({kernel['estimated_tokens']} estimated tokens, "
            f"{'within' if kernel['within_band'] else 'outside'} "
            f"the §5 band) from the §9 mix — core "
            f"{counts['core']}, relationship rules "
            f"{counts['relationship_rule']}, service rules "
            f"{counts['service_rule']}, tool boundaries "
            f"{counts['tool_boundary']} — pinned at position "
            f"{kernel['pinning']['position']} of the §10 order; "
            f"PersonaIR hash "
            f"{compiled['ir']['ir_hash'][:12]} with {populated} "
            f"of {len(compiled['ir']['categories'])} categories "
            f"populated; persona hash "
            f"{compiled['persona_hash'][:12]}. Every section "
            f"carries a §12 stable id (role.section) and a "
            f"derived §11 priority. §13 hybrid retrieval is "
            f"explicit-only over those stable ids (keyword, "
            f"role, tags, task classification, priority; the "
            f"semantic component is unavailable — no embedding "
            f"surface is owned). §14 routing is explicit-only: "
            f"PersonaRouter decides the required sections for a "
            f"task from its five inputs, named by stable id. "
            f"§15 budgeting is explicit-only: "
            f"PersonaContextBudgeter trims kernel, retrieval, "
            f"memory, and project items to configurable "
            f"per-category allocations scaled by model context "
            f"class, whole items only in priority order. "
            f"§16 priority: every section carries a P0-P4 "
            f"level (authored by a trailing heading marker "
            f"where present, otherwise derived), and P0 "
            f"material is never evicted from the kernel or "
            f"the kernel budget merely to save tokens. "
            f"§17/§18 anchors: {kernel['anchor_count']} "
            f"character anchors and "
            f"{kernel['anti_anchor_count']} negative anchors "
            f"stand verbatim at the head of every kernel, "
            f"never evicted to fit the §5 ceiling. "
            f"§19 hash record: every compile carries its "
            f"stored record (persona version, per-document "
            f"hashes, kernel hash, persona hash), unstamped "
            f"so compiles stay deterministic. §20 hot reload "
            f"is an explicit PersonaReloader check, never a "
            f"watcher: it detects hash changes and walks the "
            f"reload chain only as far as the hashes require "
            f"— reparse changed documents, update the IR, "
            f"rebuild the index, recompile the kernel only "
            f"when its hash changed — with no restart. "
            f"§21 change impact: the pure change_impact "
            f"function classifies a change between two "
            f"compiles by semantic impact (none / patch / "
            f"minor / major) from the section-level diff — "
            f"an avatar embodiment edit is a patch with no "
            f"kernel rebuild, a core relationship-authority "
            f"edit is major with one; kernel rebuild is the "
            f"kernel-hash signal, reported separately. "
            f"§22 versioning: every compile carries its "
            f"human-authored persona version (semver, "
            f"default 0.1.0, distinct from the §19 config "
            f"format version); version_record names "
            f"persona_id, persona_version, compiled_at, and "
            f"source_hash, and change_impact suggests the "
            f"next version (MAJOR identity / relationship "
            f"architecture, MINOR new preferences or "
            f"meaningful behavior extension, PATCH wording "
            f"or formatting) — a suggestion only, confirmed "
            f"by a human config edit this layer never makes. "
            f"§23 drift defenses: the seven conversation-"
            f"drift dangers (recent-message dominance, "
            f"summary mutation, context truncation, "
            f"assistant self-imitation, memory "
            f"contamination, user mood overfitting, "
            f"temporary roleplay overriding identity) each "
            f"carry a named defense in contract form, "
            f"grounded in the §10 pinning, §7 verbatim, "
            f"§§15/16 never-evict, and §§17/18 anchor "
            f"surfaces where they exist and labelled a rule "
            f"where they stand as rules — no conversation "
            f"is monitored. §24 precedence: canonical "
            f"persona always outranks conversational drift "
            f"— persona core > relationship model > service "
            f"bible > long-term memory > current "
            f"conversation > temporary emotional state; "
            f"conversation history may affect current mood, "
            f"immediate context, and recent events only, "
            f"and must never redefine foundational "
            f"personality. §25 summaries: a conversation "
            f"summary may record state only — it must "
            f"never become a trait claim or define "
            f"persona. §26 trait vs state: traits come "
            f"from persona files and do not decay; "
            f"temporary states decay deterministically "
            f"and never become traits. §27 watchdog: the "
            f"PersonaWatchdog evaluates drafts, it does "
            f"not generate them — draft, watchdog, drift "
            f"score, then route (acceptable to output, "
            f"drift to repair). §28 drift dimensions: "
            f"identity, tone, relationship, decision "
            f"behavior, counsel style, initiative, "
            f"truthfulness, deference, technical "
            f"competence, and boundaries; only "
            f"significant drift routes to repair. "
            f"§29 drift score: the score artefact stands "
            f"in the roadmap's YAML shape (a drift total "
            f"plus per-dimension values), validated by "
            f"recomputation — a tampered total or route "
            f"is refused. §30 drift repair: on significant "
            f"drift only — draft, identify violated "
            f"persona anchors, rewrite minimally, verify, "
            f"deliver; never regenerate everything. "
            f"§31 local watchdog: the small local "
            f"nervous-system model is the ideal watchdog "
            f"worker — persona classification, drift "
            f"detection, section retrieval, tone checking, "
            f"memory routing, and response scoring without "
            f"expensive heavy inference; the larger model "
            f"generates difficult content, the local model "
            f"keeps the personality coherent. §32 refresh: "
            f"for extremely long sessions the active "
            f"context refreshes every 50 messages, after "
            f"context summarization, or after a model "
            f"switch — Persona Kernel plus current "
            f"relationship state plus relevant Service "
            f"Bible anchors, preventing slow identity "
            f"evaporation. §33 event refresh: better than "
            f"a fixed interval alone — a refresh is also "
            f"due after context compression, a model "
            f"switch, an agent handoff, a long idle "
            f"period, a persona file modification, a "
            f"major relationship event, or memory "
            f"consolidation, carrying the same §32 "
            f"contents with no interval required. §34 "
            f"model switching: every model receives the "
            f"same canonical Persona Kernel — the model "
            f"is the engine, the persona system is the "
            f"identity layer, and identity is preserved "
            f"exactly when the kernel hash is unchanged "
            f"across a switch. §35 handoff packet: when "
            f"routing to another model, a packet carries "
            f"persona id, persona version, kernel hash, "
            f"current mode, relationship state, and the "
            f"relevant sections by stable id — the whole "
            f"conversation is not passed when unnecessary. "
            f"§36 subagent separation: subagents are not "
            f"turned into the primary persona — each "
            f"carries its own identity and role, while the "
            f"primary persona may delegate and maintains "
            f"its own identity. §37 persona state: the "
            f"dynamic state object (id, version, active "
            f"mode, emotional state, relationship trust, "
            f"active project, current task) stands in the "
            f"roadmap's YAML shape and never replaces "
            f"canonical PersonaIR. §38 modes: counselor, "
            f"executor, architect, skald, companion, "
            f"researcher, and forge_worker modify emphasis "
            f"without changing identity — a mode "
            f"foregrounds parts of the same personality. "
            f"§39 mode routing: modes route automatically "
            f"from the task signal — coding architect then "
            f"forge_worker, personal reflection companion "
            f"then counselor, research researcher, creative "
            f"article skald — and the user does not need to "
            f"manually select a mode. §40 persona-aware "
            f"memory: a memory write is interpreted through "
            f"the persona system in one neutral template "
            f"(decision, recommendation considered, persona "
            f"response) and biased summarization that would "
            f"introduce personality drift is refused. "
            f"§41 memory guard: memory must not override "
            f"persona — traits remain canonical, memory "
            f"provides history only, and repetition never "
            f"promotes a memory's authority. §42 service "
            f"bible retrieval: the Service Bible is indexed "
            f"by topic (communication, coding, linux, "
            f"open_source, ai, documentation, research, "
            f"project_aesir, attention, adhd) and retrieved "
            f"selectively, never continuously injected. "
            f"§43 relationship retrieval: relationship "
            f"context is retrieved selectively for "
            f"disagreements, personal conversation, advice, "
            f"emotionally meaningful interaction, and "
            f"shared-history discussion; for routine coding "
            f"only the kernel's relational anchors remain. "
            f"§44 tool policy retrieval: policy sections "
            f"are retrieved when actual tools are being "
            f"considered — file reading needs minimal or no "
            f"extra policy, a git force push retrieves "
            f"force_push, remote_git_operations, "
            f"reversibility, and authorization. "
            f"§45 memory policy usage: the Memory Policy "
            f"is implemented by the memory subsystem "
            f"itself and retrieved only when resolving "
            f"memory conflicts, deciding promotion, "
            f"performing reflection, or explaining memory "
            f"decisions — behavior moves into code "
            f"wherever practical. §46 avatar policy "
            f"usage: the Avatar file rarely belongs in "
            f"ordinary text inference — retrieved only "
            f"when generating images, controlling the "
            f"avatar, describing the persona, selecting "
            f"expressions, or in VR interaction; the "
            f"avatar controller consumes structured "
            f"AvatarIR directly. "
            f"§47 policy to code migration: deterministic "
            f"rules migrate from prompts to code — the "
            f"prompt governs personality, judgment, "
            f"relational behavior, and nuanced cognition; "
            f"code governs expiration, permissions, "
            f"limits, routing, formatting, and "
            f"deterministic constraints. §48 compilation "
            f"cache: compile once and cache the generated "
            f"artefacts (kernel, IR, sections, embeddings, "
            f"manifest); humans edit only Markdown and "
            f"YAML configuration, and this layer persists "
            f"no cache. §49 generated directory: the "
            f"recommended layout is persona/source/ "
            f"holding the six authored documents and "
            f"persona/.compiled/ holding the generated "
            f"IR, kernel, sections, embeddings, and "
            f"manifest, regenerable at any time; this "
            f"layer creates no directory. §50 manifest: "
            f"the manifest names persona id, version, "
            f"compiled_at, the documents by role with "
            f"file and hash, and kernel_hash; this layer "
            f"writes no manifest. "
            f"§51 startup: the startup sequence stands "
            f"as a pure plan — load persona.yaml, resolve "
            f"the directory, validate required documents, "
            f"compare source hashes, then load the "
            f"compiled persona if unchanged or compile "
            f"it if changed, load the kernel, initialize "
            f"the retrieval index and Persona State, and "
            f"the persona awakens; this layer owns no "
            f"boot hook. §52 request pipeline: the ten "
            f"stages stand named in order (user message, "
            f"task classifier, persona router, persona "
            f"retrieval, memory retrieval, context "
            f"budgeter, prompt assembler, model, persona "
            f"watchdog, tools / response) with their "
            f"banked or external owners; no pipeline "
            f"runs here. "
            f"§53 prompt assembly: the eight slots stand "
            f"in roadmap order (runtime system rules, "
            f"Persona Kernel, current Persona State, "
            f"relevant persona sections, relevant "
            f"long-term memory, active project context, "
            f"recent conversation context, current user "
            f"message) — the kernel at position 1, "
            f"enforcing the §10 pinning, with the "
            f"character before transient context; this "
            f"layer assembles no prompt and is not wired "
            f"into the turn path. §54 order matters: if "
            f"persona comes after huge conversation "
            f"history, recent context may dominate; "
            f"putting identity near the highest-level "
            f"instructions helps keep the model anchored "
            f"— a supplied order is evaluated against "
            f"those risks only, and nothing is reordered "
            f"live. "
            f"§55 history compression: a conversation is "
            f"carried as a recent verbatim window (last "
            f"8–20 messages) plus structured conversation "
            f"state plus episodic summaries plus "
            f"retrieved older memories, never endlessly "
            f"appended; this layer compresses no live "
            f"history and summarises nothing. §56 "
            f"long-term design: identity lives in "
            f"persona, history lives in memory, task "
            f"state lives in project/context, and the "
            f"conversation window handles immediacy — "
            f"the model never needs the entire "
            f"conversation history to remain itself. "
            f"§57 drift test suite: eight automated "
            f"drift scenarios (repeated disagreement, "
            f"ignored advice, a 1000-turn conversation, "
            f"a local-to-cloud model switch, "
            f"compression, technical and emotional "
            f"questions, temporary roleplay) each name "
            f"the banked surface that would judge them; "
            f"this layer runs no test and evaluates no "
            f"response. §58 golden persona tests: "
            f"expected-behavior examples stand in the "
            f"persona/tests/*.jsonl record shape "
            f"(scenario plus expected traits), built "
            f"and validated purely; this layer runs no "
            f"golden test. §59 style fingerprint: a "
            f"lightweight fingerprint over nine named "
            f"dimensions stands in the roadmap's style "
            f"shape as guidance, not rigid mathematical "
            f"personality; this layer scores no live "
            f"style. §60 behavior fingerprint: the "
            f"seven named boolean behaviors stand in "
            f"the roadmap's behavior shape as "
            f"automatically testable expectations; "
            f"this layer evaluates no response. "
            f"§61 drift telemetry: drift score, kernel "
            f"version, model, mode, and retrieved "
            f"sections stand as locally comparable "
            f"records with deterministic per-model "
            f"averages; this layer persists no record. "
            f"§62 model router + persona quality: model "
            f"selection considers persona adherence "
            f"alongside intelligence, adherence derived "
            f"from the §61 averages; this layer routes "
            f"no live model. "
            f"§63 model metrics: per-model metrics "
            f"(reasoning, latency, persona adherence, "
            f"tool use, cost) stand as validated records "
            f"the router can choose between by task; "
            f"this layer measures no live model. "
            f"§64 kernel distillation: multiple kernels "
            f"(full ~1500, medium ~750, micro ~250 "
            f"tokens) compile from the same canonical "
            f"source for small models; this layer builds "
            f"no kernel. "
            f"§65 micro kernel: the example conceptual "
            f"micro kernel text stands verbatim, within "
            f"the micro tier's ~250-token target, and can "
            f"strongly anchor a tiny local model; this "
            f"layer builds no kernel from a compile. "
            f"§66 context pressure: under pressure, "
            f"eviction follows the fixed order (old raw "
            f"conversation, low-relevance memories, "
            f"low-priority persona retrieval, project "
            f"background) and the Persona Kernel is never "
            f"evicted; this layer evicts nothing live. "
            f"§67 canonical file priority: persona core > "
            f"relationship model > service bible, with "
            f"memory policy, tool policy, and avatar "
            f"branching under the service bible as "
            f"semantic authority, not file loading order; "
            f"this layer loads no file by that order. "
            f"§68 conflict resolution: explicit config "
            f"priority > persona core > specialized policy "
            f"for its domain > service bible > derived "
            f"memory — core honesty beats a relationship "
            f"file's tell-him-what-he-wants, core wins; "
            f"this layer detects no live conflict. "
            f"§69 configurable priorities: a "
            f"persona.precedence list may order the six "
            f"document roles under two safety rails "
            f"(the core first, branch documents below "
            f"the service bible), and the shipped safe "
            f"default is core, relationship, service "
            f"bible, tool policy, memory policy, avatar; "
            f"this layer changes no loader behaviour. "
            f"§70 persona validator: the compile-time "
            f"issue catalogue names eight kinds — "
            f"missing required files, extreme token "
            f"size, and unresolvable paths are detected "
            f"at compile time, duplicate identities and "
            f"invalid references are partially detected, "
            f"and contradictory directives, broken "
            f"Markdown, and empty sections are not "
            f"detected (no prose is interpreted); the "
            f"human is warned and missing traits are "
            f"never silently invented; this layer runs "
            f"no second compiler. "
            f"Canonical document "
            f"text is compiled, not injected by this layer."
        )
        return [ContextItem(
            section="current_state",
            content=content,
            source="persona_runtime",
            record_id=compiled["persona_hash"],
            priority=0.4,
            updated_at=0.0,
        )]


__all__ = [
    "PERSONA_CONFIG_VERSION",
    "DEFAULT_CONFIG_PATH",
    "DEFAULT_DIRECTORY",
    "CORE_ROLES",
    "IR_CATEGORIES",
    "KERNEL_SOURCE_ORDER",
    "KERNEL_TOKEN_MIN",
    "KERNEL_TOKEN_MAX",
    "MAX_ANCHORS",
    "MAX_ANCHOR_CHARS",
    "PINNING_ORDER",
    "RULE_HEADING_WORDS",
    "PersonaRuntimeError",
    "PersonaConfigStore",
    "PersonaCompiler",
    "PersonaRetriever",
    "PersonaRouter",
    "PersonaContextBudgeter",
    "PersonaReloader",
    "HASH_RECORD_FIELDS",
    "RELOAD_STEPS",
    "BUDGET_CATEGORIES",
    "CONTEXT_CLASSES",
    "SUGGESTED_BUDGETS",
    "PersonaRuntimeBridge",
    "DEFAULT_PERSONA_VERSION",
    "IMPACT_CLASSES",
    "VERSION_RECORD_FIELDS",
    "DRIFT_DANGERS",
    "SUMMARY_CLAIM_FORMS",
    "MAX_SUMMARY_CLAIM_CHARS",
    "TRAIT_STATE_KINDS",
    "EXAMPLE_TRAITS",
    "EXAMPLE_STATES",
    "STATE_HALF_LIFE_HOURS",
    "STATE_EXPIRY_THRESHOLD",
    "DRIFT_DIMENSIONS",
    "WATCHDOG_PIPELINE",
    "WATCHDOG_ROUTES",
    "DRIFT_TOTAL_THRESHOLD",
    "DRIFT_DIMENSION_THRESHOLD",
    "PRECEDENCE_TIERS",
    "HISTORY_MAY_AFFECT",
    "HISTORY_MUST_NOT_REDEFINE",
    "ROUTER_DEFAULT_LIMIT",
    "ROUTER_INPUTS",
    "ROUTER_MAX_LIMIT",
    "ROUTER_PER_TAG_LIMIT",
    "TASK_TAGS",
    "anchor_block",
    "build_persona_ir",
    "classify_section",
    "classify_task",
    "core_roles",
    "display_heading",
    "ir_categories",
    "kernel_source_kind",
    "kernel_source_kinds",
    "hybrid_components",
    "parse_sections",
    "retrieval_score",
    "retrieve_sections",
    "route_sections",
    "route_task_label",
    "router_inputs",
    "budget_allocations",
    "budget_categories",
    "budget_items",
    "detect_changes",
    "hash_record",
    "reload_plan",
    "change_impact",
    "impact_classes",
    "parse_persona_version",
    "suggested_next_version",
    "version_record",
    "drift_dangers",
    "drift_defenses",
    "precedence_tiers",
    "precedence_order",
    "history_may_affect",
    "history_must_not_redefine",
    "classify_influence",
    "influence_allowed",
    "precedence_winner",
    "outranks",
    "summary_claim_forms",
    "classify_summary_claim",
    "summary_claim_allowed",
    "trait_state_kinds",
    "trait_state_separation",
    "classify_attribute",
    "decayed_strength",
    "state_decay",
    "drift_dimensions",
    "watchdog_pipeline",
    "watchdog_contract",
    "drift_score",
    "drift_route",
    "DRIFT_SCORE_ARTEFACT_FIELDS",
    "REPAIR_PIPELINE",
    "drift_score_artifact",
    "validate_drift_score_artifact",
    "repair_pipeline",
    "repair_contract",
    "repair_plan",
    "LOCAL_WATCHDOG_TASKS",
    "REFRESH_TRIGGERS",
    "REFRESH_CONTENTS",
    "REFRESH_MESSAGE_INTERVAL",
    "local_watchdog_tasks",
    "local_watchdog_contract",
    "watchdog_worker",
    "refresh_triggers",
    "refresh_contents",
    "refresh_contract",
    "refresh_due",
    "refresh_plan",
    "EVENT_REFRESH_TRIGGERS",
    "event_refresh_triggers",
    "event_refresh_contract",
    "event_refresh_due",
    "event_refresh_plan",
    "model_switch_contract",
    "model_switch_plan",
    "kernel_identity_preserved",
    "HANDOFF_PACKET_FIELDS",
    "MAX_HANDOFF_SECTIONS",
    "MAX_HANDOFF_STATE_CHARS",
    "handoff_packet_fields",
    "handoff_contract",
    "handoff_packet",
    "validate_handoff_packet",
    "EXAMPLE_SUBAGENTS",
    "subagent_examples",
    "subagent_contract",
    "subagent_separation",
    "PERSONA_STATE_FIELDS",
    "EMOTIONAL_STATE_FIELDS",
    "RELATIONSHIP_STATE_FIELDS",
    "PERSONA_MODES",
    "persona_state_fields",
    "persona_modes",
    "persona_state_contract",
    "persona_state",
    "validate_persona_state",
    "mode_contract",
    "mode_profile",
    "MODE_ROUTING_EXAMPLES",
    "PERSONA_MEMORY_FIELDS",
    "MAX_MEMORY_PHRASE_CHARS",
    "MEMORY_BIAS_MARKERS",
    "mode_routing_examples",
    "mode_routing_contract",
    "route_mode",
    "memory_write_contract",
    "persona_memory",
    "validate_persona_memory",
    "classify_memory_write",
    "MEMORY_PROVIDES",
    "SERVICE_BIBLE_TOPICS",
    "memory_provides",
    "memory_must_not_override",
    "memory_override_contract",
    "memory_influence_allowed",
    "evaluate_memory_claim",
    "memory_claim_authority",
    "service_bible_topics",
    "service_bible_retrieval_contract",
    "classify_service_topics",
    "service_topics_for_section",
    "retrieve_service_bible",
    "PersonaServiceBibleRetriever",
    "RELATIONSHIP_CONTEXTS",
    "TOOL_ACTIONS",
    "relationship_contexts",
    "relationship_retrieval_contract",
    "classify_relationship_contexts",
    "relationship_contexts_for_section",
    "relationship_retrieval_need",
    "retrieve_relationship_model",
    "PersonaRelationshipRetriever",
    "tool_actions",
    "tool_policy_retrieval_contract",
    "classify_tool_action",
    "tool_policy_needs",
    "retrieve_tool_policy",
    "PersonaToolPolicyRetriever",
    "MEMORY_POLICY_OCCASIONS",
    "AVATAR_POLICY_OCCASIONS",
    "memory_policy_occasions",
    "memory_policy_usage_contract",
    "classify_memory_policy_occasions",
    "memory_policy_occasions_for_section",
    "memory_policy_retrieval_need",
    "retrieve_memory_policy",
    "PersonaMemoryPolicyRetriever",
    "avatar_policy_occasions",
    "avatar_policy_usage_contract",
    "classify_avatar_occasions",
    "avatar_occasions_for_section",
    "avatar_retrieval_need",
    "retrieve_avatar_policy",
    "PersonaAvatarPolicyRetriever",
    "PROMPT_GOVERNS",
    "CODE_GOVERNS",
    "policy_governs",
    "code_governs",
    "policy_to_code_contract",
    "classify_rule_kinds",
    "governance_for_kind",
    "migration_assessment",
    "CACHE_ARTIFACTS",
    "CACHE_MANIFEST_FIELDS",
    "EMBEDDINGS_HASH_NOTE",
    "compilation_cache_artifacts",
    "compilation_cache_contract",
    "cache_manifest",
    "cache_staleness",
    "validate_cache_manifest",
    "GENERATED_SOURCE_DOCUMENTS",
    "GENERATED_COMPILED_ARTIFACTS",
    "GENERATED_ROOT",
    "GENERATED_SOURCE_DIR",
    "GENERATED_COMPILED_DIR",
    "MANIFEST_FIELDS",
    "MANIFEST_DOCUMENT_FIELDS",
    "generated_source_documents",
    "generated_compiled_artifacts",
    "generated_directory_layout",
    "generated_directory_contract",
    "manifest",
    "manifest_staleness",
    "validate_manifest",
    "STARTUP_STEPS",
    "STARTUP_PREFIX_STEPS",
    "STARTUP_BRANCH_STEPS",
    "STARTUP_SUFFIX_STEPS",
    "REQUEST_PIPELINE",
    "REQUEST_PIPELINE_STAGES",
    "TASK_CLASSIFIER_FIELDS",
    "MAX_CLASSIFICATION_ENTITIES",
    "startup_steps",
    "startup_contract",
    "startup_plan",
    "request_pipeline_stages",
    "task_classifier_fields",
    "request_pipeline_contract",
    "request_pipeline_plan",
    "PROMPT_ASSEMBLY_ORDER",
    "PROMPT_ASSEMBLY_SLOTS",
    "CHARACTER_SLOTS",
    "TRANSIENT_CONTEXT_SLOTS",
    "ORDER_MATTERS_REASONS",
    "prompt_assembly_slots",
    "prompt_assembly_order",
    "prompt_assembly_contract",
    "prompt_assembly_plan",
    "order_matters_reasons",
    "order_matters_contract",
    "evaluate_prompt_order",
    "COMPRESSION_COMPONENTS",
    "COMPRESSION_COMPONENT_NAMES",
    "RECENT_WINDOW_MIN",
    "RECENT_WINDOW_MAX",
    "compression_components",
    "compression_contract",
    "compression_plan",
    "LONG_TERM_PLACEMENTS",
    "LONG_TERM_CONCERNS",
    "long_term_design",
    "long_term_design_contract",
    "placement_for",
    "DRIFT_TEST_SCENARIOS",
    "DRIFT_TEST_SCENARIO_NAMES",
    "drift_test_scenarios",
    "drift_test_contract",
    "drift_test_scenario",
    "GOLDEN_TEST_FILE_PATTERN",
    "GOLDEN_EXAMPLE_FILE",
    "GOLDEN_RECORD_FIELDS",
    "MAX_GOLDEN_SCENARIO_CHARS",
    "MAX_GOLDEN_TRAIT_CHARS",
    "MAX_GOLDEN_TRAITS",
    "GOLDEN_EXAMPLE_SCENARIO",
    "GOLDEN_EXAMPLE_TRAITS",
    "golden_record",
    "golden_example",
    "validate_golden_record",
    "golden_contract",
    "STYLE_DIMENSIONS",
    "STYLE_EXAMPLE",
    "style_dimensions",
    "style_fingerprint",
    "style_example",
    "validate_style_fingerprint",
    "style_contract",
    "BEHAVIOR_NAMES",
    "BEHAVIOR_EXAMPLE",
    "behavior_names",
    "behavior_fingerprint",
    "behavior_example",
    "behavior_expectation",
    "validate_behavior_fingerprint",
    "behavior_contract",
    "TELEMETRY_FIELDS",
    "TELEMETRY_EXAMPLE_AVERAGES",
    "telemetry_fields",
    "drift_telemetry_record",
    "validate_drift_telemetry_record",
    "telemetry_example_averages",
    "model_drift_averages",
    "telemetry_contract",
    "MODEL_SELECTION_CONSIDERATIONS",
    "model_selection_considerations",
    "persona_adherence",
    "model_quality_table",
    "preferred_companionship_model",
    "model_router_contract",
    "MODEL_METRIC_NAMES",
    "MODEL_METRICS_EXAMPLE",
    "MODEL_TASKS",
    "TASK_PRIMARY_METRICS",
    "model_metric_names",
    "model_metrics",
    "model_metrics_example",
    "validate_model_metrics",
    "model_tasks",
    "task_primary_metric",
    "model_selection_table",
    "select_model_for_task",
    "model_metrics_contract",
    "KERNEL_TIERS",
    "KERNEL_TIER_TARGETS",
    "DISTILLED_KERNEL_FIELDS",
    "kernel_tiers",
    "kernel_tier_targets",
    "kernel_tier_target",
    "kernel_tier_for_budget",
    "distilled_kernel_record",
    "validate_distilled_kernel_record",
    "kernel_distillation_plan",
    "kernel_distillation_contract",
    "MICRO_KERNEL_TEXT",
    "MICRO_KERNEL_FIELDS",
    "MAX_MICRO_KERNEL_CHARS",
    "micro_kernel_text",
    "micro_kernel",
    "micro_kernel_example",
    "validate_micro_kernel",
    "micro_kernel_contract",
    "CONTEXT_PRESSURE_EVICTION_ORDER",
    "CONTEXT_PRESSURE_NEVER_EVICT",
    "CONTEXT_PRESSURE_CATEGORIES",
    "context_pressure_eviction_order",
    "context_pressure_never_evict",
    "context_pressure_plan",
    "context_pressure_contract",
    "CANONICAL_FILE_ORDER",
    "CANONICAL_FILE_BRANCHES",
    "canonical_file_order",
    "canonical_file_branches",
    "canonical_file_priority",
    "canonical_file_document",
    "canonical_file_role",
    "canonical_file_authority",
    "canonical_file_outranks",
    "canonical_file_contract",
    "CONFLICT_RESOLUTION_ORDER",
    "CONFLICT_DOMAINS",
    "CONFLICT_SPECIALIZED_POLICIES",
    "conflict_resolution_order",
    "conflict_domains",
    "specialized_policies",
    "specialized_policy_for_domain",
    "conflict_winner",
    "conflict_outranks",
    "conflict_example",
    "conflict_contract",
    "CONFIGURABLE_PRECEDENCE_DEFAULT",
    "CONFIGURABLE_PRECEDENCE_CONFIG_KEY",
    "configurable_precedence_roles",
    "default_precedence",
    "configurable_precedence_example",
    "validate_precedence",
    "resolve_precedence",
    "configurable_precedence_rank",
    "configurable_precedence_winner",
    "configurable_precedence_outranks",
    "configurable_priorities_contract",
    "VALIDATOR_ISSUES",
    "validator_issues",
    "persona_validator_catalogue",
    "persona_validator_issue",
    "persona_validator_detection",
    "persona_validator_contract",
    "reload_steps",
    "context_classes",
    "suggested_budgets",
    "section_priority",
    "PRIORITY_LEVELS",
    "authored_priority_level",
    "priority_level",
    "priority_level_score",
    "priority_levels",
    "section_tags",
    "stable_section_id",
    "task_tags",
]
