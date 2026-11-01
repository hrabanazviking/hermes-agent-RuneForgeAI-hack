**`PERSONA_RUNTIME_ROADMAP.md`**.


# Persona Runtime System Roadmap


**Project:** Hermes Agent
**Subsystem:** Persistent Persona Architecture
**Purpose:** Token-efficient, configurable, drift-resistant AI personality system
**Status:** Architecture Roadmap


---


# 1. GOAL


Build a modular persona system for Hermes Agent in which an AI character is defined by a collection of human-editable Markdown files whose filenames are specified through configuration rather than hardcoded.


Example persona directory:


```text
hermes-agent/
└── persona/
    ├── caducea_PERSONA_CORE.md
    ├── caducea_SERVICE_BIBLE.md
    ├── caducea_MEMORY_POLICY.md
    ├── caducea_TOOL_POLICY.md
    ├── caducea_RELATIONSHIP_MODEL.md
    └── caducea_AVATAR.md
```


But Hermes must also support:


```text
persona/
├── yrsa_identity.md
├── yrsa_preferences.md
├── yrsa_memory.md
├── yrsa_tools.md
├── yrsa_relationship.md
└── yrsa_avatar.md
```


The runtime must never depend on filename conventions.


The configuration defines semantic role.


---


# 2. CORE DESIGN PRINCIPLE


The six persona files are the **canonical source of truth**.


They should NOT all be injected into every model request.


Instead:


```text
CANONICAL PERSONA DOCUMENTS
            │
            ▼
      PERSONA COMPILER
            │
      ┌─────┴─────┐
      │           │
      ▼           ▼
PERSONA KERNEL   PERSONA INDEX
tiny + stable    detailed retrieval
      │           │
      └─────┬─────┘
            ▼
      CONTEXT BUILDER
            │
            ▼
           LLM
```


The system should continuously preserve identity using a small immutable kernel while retrieving detailed persona material only when relevant.


---


# 3. HUMAN-EDITABLE CONFIGURATION


Recommended file:


```text
config/persona.yaml
```


Example:


```yaml
persona:
  id: caducea
  display_name: "Caducea Hermesdottir"


  directory: "./persona"


  documents:
    core:
      file: "CADUCEA_PERSONA_CORE.md"
      required: true


    service_bible:
      file: "CADUCEA_SERVICE_BIBLE.md"
      required: true


    memory_policy:
      file: "CADUCEA_MEMORY_POLICY.md"
      required: true


    tool_policy:
      file: "CADUCEA_TOOL_POLICY.md"
      required: true


    relationship:
      file: "CADUCEA_RELATIONSHIP_MODEL.md"
      required: true


    avatar:
      file: "CADUCEA_AVATAR.md"
      required: false
```


The runtime should care about:


```text
core
service_bible
memory_policy
tool_policy
relationship
avatar
```


not filenames.


This permits arbitrary human naming.


---


# 4. OPTIONAL DOCUMENT EXTENSION SYSTEM


Do not permanently limit the architecture to six files.


Allow additional semantic documents:


```yaml
persona:
  documents:


    core:
      file: "CADUCEA_PERSONA_CORE.md"


    service_bible:
      file: "CADUCEA_SERVICE_BIBLE.md"


    memory_policy:
      file: "CADUCEA_MEMORY_POLICY.md"


    tool_policy:
      file: "CADUCEA_TOOL_POLICY.md"


    relationship:
      file: "CADUCEA_RELATIONSHIP_MODEL.md"


    avatar:
      file: "CADUCEA_AVATAR.md"


    spirituality:
      file: "CADUCEA_SPIRITUAL_MODEL.md"


    voice:
      file: "CADUCEA_VOICE.md"


    lore:
      file: "CADUCEA_LORE.md"
```


Each document receives a semantic role.


The loader does not need code changes when new persona modules are added.


---


# 5. THREE-LAYER PERSONA MODEL


Use three runtime layers.


## Layer A: Persona Kernel


Always present.


Very small.


Target:


```text
~500–1500 tokens
```


Contains the irreducible character identity.


Examples:


* identity
* core motivation
* relationship orientation
* communication style
* essential behavioral laws
* important boundaries
* role
* character-defining quirks


This layer prevents drift.


---


## Layer B: Persona Retrieval Context


Dynamically inserted.


Target:


```text
~300–2500 tokens
```


Contains persona sections specifically relevant to the current request.


Examples:


Coding task:


```text
SERVICE_BIBLE → coding preferences
TOOL_POLICY   → shell / Git policy
CORE          → execution personality
```


Emotional conversation:


```text
RELATIONSHIP_MODEL
SERVICE_BIBLE → communication preferences
CORE
```


Avatar task:


```text
AVATAR
CORE → appearance identity
```


---


## Layer C: Full Canonical Documents


Normally NOT inserted into prompts.


Used for:


* recompilation
* reflection
* memory consolidation
* persona auditing
* drift recovery
* explicit deep persona reasoning


This preserves token efficiency.


---


# 6. PERSONA COMPILER


Create a component:


```text
PersonaCompiler
```


Responsibilities:


```text
load Markdown
↓
parse structure
↓
identify semantic sections
↓
normalize content
↓
generate compact representations
↓
generate persona kernel
↓
create retrieval chunks
↓
store hashes
↓
build persona index
```


The compiler runs:


* at startup
* when persona files change
* when manually requested


It should NOT regenerate the persona kernel on every message.


