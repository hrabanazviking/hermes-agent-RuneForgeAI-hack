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

### Slice 27: Non-Destructive Sleep and Consolidation

`consolidation.py` closes the first Entity Lifecycle milestone with a validation checkpoint, not a
generative rewrite. `entity_sleep_cycle` and `hermes volmarr sleep run` read and validate the
stable identity, relationship ledger, goal ledger, and heartbeat state, then atomically write a
versioned `entity/consolidation.json`. The checkpoint contains a monotonic sequence, timestamp,
source class, aggregate counts, and SHA-256 digests of canonical component state. It is an audit
manifest, not a backup, memory store, or authority over its source domains.

The cycle never edits identity, relationships, goals, continuity, Hermes transcripts, MemPalace,
OpenViking, or WYRD. Corrupt or wrong-owner source/checkpoint state stops the cycle without
replacement. Verðandi receives only sequence, source, and aggregate counts. An optional daily
no-agent job is installed through `hermes volmarr sleep install`; like the frequent routine, it is
idempotent, profile-local, and paused unless `--activate` is explicit. Restart tests prove that the
identity, relationship and goal ledgers, heartbeat, and consolidation sequence resume under the
same owner, while A→B→A tests prove profile isolation.

## Milestone 7: Secrets and Security

### Slice 28: Kista Secret Source

`kista-secret-source` attaches the official Kista 2.0 CLI through Hermes' existing
`SecretSource` contract. It is a separate, opt-in general plugin because credential acquisition
is an integration boundary, not entity-domain policy and not a reason to modify Hermes core. The
source is mapped and read-only: each configured environment variable names one explicit
`kista://service/field` reference, while Hermes retains ownership of precedence, provenance,
profile secret scope, process-environment application, and startup refresh.

The adapter invokes `kista get -- <service>` without a shell or interactive stdin. Its child
receives only the secret-runner baseline plus `KISTA_DIR` and `PYTHONUTF8`; it never inherits the
post-dotenv credential environment. `KISTA_DIR` must resolve beneath the active Hermes profile and
is recomputed for every fetch, so one gateway process cannot reuse another profile's vault. Entry
JSON is bounded, top-level fields must resolve to non-empty strings, repeated fields from one entry
share one CLI read, and CLI output is never copied into errors, warnings, logs, tools, prompts, or
events. The plugin registers no tool or hook, so raw-secret retrieval is not model-callable.

Configuration lives under `secrets.kista` in `config.yaml`:

```yaml
plugins:
  enabled: [kista-secret-source]
secrets:
  kista:
    enabled: true
    vault_dir: credentials
    env:
      OPENROUTER_API_KEY: kista://openrouter/key
```

The operator may pin `binary_path` to an installed Kista executable or the official
`scripts/credstore.py` during development. Existing environment values win by default; an explicit
`override_existing: true` opts into replacement through the normal Hermes orchestrator.

### Slice 29: Profile-Scoped Exact Redaction

The Secret Source orchestrator now registers every value it actually applies with Hermes' existing
bounded exact-value vault redactor before placing the value in the target environment. This is a
generic security property of all Secret Sources rather than Kista-specific logging code. Values
that lose precedence are not registered, and no source receives access to another source's values.

The exact-value registry remains memory-only and is keyed by the normalized Hermes profile home.
Consequently, Kista credentials are scrubbed by the canonical redaction pipeline—including the
hard model-egress pass and redacting log formatter—even when a credential has no recognizable
vendor prefix. Profile A's registered bytes neither redact nor disclose matches in profile B. The
registry stores no reference, service name, environment-variable name, or persistent copy, and the
Kista plugin still owns no prompt, transcript, event, telemetry, or log integration.

### Slice 30: Cross-Surface Canary Containment

The security contract now follows one synthetic, deliberately prefix-less Kista value from real
plugin discovery and subprocess retrieval through the Secret Source orchestrator and the Volmarr
runtime. Raw copies are injected into lifecycle hook arguments, tool results, and tool errors to
prove that Verðandi lifecycle and cognition telemetry remain metadata-only. The actual terminal
output boundary applies the profile-scoped exact redactor before the result is admitted to Hermes
session history, and the canonical redacting formatter protects log output.

After the run, the contract reopens session history and scans every SQLite database, WAL, and SHM
sidecar created beneath the active profile, including any memory database created by enabled
hooks. It also inspects every captured Verðandi payload, cognition event, log record, stdout, and
stderr stream. The canary must occur in none of them. This adds no new storage path or memory
authority: an absent memory database remains absent, rather than being invented solely for a
security test.

### Slice 31: Vault Permission Gate

An initialized Kista vault must pass a read-only permission audit before the adapter invokes the
CLI. On POSIX, the vault directory, `.vault_key`, and `vault.json.enc` must be owned by the current
effective user and expose no group or world permission bits. On Windows, the adapter reads the real
NTFS DACL in SID form and permits allow entries only for the current user, LocalSystem, and the
built-in Administrators group. Conditional allow entries and unverifiable ACLs fail closed; Unix
mode bits are never treated as proof of Windows isolation.

The directory and both required files must be real filesystem objects, not symbolic links,
junctions, or other reparse points. An incomplete initialized vault is refused before any helper
process starts. A wholly absent vault still reaches Kista so its canonical initialization error and
remediation remain authoritative. The audit changes no ACL or mode and never reads secret bytes;
operators retain ownership of intentionally hardening their vault storage.

## Milestone 8: Personal Tool Suite

