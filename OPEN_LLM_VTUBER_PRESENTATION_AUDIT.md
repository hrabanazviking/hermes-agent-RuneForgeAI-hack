# Open-LLM-VTuber Presentation Boundary Audit

Audit date: 2026-09-22

Audited official backend tree: `Open-LLM-VTuber/Open-LLM-VTuber` `main`
[`992309c0aa19845960228f880013d4685fde93b5`](https://github.com/Open-LLM-VTuber/Open-LLM-VTuber/commit/992309c0aa19845960228f880013d4685fde93b5),
latest published tag `v1.2.1`.

Audited pinned web build: `Open-LLM-VTuber/Open-LLM-VTuber-Web`
[`06a659b114fff788cf0daaa86e484576db4975bf`](https://github.com/Open-LLM-VTuber/Open-LLM-VTuber-Web/commit/06a659b114fff788cf0daaa86e484576db4975bf),
built from source commit
[`3d57a9a0125a0ca13e5d096f7092e4e494ed389e`](https://github.com/Open-LLM-VTuber/Open-LLM-VTuber-Web/commit/3d57a9a0125a0ca13e5d096f7092e4e494ed389e).

This audit asks whether the current official shell can consume RuneForgeAI's bounded avatar feed as
an external presentation-only process. The answer is no. Its rendering layer is useful evidence,
but the maintained application boundary owns input, conversation, configuration, and playback
coordination as one coupled protocol.

## Useful Presentation Surface

The official backend sends `type="audio"` messages containing:

- complete base64 WAV audio in `audio`;
- per-slice volume values and `slice_length`;
- subtitle identity in `display_text`;
- Live2D expression indexes or names in `actions.expressions`;
- a `forwarded` marker for group display.

The pinned frontend queues these messages, creates a WAV data URL, plays it through an `Audio`
element, starts the model's talk motion, drives its WAV lip-sync handler, selects the first explicit
expression, and updates subtitles/history. This independently confirms that complete WAV plus
explicit visual controls is a viable presentation payload.

That payload is not the RuneForge v1 or AIAvatarKit wire format. Open-LLM-VTuber uses `audio`,
`actions`, and `slice_length`; the existing RuneForge translator emits AIAvatarKit `chunk`
responses with `audio_data` and `avatar_control_request`. A future adapter would need an explicit,
versioned translation rather than field-name guessing.

## Blocking Runtime Ownership

The official `/client-ws` route is not an audio-injection or presentation endpoint:

1. The server clones a complete session context containing the configured ASR, TTS, VAD, agent,
   translation, tool, history, and Live2D services for every client.
2. Initial messages assign the character configuration and immediately send
   `control/start-mic`.
3. The frontend connection automatically requests backgrounds, configs, history, and creation of a
   new history record.
4. The frontend's `start-mic` handler starts `MicVAD`, which obtains browser microphone media and
   eventually sends `mic-audio-data` and `mic-audio-end` input messages.
5. Output completion is part of the conversation protocol: the backend sends
   `backend-synth-complete`, waits for `frontend-playback-complete`, and only then closes the turn.
6. Model loading depends on `set-model-and-conf` and backend-served Live2D paths; the player is not
   published as a standalone output-only client.

The separate `/tts-ws` route is also inadmissible. It accepts text, invokes the configured
Open-LLM-VTuber TTS engine, and returns generated file paths. Using it would duplicate Hermes TTS
and would not provide the presentation boundary under audit.

The frontend cannot connect directly to the RuneForge loopback feed. It sends application messages
as soon as the socket opens rather than the required single `ready` envelope, sends further client
messages during playback, provides no RuneForge bearer-header admission, and expects the
Open-LLM-VTuber message schema. Relaxing the feed to accept those behaviors would erase the
presentation-only invariant.

## Version and License Constraints

The current backend README says v2 is a complete rewrite in early discussion and planning while v1
receives bug fixes. RuneForgeAI therefore must not build a compatibility fork around undocumented
v1 internals while that boundary is changing.

The backend Python tree is MIT licensed, with Live2D sample data governed separately. The pinned
official web-client repository uses `Open-LLM-VTuber License 1.0`: an Apache-2.0-based grant with
additional commercial-use conditions. It is not simply covered by the backend's MIT license.
RuneForgeAI imports none of the backend, frontend, Cubism runtime, models, or sample assets.

## Decision

Open-LLM-VTuber remains a presentation-design reference, not an adopted RuneForgeAI shell.
RuneForgeAI will not:

- launch its backend or route Hermes turns through its agent, ASR, TTS, VAD, tools, or history;
- patch its frontend to suppress microphone and protocol messages;
- copy its playback hooks, generated web bundle, Live2D SDK, models, or assets;
- weaken the RuneForge readiness, authentication, or post-readiness input rules;
- claim that manual event delivery controls a real avatar.

Direct adoption can be reconsidered only if an official maintained release exposes a documented
output-only client or presentation API with caller-supplied complete audio, explicit expressions,
no microphone/VAD/conversation/history ownership, bounded authentication, deterministic
interrupt/final cleanup, and compatible licensing.

## Next Safe Direction

The official AIAvatarKit and Open-LLM-VTuber clients now exhaust the audited shell candidates. Both
validate the complete-WAV presentation design; neither currently satisfies the output-only
admission contract. The next clean slice should consolidate this as a versioned avatar-shell
admission gate. It must keep the manual provider-free fixture truthful and leave automatic native
Hermes voice attachment deferred until a real admitted consumer exists.
