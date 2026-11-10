# E0 Integration Matrix — PROMOTED LEDGER (W08, Team 09, 2026-11-08)

Status: PROMOTED. This is the real E0 ledger, promoted inside W08 from
Team 09's `E0_LEDGER_DRAFT.md` (2026-11-07, draft sha256
`912087aff4b99f73bef8e58c4d0eedd6e588a28376d20fc37dbf102d5b511219`,
preserved unchanged beside this file) and paired with the verified
machine lock `integration-lock.json` (schema
`runeforge.integration-lock/v1`). The lock now has a live caller:
`plugins/volmarr-core/integration_ledger.py`, served as
`hermes volmarr engines {status|show|validate}` — a DRAFT lock, a
drifted first pin, or a missing adapter file is refused by name there
instead of rotting silently.

## How this promotion was verified (2026-11-08, purplelongship)

- Base tree: banked main `0d62b657bd2d63b02cf5d16839f512aca75801f2`
  (W07 banking closure) in worktree `~/hermes-team-09`, branch
  `yrsa/hermes-team-09`. README.md sha256
  `336813d11bbe5aa2ff745b4a4bc3abcf2a283cd13971c0c11d061377129db7f3`
  before and after — untouched.
- Every GitHub row's current HEAD was **re-measured** by
  `git ls-remote` on 2026-11-08 (~04:00 EST). **All 21 measurable
  HEADs are identical to the draft's 2026-11-07 measurements — no
  engine moved between the draft and this promotion.** Sagnaskemma
  was re-probed under both candidate names: repository not found,
  again.
- Every fork pin below was read in `COMPONENT_LICENSES.md` at the
  banked tree; every plugin version was read from its `plugin.yaml`;
  every adapter path in the lock was stat-checked in the tree.
- Adapter-mode words follow roadmap §13: documented / probe-only /
  read-only / deterministic tool / full read-write / realtime /
  prototype / design-only. Evidence stages follow §28.2's hierarchy
  (§28.3): documented only → contract implemented → installed
  integration → end-to-end working → production qualified, plus
  deferred/blocked. **No row is promoted past its proof.** No pin
  moved in W08: the per-engine protocol (§13 steps 1–10) requires
  each engine's own suite green in its own tree first, and that work
  is ticketed per engine (E.01–E.18), not batch-declared here.

## Corrections made at promotion (never bank a stale claim)

1. **Ravens rows 4/5 — the draft's central error.** The draft claimed
   the canonical Muninn/Huginn tree was "ABSENT on purplelongship".
   That is false and is corrected here, on Team 03's disk proof:
   `~/ravens` exists on purplelongship at
   `fc761f020b39f9be875310d271aac7423239d5f8`, byte-identical to the
   VM canonical tree; muninn 36 / huginn 27 suites green on the
   laptop; the W02 cold install selected both from the tree. The
   draft-era failures were a staging-location artifact: the
   `[tool.uv.sources]` binding is the relative path `../ravens`, so
   environments staged outside `$HOME` break it. Stage test envs
   from trees directly under `$HOME`. **Never install the PyPI
   muninn/huginn packages — unrelated software (Slice 86).**
2. **First pins are pins now.** The draft lock left the seven E0
   first-pin engines unpinned (`null`) pending E0; the promoted lock
   records them as pins (marked first-pin, never long-standing).
3. **Two §13 rows the draft omitted are added** (rows 25/26):
   Hermes SessionDB and Persistent identity / affect / goals /
   agency — fork-internal, no external pin, so the matrix covers
   every row of the roadmap's core integration matrix.
4. Branch-name discrepancy (draft blocker 5) is resolved by record:
   WAVE_PLAN.md names the branch `team-09/w08-e0-ledger`; the worktree
   was created as `yrsa/hermes-team-09` per the launch brief and all
   W08 work lands there.

## Ledger (26 rows)

