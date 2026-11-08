# E0 Integration Ledger - DRAFT (Team 09, W08 opens)

Status: DRAFT for the keeper to bank in wave order. This is the Phase E0
working ledger behind docs/modernization/INTEGRATION_MATRIX.md and the
verified integration-lock.json. It is NOT the verified lock yet: W00
(Team 01) verifies integration-lock.json rows first, and this draft is
promoted only inside W08. Nothing here was guessed.

## How this draft was measured

- Host/tree: purplelongship, worktree ~/hermes-team-09 on branch
  yrsa/hermes-team-09 (WAVE_PLAN.md names the branch
  team-09/w08-e0-ledger - discrepancy flagged for the keeper to
  reconcile; the task brief's branch name was used).
  Worktree HEAD == main tree HEAD ==
  281843f10fb0d2c6ca6ee7dab9e99070f7e141ba. No drift: the main tree
  had not moved since the Phase 0 recon (~21:33 EST).
- Current HEADs: fresh `git ls-remote <repo> HEAD` run by Team 09 on
  purplelongship at 2026-11-07T21:37:18-05:00. Every current HEAD
  below matched the Phase 0 baseline table exactly (no engine moved
  between Phase 0 and this draft).
- Tags: `git ls-remote --tags` at 2026-11-07T21:37:31-05:00.
- Licenses: two sources, named per row - COMPONENT_LICENSES.md in
  this fork (its own ledger) where a row exists there, otherwise the
  GitHub API license detection for the repo root
  (`gh api repos/<owner>/<repo>` -> license.spdx_id), read
  2026-11-07 ~21:38 EST. NOASSERTION means a license file exists but
  GitHub could not classify it; NONE means none was detected.
- Adapter levels: judged from the plugin manifests
  (plugins/*/plugin.yaml) and the adapter code itself in this tree,
  cited per row. Plugin manifest versions are plugin versions, NOT
  engine versions (roadmap section 0.1).
- COMPAT_MANIFEST.md does not exist in this tree (Phase 0
  find-verified); its fate is a W00 ticket, recorded here so the
  ledger does not pretend it exists.
- Adapter-mode words follow roadmap section 13: documented /
  probe-only / read-only / deterministic tool / full read-write /
  realtime / prototype / design-only.

## Ledger (24 rows)

| # | Engine / project | Repo | Fork pin (source) | Current HEAD (2026-11-07 21:37 EST) | Latest tag/release | License | Adapter in this fork (plugin + mode) | Verdict |
|---|---|---|---|---|---|---|---|---|
| 1 | Verdandi | https://github.com/hrabanazviking/Verdandi | dc7139416ef4bb67c9ba29c1148615d0d259b7db (COMPONENT_LICENSES.md) | 2fc9db8bf555546ab96084f74b1d442b8e1c7a63 | v0.3.0 (tag 1b27ee2aefe8) | MIT (COMPONENT_LICENSES.md; API agrees) | volmarr-core 0.26.0 - realtime: opt-in fail-open lifecycle event publish over Unix socket + health/stimuli (plugins/volmarr-core/verdandi.py, verdandi_stimuli.py) | update - E.01 |
| 2 | Project A.E.S.I.R. | https://github.com/hrabanazviking/RuneForgeAI-Project-Aesir | c1a4410ca254fa388e45936b02230999d0906a4c (COMPONENT_LICENSES.md) | d9f88b9a65531dfaf48b22df167d75d45d43ca50 | only tag seen: mimisbrunnr-v1.0 | AGPL-3.0 (COMPONENT_LICENSES.md; API agrees) | volmarr-core 0.26.0 - deterministic tool: bounded loopback OpenAI-compatible health/catalog/completion + route decisions (plugins/volmarr-core/cognition.py, routing.py) | update - E.02 |
| 3 | Bifrost / Mimir | https://github.com/hrabanazviking/bifrost | b66e98cc8a79d4dede22ba11d68a1a5ecd22ebd6, v1.0.0 (COMPONENT_LICENSES.md) | 99988dbb638d1b4f35f4a07590d61ad08b72ebd8 | no tags | MIT (COMPONENT_LICENSES.md; API agrees) | volmarr-core 0.26.0 - probe-only: profile-local read-only Mimir/Muninn probes; bridge construct-only, every write flag forced False (plugins/volmarr-core/memory_fabric.py lines 71-73) | update - E.03 |
| 4 | Muninn (ravens) | NO GitHub repo (Volmarr's alone to create) | local ravens tree fc761f0, pkg 4eafc31, v1.0.0 (COMPONENT_LICENSES.md) | n/a - canonical tree on the VM at ~/workspace/ravens, ABSENT on purplelongship (verified 2026-11-07) | none | MIT (COMPONENT_LICENSES.md) | volmarr-core 0.26.0 - full read-write behind default-off operator flags (plugins/volmarr-core/ravens.py, ravens_writes.py) | pin-first - E.04 distribution blocker |
| 5 | Huginn (ravens) | NO GitHub repo (Volmarr's alone to create) | local ravens tree fc761f0, pkg 54dd839, v1.0.0 (COMPONENT_LICENSES.md) | n/a - same absence as Muninn | none | MIT (COMPONENT_LICENSES.md) | volmarr-core 0.26.0 - full read-write behind default-off flags, constructed DIRECTLY only; through-Bifrost path is NO-GO (plugins/volmarr-core/ravens.py header) | pin-first - E.04 distribution blocker |
| 6 | MemPalace (official) | https://github.com/MemPalace/mempalace | v3.10.0 at 22fd87f09c19d5ffb2d6966486483353937931c0 (COMPONENT_LICENSES.md) | fa6ae179d852dd145d33cfee2a37db5b346c45b3 | v3.11.0 (newest tag, version-sorted) | MIT (COMPONENT_LICENSES.md; API agrees) | volmarr-core 0.26.0 - read-only: version-checked probe (MINIMUM_PACKAGE_VERSION 3.10.0) + opt-in default-off SQLite BM25 retrieval (plugins/volmarr-core/mempalace.py, mempalace_retrieval.py) | update - E.05 |
| 7 | MemPalace (Volmarr mirror) | https://github.com/hrabanazviking/mempalace | ff1bdf03407bc5d6c571fa85f8c621d7177de616 (COMPONENT_LICENSES.md) | ff1bdf03407bc5d6c571fa85f8c621d7177de616 - MATCHES pin | (mirror of official tags) | MIT (API) | none - mirror held as reference/fallback source only | reference-only |
| 8 | OpenViking (official) | https://github.com/volcengine/OpenViking | v0.4.21 at 3fca2577520f00b7f580d85d4ac6ae42bb9ba6f1 (COMPONENT_LICENSES.md); Slice 84 audit pinned server 0.5.x at e855796c83f9 (= tag v0.5.1) | 9ac008f9b86c91b79d6e93eb8df8ea7f4d48cecb | v0.5.3 (tag 178a8cdfb41b) | AGPL-3.0 (COMPONENT_LICENSES.md; API agrees) | volmarr-core 0.26.0 - probe-only + read-only: loopback /health probe (MINIMUM_SERVER_VERSION 0.4.21) + opt-in memories-only /find retrieval (plugins/volmarr-core/openviking.py, openviking_retrieval.py) | update - E.06 |
| 9 | OpenViking (Volmarr mirror) | https://github.com/hrabanazviking/OpenViking | NONE recorded (also unpinned - found at E0, beyond the seven named in the brief) | cbf8befcea5736f3b316a6c12e84ba11c40b31c4 | not measured | Apache-2.0 (API - differs from official AGPL-3.0; mirror carries its own terms, verify at E.06) | none - mirror reference only | reference-only |
| 10 | WYRD Protocol | https://github.com/hrabanazviking/WYRD-Protocol-World-Yielding-Real-time-Data-AI-world-model | v1.0.0 at 9884ce8a9e683dc20f372a91eb66ba5b02561300 (COMPONENT_LICENSES.md) | HEAD (default branch development) 89ed09394c7e13b2e63f91e342fbab8ff9890cbc; main 7df509e9140793d8b7bae91bb1d35c466be1d887 | only tag/release: v1.0.0 (tag f3dfb1a27c0a) - see WYRD reconciliation below | CC BY 4.0 per COMPONENT_LICENSES.md; GitHub API detected NONE at repo root - E.07 must verify the in-repo license text | volmarr-core 0.26.0 - read-only probe + bounded world get/query + confirmed set/observe (plugins/volmarr-core/wyrd.py: MINIMUM_SERVER_VERSION 1.0.0, API contract wyrd-http-v1) | update - E.07 |
| 11 | Kista | https://github.com/hrabanazviking/kista | v2.0.0 at ce6313cc392589abd43a5fcf614e0e272663961f (COMPONENT_LICENSES.md) | 41a6d65863af9ec5d41ca148828a0b6863605b86 | no tags (pin by SHA) | MIT (COMPONENT_LICENSES.md; API agrees) | kista-secret-source 0.2.0 - read-only: Secret Source get via plugin API, redaction-scoped (plugins/kista-secret-source) | update - E.08 |
| 12 | Astrology Engine | https://github.com/hrabanazviking/astrology-engine | 1709fcfc1e00198ab0f25fe4889868a7245cf014 (COMPONENT_LICENSES.md) | bb4ede4fbb326d21df34a5ca0ca6e343f4f49fbe | not measured | Apache-2.0 (COMPONENT_LICENSES.md; API agrees) | volmarr-astrology 0.7.0 - deterministic tool: fixed-argv bounded subprocess against a local checkout (plugins/volmarr-astrology/plugin.yaml) | update - E.09 |
| 13 | RuneTarotEngine | https://github.com/hrabanazviking/RuneTarotEngine | NONE - FIRST PIN ESTABLISHED AT E0 (below) | 432e461136ba58cb3e507bb9cd86b4bb2faba80b | no tags | MIT (API) | volmarr-tarot 0.3.0 - deterministic tool: seeded draws via bounded subprocess against a local checkout (plugins/volmarr-tarot/plugin.yaml) | pin-first - pin established at E0; audit E.10 |
| 14 | Seidr Engine | https://github.com/hrabanazviking/seidr-engine | NONE - FIRST PIN ESTABLISHED AT E0 (below) | fdc2b3c85c62982a4550dfe476751287d723519d | no tags | MIT (API) | volmarr-seidr 0.4.0 - deterministic tool: seeded composition via bounded subprocess (plugins/volmarr-seidr/plugin.yaml) | pin-first - pin established at E0; audit E.11 |
| 15 | Hamr | https://github.com/hrabanazviking/Hamr | NONE - FIRST PIN ESTABLISHED AT E0 (below) | f77aa588601b38a69b6c1fc0a6733ed5e95dffa8 | v0.7.0 (peeled 45f6704fdd52) | NOASSERTION (API - license file present, unclassified; verify text at E.13) | volmarr-hamr 0.4.0 - read-only: spec/budget/artifact preflight only, engine_root must contain src/hamr/core/spec.py (plugins/volmarr-hamr/plugin.yaml) | pin-first - pin established at E0; audit E.13 |
| 16 | Seidr-Smidja | https://github.com/hrabanazviking/Seidr-Smidja | NONE - FIRST PIN ESTABLISHED AT E0 (below) | 32cdbd7a87358bc1f6f046c4e1449c35f4d5d40a | no tags | Apache-2.0 (API) | volmarr-smidja 0.1.0 - read-only: Loom/Hoard/Gate/Oracle Eye preflight (plugins/volmarr-smidja/plugin.yaml) | pin-first - pin established at E0; audit E.14 |
| 17 | AIAvatarKit | https://github.com/hrabanazviking/aiavatarkit | NONE - FIRST PIN ESTABLISHED AT E0 (below) | 9295e096169316ec19e9fa712e52733d912fd5e7 | no tags | Apache-2.0 (API) | volmarr-voice 1.0.0 - prototype: pure presentation-shape translation only; to_aiavatarkit_response invokes NO AIAvatarKit pipeline (plugins/volmarr-voice/aiavatarkit.py line 18) | pin-first - pin established at E0; audit E.15 |
| 18 | Open-LLM-VTuber | https://github.com/hrabanazviking/Open-LLM-VTuber | audit-only, no admissible embed at last audit (baseline) | 19b58b1f6c01e082289fce089392997b9d14fbc4 | not measured | NOASSERTION (API) | none - design-only: documented architecture audit, owns its own ASR/TTS/agent loops (roadmap section 13) | reference-only - re-evaluate at E.15 |
| 19 | OmniVoice | https://github.com/hrabanazviking/OmniVoice | NONE - FIRST PIN ESTABLISHED AT E0 (below) | a4068c820f21307df337e34f67d3dda443735ad4 | no tags | Apache-2.0 (API) | volmarr-voice 1.0.0 - design-only today: voice readiness/presentation contracts; grep of plugins/volmarr-voice/*.py on 2026-11-07 found NO OmniVoice code reference | pin-first - pin established at E0; audit E.15 |
| 20 | ChatIndex | https://github.com/hrabanazviking/ChatIndex | NONE - FIRST PIN ESTABLISHED AT E0 (below) | 7df2c9208db6f113f85a6c09295bec7f0f2114e7 | no tags | Apache-2.0 (API) | none - design-only: concept reference in P2/roadmap retrieval design (ROADMAP section 8/15 notes; PERSISTENT_ENTITY_ACCEPTANCE_AUDIT.md Phase 13), no adapter code | pin-first - pin established at E0; audit inside P2/E2 work |
| 21 | MindSpark / ThoughtForge | https://github.com/hrabanazviking/MindSpark_ThoughtForge | concept reference only, no pin claimed | 68aa4d1cd29f6d6c57d1266e70833584c9b1a74e (default branch development per project records) | not measured | NONE detected (API) | none - design-only: reflex concept reference, NO runtime adapter claimed (roadmap section 13) | reference-only |
| 22 | SRD data (dnd-5e-srd) | https://github.com/hrabanazviking/dnd-5e-srd | no SHA pin in licenses | 2e62e0413061c2443e21369cdc074c7a7356a857 | not measured | NOASSERTION (API - SRD content terms; verify at E.12) | volmarr-rpg 0.8.0 - deterministic tool data: external SRD lookup via srd_root checkout (plugins/volmarr-rpg/plugin.yaml) | reference-only - E.12 boundary review |
| 23 | Older fork (provenance) | https://github.com/hrabanazviking/hermes-agent | 761a8559084e7f (Present State) and d423b611799d (Affective) adapted-module pins (COMPONENT_LICENSES.md) | 7d4c90fe7c4dad6bea95f292c5a809f3b88eb498 | not measured | MIT (COMPONENT_LICENSES.md; API agrees) | none live - provenance only: modules adapted into volmarr-core (present_state.py, affective.py), no live adapter | reference-only |
| 24 | Sagnaskemma engine | UNKNOWN - no repo found under hrabanazviking/Sagnaskemma or RuneForgeAI-Sagnaskemma (Phase 0 ls-remote: repository not found) | NONE - no pin possible | n/a | n/a | n/a | none - RPG/SRD row in roadmap section 13 names it as a future adapter (E.12) | pin-first - BLOCKED on canonical repo identification from project records |

## First pins established at E0 (2026-11-07)

These seven engines had NO pin recorded anywhere in this fork before
tonight. Each pin below is the engine repo HEAD measured by Team 09
via `git ls-remote` on purplelongship at 2026-11-07T21:37:18-05:00,
recorded as: pin established 2026-11-07 at E0, previously unpinned.
They are first pins, not long-standing pins, and must never be
presented as such.

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
mirror (row 9, current cbf8befcea5736f3b316a6c12e84ba11c40b31c4) and
SRD data (row 22). E.06/E.12 own their pin decisions.

## E.01-E.03 first engine audits (audit only - no updates made)

Method per roadmap section 13 protocol, audit stage only: commit
counts are `git rev-list --count <pin>..<current>` in blobless
--no-checkout clones made by Team 09 on purplelongship on
2026-11-07 ~21:38 EST (/tmp/t09-verdandi, /tmp/t09-aesir,
/tmp/t09-bifrost, /tmp/t09-wyrd). The per-engine waves must still run
each engine's own tests in its own tree FIRST (protocol step 3)
before any adapter work; nothing was updated in this run.

### E.01 Verdandi - current event protocol and bridge regression

- Delta: pin dc7139416ef4 -> current 2fc9db8bf555 = 67 commits.
  Tags exist to v0.3.0; the fork ledger states no version for its pin.
- What changed (from the 67-commit log): the nerve hub was hardened
  repeatedly - over-limit structured rejects, subscriber keepalive,
  SIGTERM graceful shutdown, supervisor + PID-reuse-safe health
  checks; state honesty work (all-or-nothing loads, corrupt-state
  quarantine, naive-UTC guards); CLI domain errors now exit 2 with
  single-line stderr; mood integration keys; a Telegram-to-nerve
  bridge; a WYRD mirror stack.
- Breaking-change risk to this fork: MEDIUM-HIGH. The fork publishes
  versioned lifecycle metadata (schema runeforge.hermes.lifecycle
  v1, plugins/volmarr-core/verdandi.py) and reads health/stimuli
  (verdandi_stimuli.py). Hub-side reject, keepalive and health
  semantics all changed under that contract, and the bridge is
  fail-open by design - a protocol drift would present as silence,
  not as an error. That is exactly the failure shape E.01 exists to
  catch.
- Exact update proof E.01 needs: (1) Verdandi's own test suite green
  in its own tree at 2fc9db8bf555; (2) fork contract batteries
  tests/plugins/test_volmarr_verdandi*.py via scripts/run_tests.sh
  against the current hub, not a stub; (3) a live socket round-trip
  in a disposable profile: publish a lifecycle event, observe hub
  acceptance (and its reject behaviour over the limit), run the
  stimuli catch-up path; (4) absent-service fail-open proof (no hub
  running -> turns proceed, nothing queued silently); (5) latency +
  metadata-only privacy check per protocol step 7. Only then may the
  ledger pin move.

### E.02 A.E.S.I.R. - inference/quantization/model catalog API

- Delta: pin c1a4410ca254 -> current d9f88b9a6553 = 1,779 commits,
  by far the largest delta in this ledger. The log shows the whole
  Aesir model-wave and Janas lines merged to main (2026-11-01
  merge-to-main sweep) plus, at the head, a Qwen3/Qwen3.8/Qwen-4
  research library (the top ~11 commits are docs-only).
- Breaking-change risk to this fork: HIGH for surface drift, not
  necessarily for breakage. The fork binds a bounded
  OpenAI-compatible loopback endpoint (default
  http://127.0.0.1:18434/v1; catalog capped at 256 models / 256 KiB;
  completion capped at 1 MiB; plugins/volmarr-core/cognition.py) and
  content-free route decisions (routing.py, route schema v2). 1,779
  commits of engine, quantization and catalog work can change model
  IDs, catalog shape and completion semantics while /health still
  answers - a health-only green would prove almost nothing.
- Exact update proof E.02 needs: (1) A.E.S.I.R.'s own suite green in
  its own tree at d9f88b9a6553; (2) a recorded catalog fixture diff:
  the /models payload shape at the pin vs at current, filed as a
  versioned compatibility fixture (protocol step 4); (3) fork
  contracts for cognition/routing via scripts/run_tests.sh;
  (4) a disposable-profile live loopback turn: health -> catalog ->
  one bounded completion -> cancellation, with the local-only mode
  proven to make no external request (roadmap section 14
  acceptance); (5) capability record per host (GPU/NPU/CPU paths
  actually present, never assumed). Only then may the pin move.

### E.03 Bifrost/Mimir - current retrieval and write contracts

- Delta: pin b66e98cc8a79 (v1.0.0) -> current 99988dbb638d = 2
  commits, BOTH docs: 9de12b6 (Second Brain master expansion
  roadmap) and 99988dbb (repository-specific Bifrost integration
  responsibilities). No Bifrost code has changed since the pin.
- Breaking-change risk to this fork: LOW for API drift. The fork's
  surface is a construct-only bridge with all write flags forced
  off (memory_fabric.py) plus read-only Mimir/Muninn probes, so an
  unchanged codebase cannot silently break it. The real E.03 work
  is (a) reading those two docs commits - they may state new
  integration duties this fork must honour before any promotion -
  and (b) the ravens distribution blocker below.
- RAVENS BLOCKER (known, recorded in advance): the canonical
  Muninn/Huginn tree lives on the VM at ~/workspace/ravens
  (tree fc761f0; muninn pkg 4eafc31, huginn pkg 54dd839, both
  v1.0.0, MIT per COMPONENT_LICENSES.md) and is ABSENT on
  purplelongship - verified 2026-11-07 ~21:38 EST: ~/ravens and
  ~/workspace/ravens both absent. This fork's pyproject.toml binds
  muninn/huginn through [tool.uv.sources] to ../ravens (relative to
  the checkout) for the opt-in volmarr-ravens extra. The PyPI
  projects named muninn and huginn are UNRELATED packages (Slice 86
  name-collision record): never install them for this integration,
  never treat a PyPI fallback as a fix. Until the canonical tree is
  brought to this laptop or Volmarr gives the ravens a repo of
  their own (repo creation is his alone), the ravens stay
  package_missing on this host - which is the honest result.
- Exact update proof E.03 needs: (1) Bifrost's own tests green in
  its own tree at 99988dbb638d; (2) both docs commits read and any
  stated integration duties listed against the fork's current
  surface; (3) fork contracts test_volmarr_memory_fabric* and
  test_volmarr_ravens* via scripts/run_tests.sh WITH the canonical
  ravens tree present beside the checkout; (4) read-only proof:
  Muninn store file sha256 identical before/after a probe
  (the Slice 87 standard); (5) write operations (reinforce / decay
  / consolidate / ingest) exercised only behind their default-off
  flags in a disposable profile; (6) absent-ravens proof: probe
  answers package_missing and nothing reaches PyPI.

## WYRD version reconciliation (E.07 advance work)

Question: the fork pin says WYRD v1.0.0, project records elsewhere
claim WYRD v1.5.0. Evidence, all measured 2026-11-07 on
purplelongship:

- Git tags on the WYRD repo: exactly ONE - v1.0.0 at
  f3dfb1a27c0a2a1d1821a3320d38238633778f8f (git ls-remote --tags).
- GitHub releases: exactly ONE - v1.0.0 (gh api .../releases).
  There is NO v1.5.0 tag and NO v1.5.0 release.
- The fork pin 9884ce8a9e68 (2026-09-17) sits 14 commits AFTER the
  v1.0.0 tag, and its pyproject.toml says version = 1.0.0
  (verified by git show in the blobless clone /tmp/t09-wyrd).
  The pin's v1.0.0 label is correct for its commit.
- The CURRENT code says version = 1.5.0 in pyproject.toml on BOTH
  main (7df509e91407) and development (89ed09394c7e), with a
  version-discipline comment (package version tracks development
  phases; src/wyrdforge/__init__.py kept in step - it also carries
  1.5.0). Pin-to-current distance: 73 commits to main, 75 to
  development.
- This fork's adapter requires only MINIMUM_SERVER_VERSION 1.0.0
  (plugins/volmarr-core/wyrd.py), so it attests either version.

Verdict: both records are true about different things. v1.0.0 is
the only tagged/released version and the correct label for the
fork's pin; v1.5.0 is the in-package version of the current,
untagged code - it is not a release. E.07 must pin WYRD by SHA and
record the package version separately, and the WYRD project should
either tag/release v1.5.0 or stop citing it as a release. Records
that say "WYRD v1.5.0 complete" are describing the package version
of the finished work, not a published release.

## Blockers and open items carried forward

1. Ravens tree absent on purplelongship (E.03/E.04) - see audit.
2. Sagnaskemma canonical repo unknown (row 24, E.12) - needs the
   repo name from project records before any pin exists.
3. WYRD license: fork ledger says CC BY 4.0, GitHub detected no
   license at the WYRD repo root (row 10) - E.07 verifies the text.
4. Hamr and SRD licenses are NOASSERTION (rows 15, 22) - E.13/E.12
   verify the actual texts before any compatible badge.
5. Branch-name discrepancy: WAVE_PLAN.md says team-09 branch
   team-09/w08-e0-ledger; this worktree was created as
   yrsa/hermes-team-09 per the task brief. Keeper reconciles at
   banking time.
6. This draft is UNCOMMITTED in ~/hermes-team-09 by design; the
   keeper banks serially in wave order. W08 depends on earlier
   waves banking first, so no promotion of this draft into
   INTEGRATION_MATRIX.md happens in this run.
