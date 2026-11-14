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

## Ledger (29 rows)

| # | Engine / project | Repo | Fork pin (source) | Current HEAD (re-measured 2026-11-08) | License | Adapter in this fork (plugin + mode) | Evidence stage (§28.3) | Verification | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Verdandi | hrabanazviking/Verdandi | 2fc9db8bf555546ab96084f74b1d442b8e1c7a63 (COMPONENT_LICENSES.md) | 3140de1095daf3d230336906b203b64fb6aa7c3d (pin + E01-T1 test-fix commit, test-only) | MIT | volmarr-core 0.26.0 — realtime: opt-in fail-open lifecycle publish over Unix socket + health/stimuli | contract implemented | verified | current — E.01 executed 2026-11-10 · E.17 live probes passed 2026-11-14 |
| 2 | Project A.E.S.I.R. | hrabanazviking/RuneForgeAI-Project-Aesir | d9f88b9a65531dfaf48b22df167d75d45d43ca50 (COMPONENT_LICENSES.md) | d9f88b9a65531dfaf48b22df167d75d45d43ca50 | AGPL-3.0 | volmarr-core 0.26.0 — deterministic tool: bounded loopback OpenAI-compatible health/catalog/completion + route decisions | contract implemented | verified | current — E.02 executed 2026-11-13 · E.17 live probes passed 2026-11-14 |
| 3 | Bifrost / Mimir | hrabanazviking/bifrost | 99988dbb638d1b4f35f4a07590d61ad08b72ebd8, v1.0.0 (COMPONENT_LICENSES.md) | 99988dbb638d1b4f35f4a07590d61ad08b72ebd8 | MIT | volmarr-core 0.26.0 — probe-only: profile-local read-only probes; bridge construct-only, every write flag forced False | contract implemented | verified | current — E.03 executed 2026-11-13 |
| 4 | Muninn (ravens) | hrabanazviking/Huginn-and-Muninn-Ravens (created by Volmarr 2026-10-31; 1.0.0 published at f12fb39, byte-identical to the pinned tree) | local ravens tree fc761f020b39 (pkg 4eafc31, v1.0.0) | fc761f020b39f9be875310d271aac7423239d5f8 — tree HEAD == pin, ON purplelongship (corrected) | MIT | volmarr-core 0.26.0 — full read-write behind default-off operator flags | installed integration | verified (corrected) | current — E.04 executed 2026-11-13 (distribution proven; pin stays local tree HEAD; repo-HEAD growth at unchanged 1.0.0 = future update E04-T1) · X.07 executed 2026-11-14 (dedicated repo = audited authority; independent package pin 4eafc3101e recorded in the lock; ravens_authority adapter + `hermes volmarr ravens {status|roles|smoke}` live CLI) |
| 5 | Huginn (ravens) | hrabanazviking/Huginn-and-Muninn-Ravens (created by Volmarr 2026-10-31; 1.0.0 published at f12fb39, byte-identical to the pinned tree) | local ravens tree fc761f020b39 (pkg 54dd839, v1.0.0) | fc761f020b39f9be875310d271aac7423239d5f8 — tree HEAD == pin, ON purplelongship (corrected) | MIT | volmarr-core 0.26.0 — full read-write behind default-off flags, constructed DIRECTLY only; through-Bifrost path is NO-GO | installed integration | verified (corrected) | current — E.04 executed 2026-11-13 (distribution proven; pin stays local tree HEAD; repo-HEAD growth at unchanged 1.0.0 = future update E04-T1) · X.07 executed 2026-11-14 (dedicated repo = audited authority; independent package pin 54dd839c9 recorded in the lock; ravens_authority adapter + `hermes volmarr ravens {status|roles|smoke}` live CLI) |
| 6 | MemPalace (official) | MemPalace/mempalace | v3.12.0 at 0ed1be82dcbe4f59081b87c4eaa0986af0768ff4 (COMPONENT_LICENSES.md) | 0ed1be82dcbe4f59081b87c4eaa0986af0768ff4 | MIT | volmarr-core 0.26.0 — read-only: version-checked probe (MINIMUM_PACKAGE_VERSION 3.10.0) + opt-in default-off SQLite BM25 retrieval | contract implemented | verified | current — E.05 executed 2026-11-13 · E.17 live probes passed 2026-11-14 |
| 7 | MemPalace (Volmarr mirror) | hrabanazviking/mempalace | ff1bdf03407bc5d6c571fa85f8c621d7177de616 (COMPONENT_LICENSES.md) | ff1bdf03407bc5d6c571fa85f8c621d7177de616 — MATCHES pin | MIT | none — mirror held as reference/fallback source only | documented only | verified | reference-only |
| 8 | OpenViking (official) | volcengine/OpenViking | v0.5.6.dev26 at 90f4edcede4c6a665fccb747417ebe6c1db56f4d (COMPONENT_LICENSES.md); Slice 84 audit pinned server 0.5.x at e855796c83f9 (= tag v0.5.1) | 90f4edcede4c6a665fccb747417ebe6c1db56f4d | AGPL-3.0 | volmarr-core 0.26.0 — probe-only + read-only: loopback /health probe (MINIMUM_SERVER_VERSION 0.4.21) + opt-in memories-only /find retrieval | contract implemented | verified | current — E.06 executed 2026-11-13 · E.17 live probes passed 2026-11-14 |
| 9 | OpenViking (Volmarr mirror) | hrabanazviking/OpenViking | NONE recorded (found unpinned at E0, beyond the brief's seven) | cbf8befcea5736f3b316a6c12e84ba11c40b31c4 | Apache-2.0 (text verified in E.06, 2026-11-13 — differs from official AGPL-3.0) | none — mirror reference only | documented only | verified (license text) | reference-only |
| 10 | WYRD Protocol | hrabanazviking/WYRD-Protocol-World-Yielding-Real-time-Data-AI-world-model | package v1.5.0 at 89ed09394c7e13b2e63f91e342fbab8ff9890cbc (COMPONENT_LICENSES.md; development HEAD; v1.0.0 is the only tag/release) | 89ed09394c7e13b2e63f91e342fbab8ff9890cbc (development) | CC BY 4.0 (README License section + pyproject declaration verified in E.07, 2026-11-13; no standalone LICENSE file — GitHub NONE explained) | volmarr-core 0.26.0 — X.04 upgraded single adapter (wyrd.py + wyrd_tools.py + wyrd_context.py + world_telemetry.py): liveness + capability negotiation (version mismatch fails truthfully; no silent schema migration), namespaced source-linked entity/component refs, four truth classes (durable canonical fact / tentative observation / quoted evidence / fictional state; identities + private relationship memories refused), durable transactional idempotent write journal (revision checks, stale-write rejection, replay after restart), deterministic conflict resolution with causal provenance, bounded provenance prompt packets, polling subscriptions/streaming (no server push at the pin), authorized-consumer seams; confirmed set/observe over wyrd-http-v1 (MINIMUM_SERVER_VERSION 1.0.0) | contract implemented | verified | current — E.07 executed 2026-11-13 · E.17 live probes passed 2026-11-14 · X.04 adapter upgrade executed 2026-11-14 (pin unchanged) |
| 11 | Kista | hrabanazviking/kista | v2.0.0 at 41a6d65863af9ec5d41ca148828a0b6863605b86 (COMPONENT_LICENSES.md) | 41a6d65863af9ec5d41ca148828a0b6863605b86 | MIT | kista-secret-source 0.2.0 — read-only: Secret Source get via plugin API, redaction-scoped | contract implemented | verified | current — E.08 executed 2026-11-13 |
| 12 | Astrology Engine | hrabanazviking/astrology-engine | v4.0.0 at bb4ede4fbb326d21df34a5ca0ca6e343f4f49fbe (COMPONENT_LICENSES.md) | bb4ede4fbb326d21df34a5ca0ca6e343f4f49fbe | Apache-2.0 (text verified in E.09, 2026-11-13) | volmarr-astrology 0.7.0 — deterministic tool: fixed-argv bounded subprocess against a local checkout | contract implemented | verified | current — E.09 executed 2026-11-13 |
| 13 | RuneTarotEngine | hrabanazviking/RuneTarotEngine | 432e461136ba58cb3e507bb9cd86b4bb2faba80b (COMPONENT_LICENSES.md; first pin at E0) | 432e461136ba58cb3e507bb9cd86b4bb2faba80b | MIT (LICENSE text verified in E.10, 2026-11-13, for the pinned main tree; the code-bearing development branch carries no LICENSE file — see E10_TAROT_UPDATE.md) | volmarr-tarot 0.3.0 — deterministic tool: seeded draws via bounded subprocess against a local checkout (development branch) | contract implemented | verified | current — E.10 executed 2026-11-13 · E.17 live probes passed 2026-11-14 |
| 14 | Seidr Engine | hrabanazviking/seidr-engine | fdc2b3c85c62982a4550dfe476751287d723519d (COMPONENT_LICENSES.md; first pin at E0) | fdc2b3c85c62982a4550dfe476751287d723519d | MIT (LICENSE text verified in E.11, 2026-11-14) | volmarr-seidr 0.4.0 — deterministic tool: seeded composition via bounded subprocess | contract implemented | verified | current — E.11 executed 2026-11-14 |
| 15 | Hamr | hrabanazviking/Hamr | f77aa588601b38a69b6c1fc0a6733ed5e95dffa8 (COMPONENT_LICENSES.md; first pin at E0) | f77aa588601b38a69b6c1fc0a6733ed5e95dffa8 | MIT (LICENSE text verified in E.13, 2026-11-14) | volmarr-hamr 0.4.0 — read-only: spec/budget/artifact preflight only | contract implemented | verified | current — E.13 executed 2026-11-14 |
| 16 | Seidr-Smidja | hrabanazviking/Seidr-Smidja | 32cdbd7a87358bc1f6f046c4e1449c35f4d5d40a (COMPONENT_LICENSES.md; first pin at E0) | 32cdbd7a87358bc1f6f046c4e1449c35f4d5d40a | Apache-2.0 (LICENSE text verified in E.14, 2026-11-14; pyproject.toml declares MIT — conflict ticketed E14-T1) | volmarr-smidja 0.1.0 — read-only: Loom/Hoard/Gate/Oracle Eye preflight | contract implemented | verified | current — E.14 executed 2026-11-14 |
| 17 | AIAvatarKit | hrabanazviking/aiavatarkit | **FIRST PIN at E0:** 9295e096169316ec19e9fa712e52733d912fd5e7 | 9295e096169316ec19e9fa712e52733d912fd5e7 — equals first pin (re-measured E.15, main, no tags) | Apache-2.0 (text-verified E.15, sha256 134fb4c3dd13; appendix Copyright (c) 2023 uezo; setup.py Apache v2 agrees; nested motionpngtuber example MIT) | volmarr-voice 1.0.0 — prototype: pure presentation-shape translation only; invokes NO AIAvatarKit pipeline (boundary re-proved live E.15) | contract implemented | verified | current — E.15 executed 2026-11-14 |
| 18 | Open-LLM-VTuber | hrabanazviking/Open-LLM-VTuber | audit HEAD recorded at E0: 19b58b1f6c01e082289fce089392997b9d14fbc4 (no admissible embed) | 19b58b1f6c01e082289fce089392997b9d14fbc4 — equals recorded audit HEAD (re-measured E.15, main, no tags) | MIT (root LICENSE text-verified E.15, sha256 c48a8498e88f, Copyright (c) 2025 Yi-Ting Chiu; NOASSERTION resolved) + Live2D sample data under separate Live2D terms (LICENSE-Live2D.md, sha256 5e2b759bba52) | none — design-only: documented architecture audit; owns its own ASR/TTS/agent loops | documented only | verified | reference-only — E.15 re-evaluated 2026-11-14, kept reference-only, no pin taken |
| 19 | OmniVoice | hrabanazviking/OmniVoice | **FIRST PIN at E0:** a4068c820f21307df337e34f67d3dda443735ad4 | a4068c820f21307df337e34f67d3dda443735ad4 — equals first pin (re-measured E.15, master, no tags) | Apache-2.0 (text-verified E.15, sha256 c843a20ede4d; appendix Copyright 2026 Xiaomi Corp.; pyproject Apache-2.0 agrees) | volmarr-voice 1.0.0 — design-only today: voice readiness/presentation contracts; grep re-run E.15 found NO OmniVoice code reference | documented only | verified | current — E.15 executed 2026-11-14 |
| 20 | ChatIndex | hrabanazviking/ChatIndex | **FIRST PIN at E0:** 7df2c9208db6f113f85a6c09295bec7f0f2114e7 | 7df2c9208db6f113f85a6c09295bec7f0f2114e7 — equals first pin (re-measured E.16, main, no other branches or tags) | Apache-2.0 (LICENSE text verified in E.16, 2026-11-14, sha256 c71d239df917; appendix unfilled; setup.py trove classifier declares MIT — conflict ticketed E16-T5) | none — design-only: concept reference in the P2 retrieval design; no adapter code (W06 also recorded it deferred) | documented only | verified | current — E.16 executed 2026-11-14 (pin unmoved; kept design-only, no adapter built) |
| 21 | MindSpark / ThoughtForge | hrabanazviking/MindSpark_ThoughtForge | no pin taken in X.06 (adapter incorporates no source, binds no runtime interface; audited HEAD recorded) | 68aa4d1cd29f6d6c57d1266e70833584c9b1a74e (development, re-measured by ls-remote 2026-11-14 — HEAD unmoved since E0) | CC BY 4.0 declared (README License section + pyproject license field text-read in X.06, 2026-11-14; NO standalone LICENSE file at the audited HEAD) | volmarr-core 0.26.0 — deterministic-first cognition adapter: six small-model profiles (classifier, router, reflection, persona tagging via the single persona compiler only, budget planner, validation), loopback-only optional model seam with cancellation/crash/OOM/malformed fallback, route proposals only (final authority + budget enforcement stay in Hermes) (mindspark.py) | contract implemented | verified | current — X.06 executed 2026-11-14 (model benefit not proven — deterministic-first per section 41 item 4; X06-T1) |
| 22 | SRD data (dnd-5e-srd) | hrabanazviking/dnd-5e-srd | 2e62e0413061c2443e21369cdc074c7a7356a857 (COMPONENT_LICENSES.md; FIRST PIN at E.12) | 2e62e0413061c2443e21369cdc074c7a7356a857 | OGL-1.0a (SRD 5.0 content) + MIT (repo conversion code) — LICENSE text verified in E.12, 2026-11-14 | volmarr-rpg 0.8.0 — deterministic tool data: external SRD lookup via srd_root checkout | contract implemented | verified | current — E.12 executed 2026-11-14 |
| 23 | Older fork (provenance) | hrabanazviking/hermes-agent | 761a8559084e7f (Present State) / d423b611799d (Affective) adapted-module pins (COMPONENT_LICENSES.md) | 7d4c90fe7c4dad6bea95f292c5a809f3b88eb498 | MIT | none live — provenance only: modules adapted into volmarr-core (present_state.py, affective.py) | documented only | verified | reference-only |
| 24 | Sagnaskemma engine | hrabanazviking/Sagnaskemma-Volmarrs-D-and-D-Lore-Treasure-Trove (**IDENTIFIED at E.12, 2026-11-14**) | a1f474f4b8803b7003b35b09f486a53145545685 (COMPONENT_LICENSES.md; FIRST PIN at X.05) | a1f474f4b8803b7003b35b09f486a53145545685 | private - no LICENSE file at the pin; owner private repo, license to-be-decided while non-public (THIRD_PARTY_NOTICES section 3 read at the staged tree, X.05); sole dependency d20 MIT | volmarr-core 0.26.0 - deterministic tool: versioned private local tool service (runeforge.sagnaskemma.service.v1) over engine.api protocol 1.0 + adapter-side session store with one seeded dice owner per session (sagnaskemma.py); lore retrieval canon-denied by default | contract implemented | verified | current - X.05 executed 2026-11-14 (section 40 workstream 5 of 15; E12-T1 discharged) |
| 25 | Hermes SessionDB *(added at promotion)* | fork-internal — Hermes owns the transcript store | n/a (no external engine) | n/a | n/a | volmarr-core 0.26.0 — read-only: preservation/health probe (sessiondb.py), contracts in the baseline set | contract implemented | verified | internal — §13 completeness row |
| 26 | Persistent identity / affect / goals / agency *(added at promotion)* | fork-internal volmarr-core modules | n/a (no external engine) | n/a | n/a | volmarr-core 0.26.0 — read-only surfaces + contract modules; W05 gave several their first live callers; the rest stay contract-only and are NOT declared complete (§28.2) | contract implemented | verified | current — E.16 executed 2026-11-14 (reconciliation in E16_IDENTITY_AGENCY_UPDATE.md; remainders E16-T1..T4) |
| 27 | Yggdrasil Distributed Inference System | hrabanazviking/Yggdrasil-Distributed-Inference-System | NONE - no pin taken at X.01 (contract-level prototype only; audited HEAD recorded in the lock) | 1af750f1ad2fb7b3f39776f7cefb56a68359772a (main, ls-remote 2026-11-14; no tags) | MIT (LICENSE text verified in X.01, 2026-11-14, sha256 c006b7010fa0) | volmarr-core 0.26.0 - prototype: local-host read-only discovery + versioned envelopes + pure placement records (yggdrasil_local.py); NO mesh, NO peer discovery | contract implemented | verified | current - X.01 executed 2026-11-14 (section 36 workstream 1 of 15; host-to-host live proof outstanding = X01-T2) |
| 28 | Lifthrasir | hrabanazviking/RuneForgeAI-Lifthrasir | NONE - no pin taken at X.02 (research-stage source; no installable package; audited HEAD recorded in the lock) | 69fb1ed99cb238cacd9f35c057c6936137041724 (main, ls-remote 2026-11-14; no tags) | GPL-2.0-only (LICENSE text verified in X.02, 2026-11-14, sha256 8177f9751321) | volmarr-core 0.26.0 - prototype: read-only local diagnostics adapter + DiagnosticReport contract + proposal-only layer (lifthrasir.py); NO repair execution, NO deployment | contract implemented | verified | current - X.02 executed 2026-11-14 (section 37 workstream 2 of 15; prototype repair/rollback outstanding = X02-T1) |
| 29 | Heimdall | hrabanazviking/Heimdall-SL-Hermes-Agent | NONE - no pin taken at X.03 (separate bridge service; no installable Hermes-side package; audited HEAD recorded in the lock) | cee7ce679b2070708cee59d476bdd9397dbd9f86 (development, ls-remote 2026-11-14; no tags; no main branch) | none - no LICENSE file at audited HEAD; README states license yet to be determined (X.03, 2026-11-14); no source incorporated | volmarr-core 0.26.0 - prototype: read-only presence adapter over the bridge Core IPC status command + presence-context v1 contract (qualified observations, never world truth) + action-permission gate, every write refused by name (heimdall.py); NO login, NO grid session | contract implemented | verified | current - X.03 executed 2026-11-14 (section 38 workstream 3 of 15; live grid session proof outstanding = X03-T1, Second Life bot-terms re-check before activation = X03-T2) |

Verification tally: **24 verified / 4 partially verified (rows 9, 10,
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
2. License texts unverified: Hamr (row 15,
   E.13), SRD (row 22, E.12),
   Open-LLM-VTuber (row 18, no reliance — informational).
3. Per-engine upgrades E.01–E.18: none executed in W08. Each starts
   with the engine's own suite in its own tree (§13 step 3); pins
   move one engine at a time, each with its own lock revision.
4. Ravens distribution (E.04): RESOLVED 2026-11-13 — the W08-era
   "no repo" record was stale: hrabanazviking/Huginn-and-Muninn-Ravens
   was created by Volmarr on 2026-10-31 with the 1.0.0 packages
   published the same day, byte-identical to the pinned tree; the
   new-machine route (clone as sibling `ravens`, select the
   `volmarr-ravens` extra) is proven in E04_RAVENS_DISTRIBUTION.md.
   Remaining: repo-HEAD package growth at unchanged version 1.0.0
   (E04-T1) and the pin tree having no git remote (E04-T3).
5. COMPAT_MANIFEST.md: still absent from the tree (Phase 0
   find-verified; W00.05 fixture archive remains open) — this
   matrix + lock are the living compatibility record meanwhile, and
   nothing here pretends the manifest exists.
6. W00.03-ENC (backup encryption) still awaits Volmarr's word —
   untouched by W08, not re-asked.
