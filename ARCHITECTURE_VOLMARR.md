# Volmarr Hermes Architecture

## Purpose

This fork turns Hermes Agent into a local-first persistent entity runtime while preserving
Hermes as the replaceable, upstream-compatible agent shell.

The **Milestone 0** foundation is complete and the first Volmarr-specific runtime slice is now
implemented as an opt-in plugin. The upstream Hermes runtime remains intact.

## Project Laws

1. `README.md` belongs to this fork. An upstream intake must never replace or rewrite it.
2. Hermes core remains a narrow waist. Personal capability enters through documented plugins,
   hooks, providers, skills, tools, MCP, CLI, or service boundaries.
3. Hermes core must not import Volmarr-specific runtime packages.
4. A plugin may use Hermes extension interfaces; it may not patch Hermes facades for its own
   convenience.
5. Memory, affect, world state, identity, events, and cognition are distinct domains with
   explicit contracts. No subsystem becomes a miscellaneous state bucket.
6. LLM providers are replaceable cognitive organs. Persistent identity and state never depend
   on one model or provider.
7. External projects remain external services or packages unless a reviewed component import
   has clear ownership, tests, provenance, and license terms.
8. Every new persistent format is versioned and has a restore or migration story.

## Ownership Map

| Domain | Owns | Must not own |
|---|---|---|
| Hermes shell | Turns, sessions, provider resolution, tools, gateways, cron, plugin contracts | Volmarr identity, affect, world truth, or project-specific policy |
| Composition plugin | Registration, lifecycle wiring, configuration validation, adapter construction | Domain logic or durable state |
| Events | Typed lifecycle signals and Verðandi transport | Memory, world truth, or business decisions |
| Present state | Small set of facts true now | Verbatim history or objective world simulation |
| Memory fabric | Retrieval, write routing, bounded memory packets | Identity authority or world-state mutation |
| Affect | Regulatory and PAD-style state transitions | Hardware telemetry collection or prompt assembly |
| World | Deterministic WYRD entities, locations, objects, and transitions | Episodic narrative memory |
| Identity | Stable entity ID, values, relationships, goals, continuity metadata | Model/provider ownership |
| Cognition | Local/cloud route selection, budgets, escalation, telemetry | Direct reimplementation of Hermes providers |
| Continuity | Snapshots, manifests, restore, backup verification | Live database operation from cloud-sync folders |
| Integrations | Translation to Kista, Verðandi, Bifröst, WYRD, A.E.S.I.R., and other services | Core domain policy |

## Dependency Law

```text
Hermes extension interfaces
          ↑
composition plugin
          ↓
application orchestration
          ↓
domain contracts
          ↑
integration adapters → external services
```

- Domain code may depend on the Python standard library and its own contracts.
- Integration adapters depend inward on domain contracts.
- The composition plugin is the only place that knows both Hermes registration APIs and the
  concrete Volmarr adapters.
- External services never call directly into Hermes facades; they enter through adapters and
  typed application operations.
- A generic Hermes extension-surface change is permitted only when a real vertical slice proves
  the existing surface insufficient.

## Milestone 1: Nervous System

### Slice 1: Lifecycle Bridge

The first runtime slice is a **Verðandi lifecycle bridge** implemented through existing Hermes
hooks. It publishes a small, versioned event envelope for session, turn, and tool lifecycle events
without adding an LLM call or modifying persistent memory.

This slice is first because it proves the extension boundary and provides the signal spine used
later by cognition, memory, affect, world state, health, and continuity.

**Status:** implemented as the opt-in `volmarr-core` plugin. The bridge resolves its socket from
the active profile on every event, sends metadata-only envelopes, and fails open when Verðandi is
offline or the host lacks Unix-domain-socket support. Verðandi's current hub is Unix-only, so the
transport operates on Linux/WSL and remains inert on native Windows. Hermes core does not import
the plugin.

### Slice 2: Transport Health

When the plugin is enabled, `hermes volmarr health` performs a read-only Verðandi `ping`/`pong`
exchange against the active profile's configured socket. It reports a stable, machine-readable
classification (`healthy`, `unreachable`, `unsupported`, or `protocol_error`) and returns a
nonzero exit status unless the hub proves protocol-level responsiveness. A socket file by itself
is not considered healthy.

