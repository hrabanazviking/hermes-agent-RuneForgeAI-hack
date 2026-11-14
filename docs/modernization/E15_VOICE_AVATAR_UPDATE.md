# E.15 Voice + avatar adapter update - audit record (Team 01, 2026-11-14)

**Outcome: PINS UNMOVED - audit executed, output-only boundary
re-proved live.** All three ledger rows are audited in one
slice. AIAvatarKit (row 17) and OmniVoice (row 19) stand
current at their E0 first pins, both Apache-2.0 licenses now
verified at text level. Open-LLM-VTuber (row 18) is
re-evaluated and KEPT reference-only with no pin taken; its
GitHub API NOASSERTION is resolved at text level - the root
LICENSE is MIT, with Live2D sample data under separate
Live2D terms. The fork surface is unchanged: the
`volmarr-voice 1.0.0` plugin. Its AIAvatarKit path is pure
presentation-shape translation and invokes NO engine
pipeline; its OmniVoice classification stays design-only -
no OmniVoice code reference exists in the fork. No engine
source was copied into the fork.

## Targets (re-measured, not inherited)

- Row 17 AIAvatarKit (`hrabanazviking/aiavatarkit`): first
  pin at E0 `9295e096169316ec19e9fa712e52733d912fd5e7`.
  Re-measurement this slice: `git ls-remote` HEAD ==
  `refs/heads/main` (the default branch) == the pin; the
  repo carries no tags. Tree staged directly under $HOME
  at `~/aiavatarkit-e15`, HEAD verified at the pin,
  working tree clean. COMPONENT_LICENSES.md carried no
  AIAvatarKit row before this slice; the row is added
  here.
- Row 18 Open-LLM-VTuber (`hrabanazviking/Open-LLM-VTuber`):
  audit HEAD recorded at E0
  `19b58b1f6c01e082289fce089392997b9d14fbc4`, NO pin taken
  (no admissible embed). Re-measurement: `git ls-remote`
  HEAD == `refs/heads/main` == the recorded audit HEAD;
  the fork carries no tags (the tree's `pyproject.toml`
  reads version 1.2.1). Tree staged at `~/vtuber-e15`,
  HEAD verified.
- Row 19 OmniVoice (`hrabanazviking/OmniVoice`): first
  pin at E0 `a4068c820f21307df337e34f67d3dda443735ad4`.
  Re-measurement: `git ls-remote` HEAD ==
  `refs/heads/master` (the default branch) == the pin;
  no tags. Tree staged at `~/omnivoice-e15`, HEAD verified
  at the pin, working tree clean. COMPONENT_LICENSES.md
  carried no OmniVoice row before this slice; the row is
  added here (a VTuber component row is added as well, as
  an identification record - no material incorporated).

## Licenses - text-level verification (all three rows)

- AIAvatarKit: **Apache-2.0 - PASS, verified at text
  level.** The `LICENSE` at the pin carries sha256
  `134fb4c3dd13d5dca9838ada1e9b32d82ad9dedf488c4b2ad7d747ef301b3775`.
  Its body is byte-identical to the canonical Apache-2.0
  text verified in E.09/E.14 (sha256 cfc7749b96f6) except
  the appendix copyright line, which is filled in as
  `Copyright (c) 2023 uezo`, and a leading blank line the
  canonical copy carries. A filled appendix is the
  license's own intended use, not a conflict.
  `setup.py` declares `license="Apache v2"` - in
  agreement; NO E.14-style metadata conflict. One nested
  component carries its own license:
  `examples/websocket/html/motionpngtuber/LICENSE` is MIT
  (Copyright (c) 2026 rotejin, sha256
  `1e44487355a882476455ff9c0df81e6aaa1c58281e9b5e8fcfff3f0c2ea5489d`),
  recorded per component (ticket E15-T4).
- Open-LLM-VTuber: **NOASSERTION RESOLVED at text level.**
  The root `LICENSE` at the recorded HEAD is MIT,
  sha256 `c48a8498e88fbb1e6da5438f19e919e6eb926cd7d25372b2ed35ff92b2631bd1`,
  Copyright (c) 2025 Yi-Ting Chiu, the standard MIT grant
  text. `LICENSE-Live2D.md` (sha256
  `5e2b759bba52c9d01bc79fcd3ea589aa0a7d50e4f6010a62185309947b657371`)
  carries the separate Terms of Use for Live2D Cubism
  Sample Data; the README's Third-Party Licenses section
  states the Live2D sample models are NOT covered by the
  project's MIT license. `pyproject.toml` carries no
  license field. Per-component record: backend/code MIT;
  Live2D sample data under Live2D terms. The fork imports
  none of it, so no reliance arises either way.