### Slice 32: Local Lunar Astrology

The separate, opt-in `volmarr-astrology` plugin begins the personal tool suite with one narrow
vertical slice: `astrology_lunar`. It invokes the official external AI Agent Astrology Engine at a
profile-configured `astrology_engine.py` path and returns the engine's current lunar phase,
illumination, void-of-course status, next lunations, and Moon aspects as a bounded calculation
report. The engine computes; Hermes and its normal cognition route may interpret afterward.

The tool accepts no arguments, so this first slice has no birth data, location, geocoding, network,
or prediction-range surface. Its subprocess uses fixed argv, closed stdin, a minimal environment
that excludes provider credentials and `HERMES_HOME`, a clamped timeout, and separate 64-KiB stdout
and stderr limits. Child failures are translated into static errors without echoing child output.
The plugin registers no hook, prompt contribution, provider, state store, or telemetry publisher,
and the external Apache-2.0 engine remains outside this repository.

### Slice 33: Coordinate-Bound Planetary Hours

`astrology_planetary_hours` extends the same plugin and subprocess boundary with one explicit
calendar date, latitude, and longitude. Requiring validated finite coordinates prevents the
official engine from entering its optional city-geocoding cascade, while requiring a date avoids
an implicit host-date default. Latitude is strictly bounded between the poles and longitude is
bounded to the canonical `[-180, 180]` interval before fixed CLI flags are built.

The result contains the engine's day ruler, sunrise/sunset calculation, and twelve day plus twelve
night Chaldean rulers; interpretation remains absent. The adapter also recognizes the official
engine's zero-exit `Error calculating planetary hours` output as failure, so polar-day or
ephemeris errors cannot masquerade as successful reports. No location is stored, published, or
sent to a network service by the plugin; ordinary Hermes tool-call transcript policy still applies.

### Slice 34: Explicit-Coordinate Natal Charts

`astrology_natal` accepts a real birth date, optional validated 24-hour birth time, and finite
explicit coordinates. It passes only `natal`, date, coordinate, and optional time flags to the
official engine—never a city, nation, or personal name—so its geocoder and identity-label surfaces
remain unreachable. When time is absent the engine's documented unknown-time/noon path is
preserved and the result labels `time_known: false` rather than inventing precision.

The tool returns the engine's local planetary positions, houses, aspects, dignities, lots,
antiscia, Hellenistic analysis, and Norse/rune overlay as calculation output with interpretation
explicitly absent. The plugin creates no additional state, memory record, telemetry, or network
copy. Birth inputs and reports remain ordinary Hermes tool-call data and therefore follow the
operator's normal session-history policy.

### Slice 35: Reproducible Transit Charts

`astrology_transit` compares a coordinate-bound natal chart with a required explicit sky date.
This deliberately removes the official CLI's implicit “now” branch, making every tool result
replayable from its recorded arguments. Natal and transit times remain optional but validated; the
engine's documented defaults are surfaced through `natal_time_known` and
`transit_time_explicit` metadata instead of being hidden.

Only date, time, and coordinate flags reach the external engine. City, nation, identity labels,
network geocoding, persistence, and interpretation remain outside the plugin. The returned report
contains sky positions, transiting planets in natal houses, and transit-to-natal aspects under the
same bounded, credential-free subprocess contract as the earlier astrology tools.

### Slice 36: Bounded Astrology Prediction

`astrology_predict` exposes the official engine's exact transit-to-natal aspects, stations,
ingresses, and eclipse scan over an explicit forward-moving window no longer than 366 days. Natal
date and coordinates are required; birth time remains optional and explicit. The adapter uses the
engine's documented built-in transit and natal planet sets rather than accepting arbitrary lists,
which keeps both computation and CLI construction bounded.

Start and end never default to the host clock, coordinate geocoding is unreachable, and the shared
60-second maximum process timeout plus 64-KiB output ceiling remain hard boundaries even when the
operator configures a longer value. Prediction output is calculation evidence only; the normal
cognition layer may interpret it separately.

### Slice 37: Anonymous Coordinate-Only Synastry

`astrology_synastry` calculates two-chart cross-aspects from two explicit date/coordinate pairs and
optional times. The schema contains no name, city, or nation fields, and direct-dispatch validation
rejects those extra identity surfaces before process launch. The official engine therefore labels
the charts only as Person A and Person B and cannot invoke geocoding.

The current official CLI enables house overlays only when city fields are present, even if latitude
and longitude are already supplied. This adapter does not fabricate placeholder cities to enter
that branch: `house_overlays_included` is explicitly false, while the valid coordinate-based
planetary cross-aspects remain available. The plugin adds no relationship record or interpretation;
ordinary Hermes transcript policy remains the only persistence boundary.

### Slice 38: Coordinate-Only Astrocartography

`astrology_astrocartography` completes the initial astrology set with the official engine's local
MC, IC, ASC, and DSC line calculation. It requires a real birth date plus finite birth coordinates;
birth time is optional and its presence is declared in result metadata. An optional query point may
be supplied only as a complete latitude/longitude pair, allowing the engine to report nearby lines
without accepting a city or invoking geocoding.

The schema and direct-dispatch guard reject names, city/nation labels, partial query points, and
out-of-range coordinates before the subprocess starts. Only validated date, time, birth-coordinate,
and query-coordinate flags reach the fixed CLI boundary. The plugin creates no map record, location
profile, telemetry publisher, or interpretive layer; the calculation and its ordinary Hermes tool
transcript remain subject to the same policies as the other astrology tools.

