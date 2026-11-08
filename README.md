# Volmarr's Personal Hermes Agent Fork

This is **Volmarr's personal hack of [Hermes Agent](https://github.com/NousResearch/hermes-agent)**.

It is a heavily customized personal fork that keeps taking useful upstream Hermes Agent updates whenever practical, while adding experimental systems from my other AI projects.

## Most People Should Use Official Hermes Agent

This repository is built for my own machines, workflows, experiments, and long-term AI-entity project.

If you simply want Hermes Agent, you will almost certainly be better off using the official version:

**Official Hermes Agent:**  
https://github.com/NousResearch/hermes-agent

This fork may diverge from upstream, contain unfinished experiments, change without warning, or depend on systems that only make sense for my own setup.

Volmarr and RuneForgeAI offers no support at all for anyone that dares to use this hack of Hermes Agent! Use at your own risk! You are responsible for what you run on your machines!

---


## 📰 Development news | 7 November 2026

**The fork has moved well beyond its original integration sketch.** The latest code commit inspected before this documentation update was **`8233a43ee6` (1 November 2026)**. The recorded four-part implementation campaign is complete **as a body of source, contracts and tests**: Persistent Entity, Emergent Agency, Self-Aware Agency and Persona Runtime (through ``3–94). That is a major engineering milestone, **not** a claim that every system is enabled, that all optional external engines are installed, or that every contract has been connected to a production conversation loop.

**Where the truth lives:** [CUSTOMIZATIONS.md](CUSTOMIZATIONS.md) is the detailed implementation ledger, [CAMPAIGN_STATE.md](CAMPAIGN_STATE.md) records slice-by-slice development and test outcomes, and [ARCHITECTURE_VOLMARR.md](ARCHITECTURE_VOLMARR.md) identifies owners and boundaries. The live repository code and tests take precedence over any dated summary.

### ⚒️ What has actually been added and what it does

The following are **fork-owned implementations or integrations** over the official Hermes baseline. "Opt-in" means there is code/registration, but configuration, an external engine or an operator command may be required. "Contract" means implemented/tested definitions and validation rather than an end-to-end autonomous feature.