- OmniVoice: **Apache-2.0 - PASS, verified at text
  level.** The `LICENSE` at the pin carries sha256
  `c843a20ede4d1e7595c2736b88fc62cb7483a8c082eb7092a3772248849c59e2`.
  Its body is byte-identical to the canonical Apache-2.0
  text except the filled appendix line `Copyright 2026
  Xiaomi Corp.` `pyproject.toml` declares
  `license = "Apache-2.0"` - in agreement; no metadata
  conflict. Before this slice both Apache rows rested on
  the GitHub API reading alone; both are now verified at
  text level.

## Proof 1 - engine own suites at the pins: PARTIAL, blockers named honestly

- AIAvatarKit: the engine carries a real suite
  (`tests/`, 523 tests collected in the collectable
  remainder). It was run in a dedicated venv under $HOME
  (`~/aiavatarkit-e15-venv`, deps installed with uv:
  pytest, httpx, openai, aiofiles, numpy, silero-vad,
  pytest-asyncio, websockets, asyncpg, litellm,
  pyautogui). Full run: collection INTERRUPTED - first
  22 errors, then, after the light deps landed, 10
  errors in 10 files (log `~/team01-e15-engine-suite.log`):
  `pyaudio` unbuildable on this host (the build fails
  for want of `portaudio.h`; only the runtime library is
  installed), 3 GUI test files raising `KeyError:
  'DISPLAY'` via pyautogui, `tests/character/test_loader.py`
  requiring a `CHARACTER_DIR` environment fixture, and
  five provider-SDK files (anthropic, google, azure,
  amazon_transcribe, fastmcp) whose SDKs are not
  installed. The collectable remainder (523 tests, log
  `~/team01-e15-engine-suite2.log`): **180 passed / 186
  failed / 65 skipped / 92 errors**. The failures are
  environment-bound, not engine-logic verdicts: 162+
  raise missing OpenAI/litellm credentials, 28+ fail
  PostgreSQL password authentication (no local Postgres
  with the expected credentials), the Silero VAD tests
  error on model initialization, and a block fails on
  pytest stdin capture. No API keys, database, or audio
  stack were fabricated to force a green run (ticket
  E15-T1).
- OmniVoice: the tree at the pin carries NO test suite
  (no test files anywhere in the tree) - there is
  nothing to execute; recorded, not worked around
  (ticket E15-T2).
- Open-LLM-VTuber: the tree at the recorded HEAD
  likewise carries NO test suite. Nothing executed;
  the row is reference-only in any case.

## Proof 2 - fork voice + ledger contracts before the edits: PASS with the one known failure

- `scripts/run_tests.sh` on the ten `test_volmarr_voice*.py`
  files plus `test_volmarr_integration_ledger.py` on the
  pre-edit team tree (at banked main `ec5d5889a2`):
  **11 files, 36 tests passed / 1 failed** (log
  `~/team01-e15-baseline.log`, serialized baseline
  waiter). The single failure is
  `test_volmarr_voice_runner.py::test_real_loopback_runner_delivers_canonical_stdin_event_then_eof`,
  one of the seven known live-transport failures of the
  banked baseline - expected here, not a regression.

## Proof 3 - live boundary proofs for volmarr-voice: PASS

- Live harness (script `~/team01-e15-live.py`, full
  result `~/team01-e15-live-result.json`) loads
  `volmarr-voice` through the real plugin discovery path
  (PluginManager, the same road the contract tests use)
  with a poisoned `aiavatar` module planted in
  `sys.modules` - any touch of the engine package would
  raise. None did: the planted blocker is still the
  module object after every call.