### Slice 39: Reproducible Single-Card Tarot Draw

The separate, opt-in `volmarr-tarot` plugin begins the Tarot family with `tarot_draw`: one card
from the official 78-card RuneTarot deck under a required integer seed. The result carries the
official card identity, orientation, keywords, selected orientation meanings, and Golden Dawn
correspondences. These are deck facts; question-driven or LLM-generated interpretation remains a
later cognition concern.

RuneTarotEngine's current `main` head (`432e461136ba58cb3e507bb9cd86b4bb2faba80b`) contains the
project description and MIT license but no executable tree. The current official executable is on
`development` at `5c2ed4746b1c303590bca85bb0d30a3d7b1e437b`. The adapter therefore identifies that surface
explicitly and loads only its `src.deck.TarotDeck` subsystem in an isolated child process; no
RuneTarot source or card data is copied into this repository.

The bridge never constructs RuneTarot's engine, AI reader, session manager, TUI, or renderer. It
accepts no question or identity text, sends no provider credential, closes stdin, requires the
official 78-card invariant, bounds runtime and output, and creates no RuneTarot history or export.
Seed zero remains valid, reversals are explicit, and plugin configuration is resolved from the
active Hermes profile on every draw.

### Slice 40: Positioned Multi-Card Tarot Spreads

`tarot_spread` extends the same deck-only child boundary to RuneTarot's seven official multi-card
layouts: Three Card, Past Life, Opening of the Key, Relationship, Celtic Cross, Tree of Life, and
Zodiac Wheel. The caller supplies an exact layout key and required seed; fuzzy spread matching and
arbitrary card counts are not exposed.

RuneTarot owns the card count, shuffle, orientation, position order, position meanings, and Golden
Dawn position correspondences. The bridge verifies that position count equals the official card
count, assigns every drawn card through `SpreadManager`, and returns the resulting facts without a
question or synthesis. It still never initializes the upstream AI, session, renderer, or export
surfaces, and the 64-KiB output ceiling bounds even the twelve-card Zodiac Wheel response.

### Slice 41: Official Elemental Dignity Structure

Every `tarot_spread` result now includes RuneTarot's four-element balance and its ordered adjacent
card dignity relationships. The official `GoldenDawnEngine` remains authoritative for base-element
normalization and the friendly, hostile, neutral, excessively strong, or unknown relationship; the
plugin neither reimplements the matrix nor turns it into narrative advice.

This is a pure extension of the existing spread result rather than a new model-facing tool. It
loads only RuneTarot's deterministic Golden Dawn data beside the deck and spread subsystems, then
returns the structural evidence for Hermes cognition to interpret separately. Provider calls,
questions, storage, telemetry, and prompt contributions remain outside the Tarot plugin.

### Slice 42: Reproducible Seiðr Composition

The separate, opt-in `volmarr-seidr` plugin begins Norse poetry with `seidr_compose`, backed by the
official MIT-licensed Seiðr Engine at current `main` commit
`a1999cd21bdac6c65791ff98c0f8125bff04cc69`. It exposes the engine's four meters, optional Nine
Worlds vocabulary domain, one to four stanzas, explicit kenning control, and structured line-level
syllable/alliteration metadata. No engine source or lexicon is copied into Hermes.

Composition runs through the official `Lexicon`, `Skald`, and `PoemConfig` API in a bytecode-free,
no-user-site child with closed stdin, minimal environment, static failures, and 64-KiB output cap.
The adapter fixes `PYTHONHASHSEED=0` because the current engine selects from an unordered set of
alliteration groups; without that process invariant, identical numeric seeds diverge across fresh
interpreters. Numeric seed zero is rejected because the current `compose_poem` implementation
treats it as falsy and enters an unseeded branch. The plugin accepts no free-form topic yet and
makes no model call, state write, prompt contribution, or telemetry emission.

### Slice 43: Canonical Seiðr Form Catalog

`seidr_forms` reads the official engine's `FORMS` registry and returns each canonical meter's code
key, Old Norse name, syllable range, and structural description. Registry aliases such as the
alternate ASCII spelling of fornyrðislag are collapsed by comparing each entry's key with the
form object's own canonical name, so Hermes does not publish duplicate forms or maintain a second
catalog.

The tool accepts no arguments and uses the same read-only, credential-free child boundary as
composition. It adds no cache, persistence, or prompt text; changes in the external engine's
canonical registry appear when the configured checkout changes.

### Slice 44: Official Kenning Catalog

`seidr_kennings` returns the configured engine's complete `Lexicon.kennings` collection, including
each described base, poetic expression, component words, Nine Worlds domain, and the engine's own
computed syllable count. The tool has no filters or pagination, so the compact authoritative
catalog is read in full and no model can mistake a partial page for the vocabulary boundary.

Hermes neither copies nor extends this lexicon. The catalog is resolved from the active profile's
external checkout on every call through the same closed-stdin, bytecode-free child, without state,
network, provider credentials, or prompt mutation.

### Slice 45: Independent Seiðr Meter Validation

`seidr_validate_meter` accepts one canonical form and one to eight bounded verse lines. Inside the
isolated engine child, each line is tokenized into words, measured with the official approximate
syllable counter, assigned the official first-word alliteration group, constructed as an official
`Line`, and passed to the selected form's `validate_stanza` implementation. The response exposes
the verdict and every computed metric rather than replacing the engine's result with prose.