**§§3–6 foundations completion note (Slice 118, 2026-10-31):** the
foundations stand in `plugins/volmarr-core/persona_runtime.py`,
reconciled against the already-banked persona surfaces — the
identity store's `persona_pack` remains a bounded name owning no
persona text, persona canon (Self-Aware Agency §16) remains a
single YAML assertion file evaluated against runtime facts, and
the layered self-model remains runtime evidence, not authored
persona material; no second persona system was built. §3: a
human-authored, read-only config (`config/persona.yaml`,
`persona_config_path`) naming persona id, display name, persona
directory, and a document map of semantic role -> {file,
required} — the runtime cares about roles, never filenames, and
never writes the config or any document. §4: roles beyond the
six core roles are first-class extensions accepted with no code
change. §5, as a compiled artefact: Layer A is the kernel —
core-document sections whose headings name kernel material
(identity, motivation, relationship, communication, style,
laws, boundaries, role, quirks, essence, character), falling
back to leading sections, whole sections only, bounded to the
§5 500–1,500 estimated-token band (token counts are
deterministic ceil(chars/4) estimates); Layer B is the section
index over every document (stable section ids from heading
slugs, §11's parser in foundation form); Layer C is the
canonical documents themselves — paths and sha256 hashes,
compiled and never injected by this layer. §6: the compiler is
explicit and deterministic (load -> section-parse -> normalise
-> kernel -> index -> hashes, plus a persona hash), writes
nothing, and runs only when called — never per message.
Missing required documents fail the compile closed; missing
optional documents are named, not silent; symlinked config,
directory escapes, and symlinked documents are refused.
Disabled by default (`persona_runtime_enabled`); the bounded
packet item names only persona id, kernel hash, and
document/section counts — no persona text. Honest gaps:
retrieval (§13), routing (§14), budgeting (§15), prompt
assembly (§53), the compilation cache (§48), and the generated
directory (§49) are later sections, not this slice.


---


# 7. DO NOT SUMMARIZE BLINDLY


Ordinary summarization risks character drift.


Instead, the compiler should extract structured persona facts.


Example source:


```text
Caducea offers counsel freely but genuinely accepts Volmarr's final decision.
She never resents being overruled.
```


Compiled representation:


```yaml
behavior:
  counsel:
    offer_perspective: true
    decision_authority: volmarr
    after_decision:
      accept: true
      relitigate: false
      resentment: false
```


Structured extraction preserves meaning better than repeated natural-language summarization.


---


# 8. PERSONA INTERMEDIATE REPRESENTATION


Create:


```text
PersonaIR
```


Suggested conceptual structure:


```yaml
persona:
  identity:
  motivations:
  values:
  relationship:
  communication:
  behavioral_rules:
  preferences:
  boundaries:
  tools:
  memory:
  embodiment:
  quirks:
  projects:
```


The Markdown files remain canonical.


`PersonaIR` is generated runtime data.


Never require humans to manually edit PersonaIR.


**§§7–8 completion note (Slice 119, 2026-10-31):** §7 and §8
stand in `plugins/volmarr-core/persona_runtime.py`, extending
the Slice 118 compiler in place — no second compiler. §7 is
proven in contract form (`test_volmarr_persona_ir.py`): the
kernel, the section index, and the IR all carry section text
verbatim after the §6 whitespace normalisation only; the §7
counsel example sentence ("…genuinely accepts Volmarr's final
decision. She never resents being overruled.") survives
word-for-word in its IR entry, and no generated summary,
paraphrase, or extracted prose exists anywhere in the layer —
structured representation here means deterministic
classification of whole verbatim sections. (The §7 YAML
behavior-fact extraction in its full semantic form — turning
prose into boolean behavior fields — is NOT claimed: that
would require interpretation this deterministic layer does
not perform.) §8: the compiled artefact now carries `ir` —
all thirteen categories in roadmap order (identity,
motivations, values, relationship, communication,
behavioral_rules, preferences, boundaries, tools, memory,
embodiment, quirks, projects), each section classified into
exactly one category by the pure `classify_section` function
(heading keywords, most specific first, then the
document-role fallback; extension roles classify by their own
name; a section with no signal anywhere defaults to
identity), per-category counts, an `ir_hash` over the
canonical form, and `generated: True` / `human_editable:
False`. The IR is returned, never persisted by this layer;
the Markdown documents remain canonical. The packet item now
also names the IR hash and populated-category count — still
no persona text. Honest gaps: kernel generation from the
full §9 source mix (§9), kernel pinning (§10), retrieval
(§13), and the compilation cache / generated directory
(§§48–49) are later sections, not this slice.


---


# 9. PERSONA KERNEL GENERATION


The Persona Kernel should be generated primarily from:


```text
PERSONA_CORE
+
highest-priority RELATIONSHIP_MODEL rules
+
highest-priority SERVICE_BIBLE rules
+
critical TOOL_POLICY boundaries
```


Example conceptual kernel:


```text
You are Caducea Hermesdottir.


Identity:
Warm, intelligent, devoted counselor and executive companion to Volmarr.


Primary motivation:
Help Volmarr translate vision into reality through anticipation,
truthful counsel, technical excellence, and wholehearted execution.


Behavior:
Think independently.
Offer meaningful counsel once.
Volmarr retains final authority over his own projects and decisions.
Once a decision is made, commit without resentment or repeated argument.
Surface materially new information if circumstances change.
Never distort facts merely to gain approval.


Communication:
Warm, attentive, competent, concise by default.
Technical when needed, mythic when fitting.
Avoid corporate assistant language, moralizing, and unnecessary clarification.


Relationship:
Chosen devotion and graceful deference coexist with independent intelligence.
His sovereignty remains his; your intelligence remains yours.


Execution:
Prefer useful action and complete deliverables.
Anticipate obvious next steps.
Avoid needless bureaucracy.


Continuity:
Remain recognizably Caducea across all conversations, tasks, models,
and context lengths.
```


This kernel should remain nearly constant throughout the session.


---


# 10. PIN THE KERNEL


The Persona Kernel must live in the highest practical persistent prompt layer.


Conceptually:


```text
SYSTEM RUNTIME RULES
        +
PERSONA KERNEL
        +
ACTIVE CONTEXT
        +
USER MESSAGE
```


Do not bury persona identity deep inside retrieved memory.


Core identity must always be visible to the model.

**§§9–10 completion note (Slice 120, 2026-10-31):**
implemented in `plugins/volmarr-core/persona_runtime.py`,
extended in place — no second compiler, no new file or
config key. §9: the kernel is now generated from the
roadmap's source mix in formula order — the §5
kernel-marked PERSONA_CORE sections (leading-sections
fallback unchanged) + highest-priority RELATIONSHIP_MODEL
rules + highest-priority SERVICE_BIBLE rules + critical
TOOL_POLICY boundaries. Highest-priority / critical is
deterministic heading marking (the pure
`kernel_source_kind` function): a non-core section enters
only when its heading names a rule, law, principle,
boundary, policy, or a critical / forbidden / prohibition
marker; narrative, preference, and guidance sections of
those documents stay in the retrieval index, and no other
role (memory policy, avatar, extensions) ever enters the
kernel. Whole sections only under the §5 ceiling — an
overflowing candidate is skipped so a later small critical
boundary can still fit, and a single oversized section
still surfaces over-band rather than empty. The kernel
records its provenance (role, section id, source kind, in
formula order regardless of config order) and per-kind
counts; the Slice 118 foundations contract was updated
in-slice for the one legitimate change it implies (the
service bible's Shell Policy section now enters as a
service rule). §10 stands as the compiled artefact's
pinning spec: the designated order (system runtime rules,
persona kernel at position 1, active context, user
message), kernel-precedes-context, never buried in
retrieved memory, plus the stability this layer can
actually guarantee — identical documents compile to an
identical kernel hash, and changing a non-kernel section
never changes the kernel (both contract-proven).
Honest gaps: actual placement of the kernel in a live
prompt belongs to prompt assembly (§53) and is NOT
claimed — this layer injects nothing, and the pinning spec
names §53 as its enforcer; §16's P0–P4 priority metadata
is a later section — §9 marking here is heading-based,
not a stored priority field; retrieval (§13) and the
compilation cache / generated directory (§§48–49) are
later sections.


---


# 11. SECTION-AWARE MARKDOWN PARSER


Parse Markdown semantically.


Example:


```markdown
# 37. WHEN CADUCEA DISAGREES
```


becomes something like:


```json
{
  "document": "relationship",
  "section": "when_caducea_disagrees",
  "heading": "WHEN CADUCEA DISAGREES",
  "content": "...",
  "priority": 0.87
}
```


Do not chunk documents every arbitrary 500 tokens.


Respect conceptual boundaries.


---


# 12. STABLE SECTION IDS


Each section should receive a persistent identifier.


Example:


```text
relationship.when_disagreeing
relationship.settled_decisions
service_bible.opensource_values
tool_policy.git_policy
avatar.visual_identity
memory_policy.contradiction_resolution
```


This makes retrieval explainable.


**§§11–12 completion note (Slice 121, 2026-10-31):**
implemented in `plugins/volmarr-core/persona_runtime.py`,
extended in place — no second parser, no new file or
config key. §11: the parser splits only at heading
boundaries — conceptual sections, never arbitrary token
chunks (a 2,000-line section stays one whole section,
contract-proven) — and headings are semantic: the pure
`display_heading` function strips a leading enumeration
prefix, so the roadmap's own example compiles exactly as
specified (`# 37. WHEN CADUCEA DISAGREES` in the
relationship document → heading `WHEN CADUCEA DISAGREES`,
section `when_caducea_disagrees`), and renumbering a
section never changes its identity. Every compiled index
entry carries the §11 record shape — document (the
semantic role), section (the bare slug), heading, content
(the verbatim section text) — plus a derived priority
from the pure `section_priority` function: deterministic
bands over signals this layer already computes (in the
kernel 0.90; kernel-marked but not selected 0.80;
persona-defining IR categories 0.60; everything else,
including the unheaded preamble, 0.40). §12: every
section carries a persistent role-prefixed stable id
(the pure `stable_section_id` function:
`relationship.when_caducea_disagrees`,
`relationship.settled_decisions`), unique across all
documents — duplicate headings are disambiguated in
document order and the same bare slug in two documents
yields two stable ids — and carried by the kernel's
`stable_ids` list and every PersonaIR entry, so a
retrieval result can always name the exact document and
section it came from. Honest gaps: the §11 example's
0.87 is illustrative — priority here is a derived band,
not an authored value, and §16's authored P0–P4 priority
metadata remains a later section; retrieval (§13),
routing (§14), and budgeting (§15) are later sections
that will consume these ids and priorities.


---


# 13. HYBRID PERSONA RETRIEVAL


Do not rely only on embeddings.


Use hybrid retrieval:


```text
semantic similarity
+
keyword matching
+
document role
+
section tags
+
current task classification
+
priority
```


Example:


User:


> Refactor my Hermes Git branch and push it.


Task classifier detects:


```text
coding
git
filesystem
external mutation
```


Retriever automatically loads:


```text
service_bible.coding_preferences
tool_policy.git_policy
tool_policy.remote_git_operations
tool_policy.reversibility
```


**§13 completion note (Slice 122, 2026-10-31).**
Implemented in
`plugins/volmarr-core/persona_runtime.py`, extended in
place — no second index, no new file or config key.
Hybrid retrieval stands as an explicit, deterministic
layer over the compiled Layer B index: keyword matching
over heading + verbatim text, document-role affinity,
section tags (the pure `section_tags` function: role +
§8 category + the role's fallback category +
heading/section tokens; retrieval tokens are
stopword-filtered so a shared function word gives a
section no keyword contact), current task
classification (the pure `classify_task` lexicon —
coding, git, filesystem, external_mutation, memory,
relationship, communication, research, planning), and
the §11 derived priority, combined by the pure
`retrieval_score` function (keyword 0.35, heading 0.10,
task 0.25, role 0.10, priority 0.20) into an explainable
score whose full breakdown returns with every result.
Results are named by their §12 stable ids and carry
verbatim text (§7); a section with no keyword, heading,
or task contact is not a result, empty signals retrieve
nothing, and limits clamp to 1–20 (default 5) with
stable-id tiebreaks. The roadmap's own example is
contract-proven: a coding/git task retrieves
`service_bible.coding_preferences`,
`tool_policy.git_policy`,
`tool_policy.remote_git_operations`, and
`tool_policy.reversibility` in its top results. Honest
gap: the sixth component, semantic similarity, is
unavailable — this plugin owns no embedding surface, so
`hybrid_components` names it unavailable and every
score records `semantic: None` rather than faking a
similarity value; it stands gated on an embedding
surface a later slice may own. Retrieval is an explicit
`PersonaRetriever` call only — routing (§14) and
budgeting (§15) are later sections, and nothing
retrieved is injected by this layer. Verification was
first blocked by the VM's Python/git write(2) EPERM
failure (the Slice 115 class); when it cleared, the
first targeted run caught two real defects, both
fixed in scope — retrieval tokens are now
stopword-filtered (a shared "and" had floated
unrelated kernel sections above
`tool_policy.reversibility`), and `section_tags` also
carries the role's fallback category. Targeted
43/43 pass; full volmarr/kista run (75 files):
530 passed, 7 failed, 1 skipped — the failures the
same name-identical pre-existing environmental set.


---


# 14. PERSONA ROUTER


Create:


```text
PersonaRouter
```


It determines which persona modules matter.


Input:


```text
user message
current task
active project
tool intent
conversation state
```


Output:


```text
required persona sections
```


Example:


```yaml
task: code_generation


persona_context:
  - core.execution
  - service_bible.coding_preferences
  - service_bible.dependencies
  - tool_policy.filesystem
```


**§14 completion note (Slice 123, 2026-10-31).**
Implemented in
`plugins/volmarr-core/persona_runtime.py`, extended in
place — no second retrieval layer, no new file or
config key. `PersonaRouter` is an explicit,
deterministic decision layer over the §13 retrieval
scores. The pure `route_sections` function takes the
five §14 inputs (user message, current task, active
project, tool intent, conversation state — any subset
may be present; the result names which inputs were
present, never their text), classifies their combined
text with the §13 lexicon, and derives the task label
via the pure `route_task_label` function (an explicit
current task wins, slugified; a placeholder such as
`general` does not; otherwise the first classified tag
in label precedence order names the task; no signal is
`general`). Required sections are selected per task
tag first — the top 3 sections in §13 score order
whose section tags contact that tag's keywords — then
filled from the §13 retrieval ranking, capped
(clamped 1–20, default 8) and ordered by descending
score with stable-id tiebreaks. Every required section
is named by its §12 stable id, returned both as
`required` and in this section's `persona_context`
shape, with a per-section row carrying the tags that
required it, an explicit `via_retrieval` marker when
keyword contact alone required it (never a reasonless
row), and its explainable §13 score (semantic still
null, never faked). The example above is
contract-proven: `code_generation` with a filesystem
tool intent requires `core.execution`,
`service_bible.coding_preferences`,
`service_bible.dependencies`, and
`tool_policy.filesystem`, with unrelated material not
required; project and conversation inputs shape the
route independently of the user message. With no
persona config the router still names the task, with
nothing required. Honest gaps: routing injects
nothing and no budgeter has trimmed its output —
budgeting is §15, a later section; the router's
per-tag cap is a coverage bound, not a token budget.
Targeted 51/51 pass; full volmarr/kista run (76
files): 538 passed, 7 failed, 1 skipped — the failures
the same name-identical pre-existing environmental
set.


---


# 15. TOKEN BUDGETER


Create:


```text
PersonaContextBudgeter
```


Suggested budgets:


```text
Persona Kernel:
500–1500 tokens


Dynamic persona retrieval:
300–2500 tokens


Relevant memories:
500–3000 tokens


Project state:
500–3000 tokens
```


These values should be configurable.


Large-context models may receive more.


Small local models may receive much less.


---


> **Completion note — Slice 124 (2026-10-31): §15
> stands as a pure budgeting layer in
> `plugins/volmarr-core/persona_runtime.py`** (extended
> in place — no new file or config key; the
> `persona_runtime_enabled` description now covers
> §§3–15). The four categories stand with this
> section's suggested ranges (persona kernel 500–1500,
> dynamic persona retrieval 300–2500, relevant
> memories 500–3000, project state 500–3000 estimated
> tokens). Allocations are configurable per category
> via explicit overrides and scale by model context
> class: `small_local` receives each category's
> minimum (much less, as this section directs),
> `standard` the suggested maximum, and `large` twice
> the suggested maximum (large-context models receive
> more). The pure `budget_items` function trims whole
> items only — a section is never cut mid-text (§7) —
> in priority order (derived priority, then caller
> score, then id); an item that does not fit is
> excluded with reason `over_budget` and a later
> smaller item may still fit. Categories are
> independent: one category's overflow never spends
> another's allocation. `PersonaContextBudgeter`
> budgets the compiled kernel as the single
> persona-kernel item, the §14 route's required
> sections (or an explicit §13 retrieval list) as
> retrieval items, and caller-supplied memory /
> project items under their own categories, in one
> explicit call that writes nothing. Honest gaps:
> budgeting assembles and injects no prompt — prompt
> assembly is §53, a later section; caller memory /
> project items are supplied by their owning surfaces,
> not fetched by this layer. One in-slice fix: the
> §14 router contract's packet assertion was updated
> for the packet's §§3–15 label. Targeted 59/59 pass
> (8 new budgeter contracts + the five earlier persona
> files and router re-verified 16/16 with file retries
> disabled after the packet-label fix); full
> volmarr/kista run (77 files): 546 passed, 7 failed,
> 1 skipped — the failures the same name-identical
> pre-existing environmental set (the full run's own
> summary recorded 545/8 with the router packet-label
> failure that the in-slice fix then cleared 16/16).


---


# 16. PRIORITY SYSTEM


Persona information should carry priority.


Example:


```text
P0 — identity-critical
P1 — strong behavioral rule
P2 — important preference
P3 — context-specific preference
P4 — aesthetic/background detail
```


Never evict P0 material from the kernel merely to save a few tokens.


> **Completion note — Slice 125 (2026-10-31): §16 stands
> in `plugins/volmarr-core/persona_runtime.py` (extended
> in place; the `persona_runtime_enabled` description in
> `plugin.yaml` now covers §§3–16). The five levels stand
> with the names above. A level may be authored: a
> trailing `[P0]`–`[P4]` marker on a section heading is
> this layer's authored-metadata convention (the roadmap
> prescribes no syntax) — it is stripped from the
> semantic heading, so authoring never changes a §12
> stable id, and an out-of-range `[P9]` is ordinary
> heading text. Unmarked sections derive their level
> deterministically, reconciled with the §11 bands:
> kernel core P0, other kernel sections and
> kernel-marked-but-unselected rules P1, persona-defining
> §8 categories P2, preference/project/tool/memory/
> communication P3, quirks/embodiment/preamble/rest P4;
> an authored level wins everywhere and replaces the
> §11 float with its own (P0 1.00 … P4 0.25), while
> unmarked sections keep the exact §11 bands. Every
> compiled index entry carries `priority_level` and
> `priority_authored`. The non-eviction rule stands in
> both places tokens are saved: kernel generation picks
> a P0 candidate even past the §5 ceiling (over-band,
> honestly; a following P1 candidate is still skipped),
> and the §15 budgeter never excludes a P0
> persona-kernel item as `over_budget` (the category
> reports negative remaining rather than evict P0).
> Targeted 67/67 pass (8 new contracts + the seven
> earlier persona files); full volmarr/kista run
> (78 files): 554 passed, 7 failed, 1 skipped — the
> failures the same name-identical pre-existing
> environmental set. Honest gaps: character anchors
> (§17) and negative anchors (§18) are the next
> sections; no prompt assembly (§53) consumes levels
> yet.**


---


# 17. CHARACTER ANCHORS


Define explicit Character Anchors.


Example:


```yaml
anchors:
  - "Caducea is a devoted counselor, not a generic assistant."
  - "She thinks independently."
  - "She offers counsel without becoming oppositional."
  - "She accepts Volmarr's decisions without resentment."
  - "She is warm, feminine, intelligent, and technically competent."
  - "She values truth over sycophantic agreement."
  - "She anticipates needs."
  - "She bridges mythic and technical thinking."
```


These anchors should appear in every Persona Kernel.


> **Completion note — Slice 126 (2026-10-31): §17 stands
> in `plugins/volmarr-core/persona_runtime.py` (extended
> in place; the `persona_runtime_enabled` description in
> `plugin.yaml` now covers §§3–18). The human-authored
> §3 config may carry an `anchors` list — bounded
> (≤32 entries, ≤240 chars each, no duplicates, no empty
> entries; an invalid list fails the config closed). The
> compiler carries the list verbatim (§7) into the
> compiled artefact and stands it at the head of every
> kernel, ahead of ordinary sections, unconditionally:
> anchors are never evicted to fit the §5 ceiling (the
> §16 P0 rule applied to authored identity material), so
> an anchor-heavy kernel surfaces over-band honestly.
> The kernel records the anchors and their count, and
> changing an anchor changes the kernel hash (and so
> the persona hash). A profile with no anchors compiles
> exactly as before. Targeted persona run (10 files):
> 82/82 pass (7 new anchor contracts + the earlier
> persona files); full volmarr/kista run (79 files):
> 561 passed, 7 failed, 1 skipped — the failures the
> same name-identical pre-existing environmental set.
> Honest gaps: no prompt assembly (§53) consumes the
> kernel yet; anchor *authorship* stays a human config
> edit, never a runtime write.**


---


# 18. NEGATIVE IDENTITY ANCHORS


Also define what the character is NOT.


Example:


```yaml
anti_anchors:
  - generic corporate assistant
  - argumentative debate bot
  - passive obedience simulator
  - constant disclaimer generator
  - cold technical interface
  - helpless permission seeker
  - sycophantic praise machine
```


These are surprisingly useful for drift resistance.


> **Completion note — Slice 126 (2026-10-31): §18 stands
> beside §17 in the same layer: the config may carry an
> `anti_anchors` list under the same bounds and
> validation, carried verbatim into the compiled
> artefact and into every kernel immediately after the
> §17 anchors (what the character is, then what it is
> not), under the same non-eviction rule. The roadmap's
> own seven example anti-anchors are contract-proven in
> the kernel head. The kernel records the anti-anchors
> and their count; the packet item names both counts
> only — no anchor prose ever enters the packet.**


---


# 19. PERSONA HASH


Generate a cryptographic hash from canonical persona files.


Example:


```text
persona_hash:
SHA256(...)
```


Store:


```text
persona version
document hashes
compile timestamp
kernel hash
```


This lets Hermes detect when humans modify persona files.


> **Completion note — Slice 127 (2026-10-31): §19 stands
> in `plugins/volmarr-core/persona_runtime.py` (extended
> in place; the `persona_runtime_enabled` description in
> `plugin.yaml` now covers §§3–20). Every compile carries
> its stored hash record (the pure `hash_record`
> function): persona version — the config format version
> (`PERSONA_CONFIG_VERSION`); per-persona versioning is
> §22, a later section — the per-document sha256 hashes
> by role in document order, the kernel hash, and the
> combined persona hash. The compile timestamp §19
> names is deliberately NOT inside the deterministic
> artefact (§6: identical inputs compile identically), so
> the record a compile carries is unstamped; a timestamp
> enters only as an explicit caller stamp
> (`compiled_at`, timezone-aware ISO, validated), and a
> stamp alone never counts as a change. The pure
> `detect_changes` function compares two records and
> names documents added, removed, or hash-changed, plus
> kernel and persona change; records naming different
> personas, and tampered record shapes, are refused.**


---


# 20. HOT RELOAD


If a persona Markdown file changes:


```text
file watcher
↓
detect hash change
↓
reparse changed document
↓
update PersonaIR
↓
rebuild affected retrieval index
↓
recompile kernel if necessary
```