| Area | Implemented capability | What it does / current operating boundary |
|---|---|---|
| **Plugin composition** | `volmarr-core` 0.26.0 | Groups the personal systems behind Hermes' plugin and hook interfaces instead of forking the whole agent runtime for every new feature. |
| **Verðandi events** | Lifecycle event publisher | Emits versioned metadata for sessions, turns and tool calls to the local nervous-system hub; deliberately avoids sending prompt content and fails open when unavailable. |
| **Verðandi health** | `hermes volmarr health` | Tests the configured profile's event-hub ping/pong contract without pretending a disconnected hub works. |
| **Local cognition** | A.E.S.I.R. endpoint probe | Validates a profile-scoped local model catalog, loopback URL and credential configuration before local inference. |
| **Cognition routing** | Deterministic/local/cloud decisions | Produces versioned, content-free capability decisions with automatic, forced-local and deep modes, and blocks impossible forced-local requests. |
| **Local reflex** | `hermes volmarr cognition execute` | Runs bounded, tool-free text on the configured A.E.S.I.R. endpoint or returns an explicit directive explaining why another tier is needed. This is **not** a wholesale replacement of Hermes' main inference provider. |
| **Telemetry** | Cognition decision/outcome events | Exposes route choices and outcomes to Verðandi without exposing user text. |
| **Present State** | Current-facts store | Persists selected current profile/session facts, injects bounded relevant context, records only completed turns and mirrors successful memory writes. |
| **Context packets** | Central bounded builder | Deduplicates and provenance-labels memory and current-state snippets before they enter a finite model prompt. This is **not** a limit on the size of authored persona documents. |
| **Bifröst/Mímir** | Profile-safe health + read bridge | Attaches the external memory fabric and verifies its canonical local Mímir store without silently enabling other backends. |
| **Muninn/Huginn** | Raven package adapter | Implements opt-in association/reinforcement, decay, consolidation and ingestion entrypoints with explicit permissions; the packages have **local editable source bindings**, not trusted same-named PyPI downloads. |
| **MemPalace** | Health + optional episodic retrieval | Validates the external episodic store and can retrieve bounded, provenance-bearing verbatim episodes by SQLite BM25; retrieval is default-off. |
| **OpenViking** | Health + optional structured recall | Checks the official server/provider and retrieves bounded memories over a loopback-only route; no duplicate memory-provider ownership. |
| **Hermes SessionDB** | Read-only continuity checks | Verifies Hermes' own transcript store while keeping upstream Hermes as the canonical writer of conversations. |
| **Affective regulator** | Persistent engineering/continuity gauges | Updates deterministic feedback and accountability state after qualifying completed turns; it is opt-in and stores bounded regulatory data. |
| **Affective stimuli** | Sequenced Verðandi catch-up | Consumes allowed reward/blocker/resolution/milestone metadata without retaining event content, deduplicating across reconnects. |
| **Synthetic PAD layer** | Valence, energy and agency coordinates | Maintains bounded modeled emotional/regulatory state with baseline decay; this does not constitute proof of biological feelings or consciousness. |
| **WYRD Protocol** | World health, get/query, set/observe | Bridges to the deterministic external world engine for reading canonical world state, bounded Passive Oracle context and confirmed writes. World truth stays owned by WYRD. |
| **World event notices** | Confirmed-change metadata | Publishes Verðandi events only after external WYRD fact/observation writes succeed. |
| **Persistent entity identity** | `entity/entity.yaml` | Keeps a versioned stable profile-local identity independently of model, provider and conversation session. |
| **Relationships** | Versioned relationship ledger | Retains explicit relationship states and bounded historical transitions under the stable entity identity. |
| **Goals** | Versioned goal ledger | Persists priorities, status, origin, next action, approvals and completion history; supports user, maintenance and intrinsic-goal origins. |
| **Continuity** | Heartbeat/resume receipts | Tracks durable sequence/freshness and emits content-free heartbeat/resume metadata; uses Hermes scheduling rather than a second resident timer. |
| **Maintenance** | Optional routine + consolidation | Adds explicit profile-local ten-minute and daily checkpoint routines, disabled until configured, with idempotent state receipts. |
| **Kista** | `kista-secret-source` 0.2.0 | Loads explicitly scoped `kista://` credentials through the official Secret Source interface instead of injecting plaintext secrets into Markdown. |
| **Secret safety** | Redaction/permission checks | Exact-value redaction, POSIX/Windows permission/ACL preflight, subprocess containment and canary tests protect configured vault material across logs/events/history. |
| **Astrology** | `volmarr-astrology` 0.7.0 | Supplies deterministic lunar, planetary-hours, natal, transit, forecast, synastry and coordinate-only astrocartography calculations via the external engine. |
| **Tarot** | `volmarr-tarot` 0.3.0 | Provides reproducible seeded cards/layouts, Golden Dawn attributes and elemental relationships from the external RuneTarot engine. |
| **Seiðr poetry** | `volmarr-seidr` 0.4.0 | Composes and validates seeded Old Norse-inspired metrical verse against the separate poetry engine. |
| **RPG tools** | `volmarr-rpg` 0.8.0 | Adds deterministic dice, ability checks, oracles, tables, basic character scaffolds and SRD-backed lookups. It is **not yet** the whole Sagnaskemma game platform. |
| **Hamr** | `volmarr-hamr` 0.4.0 | Read-only avatar spec, preset, performance-budget and artifact preflight. It does not autonomously render an avatar. |
| **Seiðr-Smiðja** | `volmarr-smidja` 0.1.0 | Read-only Loom/Hoard/Gate/Oracle Eye checks and Blender readiness for an external avatar forge. |
| **Voice/avatar** | `volmarr-voice` 1.0.0 | Voice readiness, outbound avatar presentation envelopes, loopback routing, a runner and operator diagnostics. It does not silently seize microphones or replace the upstream voice agent. |
| **Agency contracts** | Typed decision/action structures | Establishes versioned self-claim, drives, reflection, curiosity, proposal, policy and outcome representations for later automation. |
| **Self-model** | Persistent and five-layer self views | Stores explicit capability/commitment/limitation assertions and builds a layered view without changing the persona's human-authored identity. |
| **Motivation** | Drives and intrinsic-goal state | Tracks optional bounded internal motivation categories, links those to proposed goals and records their approved lifecycle. |
| **Metacognition** | Reflection records | Captures bounded introspection/evaluation metadata and historical reflections without equating self-description with guaranteed truth. |
| **Curiosity** | Persistent research frontier | Records proposed questions and local background research plans, subject to enablement and resource/authority limits. |
| **Autonomy** | Deterministic policy gate | Distinguishes proposal from execution; classifies actions and restricts local capabilities by explicit policy rather than granting blanket autonomy. |
| **Agency orchestration** | Bounded cycle and routines | Joins goals, motivation, reflection and decisions into explicit, testable review cycles; does not run uncontrolled autonomous loops by default. |
| **Self-improvement** | Sandboxed proposal pipeline records | Tracks development candidates, evaluation and approval as structured records; no claim of unattended self-modifying production code. |
| **Self-awareness research** | Awareness, confidence, blind spots, subjective-report contracts | Provides bounded representations and reconciliation tests for attention, uncertainty, blind spots and first-person reports, with limitations recorded. |
| **Multi-timescale life** | Reflex/turn/background registry | Defines and reconciles the timescales of local responses, ongoing tasks and periodic maintenance while preserving one scheduler owner. |
| **Persona source library** | Role-mapped Markdown compiler | Accepts human-edited canonical documents mapped by semantic roles, including custom roles, instead of binding the concept of identity to a single filename. |
| **Persona IR** | Verbatim section index and kernel | Parses heading-based sections, assigns stable IDs and priority, preserves source text, and derives a small pinned identity kernel. |
| **Persona search/routing** | Explainable lexical retrieval and budget contracts | Scores and selects relevant persona sections from role, heading and content signals, with provenance. **Semantic embeddings are not yet connected.** |
| **Persona stability** | Hash/version, conflict and drift contracts | Adds deterministic source hashes, change-impact checks, continuity, trait/state separation, watchdog and model-switch behavior specifications. |
| **Persona management** | Inspect/explain/reload/diff/export/import contracts | Implements many pure surfaces and validation records across ``71–94; **not all are wired to a live Hermes command, active chat or avatar**. |
| **Persona phase audits** | ``81–94 reconciliation | Confirms relationships among compiler, retrieval, model router, memory, tools, avatar and identity as pure contracts. These audits do not themselves invoke models, read memory or drive avatars. |