- Speech translation: a canonical speech event (160-frame
  WAV, face `joy`, animation `wave_hands`) translates to
  the AIAvatarKit presentation shape: type `chunk`,
  session `avatar-session`, response keys exactly
  {audio_data, avatar_control_request, metadata,
  session_id, type}, controls {face_name: joy,
  face_duration: 4.0, animation_name: wave_hands,
  animation_duration: 4.0}, metadata keys exactly
  {audio_sha256, runeforge_contract, sequence,
  transaction_id}; the embedded audio decodes as a
  160-frame WAV. Response sha256
  `2392e4cb65f0ed1041b7efcffd08ee5918ddb24bdae0f9daa4a988608cd119c3`.
- Control mapping: `stop` -> type `stop` (sha256
  `7f1ad00a6198f5577109a1c3fddd7a62b5e4abfea003e49901478b2f0081d27d`),
  `final` -> type `final` (sha256
  `16e42ba5011e96cf5f7a662d3e96621a944e787f6a8958ea3901768ab77195c1`);
  neither carries audio or avatar controls.
- Determinism: every translation and the readiness call
  were run twice and asserted byte-identical.
- Tamper refusal: an event carrying an unexpected `text`
  field is refused with `PresentationContractError` -
  the boundary accepts canonical presentation events
  only.
- No-pipeline evidence: `aiavatarkit.py` imports only
  `typing` and `.presentation.validate_presentation_event`;
  its source contains no `subprocess` and no `socket`.
  The adapter has no engine-root configuration at all:
  it runs identically with no AIAvatarKit checkout
  present, which is the truthful absent-engine behavior
  for a pure translator - there is no engine call that
  could fail or be faked.