| # | Engine / project | Repo | Fork pin (source) | Current HEAD (re-measured 2026-11-08) | License | Adapter in this fork (plugin + mode) | Evidence stage (§28.3) | Verification | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Verdandi | hrabanazviking/Verdandi | 2fc9db8bf555546ab96084f74b1d442b8e1c7a63 (COMPONENT_LICENSES.md) | 3140de1095daf3d230336906b203b64fb6aa7c3d (pin + E01-T1 test-fix commit, test-only) | MIT | volmarr-core 0.26.0 — realtime: opt-in fail-open lifecycle publish over Unix socket + health/stimuli | contract implemented | verified | current — E.01 executed 2026-11-10 |
| 2 | Project A.E.S.I.R. | hrabanazviking/RuneForgeAI-Project-Aesir | c1a4410ca254fa388e45936b02230999d0906a4c (COMPONENT_LICENSES.md) | d9f88b9a65531dfaf48b22df167d75d45d43ca50 | AGPL-3.0 | volmarr-core 0.26.0 — deterministic tool: bounded loopback OpenAI-compatible health/catalog/completion + route decisions | contract implemented | verified | update — E.02 |
| 3 | Bifrost / Mimir | hrabanazviking/bifrost | b66e98cc8a79d4dede22ba11d68a1a5ecd22ebd6, v1.0.0 (COMPONENT_LICENSES.md) | 99988dbb638d1b4f35f4a07590d61ad08b72ebd8 | MIT | volmarr-core 0.26.0 — probe-only: profile-local read-only probes; bridge construct-only, every write flag forced False | contract implemented | verified | update — E.03 |
| 4 | Muninn (ravens) | NO GitHub repo (Volmarr's alone to create) | local ravens tree fc761f020b39 (pkg 4eafc31, v1.0.0) | fc761f020b39f9be875310d271aac7423239d5f8 — tree HEAD == pin, ON purplelongship (corrected) | MIT | volmarr-core 0.26.0 — full read-write behind default-off operator flags | installed integration | verified (corrected) | pin-first — E.04 distribution blocker |
| 5 | Huginn (ravens) | NO GitHub repo (Volmarr's alone to create) | local ravens tree fc761f020b39 (pkg 54dd839, v1.0.0) | fc761f020b39f9be875310d271aac7423239d5f8 — tree HEAD == pin, ON purplelongship (corrected) | MIT | volmarr-core 0.26.0 — full read-write behind default-off flags, constructed DIRECTLY only; through-Bifrost path is NO-GO | installed integration | verified (corrected) | pin-first — E.04 distribution blocker |
| 6 | MemPalace (official) | MemPalace/mempalace | v3.10.0 at 22fd87f09c19d5ffb2d6966486483353937931c0 (COMPONENT_LICENSES.md) | fa6ae179d852dd145d33cfee2a37db5b346c45b3 | MIT | volmarr-core 0.26.0 — read-only: version-checked probe (MINIMUM_PACKAGE_VERSION 3.10.0) + opt-in default-off SQLite BM25 retrieval | contract implemented | verified | update — E.05 |
| 7 | MemPalace (Volmarr mirror) | hrabanazviking/mempalace | ff1bdf03407bc5d6c571fa85f8c621d7177de616 (COMPONENT_LICENSES.md) | ff1bdf03407bc5d6c571fa85f8c621d7177de616 — MATCHES pin | MIT | none — mirror held as reference/fallback source only | documented only | verified | reference-only |
| 8 | OpenViking (official) | volcengine/OpenViking | v0.4.21 at 3fca2577520f00b7f580d85d4ac6ae42bb9ba6f1 (COMPONENT_LICENSES.md); Slice 84 audit pinned server 0.5.x at e855796c83f9 (= tag v0.5.1) | 9ac008f9b86c91b79d6e93eb8df8ea7f4d48cecb | AGPL-3.0 | volmarr-core 0.26.0 — probe-only + read-only: loopback /health probe (MINIMUM_SERVER_VERSION 0.4.21) + opt-in memories-only /find retrieval | contract implemented | verified | update — E.06 |
| 9 | OpenViking (Volmarr mirror) | hrabanazviking/OpenViking | NONE recorded (found unpinned at E0, beyond the brief's seven) | cbf8befcea5736f3b316a6c12e84ba11c40b31c4 | Apache-2.0 (API — differs from official AGPL-3.0; text unverified) | none — mirror reference only | documented only | partially verified | reference-only |
| 10 | WYRD Protocol | hrabanazviking/WYRD-Protocol-World-Yielding-Real-time-Data-AI-world-model | v1.0.0 at 9884ce8a9e683dc20f372a91eb66ba5b02561300 (COMPONENT_LICENSES.md) | 89ed09394c7e13b2e63f91e342fbab8ff9890cbc (development) | CC BY 4.0 per fork ledger; GitHub detected NONE at repo root — text unverified | volmarr-core 0.26.0 — read-only probe + bounded world get/query + confirmed set/observe (MINIMUM_SERVER_VERSION 1.0.0, contract wyrd-http-v1) | contract implemented | partially verified (license) | update — E.07 |
| 11 | Kista | hrabanazviking/kista | v2.0.0 at ce6313cc392589abd43a5fcf614e0e272663961f (COMPONENT_LICENSES.md) | 41a6d65863af9ec5d41ca148828a0b6863605b86 | MIT | kista-secret-source 0.2.0 — read-only: Secret Source get via plugin API, redaction-scoped | contract implemented | verified | update — E.08 |
| 12 | Astrology Engine | hrabanazviking/astrology-engine | 1709fcfc1e00198ab0f25fe4889868a7245cf014 (COMPONENT_LICENSES.md) | bb4ede4fbb326d21df34a5ca0ca6e343f4f49fbe | Apache-2.0 | volmarr-astrology 0.7.0 — deterministic tool: fixed-argv bounded subprocess against a local checkout | contract implemented | verified | update — E.09 |
| 13 | RuneTarotEngine | hrabanazviking/RuneTarotEngine | **FIRST PIN at E0:** 432e461136ba58cb3e507bb9cd86b4bb2faba80b | 432e461136ba58cb3e507bb9cd86b4bb2faba80b — equals first pin | MIT (API) | volmarr-tarot 0.3.0 — deterministic tool: seeded draws via bounded subprocess against a local checkout | contract implemented | verified | pin-first — audit E.10 |
| 14 | Seidr Engine | hrabanazviking/seidr-engine | **FIRST PIN at E0:** fdc2b3c85c62982a4550dfe476751287d723519d | fdc2b3c85c62982a4550dfe476751287d723519d — equals first pin | MIT (API) | volmarr-seidr 0.4.0 — deterministic tool: seeded composition via bounded subprocess | contract implemented | verified | pin-first — audit E.11 |
| 15 | Hamr | hrabanazviking/Hamr | **FIRST PIN at E0:** f77aa588601b38a69b6c1fc0a6733ed5e95dffa8 | f77aa588601b38a69b6c1fc0a6733ed5e95dffa8 — equals first pin (tag v0.7.0) | NOASSERTION (API — license file present, unclassified) | volmarr-hamr 0.4.0 — read-only: spec/budget/artifact preflight only | contract implemented | partially verified (license) | pin-first — audit E.13 |
| 16 | Seidr-Smidja | hrabanazviking/Seidr-Smidja | **FIRST PIN at E0:** 32cdbd7a87358bc1f6f046c4e1449c35f4d5d40a | 32cdbd7a87358bc1f6f046c4e1449c35f4d5d40a — equals first pin | Apache-2.0 (API) | volmarr-smidja 0.1.0 — read-only: Loom/Hoard/Gate/Oracle Eye preflight | contract implemented | verified | pin-first — audit E.14 |
| 17 | AIAvatarKit | hrabanazviking/aiavatarkit | **FIRST PIN at E0:** 9295e096169316ec19e9fa712e52733d912fd5e7 | 9295e096169316ec19e9fa712e52733d912fd5e7 — equals first pin | Apache-2.0 (API) | volmarr-voice 1.0.0 — prototype: pure presentation-shape translation only; invokes NO AIAvatarKit pipeline | contract implemented | verified | pin-first — audit E.15 |
| 18 | Open-LLM-VTuber | hrabanazviking/Open-LLM-VTuber | audit HEAD recorded at E0: 19b58b1f6c01e082289fce089392997b9d14fbc4 (no admissible embed) | 19b58b1f6c01e082289fce089392997b9d14fbc4 | NOASSERTION (API) | none — design-only: documented architecture audit; owns its own ASR/TTS/agent loops | documented only | verified | reference-only — re-evaluate at E.15 |
| 19 | OmniVoice | hrabanazviking/OmniVoice | **FIRST PIN at E0:** a4068c820f21307df337e34f67d3dda443735ad4 | a4068c820f21307df337e34f67d3dda443735ad4 — equals first pin | Apache-2.0 (API) | volmarr-voice 1.0.0 — design-only today: voice readiness/presentation contracts; grep at promotion found NO OmniVoice code reference | documented only | verified | pin-first — audit E.15 |
| 20 | ChatIndex | hrabanazviking/ChatIndex | **FIRST PIN at E0:** 7df2c9208db6f113f85a6c09295bec7f0f2114e7 | 7df2c9208db6f113f85a6c09295bec7f0f2114e7 — equals first pin | Apache-2.0 (API) | none — design-only: concept reference in the P2 retrieval design; no adapter code (W06 also recorded it deferred) | documented only | verified | pin-first — audit inside P2/E2 work |
| 21 | MindSpark / ThoughtForge | hrabanazviking/MindSpark_ThoughtForge | concept reference only, no pin claimed | 68aa4d1cd29f6d6c57d1266e70833584c9b1a74e (development) | NONE detected (API) | none — design-only: reflex concept reference, NO runtime adapter claimed | documented only | verified | reference-only |
| 22 | SRD data (dnd-5e-srd) | hrabanazviking/dnd-5e-srd | no SHA pin in licenses | 2e62e0413061c2443e21369cdc074c7a7356a857 | NOASSERTION (API — SRD content terms) | volmarr-rpg 0.8.0 — deterministic tool data: external SRD lookup via srd_root checkout | contract implemented | partially verified (license) | reference-only — E.12 boundary review |
| 23 | Older fork (provenance) | hrabanazviking/hermes-agent | 761a8559084e7f (Present State) / d423b611799d (Affective) adapted-module pins (COMPONENT_LICENSES.md) | 7d4c90fe7c4dad6bea95f292c5a809f3b88eb498 | MIT | none live — provenance only: modules adapted into volmarr-core (present_state.py, affective.py) | documented only | verified | reference-only |
| 24 | Sagnaskemma engine | UNKNOWN — no repo found under hrabanazviking/Sagnaskemma or RuneForgeAI-Sagnaskemma (**re-probed 2026-11-08: repository not found, both names**) | NONE — no pin possible | n/a | n/a | none — §13/§40 names it as the future RPG adapter (E.12) | deferred/blocked | **blocked** | pin-first — BLOCKED on canonical repo identification from project records |
| 25 | Hermes SessionDB *(added at promotion)* | fork-internal — Hermes owns the transcript store | n/a (no external engine) | n/a | n/a | volmarr-core 0.26.0 — read-only: preservation/health probe (sessiondb.py), contracts in the baseline set | contract implemented | verified | internal — §13 completeness row |
| 26 | Persistent identity / affect / goals / agency *(added at promotion)* | fork-internal volmarr-core modules | n/a (no external engine) | n/a | n/a | volmarr-core 0.26.0 — read-only surfaces + contract modules; W05 gave several their first live callers; the rest stay contract-only and are NOT declared complete (§28.2) | contract implemented | verified | internal — live-hook reconciliation is E.16 |

Verification tally: **21 verified / 4 partially verified (rows 9, 10,
15, 22 — all license-text questions, named per row) / 1 blocked
(row 24)**. Every "verified" above means the row's pin, current HEAD,
plugin version, adapter mode and adapter files were each read from a
named source at promotion — not that the engine's upgrade is done.

## First pins established at E0 (2026-11-07, Team 09)

Seven engines had NO pin recorded anywhere in this fork before E0.
Each pin is the engine repo HEAD measured by Team 09 via
`git ls-remote` on purplelongship at 2026-11-07T21:37:18-05:00, and
**re-measured identical at promotion on 2026-11-08** — none of the
seven has moved. They are first pins, not long-standing pins, and
must never be presented as such. The promoted lock records them as
`pinned` values, and `integration_ledger.FIRST_PINS` enforces them:
a silent drift fails `hermes volmarr engines validate` by name.

| Engine | First pin (E0, 2026-11-07) |
|---|---|
| RuneTarotEngine | 432e461136ba58cb3e507bb9cd86b4bb2faba80b |
| Seidr Engine (seidr-engine) | fdc2b3c85c62982a4550dfe476751287d723519d |
| Hamr | f77aa588601b38a69b6c1fc0a6733ed5e95dffa8 |
| Seidr-Smidja | 32cdbd7a87358bc1f6f046c4e1449c35f4d5d40a |
| AIAvatarKit (aiavatarkit) | 9295e096169316ec19e9fa712e52733d912fd5e7 |
| OmniVoice | a4068c820f21307df337e34f67d3dda443735ad4 |
| ChatIndex | 7df2c9208db6f113f85a6c09295bec7f0f2114e7 |

Also found unpinned at E0, outside the brief's seven: the OpenViking
mirror (row 9) and SRD data (row 22). E.06/E.12 own their pin
decisions; W08 does not invent pins for them.

## E.01–E.03 first engine audits (audit only — no updates made, no pins moved)

Carried from the E0 draft unchanged in substance; the §13 protocol
(step 3: the engine's own suite green in its own tree FIRST) has not
been run for any engine yet, so every pin below stays where it is.

### E.01 Verdandi — current event protocol and bridge regression

- Delta: pin dc7139416ef4 → current 2fc9db8bf555 = 67 commits
- EXECUTED 2026-11-10 (Volmarr ruling 03:29 EST, ticket E01-T1): pin moved dc7139416ef4 → 2fc9db8bf555; the one proof-1 failure was an engine-side test-isolation defect, fixed in the Verdandi repo itself (get_context_for_cron now reads the nerve feed and reactor from STATE_DIR, not the ambient home), after which the Verdandi suite runs clean in a pristine environment. Full record: docs/modernization/E01_VERDANDI_UPDATE.md.
  (blobless-clone count at E0). The nerve hub was hardened repeatedly:
  over-limit structured rejects, subscriber keepalive, SIGTERM
  graceful shutdown, supervisor + PID-reuse-safe health checks;
  state honesty (all-or-nothing loads, corrupt-state quarantine,
  naive-UTC guards); CLI domain errors exit 2; mood integration keys;
  a Telegram-to-nerve bridge; a WYRD mirror stack.
- Breaking-change risk to this fork: MEDIUM-HIGH. The fork publishes
  versioned lifecycle metadata (schema runeforge.hermes.lifecycle v1)
  and reads health/stimuli; hub-side reject, keepalive and health
  semantics all changed under that contract, and the bridge is
  fail-open by design — protocol drift would present as silence, not
  as an error. That is exactly the failure shape E.01 exists to catch.
- Exact update proof E.01 still needs: (1) Verdandi's own suite green
  in its own tree at 2fc9db8bf555; (2) fork contract batteries
  `test_volmarr_verdandi*.py` via `scripts/run_tests.sh` against the
  current hub, not a stub; (3) a live socket round-trip in a
  disposable profile incl. over-limit reject behaviour and stimuli
  catch-up; (4) absent-service fail-open proof; (5) latency +
  metadata-only privacy check (§13 step 7). Only then may the pin move.

### E.02 A.E.S.I.R. — inference/quantization/model catalog API

- Delta: pin c1a4410ca254 → current d9f88b9a6553 = 1,779 commits, by
  far the largest in this ledger (the whole Aesir model-wave and
  Janas lines merged to main 2026-11-01, plus a docs-only
  Qwen3/Qwen3.8/Qwen-4 research library at the head).
- Breaking-change risk: HIGH for surface drift. The fork binds a
  bounded OpenAI-compatible loopback endpoint (default
  http://127.0.0.1:18434/v1; catalog capped at 256 models / 256 KiB;
  completion capped at 1 MiB) and content-free route decisions
  (route schema v2). 1,779 commits can change model IDs, catalog
  shape and completion semantics while /health still answers — a
  health-only green would prove almost nothing.
- Exact update proof E.02 still needs: (1) A.E.S.I.R.'s own suite
  green in its own tree at d9f88b9a6553; (2) a recorded catalog
  fixture diff (the /models payload shape at pin vs at current,
  filed as a versioned compatibility fixture, §13 step 4); (3) fork
  cognition/routing contracts via `scripts/run_tests.sh`; (4) a
  disposable-profile live loopback turn (health → catalog → one
  bounded completion → cancellation) with local-only mode proven to
  make no external request (§14 acceptance); (5) a capability record
  per host (GPU/NPU/CPU paths actually present, never assumed).

### E.03 Bifrost/Mimir — current retrieval and write contracts

- Delta: pin b66e98cc8a79 (v1.0.0) → current 99988dbb638d = 2
  commits, BOTH docs (Second Brain master expansion roadmap;
  repository-specific Bifrost integration responsibilities). No
  Bifrost code has changed since the pin.
- Breaking-change risk: LOW for API drift (the fork's surface is a
  construct-only bridge, write flags forced off, plus read-only
  probes). The real E.03 work is (a) reading those two docs commits —
  they may state new integration duties this fork must honour before
  any promotion — and (b) the ravens distribution question (E.04).
- **RAVENS — CORRECTED RECORD (supersedes the draft).** The draft
  recorded the canonical tree as absent on purplelongship; it is
  present (`~/ravens`, fc761f0) and the fork's contracts run against
  it from `$HOME`-level trees. What remains genuinely open for E.03/
  E.04 is *distribution*: the ravens have no repo and no publishable
  package route (repo creation is Volmarr's alone; first-party
  publication route is design-only per W02 ticket T3), so a checkout
  on a NEW machine still cannot resolve the `volmarr-ravens` extra
  without the tree being carried there by hand.
- Exact update proof E.03 still needs: (1) Bifrost's own tests green
  in its own tree at 99988dbb638d; (2) both docs commits read and any
  stated integration duties listed against the fork's current
  surface; (3) fork contracts `test_volmarr_memory_fabric*` and
  `test_volmarr_ravens*` via `scripts/run_tests.sh` with the
  canonical tree beside the checkout (they pass in the W08 baseline
  run — that is contract proof, not E.03 completion); (4) read-only
  proof: Muninn store file sha256 identical before/after a probe
  (the Slice 87 standard); (5) write operations exercised only
  behind their default-off flags in a disposable profile;
  (6) absent-ravens proof on a tree staged without the sibling:
  probe answers package_missing and nothing reaches PyPI.

## WYRD version reconciliation (E.07 advance work, carried from the draft)

- Git tags on the WYRD repo: exactly ONE — v1.0.0 at f3dfb1a27c0a.
  GitHub releases: exactly ONE — v1.0.0. There is NO v1.5.0 tag and
  NO v1.5.0 release.
- The fork pin 9884ce8a9e68 (2026-09-17) sits 14 commits AFTER the
  v1.0.0 tag; its pyproject.toml says version = 1.0.0. The pin's
  v1.0.0 label is correct for its commit.
- The CURRENT code says version = 1.5.0 in pyproject.toml on BOTH
  main (7df509e91407) and development (89ed09394c7e); the pin's
  distance is 73 commits to main, 75 to development. This fork's
  adapter requires only MINIMUM_SERVER_VERSION 1.0.0, so it attests
  either version.
- Verdict: both records are true about different things. v1.0.0 is
  the only tagged/released version; v1.5.0 is the in-package version
  of the current, untagged code — it is not a release. E.07 must pin
  WYRD by SHA and record the package version separately (the
  promoted lock does exactly that).

## What W08 did per phase E1–E5 (and what it honestly did not)

- **E0 (this ledger + lock + registry): DONE.** Ledger promoted with
  corrections, lock promoted and verified per row, first pins
  recorded and enforced, and the lock given a live caller
  (`integration_ledger.py` + `hermes volmarr engines …`) so its
  state is checkable in one command instead of by archaeology.
- **E1 local cognition (Aesir, routing): audit-only in W08** — the
  E.02 audit above is the wave's E1 deliverable. The cognition/
  routing adapters stand at contract-implemented; no capability
  discovery, streaming, or pin work was built, and none is claimed.
- **E2 memory fabric: verification-only in W08** — the fabric's
  sources (Bifrost probes, ravens, MemPalace, OpenViking, SessionDB,
  persona canon) are the rows verified above; the ravens correction
  is the substantive E2 fix. No universal memory envelope was built;
  ChatIndex stays design-only (row 20), as W06 also recorded.
- **E3 real-time events (Verdandi): audit-only in W08** — the E.01
  audit above. No event-schema upgrade (publisher identity,
  idempotency, ack/replay) was built; the 7 baseline live-transport
  failures remain exactly that — environment-bound absences, with
  the real-socket diagnosis still open as §28.2 names it.
- **E4 voice/avatar: pin + audit-only in W08** — AIAvatarKit and
  OmniVoice first pins recorded (rows 17/19); the output-only
  boundary stands as audited (AIAvatarKit translation invokes no
  pipeline; OmniVoice has no code reference). No adapter was built.
- **E5 spiritual/creative/tabletop: pin + audit-only in W08** —
  Astrology stands verified at its existing pin (E.09 fixtures are
  future work); RuneTarot/Seidr first pins recorded (E.10/E.11
  audits future); SRD/Sagnaskemma stay behind the E.12 license +
  repo-identification blockers, named in rows 22/24, not worked
  around.

## Blockers and open items carried forward

1. Sagnaskemma canonical repo unknown (row 24, E.12) — re-probed
   2026-11-08, still not found under either candidate name; needs
   the repo name from Volmarr's project records before any pin
   exists. (Repo creation is Volmarr's alone regardless.)
2. License texts unverified: WYRD (row 10, E.07), Hamr (row 15,
   E.13), SRD (row 22, E.12), OpenViking mirror (row 9, E.06),
   Open-LLM-VTuber (row 18, no reliance — informational).
3. Per-engine upgrades E.01–E.18: none executed in W08. Each starts
   with the engine's own suite in its own tree (§13 step 3); pins
   move one engine at a time, each with its own lock revision.
4. Ravens distribution (E.04): no repo, no publication route —
   design-only per W02 T3; the tree itself is present and pinned.
5. COMPAT_MANIFEST.md: still absent from the tree (Phase 0
   find-verified; W00.05 fixture archive remains open) — this
   matrix + lock are the living compatibility record meanwhile, and
   nothing here pretends the manifest exists.
6. W00.03-ENC (backup encryption) still awaits Volmarr's word —
   untouched by W08, not re-asked.