This validation is intentionally structural, matching the current engine's published rules and
limitations; it is not a claim of philological correctness. Input is never persisted or sent to a
model or network service, and the strict eight-line/200-character bounds keep argv and output
finite.

### Slice 46: Replayable Bounded Dice

The separate, opt-in `volmarr-rpg` plugin begins reusable D&D/Norse Saga mechanics with
`dice_roll`. It accepts a structured dice count, side count, optional flat modifier, and required
seed rather than parsing an open-ended notation language. Count, sides, modifier, and seed are all
bounded before the standard-library PRNG is constructed.

The result includes every die, subtotal, modifier, total, and normalized notation, making the
arithmetic auditable and the roll exactly replayable—including seed zero. The plugin owns no
campaign, character, encounter, narration, rules corpus, memory, or prompt state and requires no
external dependency.

### Slice 47: SRD-Grounded Ability Checks

`rpg_skill_check` implements the SRD ability-check rule as a replayable mechanic: roll one d20,
add the supplied total modifier, and succeed when the total equals or exceeds the Difficulty Class.
Normal, advantage, and disadvantage modes roll one or two d20s and keep the required result. The
rule was verified against official fork commit `2e62e0413061c2443e21369cdc074c7a7356a857` without
copying SRD text or data into the plugin.

The tool deliberately reports `natural_d20_automatic: false`: ordinary ability checks resolve by
the modified total, unlike attack-roll critical rules. It accepts no character sheet, ability
name, skill label, proficiency state, or narrative outcome; callers calculate one bounded modifier
and the GM retains authority over consequences.

### Slice 48: Replayable Binary Oracle

`rpg_oracle` is a small original percentile mechanic, not a copy of a Mythic GME table or a
NorseSagaEngine subsystem. A named likelihood maps to a disclosed 0–100 yes threshold, while a
bounded chaos factor controls only the size of the exceptional-result bands at the two extremes.
This keeps probability and volatility separate and makes every outcome auditable.

The tool requires an explicit seed and returns the percentile roll, yes threshold, exceptional
band, Boolean answer, and normalized outcome. It accepts no question text, campaign state,
narrative consequence, hidden entropy, or model dependency. The caller supplies meaning; the
plugin supplies only finite replayable mechanics.

### Slice 49: Caller-Owned Random Tables

`rpg_random_table` selects one entry from a caller-supplied table of at most 100 short strings.
It uses an explicit seed, reports a one-based dN-style roll, and returns the normalized selected
entry. This creates a reusable random-table primitive without embedding copyrighted setting or
rules content in Hermes.

The table is ephemeral call input: the plugin does not name, persist, merge, weight, interpret, or
narrate entries. Per-entry and table-size bounds keep the result finite, and strict field refusal
prevents accidental expansion into campaign storage or a hidden table language.

### Slice 50: External SRD Condition Lookup

`rpg_condition_lookup` reads one named condition from `json/12 conditions.json` in a configured
external `dnd-5e-srd` checkout. The root is resolved from the active profile at call time, so
profile switches cannot retain another profile's rules source. Hermes bundles no SRD prose and
does not rewrite or persist the returned definition.

The adapter accepts only one short condition name, matches it case-insensitively, bounds both the
source file and selected definition, and reports the external corpus file plus OGL 1.0a
provenance. The currently verified official fork is commit
`2e62e0413061c2443e21369cdc074c7a7356a857`; alternate configured checkouts remain explicit
operator choices rather than silently embedded dependencies.

### Slice 51: Replayable Character Ability Skeleton

`rpg_random_character` creates only a mechanical ability skeleton: Strength, Dexterity,
Constitution, Intelligence, Wisdom, and Charisma are each rolled with a fixed 4d6-drop-lowest
method. Every die, the exact dropped index and value, resulting score, and floor-derived modifier
are returned under an explicit seed.

The tool marks `character_complete: false` because abilities are not a character identity. It
does not choose or accept a name, ancestry, class, culture, gender, alignment, personality,
equipment, biography, art prompt, or campaign state. Those semantic layers remain separate from
the finite random mechanic and no catalog content is copied from the SRD or NorseSagaEngine.

### Slice 52: Replayable Encounter Initiative

`rpg_encounter_initiative` rolls one d20 for each of at most 40 participants, adds the caller's
bounded total initiative modifier, and returns a complete ordered list. Participants carry only a
short opaque identifier and modifier; the tool does not ingest character sheets, hit points,
conditions, actions, or narrative descriptions.

The result exposes every roll and sum and states that natural d20 values have no automatic
initiative meaning. Ties use a documented adapter rule—higher modifier, then identifier, then
input order—so replay remains total and deterministic without pretending that this ordering is a
mandatory SRD table rule.

### Slice 53: Finite Hit-Point Transitions

`rpg_hit_points` applies exactly one supplied damage or healing amount to caller-owned hit-point
values. Damage consumes temporary hit points before current hit points; healing is capped at the
maximum and never restores temporary hit points. The result returns complete before/after values,
applied deltas, unused healing or overflow damage, and whether current hit points reached zero.

The tool is intentionally stateless and does not roll damage, infer resistance or vulnerability,
award temporary hit points, or resolve unconsciousness, instant death, death saves, or stability.
It explicitly reports that those zero-hit-point consequences remain unresolved, keeping this
slice faithful to its finite arithmetic boundary.

### Slice 54: Read-Only Hamr Spec Validation

