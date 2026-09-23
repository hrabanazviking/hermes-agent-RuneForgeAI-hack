# Avatar Feed Orchestration Audit

Audit date: 2026-09-22

This audit decides who may start the avatar feed and how presentation events may enter it. The
answer is the human operator. No model-facing tool or lifecycle hook may start, stop, bind, or
reconfigure the service.

## Existing Hermes Seam Result

Hermes' `post_tool_call` plugin observer sees successful `text_to_speech` calls dispatched as model
tools. It is not a universal TTS-completion seam. CLI voice playback and the native voice loop call
`text_to_speech_tool` directly, consume its result, play the files, and then clean temporary files
without emitting that observer.

A plugin hook based only on `post_tool_call` would therefore mirror some model-requested speech but
silently miss normal voice replies. RuneForgeAI will not present that partial behavior as native
avatar integration. Adding a new core hook is also outside the plugin-only boundary.

## Operator-Owned Command

The next allowable runtime surface is an explicit plugin CLI command:

```text
hermes volmarr-voice serve --port <unprivileged-port>
```

The command:

- is invoked and stopped by the operator; it is never run during plugin discovery, session start,
  an LLM tool call, cron, or background routine;
- binds the already-fixed `127.0.0.1` host and `/v1/presentation` path, with no host override;
- reads `VOLMARR_AVATAR_TOKEN` only from the process environment populated through `.env`; there is
  no token flag, config field, stdin token, prompt, or generated credential;
- starts one `AvatarLoopbackFeed`, consumes canonical v1 events as newline-delimited JSON from
  standard input, and stops cleanly on EOF, Ctrl-C, or feed failure;
- accepts no text-to-speech request, text prompt, provider choice, model choice, microphone data,
  expression inference, filesystem path, URL, avatar asset command, or Hermes conversation state;
- validates each line through the canonical event validator before routing it; malformed input
  fails closed without echoing the input;
- emits only bounded status/error summaries to stderr and never prints event audio, tokens, or
  Authorization values;
- has no durable queue or replay. Events received before a consumer is ready or after disconnect
  fail rather than being retained for a later session.

Standard input keeps producer authority local and explicit. It does not create a second producer
socket, unauthenticated HTTP control route, watched directory, clipboard monitor, or profile store.

## Deliberately Deferred Automation

Automatic mirroring of every Hermes voice reply remains unavailable until Hermes exposes a generic
plugin observer after successful TTS delivery files are finalized and before native cleanup. Such a
surface would need bounded path/byte access, call-time profile and session identifiers, outcome and
interruption semantics, and observer-only behavior. RuneForgeAI will consume that surface if it
arrives upstream; it will not patch core or monkey-patch `text_to_speech_tool` to manufacture it.

The operator CLI and stdin contract can still support integration tests, presentation development,
and explicit pipelines. They do not claim that the avatar is attached to all Hermes voice modes.

## Verification Gate

Before registering the command, tests must prove:

1. discovery registers only the operator CLI and no model tool or lifecycle hook;
2. help and invalid arguments do not load the token or bind a socket;
3. serve loads the token only at execution time and refuses absent/weak tokens before bind;
4. one canonical stdin event reaches a real authenticated loopback consumer;
5. malformed/oversize/non-canonical lines fail without echo or partial delivery;
6. EOF, Ctrl-C, client disconnect, and publish failure all close the listener and release sessions;
7. no credential, audio base64, or event content appears in stdout, stderr, logs, argv, or config.

Slice 76 registers only `hermes volmarr-voice status`. The command truthfully reports that serving
and automatic voice mirroring remain disabled. `serve` is not yet a parseable action, and status
imports no admission or loopback module, loads no token, and creates no socket.
