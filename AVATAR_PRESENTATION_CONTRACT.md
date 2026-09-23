# Avatar Presentation Contract

Contract version: `runeforge.avatar.presentation.v1`

Audit date: 2026-09-22

This contract defines the smallest boundary between Hermes-owned speech and an optional avatar
shell. Hermes remains the sole owner of capture, VAD, transcription, turn execution, synthesis,
barge-in, and playback policy. A presentation adapter may receive completed audio and explicit
visual controls; it must not start another conversational or voice pipeline.

## Boundary

```text
Hermes turn + Hermes TTS
          │
          ├── speech event: WAV bytes + optional face/animation
          ├── stop event: interrupt the current presentation
          └── final event: close the presentation transaction
                                      │
                                      ▼
                              optional avatar shell
```

The v1 event envelope is transport-neutral JSON:

```json
{
  "contract": "runeforge.avatar.presentation.v1",
  "kind": "speech",
  "session_id": "opaque-session-id",
  "transaction_id": "opaque-turn-id",
  "sequence": 0,
  "audio": {
    "encoding": "base64",
    "container": "wav",
    "data": "UklGR...",
    "sha256": "lowercase-hex-digest"
  },
  "expression": {
    "face_name": "joy",
    "face_duration_seconds": 4.0,
    "animation_name": "wave_hands",
    "animation_duration_seconds": 4.0
  }
}
```

`speech` requires a complete valid WAV payload. `stop` and `final` omit `audio` and `expression`.
Every event carries the same opaque session and transaction identifiers, and `sequence` increases
within a transaction. A newer transaction invalidates unsent or queued events from the older one.
Names select shell-owned visuals; they never grant script, path, URL, or arbitrary command
execution.

## Ownership and Safety Rules

- The adapter accepts already-synthesized audio only. It never invokes STT, an LLM, TTS, memory,
  tools, or conversation history.
- The adapter does not open a microphone or speaker and does not decide barge-in policy. It only
  forwards `speech`, `stop`, and `final` events to a configured presentation consumer.
- Audio is carried as bytes, not as a host filesystem path. A receiver validates the WAV container,
  decoded-size bound, and SHA-256 digest before use.
- Face and animation are explicit fields. Control markup is not inserted into model text or spoken
  text.
- Session and transaction identifiers are routing tokens, not identity or conversation ownership.
- No credential appears in an event. Transport authentication stays outside this payload.
- Delivery failure cannot replay a turn, change Hermes state, or fall back to a second voice engine.

## AIAvatarKit Adaptation

The official AIAvatarKit `main` tree at
[`38b617b8b9269939734e70ef503d7ea6976acdbd`](https://github.com/uezo/aiavatarkit/commit/38b617b8b9269939734e70ef503d7ea6976acdbd)
already defines the presentation-side fields needed by v1. A bounded adapter can translate:

| RuneForge event | AIAvatarKit `AIAvatarResponse` |
|---|---|
| `speech` | `type="chunk"`, base64 complete-WAV `audio_data`, matching `session_id`, and explicit `avatar_control_request` |
| `stop` | `type="stop"` with matching `session_id` |
| `final` | `type="final"` with matching `session_id` |
| `expression.face_name` | `avatar_control_request.face_name` |
| `expression.face_duration_seconds` | `avatar_control_request.face_duration` |
| `expression.animation_name` | `avatar_control_request.animation_name` |
| `expression.animation_duration_seconds` | `avatar_control_request.animation_duration` |

Complete-WAV mode is the minimal compatible audio form. AIAvatarKit's alternative streamed-PCM
mode needs a separate format announcement and chunk sequence, so it is outside v1.

The current public `POST /avatar/perform` route is not this boundary: it accepts text and invokes
AIAvatarKit's configured TTS before emitting avatar output. The stock WebSocket client also starts
microphone capture. RuneForgeAI therefore does not call that route or adopt that client as-is.
Integration requires a presentation-only adapter or client mode that consumes the mapped response
events while leaving capture and synthesis disabled.

## Explicit Non-Goals

Version 1 does not define microphone input, transcript or caption transport, visemes, streamed PCM,
emotion inference, expression selection, avatar asset loading, shell installation, network
discovery, durable queues, or retry policy. Those capabilities require separate evidence and
ownership decisions.