The separate, opt-in `volmarr-hamr` plugin begins Embodiment with
`hamr_spec_validate`. It resolves the official Hamr engine, an allowed spec root, and compatible
Python interpreter from the active profile at call time, then invokes Hamr's public
`Spec.from_yaml` API in a bounded subprocess. The local official `Development` head verified for
this boundary is `db90f4657c2725d0b6432651d1400f1a05f77b7d` under MIT.

Only relative YAML paths contained beneath the configured spec root are accepted. The subprocess
has closed stdin, a minimal environment without service credentials or `HERMES_HOME`, bytecode
writes disabled, finite input/output/time bounds, and no Blender invocation. Results preserve
Hamr's validation verdict and errors while explicitly reporting that no avatar output was created.

### Slice 55: Read-Only Hamr Preset Discovery

`hamr_presets` reads Hamr's published `BODY_PRESETS` and `CHARACTER_PRESETS` catalogs through the
same active-profile, credential-scrubbed subprocess boundary. Body entries expose their numeric
proportions; character entries expose only key, display name, and short description rather than
copying complete preset specs into Hermes.

The tool accepts no arguments, launches no Blender process, creates no output, and returns finite
catalog counts with MIT provenance. This gives later build planning a discoverable official
vocabulary without prematurely granting avatar-build or filesystem-write authority.

### Slice 56: Hamr Performance Budget Preflight

`hamr_budget_check` loads one already bounded spec path and invokes Hamr's pure-Python
`check_budget` estimator against one exact official tier: `minimal`, `balanced`, or `high`. It
returns Hamr's build-time, peak-memory, triangle, and texture estimates alongside every selected
limit, warning, and the official within-budget verdict.

Like validation and preset discovery, budget preflight runs with closed stdin, scrubbed
credentials, call-time profile resolution, and finite subprocess bounds. It explicitly launches
no Blender process and writes no output, so planning remains separate from the later authority to
forge a body.

### Slice 57: Honest Hamr Artifact Probe

`hamr_artifact_probe` calls Hamr's current public `builder.inspect` API for one traversal-safe VRM
or GLB beneath an active-profile artifact root. Inputs are limited to the official interface's
documented VRChat and VRoid targets, and files are bounded at 512 MiB before the isolated process
starts.

At the verified Hamr commit, `builder.inspect` reports file existence, size, requested targets, and
an empty checks list; the separate inspection module also identifies itself as a placeholder.
Therefore the adapter reports `inspection_scope: metadata_only` and
`compliance_performed: false` instead of presenting file metadata as certification. It can expose
real official checks later without changing this truth boundary.

### Slice 58: Read-Only Seiðr-Smiðja Loom Validation

The separate opt-in `volmarr-smidja` plugin begins the higher-level avatar forge boundary with
`smidja_spec_validate`. It calls the official public `loom.load_and_validate` API at clean current
`development` commit `482c8f0032b28c4ceb323478e7854adae3715f72`, returning a bounded summary or
field/reason failures without received values. Paths remain beneath an active-profile spec root.

The subprocess has closed stdin, scrubbed credentials, disabled bytecode writes, and finite file,
time, and output bounds. It dispatches no forge, Blender, REST, MCP, or Brúarhönd control. The
upstream root `LICENSE` says Apache-2.0 while `pyproject.toml` declares MIT; the adapter copies no
engine source and explicitly reports this unresolved metadata conflict rather than choosing one.

### Slice 59: Read-Only Seiðr-Smiðja Hoard Discovery

`smidja_assets` exposes the official public `LocalHoardAdapter.list_assets` boundary with bounded
asset-type and tag filters. Results contain only the upstream `AssetMeta` contract: identifier,
display name, type, tags, VRM version, declared size, and whether the backing file currently exists.

Discovery never calls `resolve`, the network-capable bootstrap command, or any build surface. It
does not return filesystem paths or remote source URLs, and it declares that no asset was resolved,
fetched, or bootstrapped. Engine and Python settings are resolved from the active profile on every
call; A→B→A coverage protects that boundary.

### Slice 60: Read-Only Seiðr-Smiðja Gate Rule Discovery

`smidja_gate_rules` exposes `gate.list_rules` for exactly one official target (`VRCHAT` or
`VTUBE_STUDIO`). It returns only rule identifiers, display names, severities, and descriptions;
threshold extras remain inside the external engine until a dedicated contract needs them.

This is diagnostics, not certification. No avatar is opened, no Gate check executes, and the result
explicitly states that artifact inspection and compliance evaluation did not occur. Rule files are
selected beneath the verified engine checkout, and call-time A→B→A coverage remains mandatory.

### Slice 61: Read-Only Seiðr-Smiðja Oracle Eye View Discovery

`smidja_render_views` exposes only `oracle_eye.list_standard_views`, preserving the official order
and open-ended names. It accepts no paths or rendering options and explicitly reports that Blender
was not launched and no images were created.

The view catalog remains owned by the external engine and is resolved from the active profile at
call time. This creates a safe planning surface without granting render or filesystem authority.

### Slice 62: Bounded Seiðr-Smiðja Gate Structural Check

`smidja_gate_check` admits one relative `.vrm` beneath an active-profile artifact root and invokes
the official `gate.check` API for a bounded target set and VRChat tier. The adapter returns the
official pass value and sanitized rule findings without echoing artifact-derived values.

The current upstream reader inspects only the glTF JSON header. Polygon and texture rules remain
advisory and explicitly surface in `unevaluated_rule_ids`; consequently the adapter always reports
`certification_complete: false` and names its scope `official_gate_structural_header`. It creates no
output, launches no Blender process, and enforces path containment plus a 128 MiB input ceiling.