- OmniVoice boundary: a fresh grep of
  `plugins/volmarr-voice/*.py` this slice found ZERO
  OmniVoice references (the W08 promotion grep result
  stands). The plugin's `voice_pipeline_readiness`
  handler is Hermes-native (source engine "Hermes
  Agent"): against an empty profile it returns success
  with mode `chained`, `end_to_end_verified` false,
  `provider_contacted` false, `microphone_opened` false,
  `speech_synthesized` false - readiness/presentation
  contracts only, honestly not end-to-end (response
  sha256 `5425be96cbf3bc58002a04c00610249b9832c75ca5fba7199851c2aa1f3b7edb`).
  Called with arguments it refuses truthfully:
  "voice_pipeline_readiness accepts no arguments".
- Open-LLM-VTuber boundary: no adapter exists and none
  was built; the 2026-09-22 presentation audit's
  blocking findings (its `/client-ws` owns ASR/TTS/agent
  loops per session; it is not an output-only endpoint)
  stand unchanged at this HEAD.

## Proof 4 - fork targeted batteries after the edits: PASS

- Same eleven files as Proof 2, after the ledger edits
  (log `~/team01-e15-targeted.log`, serialized gate
  waiter): **11 files, 36 tests passed / 1 failed** - the
  one failure is again the known voice-runner
  live-transport test. The ledger battery now carries
  the three new pin-guard assertions (AIAvatarKit
  `9295e096169316ec19e9fa712e52733d912fd5e7`, OmniVoice
  `a4068c820f21307df337e34f67d3dda443735ad4`, and the
  Open-LLM-VTuber audit baseline
  `19b58b1f6c01e082289fce089392997b9d14fbc4`) inside the
  existing CLI test, so the test count is unchanged.

## Pin status

- Row 17 pin **unmoved**: `pinned` == `current_head` ==
  `9295e096169316ec19e9fa712e52733d912fd5e7` in
  integration-lock.json (license now Apache-2.0
  text-verified, pin_source COMPONENT_LICENSES.md,
  verdict "current - E.15 executed 2026-11-14",
  `update_needed` false), INTEGRATION_MATRIX.md row 17,
  the new COMPONENT_LICENSES.md row, and the new
  pin-guard assertion in
  `tests/plugins/test_volmarr_integration_ledger.py`.
- Row 19 pin **unmoved**: `pinned` == `current_head` ==
  `a4068c820f21307df337e34f67d3dda443735ad4`, same four
  records updated the same way.
- Row 18: **no pin taken** - by decision, not by
  omission. `pinned` continues to record the E0 audit
  HEAD `19b58b1f6c01e082289fce089392997b9d14fbc4` as the
  audit baseline (the ledger CLI pin-guard now asserts
  it as such); the lock records license MIT + Live2D
  terms (NOASSERTION resolved), `latest_tag` null (the
  fork carries no tags), `update_needed` false, verdict
  "reference-only - E.15 re-evaluated 2026-11-14, kept
  reference-only". Reasons: the application owns its
  own ASR/TTS/agent loops and offers no admissible
  output-only embed; building one would mean forking a
  v1 boundary its own README says is headed for a v2
  rewrite. A pin is PROPOSED (not taken) only for a
  future slice that builds a versioned presentation
  translation against a settled boundary (ticket
  E15-T3).
- Verification tally does not move: **25 verified / 0
  partially verified / 1 blocked (Sagnaskemma)** - all
  three rows were already counted verified; E.15 deepens
  their evidence (two license texts verified, one
  NOASSERTION resolved) without changing statuses.
- No adapter change: no fork code was modified in this
  slice. No CUSTOMIZATIONS.md row: ledger state only
  (E.03 / E.05-E.14 precedent).
- README.md untouched (sha256
  `336813d11bbe5aa2ff745b4a4bc3abcf2a283cd13971c0c11d061377129db7f3`
  before and after).

## Gate evidence - full fork contracts

Full fork contracts on the edited team tree via
scripts/run_tests.sh = 137 files, 1,171 passed / 7 failed
/ 1 skipped - exactly the banked baseline, the 7
name-identical to the known live-transport set (5
test_volmarr_core_plugin.py + 1
test_volmarr_verdandi_stimuli.py + 1
test_volmarr_voice_runner.py); ZERO regressions (log
`~/team01-e15-fullcontracts.log`, serialized gate waiter
`~/team01-e15-gate-waiter.sh`). Targeted batteries
(voice + integration ledger) 36 passed / 1 failed both
before the edits (`~/team01-e15-baseline.log`) and after
(`~/team01-e15-targeted.log`), the 1 being the known
voice-runner failure in both runs. Engine own suite
(AIAvatarKit): collection interrupted by named
environment blockers; collectable remainder 180 passed /
186 failed / 65 skipped / 92 errors, failures
environment-bound (E15-T1; logs
`~/team01-e15-engine-suite.log`,
`~/team01-e15-engine-suite2.log`). OmniVoice and
Open-LLM-VTuber carry no test suites at their pins.

## Honest remainders (named, not hidden)

- **E15-T1** (AIAvatarKit engine suite not fully runnable
  on this host): PyAudio cannot build (no `portaudio.h`
  - runtime library only), three GUI test files need a
  DISPLAY, one needs a `CHARACTER_DIR` fixture, five
  need optional provider SDKs (anthropic, google, azure,
  amazon_transcribe, fastmcp), and the collectable
  remainder's failures are dominated by missing provider
  credentials, absent PostgreSQL credentials, and Silero
  model initialization. A full engine-suite green run
  awaits a host provisioned with those dependencies and
  credentials; the fork's boundary proofs do not depend
  on it (the adapter invokes no engine code).
- **E15-T2** (OmniVoice has no engine suite): the pinned
  tree carries no tests at all, so engine currency for
  row 19 rests on ls-remote identity, license text, and
  the fork-side grep + readiness proofs. If the engine
  gains a suite, a future audit should execute it.
- **E15-T3** (Open-LLM-VTuber pin proposed, not taken):
  kept reference-only at E.15. Revisit only when a
  future slice builds a versioned presentation
  translation against a settled upstream boundary (the
  v2 rewrite its README announces), or Volmarr directs
  otherwise. No repo is created and no code is imported
  in the meantime.
- **E15-T4** (per-component licenses recorded):
  AIAvatarKit's nested `motionpngtuber` example is MIT
  inside an Apache-2.0 repo, and Open-LLM-VTuber's
  Live2D sample data sits under Live2D's own terms
  inside an MIT repo. Both are recorded in the lock,
  the matrix, and COMPONENT_LICENSES.md; neither is
  imported by the fork, so neither creates reliance -
  any future import must re-check the component license
  of the exact files taken.
- **E12-T2** (matrix tally drift) continues: the
  INTEGRATION_MATRIX "Verification tally" paragraph
  still carries its W08 promotion counts. The lock and
  the ledger test are the enforced truth (25 / 0 / 1);
  the tally paragraph wants a dedicated correction
  pass, out of this slice's rows-only scope.
- The section 32 release scorecard still reads NOT
  releasable; E.15 changes engine currency only, nothing
  else.
- Next in roadmap order: E.16.