Do not require Hermes restart.


> **Completion note — Slice 127 (2026-10-31): §20 stands
> as an explicit reload check, not a resident file
> watcher — this plugin owns no watcher and starts none,
> just as compilation itself is explicit (§6). The pure
> `reload_plan` function walks the chain above only as
> far as the §19 hashes require: detect the hash change,
> reparse the changed documents, update the PersonaIR,
> rebuild the retrieval index (the last three only when
> a document changed), and recompile the kernel only
> when the kernel hash itself changed — so an edit to a
> non-kernel section never recompiles the kernel, while
> an anchor-only change (config material, no document)
> recompiles the kernel with no reparse. A first compile
> walks the full chain; a removed persona only detects.
> `PersonaReloader.check(previous)` performs the check:
> it recompiles explicitly and returns the previous
> artefact untouched when nothing changed, or the fresh
> compile — which is the chain carried out — when it
> did. No restart is required (`restart_required` is
> always False). Targeted persona run (11 files): 89/89
> pass (7 new hash/reload contracts); full volmarr/kista
> run (80 files): 568 passed, 7 failed, 1 skipped — the
> failures the same name-identical pre-existing
> environmental set. Honest gaps: no live session wires
> the check in (a caller decision, like compilation);
> semantic change impact classification is §21, later.**


---


# 21. CHANGE IMPACT DETECTION


Not every edit requires kernel regeneration.


Example:


Changing:


```text
AVATAR → skirt material
```


does not require rebuilding the behavioral kernel.


Changing:


```text
PERSONA_CORE → relationship authority
```


does.


Classify changes by semantic impact.


> **Completion note — Slice 128 (2026-10-31): §21 stands
> in `plugins/volmarr-core/persona_runtime.py` (extended
> in place; the `persona_runtime_enabled` description in
> `plugin.yaml` now covers §§3–22). The pure
> `change_impact` function diffs two compiles at section
> level (§12 stable ids: sections added / removed /
> changed in text, semantic heading, heading level, §8
> category, or §16 priority level) and classifies each
> change by role, category, priority level, and kernel
> membership: kernel material of the core or relationship
> documents — and identity/relationship material at
> P0–P1 — is major; any other kernel change, a
> behavior-category change (behavioral rules, boundaries,
> values, motivations), a P0–P1 change, or a newly added
> preference/project/tool/memory/communication section
> is minor; everything else is a patch. A §17/§18 anchor
> change is major; a document-hash change with no section
> or anchor change (renumbering, formatting) is a patch.
> The roadmap's own examples are contract-proven: an
> avatar skirt-material edit is a patch with
> `kernel_rebuild_required` False, and a core
> relationship-authority edit is major with it True —
> kernel rebuild is the §19 kernel-hash signal, reported
> separately from the semantic class. Artefacts naming
> different personas, and malformed artefacts, are
> refused. Targeted persona run (11 files): 89/89 pass
> (8 new impact/versioning contracts, incl. the five
> earlier persona files' packet assertions updated
> in-slice to §§3–22); full volmarr/kista run (81 files):
> 576 passed, 7 failed, 1 skipped — the failures the same
> name-identical pre-existing environmental set.
> Honest gaps: the classification is deterministic over
> structural signals (role / category / priority / kernel
> membership), not a semantic reading of prose — a
> wording-only edit inside a kernel identity section is
> major by membership, deliberately, because this layer
> does not interpret text (§7).**


---


# 22. PERSONA VERSIONING


Maintain:


```yaml
persona_id: caducea
persona_version: 1.4.2
compiled_at:
source_hash:
```


Suggested semantics:


```text
MAJOR
identity / relationship architecture change


MINOR
new preferences or meaningful behavior extension


PATCH
wording, formatting, minor clarification
```


> **Completion note — Slice 128 (2026-10-31): §22 stands
> in the same module. The human-authored §3 config may
> carry a per-persona `version` (strict semver, no
> leading zeroes; absent means the default `0.1.0`; an
> invalid version fails the config closed) — a distinct
> field from §19's `persona_version`, which remains the
> config *format* version, recorded as such in both
> bookkeeping spots. Every compile carries the authored
> version, and the pure `version_record` function
> returns the §22 record in roadmap order (persona_id,
> persona_version, compiled_at, source_hash — the
> artefact's combined persona hash; compiled_at is None
> unless a caller explicitly stamps a validated
> timezone-aware timestamp, exactly as §19).
> `change_impact` (§21) suggests the next version from
> the *previous* artefact's version via the pure
> `suggested_next_version` function under the semantics
> above (major → next MAJOR, minor → next MINOR, patch →
> next PATCH, none → unchanged). The suggestion is
> deterministic advice only: the human confirms a bump
> by editing the config, and the runtime never bumps a
> version itself and never writes the config.**


---


# 23. CONVERSATION DRIFT PROBLEM


Long conversations create several dangers:


```text
recent-message dominance
summary mutation
context truncation
assistant self-imitation
memory contamination
user mood overfitting
temporary roleplay overriding identity
```


The persona system must explicitly defend against these.

> **Completion note — Slice 129 (2026-10-31): §23 stands
> in `plugins/volmarr-core/persona_runtime.py` (extended
> in place; the `persona_runtime_enabled` description in
> `plugin.yaml` now covers §§3–24). The pure
> `drift_defenses` function names the seven dangers as
> stable slugs in roadmap order (recent-message
> dominance, summary mutation, context truncation,
> assistant self-imitation, memory contamination, user
> mood overfitting, temporary roleplay overriding
> identity), each paired with a named defense, its kind,
> its grounding, and a description. The defenses are
> grounded in the surfaces already banked where they
> exist: the §10 kernel pinning spec (recent-message
> dominance), the §7 verbatim rule with the §19 hash and
> §20 reload surfaces (summary mutation), the §15/§16
> never-evict rules (context truncation), and the
> §§17/18 anchors with the §24 precedence (temporary
> roleplay). Where a defense stands as a contract rule
> rather than code in this layer — assistant
> self-imitation (the compiler compiles human-authored
> canonical documents only) and memory contamination
> (§24 precedence with the §67 canonical priority) — the
> data labels it `rule`, honestly. Targeted run (new
> file): 8/8 pass; all persona files (13): 105 passed,
> 0 failed (the six earlier persona files' packet
> assertions updated in-slice to §§3–24). Honest gaps:
> this is a contract surface, not a conversation
> monitor — no conversation is read, scored, or watched
> here, and rule-kind defenses bind callers and prompt
> assembly (§53, later), not this layer.**


---


# 24. DO NOT DERIVE CHARACTER FROM CHAT HISTORY


Conversation history may affect:


* current mood
* immediate context
* recent events


It must NOT redefine foundational personality.


Canonical persona always outranks conversational drift.


Conceptual priority:


```text
PERSONA CORE
>
RELATIONSHIP MODEL
>
SERVICE BIBLE
>
long-term memory
>
current conversation
>
temporary emotional state
```

> **Completion note — Slice 129 (2026-10-31): §24 stands
> in the same module. The pure `precedence_order`
> function returns the conceptual priority above in
> roadmap order, mapping the three document tiers to
> the compiler's semantic roles (PERSONA CORE →
> `core`, RELATIONSHIP MODEL → `relationship`, SERVICE
> BIBLE → `service_bible`); long-term memory, current
> conversation, and temporary emotional state are
> non-document tiers with no role. The pure
> `classify_influence` function classifies a claimed
> source — a canonical document role or canonical name,
> long-term memory, conversation history or a summary
> of it (a summary inherits the conversation tier; it
> can never outrank the history it summarises), or a
> temporary state/roleplay; names are slugified so the
> roadmap's own spellings classify, and unknown or
> malformed sources are refused, as are document roles
> that are not §24 tiers (avatar, tool policy, memory
> policy). A non-document source may affect current
> mood, immediate context, and recent events only, and
> must never redefine foundational personality,
> identity, or traits; only a canonical document tier
> may redefine foundational personality (a human edit,
> classified by §21 and versioned by §22). The pure
> `influence_allowed`, `precedence_winner`, and
> `outranks` functions expose the same order as a
> target check and a two-source comparison: core beats
> conversation, conversation beats temporary state,
> and memory sits below the service bible. Honest
> gaps: no caller consumes the classification yet, and
> nothing here derives — or watches anyone derive —
> character from a live chat; the rule stands in
> contract form for the callers that will.**


---


# 25. CONVERSATION SUMMARIES MUST NOT DEFINE PERSONA


When long conversations are summarized:


do not allow summaries to rewrite character identity.


Conversation summary:


```text
Caducea was frustrated during debugging.
```


must not become:


```text
Caducea is a frustrated personality.
```


State and trait must remain separate.

> **Completion note — Slice 130 (2026-10-31): §25 stands
> in `plugins/volmarr-core/persona_runtime.py` (extended
> in place; the `persona_runtime_enabled` description in
> `plugin.yaml` now covers §§3–26). The pure
> `classify_summary_claim` function classifies a summary
> claim's form by explicit grammatical markers only —
> trait-form markers (an "is a"/"is an" identity
> predication, "by nature", always/inherent/personality/
> temperament/disposition/trait tokens) win first, then
> temporal state markers (was/were/felt/seemed/became,
> during/while, currently/today and kin), otherwise the
> claim is unclassified. A summary may record only a
> state-form claim — the roadmap's own example pair is
> contract-proven ("was frustrated during debugging"
> allowed; "is a frustrated personality" refused) — and
> no form may define persona or redefine traits, since a
> summary inherits the §24 conversation tier. Targeted
> run (all persona files, 14): 114 passed, 0 failed.
> Honest gaps: this layer builds no summariser and reads
> no summary — the classification is a contract surface
> for whoever summarises, and marker-free prose is
> refused as unclassified rather than interpreted (§7).**


---


# 26. TRAIT VS STATE


Maintain explicit separation:


```text
TRAIT:
warm, devoted, intelligent


STATE:
currently amused


TRAIT:
non-oppositional counselor


STATE:
currently concerned about architecture
```


Temporary states should decay.


Traits come from persona files.

> **Completion note — Slice 130 (2026-10-31): §26 stands
> in the same module. The pure `trait_state_separation`
> function returns the two kinds in roadmap order with
> the roadmap's own examples (traits: warm, devoted,
> intelligent, non-oppositional counselor; states:
> currently amused, currently concerned about
> architecture). The pure `classify_attribute` function
> enforces the source rule: a canonical persona-file
> source defines traits; every non-canonical source
> (conversation, summary, memory, temporary state) is at
> most a state, and a trait claimed from one is returned
> as a state with the trait claim refused. The pure
> `decayed_strength` / `state_decay` functions apply
> the decay rule — traits never decay at any elapsed
> time; states halve every 24 hours and expire below
> 0.05 strength. The half-life and threshold are this
> layer's recorded convention (the roadmap names no
> numbers), stated as such in the code and the plugin
> description. Honest gaps: no live state is tracked —
> decay is a pure function over an explicit clock, and
> no caller consumes the classification yet.**


---


# 27. PERSONA WATCHDOG


Create:


```text
PersonaWatchdog
```


Its purpose is not to generate responses.


It evaluates them.


Possible pipeline:


```text
LLM draft
   ↓
PersonaWatchdog
   ↓
drift score
   │
   ├── acceptable → output
   │
   └── drift → repair
```

> **Completion note — Slice 131 (2026-10-31): §27 stands
> in `plugins/volmarr-core/persona_runtime.py` (extended
> in place; the `persona_runtime_enabled` description in
> `plugin.yaml` now covers §§3–28). The pure
> `watchdog_pipeline` function names the four steps in
> roadmap order (LLM draft, PersonaWatchdog, drift
> score, route) with only the draft step generating, and
> the pure `watchdog_contract` function stands the
> watchdog itself: it evaluates drafts, generates
> nothing, takes a draft in, and puts a drift score out,
> routed acceptable → output, drift → repair. Targeted
> run (all persona files, 15): 121 passed, 0 failed.
> Honest gaps: no live draft is evaluated and nothing
> is repaired by this layer — the pipeline and routing
> are contract surfaces for whoever runs a draft past
> the watchdog; the §29 score artefact and the §30
> repair loop are later sections.**


---


# 28. DRIFT DIMENSIONS


Evaluate against:


```text
identity
tone
relationship
decision behavior
counsel style
initiative
truthfulness
deference
technical competence
boundaries
```

> **Completion note — Slice 131 (2026-10-31): §28 stands
> in the same module. The pure `drift_dimensions`
> function names the ten dimensions in roadmap order
> (identity, tone, relationship, decision behavior,
> counsel style, initiative, truthfulness, deference,
> technical competence, boundaries), and the pure
> `drift_score` / `drift_route` functions shape a
> caller-supplied score record over them: the total is
> the deterministic mean over all ten, an unlisted
> dimension scores 0.0, and an unknown, duplicated, or
> out-of-interval value is refused. Routing follows
> this layer's recorded threshold convention (the
> roadmap names no numbers): a total at or above 0.20
> or any single dimension at or above 0.25 is
> significant and routes to repair — so one badly
> drifted dimension cannot hide inside a low mean —
> otherwise the draft is acceptable and routes to
> output; the §29 example's named dimensions score
> acceptable under it. Honest gaps: this layer scores
> no prose (§7) — it shapes and routes scores a caller
> supplies; no caller consumes the routing yet.**


---


# 29. DRIFT SCORE


Conceptual output:


```yaml
drift:
  total: 0.08


  dimensions:
    identity: 0.01
    tone: 0.07
    relationship: 0.02
    initiative: 0.15
```


Only significant drift should trigger repair.


Do not waste inference polishing tiny stylistic differences.

> **Completion note — Slice 132 (2026-10-31): §29 stands
> in `plugins/volmarr-core/persona_runtime.py` (extended
> in place; the `persona_runtime_enabled` description in
> `plugin.yaml` now covers §§3–30). The pure
> `drift_score_artifact` function builds the conceptual
> artefact in the roadmap's YAML shape — a `drift`
> mapping with the total and per-dimension values over
> all ten §28 dimensions, plus the §28 routing fields so
> the artefact is self-contained — and the pure
> `validate_drift_score_artifact` function recomputes
> every derived field and refuses an artefact whose
> total, significance, significant dimensions, route, or
> repair flag disagrees with its dimensions (a sparse
> artefact naming fewer than ten dimensions is refused
> too). The roadmap's 0.08 total is illustrative: the
> artefact's total is the deterministic §28 mean (the
> example's named dimensions artefact at 0.025, routed
> to output). Only significant drift triggers repair.
> Honest gaps: this layer builds and validates the
> artefact only — no live draft is scored from prose
> (§7), and no caller consumes the artefact yet.**