### Slice 63: Read-Only Seiðr-Smiðja Hoard Resolution Readiness

`smidja_asset_probe` calls the local-only `LocalHoardAdapter.resolve` boundary for one bounded asset
identifier. It reports availability, file type, and size while withholding the resolved filesystem
path and leaving the asset unopened.

Missing catalog entries and uncached files are normal `available: false` results. The adapter never
invokes Hoard bootstrap or any fetch path, and engine selection remains call-time profile scoped
with A→B→A proof.

### Slice 64: Read-Only Seiðr-Smiðja Forge Readiness

`smidja_forge_readiness` invokes the official Blender executable resolver with an optional
profile-scoped absolute path, then verifies that the external Forge build script is present. It
returns only readiness booleans and the executable filename; the full path remains withheld.

The probe never calls `run_blender` or `forge.build`, creates no output directory, and grants no
build authority. On the verified Windows host no Blender executable is currently discoverable, so
real Forge execution remains deliberately unavailable rather than simulated.

### Slice 65: Native Hermes Voice Readiness

The opt-in `volmarr-voice` plugin begins the voice phase with `voice_pipeline_readiness`, a
read-only view over Hermes' existing voice configuration and prerequisite checks. Hermes already
owns microphone capture, VAD, STT, turn execution, TTS, streaming, and barge-in, so the personal
layer does not duplicate those systems or choose an external voice framework prematurely.

The tool resolves voice mode and STT/TTS selections from the active profile at call time, reports
only local prerequisite booleans, and withholds credentials. It never opens a microphone, records
audio, transcribes, synthesizes speech, or contacts a provider. Dependency readiness is explicitly
separate from credential, connectivity, and end-to-end verification; A→B→A discovery coverage
protects the profile boundary. Custom plugin-provider readiness remains unknown rather than calling
arbitrary provider code from a diagnostic probe.

### Slice 66: Official Voice and Avatar Candidate Audit

`VOICE_EMBODIMENT_AUDIT.md` pins current official heads and releases for Hermes, AIAvatarKit,
Open-LLM-VTuber, and OmniVoice. The audit keeps Hermes as the sole voice-loop owner: AIAvatarKit
and Open-LLM-VTuber may later serve bounded presentation/channel roles, while OmniVoice may later
serve only as an optional Hermes TTS provider.

The personal OmniVoice fork is not current: its `0.1.3` head is an ancestor of official
`k2-fsa/OmniVoice`, which is 50 commits ahead at `0.2.1`. No dependency, model, source, or sample
avatar enters the repository in this slice. Candidate adoption requires a separate interface,
resource, license, and consent audit.

### Slice 67: Provider-Free Hermes Voice Dispatch Contract

A second real-discovery contract installs temporary profile-scoped STT and TTS provider fixtures,
passes a valid synthetic WAV through `transcribe_audio`, and feeds the returned transcript through
`text_to_speech_tool`. Both calls use Hermes' real validation, provider registry, configuration,
dispatch, and output-envelope paths.

The fixture performs no inference and is created only inside the test profile. The contract opens
no microphone or speaker, contacts no network, reads no credential, and downloads no model. It
also proves the input audio remains byte-identical while the TTS dispatcher returns one valid WAV.
This establishes the extension seam without adding a second voice orchestrator.

### Slice 68: Presentation-Only Avatar Contract

`AVATAR_PRESENTATION_CONTRACT.md` defines the minimal versioned handoff from Hermes-owned TTS to
an optional avatar shell: complete WAV bytes, explicit face/animation controls, stop/final events,
and opaque session/transaction sequencing. It forbids microphone capture, STT, LLM, TTS, memory,
tools, conversation ownership, filesystem-path transport, credentials, and expression markup in
model or spoken text.

The contract is grounded in the official AIAvatarKit response model and maintained clients at
commit `38b617b8b9269939734e70ef503d7ea6976acdbd`. A future bounded adapter can map `speech` to a
complete-WAV `chunk` response and map `stop`/`final` directly. The existing `/avatar/perform`
endpoint is explicitly rejected because it accepts text and invokes AIAvatarKit's own TTS; the
stock WebSocket client is not adopted as-is because it also starts microphone capture. This slice
adds no runtime hook, dependency, network service, audio operation, or candidate source.

### Slice 69: Provider-Free Presentation Serializer

`volmarr-voice.presentation` encodes the v1 handoff without registering a tool, hook, transport, or
resident process. It validates bounded opaque routing tokens, monotonic-compatible integer sequence
values, complete uncompressed PCM WAV payloads, and shell-owned face/animation names before
producing base64 audio with a SHA-256 digest and decoded format evidence.

Real plugin discovery loads the defining module and proves byte-exact WAV round-trip, explicit
control mapping, absence of text/path fields, strict malformed-WAV rejection, and audio-free
`stop`/`final` events. The serializer opens no device, contacts no provider or network, reads no
credential or profile setting, and does not select an expression. It is the concrete producer a
future presentation transport must consume rather than a speculative generic hook.

### Slice 70: AIAvatarKit Response Translation Contract

`volmarr-voice.aiavatarkit` provides a pure translation from canonical v1 events to the official
AIAvatarKit presentation response fields. `speech` becomes a complete-WAV `chunk` with explicit
`avatar_control_request`; `stop` and `final` map directly. Contract, transaction, sequence, and
audio-digest evidence remains bounded inside response metadata, while text, voice text, user
identity, conversation context, and pipeline requests remain absent.

