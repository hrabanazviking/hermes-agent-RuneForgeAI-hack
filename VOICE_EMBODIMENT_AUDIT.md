# Voice and Embodiment Candidate Audit

Audit date: 2026-09-22

This record answers one architectural question: which current official project, if any, should own
Volmarr's voice loop? The answer is Hermes. External projects remain bounded candidates for a
specific missing output capability, not replacement minds, conversation stores, or voice
orchestrators.

## Verified Baseline

The official Hermes `main` head was
[`d3b25b52ad1318c526bdb259b600eeca3d5f38e6`](https://github.com/NousResearch/hermes-agent/commit/d3b25b52ad1318c526bdb259b600eeca3d5f38e6)
at audit time. That tree still provides chained and GPT-Live modes, microphone capture, VAD,
provider-selectable STT/TTS, streaming playback, client-direct or relay resolution, wake word, and
full-duplex barge-in. The personal fork's `voice_pipeline_readiness` adapter uses the same owned
configuration and requirement surfaces without operating them.

## Candidate Matrix

| Candidate | Verified official state | Useful unique surface | Decision |
|---|---|---|---|
| [AIAvatarKit](https://github.com/uezo/aiavatarkit) | `main` [`38b617b8b9269939734e70ef503d7ea6976acdbd`](https://github.com/uezo/aiavatarkit/commit/38b617b8b9269939734e70ef503d7ea6976acdbd), latest tag `v0.9.0`, Apache-2.0 | Streaming avatar/channel adapters, expression and animation output, metaverse/device surfaces | Do not adopt its complete VAD→STT→LLM→TTS pipeline. Revisit only as an out-of-process presentation/channel adapter after an exact protocol audit. |
| [Open-LLM-VTuber](https://github.com/Open-LLM-VTuber/Open-LLM-VTuber) | `main` [`992309c0aa19845960228f880013d4685fde93b5`](https://github.com/Open-LLM-VTuber/Open-LLM-VTuber/commit/992309c0aa19845960228f880013d4685fde93b5), latest tag `v1.2.1`; MIT backend, separately governed Live2D samples, and pinned web client with additional commercial-use license conditions | Live2D web/Electron shell, expressions, subtitles, pet mode, touch and screen presentation | Do not bind: the current client/server protocol owns microphone/VAD, agent, TTS, history, configuration, and playback acknowledgements, and the project is planning a v2 rewrite. Revisit only if an official output-only boundary appears. |
| [OmniVoice](https://github.com/k2-fsa/OmniVoice) | official `master` [`08be0b4ccbac3e13e374e86fbfead4b4cac343e2`](https://github.com/k2-fsa/OmniVoice/commit/08be0b4ccbac3e13e374e86fbfead4b4cac343e2), latest tag `0.2.1`, Apache-2.0 code | Optional local multilingual TTS, voice design, and consented reference-voice synthesis | Possible future Hermes TTS provider only. Require a separate model-weight/license, VRAM/latency, output-format, and voice-consent audit before installation or inference. |

## Fork Freshness Rule

The roadmap link `hrabanazviking/OmniVoice` resolved to `a4068c820f21307df337e34f67d3dda443735ad4`
(`0.1.3`). Git history proved that commit is an ancestor of the official head and that the official
repository is 50 commits ahead with no fork-only commits. Any future OmniVoice work must therefore
start from `k2-fsa/OmniVoice`, then compare the personal fork explicitly rather than assuming it is
current.

## Boundary Decision

```text
Hermes owns capture → VAD → STT → turn → TTS → playback
                               │
                               └── bounded expression/audio events → optional avatar shell
```

No candidate source, model, sample avatar, or dependency is copied by this audit. Slice 67 adds a
synthetic, provider-free regression contract proving that Hermes' existing STT and TTS plugin
dispatch can complete a loop without network, microphone, speaker, credentials, or model downloads.

## Presentation Protocol Result

The exact AIAvatarKit audit is recorded in `AVATAR_PRESENTATION_CONTRACT.md`. Its outbound
`AIAvatarResponse` supports complete-WAV `chunk` events and explicit face/animation fields, which
are sufficient for a presentation-only adapter. Its public `/avatar/perform` control route is not a
safe Hermes boundary because it synthesizes supplied text through AIAvatarKit TTS, and its stock
WebSocket client starts microphone capture. RuneForgeAI therefore defines the narrow response
mapping but imports and invokes nothing until a presentation-only consumer can honor it.

The follow-up `AIAVATARKIT_PRESENTATION_CONSUMER_AUDIT.md` confirms that both maintained clients
currently combine compatible output handling with mandatory input ownership. Direct adoption stays
deferred until an official output-only mode exists.

`OPEN_LLM_VTUBER_PRESENTATION_AUDIT.md` reaches the same boundary for the remaining shell
candidate. Its pinned web player confirms complete-WAV lip sync and explicit expression handling,
but the application protocol starts microphone/VAD, creates conversation history, expects backend
model/configuration state, and acknowledges synthesis completion. Its `/tts-ws` route invokes
duplicate TTS rather than accepting completed Hermes audio for presentation. No maintained
output-only client or injection API exists at the audited revisions, so adoption remains deferred.