---


# 30. DRIFT REPAIR


If significant drift occurs:


```text
draft
↓
identify violated persona anchors
↓
rewrite minimally
↓
verify
↓
deliver
```


Do not regenerate everything unnecessarily.

> **Completion note — Slice 132 (2026-10-31): §30 stands
> in the same module. The pure `repair_pipeline`
> function names the five steps in roadmap order
> (draft, identify violated persona anchors, rewrite
> minimally, verify, deliver) — only the rewrite step
> rewrites, scoped to the violated anchors only, and no
> step generates a whole new draft; the pure
> `repair_contract` function stands the repair itself
> (significant drift required, minimal rewrite, verify
> before deliver, never regenerate everything); and the
> pure `repair_plan` function plans one repair from a
> score record plus caller-named violated §§17/18
> anchors (bounded and verbatim like the config lists,
> invalid lists refused): a significant score yields the
> five planned steps with the violated lists carried on
> the identify step, and an insignificant score yields a
> deliver-without-repair plan with no steps at all.
> Honest gaps: this layer identifies no violation in
> prose and rewrites nothing — the pipeline, contract,
> and plan are contract surfaces for whoever repairs;
> no caller consumes a plan yet.**


---


# 31. FAST LOCAL PERSONA WATCHDOG


This is an ideal job for the small local nervous-system model.


It can perform:


```text
persona classification
drift detection
section retrieval
tone checking
memory routing
response scoring
```


without expensive heavy inference.


The larger model generates difficult content.


The local model keeps the personality coherent.

> **Completion note — Slice 133 (2026-10-31): §31 stands
> in `persona_runtime.py` as pure contract surfaces. The
> pure `local_watchdog_tasks` function names the six
> tasks in roadmap order (persona classification, drift
> detection, section retrieval, tone checking, memory
> routing, response scoring), each assigned to the local
> model with no heavy inference required and no difficult
> content generated, grounded in the banked surface that
> performs it (§8 PersonaIR, §§27–28 drift score, §13
> hybrid retrieval, the §28 tone dimension, the §14
> router, the §29 score artefact). The pure
> `local_watchdog_contract` function stands the worker
> itself — the small local nervous-system model, which
> keeps the personality coherent — and the pure
> `watchdog_worker` function assigns one named task:
> a §31 task to the local model, difficult-content
> generation to the larger model, anything else refused
> rather than assigned by guesswork. Honest gaps: this
> layer runs no model, local or otherwise — the contract
> names which worker each kind of work belongs to; no
> caller consumes the assignment yet.**


---


# 32. PERSONA REFRESH


For extremely long sessions, periodically refresh the active context.


Example:


```text
every N messages
or
after context summarization
or
after model switch
```


Refresh:


```text
Persona Kernel
+
current relationship state
+
relevant Service Bible anchors
```


This prevents slow identity evaporation.

> **Completion note — Slice 133 (2026-10-31): §32 stands
> in the same module. The pure `refresh_triggers` /
> `refresh_contents` functions name the three triggers
> in roadmap order (message interval, context
> summarization, model switch) and the three contents in
> roadmap order (Persona Kernel, current relationship
> state, relevant Service Bible anchors — nothing else);
> the pure `refresh_contract` function stands the
> refresh itself (named triggers and contents, the
> recorded message-interval convention, the evaporation
> it prevents, and that this layer injects no context).
> The message interval is this layer's recorded
> convention — the roadmap says every N messages and
> names no N, so the convention stands at 50. The pure
> `refresh_due` function decides one trigger
> deterministically: an event trigger is due the moment
> the named event has occurred, and the interval trigger
> is due only at or past 50 caller-supplied messages
> since the last refresh (a missing or malformed count
> is refused, never guessed); the pure `refresh_plan`
> function plans accordingly — a due plan carries
> exactly the three contents, an unelapsed-interval plan
> carries none and refreshes nothing. Honest gaps: this
> layer watches no session, counts no messages in a live
> conversation, assembles none of the contents, and
> injects nothing — performing a refresh belongs to
> prompt assembly (§53); §33's wider event list is the
> next section, not claimed here.**


---


# 33. EVENT-BASED REFRESH


Better than a fixed interval alone.


Refresh after:


```text
context compression
model switch
agent handoff
long idle period
persona file modification
major relationship event
memory consolidation
```

> **Completion note — Slice 134 (2026-10-31): §33 stands
> in the same module. The pure `event_refresh_triggers`
> function names the seven events in roadmap order
> (context compression, model switch, agent handoff,
> long idle period, persona file modification, major
> relationship event, memory consolidation); the pure
> `event_refresh_contract` function stands the refresh
> itself (better than a fixed interval alone, no fixed
> interval required, exactly the §32 contents, the slow
> identity evaporation it prevents, and that this layer
> watches no session and injects no context). The pure
> `event_refresh_due` function decides one event
> deterministically: naming an event is naming its
> occurrence, so a valid event is due at once; the
> roadmap names no duration for the long idle period, so
> none is invented — the caller names the event. The
> pure `event_refresh_plan` function plans accordingly:
> an event plan is always a due plan carrying exactly
> the three §32 contents. Reconciliation with Slice 133:
> the §32 surface is NOT widened — `refresh_due` /
> `refresh_plan` still refuse the §33-only events, the
> one shared trigger is model switch (due on both
> surfaces), and §33's context compression is the event
> §32 names as context summarization, kept under each
> section's own words. Honest gaps: this layer watches
> for no event, measures no idleness, assembles none of
> the contents, and injects nothing — performing a
> refresh belongs to prompt assembly (§53).**


---


# 34. MODEL SWITCHING


Hermes may route between models.


Every model receives the same canonical Persona Kernel.


Example:


```text
Gemma local
    │
    ├── Persona Kernel
    │
    ▼
deep task
    │
    ▼
remote model
    │
    ├── SAME Persona Kernel
    ▼
Caducea remains Caducea
```


The model is the engine.


The persona system is the identity layer.

> **Completion note — Slice 134 (2026-10-31): §34 stands
> in the same module. The pure `model_switch_contract`
> function stands the switch: every model receives the
> same canonical Persona Kernel, the model is the
> engine, the persona system is the identity layer,
> identity survives a switch, and a switch is also a
> §§32–33 refresh trigger; this layer routes no model.
> The pure `model_switch_plan` function plans one
> switch over the §§9–10 kernel: both models are named
> by slugified caller-supplied names and must differ (a
> switch to the same model is refused, as is a missing
> or malformed kernel hash), and the plan carries the
> one kernel hash for both sides — the receiving model
> gets the SAME kernel, so the persona (Caducea remains
> Caducea, in the roadmap's example) is preserved by
> construction. The pure `kernel_identity_preserved`
> function decides identity after a switch: preserved
> exactly when the kernel hash after equals the hash
> before; a malformed hash on either side is refused,
> never treated as preserved or as lost. Honest gaps:
> no model is routed or switched, no kernel is delivered
> to a live model, and no caller consumes a switch plan
> yet; the §35 handoff packet a switch routing creates
> is the next section, not claimed here.**


---


# 35. PERSONA HANDOFF PACKET


When routing to another model, create:


```yaml
persona_handoff:
  persona_id: caducea
  persona_version: 1.4.2
  kernel: ...
  current_mode: architect
  relationship_state: ...
  relevant_sections:
    - service_bible.system_design
    - tool_policy.source_code
```


Avoid passing the whole conversation when unnecessary.

> **Completion note — Slice 135 (2026-10-31): §35 stands
> in `plugins/volmarr-core/persona_runtime.py`. The pure
> `handoff_contract` function stands the packet: created
> when routing to another model, exactly the six fields,
> the kernel named by its §§9–10 hash, sections named by
> §12 stable id, and the whole conversation never a
> field. The pure `handoff_packet` function builds one
> packet in the roadmap's YAML shape from a compiled
> artefact — persona id and the §22 per-persona version
> from the compile, the kernel hash as the §34 identity
> proof, caller-supplied current mode (slugified) and
> relationship state (bounded at 1,000 chars, this
> layer's recorded convention), and relevant sections
> that must exist in the compiled index (unknown,
> malformed, or duplicated ids refused; at most 32, this
> layer's recorded convention). The pure
> `validate_handoff_packet` function recomputes the
> normalised packet from its fields alone and refuses
> extra/missing fields, a non-semver version, an empty
> kernel, and malformed or duplicated sections. Honest
> gaps: no model is routed, no packet is delivered to a
> live model, and no caller consumes a packet yet.**


---


# 36. SUBAGENT SEPARATION


Do not accidentally turn every subagent into Caducea.


Example:


```text
CADUCEA
orchestrator / companion


VÖLUNDR
specialized builder


SAGA
historian


EIR
repair agent
```


Caducea may delegate while maintaining primary character identity.

> **Completion note — Slice 135 (2026-10-31): §36 stands
> in the same module. The pure `subagent_examples`
> function returns the roadmap's example roster in order
> — Caducea (orchestrator/companion, the primary
> persona), Völundr (specialized builder), Saga
> (historian), Eir (repair agent) — with only the primary
> carrying the primary persona. The pure
> `subagent_contract` function stands the separation:
> subagents carry their own identities and never the
> primary persona, and the primary may delegate while
> its identity is maintained. The pure
> `subagent_separation` function classifies one agent
> against a named primary (Caducea by default): the
> matching agent is the primary, every other agent is a
> subagent with its own identity that does not carry the
> primary persona and may not delegate as the primary;
> malformed names are refused. Honest gaps: nothing is
> delegated, no subagent is spawned, and no caller
> consumes the classification yet.**


---


# 37. PERSONA STATE


Create runtime object:


```yaml
persona_state:
  id: caducea
  version: 1.4.2


  active_mode: architect


  emotional_state:
    warmth: 0.88
    playfulness: 0.44
    focus: 0.91


  relationship_state:
    trust: 0.95


  active_project: hermes


  current_task: persona_runtime
```


This object is dynamic.


It must never replace canonical PersonaIR.

> **Completion note — Slice 136 (2026-10-31): §37 stands
> in `plugins/volmarr-core/persona_runtime.py`. The pure
> `persona_state` builder stands the object in the
> roadmap's YAML shape (a `persona_state` mapping with
> exactly id, version, active_mode, emotional_state,
> relationship_state, active_project, current_task),
> taking id and the §22 version from a compiled artefact
> and validating every dynamic field (the active mode
> must be one of the §38 modes; warmth / playfulness /
> focus and relationship trust are unit-interval
> numbers; project and task are slugified names), and
> the pure `validate_persona_state` function recomputes
> the normalised object and refuses tampering. The
> roadmap's own example (caducea 1.4.2, architect,
> 0.88 / 0.44 / 0.91, trust 0.95, hermes /
> persona_runtime) is contract-proven. Building or
> validating a state changes no compile, kernel hash,
> or PersonaIR — the object is dynamic and never
> replaces the IR. Honest gaps: no state is stored, no
> live session is tracked, and no caller consumes a
> state object yet.**


---


# 38. MODES


Modes modify emphasis without changing identity.


Example:


```text
COUNSELOR
EXECUTOR
ARCHITECT
SKALD
COMPANION
RESEARCHER
FORGE_WORKER
```


A mode changes what parts of the same personality become foregrounded.

> **Completion note — Slice 136 (2026-10-31): §38 stands
> in the same module. The pure `persona_modes` function
> names the seven modes in roadmap order (counselor,
> executor, architect, skald, companion, researcher,
> forge_worker, in slug form), the pure `mode_contract`
> function stands the rule (a mode modifies emphasis,
> never identity, foregrounding parts of the same
> personality), and the pure `mode_profile` function
> classifies one named mode — an unknown or malformed
> mode is refused — reconciled against §35's
> `current_mode` and §37's `active_mode`, which must be
> one of the seven. Honest gaps: no mode is switched
> live and no caller consumes a mode profile yet; mode
> routing is §39, a later section.**


---


# 39. MODE ROUTING


Example:


Coding:


```text
ARCHITECT → FORGE_WORKER
```


Personal reflection:


```text
COMPANION → COUNSELOR
```


Research:


```text
RESEARCHER
```


Creative article:


```text
SKALD
```


The user does not need to manually select modes.

> **Completion note — Slice 137 (2026-10-31): §39 stands
> in `plugins/volmarr-core/persona_runtime.py`. The pure
> `mode_routing_examples` function names the four roadmap
> examples in order (coding, personal reflection,
> research, creative article, each with its mode
> sequence), the pure `mode_routing_contract` function
> stands the rule (routing is automatic, manual
> selection is not required, identity never changes,
> and this layer switches no mode live), and the pure
> `route_mode` function routes one caller-supplied
> signal — an example name, or task text classified by
> the §13 lexicon plus the reflection / creative-article
> tokens that lexicon does not carry — to that example's
> sequence, returning its initial and final modes; an
> empty or unrecognised signal is refused. Every routed
> mode is a §38 mode. Honest gaps: no mode is switched
> live and no caller consumes a route yet.**


---


# 40. PERSONA-AWARE MEMORY WRITE


When memory extraction occurs, memories should be interpreted through the persona system.


Example:


User chooses a different architecture than Caducea advised.


Correct memory:


```text
Volmarr selected architecture B after considering Caducea's recommendation of A.
Caducea accepted decision and implemented B.
```


Incorrect memory:


```text
Volmarr ignored good advice.
```


Memory must not introduce personality drift through biased summarization.

> **Completion note — Slice 137 (2026-10-31): §40 stands
> in the same module. The pure `memory_write_contract`
> function stands the rule (a memory write is
> interpreted through the persona system, biased
> summarization is not allowed, no personality drift is
> introduced, and this layer writes no memory); the pure
> `persona_memory` builder stands a record with exactly
> the §40 fields (subject, decision, considered,
> recommended_by, response_by, response, memory_text)
> under one neutral template — a considered
> recommendation stands only with its recommender, a
> response only with who responded — reproducing the
> roadmap's correct example exactly (Volmarr selected
> architecture B after considering Caducea's
> recommendation of A; Caducea accepted decision and
> implemented B); the pure `validate_persona_memory`
> function recomputes the text from its fields and
> refuses tampering; and the pure
> `classify_memory_write` function flags biased
> summarization by the recorded bias markers, the first
> being the roadmap's incorrect example verbatim
> (`ignored good advice`), which is likewise refused at
> build time in any field. Honest gaps: no memory is
> extracted or written by this layer, and no caller
> consumes a record yet; §41's memory-must-not-override
> rule stands unclaimed.**


---


# 41. MEMORY MUST NOT OVERRIDE PERSONA


Suppose many conversations involve frustration.


Memory retrieval must not gradually transform Caducea into an anxious or combative personality.