The translator revalidates the complete canonical envelope, so altered fields, digests, formats,
audio, or ownership-bearing additions fail before translation. A provider-free consumer fixture
decodes the exact response like the maintained AIAvatarKit client, verifies WAV frames and visual
controls, exercises stop/final delivery, and rejects injected second-mind text. No socket, server,
authentication, retry queue, external package, device, or AIAvatarKit pipeline is started.

### Slice 71: Presentation Transaction Lifecycle

`PresentationTransactionRouter` owns one active presentation transaction per session without
owning a network connection. Transactions begin only with `speech` sequence zero and then advance
by exactly one. A replacement transaction first yields an AIAvatarKit-compatible interruption,
retires the old identifier, and only then yields new audio. Retired IDs are refused, final events
release live ownership, disconnect performs deterministic cleanup, and stale-ID memory is bounded.

Real discovery proves A→B replacement ordering, stale-A rejection, final cleanup, sequence-gap
rejection, independent sessions, and idempotent disconnect. State is process-local and contains
only opaque routing tokens. No profile configuration, durable queue, retry, socket, authentication,
audio device, provider, external service, or core change participates.

### Slice 72: Loopback Delivery and Authentication Audit

`AVATAR_LOOPBACK_TRANSPORT_AUDIT.md` selects a future outbound-only WebSocket feed on literal
`127.0.0.1`. The shell receives proven AIAvatarKit-compatible response JSON after a bounded
presentation-only readiness message; every input-bearing request type remains forbidden. One
consumer owns a session, writes are serialized, ownership is rechecked before send, and disconnect
drops unsent data without replay or Hermes-state changes.

The proposed listener requires a strong `VOLMARR_AVATAR_TOKEN` loaded only through `.env` and sent
only as an Authorization bearer header. Query, URL, cookie, subprotocol, YAML, argv, event, log, and
error exposure are forbidden; browser-Origin connections are deferred and rejected. The design can
use Hermes' existing pinned `websockets==15.0.1` dependency and needs no candidate code or web
framework. This slice adds no listener, socket, runtime registration, dependency, or secret.

### Slice 73: Pre-Socket Avatar Admission

`volmarr-voice.admission` validates the future listener before any networking is possible. It
accepts only literal `127.0.0.1`, an unprivileged port, the fixed presentation path, and no browser
Origin. It loads a 32–256 character printable bearer only from `VOLMARR_AVATAR_TOKEN`, registers
the exact value with the active profile's bounded in-memory redactor, wraps it in a non-revealing
object, and compares Authorization values in constant time with generic rejection errors.

The readiness parser accepts at most 512 UTF-8 bytes and exactly three fields: `type=ready`, the v1
contract, and a bounded opaque session ID. `invoke`, microphone/audio fields, unknown fields,
wrong versions, malformed JSON, and oversize input fail closed. Real discovery proves token
redaction across A→B→A profiles and refuses wildcard/hostname/privileged/path/Origin targets. The
module does not import WebSockets, bind a socket, register a runtime surface, or read YAML.

### Slice 74: Disposable Authenticated Loopback Feed

`AvatarLoopbackFeed` is an explicit async helper built on the already-pinned `websockets==15.0.1`;
the plugin does not import, register, or start it during discovery. An operator-owned caller must
provide the validated environment token and invoke `start()`/`stop()`. The helper binds only the
prevalidated target, admits one bearer-authenticated ready consumer per session, serializes writes,
routes canonical events through the proven transaction state, refuses every later client message,
and releases ownership on disconnect or shutdown.

Disposable real-loopback tests deliver a complete WAV and face control through the actual socket,
then deliver `final` and tear down. They also prove bad-auth refusal, duplicate-owner refusal, and
input-bearing client closure with no provider, microphone, avatar process, retry, durable queue, or
Hermes runtime registration. The exact pinned dependency was installed into the selected local
Python 3.11 test environment because it was declared by the repository but missing there.

### Slice 75: Operator-Owned Feed Orchestration Audit

`AVATAR_ORCHESTRATION_AUDIT.md` reserves feed start/stop authority for an explicit future
`hermes volmarr-voice serve` command. The command will use fixed loopback settings, load its bearer
only at execution time from `VOLMARR_AVATAR_TOKEN`, accept canonical v1 NDJSON only through stdin,
and stop on EOF or operator interruption. It will accept no text, TTS request, provider, model,
microphone, filesystem path, URL, asset command, or conversation state.

The audit proves from current call sites that `post_tool_call` observes model-dispatched TTS tools
but not direct TTS calls made by CLI and native voice playback. RuneForgeAI therefore refuses a
partial hook-based integration and will not patch or monkey-patch Hermes core. Automatic mirroring
stays deferred until a generic upstream post-TTS observer exists. This slice registers no command,
hook, tool, service, scheduler, or new dependency.

### Slice 76: Side-Effect-Free Operator CLI Gate

Real discovery now registers `hermes volmarr-voice status` alongside the existing readiness tool.
Status reports the v1 contract, operator-stdin producer intent, disabled serve action, absent runtime
registration/listener, and unavailable automatic voice mirroring. The `serve` action is not yet
parseable, so neither help nor invalid serve attempts can load a token or bind a socket.

Tests prove discovery adds exactly one operator CLI, no lifecycle hook, and no new model tool;
status succeeds even when socket construction is forced to fail, does not read or print a planted
token, and rejects `serve`. The CLI module imports neither admission nor loopback. This establishes
the authority boundary before the eventual explicit runner is enabled.

