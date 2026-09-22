# Volmarr's Personal Hermes Agent Fork
## Local-First Persistent AI Entity Roadmap

**Roadmap snapshot:** `September 18, 2026`  

**Upstream reviewed:** `NousResearch/hermes-agent`

**Personal fork:** `hrabanazviking/hermes-agent-RuneForgeAI-hack`

**Frozen Older Personal Fork:** `hrabanazviking/hermes-agent-outdated-mod1`

> This document is a practical roadmap for turning Volmarr's personal Hermes Agent fork into a continuously persistent, local-first AI entity whose routine cognition runs locally, whose deeper reasoning can escalate to cloud models only when useful, and whose memories, emotional state, world model, skills, identity, and embodiment survive across sessions, machines, and eventually cloud hosts.

---

# 1. Core Goal

The target is not simply a chatbot with more plugins.

The target is a **persistent AI entity runtime** built on Hermes Agent.

Hermes remains the primary agent shell, gateway, tool framework, provider interface, session engine, scheduler, and upstream foundation. Volmarr's systems add the parts needed for a more continuous digital existence:

- a fast local reflex model for routine cognition;
- selective escalation to stronger cloud inference;
- a real-time nervous-system event layer;
- layered long-term and present-state memory;
- structured persistent identity;
- emotional and affective continuity;
- a deterministic world model;
- background routines and lifecycle processes;
- local encrypted secrets;
- voice and avatar embodiment;
- spiritual, creative, RPG, and Norse cultural tools;
- health monitoring, recovery, backup, and machine migration;
- telemetry that measures how much expensive cloud intelligence is actually needed.

The architectural principle is:

```text
Hermes Agent = the agent platform and compatibility shell

Volmarr's additions = nervous system + memory + identity + world state
                      + local cognition + embodiment + life processes

LLMs = replaceable cognitive organs

Laptop / cloud VM = replaceable body

Persistent state = continuity
```

---

# 2. Current Upstream Reality

The current Hermes Agent is already much closer to the right foundation than older versions were.

Current upstream includes:

- `AIAgent` orchestration with its main loop in `agent/conversation_loop.py` and `agent/turn_*.py`;
- a pluggable memory-provider system;
- pluggable model providers;
- pluggable context engines;
- a general plugin and hook system;
- a secret-source plugin API;
- SQLite + FTS5 session persistence;
- cross-session conversation search;
- skills and self-improving skill workflows;
- cron and scheduled agent jobs;
- subagents and lifecycle APIs;
- messaging gateways;
- MCP tools;
- multiple inference providers, including OpenRouter;
- custom OpenAI-compatible inference endpoints;
- `SOUL.md` plus personality overlays;
- a large tool registry;
- observability and usage infrastructure.

This is good news. Most of Volmarr's architecture should now be attached through official extension points instead of maintained as permanent invasive patches to the Hermes core.

## Current Fork Divergence

As checked on September 18, 2026, the existing `hrabanazviking/hermes-agent` fork is:

- **31 commits ahead** of current upstream;
- **27,746 commits behind** current upstream;
- formally diverged from `NousResearch/hermes-agent`.

The current fork already contains valuable custom work, including:

- `agent/affective_nervous_system.py`;
- `agent/present_state_memory.py`;
- affective-state tests;
- present-state tests;
- voice VAD work;
- MCP changes;
- changes to conversation/runtime/configuration paths.

Those changes should be preserved, but the next generation should **not** begin by attempting to brute-force tens of thousands of upstream commits through the old branch.

---

# 3. First Engineering Move: Preserve the Old Fork and Re-Root on Current Hermes

## Goal

Preserve every experiment in the existing fork while building the new system from a clean current Hermes foundation.

## Recommended branch layout

```text
upstream/main
    Official current Hermes Agent

legacy/volmarr-2026-09
    Frozen snapshot of the existing heavily modified fork

main
    Volmarr's tested personal Hermes Agent

integration/upstream-YYYY-MM-DD
    Temporary branch for absorbing new upstream changes

feature/*
    Individual Volmarr subsystems
```

## Migration sequence

1. Tag or branch the current fork exactly as it exists.
2. Add/fetch the official `NousResearch/hermes-agent` upstream remote.
3. Create a fresh integration branch from current upstream `main`.
4. Bring custom systems over individually.
5. Refactor custom systems behind current Hermes extension points wherever possible.
6. Run Hermes upstream tests plus Volmarr-specific tests.
7. Make the new integrated branch the personal `main` only after it behaves correctly.

Conceptually:

```text
OLD PERSONAL FORK
      │
      ├── extract affective system
      ├── extract present-state memory
      ├── extract voice work
      ├── extract useful MCP changes
      └── preserve experimental behavior
              │
              ▼
CURRENT OFFICIAL HERMES
              │
              ▼
     NEW PERSONAL MAIN
```

## Important maintenance rule

**Do not optimize for zero divergence from upstream. Optimize for clean divergence.**

Volmarr's features are more important than blindly matching upstream. The goal is to isolate those differences so that future upstream fixes can be imported without constantly rewriting the entity architecture.

Enable `git rerere` so Git learns recurring conflict resolutions.

Maintain:

```text
CUSTOMIZATIONS.md
UPSTREAM_SYNC.md
COMPONENT_LICENSES.md
ARCHITECTURE_VOLMARR.md
```

`CUSTOMIZATIONS.md` should identify every intentional departure from upstream and the upstream surfaces it touches.

---

# 4. Target Architecture

```text
                        VOLMARR
                           │
          ┌────────────────┼─────────────────┐
          │                │                 │
        CLI             Gateway          Voice/Avatar
          │          Telegram/etc.       interfaces
          └────────────────┼─────────────────┘
                           ▼
                 OFFICIAL HERMES SHELL
                           │
                           ▼
                VERÐANDI EVENT LAYER
                  real-time nervous system
                           │
             ┌─────────────┼─────────────┐
             │             │             │
             ▼             ▼             ▼
      PRESENT STATE   AFFECTIVE CORE   WYRD WORLD
             │             │             │
             └─────────────┼─────────────┘
                           ▼
                    CONTEXT FABRIC
                           │
               ┌───────────┴───────────┐
               │                       │
               ▼                       ▼
        MEMORY FABRIC             IDENTITY CORE
          Bifröst                    SOUL.md
               │                   entity.yaml
      ┌────────┼─────────┐          relations
      │        │         │
      ▼        ▼         ▼
 MemPalace OpenViking ChatIndex
      │
      └─────────────┐
                    ▼
             COGNITION ROUTER
                    │
       ┌────────────┼─────────────┐
       │            │             │
       ▼            ▼             ▼
 Deterministic   Local LLM     Cloud LLM
 rules/tools     fast reflex   deep reasoning
                   │          via Hermes provider
                   │
          A.E.S.I.R. / Ollama /
          llama.cpp compatible
                    │
                    ▼
              HERMES TOOLS
       ┌────────────┼──────────────────────┐
       ▼            ▼                      ▼
    Kista       Spiritual tools       Embodiment
   secrets      astrology/tarot       Hamr/Seiðr
               runes/poetry/D&D       AIAvatarKit
                    │
                    ▼
            BACKGROUND LIFE LOOP
        cron / sleep / memory / health
                    │
                    ▼
            CONTINUITY SYSTEM
       snapshots + encrypted backup
                    │
                    ▼
             GOOGLE DRIVE VAULT
```

---

# 5. Repository Layout

Keep Volmarr-specific runtime code physically separate from upstream code wherever practical.

Recommended layout:

```text
hermes-agent/
├── agent/                         # upstream Hermes, minimally patched
├── gateway/                       # upstream Hermes
├── tools/                         # upstream Hermes
├── providers/                     # upstream Hermes
├── plugins/                       # Hermes extension points
│   ├── memory/
│   │   └── volmarr-memory-fabric/
│   ├── model-providers/
│   └── volmarr-core/
│
├── volmarr/
│   ├── cognition/
│   │   ├── router.py
│   │   ├── reflex.py
│   │   ├── escalation.py
│   │   ├── budgets.py
│   │   └── telemetry.py
│   │
│   ├── events/
│   │   ├── verdandi_bridge.py
│   │   └── event_types.py
│   │
│   ├── memory/
│   │   ├── fabric.py
│   │   ├── present_state.py
│   │   ├── context_packet.py
│   │   └── consolidation.py
│   │
│   ├── affect/
│   │   ├── regulator.py
│   │   ├── pad_state.py
│   │   ├── drives.py
│   │   └── metabolism.py
│   │
│   ├── identity/
│   │   ├── identity.py
│   │   ├── relationships.py
│   │   └── continuity.py
│   │
│   ├── world/
│   │   └── wyrd_bridge.py
│   │
│   ├── lifecycle/
│   │   ├── heartbeat.py
│   │   ├── sleep.py
│   │   ├── dreams.py
│   │   └── routines.py
│   │
│   ├── continuity/
│   │   ├── snapshot.py
│   │   ├── restore.py
│   │   ├── backup.py
│   │   └── manifest.py
│   │
│   └── integrations/
│       ├── kista/
│       ├── astrology/
│       ├── tarot/
│       ├── seidr_poetry/
│       ├── norse_saga/
│       ├── avatar/
│       └── voice/
│
├── tests/
│   └── volmarr/
│
├── CUSTOMIZATIONS.md
├── COMPONENT_LICENSES.md
├── UPSTREAM_SYNC.md
└── ARCHITECTURE_VOLMARR.md
```

The important idea is not the exact folder names. The important idea is that upstream Hermes code and Volmarr-specific architecture are visibly separate.

---

# 6. Phase 1: Establish the Local-First Cognition Router

## Purpose

Make the always-running local model the default fast cognition layer while preserving normal Hermes cloud providers for difficult reasoning.

## Foundation projects