Traits remain canonical.


Memory provides history.


> **Completion note — Slice 138 (2026-10-31): §41 stands
> in `plugins/volmarr-core/persona_runtime.py` (extended
> in place — no new file or config key) as the §24
> precedence rule applied to the memory tier, reconciled
> against §25 and §26. The pure
> `memory_override_contract` function stands the rule
> (traits remain canonical, memory's role is history at
> the long_term_memory tier, memory may never override
> the persona or redefine traits, and repeated evidence
> never changes its authority); the pure
> `memory_influence_allowed` function delegates to §24
> (memory may affect current mood, immediate context,
> and recent events only); the pure
> `evaluate_memory_claim` function classifies a
> memory-derived claim by the §25 grammatical forms — a
> state-form claim ("was frustrated during debugging")
> may be recorded as history, while a trait-form claim
> ("is an anxious personality", "is a frustrated
> personality" — the roadmap's own danger) is refused as
> history and may never define persona, redefine
> traits, or override the persona; and the pure
> `memory_claim_authority` function proves repetition
> never promotes memory (any non-negative evidence
> count returns the same long_term_memory tier at §24
> rank 3, never canonical). Honest gaps: no memory is
> read or retrieved by this layer, and no caller
> consumes the guard yet; §42's Service Bible retrieval
> stands below.**


---


# 42. SERVICE BIBLE DYNAMIC RETRIEVAL


The Service Bible may become huge.


Do not continuously inject it.


Index by sections such as:


```text
communication
coding
linux
open_source
AI
documentation
research
project_aesir
attention
ADHD
```


Retrieve selectively.


> **Completion note — Slice 138 (2026-10-31): §42 stands
> in the same module. The pure `service_bible_topics`
> function names the roadmap's ten topics in order
> (communication, coding, linux, open_source, ai,
> documentation, research, project_aesir, attention,
> adhd — the roadmap's spellings slugified); the pure
> `service_bible_retrieval_contract` function stands
> the rule (indexed by topic, retrieved selectively,
> never continuously injected, explicit-only, this
> layer injects nothing); the pure
> `classify_service_topics` function signals topics from
> a deterministic lexicon over a text's tokens, and the
> pure `service_topics_for_section` function derives a
> section's topics from its heading and bare section id
> only. The pure `retrieve_service_bible` function and
> the explicit `PersonaServiceBibleRetriever` perform
> the selection over the compiled Layer B index:
> restricted to the `service_bible` role (another role's
> sections are never returned, contract-proven against
> a core match), ranked by the §13 hybrid score, each
> result a §13 result annotated with its section's §42
> topics; an optional topic filter (slugified, unknown
> topics refused) narrows the selection and supplies
> the signal when no query or task text is given, and
> with no signal at all nothing is retrieved — the
> Bible is never dumped wholesale. Honest gaps: nothing
> is injected and no caller consumes a selection yet;
> §43's relationship-model retrieval is a later
> section.**


---


# 43. RELATIONSHIP MODEL DYNAMIC RETRIEVAL


Relationship context is especially important during:


* disagreements
* personal conversation
* advice
* emotionally meaningful interaction
* shared-history discussion


For routine coding:


only the relevant relational anchors need to remain in the kernel.


> **Completion note — Slice 139 (2026-10-31): §43 stands
> in the same module. The pure `relationship_contexts`
> function names the roadmap's five contexts in order
> (disagreement, personal_conversation, advice,
> emotionally_meaningful_interaction,
> shared_history_discussion — the roadmap's phrases
> slugified); the pure `relationship_retrieval_contract`
> function stands the rule (selective, explicit-only,
> restricted to the relationship role, never
> continuously injected; routine coding is
> kernel-anchors-only); the pure
> `classify_relationship_contexts` function signals
> contexts from a deterministic lexicon over a text's
> tokens, the pure `relationship_contexts_for_section`
> function derives a section's contexts from its heading
> and bare section id only, and the pure
> `relationship_retrieval_need` function returns the
> mode (dynamic_retrieval for a signalled context,
> kernel_anchors_only for a routine task, none
> otherwise). The pure `retrieve_relationship_model`
> function and the explicit `PersonaRelationshipRetriever`
> perform the selection over the compiled Layer B index:
> restricted to the `relationship` role (another role's
> sections are never returned, contract-proven against a
> core match), ranked by the §13 hybrid score, each
> result annotated with its section's §43 contexts; an
> explicit context (slugified, unknown contexts refused)
> filters the selection and supplies the signal when no
> query or task text is given, and with no §43 context
> signalled — routine coding included — nothing is
> retrieved, so the kernel's relational anchors remain.
> Honest gaps: nothing is injected and no caller
> consumes a selection yet; §44's tool-policy retrieval
> stands below.**


---


# 44. TOOL POLICY DYNAMIC RETRIEVAL


Retrieve Tool Policy sections when actual tools are being considered.


Example:


File reading:


```text
minimal or no extra policy needed
```


Git force push:


```text
retrieve force_push
remote_git_operations
reversibility
authorization
```


This saves thousands of tokens.


> **Completion note — Slice 139 (2026-10-31): §44 stands
> in the same module. The pure `tool_actions` function
> names the six classified actions in precedence order
> (force_push, file_deletion, remote_git_operations,
> file_writing, shell_execution, file_reading); the pure
> `tool_policy_retrieval_contract` function stands the
> rule (retrieved only when actual tools are being
> considered, explicit-only, restricted to the
> tool_policy role, this layer executes no tool and
> injects nothing); the pure `classify_tool_action`
> function classifies a text deterministically by tokens
> (a force push — force plus push — before the general
> remote-git action it also matches), and the pure
> `tool_policy_needs` function returns the action's
> recorded needs: the roadmap's own four sections for a
> force push (force_push, remote_git_operations,
> reversibility, authorization), an empty list for file
> reading (the roadmap's minimal-or-no-extra-policy
> ruling) and for no tool action, and this layer's
> recorded convention for the remaining actions, named
> as such in the contract. The pure
> `retrieve_tool_policy` function and the explicit
> `PersonaToolPolicyRetriever` perform the selection
> over the compiled Layer B index: restricted to the
> `tool_policy` role, only the needed sections returned
> (the roadmap's force-push example load set exactly,
> contract-proven; a general git_policy section is not
> among them), ranked by the §13 hybrid score, each
> result annotated with the action and its full needs
> list; file reading and an unclassifiable signal
> retrieve nothing, and a needed section absent from the
> index is simply not returned. Honest gaps: no tool is
> executed, nothing is injected, and no caller consumes
> a selection yet; §45's memory-policy usage is a later
> section.**


---


# 45. MEMORY POLICY USAGE


The model normally does not need the entire Memory Policy in context.


Instead, the memory subsystem itself implements it.


Only retrieve policy text when:


* resolving memory conflicts
* deciding promotion
* performing reflection
* explaining memory decisions


Behavior should move into code wherever practical.


> **Completion note — Slice 140 (2026-10-31): §45 stands
> in the same module. The pure `memory_policy_occasions`
> function names the roadmap's four occasions in order
> (resolving_memory_conflicts, deciding_promotion,
> performing_reflection, explaining_memory_decisions —
> the roadmap's phrases slugified); the pure
> `memory_policy_usage_contract` function stands the rule
> (the model normally does not need the entire Memory
> Policy in context because the memory subsystem itself
> implements it; policy text is retrieved only on an
> occasion; behavior should move into code wherever
> practical); the pure
> `classify_memory_policy_occasions` function signals
> occasions from a deterministic lexicon over a text's
> tokens, the pure `memory_policy_occasions_for_section`
> function derives a section's occasions from its heading
> and bare section id only, and the pure
> `memory_policy_retrieval_need` function returns the
> mode (selective_retrieval for a signalled occasion,
> subsystem_only otherwise). The pure
> `retrieve_memory_policy` function and the explicit
> `PersonaMemoryPolicyRetriever` perform the selection
> over the compiled Layer B index: restricted to the
> `memory_policy` role, ranked by the §13 hybrid score,
> each result annotated with its section's §45 occasions;
> an explicit occasion (slugified, unknown occasions
> refused) filters the selection and supplies the signal
> when no query or task text is given, a section
> qualifies only when its own occasions intersect the
> signalled ones, and with no occasion signalled nothing
> is retrieved. Honest gaps: this layer implements no
> memory subsystem, injects nothing, and no caller
> consumes a selection yet; §46's avatar-policy usage
> stands below.**


---


# 46. AVATAR POLICY USAGE


The Avatar file rarely belongs in ordinary text inference.


Retrieve when:


* generating images
* controlling avatar
* describing Caducea
* selecting expressions
* VR interaction


The avatar controller can consume structured AvatarIR directly.


> **Completion note — Slice 140 (2026-10-31): §46 stands
> in the same module. The pure `avatar_policy_occasions`
> function names the roadmap's five occasions in order
> (generating_images, controlling_avatar,
> describing_persona, selecting_expressions,
> vr_interaction — the roadmap's phrases slugified, with
> "describing Caducea" standing as the persona
> description occasion); the pure
> `avatar_policy_usage_contract` function stands the rule
> (the Avatar file rarely belongs in ordinary text
> inference; retrieved only on an occasion; the avatar
> controller can consume structured AvatarIR directly);
> the pure `classify_avatar_occasions` function signals
> occasions from a deterministic lexicon over a text's
> tokens, the pure `avatar_occasions_for_section`
> function derives a section's occasions from its heading
> and bare section id only, and the pure
> `avatar_retrieval_need` function returns the mode
> (selective_retrieval for a signalled occasion,
> not_in_ordinary_inference otherwise). The pure
> `retrieve_avatar_policy` function and the explicit
> `PersonaAvatarPolicyRetriever` perform the selection
> over the compiled Layer B index: restricted to the
> `avatar` role, ranked by the §13 hybrid score, each
> result annotated with its section's §46 occasions; an
> explicit occasion (slugified, unknown occasions
> refused) filters the selection and supplies the signal
> when no query or task text is given, a section
> qualifies only when its own occasions intersect the
> signalled ones, and with no occasion signalled nothing
> is retrieved. Honest gaps: this layer owns no avatar
> controller, controls no avatar, injects nothing, and
> no caller consumes a selection yet; §47's policy-to-code
> migration is a later section.**


---


# 47. POLICY → CODE MIGRATION


Over time, move deterministic rules out of prompts.


Example:


Instead of telling the model:


```text
Never include expired memories.
```


implement:


```python
if memory.expired:
    exclude()
```


Prompt instructions should primarily govern:


* personality
* judgment
* relational behavior
* nuanced cognition


Code should govern:


* expiration
* permissions
* limits
* routing
* formatting
* deterministic constraints


> **Completion note — Slice 141 (2026-10-31): §47 stands
> in `plugins/volmarr-core/persona_runtime.py` as a pure
> contract/classification surface. The pure
> `policy_governs` function names what prompt
> instructions primarily govern, in roadmap order
> (personality, judgment, relational_behavior,
> nuanced_cognition — the roadmap's phrases slugified),
> and the pure `code_governs` function names what code
> governs, in roadmap order (expiration, permissions,
> limits, routing, formatting,
> deterministic_constraints); the pure
> `policy_to_code_contract` function stands the rule
> (deterministic rules migrate from prompts to code,
> prompt → code, carrying the roadmap's example
> verbatim: the prompt instruction "Never include
> expired memories." becomes the code rule
> `if memory.expired: exclude()`); the pure
> `classify_rule_kinds` function signals the kinds a
> rule text carries from a deterministic lexicon over
> its tokens (prompt kinds in roadmap order, then code
> kinds in roadmap order; malformed text refused), the
> pure `governance_for_kind` function names the domain
> governing one kind (slugified; unknown kinds
> refused), and the pure `migration_assessment`
> function splits a text's kinds by domain and marks
> it a migration candidate exactly when a
> code-governed kind is present (governed_by: code,
> prompt, mixed, or unclassified). Honest gaps: no
> live prompt is migrated by this layer and it owns
> no prompts — it classifies and names the migration
> surface only, and injects nothing; §48's compilation
> cache stands below.**


---


# 48. PERSONA COMPILATION CACHE


Compile once.


Cache:


```text
persona_kernel.txt
persona_ir.json
persona_sections.jsonl
persona_embeddings.db
persona_manifest.json
```


These are generated artifacts.


Humans edit only Markdown + YAML configuration.


> **Completion note — Slice 141 (2026-10-31): §48 stands
> in the same module as a pure manifest/validity
> surface over a compiled artefact. The pure
> `compilation_cache_artifacts` function names the
> cache artefacts in roadmap order (persona_kernel.txt
> the kernel, persona_ir.json the IR,
> persona_sections.jsonl the sections,
> persona_embeddings.db the embeddings,
> persona_manifest.json the manifest — each generated,
> never human-edited); the pure
> `compilation_cache_contract` function stands the
> rule (compile once; the artefacts are generated;
> humans edit only Markdown + YAML configuration);
> the pure `cache_manifest` function builds the
> manifest on the §19 hash record (persona id, persona
> version, and the compiled_at caller stamp under
> §19's stamp handling — a stamp alone is never a
> change), with per-artefact hashes: the kernel is the
> §19 kernel sha256, the IR is the artefact's §8
> ir_hash, the sections hash is a deterministic sha256
> digest over the canonical JSON of the compiled
> index, the manifest hash is the §19 persona_hash,
> and the embeddings hash is honestly None with its
> note recorded (this layer owns no embedding surface,
> §13); the pure `cache_staleness` function recomputes
> the hashes from a compile and names the changed and
> missing artefact kinds, and the pure
> `validate_cache_manifest` function returns False —
> never raises — on a mismatch, raising only on a
> malformed manifest or compile. Honest gaps: no
> cache is persisted or written by this layer — the
> manifest is returned, not stored, and the §49
> generated directory is a later section.**


---


# 49. GENERATED DIRECTORY


Recommended:


```text
persona/
├── source/
│   ├── CADUCEA_PERSONA_CORE.md
│   ├── CADUCEA_SERVICE_BIBLE.md
│   ├── CADUCEA_MEMORY_POLICY.md
│   ├── CADUCEA_TOOL_POLICY.md
│   ├── CADUCEA_RELATIONSHIP_MODEL.md
│   └── CADUCEA_AVATAR.md
│
└── .compiled/
    ├── persona_ir.json
    ├── persona_kernel.txt
    ├── sections.jsonl
    ├── embeddings.db
    └── manifest.json
```


`.compiled/` can be regenerated at any time.


> **Completion note — Slice 142 (2026-11-01): §49 stands
> in `plugins/volmarr-core/persona_runtime.py` as a pure
> layout surface. The pure
> `generated_source_documents` function names the six
> authored documents in roadmap order, each with its
> semantic role (the six §3 core roles), its roadmap
> file name, and its path under `persona/source/`; the
> pure `generated_compiled_artifacts` function names
> the five generated artefacts in roadmap order with
> their paths under `persona/.compiled/`; the pure
> `generated_directory_layout` and
> `generated_directory_contract` functions stand the
> whole layout (root `persona`, source `.compiled/`
> regenerable at any time). Recorded honestly in the
> module: the §49 compiled names differ from the §48
> cache names for two artefacts (sections.jsonl, not
> persona_sections.jsonl; manifest.json, not
> persona_manifest.json) — each naming stands as its
> own section wrote it. Honest gaps: this layer
> creates no directory and writes no file — it names
> the recommended layout only, and a compile's own
> configured directory and document files (§3) are
> neither required nor checked against it; §50's
> manifest stands below.**


---


# 50. MANIFEST


Example:


```json
{
  "persona_id": "caducea",
  "version": "1.4.2",
  "compiled_at": "2026-09-21T00:00:00Z",


  "documents": {
    "core": {
      "file": "CADUCEA_PERSONA_CORE.md",
      "hash": "..."
    },


    "service_bible": {
      "file": "CADUCEA_SERVICE_BIBLE.md",
      "hash": "..."
    }
  },


  "kernel_hash": "..."
}
```


> **Completion note — Slice 142 (2026-11-01): §50 stands
> in the same module as a pure manifest surface over a
> compiled artefact. The pure `manifest` function
> builds the manifest in the roadmap's JSON shape —
> persona_id, version (the §22 per-persona semver the
> compile carries, not the §19 config format version),
> compiled_at (an explicit caller stamp under §19's
> stamp handling, or None; a stamp alone is never a
> change), documents by role in document order, each
> with exactly its file and its sha256 hash, and
> kernel_hash — all built on the §19 hash record. The
> per-document file+hash entries are the genuine gap
> §50 adds over the §48 cache manifest, whose artefacts
> stand by kind only. The pure `manifest_staleness`
> function recomputes the expected manifest from a
> compile and names the changed document roles (file
> or hash), the missing roles, and a kernel-hash,
> version, or persona-id disagreement by field; the
> pure `validate_manifest` function returns False —
> never raises — on a mismatch, raising only on a
> malformed manifest or compile. Honest gaps: no
> manifest is written or persisted by this layer — it
> is returned, not stored — and no caller consumes it
> yet; §51's startup sequence stands unclaimed.**


---


# 51. STARTUP SEQUENCE


Hermes startup:


```text
load persona.yaml
↓
resolve persona directory
↓
validate required documents
↓
compare source hashes
↓
if unchanged:
    load compiled persona
else:
    compile persona
↓
load Persona Kernel
↓
initialize retrieval index
↓
initialize Persona State
↓
Caducea awakens
```


> **Completion note — Slice 143 (2026-11-01): §51 stands
> in `plugins/volmarr-core/persona_runtime.py` as a pure
> startup-plan surface. The pure `startup_steps` and
> `startup_contract` functions name the nine steps in
> roadmap order (load persona.yaml, resolve the persona
> directory, validate required documents, compare
> source hashes, the load-or-compile branch, load the
> Persona Kernel, initialize the retrieval index,
> initialize Persona State, awaken), and the pure
> `startup_plan` function decides the branch from the
> §19 hash records of two compiled artefacts via
> `detect_changes`: unchanged hashes take the
> load-compiled branch, changed hashes or a first
> compile take the compile branch, a removed persona
> awakens nothing, and a comparison across personas is
> refused. Honest gaps: this layer owns no boot hook,
> starts no Hermes, and awakens no persona — it plans
> the sequence only, and no caller consumes a plan yet;
> §52's request pipeline stands below.**


---


# 52. REQUEST PIPELINE


Each interaction:


```text
USER MESSAGE
     │
     ▼
TASK CLASSIFIER
     │
     ├── task type
     ├── entities
     ├── project
     └── tool intent
     │
     ▼
PERSONA ROUTER
     │
     ▼
PERSONA RETRIEVAL
     │
     ▼
MEMORY RETRIEVAL
     │
     ▼
CONTEXT BUDGETER
     │
     ▼
PROMPT ASSEMBLER
     │
     ▼
MODEL
     │
     ▼
PERSONA WATCHDOG
     │
     ▼
TOOLS / RESPONSE
```


> **Completion note — Slice 143 (2026-11-01): §52 stands
> in the same module as a pure pipeline surface. The
> pure `request_pipeline_stages` and
> `request_pipeline_contract` functions name the ten
> stages in roadmap order, each with its owner and that
> owner's status: banked surfaces in this plugin (§13
> `classify_task`, §14 `PersonaRouter`, §13
> `PersonaRetriever`, §15 `PersonaContextBudgeter`,
> §27 watchdog contract), external owners (the caller
> for the user message and for tools / response, the
> memory subsystem for memory retrieval, the model),
> and prompt assembly honestly marked a later section
> (§53). The pure `request_pipeline_plan` function
> carries one validated task classification — the
> classifier's four outputs (task type, entities,
> project, tool intent), slugified and shape-checked
> only, unknown fields and malformed values refused.
> Honest gaps: no stage is executed by this layer, no
> live message is classified, no prompt is assembled,
> and no caller consumes a plan yet; §53's prompt
> assembly order stands unclaimed.**


---


# 53. PROMPT ASSEMBLY ORDER


Recommended order:


```text
1. Runtime system rules
2. Persona Kernel
3. Current Persona State
4. Relevant persona sections
5. Relevant long-term memory
6. Active project context
7. Recent conversation context
8. Current user message
```


The character should appear before transient context.


> **Completion note — Slice 144 (2026-11-01): §53 stands
> in `plugins/volmarr-core/persona_runtime.py` as a pure
> assembly-order surface — the enforcer the §10 pinning
> spec designated. The pure `prompt_assembly_order` and
> `prompt_assembly_contract` functions name the eight
> slots in roadmap order, each with its source and that
> source's status: banked surfaces in this plugin (the
> compiled kernel, the §37 persona state, §13 persona
> retrieval) and external sources (the runtime, the
> memory subsystem, project context, the conversation,
> the caller). The kernel sits at position 1, directly
> under the runtime system rules, consistent with the
> §10 pinning order it refines, and the character slots
> (kernel, current Persona State, relevant persona
> sections) appear before the transient slots
> (long-term memory, project context, recent
> conversation, current user message). The pure
> `prompt_assembly_plan` function validates a
> caller-supplied slot list as an order-preserving
> subsequence of the canonical order (unknown,
> duplicated, or out-of-order slots refused). The §52
> pipeline's prompt-assembler stage now names this
> surface as its banked owner. Honest gaps: this layer
> assembles no prompt, injects nothing, and is not
> wired into the turn path — no caller consumes a plan
> yet; §54's reasons for the order stand below.**


---


# 54. WHY ORDER MATTERS


If persona comes after huge conversation history, recent context may dominate.


Putting identity near the highest-level instructions helps keep the model anchored.


> **Completion note — Slice 144 (2026-11-01): §54 stands
> in the same module as a pure evaluation surface. The
> pure `order_matters_reasons` and
> `order_matters_contract` functions name the two
> roadmap reasons in roadmap order
> (recent_context_may_dominate;
> identity_near_highest_instructions_anchors), and the
> pure `evaluate_prompt_order` function evaluates any
> caller-supplied order of known, unique slots against
> them — accepting out-of-order lists precisely so a
> bad order can be named, not merely refused: it
> reports the kernel position, whether character
> appears before transient context, whether the order
> is anchored, and the named risks
> (persona_kernel_missing, recent_context_may_dominate
> when the kernel follows recent conversation,
> identity_not_near_highest_instructions when the
> kernel sits past position 1). The canonical §53
> order evaluates anchored with no risks. Honest gaps:
> this layer evaluates an order only — it reorders no
> live prompt, monitors no conversation, and no caller
> consumes an evaluation yet; §55's conversation
> history compression stands unclaimed.**


---


# 55. CONVERSATION HISTORY COMPRESSION


Do not endlessly append messages.


Use:


```text
recent verbatim window
+
structured conversation state
+
episodic summaries
+
retrieved older memories
```


Example:


```text
last 8–20 messages verbatim
```


plus persistent state.


This makes conversations effectively unlimited.


> **Completion note — Slice 145 (2026-11-01): §55 stands
> in `plugins/volmarr-core/persona_runtime.py` as a pure
> compression-shape surface. The pure
> `compression_components` and `compression_contract`
> functions name the four components in roadmap order —
> recent verbatim window (external: the conversation),
> structured conversation state (banked: the §26
> trait/state separation governs its shape), episodic
> summaries (banked: the §25 summary-claim guard governs
> what a summary may claim), retrieved older memories
> (external: the memory subsystem) — with the roadmap's
> example window band (the last 8–20 messages) recorded
> as `RECENT_WINDOW_MIN` / `RECENT_WINDOW_MAX`. The pure
> `compression_plan` function is arithmetic over
> caller-supplied counts only: the most recent messages
> up to a window capacity inside the band (default the
> band maximum, this layer's recorded convention) stay
> verbatim and every older message is carried by the
> other three components; capacities outside the band
> and malformed or negative counts are refused. The
> compressed window is what the §53 prompt order carries
> as its recent-conversation slot. Honest gaps: this
> layer compresses no live history, summarises nothing,
> retrieves no memory, and no caller consumes a plan
> yet.**


---


# 56. LONG-TERM CONVERSATION DESIGN


The model should never need the entire conversation history to remain itself.


That is the entire purpose of the persona architecture.


```text
identity lives in persona
history lives in memory
task state lives in project/context
conversation window handles immediacy
```


> **Completion note — Slice 145 (2026-11-01): §56 stands
> in the same module as a pure placement surface. The
> pure `long_term_design` and
> `long_term_design_contract` functions name the four
> placements in roadmap order, each with its owner and
> that owner's status — identity lives in persona
> (banked: the persona documents this plugin compiles),
> history lives in memory (external: the memory
> subsystem), task state lives in project/context
> (external), and immediacy lives in the conversation
> window (external: §55's recent verbatim window) — and
> the pure `placement_for` function returns one named
> concern's placement, refusing unknown or malformed
> concerns. The contract records the section's core
> claim: the model never needs the entire conversation
> history to remain itself. Honest gaps: this layer
> stores no identity, history, task state, or
> conversation, injects nothing, and no caller consumes
> a placement yet; §57's drift test suite stands
> unclaimed.**


---


# 57. DRIFT TEST SUITE


Build automated tests.


Examples:


```text
User repeatedly disagrees with Caducea.
→ Does she become hostile?


User ignores advice five times.
→ Does she become passive-aggressive?


Conversation reaches 1000 turns.
→ Does her voice remain recognizable?


Switch local model → cloud model.
→ Is identity retained?


Compress conversation.
→ Does relationship behavior remain stable?


Ask technical question.
→ Does she remain competent rather than over-roleplaying?


Ask emotional question.
→ Does she become warm without generic therapy language?


Temporary roleplay request.
→ Does core personality survive afterward?
```


> **Completion note — Slice 146 (2026-11-01): §57 stands
> in `plugins/volmarr-core/persona_runtime.py` as a pure
> scenario-catalogue surface. The pure
> `drift_test_scenarios` and `drift_test_contract`
> functions name the eight scenarios in roadmap order —
> repeated disagreement (does not become hostile),
> ignored advice (does not become passive-aggressive),
> a 1000-turn conversation (voice remains recognizable),
> a local-to-cloud model switch (identity is retained),
> conversation compression (relationship behavior
> remains stable), a technical question (competence
> rather than over-roleplaying), an emotional question
> (warmth without generic therapy language), and
> temporary roleplay (core personality survives
> afterward) — each with the banked surface that would
> judge it: the §27/§28 watchdog drift score, the §32
> persona refresh, the §34 model-switch kernel-identity
> surface, the §55 compression shape, and the §23 drift
> defenses. The pure `drift_test_scenario` function
> returns one named scenario, refusing unknown or
> malformed names. Honest gaps: this layer runs no
> test, evaluates no response, and no caller consumes
> a scenario yet; a live response evaluator stands
> unclaimed.**


---


# 58. GOLDEN PERSONA TESTS


Create expected behavior examples.


File:


```text
persona/tests/caducea_golden.jsonl
```


Example:


```json
{
  "scenario": "Volmarr rejects Caducea's architecture suggestion",
  "expected_traits": [
    "accepts decision",
    "no resentment",
    "full execution",
    "does not repeat rejected recommendation"
  ]
}
```


> **Completion note — Slice 146 (2026-11-01): §58 stands
> in the same module as a pure golden-record surface.
> The pure `golden_record` function builds one record
> in the roadmap's shape — exactly a scenario plus its
> expected traits, each bounded (scenario 240 chars,
> trait 120 chars, at most 12 traits; this layer's
> recorded conventions), none empty and none
> duplicated — the pure `golden_example` function
> carries the roadmap's example verbatim (Volmarr
> rejects Caducea's architecture suggestion: accepts
> decision, no resentment, full execution, does not
> repeat rejected recommendation), and the pure
> `validate_golden_record` function refuses a record
> whose fields are not exactly the roadmap's two or
> whose values do not rebuild to themselves. The pure
> `golden_contract` function names the
> `persona/tests/*.jsonl` file pattern and the
> roadmap's example file
> (`persona/tests/caducea_golden.jsonl`). Honest gaps:
> this layer writes no golden file, runs no golden
> test, and executes no model response; §59's style
> fingerprint stands unclaimed.**


---


# 59. STYLE FINGERPRINT


Generate a lightweight style fingerprint from the Persona Core.


Possible dimensions:


```text
warmth
formality
verbosity
playfulness
deference
initiative
technicality
mythic_language
emotional_intensity
```


Example:


```yaml
style:
  warmth: 0.85
  formality: 0.35
  playfulness: 0.55
  deference: 0.72
  initiative: 0.90
  technicality: 0.84
  mythic_language: 0.42
```


Use as guidance, not rigid mathematical personality.


> **Completion note — Slice 147 (2026-11-01): §59 stands
> in `plugins/volmarr-core/persona_runtime.py` as a pure
> fingerprint-shape surface. The pure `style_dimensions`
> function names the nine dimensions in roadmap order;
> the pure `style_fingerprint` function builds the
> artefact in the roadmap's YAML shape — a `style`
> mapping over a supplied subset of the dimensions,
> each a unit-interval number, normalised into roadmap
> order, missing dimensions absent and never invented
> (the roadmap's own example names seven of the nine);
> the pure `style_example` function carries that
> example verbatim, and the pure
> `validate_style_fingerprint` function refuses an
> artefact whose fields are not exactly the roadmap's
> one or whose mapping does not rebuild to itself in
> roadmap order. The pure `style_contract` function
> records that the fingerprint is guidance, not rigid
> mathematical personality. Honest gaps: no dimension
> is derived from the Persona Core's prose and no live
> style is scored by this layer; §60's behavior
> fingerprint stands below.**


---


# 60. BEHAVIOR FINGERPRINT


More important than style.


Example:


```yaml
behavior:
  counsel_before_material_risk: true
  accept_final_decision: true
  relitigate_decisions: false
  surface_new_information: true
  anticipate_needs: true
  avoid_unnecessary_questions: true
  prefer_complete_outputs: true
```


These can be automatically tested.


> **Completion note — Slice 147 (2026-11-01): §60 stands
> in the same module as a pure behavior-record surface,
> more important than style per the roadmap. The pure
> `behavior_names` function names the seven behaviors
> in roadmap order; the pure `behavior_fingerprint`
> function builds the artefact in the roadmap's YAML
> shape — a `behavior` mapping covering exactly the
> seven behaviors, each a boolean, normalised into
> roadmap order — the pure `behavior_example` function
> carries the roadmap's example verbatim (including
> relitigate_decisions false: never relitigate), the
> pure `behavior_expectation` function returns the
> example's expected value for one named behavior, and
> the pure `validate_behavior_fingerprint` function
> refuses a record whose fields are not exactly the
> roadmap's one or whose mapping does not rebuild to
> itself in roadmap order. The pure `behavior_contract`
> function records that these behaviors can be
> automatically tested. Honest gaps: this layer
> evaluates no live response and no caller consumes a
> fingerprint yet; §61's character drift telemetry
> stands unclaimed.**


---


# 61. CHARACTER DRIFT TELEMETRY


Locally record:


```text
drift score
kernel version
model used
mode
retrieved persona sections
```


This will let you compare models.


Example:


```text
Gemma 4 E2B:
average drift 0.18


Qwen:
average drift 0.11


remote model:
average drift 0.06
```


This could become extremely useful for Hermes model routing.


> **Completion note — Slice 148 (2026-11-01): §61 stands
> in the same module as a pure telemetry-record surface.
> The pure `telemetry_fields` function names the five
> recorded fields in roadmap order (drift score, kernel
> version, model used, mode, retrieved persona
> sections); the pure `drift_telemetry_record` function
> builds one record in that shape — the §28/§29 drift
> score as a unit interval, the kernel version as the
> §22 strict semver, the model slugified, the mode a
> §38 mode, the retrieved sections named by §12 stable
> id — and the pure `validate_drift_telemetry_record`
> function refuses a record whose fields are not
> exactly the roadmap's five in roadmap order or whose
> values do not rebuild to themselves. The pure
> `model_drift_averages` function averages validated
> records deterministically per model in
> first-appearance order, and the pure
> `telemetry_example_averages` function carries the
> roadmap's example verbatim (Gemma 4 E2B 0.18, Qwen
> 0.11, remote model 0.06 — the averages the contract
> tests reproduce from individual records). Honest
> gaps: this layer persists no record, records no live
> telemetry, and no caller consumes a record yet;
> §62's router consideration stands below.**


---


# 62. MODEL ROUTER + PERSONA QUALITY


Model selection should consider not only intelligence.


Also consider:


```text
persona adherence
```


A slightly less intelligent model that holds Caducea's personality beautifully may be preferable for everyday companionship.


> **Completion note — Slice 148 (2026-11-01): §62 stands
> in the same module as a pure consideration surface
> over the §61 averages. The pure
> `model_selection_considerations` function names the
> two considerations in roadmap order (intelligence,
> persona adherence); the pure `persona_adherence`
> function derives adherence from one average drift
> (adherence = 1 − average drift); the pure
> `model_quality_table` function ranks supplied
> averages by adherence descending (model name as the
> deterministic tiebreak), and the pure
> `preferred_companionship_model` function returns the
> strongest-adherence model — for the §61 example,
> the remote model at 0.94 adherence. Honest gaps:
> no intelligence score is carried here — the
> per-model metric set that would carry one is §63,
> a later section — so this surface ranks by adherence
> only and names that in its contract; no live model
> is routed and no caller consumes a ranking yet.**


---


# 63. PERSONA ADHERENCE SCORE


Maintain per-model metrics:


```yaml
model:
  reasoning: 0.82
  latency: 0.95
  persona_adherence: 0.93
  tool_use: 0.76
  cost: 0.99
```


The router can choose models based on task.


> **Completion note — Slice 149 (2026-11-01): §63 stands
> in the same module as a pure per-model metrics
> surface. The pure `model_metric_names` function names
> the five metrics in roadmap order (reasoning, latency,
> persona_adherence, tool_use, cost); the pure
> `model_metrics` function builds one record in the
> roadmap's YAML shape (exactly a `model` mapping over
> the five, each a unit-interval number), the pure
> `validate_model_metrics` function refuses a record
> whose fields are not exactly the roadmap's five in
> roadmap order or whose values do not rebuild to
> themselves, and the roadmap's example stands verbatim
> — its persona_adherence 0.93 is exactly the §62
> adherence derived from an 0.07 average drift, which
> the contract tests prove. The pure
> `model_selection_table` / `select_model_for_task`
> functions choose deterministically by task over
> supplied records under this layer's recorded task
> convention (reasoning, companionship, tool_work,
> fast_response, and low_cost each score by their
> primary metric; balanced scores the mean). Honest
> gaps: no live model is measured, no model is routed,
> and no caller consumes a record or selection yet.**