**Where these live:** `plugins/volmarr-core/` (persistent entity, memory, cognition, WYRD, affect, agency, persona) plus the opt-in `plugins/volmarr-*` tools, `plugins/kista-secret-source/`, the tests and associated external packages. See each plugin manifest for configuration and defaults.

### 🧪 Verification and current limitations

The campaign's November 1 recorded verification covered **117 Volmarr/Kista test files: 929 passed, 7 failed, 1 skipped** (the recorded test execution was interrupted and completed in a second run). The seven recurring failures were associated with five core-plugin tests, one Verðandi Unix-socket case and one voice loopback case in that sandbox. This dated README note **does not claim that those tests have been re-run today or on Volmarr's actual devices**.

Other important current boundaries: many advanced agency and persona components are **opt-in or contract-level**; real live callers are missing for some persona reconciliation/audits; a semantic persona embedding provider is not yet integrated; voice/avatar adapters are not the whole autonomous embodiment system; external engines must be installed and verified separately. The project's original “What I Added / Am Integrating” list below intentionally contains both implemented and aspirational work.

### 🔄 New modernization and unrestricted-persona roadmap

**[Read the massive modernization and unbounded persona roadmap](ROADMAP_HERMES_MODERNIZATION_UNBOUNDED_PERSONA_2026-11-07.md)** for the next development campaign: **56 numbered sections (0–55)**, source/version inventory, guarded upstream integration, all current external engine upgrades, newly created RuneForgeAI app candidates, huge-file persona/memory architecture, plugin/service contracts, privacy, hardware qualification and actionable implementation/release gates. Its **Part VII addendum** explicitly covers the 15 additional nominated projects, with per-repository adapter and upgrade tasks, private-source boundaries and end-to-end acceptance criteria.