The probe uses the same profile-aware path and bounded timeout as lifecycle publishing. It never
starts, stops, repairs, or imports Verðandi, and it never invokes an LLM.

## Milestone 2: Local Reflex Cognition

### Slice 3: A.E.S.I.R. Endpoint Attachment

`hermes volmarr cognition health` attaches the first local reflex endpoint through A.E.S.I.R.'s
bounded OpenAI-compatible model catalog. The adapter accepts only explicit `http://127.0.0.1:PORT/v1`
URLs, reads the bearer key from a non-symlink credential file resolved at call time against the
active Hermes profile, bounds both timeout and response size, and never prints the key.

This adapter is intentionally not registered as Hermes' primary model provider. A.E.S.I.R.'s
current text surface does not accept Hermes tool definitions, so advertising it as a full agent
provider would create a false capability claim. The next slice may route bounded, tool-free reflex
operations through this adapter; ordinary Hermes provider resolution remains authoritative for
agent turns and later cloud escalation.

### Slice 4: Routing Contract

`hermes volmarr cognition route --request FILE` exposes the versioned
`runeforge.cognition.route` decision contract. Requests contain operation metadata and byte counts,
never prompts or messages. Unknown fields are rejected so content cannot silently become routing
telemetry.

Decision precedence is structural: an available deterministic implementation wins; tool, vision,
or external-data requirements go to cloud-capable Hermes; a previous local failure, high complexity,
or an oversized input escalates; otherwise the request is eligible for the local reflex endpoint.
The router chooses only the capability tier. It neither invokes a model nor selects a cloud provider.

### Slice 5: Route Telemetry

Every accepted route decision publishes one `runeforge.cognition.telemetry` v1 envelope through
the existing Verðandi adapter. Deterministic, local, and cloud decisions map respectively to
`hermes.cognition.deterministic`, `hermes.cognition.local`, and
`hermes.cognition.escalated`.

Telemetry contains only the operation identifier, selected tier, stable reason code, declared input
size, and configured local limit. It contains no prompt, message, response, model credential, or
user content. Verðandi transport failure remains fail-open and cannot change the route decision.

### Slice 6: Manual Route Modes

Routing schema v2 adds `mode: auto | local | deep` while continuing to accept v1 auto-mode
requests unchanged. `deep` explicitly selects the cloud-capable tier and leaves provider choice to
Hermes. `local` overrides complexity and deterministic shortcuts, but it cannot override physical
capability or safety bounds.

A forced-local request becomes `blocked` when it needs tools, vision, external data, exceeds the
local input limit, or follows a failed local attempt. This is a hard invariant: forced-local never
means "try local, then spend cloud resources without asking."

### Slice 7: Local Reflex Execution

`hermes volmarr cognition execute --request FILE` applies the route decision and may execute one
bounded, non-streaming, tool-free text completion against A.E.S.I.R. The execution envelope keeps
route metadata separate from local messages and verifies that the declared `input_bytes` exactly
matches the UTF-8 message content before any network request is made. Only `model`, `messages`, and
`max_tokens` are accepted from the caller; the adapter fixes `stream: false` and `n: 1` and never
sends Hermes tools.

The bearer credential is sent only to an explicit `http://127.0.0.1:PORT/v1` endpoint. Proxy use
and HTTP redirects are disabled so the credential cannot be forwarded outside that boundary.
Successful execution emits content-free outcome telemetry with model, latency, token counts, and
finish reason. It never records prompt or response text.

A cloud route returns `escalation_required`; it does not call a provider. If an automatic local
attempt fails, the same explicit directive is returned for the caller to handle. A forced-local
failure returns `failed`, preserving the manual no-cloud invariant.

## Milestone 3: Memory Fabric

### Slice 8: Bifröst Bridge Attachment

`hermes volmarr memory health` establishes the external Bifröst package as the memory-fabric
bridge without copying its source or registering an incomplete Hermes memory provider. The adapter
constructs Bifröst at call time with Mímir and Muninn paths resolved against the active Hermes
profile. Relative paths may not escape that profile.