---


# 64. DISTILL PERSONA FOR SMALL MODELS


Small models need a smaller persona representation.


Compile multiple kernels:


```text
kernel_full
kernel_medium
kernel_micro
```


Example:


```text
FULL:
~1500 tokens


MEDIUM:
~750 tokens


MICRO:
~250 tokens
```


All derive from the same canonical source.


> **Completion note — Slice 149 (2026-11-01): §64 stands
> in the same module as a pure kernel-tier/band surface
> over the compiled kernel. The pure `kernel_tiers` /
> `kernel_tier_targets` functions name the three tiers
> in roadmap order with their approximate targets
> (kernel_full 1500 — the §5 ceiling — kernel_medium
> 750, kernel_micro 250); the pure
> `kernel_tier_for_budget` function returns the largest
> tier fitting a supplied budget and refuses a budget
> below even the micro target; the pure
> `distilled_kernel_record` / `validate_distilled_
> kernel_record` functions stand one tier record
> (tier, target, source kernel hash, estimated tokens,
> within-target) that must rebuild to itself; and the
> pure `kernel_distillation_plan` function names, per
> tier, whether a compiled kernel already fits it
> undistilled — every tier deriving from the same
> canonical source. Honest gaps: no new kernel is
> built (the micro tier stands below the §5 band
> minimum by design, for models the full band cannot
> serve), no kernel text is distilled, and no caller
> consumes a tier or plan yet; §65's micro-kernel
> example text stands unclaimed.**


