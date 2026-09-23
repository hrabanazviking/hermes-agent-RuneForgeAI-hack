# AIAvatarKit Presentation Consumer Audit

Audit date: 2026-09-22

Audited official tree: `uezo/aiavatarkit` `main`
[`38b617b8b9269939734e70ef503d7ea6976acdbd`](https://github.com/uezo/aiavatarkit/commit/38b617b8b9269939734e70ef503d7ea6976acdbd)

This audit asks whether an official maintained AIAvatarKit client can consume the RuneForge avatar
feed without also taking microphone or voice-loop ownership. The current answer is no.

## Compatible Output Surface

Both maintained clients already understand the response fields emitted by RuneForgeAI:

- base64 complete-WAV `audio_data` on `type="chunk"`;
- `avatar_control_request.face_name` and `face_duration`;
- `avatar_control_request.animation_name` and `animation_duration`;
- `stop` and `final` lifecycle messages.

The Python client decodes chunk audio, dispatches face/animation controllers, and plays complete WAV
responses. The browser client queues `start`/`chunk` messages, applies face and animation controls,
and decodes/plays response audio. This confirms that the RuneForge response translation is grounded
in a real maintained consumer shape.

## Blocking Input Ownership

The Python path is not output-only:

1. `AIAvatarClientBase.__init__` constructs an `AudioDevice`, `AudioRecorder`, and `AudioPlayer`.
2. `AIAvatarWebSocketClient.start_listening` schedules `send_microphone_worker` alongside the
   response workers.
3. Initialization sends AIAvatarKit's `type="start"` request rather than the presentation-only v1
   `ready` envelope.
4. Shutdown sends a client `stop` request, while the RuneForge consumer is forbidden from sending
   anything after readiness.

The browser path is also not output-only:

1. `startListening` authenticates through an `Authorization.<base64>` WebSocket subprotocol rather
   than a bearer header.
2. It sends `type="start"` rather than `ready`.
3. It immediately calls `navigator.mediaDevices.getUserMedia`.
4. Its audio process sends continuous `type="data"` microphone frames, including silent frames
   while muted.
5. A browser connection carries an Origin header, which the v1 native-client feed rejects.

Muted mode is therefore not presentation-only mode: it still owns capture infrastructure and sends
input frames.

## Decision

RuneForgeAI does not install AIAvatarKit as a runtime dependency and does not subclass or monkey-
patch these clients. A subclass would still execute the base constructor's input-device setup, and
overriding startup/shutdown/protocol behavior would amount to maintaining a forked client contract
inside the Hermes plugin.

The official project becomes directly adoptable only when it provides an output-only client mode
with all of these properties:

- no input-device enumeration or `AudioRecorder` construction;
- no microphone permission, capture worker, silent-frame transmission, or echo-cancellation state;
- caller-selectable initial readiness envelope;
- bearer-header authentication for a native client, or a separately audited browser-ticket design;
- receive/playback/controller reuse without STT, LLM, TTS, memory, tools, or conversation state;
- deterministic response-task cancellation and output-device cleanup.

Until then, RuneForgeAI's provider-free presentation fixture is the only admitted consumer. It
proves the wire contract but is not an avatar product shell.

## Next Safe Direction

No source, dependency, sample avatar, or controller code is copied by this audit. The next clean
slice may either:

1. re-audit a newer official AIAvatarKit release for output-only support; or
2. audit another maintained shell's external presentation API without importing its duplicate
   ASR/LLM/TTS/history stack.

Building a new avatar renderer inside Hermes is outside the plugin boundary.