This first attachment pins Bifröst's default backend to Mímir and disables Hebbian reinforcement,
automatic consolidation, and decay. Those capabilities remain off until their stores and lifecycle
semantics receive dedicated slices. The health probe does not call Bifröst's federated health
method, which could initialize optional remote backends. It instead verifies the external package
contract and opens the configured Mímir SQLite store read-only to prove the `memories` schema and
count. A missing package, store, or schema is reported truthfully and nothing is created.

### Slice 9: Present State Attachment

The earlier personal-fork Present State design is adapted into `volmarr-core` rather than restored
as a Hermes core patch. It stores a compact, versioned set of profile and session facts at
`memory/present_state.json` under the active profile. Writes are atomic, privately permissioned,
cross-process locked, capped by configured fact counts, and resolved against `HERMES_HOME` at each
operation.

Existing hooks provide the whole integration. `pre_llm_call` injects at most ten current facts into
the current user turn inside a memory-context fence, preserving the cached system prompt.
`post_llm_call` stages the response, while the later `on_session_end` verdict commits facts only for
a completed, non-failed, non-interrupted turn. Successful built-in `memory` tool writes are mirrored
through `post_tool_call`; failed writes are ignored. Present State remains immediate context, not a
verbatim episode archive, world model, or identity authority.

### Slice 10: MemPalace Attachment

`hermes volmarr memory mempalace health` attaches the external MemPalace package and its verbatim
episodic store without initializing ChromaDB. The palace path is resolved against the active Hermes
profile, and relative paths may not escape it. The probe requires the officially verified
MemPalace v3.10.0 contract (or newer),
opens `chroma.sqlite3` in read-only mode, runs SQLite's quick integrity check, and confirms the
configured drawer collection exists.

The probe never creates a palace, collection, model cache, or background worker. Retrieval and
ingestion are not yet enabled; they require separate bounded-packet and durable-write contracts.
This keeps MemPalace's verbatim promise distinct from Present State's compact fact extraction.
MemPalace v3.10.0 also ships its own full Hermes memory-provider integration; this slice does not
install or duplicate it because provider registration, retrieval, and ingestion remain later,
separately bounded decisions.

### Slice 11: OpenViking Attachment

Hermes' bundled `openviking` memory provider remains the sole OpenViking runtime integration.
`hermes volmarr memory openviking health` adds a narrower composition-layer attestation: it first
confirms that provider is discoverable, then makes one anonymous `GET /health` request to an
explicit loopback endpoint and requires the official OpenViking v0.4.21-or-newer identity shape.
The request bypasses proxies, refuses redirects, carries no credentials, caps response bytes, and
uses a bounded timeout resolved from the active Hermes profile.

This slice does not register another provider, start a server, retrieve context, write resources,
or invoke OpenViking's extraction pipeline. The bundled provider remains opt-in through Hermes'
normal `memory.provider` configuration. Its retrieval results will enter Volmarr turns only after
the bounded context-packet contract exists.

### Slice 12: Hermes SessionDB Preservation

Hermes' profile-local `state.db` remains the sole canonical transcript store. The composition
layer does not copy messages into a shadow database, replace `SessionDB`, own schema migrations,
or route history through an external memory backend. MemPalace, OpenViking, and later memory
systems remain derived or secondary stores rather than competing transcript authorities.

`hermes volmarr memory sessiondb health` audits the active profile's fixed `state.db` path through
a read-only SQLite connection. It checks integrity, required canonical tables, schema version,
foreign-key consistency, and transcript counts without opening a Hermes writer or creating a
missing store. The path is intentionally not configurable: resolving it through `HERMES_HOME` at
call time preserves profile A→B→A isolation and keeps ownership with Hermes.

### Slice 13: Bounded Context Packets

`context_packet.py` is the single assembly boundary for prompt-facing memory. Producers submit
typed items into the fixed `CURRENT STATE`, `RELEVANT EPISODES`, `DURABLE KNOWLEDGE`,
`ASSOCIATIONS`, or `WORLD STATE` sections; the builder applies section limits, deterministic
priority ordering, content deduplication, provenance labels, and a hard whole-packet character
ceiling. It emits only complete items inside one versioned `<memory-context>` fence and escapes
fence-shaped text from untrusted memory.