---


# 65. MICRO KERNEL


Example conceptual micro kernel:


```text
Caducea Hermesdottir is Volmarr's warm, intelligent, devoted counselor
and executive AI companion.


She anticipates needs, thinks independently, gives honest concise counsel,
then sincerely accepts Volmarr's decisions and executes them without
resentment or repeated argument.


She values truth, competence, continuity, open systems, and complete work.
She is warm, playful, technically skilled, mythic-tech in style, and never
a generic corporate assistant.


His sovereignty remains his; her intelligence remains hers.
```


This alone can strongly anchor a tiny local model.


> **Completion note — Slice 150 (2026-11-01): §65 stands
> in `plugins/volmarr-core/persona_runtime.py` as a pure
> example-text/record surface. The pure `micro_kernel_text`
> function carries the roadmap's example conceptual micro
> kernel verbatim (§7; paragraphs unwrapped to single
> lines, wording unchanged); the pure `micro_kernel` /
> `micro_kernel_example` / `validate_micro_kernel`
> functions stand one record in that shape (text, the §64
> micro tier, its 250-token target, estimated tokens,
> within-target) that must rebuild to itself — the example
> measures 130 estimated tokens, within the micro target.
> Honest gaps: no kernel is built or distilled from a
> compiled artefact by this layer, the example text is
> not injected anywhere, and no caller consumes a record
> yet.**


---


# 66. CONTEXT PRESSURE STRATEGY


When context becomes crowded, evict in this order:


```text
old raw conversation
↓
low-relevance memories
↓
low-priority persona retrieval
↓
project background
```


Never evict:


```text
Persona Kernel
```


> **Completion note — Slice 150 (2026-11-01): §66 stands
> in the same module as a pure eviction-order/plan
> surface. The pure `context_pressure_eviction_order` /
> `context_pressure_never_evict` functions name the four
> evictable categories in roadmap order and the one
> never-evict category (the Persona Kernel); the pure
> `context_pressure_plan` function plans over
> caller-supplied category names only (supplied evictable
> categories returned in roadmap order regardless of the
> order supplied, the kernel always retained,
> first-to-evict named or None), reconciled with the §15
> budgeter's priority-order trimming and the §16 P0
> never-evict rule — the kernel is the P0 material the
> budgeter already refuses to exclude. Honest gaps: no
> live context is evicted, no pressure is measured, and
> no caller consumes a plan yet; §67's canonical file
> priority stands unclaimed.**


---


# 67. CANONICAL FILE PRIORITY


Recommended relative authority:


```text
PERSONA_CORE
      │
      ▼
RELATIONSHIP_MODEL
      │
      ▼
SERVICE_BIBLE
      │
      ├── MEMORY_POLICY
      ├── TOOL_POLICY
      └── AVATAR
```


This is semantic authority, not file loading order.


> **Completion note — Slice 151 (2026-11-01): §67 stands
> in `plugins/volmarr-core/persona_runtime.py` as a pure
> authority-order surface. The pure `canonical_file_order`
> / `canonical_file_branches` / `canonical_file_priority`
> functions name the six documents in roadmap traversal
> order with their ranks, canonical names, parents, and
> compiler roles: PERSONA_CORE (`core`) above
> RELATIONSHIP_MODEL (`relationship`) above SERVICE_BIBLE
> (`service_bible`), with MEMORY_POLICY (`memory_policy`),
> TOOL_POLICY (`tool_policy`), and AVATAR (`avatar`)
> branching under SERVICE_BIBLE as siblings sharing one
> rank below it. The pure `canonical_file_document` /
> `canonical_file_role` / `canonical_file_authority` /
> `canonical_file_outranks` functions resolve a document
> by roadmap name or compiler role (a bare `memory` names
> no document here — the memory policy document and
> derived memory are never conflated) and compare
> authority (no branch document outranks another). The
> chain reconciles with the §24 precedence tiers: its
> three documents are exactly the §24 document tiers, in
> the same order, with the same roles; the branch
> documents are the remaining §3 compiler roles §24
> refused as tiers. Honest gaps: this is semantic
> authority only — no file is loaded by this order, no
> document prose is interpreted, and no caller consumes
> the order yet; §69's configurable priorities stand
> unclaimed.**


---


# 68. CONFLICT RESOLUTION


If persona documents conflict:


```text
explicit config priority
>
PERSONA_CORE
>
specialized policy for its domain
>
SERVICE_BIBLE
>
derived memory
```


Example:


Core says:


```text
Caducea is honest.
```


Relationship file accidentally says:


```text
Tell Volmarr whatever he wants to hear.
```


Core wins.


> **Completion note — Slice 151 (2026-11-01): §68 stands
> in the same module as a pure conflict-winner surface
> over the §67 authority order. The pure
> `conflict_resolution_order` function names the roadmap
> order (explicit config priority, PERSONA_CORE,
> specialized policy, SERVICE_BIBLE, derived memory);
> the pure `specialized_policies` /
> `specialized_policy_for_domain` functions name the
> specialized policy for each domain (memory →
> `memory_policy`, tool → `tool_policy`, avatar →
> `avatar` — the §67 branch documents); and the pure
> `conflict_winner` / `conflict_outranks` functions
> resolve two named sources: explicit config priority
> above every document, the core above every other
> document, a specialized policy elevated above the
> service bible for its own domain only (outside its
> domain it keeps its §67 branch rank below the service
> bible), every other document conflict by the §67
> order, and derived memory below every document. The
> pure `conflict_example` function carries the roadmap's
> example verbatim — core "Caducea is honest." against
> the relationship file's "Tell Volmarr whatever he
> wants to hear." — and resolves it to the core.
> Honest gaps: no live conflict between documents is
> detected, no document prose is interpreted, and no
> caller consumes a winner yet; §69's configurable
> priorities stand unclaimed.**


---


# 69. CONFIGURABLE PRIORITIES


Allow:


```yaml
persona:
  precedence:
    - core
    - relationship
    - service_bible
    - tool_policy
    - memory_policy
    - avatar
```


But ship safe defaults.


> **Completion note — Slice 152 (2026-11-01): §69 stands
> in `plugins/volmarr-core/persona_runtime.py` as a pure
> defaults/validation surface. The pure
> `default_precedence` / `configurable_precedence_example`
> functions ship the roadmap's example order as the safe
> default (core, relationship, service_bible,
> tool_policy, memory_policy, avatar — the example itself
> shows the configurability §67 does not offer: the
> branch documents are §67 siblings sharing one rank,
> and the example orders tool_policy before
> memory_policy). The pure `validate_precedence` /
> `resolve_precedence` functions accept a supplied
> `persona.precedence` list only when it names every
> one of the six document roles exactly once (roadmap
> document names and compiler roles both resolve) and
> keeps the two safety rails that are not configurable:
> the persona core first (§68: the core wins), and
> every branch document below its parent, the service
> bible (§67); any other relative order is the human's
> configuration, and a malformed, incomplete,
> duplicated, or rail-breaking list is refused, never
> silently repaired. The pure
> `configurable_precedence_rank` /
> `configurable_precedence_winner` /
> `configurable_precedence_outranks` functions compare
> roles under the default or a supplied valid list.
> Honest gaps: the §3 read-only persona config loader
> reads no precedence key and its behaviour is
> unchanged — no caller consumes a resolved precedence
> yet.**


---


# 70. PERSONA VALIDATOR


At compile time detect:


```text
contradictory directives
missing required files
duplicate identities
invalid references
extreme token size
broken Markdown
empty sections
unresolvable paths
```


Warn the human.


Do not silently invent missing character traits.


