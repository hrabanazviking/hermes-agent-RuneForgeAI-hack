# Avatar Loopback Transport Audit

Audit date: 2026-09-22

This audit selects a future delivery surface for `runeforge.avatar.presentation.v1`. It does not
start a listener, register a Hermes hook or tool, or grant live avatar authority.

## Decision

RuneForgeAI may expose one outbound, presentation-only WebSocket feed on the literal IPv4 loopback
address. A shell connects as a consumer and receives the AIAvatarKit-compatible responses already
produced by `volmarr-voice`. The bridge never accepts microphone data, text prompts, pipeline
requests, tools, memory, or avatar asset commands.

```text
Hermes-owned turn/TTS
        │ canonical v1 event
        ▼
transaction router
        │ AIAvatarKit-compatible response JSON
        ▼
ws://127.0.0.1:<operator-port>/v1/presentation
        │ outbound only
        ▼
presentation-only shell
```

Hermes already pins `websockets==15.0.1`, so a future helper can use an existing core dependency.
No FastAPI/Uvicorn service or candidate-project dependency is needed for this boundary.

## Listener and Consumer Contract

- Bind exactly `127.0.0.1`; reject wildcard, hostname, non-loopback, forwarded-host, and remote
  binding. IPv6 support is deferred rather than assuming dual-stack safety.
- Use path `/v1/presentation`. The chosen session is established in a bounded first message, not in
  the URL, query string, cookie, or log-prone command line.
- Admit one authenticated consumer for a session. A second connection does not silently replace the
  first; replacement requires deterministic disconnect cleanup.
- The first client message is a small `ready` envelope containing only the contract version and an
  opaque session ID. After readiness, client data messages are forbidden. Microphone `data`,
  `invoke`, `config`, text, files, and audio uploads close the connection.
- Server output is JSON text using the proven AIAvatarKit response translation. Complete-WAV audio
  remains base64 in a `chunk`; `stop` and `final` remain audio-free.
- Each WebSocket write is serialized. A replacement transaction sends its interruption before new
  audio. The router re-checks active ownership immediately before every write.
- There is no offline replay, durable queue, best-effort fallback, or retry into a later session.
  Disconnect drops unsent presentation data and cannot change Hermes turn state.
- Bound handshake time, inbound message size, outbound event size, connection count, and close time.
  Normal ping/pong liveness is transport maintenance, not an entity heartbeat.

## Authentication

The future listener requires `Authorization: Bearer <token>` on the WebSocket upgrade. The token:

- comes only from the process environment variable `VOLMARR_AVATAR_TOKEN`, populated through the
  operator's `.env` workflow;
- is never stored in YAML, a URL, query parameter, cookie, WebSocket subprotocol, event, response,
  log, error, or repository file;
- must be non-empty and sufficiently strong before the listener can bind;
- is compared in constant time and is redacted through the existing exact-value redaction path
  before service startup;
- grants presentation consumption only, not Hermes APIs, voice input, tools, memory, or shell
  control.

Version 1 accepts native clients that can set an Authorization header. Browser ticket exchange and
subprotocol authentication are deferred. Rejecting browser `Origin` requests prevents accidental
cross-site WebSocket access instead of weakening the bearer boundary for the stock browser demo.
Loopback binding reduces exposure but does not replace authentication.

## AIAvatarKit Compatibility Result

The official AIAvatarKit tree at
[`38b617b8b9269939734e70ef503d7ea6976acdbd`](https://github.com/uezo/aiavatarkit/commit/38b617b8b9269939734e70ef503d7ea6976acdbd)
uses the same response fields consumed by this feed. Its current public server, however, owns a full
STS pipeline, and its maintained WebSocket client starts microphone capture. A future integration
must therefore be a small presentation-only consumer mode or wrapper around its response handling,
not the stock server and not `start_listening()`.

## Admission Gate for Live Work

A live listener remains forbidden until focused tests prove all of the following:

1. literal-loopback-only bind validation and refusal before socket creation;
2. missing, weak, incorrect, or exposed token refusal before session admission;
3. bounded `ready` parsing and rejection of every input-bearing AIAvatarKit request type;
4. one-consumer ownership, serialized writes, A→B interruption ordering, and stale suppression;
5. disconnect/cancellation cleanup with no replay into a later session;
6. credential absence from output, logs, errors, process arguments, and event metadata;
7. real loopback delivery to a presentation-only fixture with no microphone, provider, or avatar
   process.

Until this gate passes, `volmarr-voice` remains an I/O-free producer, translator, and transaction
router.

Slice 73 implements only the pre-socket portion of this gate in `volmarr-voice.admission`: literal
target validation, strong environment-token loading with profile-scoped exact-value redaction,
constant-time bearer comparison, and exact bounded `ready` parsing. These validators do not import
or call `websockets` and cannot create a listener.