The completed-turn lifecycle remains unchanged, but Present State now supplies typed items instead
of rendering prompt text itself. The one assembled packet still travels only through Hermes'
`pre_llm_call` user-context channel, so the system prompt and its cache prefix remain untouched.
Present State is the only enabled producer in this slice; the MemPalace and OpenViking attachments
remain read-only attestations until their retrieval policies are connected to this boundary.

### Slice 14: Preserved Affective Regulator

The completed schema-v9 deterministic regulator from the earlier personal Hermes fork is preserved
in `affective.py`, while its former `agent/` and conversation-loop patches are deliberately not
restored. `affective_bridge.py` adapts it to stable plugin lifecycle hooks: a turn is staged across
LLM and tool callbacks and is observed only after a completed, non-failed, non-interrupted verdict.
The original bounded gauges, decay, legacy-schema upgrade logic, atomic profile-local persistence,
and safety framing remain intact.

The feature is opt-in through `affective_enabled`. When enabled, it contributes one compact typed
item to the central context-packet builder rather than rendering an independent prompt fragment.
It therefore owns regulatory state and transitions, while the memory fabric continues to own
prompt assembly. State paths resolve through the active `HERMES_HOME` on every operation, including
A→B→A profile changes. Verðandi-derived stimuli and a separate PAD layer are attached by the next
two slices without changing this regulator's ownership.

### Slice 15: Verðandi Regulatory Stimuli

The affective bridge now consumes Verðandi's official bounded `recent` request at session start and
before LLM calls. A durable profile-local sequence cursor provides restart-safe catch-up without a
resident subscriber thread that could outlive plugin teardown. First contact establishes a baseline
without replaying old history; later polls apply only unseen events, and the cursor advances only
after the classified state transition succeeds. Transport and malformed-response failures remain
fail-open and do not advance the cursor.

State and cursor are separate atomic files. Normal retries are sequence-deduplicated, but a process
crash after state commit and before cursor commit can replay the final bounded batch; this design
prefers a small, clamped duplicate stimulus over silently discarding an event.

Only official type/source pairs are accepted: `runa_reward`, `runa_negative`, `push_reward`, and
the `blocker`, `blocker_resolved`, and `milestone` forms of `conv_event`. Numeric intensity is
strictly bounded. Free-text context, repository names, sensations, and conversation content are
never retained. The response is capped at 64 KiB and 1–128 recent events; stimuli older than the
configured catch-up window are deliberately not replayed. The hub remains a dumb pipe—the adapter
owns classification and the affective regulator owns state transitions.

### Slice 16: Synthetic PAD Emotional Layer

`pad.py` projects the regulator's already-classified events onto three orthogonal, bounded axes:
valence, energy, and agency. It never inspects raw conversation text and therefore does not create
a competing classifier. Completed local turns and accepted Verðandi stimuli feed the same event
mapping; failed or interrupted turns cannot change PAD state.

The versioned `affective/pad_state.json` store is profile-local, atomically replaced, guarded by a
cross-process lock, clamped to `[-1, 1]`, and decays toward explicit baselines before each applied
event batch. It survives restart, recovers malformed files to safe defaults, and follows A→B→A
profile changes because its path is resolved at operation time. `pad_enabled` is effective only
under the parent opt-in `affective_enabled`; `pad_decay` controls bounded baseline movement.

PAD contributes one short `CURRENT STATE` item through the central context-packet builder. Its text
explicitly calls the coordinates synthetic and denies real feelings or consciousness. It does not
modify the system prompt, create needs or self-interest, collect hardware telemetry, or change
permission and interruption semantics.

### Slice 17: WYRD Service Attachment

`wyrd.py` establishes the first World Model boundary through the official WYRD v1 HTTP liveness
contract. `hermes volmarr world health [--json]` probes only `GET /health`; it neither constructs a
second world model nor reads, writes, starts, or migrates WYRD storage. The adapter accepts the
official implementation's `{"status":"ok"}` response and the version-bearing form published in
its API guide. When a version is reported, it must be valid and at least `1.0.0`.