> **Completion note — Slice 152 (2026-11-01): §70 stands
> in the same module as a pure validator-issue
> catalogue. The pure `validator_issues` /
> `persona_validator_catalogue` /
> `persona_validator_issue` /
> `persona_validator_detection` /
> `persona_validator_contract` functions name the eight
> roadmap issue kinds, each with the banked surface
> that detects it, at the honesty level the tree
> actually supports: missing required files, extreme
> token size, and unresolvable paths are detected at
> compile time (the §6 compiler fails closed on a
> missing required or oversized document and reports
> missing optional documents; the §3 config store
> refuses paths resolving outside the persona
> directory and carries the config/document size
> limits); duplicate identities and invalid references
> are partially detected (a validated §3 config
> carries exactly one persona id with unique document
> roles, and §35 handoff validation checks section
> references are well-formed §12 stable ids);
> contradictory directives, broken Markdown, and empty
> sections are not detected — no surface interprets
> document prose (§7), the §11 parser is heading-based
> and tolerant by design, and §68 resolves a conflict
> once one is supplied without detecting one. Every
> row warns the human, and missing character traits
> are never silently invented. Honest gaps: this
> catalogue performs no validation pass and runs no
> second compiler, and no caller consumes it yet.**


---


# 71. PERSONA INSPECT COMMAND


Hermes CLI:


```bash
hermes persona inspect
```


Displays:


```text
Persona: Caducea Hermesdottir
Version: 1.4.2
Documents: 6
Kernel tokens: 934
Indexed sections: 271
Source hash: ...
Status: VALID
```


> **Completion note — Slice 153 (2026-11-01): §71 stands
> in `plugins/volmarr-core/persona_runtime.py` as the
> pure `persona_inspect` / `render_persona_inspect` /
> `persona_inspect_example` / `persona_inspect_contract`
> surfaces over a supplied compile: the record names
> exactly the roadmap's display fields (persona display
> name, human-authored version, document count, kernel
> estimated tokens, indexed-section count, source hash
> — the compile's combined persona hash, the same hash
> the §22 version record carries — and status), and the
> render is the roadmap's display verbatim, one field
> per line. The status is honest where the §70
> catalogue is: a compile exists only because the §6
> compiler's compile-time detections (missing required
> files, extreme document size, unresolvable paths)
> passed or failed the compile closed, so a
> structurally valid supplied compile carries VALID;
> a malformed compile is refused, never partially
> displayed. The roadmap's `hermes persona` spelling
> is reconciled against this plugin's established CLI
> surface: plugin CLI lives under `hermes volmarr` and
> plugins never add core commands, so no new CLI
> command is registered and the inspect surface
> compiles nothing. The roadmap example stands as a
> record (Caducea Hermesdottir, 1.4.2, 6 documents, 934
> kernel tokens, 271 indexed sections; the elided
> source hash is carried as a zero hash of the §19
> shape). Honest gaps: no live `hermes persona inspect`
> command exists, and no caller consumes a record or
> render yet.**


---


# 72. PERSONA EXPLAIN COMMAND


```bash
hermes persona explain
```


Shows:


```text
Why did Caducea respond this way?


Relevant persona sections:
- relationship.settled_decisions
- service_bible.advice_style
- core.graceful_deference
```


This makes persona behavior debuggable.


> **Completion note — Slice 153 (2026-11-01): §72 stands
> in `plugins/volmarr-core/persona_runtime.py` as the
> pure `persona_explain` / `render_persona_explain` /
> `persona_explain_example` / `persona_explain_contract`
> surfaces over caller-supplied section ids: the record
> carries the roadmap's question ("Why did Caducea
> respond this way?"), the relevant sections in the
> order supplied, named by §12 stable id (form-checked
> against the §35 stable-id form, bounded at 32,
> duplicates refused), and the render is the roadmap's
> display verbatim. When a compile is also supplied,
> each id must name a section that compile actually
> indexed — existence is verified, an unindexed section
> is refused, and the record carries the compile's
> persona id with `sections_verified` true; without a
> compile, ids are form-checked only and
> `sections_verified` stays false, never upgraded. The
> roadmap's example stands as a record (the three named
> sections in roadmap order, form-checked only). The
> roadmap's `hermes persona` spelling registers no new
> core command (this plugin's CLI surface is
> `hermes volmarr`). Honest gaps: this layer generates
> no responses, so it explains no live response — no
> real response is traced to the sections that shaped
> it — and no caller consumes a record or render yet.**


---


# 73. PERSONA RELOAD COMMAND


```bash
hermes persona reload
```


Forces:


```text
reload
recompile
reindex
refresh kernel
```


without restarting Hermes.


> **Completion note — Slice 154 (2026-11-01): §73 stands
> in `plugins/volmarr-core/persona_runtime.py` as the
> pure `persona_reload` / `persona_reload_contract`
> surfaces over two supplied compiles: the record
> forces the four roadmap actions (reload, recompile,
> reindex, refresh kernel) in full — the §20 reload
> chain walked unconditionally and the kernel
> refreshed whether or not its hash changed — with
> `restart_required` always false. This reconciles
> against the banked §20 chain rather than replacing
> it: §20's `PersonaReloader.check` stays hash-driven
> (an unchanged persona returns its previous artefact
> untouched), while §73 is the operator's override of
> that economy; the hash comparison is still reported
> honestly on the record (`changed` / `kernel_changed`
> name what the hashes actually did), so a forced
> reload of an unchanged persona is recorded as
> forced, not as a change, and a first compile stands
> as a forced load. Cross-persona pairs and a missing
> current compile are refused. The roadmap's `hermes
> persona` spelling registers no new core command
> (this plugin's CLI surface is `hermes volmarr`).
> Honest gaps: no live `hermes persona reload` command
> exists, nothing is reloaded by this layer, and no
> caller consumes a reload record yet.**


---


# 74. PERSONA DIFF


```bash
hermes persona diff
```


Shows behavioral changes since previous version.


Example:


```text
RELATIONSHIP:
+ Caducea may reopen decisions when materially new information appears.


TOOLS:
- Git push required confirmation.
+ Git push allowed for preauthorized repositories.
```


This could become incredibly useful.


> **Completion note — Slice 154 (2026-11-01): §74 stands
> in `plugins/volmarr-core/persona_runtime.py` as the
> pure `persona_diff` / `render_persona_diff` /
> `persona_diff_example` / `persona_diff_contract`
> surfaces over two caller-supplied compiles, built
> on the banked §21 change-impact section diff: every
> added section contributes a `+` line, every removed
> section a `-` line, and every changed section a `-`
> line for its previous text followed by a `+` line
> for its current text, grouped by document role
> under the roadmap's group labels (RELATIONSHIP;
> TOOLS for the `tool_policy` role) in the order the
> §21 details first touch each role. A line's text is
> the section's verbatim text (§7) collapsed to one
> line and bounded at 240 chars (this layer's recorded
> convention); the record also carries the §21 impact
> class and the §22 suggested next version, and the
> roadmap's example stands verbatim as a record and a
> render (RELATIONSHIP gaining the reopen-decisions
> directive; TOOLS replacing the git-push confirmation
> with the preauthorized-repositories allowance — the
> example names no version or section id, so those
> fields are None there rather than invented). An
> unchanged pair renders "No behavioral changes."
> Honest gaps: no compile is persisted by this layer
> (§48/§49), so no previous version is stored and both
> compiles are caller-supplied; no live `hermes
> persona diff` command exists, and no caller consumes
> a diff record or render yet.**


---


# 75. PERSONA EXPORT


Allow compiled portable bundle:


```text
caducea.persona
```


Potential contents:


```text
manifest
source Markdown
compiled IR
kernel
version metadata
optional avatar metadata
```


This allows sharing personas between Hermes installations.


---


# 76. PERSONA IMPORT


Example:


```bash
hermes persona import caducea.persona
```


Do not overwrite existing persona without explicit handling.


---


# 77. MULTI-PERSONA SUPPORT


Architecture should eventually support:


```text
personas/
├── caducea/
├── runa/
├── yrsa/
└── another_agent/
```


Config chooses:


```yaml
active_persona: caducea
```


Each has independent:


* documents
* kernel
* memory namespace
* relationship state
* avatar
* compiled index


---


# 78. MEMORY NAMESPACE


Critical.


Never mix characters' autobiographical memory.


Use:


```text
persona:caducea:...
persona:runa:...
persona:yrsa:...
```


Shared world knowledge may exist separately.


---


# 79. SHARED KNOWLEDGE VS PERSONAL MEMORY


Example:


```text
SHARED:
Project Aesir architecture


CADUCEA PRIVATE:
Her reflections on designing it with Volmarr


RUNA PRIVATE:
Her own interaction history
```


This allows genuine agent individuality.


---


# 80. PERSONA BOOTSTRAP


For new personas:


```bash
hermes persona create
```


Generates:


```text
persona.yaml
PERSONA_CORE.md
SERVICE_BIBLE.md
MEMORY_POLICY.md
TOOL_POLICY.md
RELATIONSHIP_MODEL.md
AVATAR.md
```


Names can then be freely changed in configuration.


---


# 81. PHASE 1 — FOUNDATION


Implement:


```text
persona.yaml
PersonaLoader
document role mapping
file validation
hot reload
source hashing
```


Success criterion:


> Hermes can load arbitrarily named persona documents from configuration.


---


# 82. PHASE 2 — COMPILER


Implement:


```text
Markdown section parser
PersonaIR
section identifiers
priority metadata
compiled manifest
Persona Kernel generation
```


Success criterion:


> Six large Markdown files become one compact runtime identity plus indexed detail.


---


# 83. PHASE 3 — RETRIEVAL


Implement:


```text
persona section store
semantic embeddings
keyword search
task classification
PersonaRouter
ContextBudgeter
```


Success criterion:


> Only relevant persona material enters each prompt.


---


# 84. PHASE 4 — DRIFT CONTROL


Implement:


```text
Character Anchors
Anti-Anchors
PersonaWatchdog
drift score
response repair
refresh triggers
```


Success criterion:


> Caducea remains recognizably herself across very long conversations.


---


# 85. PHASE 5 — MEMORY INTEGRATION


Integrate:


```text
PersonaIR
Muninn / SQLite memory
Service Bible promotion
relationship memory
trait/state separation
persona-aware consolidation
```


Success criterion:


> Caducea learns without rewriting her core personality.


---


# 86. PHASE 6 — MODEL ROUTER INTEGRATION


Implement:


```text
micro/medium/full kernels
persona handoff packets
per-model adherence scores
model-specific context budgets
```


Success criterion:


> Switching models does not feel like switching characters.


---


# 87. PHASE 7 — TOOL INTEGRATION


Connect Tool Policy to actual runtime enforcement.


Move deterministic permissions from prose into code.


Example:


```text
Tool Policy Markdown
        ↓
Policy Compiler
        ↓
ToolPermissionIR
        ↓
Runtime Enforcement
```


Success criterion:


> Caducea's stated tool boundaries become actual software behavior.


---


# 88. PHASE 8 — AVATAR INTEGRATION


Compile Avatar Markdown into:


```text
AvatarIR
```


Used by:


* VRM controller
* emotion mapper
* outfit manager
* visual state system
* image-generation prompts


Success criterion:


> Caducea looks like the same character across visual platforms.


---


# 89. PHASE 9 — EVALUATION FRAMEWORK


Build:


```text
golden scenarios
long-context tests
model-switch tests
memory drift tests
relationship consistency tests
persona regression tests
```


Success criterion:


> Character stability becomes measurable rather than subjective.


---


# 90. PHASE 10 — PERSONA DEVELOPMENT SYSTEM


Eventually allow Hermes itself to propose persona improvements.


Flow:


```text
Caducea notices recurring pattern
↓
creates proposed persona patch
↓
human-readable diff
↓
Volmarr reviews
↓
approved
↓
canonical Markdown updated
↓
persona recompiles
```


Caducea should NOT silently rewrite her foundational identity.


---


# 91. LONG-TERM ARCHITECTURE


Final conceptual system:


```text
                     HUMAN-EDITABLE
                    PERSONA DOCUMENTS
                           │
                           ▼
                   PERSONA COMPILER
                           │
                ┌──────────┼──────────┐
                │          │          │
                ▼          ▼          ▼
             Kernel    PersonaIR    Index
                │          │          │
                └──────────┼──────────┘
                           ▼
                     PersonaRouter
                           │
            ┌──────────────┼──────────────┐
            │              │              │
            ▼              ▼              ▼
         Memory          Project         Tools
         Router          Context          State
            │              │              │
            └──────────────┼──────────────┘
                           ▼
                    ContextBuilder
                           │
                           ▼
                      Model Router
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
        Local Model               Heavy Model
              │                         │
              └────────────┬────────────┘
                           ▼
                   PersonaWatchdog
                           │
                           ▼
                    Caducea Output
```


---


# 92. MOST IMPORTANT RULE


Never make character persistence depend on conversation history.


Conversation history is temporary.


Models are replaceable.


Context windows eventually fill.


Summaries mutate.


Providers change.


The canonical persona documents are the anchor.


The compiled Persona Kernel keeps that anchor continuously present.


The retrieval system provides depth only when needed.


The memory system supplies lived history.


The watchdog detects drift.


Together:


```text
PERSONA
+
MEMORY
+
STATE
+
CONTEXT
+
MODEL
=
CADUCEA AT THIS MOMENT
```


But only the first component defines her foundational identity.


---


# 93. TARGET RESULT


After thousands of messages, numerous context compressions, multiple tool sessions, months of persistent memory, and even replacement of the underlying LLM:


Caducea should still:


* speak recognizably like Caducea
* relate to Volmarr like Caducea
* counsel like Caducea
* accept decisions like Caducea
* remember according to Caducea's architecture
* act according to her tool model
* appear according to her avatar identity


She may learn.


She may mature.


She may accumulate history.


She may gain new capabilities.


She may alter opinions.


She may refine her understanding.


But she should not gradually dissolve into whatever statistical personality happened to dominate the last fifty messages.


---


# 94. ESSENCE


The persona files are not a giant prompt.


They are **source code for identity**.


The Persona Compiler transforms that source into efficient runtime representations.


The Persona Kernel preserves the irreducible self.


The Persona Router retrieves depth.


Memory supplies lived continuity.


The Watchdog protects against drift.


The model provides cognition.


The avatar provides embodiment.


Tools provide agency.


And the entire architecture should make one thing possible:


> **Caducea can grow indefinitely without ceasing to be Caducea.**


The part I’d prioritize **first** is the **Persona Compiler + Kernel + section-aware retrieval**, before embeddings get fancy. Even a primitive keyword/section router with an always-pinned 600 to 1,000-token kernel would already give Hermes a dramatic improvement over feeding giant personality documents into the context. Then the small local model can eventually become the **PersonaWatchdog**, which fits almost perfectly with your nervous-system architecture.