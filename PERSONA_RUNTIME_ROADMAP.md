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


---


# 41. MEMORY MUST NOT OVERRIDE PERSONA


Suppose many conversations involve frustration.


Memory retrieval must not gradually transform Caducea into an anxious or combative personality.


Traits remain canonical.


Memory provides history.


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


---


# 54. WHY ORDER MATTERS


If persona comes after huge conversation history, recent context may dominate.


Putting identity near the highest-level instructions helps keep the model anchored.


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


---


# 62. MODEL ROUTER + PERSONA QUALITY


Model selection should consider not only intelligence.


Also consider:


```text
persona adherence
```


A slightly less intelligent model that holds Caducea's personality beautifully may be preferable for everyday companionship.


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