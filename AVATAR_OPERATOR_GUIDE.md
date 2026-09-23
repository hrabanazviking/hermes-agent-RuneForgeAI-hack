# Avatar Presentation Operator Guide

This guide covers the manual RuneForgeAI avatar presentation feed. It does not claim automatic
attachment to Hermes CLI voice, GPT-Live, messaging voice, or native playback.

## Prerequisites

1. Enable `volmarr-voice` for the active Hermes profile.
2. Put a strong random `VOLMARR_AVATAR_TOKEN` in the operator-managed `.env`. Do not place the
   value in YAML, a command argument, a URL, a query string, or this repository.
3. Use a native presentation-only consumer that can set an Authorization header and consume
   AIAvatarKit-compatible response JSON without starting microphone capture, STT, an LLM, or TTS.

The stock AIAvatarKit `start_listening()` client is not suitable because it starts microphone
capture. Its `/avatar/perform` endpoint is also not suitable because it invokes AIAvatarKit TTS.
The exact client findings are recorded in `AIAVATARKIT_PRESENTATION_CONSUMER_AUDIT.md`.

## Inspect the Gate

```powershell
hermes volmarr-voice status --json
```

The result should report contract `runeforge.avatar.presentation.v1`, operator serving enabled,
no running listener, and automatic voice mirroring unavailable. Status never loads the token or
creates a socket.

## Start the Feed

```powershell
hermes volmarr-voice serve --port 8765
```

The command binds only `ws://127.0.0.1:8765/v1/presentation` and waits for canonical event lines on
stdin. It prints bounded lifecycle status to stderr. Stop it with EOF or Ctrl-C.

The presentation consumer connects with:

- header `Authorization: Bearer <the value from .env>`;
- no browser `Origin` header;
- first message:

```json
{"type":"ready","contract":"runeforge.avatar.presentation.v1","session_id":"avatar-session"}
```

After `connected`, the consumer sends nothing else. It only receives `chunk`, `stop`, and `final`
responses.

## Encode One Complete WAV

In a separate operator shell:

```powershell
hermes volmarr-voice encode `
  --audio C:\path\to\spoken.wav `
  --session avatar-session `
  --transaction turn-001 `
  --face joy `
  --animation wave_hands
```

The command writes exactly one canonical JSON line to stdout. It never writes the source path into
the event and never reads the avatar bearer. Copy that complete line into the already-running feed's
stdin only after the consumer has received `connected`.

Do not use a naïve `encode | serve` pipeline: the event may arrive before the presentation consumer
owns the session, and the feed correctly refuses rather than queues it. For automation, supply a
producer that keeps stdin open and writes only after consumer readiness; do not add an unauthenticated
producer socket, watched directory, or replay file.

Subsequent events for the same transaction increment `sequence` by exactly one. A new transaction
begins at sequence zero and interrupts the prior transaction before its new audio. Send a canonical
`final` event to retire the transaction; the current encoder intentionally creates speech events
only.

## Repeatable Repository Smoke

The maintained smoke is the real-loopback contract, not a simulated protocol test:

```powershell
$env:HERMES_PYTHON='C:/Users/volma/AppData/Local/Programs/Python/Python311/python.exe'
& 'C:\Program Files\Git\bin\bash.exe' scripts/run_tests.sh `
  tests/plugins/test_volmarr_voice_cli_serve.py `
  tests/plugins/test_volmarr_voice_cli_encode.py
```

It proves missing-token refusal before socket creation, a real authenticated loopback connection,
stdin delivery of complete WAV audio, clean EOF shutdown, byte-exact encoding, and secret/audio-free
operator output.

## Current Boundary

- Hermes remains the sole voice-loop owner.
- The feed is operator-started and has no model-facing lifecycle tool.
- Audio is already synthesized before it enters the v1 event.
- No avatar assets, model weights, provider credentials, or candidate source are bundled.
- Automatic mirroring of native Hermes voice output remains deferred because current plugin hooks do
  not observe every direct TTS call.
