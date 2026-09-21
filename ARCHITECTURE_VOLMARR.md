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
A→B→A profile changes. Verðandi-derived stimuli and a separate PAD layer remain later slices.

## Verification Standard

- Run tests through `scripts/run_tests.sh`.
- Exercise plugins through real discovery against a temporary `HERMES_HOME`.
- Preserve prompt-cache stability and profile scope.
- Keep upstream Hermes behavior unchanged when the personal plugin is disabled.
- Add behavior-contract tests, not source-shape or catalog-count snapshots.