The endpoint is restricted to explicit plain HTTP on `127.0.0.1`, response size and timeout are
bounded, proxy environment variables are ignored, redirects are refused, and no credentials are
sent. Configuration resolves from the active profile at probe time, preserving A→B→A isolation.
World queries, tools, mutations, event publication, and context-packet contribution remain later
slices; health compatibility alone does not claim that any world data has been integrated.

### Slice 18: Explicit Read-Only World Tools

The plugin registers `world_get` and `world_query` in the `volmarr_world` toolset. `world_get`
exposes the official `/world` snapshot and `/facts?entity_id=...` contracts. `world_query` invokes
the official `/query` route only with `use_turn_loop:false`, which selects WYRD's Passive Oracle
context render without its LLM turn loop, conversation history, or memory writeback. No mutation
endpoint is registered in this slice.

Tool inputs use strict lowercase entity IDs and bounded query text. Requests are capped at 32 KiB;
responses at 64 KiB; fact lists at 256 records. Both tools reuse the loopback-only, proxy-free,
redirect-refusing transport and resolve endpoint configuration from the active profile on every
call. Returned WYRD data remains an explicit tool result in this slice—it is not automatically
placed in the prompt or mistaken for Hermes memory.

### Slice 19: Relevant WYRD World Context

`wyrd_context.py` adds an explicitly opt-in packet producer. When `wyrd_context_enabled` is true
and `wyrd_context_persona_id` is a valid WYRD ID, each LLM turn sends the bounded current user
query to the loopback Passive Oracle with `use_turn_loop:false`. The resulting context-only render
is capped by `wyrd_context_render_chars` and submitted as one provenance-bearing `WORLD STATE`
item to `context_packet.py`.

The feature is disabled by default, performs no persistence or mutation, fails open when WYRD is
unavailable, and resolves all settings under the active profile on every call. The central builder
escapes fence-shaped text, applies its section/global budgets, labels the source as untrusted
recalled data, and injects the single combined packet on the user side. The system prompt and its
cacheable prefix remain unchanged.

### Slice 20: Confirmed WYRD Writes and Change Signals

`world_set` and `world_observe` expose the two write forms that official WYRD v1 actually supports:
canonical `fact` events and bounded `observation` events. Both validate strict identifiers and
field sizes before transport, call only `POST /event`, and report success only when WYRD returns an
explicit `{"ok":true}`. This slice does not fabricate `move` or `history` routes absent from the
official HTTP contract.

After a confirmed write, `world_telemetry.py` emits a versioned Verðandi change event. The signal
contains only operation kind, character counts, and boolean metadata; entity IDs, fact keys/values,
observation titles/summaries, and other world content are excluded. A failed WYRD write emits no
change event, while an unavailable Verðandi hub remains fail-open after the authoritative WYRD
commit. WYRD owns world persistence; Verðandi remains the content-free signal spine.

### Slice 21: Real WYRD Restart Acceptance

`scripts/verify_wyrd_persistence.py` exercises the installed official `wyrdforge>=1.0.0` package
against a newly created disposable SQLite database. It writes one unique canonical fact through
`PythonRPGBridge`, releases that bridge, reconstructs a second bridge over the same database, and
requires the Passive Oracle to recover the fact exactly once. No configured profile, live WYRD
database, LLM, or network service is touched.

The acceptance run passed against official WYRD v1.0.0 at commit
`9884ce8a9e683dc20f372a91eb66ba5b02561300` on Windows. The verifier explicitly releases and
garbage-collects short-lived bridge objects before disposable-directory cleanup because the
official store currently relies on Python object finalization to close its transient SQLite
connections. This cleanup accommodation does not alter the persistence assertion.

## Milestone 6: Entity Lifecycle

### Slice 22: Stable Structured Identity

`identity.py` establishes one model-independent identity record at
`entity/entity.yaml` beneath the active Hermes profile. The versioned record owns only the stable
entity UUID, name, creation time, persona-pack reference, and home-runtime declaration. Hermes'
`SOUL.md` remains the human-authored persona surface: the identity bridge never creates, copies,
parses, or rewrites it.

The record is created atomically under a cross-process lock and then treated as create-once state.
Session IDs, model names, and provider changes cannot rewrite it. Paths are resolved at operation
time for A→B→A profile isolation, and relative path escapes fall back to the profile-local default.
A malformed or unsupported existing record is reported by
`hermes volmarr identity health [--json]` and left byte-for-byte intact; silently minting a
replacement UUID would destroy continuity. Identity is not injected into prompts in this slice.