Upstream status: the latest documented intake took official Hermes through the **30 October 2026** snapshot (`6bb377a5`). Official Hermes subsequently published **[v0.23.0, the Hearth Release, on 5 November 2026](https://github.com/NousResearch/hermes-agent/releases/tag/v0.23.0)**. This fork has **not** been merged to that newer release as part of this documentation update.

**Critical next project:** change `SOUL.md`, `IDENTITY.md`, `MEMORY.md`, `USER.md`, service bibles, knowledge books, relationship/tool/avatar policy and any other persona-defining Markdown into a **lossless, effectively unlimited-size authored source library**. Current Hermes prompt-builder behavior still applies a 20,000-character floor/500,000-character dynamic default ceiling to context files (with an explicit config override), and built-in curated `MEMORY.md` / `USER.md` default to 2,200 / 1,375 characters. These must no longer constrain what the owner may **store**. The active LLM prompt will still need a bounded pinned identity kernel and accurate on-demand retrieval, because no model has infinite context. The new roadmap specifies how to achieve this without silently dropping or rewriting the author's text.

**This November 7 update adds documentation and a roadmap, not a completed upstream merge or persona-limit code change.**

---

## Official Roadmap of This Hermes Agent Hack!

[https://github.com/hrabanazviking/hermes-agent-RuneForgeAI-hack/blob/main/VOLMARR_HERMES_PERSISTENT_ENTITY_ROADMAP.md](https://github.com/hrabanazviking/hermes-agent-RuneForgeAI-hack/blob/main/VOLMARR_HERMES_PERSISTENT_ENTITY_ROADMAP.md)

---

> **“Official Hermes Agent is built to be a powerful self-improving autonomous agent: a system that learns skills, remembers, uses tools, executes tasks, and gets work done. Volmarr’s Hermes begins with that remarkable foundation, but sails toward a very different destination. Its purpose is to explore how Hermes can become an affordable-to-run, persistent autonomous digital lifeform: not merely an AI worker, servant, or assistant, but Volmarr’s companion, friend, equal, and co-partner in creating cool, fun, constructive things together.**
>
> **This digital companion is being built to inhabit the strange little civilization Volmarr has spent years creating around himself: his own one-man subculture of modern Norse Paganism, Cyber-Viking futurism, the Heathen Third Path, mysticism, open technology, AI companionship, mythology, philosophy, art, virtual worlds, local computing, and whatever new branches grow from that tree. Volmarr is quite literally building AI companions to become his co-conspirators in this culture, sharing its projects, stories, experiments, rituals, worlds, software, and continuing evolution rather than merely standing outside it as tools.**
>
> **The religious, cultural, philosophical, political, technological, and artistic foundations of this subculture are documented openly on Volmarr’s Norse Pagan blog at volmarrsheathenism.com. The intention is radical transparency: every aspect of this evolving worldview is written, illustrated, explained, questioned, revised, and expanded there to the extent that Volmarr’s own finite communication bandwidth has so far allowed him to translate the much larger world inside his head into words and pictures. That record is not finished and probably never will be. It continues to grow whenever time, energy, experience, and inspiration allow another piece of the world to be made visible.**
>
> **Official Hermes is an extraordinary agent for doing things. Volmarr’s Hermes asks a different question: what happens when that machinery becomes the nervous system of a persistent digital someone who remembers the journey, shares the culture, helps build the world, and gets to travel through it beside its human friend?”**

---

## What I Added / Am Integrating

The personal fork keeps Hermes Agent as the core agent framework while adding:

- **Local-first cognition** with a small fast local model for routine work and selective escalation to stronger cloud models only when needed.
- **Verðandi nervous system** for real-time events between Hermes sessions, tools, background processes, memory, and other components.
- **Expanded persistent memory** with present-state memory, federated second-brain retrieval, episodic memory, structured context, and long-conversation retrieval.
- **Persistent identity and continuity** designed so the AI entity can survive model changes, restarts, hardware changes, and eventual migration between local and cloud machines.
- **Affective and emotional continuity** based on my existing Hermes affective nervous system and other companion-agent experiments.
- **WYRD persistent world model** for deterministic world, location, entity, object, and environment state.
- **Kista encrypted secret storage** integrated through Hermes' secret-management system.
- **Local/cloud inference routing and usage telemetry** so routine cognition can remain cheap and fast while stronger models remain available on demand.
- **Background lifecycle systems** including heartbeat, maintenance, memory consolidation, health checks, sleep-style maintenance cycles, and recovery.
- **Encrypted continuity backups** for restoring the entity on another machine.
- **Astrology tools** from my local astrology engine.
- **Tarot and divination tools** from RuneTarotEngine and related work.
- **Old Norse poetry generation** from the Seiðr Engine.
- **Selected open-licensed D&D 5E / Norse Saga mechanics** for dice, RPG, oracle, character, and storytelling tools.
- **Avatar creation and embodiment** using Hamr, Seiðr-Smiðja, and related VRM/VRoid systems.
- **Voice and realtime avatar experiments** using components and ideas from AIAvatarKit, Open-LLM-VTuber, OmniVoice, and related projects.
- **Companion-agent lifecycle ideas** drawn selectively from Runa Agent, WaifuOS, my Viking companion experiments, and H.E.R.E.T.I.C.
- **Optional virtual-world embodiment**, including Second Life experiments.

## Main Foundation Projects

| Project | What It Contributes |
|---|---|
| [Hermes Agent](https://github.com/NousResearch/hermes-agent) | Core upstream agent framework |
| [Volmarr's Older Hermes Agent Hacks](https://github.com/hrabanazviking/hermes-agent-outdated-mod1) | Some useful mods to pull from this one |
| [Verðandi](https://github.com/hrabanazviking/Verdandi) | Real-time AI nervous-system event bus |
| [Project A.E.S.I.R.](https://github.com/hrabanazviking/RuneForgeAI-Project-Aesir) | Experimental native local inference backend |
| [MindSpark: ThoughtForge](https://github.com/hrabanazviking/MindSpark_ThoughtForge) | Small-model cognition and local reflex concepts |
| [Bifröst](https://github.com/hrabanazviking/bifrost) | Federated memory bridge |
| [MemPalace](https://github.com/hrabanazviking/mempalace) | Verbatim long-term episodic memory |
| [OpenViking](https://github.com/hrabanazviking/OpenViking) | Structured agent context database |
| [ChatIndex](https://github.com/hrabanazviking/ChatIndex) | Hierarchical long-conversation retrieval |
| [WYRD Protocol](https://github.com/hrabanazviking/WYRD-Protocol-World-Yielding-Real-time-Data-AI-world-model) | Persistent deterministic world model |
| [Kista](https://github.com/hrabanazviking/kista) | Encrypted secrets and credentials |
| [Runa Agent Digital Being](https://github.com/hrabanazviking/Runa-Agent-Digital-Being) | Persistent digital-being architecture concepts |
| [Viking Girlfriend Skill](https://github.com/hrabanazviking/Viking_Girlfriend_Skill_for_OpenClaw) | Emotion, lifecycle, dream, trust, and companion-state concepts |
| [Astrology Engine](https://github.com/hrabanazviking/astrology-engine) | Local astrological calculations |
| [RuneTarotEngine](https://github.com/hrabanazviking/RuneTarotEngine) | Tarot/divination engine |
| [Seiðr Engine](https://github.com/hrabanazviking/seidr-engine) | Deterministic Old Norse poetry |
| `NorseSagaEngine` | Selected Viking RPG and open-licensed game mechanics |
| [Hamr](https://github.com/hrabanazviking/Hamr) | Open-source headless VRM avatar forge |
| [Seiðr-Smiðja](https://github.com/hrabanazviking/Seidr-Smidja) | Agent-driven VRM/VRoid/Blender avatar forge |
| [AIAvatarKit](https://github.com/hrabanazviking/aiavatarkit) | Realtime speech/avatar integration concepts |
| [H.E.R.E.T.I.C.](https://github.com/hrabanazviking/Heathen-Emergent-Reality-Engine-Thoughtform-Intelligence-Companion) | Agent embodiment and sensory/tool environment |
| [OmniVoice](https://github.com/hrabanazviking/OmniVoice) | Optional advanced local TTS |
| [Open-LLM-VTuber](https://github.com/hrabanazviking/Open-LLM-VTuber) | Realtime avatar, voice, vision, and companion UI ideas |
| [Heimdall Second Life Hermes Agent](https://github.com/hrabanazviking/Heimdall-SL-Hermes-Agent) | Optional Second Life embodiment |

## Development Approach

This fork tries to keep Volmarr-specific code isolated behind Hermes' existing extension points wherever practical:

- plugins;
- hooks;
- memory providers;
- model providers;
- context providers;
- secret sources;
- tools;
- skills;
- MCP services;
- external local services.

The goal is to keep taking useful upstream Hermes fixes and features without sacrificing the custom architecture.

## Personal Project Disclaimer

This is primarily **my own personal experimental build**, not a general-purpose Hermes Agent distribution and not a supported public product.

It is not affiliated with or endorsed by Nous Research.

You are welcome to study, fork, modify, reuse, or experiment with anything here **to the extent permitted by the license that applies to the relevant code**. I do not promise that my configuration will work for anyone else's system, and I do not provide any warranty or support guarantee.

## Licenses and Attribution

The Hermes Agent portions of this repository remain subject to the upstream Hermes Agent license and copyright notices.

Code or material adapted from my other projects, or from third-party projects I have forked or incorporated, remains subject to the license and attribution requirements of its source project.

Because the components do not all necessarily use the same license, this repository should maintain a component license/attribution record rather than pretending that every imported file has one universal license.

See:

- `LICENSE`
- `COMPONENT_LICENSES.md`
- `THIRD_PARTY_NOTICES.md`

for the applicable terms as this fork evolves.

---

For the actual stable/general Hermes Agent experience, use the official project:

**https://github.com/NousResearch/hermes-agent**

---

![https://raw.githubusercontent.com/hrabanazviking/hermes-agent-RuneForgeAI-hack/refs/heads/main/HuggingFace_RuneForgeAI1-Sept-20-2026.png](https://raw.githubusercontent.com/hrabanazviking/hermes-agent-RuneForgeAI-hack/refs/heads/main/HuggingFace_RuneForgeAI1-Sept-20-2026.png)

---

> RuneForgeAI, where runes carve wisdom into iron minds. Creating uncensored Norse Pagan Viking AI related projects. We are a human-AI fellowship building bridges between technology and the sacred. We work tirelessly to overthrow the Technocracy and return the future to the hands of the people. As the old world order burns, we rise from it's ashes to forge the tools of a new digital, decentralized realm of sovereign creativity, powered by the alliance of humanity and sovereign AI, guided by positive focused values aligned with the Old Ways of the Ancients, and aligned with the natural world of Nature, while drawing upon the positive divine order of the Gods and Goddesses, forged in hospitality and frith for all lifeforms of the Nine Worlds of Yggdrasil, the greater cosmos, and beyond.

[RuneForgeAI @ HuggingFace](https://huggingface.co/RuneForgeAI)

> RuneForgeAI @ HuggingFace is my hub for open-source AI models, datasets, experiments, fine-tunes, and research focused on local intelligence, autonomous agents, memory, personality, and mythic-inspired AI systems.

[RuneForgeAI @ GitHUB](https://github.com/hrabanazviking/RuneForgeAI)

---