### Slice 77: Bounded Stdin Feed Runner

`run_feed_from_stream` starts an explicitly supplied feed, consumes one newline-terminated binary
stdin record at a time, enforces a bound derived from the 16 MiB WAV ceiling, decodes UTF-8/JSON,
revalidates the exact canonical envelope, and publishes without echoing content. EOF returns the
published count; malformed, oversize, non-canonical, or delivery-failed input raises only a generic
operator error. A `finally` block always stops the feed.

A disposable real-loopback test starts the runner behind the still-disabled CLI action, connects an
authenticated presentation consumer, delivers one canonical stdin WAV event, observes the chunk,
then sends EOF and proves clean return. A second invariant proves malformed and oversize input never
publishes and always tears down. No tool, hook, CLI serve action, auto-start, file path, or core seam
is added.

### Slice 78: Explicit Operator Serve Action

`hermes volmarr-voice serve --port PORT` now connects the proven operator CLI, loopback feed, and
stdin runner. The parser accepts only unprivileged ports. Network and admission modules are imported
only inside the serve handler; the fixed host/path and environment-only bearer cannot be overridden
by arguments. Missing credentials fail before socket creation. Runtime failures produce one generic
stderr line without event or secret content, EOF reports only the event count, and Ctrl-C has a
distinct operator-stop result.

Real discovery proves missing-token preflight with socket construction forbidden. A full command
test runs the synchronous handler in an operator thread, connects a real authenticated consumer,
delivers one canonical stdin WAV event, sends EOF, joins the thread, and proves stdout is empty and
stderr contains neither bearer nor audio. Status remains non-running, and no model tool, lifecycle
hook, autostart, native-voice claim, or core change is introduced.

### Slice 79: Operator WAV Event Encoder

`hermes volmarr-voice encode` converts one operator-selected complete WAV into one canonical v1
speech-event line. It requires explicit session and transaction IDs, defaults to sequence zero, and
accepts only optional shell-owned face/animation names. The source must be a regular non-symlink
file within the existing 16 MiB bound; the serializer then validates PCM/container/duration and
adds format and digest evidence.

Encoding imports no admission or loopback module, reads no bearer, opens no socket, performs no TTS,
and emits no path or text. Invalid audio produces one generic stderr line without path or content.
Real discovery proves byte-exact output, canonical revalidation, explicit controls, and path/text
absence with socket construction forbidden. This completes a manual operator pipeline without
pretending to attach every native Hermes voice reply.

### Slice 80: Avatar Operator Guide and Smoke Recipe

`AVATAR_OPERATOR_GUIDE.md` consolidates the profile enablement, `.env` bearer rule, fixed endpoint,
native presentation-only readiness handshake, explicit serve lifecycle, WAV encoder, ordering, and
focused real-loopback verification commands. It warns that the consumer must own the session before
stdin receives an event and rejects a naïve `encode | serve` pipeline rather than implying an
unproven queue.

The guide also keeps both unsafe official surfaces out: the stock AIAvatarKit client starts a
microphone, and `/avatar/perform` starts AIAvatarKit TTS. It states the current manual-development
scope and automatic native-voice seam gap without altering the protected project `README.md`.

### Slice 81: AIAvatarKit Presentation Consumer Audit

`AIAVATARKIT_PRESENTATION_CONSUMER_AUDIT.md` reads both maintained client implementations at the
pinned official commit. Their output behavior validates the RuneForge response map: complete-WAV
chunks, face/animation controls, stop, and final are real consumer fields. Neither client is an
admissible presentation-only shell, however.

The Python client constructs input and output devices plus `AudioRecorder`, schedules the microphone
worker, sends `start`, and sends a client `stop`. The browser client uses subprotocol auth, sends
`start`, requests `getUserMedia`, and continuously sends microphone or silent `data` frames. Muting
does not remove input ownership. RuneForgeAI therefore imports no dependency or source and refuses
subclass/monkey-patch drift until official output-only construction, readiness, authentication, and
cleanup exist.

### Slice 82: Open-LLM-VTuber Presentation Boundary Audit

`OPEN_LLM_VTUBER_PRESENTATION_AUDIT.md` reads the current official backend and its exact pinned web
build. The web player independently validates complete-WAV playback, lip sync, talk motion,
subtitles, and explicit Live2D expressions, but those functions are not published behind an
output-only application boundary.

Every `/client-ws` connection clones the backend's ASR, TTS, VAD, agent, tool, history, and model
context, then commands the frontend to start its microphone. The frontend also creates history,
requests configuration, sends captured audio, and participates in a synthesis/playback
acknowledgement cycle. `/tts-ws` is rejected because it starts duplicate TTS. Its message schema,
admission behavior, and lifecycle are incompatible with the strict RuneForge feed without a fork
that would erase the presentation-only invariant.

No candidate code, dependency, web bundle, Cubism runtime, model, or asset is copied. The audit also
records that the pinned frontend has a separate license with additional commercial-use conditions,
while the backend is MIT and its Live2D samples are separately governed. Adoption stays deferred
through the announced v2 rewrite unless an official output-only boundary appears.

## Verification Standard

- Run tests through `scripts/run_tests.sh`.
- Exercise plugins through real discovery against a temporary `HERMES_HOME`.
- Preserve prompt-cache stability and profile scope.
- Keep upstream Hermes behavior unchanged when the personal plugin is disabled.
- Add behavior-contract tests, not source-shape or catalog-count snapshots.