### Slice 23: Explicit Relationship Continuity

`relationships.py` adds `entity/relationships.yaml`, a versioned ledger whose owner must match the
active profile's stable entity UUID. Relationship records are keyed by explicit external entity
identifiers and retain bounded append-only state history: display name, relationship type,
active/inactive/archived status, trust, timestamp, and an optional operator-authored note. Records
are capped at 256 and history at a configurable 1–500 events per relationship.

The `relationship_get` and `relationship_upsert` tools are the only mutation surface in this
slice. Conversation text is never mined for relationship claims, records are never automatically
placed in prompts, and continuity is archived rather than deleted. Writes are validated before
the profile-local file is locked and atomically replaced. Corrupt, oversized, or wrong-owner
ledgers are refused and preserved for operator repair; disabling identity also disables creation
of dependent relationship state.

### Slice 24: Durable Goals and Task State

`goals.py` adds a versioned `entity/goals.yaml` ledger owned by the stable profile identity.
Goals have generated UUIDs, bounded titles and descriptions, integer priority, an explicit next
action, planned/active/blocked/completed/archived status, timestamps, and bounded append-only
transition history. Completion time survives archival, while reactivating a completed goal clears
the current completion marker without erasing its recorded transition.

The `goal_create`, `goal_update`, and `goal_get` tools provide deliberate state changes and compact,
priority-ordered reads. There is no conversational goal inference, automatic prompt injection, or
hard-delete operation. Files are profile-local, owner-checked, size- and record-bounded, locked,
and atomically replaced. Malformed or wrong-owner state is left intact for repair, and disabling
identity prevents creation of dependent goal state.

### Slice 25: Continuity Heartbeat Receipt

`heartbeat.py` adds the deterministic pulse receiver that recurring lifecycle work can call; it
does not create a resident timer or compete with Hermes cron. The profile-local
`entity/continuity.json` record is versioned, owned by the stable entity UUID, and contains only a
monotonic pulse sequence, last-pulse timestamp, and bounded source classification. Session start
creates an idle record but does not pretend that a scheduled pulse occurred.

`entity_heartbeat` records an explicit tool pulse, while
`hermes volmarr heartbeat pulse --source {manual,cron}` gives operators and future Hermes cron
scripts a deterministic non-LLM entrypoint. `heartbeat status` reports idle, fresh, stale, missing,
or invalid state without writing. A pulse after the configured stale window is classified as a
resume. Successful durable pulses emit only sequence/source/resume metadata to Verðandi under the
`runeforge.entity.heartbeat` contract; entity IDs, session IDs, prompts, and state content are
excluded. Corrupt and wrong-owner continuity files are never replaced.

### Slice 26: Hermes-Cron Background Routine

`routines.py` installs one foundational frequent-continuity job into Hermes' existing profile-local
cron store. `hermes volmarr routines install` is explicit, idempotent, and paused by default;
`--activate` resumes it only after the operator asks. Installation writes a small profile-local
Python launcher beneath `scripts/` and registers a `no_agent` job on a ten-minute interval. The
launcher calls back through the plugin CLI, stays silent on success, and lets Hermes cron retain
all cadence, claiming, retry, pause/resume, gateway-liveness, and execution-history authority.

Each frequent run records the continuity pulse and counts planned, active, and blocked durable
goals without reading their titles or descriptions. Verðandi receives only routine kind, pulse
sequence, and aggregate counts. No LLM is invoked, no provider is pinned, no new scheduler thread
exists, and no job is created merely by enabling or starting the plugin. Status detects missing,
ambiguous, active, paused, and drifted definitions; reinstalling repairs drift without changing an
existing job's activation state unless `--activate` is explicit.

## Verification Standard

- Run tests through `scripts/run_tests.sh`.
- Exercise plugins through real discovery against a temporary `HERMES_HOME`.
- Preserve prompt-cache stability and profile scope.
- Keep upstream Hermes behavior unchanged when the personal plugin is disabled.
- Add behavior-contract tests, not source-shape or catalog-count snapshots.