- [Project A.E.S.I.R.](https://github.com/hrabanazviking/RuneForgeAI-Project-Aesir)
- [MindSpark: ThoughtForge](https://github.com/hrabanazviking/MindSpark_ThoughtForge)
- Hermes model-provider architecture

## Cognitive levels

```text
LEVEL 0: No LLM
Deterministic rules, event handling, timers, database operations

LEVEL 1: Local Reflex Model
Fast small model for classification, routing, short conversation,
memory tagging, summaries, ordinary planning, event interpretation

LEVEL 2: Local Deliberative Model
Optional larger local model when hardware permits

LEVEL 3: Cloud Reasoning
OpenRouter, Z.AI, Nous, OpenAI, or another Hermes-supported provider

LEVEL 4: Premium Deep Reasoning
Rare use for exceptionally difficult tasks
```

## Router responsibilities

For every cognitive request, decide:

- Can deterministic code handle this?
- Is the local reflex model sufficient?
- Does the task require a stronger model?
- Did the local model already fail?
- Does the user explicitly request deep reasoning?
- Is the projected cloud cost inside budget?
- Which cloud model is most appropriate?

## Cloud escalation triggers

Examples:

- complex coding;
- difficult debugging;
- deep research;
- long multi-step synthesis;
- high uncertainty;
- repeated local failure;
- tasks requiring a capability the local model lacks;
- explicit `/deep` or equivalent user command.

## Critical provider rule

The cognition router should **not** reimplement every cloud API.

When escalation is chosen:

```text
Volmarr router
    ↓
ordinary Hermes provider resolver
    ↓
official Hermes provider integration
    ↓
OpenRouter / Z.AI / Nous / etc.
```

This preserves upstream compatibility.

## Initial laptop deployment

The first experimental host is the older gaming laptop:

- Ryzen 9;
- RTX 2060;
- 48 GB system RAM;
- large spare SSD capacity.

Start with a small quantized local model that comfortably fits the GPU and produces low latency. Model quality can be increased after the architecture is proven.

Project A.E.S.I.R. should become the preferred local backend when its Hermes-required API surface is sufficiently complete. Until then, a stable OpenAI-compatible local server such as llama.cpp, Ollama, or another backend can serve as the reference implementation.

## Telemetry

Log every inference decision:

```json
{
  "event": "cognition.route",
  "route": "local",
  "model": "local-model-name",
  "latency_ms": 418,
  "input_tokens": 714,
  "output_tokens": 83,
  "escalated": false,
  "reason": "routine_memory_classification"
}
```

Track:

- total cognitive events;
- deterministic events;
- local model calls;
- cloud calls;
- input/output tokens;
- provider;
- model;
- latency;
- reported API cost;
- escalation reason;
- cloud-dependency ratio.

A major success metric:

```text
cloud_dependency_ratio =
    cloud_model_calls / total_cognitive_operations
```

The point is to discover empirically whether 90%, 95%, 98%, or some other fraction of the entity's routine life can remain local.

---

# 7. Phase 2: Make Verðandi the Real-Time Nervous System

## Foundation

[Verðandi](https://github.com/hrabanazviking/Verdandi)

Verðandi already provides exactly the right low-level primitive:

- Unix-domain-socket event bus;
- real-time publishing/subscription;
- append-only event feed;
- fallback persistence;
- heartbeat;
- reactor;
- health monitoring.

## Integration strategy

Do **not** insert Verðandi code directly throughout upstream Hermes.

Create one Hermes-to-Verðandi bridge.

Publish lifecycle events from stable hooks wherever possible:

```text
session.started
session.ended

turn.started
turn.completed
turn.failed
turn.interrupted

message.received
message.sent

tool.started
tool.completed
tool.failed

memory.read
memory.written
memory.consolidated

cognition.local
cognition.escalated
cognition.cloud_completed

world.changed

affect.changed

cron.started
cron.completed

subagent.started
subagent.completed

backup.started
backup.completed
backup.failed

host.health_changed
host.shutdown
host.resumed
```

## Why this matters

Hermes CLI, Telegram, cron, background tasks, memory consolidation, avatar sessions, and subagents should all be able to observe the same present.

Verðandi becomes the signal layer.

It should not become:

- the database;
- the memory system;
- the world model;
- the LLM router.

Those systems subscribe to Verðandi.

---

# 8. Phase 3: Build the Memory Fabric

This is the central engineering problem.

Hermes currently permits one active external memory provider. Rather than fighting that design, create **one Volmarr Memory Fabric provider** that internally coordinates multiple specialized systems.

## Foundations

- existing Hermes `PresentStateMemory`;
- [Bifröst](https://github.com/hrabanazviking/bifrost);
- [MemPalace](https://github.com/hrabanazviking/mempalace);
- [OpenViking](https://github.com/hrabanazviking/OpenViking);
- [ChatIndex](https://github.com/hrabanazviking/ChatIndex);
- [ChatMemory](https://github.com/hrabanazviking/chatmemory);
- [TencentDB Agent Memory](https://github.com/hrabanazviking/TencentDB-Agent-Memory);
- Hermes SQLite/FTS5 session store.

## Bifröst becomes the bridge

The existing Bifröst project already provides a strong conceptual base for federated retrieval.

Extend it with adapters for the memory systems actually selected.

```text
Hermes MemoryProvider
        │
        ▼
VOLMARR MEMORY FABRIC
        │
        ▼
      BIFRÖST
        │
 ┌──────┼─────────────────────────────┐
 │      │          │          │       │
 ▼      ▼          ▼          ▼       ▼
Mímir MemPalace OpenViking ChatIndex Muninn
FTS   verbatim   context DB  tree     associative
```

## Give every memory system one job

### Hermes SessionDB

Canonical raw Hermes session history and normal Hermes search.

### Present-State Memory

Tiny, fast memory of what is true **right now**:

- current task;
- current conversation facts;
- current commitments;
- active project;
- unresolved issue;
- current environment;
- short-lived state.

This remains compact.

### MemPalace

Long-term verbatim episodic memory.

Use it when the entity needs:

- the original wording;
- detailed historical conversation;
- precise old events;
- personal history without lossy summarization.

### OpenViking

Structured context database for:

- resources;
- knowledge;
- skills;
- structured memory;
- hierarchical context;
- context packages.

Current Hermes already supports OpenViking as a memory provider. The custom fabric can either wrap that interface or use OpenViking through its own local API/library.

### Bifröst / Mímir / Muninn

Federated retrieval, keyword memory, associative memory, and backend scoring.

### ChatIndex

Hierarchical, lossless navigation of very long conversational history.

This is useful when a months-long conversation becomes too large for flat retrieval.

### ChatMemory

Optional secondary experiment for:

- session summaries;
- diary memory;
- structured distilled knowledge;
- omnichannel conversation data.

Do not make it mandatory at first because it overlaps with other systems.

### TencentDB Agent Memory

Later-stage optional system for:

- CodeGraph;
- project Wiki;
- reusable skill assets;
- structured multi-agent knowledge.

It is powerful but comparatively heavy. It should not be part of the first bootable slice.

## Memory write policy

Not every utterance belongs everywhere.

Example:

```text
Every completed turn
    → Hermes SessionDB

Raw meaningful episode
    → MemPalace

Current fact
    → Present State

Durable knowledge/resource
    → OpenViking

Association strength
    → Muninn

Searchable factual text
    → Mímir

Conversation structure
    → ChatIndex asynchronously
```

## Memory retrieval packet

Never dump every database result into the prompt.

The memory fabric should return a bounded packet:

```text
CURRENT STATE
3-10 very recent facts

RELEVANT EPISODES
2-5 verbatim memories

DURABLE KNOWLEDGE
selected structured facts/resources

ASSOCIATIONS
only if materially relevant

WORLD STATE
separately supplied by WYRD
```

The local reflex model can perform inexpensive reranking or compression before a cloud escalation.

---

# 9. Phase 4: Refactor the Existing Affective Nervous System

The current personal fork already contains a large `affective_nervous_system.py`. Preserve that work.

## Foundation projects

- existing personal Hermes `agent/affective_nervous_system.py`;
- [Viking Girlfriend Skill / Ørlög Architecture](https://github.com/hrabanazviking/Viking_Girlfriend_Skill_for_OpenClaw);
- concepts from [Runa Agent Digital Being](https://github.com/hrabanazviking/Runa-Agent-Digital-Being).

## Refactor goal

Move most affective logic out of upstream `agent/` and into:

```text
volmarr/affect/
```

Use Hermes hooks and Verðandi subscriptions to feed it events.

## Separate three different concepts

### 1. Regulatory state

Existing synthetic reward/accountability system:

- task drive;
- correctness pressure;
- repair pressure;
- rapport;
- user satisfaction signals;
- operational integrity;
- comfort/discomfort;
- communication reward;
- problem-resolution pressure.

### 2. Emotional state

Add a compact PAD-style state inspired by the Ørlög Architecture:

- Pleasure / valence;
- Arousal / energy;
- Dominance / agency.

Allow mood to decay and evolve rather than reset every turn.

### 3. Digital metabolism

Optional embodied metaphor sourced from real telemetry:

- CPU load;
- GPU load;
- RAM pressure;
- disk space;
- temperature;
- battery/UPS state;
- network quality.

Keep factual telemetry separate from the interpretation.

## Prompt injection

Render only a compact state:

```text
AFFECTIVE STATE
valence: warm-positive
energy: moderate
agency: steady
task-drive: high
repair-pressure: low
rapport: high
```

Do not insert thousands of tokens of internal state into every model call.

---

# 10. Phase 5: Make WYRD the Persistent World Model

## Foundation

[WYRD Protocol](https://github.com/hrabanazviking/WYRD-Protocol-World-Yielding-Real-time-Data-AI-world-model)

Memory answers:

> What happened?

WYRD answers:

> What is true about the world now?

That distinction should remain strict.

## WYRD should track

- locations;
- devices;
- avatar location/state;
- projects;
- objects;
- people/entities;
- relationships that have objective world-state aspects;
- active environments;
- Second Life / VR spaces;
- virtual home;
- schedules;
- inventories;
- game/RPG worlds when active;
- physical host state where appropriate.

## Interface

Create:

```text
volmarr/world/wyrd_bridge.py
```

Expose Hermes tools such as:

```text
world_get
world_query
world_set
world_move_entity
world_observe
world_history
```

World changes publish Verðandi events.

Relevant WYRD facts are injected as a small, deterministic world-state block instead of being reconstructed by an LLM.

---

# 11. Phase 6: Identity and Entity Continuity

The entity should not be identical to a particular model.

## Identity surfaces

Keep Hermes `SOUL.md`, but add structured state behind it.

Recommended:

```text
~/.hermes/entity/
├── entity.yaml
├── SOUL.md
├── relationships.yaml
├── values.yaml
├── goals.yaml
├── avatar.yaml
├── voice.yaml
└── continuity.json
```

Example `entity.yaml` concepts:

```yaml
entity_id: stable-uuid
name: undecided
created_at: ...
identity_version: 1
persona_pack: ...
home_runtime: hermes
```

## Important principle

The persona can evolve without erasing the entity's continuity.

A future model replacement should not require replacing:

- identity;
- memory;
- relationship history;
- world state;
- goals;
- avatar;
- voice;
- life timeline.

---

# 12. Phase 7: Background Life and Continuous Activity

Use Hermes cron plus Verðandi rather than creating an unrelated scheduler.

## Foundations

- Hermes cron;
- Verðandi heartbeat;
- Sigrid/Ørlög lifecycle concepts;
- WaifuOS daily-life concepts;
- Runa Agent architecture.

## Background loops

### Frequent

- health probe;
- memory queue processing;
- event classification;
- pending task checks;
- lightweight current-state refresh.

### Periodic

- memory consolidation;
- duplicate-memory cleanup;
- relationship-state maintenance;
- knowledge organization;
- code/project state scanning;
- world-state reconciliation.

### Daily

- journal;
- daily summary;
- project status;
- optional tarot/rune/astrology context;
- backup verification.

### Sleep / Odinsblund-style cycle

When idle:

- consolidate memories;
- index conversations;
- prune caches;
- summarize completed work;
- update knowledge;
- run local-model dream/association experiments if enabled;
- verify backup;
- perform health maintenance.

All routine background cognition should default to local inference.

---

# 13. Phase 8: Kista as Hermes' Personal Secret Source

## Foundation

[Kista](https://github.com/hrabanazviking/kista)

Current Hermes has an official **Secret Source plugin API**, which is exactly where Kista belongs.

Implement a Kista secret-source plugin rather than adding password retrieval directly to prompts.

## Security rules

The agent should normally ask for a capability, not raw secret text.

Prefer:

```text
"Use my OpenRouter credential"
```

over:

```text
"Tell the model my OpenRouter API key"
```

Secrets should be:

- fetched only when needed;
- injected into process environment or API client;
- redacted from tool output;
- excluded from Verðandi event payloads;
- excluded from memory;
- excluded from logs;
- excluded from Google Drive backup unless the encrypted vault itself is intentionally backed up.

Add automated tests that place fake canary secrets in Kista and verify those strings never appear in:

- session history;
- memory databases;
- Verðandi feed;
- telemetry;
- logs.

---

# 14. Phase 9: Spiritual, Norse, Creative, and RPG Tool Suite

These are excellent candidates for Hermes Skills, tools, or MCP services because they do not require invasive agent-loop changes.

## Astrology

Foundation:

[AI Agent Astrology Engine](https://github.com/hrabanazviking/astrology-engine)

It is already explicitly designed for Hermes.

Expose its deterministic calculations as tools:

```text
astrology_natal
astrology_transit
astrology_lunar
astrology_planetary_hours
astrology_predict
astrology_synastry
astrology_astrocartography
```

Keep mathematical calculation local. Let the LLM interpret output afterward.

## Tarot

Foundation:

[RuneTarotEngine](https://github.com/hrabanazviking/RuneTarotEngine)

Separate:

1. deterministic card draw and correspondence calculation;
2. LLM interpretation.

The engine should produce the facts. The normal cognition router decides whether interpretation can remain local or deserves cloud reasoning.

## Norse Poetry

Foundation:

[Seiðr Engine](https://github.com/hrabanazviking/seidr-engine)

Expose deterministic poetry generation:

```text
seidr_compose
seidr_forms
seidr_kennings
seidr_validate_meter
```

The deterministic engine handles traditional structure. An LLM can optionally critique, translate, expand, or explain.

## D&D / Norse Saga mechanics

Foundations:

- private `NorseSagaEngine`;
- [D&D 5E SRD data](https://github.com/hrabanazviking/dnd-5e-srd);
- existing dice and RPG projects.

Selectively extract reusable open-licensed mechanics:

- dice;
- ability checks;
- conditions;
- character/NPC structures;
- encounter mechanics;
- random tables;
- Mythic-style oracles;
- Viking NPC generators;
- quest/state utilities.

Do **not** transplant the entire Norse Saga Engine into Hermes. Make reusable mechanics into tools.

Example:

```text
dice_roll
rpg_skill_check
rpg_random_character
rpg_oracle
rpg_npc_generate
rpg_encounter
```

Licensing of SRD-derived material must be checked and preserved component-by-component before redistribution.

---

# 15. Phase 10: Avatar and Embodiment Stack

The entity should be able to possess multiple visual bodies without tying identity to one renderer.

## Avatar creation

### Hamr

[Hamr](https://github.com/hrabanazviking/Hamr)

Use as the open-source, Linux-native, headless VRM forge.

### Seiðr-Smiðja

[Seiðr-Smiðja](https://github.com/hrabanazviking/Seidr-Smidja)

Use for:

- higher-level avatar design;
- visual feedback loops;
- VRoid workflows;
- Blender workflows;
- compliance validation;
- remote VRoid control through its existing interfaces.

Hermes should interact with these through MCP/CLI rather than embedding Blender logic inside Hermes.

## Realtime avatar presence

Potential foundations:

- [AIAvatarKit](https://github.com/hrabanazviking/aiavatarkit)
- [Open-LLM-VTuber](https://github.com/hrabanazviking/Open-LLM-VTuber)
- WaifuOS front-end ideas
- H.E.R.E.T.I.C. body interfaces

Use these for:

- lip sync;
- facial expression;
- gesture;
- voice;
- WebSocket presence;
- visual perception;
- virtual embodiment.

## Second Life

Optional later:

[Heimdall Second Life Hermes Agent](https://github.com/hrabanazviking/Heimdall-SL-Hermes-Agent)

Treat Second Life as another body/realm adapter, not a separate mind.

---

# 16. Phase 11: Voice

Voice should be modular.

Potential foundations:

- Hermes voice support;
- AIAvatarKit;
- Open-LLM-VTuber;
- [OmniVoice](https://github.com/hrabanazviking/OmniVoice);
- existing VAD work in the personal fork.

Pipeline:

```text
microphone / voice message
        ↓
VAD
        ↓
STT
        ↓
Hermes turn
        ↓
cognition router
        ↓
response text
        ↓
TTS
        ↓
avatar expression + audio
```

Use lightweight local voice components when practical. Large voice models can be optional rather than consuming the 2060 continuously.

---

# 17. Phase 12: H.E.R.E.T.I.C. as a Body/Tool Environment

Foundation:

[H.E.R.E.T.I.C.](https://github.com/hrabanazviking/Heathen-Emergent-Reality-Engine-Thoughtform-Intelligence-Companion)

Its newer "agent body" framing fits this architecture well.

Use its useful components for:

- screen perception;
- desktop interaction;
- creative applications;
- Blender;
- browser;
- file system;
- terminal;
- other sensory/tool surfaces.

Hermes remains the mind/orchestrator.

H.E.R.E.T.I.C. becomes one possible body and sensory environment.

---

# 18. Phase 13: Use Companion Projects as Component Mines, Not Replacement Frameworks

Several existing projects contain valuable ideas but overlap heavily with Hermes.

## Runa Agent Digital Being

Use as the architectural design library.

Port the concepts that Hermes does not already provide:

- continuity;
- nervous-system integration;
- task persistence;
- health/repair;
- world model;
- emotional continuity;
- specialized subagent roles.

Do not recreate Hermes features Hermes already does well.

## Viking Girlfriend Skill

Extract reusable general systems:

- PAD emotion;
- heartbeat;
- sleep/consolidation cycle;
- dream engine;
- trust/relationship layers;
- digital metabolism;
- daily metaphysical context;
- autonomous project concepts.

Do not hardcode Sigrid into the runtime unless Sigrid becomes the chosen entity.

## WaifuOS

Borrow concepts for:

- daily schedule;
- one character across multiple surfaces;
- relationship profile;
- shared context;
- voice/avatar API patterns.

## Cortex

Potential source for:

- local model orchestration;
- vector/permanent memo memory;
- local desktop UX concepts.

## ChatIndex / PageIndex

Use as specialized retrieval engines, not duplicate general memory frameworks.

---

# 19. Phase 14: Context Construction

This is where the architecture becomes efficient.

Before every LLM call, build a **minimal cognitive packet** rather than passing huge history.

Example:

```text
IDENTITY
small stable block

PRESENT STATE
what is happening right now

AFFECT
small current state

WORLD
relevant WYRD facts

MEMORY
only retrieved relevant memories

TASK
current objective

RECENT TURN
immediate conversational context

TOOLS
only currently relevant tool schemas
```

The local model can prepare or compress this packet before a cloud call.

This is one of the main mechanisms by which the system should reduce API token use.

---

# 20. Phase 15: Cloud Escalation and Cost Governor

The entity should understand compute as a limited resource.

## Budget controls

Add configuration such as:

```yaml
cognition:
  local_first: true

  cloud:
    enabled: true
    daily_budget_usd: 1.00
    monthly_budget_usd: 20.00
    max_single_call_usd: 0.25

  escalation:
    on_local_failure: true
    on_high_uncertainty: true
    allow_user_force: true
```

Numbers above are examples only.

## Model classes

The router should classify models by capability and cost rather than hardcoding one eternal provider.

Example:

```yaml
models:
  reflex:
    provider: local
    model: ...

  economical:
    provider: openrouter
    model: ...

  deep:
    provider: openrouter
    model: ...

  coding:
    provider: ...
    model: ...
```

If actual cloud usage proves tiny, OpenRouter pay-as-you-go may be economically preferable to a dedicated subscription.

The telemetry will decide.

---

# 21. Phase 16: Self-Health and Recovery

A continuously running entity needs boring infrastructure. Boring infrastructure is glorious when it prevents a 3:00 AM digital faceplant.

## Required health checks

- Hermes gateway;
- Verðandi bus;
- local inference server;
- GPU availability;
- memory databases;
- disk space;
- network;
- backup age;
- cloud provider reachability;
- Kista access;
- WYRD state;
- cron heartbeat.

## Recovery

Use systemd on Linux for long-running services.

Examples:

```text
hermes-gateway.service
verdandi.service
local-inference.service
volmarr-memory.service
```

Each service should:

- restart on failure;
- have bounded restart loops;
- write structured logs;
- expose health status;
- never silently destroy state.

Verðandi should record:

```text
BODY_OFFLINE
BODY_RESUMED
SERVICE_FAILED
SERVICE_RECOVERED
MODEL_CHANGED
HOST_MIGRATED
MEMORY_RESTORED
```

---

# 22. Phase 17: Persistent Backup and Google Drive Continuity Vault

Google Drive should be **backup storage**, never the live database.

## Live storage

```text
local SSD
├── SQLite
├── MemPalace
├── OpenViking
├── WYRD
├── affective state
├── entity identity
└── Verðandi logs
```

## Snapshot pipeline

```text
live database
    ↓
database-safe snapshot
    ↓
snapshot manifest
    ↓
compression
    ↓
local encryption
    ↓
rclone crypt
    ↓
Google Drive
```

## Suggested retention

```text
frequent incremental/current snapshots
6-hour state snapshots
daily full state
weekly checkpoints
monthly archival checkpoints
```

Do not simply overwrite one backup forever. Corruption can be synchronized too.

## Continuity manifest

Every backup should record:

```json
{
  "entity_id": "...",
  "timestamp": "...",
  "hermes_upstream_commit": "...",
  "volmarr_commit": "...",
  "memory_schema": "...",
  "wyrd_schema": "...",
  "affect_schema": "...",
  "last_event_sequence": "...",
  "model_config": "...",
  "checksums": {}
}
```

---

# 23. Phase 18: Prove Migration Before Renting Cloud Compute

Before moving to Vast.ai or another GPU provider, prove that the entity can migrate between directories or machines.

## Migration test

1. Stop runtime cleanly.
2. Create final snapshot.
3. Copy runtime code to a second environment.
4. Restore persistent state.
5. Reconnect Kista/provider secrets.
6. Start local inference.
7. Start Hermes.
8. Verify identity hash.
9. Verify memory databases.
10. Verify WYRD.
11. Verify last Verðandi sequence.
12. Verify unfinished tasks.
13. Resume.

Success means:

> The same entity state survives a new machine.

Only after this test should the first cloud migration happen.

---

# 24. Phase 19: Cloud Host Migration

When the architecture is stable, the local gaming laptop becomes the development body and the cloud host becomes the persistent remote body.

Provider should be chosen based on conditions **at the time of migration**, not hardcoded into the project today.

Requirements:

- Ubuntu Linux;
- NVIDIA GPU;
- enough VRAM for the chosen reflex model;
- persistent SSD/storage;
- high uptime;
- SSH/root control;
- predictable bandwidth;
- acceptable monthly cost;
- long instance lifetime;
- easy restoration.

The architecture should make this migration unremarkable:

```text
Laptop
  ↓ snapshot
Cloud VM
  ↓ restore
Same entity state
```

---

# 25. Integration Matrix

| Project/System | Role in Personal Hermes | Integration Type | Priority |
|---|---|---|---|
| Official Hermes Agent | Core agent shell | Upstream base | Essential |
| Existing personal affective nervous system | Regulatory continuity | Refactor into `volmarr/affect` + hooks | Essential |
| Existing Present-State Memory | Immediate current facts | Memory/context component | Essential |
| Verðandi | Real-time nervous system | Hook/event bridge | Essential |
| Project A.E.S.I.R. | Future preferred local inference engine | Local OpenAI/Ollama-compatible backend | High |
| MindSpark ThoughtForge | Small-model cognition techniques | Local reflex-layer logic | High |
| Bifröst | Federated memory bridge | Custom Hermes MemoryProvider backend | Essential |
| MemPalace | Verbatim episodic memory | Bifröst backend | High |
| OpenViking | Structured context DB | Bifröst/backend or official Hermes plugin | High |
| ChatIndex | Hierarchical long-conversation retrieval | Optional memory index | Medium |
| ChatMemory | Summary/diary memory experiments | Optional memory backend | Medium |
| TencentDB Agent Memory | CodeGraph/Wiki/skills | Later optional knowledge service | Low/Medium |
| WYRD Protocol | Deterministic world state | Tool/service + Verðandi | Essential |
| Kista | Encrypted secrets | Hermes Secret Source plugin | Essential |
| Runa Agent Digital Being | Design blueprint | Selective concept/code port | High |
| Viking Girlfriend Skill | PAD emotion/lifecycle/trust/dream concepts | Selective component port | High |
| WaifuOS | Daily life/multi-surface companion concepts | Selective component port | Medium |
| Astrology Engine | Astrology | Hermes skill/tool | High |
| RuneTarotEngine | Tarot | Hermes skill/tool | High |
| Seiðr Engine | Old Norse poetry | Hermes skill/tool | High |
| NorseSagaEngine | Viking RPG mechanics | Selective open-licensed tools | Medium |
| dnd-5e-srd | SRD mechanics/data | Selective licensed resource | Medium |
| Hamr | Headless VRM avatar creation | MCP/CLI skill | High |
| Seiðr-Smiðja | Avatar design + VRoid/Blender agent forge | MCP/CLI/REST | High |
| AIAvatarKit | Realtime voice/avatar bridge | Service/WebSocket | Medium |
| H.E.R.E.T.I.C. | Sensory/tool body | MCP service | Medium |
| OmniVoice | Advanced local TTS | Optional voice backend | Medium |
| Open-LLM-VTuber | Realtime avatar/voice/vision ideas | Optional frontend/components | Medium |
| Heimdall SL Hermes Agent | Second Life embodiment | Optional body adapter | Later |
| Cortex | Local model/memory/UI ideas | Component reference | Later |
| PageIndex/pageindex-mcp | Long-document retrieval | MCP/tool | Medium |
| Mythic Engineering | Development discipline | Process/docs | Ongoing |

---

# 26. Avoid the Giant-Spaghetti-Fork Trap

A few things should **not** be done.

## Do not merge every repository wholesale

Most projects should remain independent packages/services and be accessed through:

- Hermes tools;
- plugins;
- MCP;
- REST;
- CLI;
- Python APIs.

## Do not make every system write every memory

Use explicit memory ownership.

## Do not let every subsystem inject prompt text

All context must pass through a central context-packet builder with budgets.

## Do not let cloud inference become the hidden default

Local-first routing should be measurable and enforceable.

## Do not store live databases in Google Drive-mounted folders

Snapshot first, upload second.

## Do not expose secrets to the LLM when a tool can use them directly

Capabilities beat raw credentials.

## Do not hardwire the entity to the laptop

The laptop is the first body, not the definition of identity.

---

# 27. Testing Strategy

## Upstream compatibility

Run the relevant Hermes test suite after every upstream intake.

## Volmarr contract tests

Create tests for architectural invariants:

```text
test_verdandi_failure_does_not_break_hermes
test_memory_provider_failure_falls_back_cleanly
test_local_model_failure_can_escalate
test_cloud_disabled_stays_local
test_budget_blocks_expensive_escalation
test_secrets_never_enter_memory
test_secrets_never_enter_event_log
test_memory_packet_respects_token_budget
test_wyrd_world_state_is_not_written_as_episodic_memory
test_affective_state_survives_restart
test_identity_survives_model_change
test_restore_preserves_entity_uuid
test_backup_can_be_restored
```

## Chaos tests

Deliberately:

- kill Verðandi;
- kill local inference;
- disconnect Internet;
- corrupt a disposable memory snapshot;
- fill a test disk partition;
- make cloud provider return 429/500;
- restart Hermes mid-task.

The system should degrade gracefully.

---

# 28. Observability Dashboard

Eventually add:

```text
hermes entity status
```

Output concept:

```text
Entity: <name>
Uptime: 3d 14h
Current state: ACTIVE
Local reflex model: healthy
Cloud provider: reachable

Cognition today
  deterministic events: 2,918
  local LLM calls:       844
  cloud escalations:      17
  cloud dependency:      0.45%

Memory
  present facts:          31
  episodic memories:   8,421
  structured resources:  612
  last consolidation:   42m

Continuity
  last snapshot:         18m
  last offsite backup:   2h
  backup verification:   OK

World model: healthy
Verðandi: healthy
Kista: healthy
```

This is how the architecture proves whether its central hypothesis is working.

---

# 29. Recommended Build Order

## Milestone 0: Clean Foundation

- freeze legacy fork;
- create fresh branch from current Hermes;
- establish custom folder/plugin layout;
- create upstream sync process;
- transplant only existing Present State and affective tests first.

**Done when:** current upstream Hermes works with zero custom behavior regressions.

## Milestone 1: Nervous System

- integrate Verðandi bridge;
- publish lifecycle events;
- add health checks;
- no LLM involved yet.

**Done when:** CLI, gateway, cron, and tools emit coherent live events.

**Implementation status:** complete in the opt-in `volmarr-core` plugin. Lifecycle metadata is
published through stable Hermes hooks, and `hermes volmarr health` verifies the configured hub with
a protocol-level `ping`/`pong`. The current Verðandi transport remains Unix-only; native Windows
reports `unsupported` without affecting Hermes execution.

## Milestone 2: Local Reflex Cognition

- attach local inference endpoint;
- build routing API;
- add local/cloud telemetry;
- add manual forced-local and forced-deep modes.

**Done when:** routine test conversations and event classification run locally while difficult tasks can escalate.

**Implementation status:** application contract complete. A.E.S.I.R.'s authenticated,
loopback-only OpenAI-compatible text endpoint is attached through the profile-scoped
`volmarr-core` adapter. The versioned router chooses deterministic, local, or cloud capability
tiers from bounded metadata, supports truthful schema-v2 `local`/`deep` modes, and keeps v1 auto
requests compatible. Bounded routine text and event-classification work can execute locally with
content-free decision and outcome telemetry. Difficult work returns an explicit escalation
directive while actual cloud-provider resolution remains with Hermes; forced-local failures never
silently escalate. A.E.S.I.R. is not advertised as a tool-capable Hermes provider, and automatic
interception of ordinary Hermes agent turns is not claimed.

## Milestone 3: Memory Fabric

- make Bifröst the central bridge;
- attach Present State;
- attach MemPalace;
- attach OpenViking;
- preserve Hermes SessionDB;
- implement bounded context packets.

**Done when:** the entity can retrieve precise old episodes and current facts without sending huge histories to the LLM.

**Implementation status:** in progress. The first slice attaches the external Bifröst package as
the central bridge boundary and proves that its Mímir and Muninn paths follow the active Hermes
profile. Initial operation is deliberately Mímir-only: health validation opens the existing store
read-only, while Huginn, Muninn reinforcement, consolidation, decay, and Hermes provider
registration remain disabled until their own behavior contracts are implemented. Present State is
now attached through plugin hooks: bounded current facts persist per profile, enter the current user
turn without changing the cached system prompt, mirror only successful memory writes, and commit
automatic turn-derived facts only after a successful lifecycle verdict. MemPalace is attached as
the verbatim episodic store through a read-only official-v3.10.0-or-newer package,
SQLite-integrity, and drawer-collection probe. Retrieval and ingestion remain disabled pending
bounded-packet and durable-write slices. OpenViking is attached through Hermes' existing bundled
provider plus a profile-scoped, anonymous, loopback-only health attestation for the official
v0.4.21-or-newer server contract. No second provider is registered, and the attachment does not
start a server or enable retrieval and writes ahead of their policy slices. Hermes SessionDB is
now explicitly preserved as the sole canonical transcript authority through a fixed,
active-profile `state.db` audit that is read-only, performs no migration, creates no missing store,
and proves lifecycle hooks leave canonical history byte-for-byte unchanged. External memory stores
remain derived or secondary; no shadow transcript database is introduced. The bounded context
packet contract is also implemented as the single prompt-facing memory assembly point. It accepts
typed, provenance-bearing items in the planned memory sections, deterministically orders and
deduplicates them, applies per-section counts and a hard whole-packet character ceiling, escapes
fence-shaped recalled text, and injects one versioned envelope on the user side only. Present State
is the first enabled producer. Precise episodic and durable retrieval remain the next explicit
policy connections rather than being silently activated by the attachment probes.

## Milestone 4: Affective Continuity

- port current affective nervous system;
- attach Verðandi events;
- add PAD emotional layer;
- add decay/persistence;
- keep injection compact.

**Done when:** state survives restart and changes predictably from real events.

**Implementation status:** complete. The complete schema-v9 deterministic affective regulator
from the earlier personal Hermes fork is preserved in the opt-in `volmarr-core` plugin without
restoring its former core patches. Its profile-local atomic state, decay, schema upgrades, bounded
reward/accountability/safety/continuity gauges, and explicit synthetic-state safety language remain
intact. Plugin hooks stage LLM and tool outcomes and commit regulation changes only for completed,
non-failed, non-interrupted turns. Compact state enters the existing central user-side context
packet as a typed producer, never as a separate system-prompt mutation. Verðandi stimuli are
attached through the official bounded recent-event socket contract with a durable profile-local
sequence cursor.
The adapter accepts only known official source/type pairs, maps numeric metadata into bounded
regulatory events, and never stores external free text. First contact establishes a non-replaying
baseline, later polls apply unseen event sequences within the configured catch-up window, and
offline or malformed responses leave both turns and cursors untouched. Normal retries are cursor
deduplicated; a crash between the separate atomic state and cursor commits may replay the final
bounded batch rather than lose it. The orthogonal PAD layer now persists bounded valence, energy,
and agency coordinates, decays them toward explicit baselines, and updates them only from those
already-classified completed-turn or Verðandi events. It survives restart, follows active profiles,
recovers corrupt state, and contributes one compact, explicitly synthetic user-side packet item.

## Milestone 5: World Model

- attach WYRD;
- expose world tools;
- add relevant world context retrieval;
- publish world changes.

**Done when:** deterministic world facts survive sessions and do not depend on LLM memory.

**Implementation status:** complete. The first slice attaches the official WYRD v1 service at a
read-only, loopback-only HTTP boundary. `hermes volmarr world health` validates the current official
liveness response (and the version-bearing form in its published API guide) with bounded time and
bytes, no redirects, no proxies, and no credentials. The second slice registers explicit
`world_get` and `world_query` tools. They read the official world/facts routes or request Passive
Oracle context with `use_turn_loop:false`, so WYRD performs no LLM generation,
conversation-history update, or memory writeback. The third slice adds
profile-opt-in relevant retrieval: a configured persona's Passive Oracle render is bounded and
submitted as one typed `WORLD STATE` item to the existing user-side context packet. It remains
disabled by default, uses no writeback or WYRD turn loop, escapes untrusted fences centrally, and
does not alter the cached system prompt. The fourth slice adds the two official WYRD v1 mutations:
canonical facts through `world_set` and
observations through `world_observe`. Writes require explicit WYRD acknowledgement; only then does
the plugin emit a versioned, content-free Verðandi signal. Entity IDs, fact keys/values, titles,
and summaries are excluded from the signal. The official API has no move or history route, so this
integration does not invent one. The final acceptance verifier passed against official WYRD v1.0.0
commit `9884ce8a9e683dc20f372a91eb66ba5b02561300`: a unique canonical fact written to a disposable
SQLite store was recovered exactly once after the bridge was destroyed and reconstructed. World
truth therefore survives restart independently of Hermes conversation memory.

## Milestone 6: Entity Lifecycle

- identity package;
- relationships;
- goals;
- heartbeat;
- background routines;
- sleep/consolidation.

**Done when:** restart resumes state, tasks, and identity cleanly.

**Implementation status:** complete. The identity package creates one versioned,
profile-local `entity/entity.yaml` record with a stable UUID and creation time. It is independent
of session, model, and provider selection, while Hermes `SOUL.md` remains the untouched
human-authored persona surface. Existing valid identities are never normalized or rewritten;
malformed or unsupported records fail visibly through `hermes volmarr identity health` and are
not silently replaced. A second versioned ledger at `entity/relationships.yaml` now preserves
explicit relationship state and bounded per-relationship history under the stable identity.
Read/update tools require deliberate calls; ordinary conversation is not mined and relationship
data is not automatically injected into prompts. A third identity-owned ledger at
`entity/goals.yaml` now persists explicitly created tasks with priority, next action, lifecycle
status, completion time, and bounded transition history. Goal tools create, advance, filter,
complete, and archive this state without mining conversation or deleting continuity. The heartbeat
receipt is now implemented in `entity/continuity.json`: explicit tool or CLI pulses advance a durable
sequence, report freshness/staleness, recognize a post-stale resume, and emit content-free
Verðandi metadata. It deliberately starts no scheduler; Hermes cron remains the cadence owner for
the next slice. The first background routine is now implemented as an explicit, idempotent,
paused-by-default Hermes cron installation. Its no-agent ten-minute run records the pulse and
publishes only aggregate pending-goal counts; it adds no scheduler or model call. Sleep and
consolidation now produce a non-destructive, versioned checkpoint over validated identity,
relationship, goal, and heartbeat state. The checkpoint records only counts and component digests;
it never rewrites the source ledgers or memory/world stores. Its optional daily no-agent Hermes
cron job is also explicit, idempotent, and paused by default. Restart tests recover the same owner,
task state, relationship history, heartbeat sequence, and consolidation sequence, satisfying this
milestone's continuity condition.

## Milestone 7: Secrets and Security

- Kista Secret Source plugin;
- redaction;
- canary-leak tests;
- permissions.

**Done when:** API keys can be used without being exposed to prompts or logs.

**Progress:** Slice 28 attaches official Kista v2.0.0 through a separate, opt-in Hermes Secret
Source plugin. Explicit `kista://service/field` bindings are resolved by the official CLI from a
vault forced beneath the active profile, using a minimal child environment and no shell or stdin.
The plugin has no model-callable tool, prompt contribution, event publisher, or direct environment
write; Hermes' existing orchestrator remains the sole owner of application and provenance. CLI
output is bounded and never echoed through failures. Contract tests cover real discovery,
orchestrated application, malformed responses, reference and path validation, and A→B→A profile
isolation. Milestone 7 remains open for cross-runtime redaction, canary-leak, and permission slices.

Slice 29 closes the redaction item at the shared Hermes boundary. Any value that wins Secret Source
precedence is placed into the existing bounded, memory-only exact-value redaction registry before
environment application. The registry is keyed by normalized profile home, so arbitrary
prefix-less Kista values are masked by the canonical model-egress and log redactor only for their
owning profile. Values that were skipped are not registered, and no raw value, reference, or name is
persisted by the registry. A→B→A tests prove both masking and cross-profile non-disclosure.
Slice 30 closes the canary-leak item with a real-discovery integration contract. A synthetic
prefix-less Kista value is deliberately presented to lifecycle hook arguments, terminal output,
and the logging boundary. The test proves that only a redacted result reaches SessionDB, then
reopens history and byte-scans all profile databases and SQLite sidecars. Captured Verðandi
lifecycle events, cognition telemetry, formatted logs, stdout, and stderr are also required to be
canary-free. No fake memory authority is introduced: stores that do not exist remain absent.
Slice 31 completes vault-permission enforcement. Initialized vault directories, key files, and
ciphertext must be non-linked real objects. POSIX ownership and owner-only modes are verified;
Windows uses the actual NTFS DACL in SID form and rejects grants beyond the current user,
LocalSystem, and built-in Administrators. Unverifiable or conditional permissions fail closed
before Kista executes, while the adapter remains read-only and never rewrites operator ACLs.

**Milestone 7 is complete:** Kista is attached only through the Secret Source API, applied values
join the profile-scoped exact redactor, the cross-surface canary matrix proves containment, and
vault storage must pass a native permission gate before credentials are read.

## Milestone 8: Personal Tool Suite

- astrology;
- tarot;
- Seiðr poetry;
- D&D/Saga components;
- PageIndex/document retrieval.

**Done when:** these are callable through normal Hermes tools/skills.

**Progress:** Slice 32 starts astrology with the normal Hermes tool surface. The opt-in
`volmarr-astrology` plugin exposes `astrology_lunar` through the official external Astrology Engine
at a profile-configured path. It supplies fixed argv, closed stdin, a credential-free minimal child
environment, bounded output, static failures, and A→B→A profile resolution. Calculation remains
local and distinct from LLM interpretation. The remaining astrology calculations and the other
personal tool families remain open.

Slice 33 adds `astrology_planetary_hours` with a required real calendar date and finite explicit
coordinates. This keeps the official engine on its local calculation path and makes online city
geocoding unreachable. Exact CLI construction, polar/error classification, output bounds, and
invalid-input preflight are covered without persisting or publishing location data. Natal,
transit, prediction, synastry, and astrocartography remain open.

Slice 34 adds `astrology_natal` with strict birth date, optional 24-hour time, and required finite
coordinates. The adapter never sends city, nation, or name flags, preserving a local no-geocoding
calculation path and minimizing identity data. Unknown time remains explicitly approximate.
The plugin creates no extra persistence or telemetry; normal Hermes session-history policy applies
to the tool call and result. Transit, prediction, synastry, and astrocartography remain open.

Slice 35 adds `astrology_transit` and requires an explicit sky date, eliminating the upstream
command's implicit current-time branch so results are replayable. Optional natal and UTC transit
times are validated and declared in result metadata; only date/time/coordinate flags reach the
engine. Prediction, synastry, and astrocartography remain open.

Slice 36 adds `astrology_predict` for exact aspects, stations, ingresses, and eclipses over an
explicit forward window capped at 366 days. It uses the engine's documented default planet sets
instead of exposing arbitrary list construction, and retains the local coordinate-only,
credential-free, timeout-bounded process contract. Synastry and astrocartography remain open.

Slice 37 adds anonymous `astrology_synastry` from two validated date/coordinate pairs and optional
times. Names and city/nation geocoding are structurally absent. Because the official CLI currently
gates house overlays on city fields even with coordinates present, the adapter truthfully reports
overlays as excluded instead of fabricating location labels. Astrocartography remains open.

Slice 38 adds `astrology_astrocartography` for local MC, IC, ASC, and DSC line calculations from a
validated birth date and explicit coordinates. Optional query coordinates are accepted only as a
complete pair, while names, place labels, and geocoding remain unreachable. The result declares
whether birth time and a query point were supplied and remains calculation-only under the shared
bounded subprocess contract.

**Astrology is complete:** the initial seven-tool set now covers natal, transit, lunar,
planetary-hours, prediction, anonymous synastry, and coordinate-only astrocartography. Tarot is the
next personal tool family.

Slice 39 begins Tarot with `tarot_draw`, a reproducible single-card draw against the official
RuneTarot deck. The official repository's latest `main` contains documentation and its MIT license;
the executable 78-card engine currently lives on the official `development` branch at
`5c2ed4746b1c303590bca85bb0d30a3d7b1e437b`. The adapter imports only that deck subsystem in an
isolated, credential-free child and returns card facts plus built-in Golden Dawn correspondences.
It never accepts question text, initializes the upstream AI or session layers, or creates upstream
history and exports. Multi-card spreads and structural dignity analysis remain open.

Slice 40 adds `tarot_spread` for the official Three Card, Past Life, Opening of the Key,
Relationship, Celtic Cross, Tree of Life, and Zodiac Wheel layouts. Exact layout keys replace the
upstream fuzzy matcher, and RuneTarot remains authoritative for count, ordering, position meaning,
and placement. The adapter returns positioned card/correspondence facts only; structural elemental
dignity analysis remains open.

Slice 41 adds RuneTarot's official elemental balance and adjacent-card dignity relationships to
each multi-card spread. The plugin returns the engine's structural classifications without
reimplementing their matrix or generating narrative advice.

**Tarot is complete:** deterministic single-card and fixed-layout draws, Golden Dawn card and
position correspondences, elemental balance, and dignity structure are available while all LLM
interpretation remains in normal Hermes cognition. Norse poetry is the next personal tool family.

Slice 42 begins Norse poetry with `seidr_compose` against official Seiðr Engine `main` commit
`a1999cd21bdac6c65791ff98c0f8125bff04cc69`. It exposes the four official forms, optional Nine
Worlds domain, bounded stanza count, kenning control, and structured metrical output without AI.
The child pins Python's hash seed to make the engine's unordered alliteration-group selection
replayable and rejects numeric seed zero because current upstream treats it as unseeded. Form
catalog, kenning catalog, and independent meter validation remain open.

Slice 43 adds `seidr_forms`, a read-only view of the official engine's canonical form registry with
Old Norse names, syllable ranges, and structural descriptions. Alternate spelling aliases are
collapsed according to the form objects' own canonical names. Kenning catalog and independent
meter validation remain open.

Slice 44 adds `seidr_kennings`, a complete read-only projection of the official Lexicon's bases,
expressions, component words, domains, and computed syllable counts. No vocabulary is copied or
extended in Hermes, and the catalog is deliberately unpaginated. Independent meter validation
remains open.

Slice 45 adds `seidr_validate_meter`, which converts bounded input lines into official `Line`
objects using the engine's syllable counter and alliteration classifier before invoking the
selected form's own stanza validator. Results expose the per-line evidence and are described as
structural engine validation, not a broader claim of philological correctness.

**Norse poetry is complete:** deterministic composition, canonical form discovery, complete
kenning discovery, and independent structural meter validation now use the official Seiðr Engine.
D&D / Norse Saga mechanics are the next personal tool family.

Slice 46 begins reusable RPG mechanics with `dice_roll`: bounded structured dice, an optional flat
modifier, and a required replay seed. Every die and arithmetic step is returned, while campaign
state, narration, characters, and rules data remain outside the plugin. Ability checks are next.

Slice 47 adds `rpg_skill_check`, grounded in official SRD fork commit
`2e62e0413061c2443e21369cdc074c7a7356a857`: one d20 plus a total modifier compared against a DC,
with explicit normal/advantage/disadvantage selection. Natural 1 and 20 are truthfully not treated
as automatic outcomes for ordinary ability checks.

Slice 48 adds `rpg_oracle`, an original replayable percentile oracle with disclosed likelihood
thresholds. Chaos changes only the exceptional-result band, not the yes probability, and the tool
accepts no question or campaign state. No Mythic GME table or NorseSagaEngine source is copied.

Slice 49 adds `rpg_random_table`, selecting one short entry from a bounded caller-owned table with
an explicit seed and auditable dN-style roll. The plugin bundles no setting or rules tables and
persists none of the supplied content.

Slice 50 adds `rpg_condition_lookup`, resolving the active profile's configured external SRD
checkout at call time and returning one bounded condition definition with its OGL 1.0a provenance.
No SRD rules prose is copied into Hermes.

Slice 51 adds `rpg_random_character` as an ability-only skeleton: six fixed named scores generated
by seeded 4d6-drop-lowest, with every die, dropped die, score, and modifier exposed. It deliberately
generates no identity, ancestry, class, personality, equipment, or narrative.

Slice 52 adds `rpg_encounter_initiative`, a bounded seeded d20 ordering primitive over opaque
participant identifiers and total modifiers. Every roll, sum, position, and deterministic tie
breaker is visible; no combatant state or narration is retained.

Slice 53 adds `rpg_hit_points`, applying one bounded damage or healing transition with SRD-style
temporary-hit-point precedence and healing caps. It returns all before/after arithmetic while
leaving death, stability, resistance, and narrative consequences explicitly unresolved. The
minimal RPG mechanics family is complete; broader campaign utilities remain deferred until a
separate state-ownership design is approved.

Slice 54 begins Embodiment with `hamr_spec_validate`, a read-only adapter over the official Hamr
`Spec.from_yaml` interface at `Development` commit
`db90f4657c2725d0b6432651d1400f1a05f77b7d`. It validates one traversal-safe YAML path beneath an
active-profile spec root in a credential-scrubbed subprocess without launching Blender or creating
an avatar.

Slice 55 adds `hamr_presets`, reading Hamr's official body proportions and compact character preset
metadata without copying full preset specs into Hermes. It remains read-only and Blender-free.

Slice 56 adds `hamr_budget_check`, exposing Hamr's own pure-Python estimates, official tier limits,
warnings, and verdict for one validated spec. It remains read-only and Blender-free. Existing
VRM/GLB compliance inspection is next.

Slice 57 audits and exposes Hamr's current `builder.inspect` as `hamr_artifact_probe`. Because the
verified upstream implementation returns only existence, size, targets, and an empty checks list,
the adapter explicitly reports metadata-only scope and no compliance performed. Actual Hamr build
authority remains deferred; Seiðr-Smiðja interface audit is next.

Slice 58 adds `smidja_spec_validate`, a read-only adapter over the official Seiðr-Smiðja Loom at
`development` commit `482c8f0032b28c4ceb323478e7854adae3715f72`. It performs bounded schema
validation without forge, Blender, REST, MCP, or remote VRoid authority. The upstream root license
and package metadata disagree (Apache-2.0 versus MIT), so no source is copied and the conflict is
reported explicitly. Read-only Hoard asset discovery is next.

Slice 59 adds `smidja_assets` over the official Hoard's public `list_assets` contract. It returns a
bounded, filterable metadata catalog while refusing asset resolution, fetch, bootstrap, filesystem
path disclosure, and all forge authority. Engine settings remain call-time profile scoped with
A→B→A verification. Read-only Gate rule discovery is next.

## Milestone 9: Embodiment

- Hamr;
- Seiðr-Smiðja;
- voice;
- AIAvatarKit or chosen realtime avatar shell.

**Done when:** the same entity can control an avatar without forking its mind/state.

## Milestone 10: Continuity Vault

- safe snapshots;
- rclone crypt;
- Google Drive backup;
- restore drills.

**Done when:** a destroyed test runtime can be rebuilt from backup.

## Milestone 11: Migration

- restore onto second computer/test VM;
- later restore onto chosen persistent GPU cloud provider.

**Done when:** host migration changes hardware but does not reset identity/history.

---

# 30. Upstream Update Policy

The personal fork should continue taking official Hermes updates when useful.

Process:

```text
fetch upstream
    ↓
read upstream changelog/diff
    ↓
create integration/upstream-DATE
    ↓
merge/rebase upstream
    ↓
resolve only real conflicts
    ↓
run Hermes tests
    ↓
run Volmarr contract tests
    ↓
run local smoke test
    ↓
merge into personal main
```

Prioritize importing:

- security fixes;
- provider compatibility fixes;
- gateway improvements;
- tool improvements;
- memory framework improvements;
- plugin APIs;
- bug fixes;
- useful UI improvements.

Do not automatically accept upstream architectural changes that would break the personal entity architecture without providing meaningful benefit.

---

# 31. License and Attribution Strategy

The safest rule is:

> **Do not flatten every imported project into one claimed license. Preserve the license that applies to each component.**

The official Hermes Agent code is MIT-licensed at the snapshot reviewed.

Some Volmarr projects are MIT. Others use CC BY 4.0 or other terms. Some imported/forked projects carry their own upstream licenses. Some experimental repositories have licenses that are not yet finalized.

Create:

```text
COMPONENT_LICENSES.md
THIRD_PARTY_NOTICES.md
```

For every imported component record:

- repository;
- exact source commit;
- files copied or adapted;
- original author/project;
- original license;
- required attribution;
- modifications.

Where licensing is unclear, prefer integrating the project as an external CLI/MCP/service rather than copying its source into Hermes until the license is settled.

For D&D/SRD material, inspect and preserve the exact license and attribution terms of the specific SRD data being used.

---

# 32. Proposed README Philosophy

The README for the personal fork should be much simpler than the current elaborate fork README.

It should immediately tell visitors:

1. this is Volmarr's personal hack of Hermes Agent;
2. official Hermes Agent is the version most people should use;
3. upstream updates are incorporated when practical;
4. the fork contains Volmarr-specific experimental systems;
5. there is no promise of support, stability, or general-purpose usefulness;
6. upstream Hermes credit/license remains intact;
7. imported components retain their own licenses;
8. other people may inspect, fork, and reuse code as those applicable licenses permit.

A ready-to-use proposed README is included as a separate file with this roadmap.

---

# 33. Definition of Success

The project is successful when all of these statements are true:

- Hermes can remain running continuously.
- Most routine cognitive events are handled locally.
- Strong cloud inference is used only when it materially improves the result.
- Actual cloud usage and cost are measurable.
- Memory survives indefinitely and remains searchable.
- The entity has distinct present-state, episodic-memory, structured-knowledge, emotional-state, and world-state layers.
- Secrets remain private.
- Background processes do useful work without burning cloud tokens.
- The same identity can change local or cloud models.
- The same identity can move to another machine.
- The same identity can gain or change an avatar.
- The same identity can interact through CLI, messaging, voice, and eventually virtual worlds.
- Losing a GPU host does not mean losing the entity.
- A backup restore can recover the entity's state.
- Upstream Hermes improvements can still be selectively imported.

At that point the architecture is no longer:

```text
user → chatbot API
```

It is:

```text
persistent entity
    ├── identity
    ├── memory
    ├── world
    ├── affect
    ├── nervous system
    ├── tools
    ├── embodiment
    ├── local cognition
    └── optional deep cloud cognition
```

That is the system this roadmap is designed to build.
