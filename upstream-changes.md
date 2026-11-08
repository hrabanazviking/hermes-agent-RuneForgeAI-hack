# Upstream Changes - v0.23.0 Intake (2026-11-07)

W01 / Phase U1 record for `ROADMAP_HERMES_MODERNIZATION_UNBOUNDED_PERSONA_2026-11-07.md` section 4.
Produced on branch `integration/upstream-2026-11-07` (Team 02, sole writer), purplelongship.

## Pin and provenance (W01.01)

- Personal freeze: `281843f10fb0d2c6ca6ee7dab9e99070f7e141ba` (origin/main at intake).
- Selected upstream: official release tag `v0.23.0` (tag object `df1774294af26285ae758c6114f3f2f60e2a602d`), peeled commit `2bd378ed1b8d6bf2192cb26e0a55ff3091e6bd19` (2026-11-05).
- Merge-base is exactly `6bb377a51d5c8e279a7a5e34d717d653d421d064` (the 2026-10-30 intake), so this intake is the 1,792 upstream commits since that intake.
- Upstream `main` was reviewed, not chased: at intake it stood at `30c8a273da711a2f20c9b6889d4ad2f65e566b70`, 1,153 commits past the pin, and had already moved 3 times in the preceding day (2852-commit reading at `334f66b835` during Phase 0). Per roadmap section 4, the reviewed release pin governs.
- Reviewed merge commit: `6d8a10d38335479a3524ffc35127fa5e06a9b0c1`, parents = freeze + pin.
- Diff of the merge: 2,171 files changed, 94,802 insertions, 17,434 deletions. By area (files): apps/ 578, tests/ 472, hermes_cli/ 114, gateway/ 104, ui-tui/ 74, agent/ 73, tools/ 52, web/ 30, plugins/ 27, pm/ 18, skills/ 10, cron/ 7, plus pyproject.toml, uv.lock, package.json, package-lock.json.

## Procedure (W01.02) and one recorded deviation

- Followed `UPSTREAM_SYNC.md` and `scripts/sync_upstream.py`. The script fetches a moving branch by default; to merge the reviewed pin instead of unstable `main`, the peeled pin was placed at the remote-tracking ref `upstream/v0.23.0-pin` and the script was run in its own supported `--no-fetch --branch v0.23.0-pin` mode. Everything else (clean-tree refusal, no-commit no-ff merge, README restoration, conflict reporting) ran exactly as documented. The named `upstream` remote was added per the doc one-time setup (HTTPS URL; origin untouched).
- README proof: sha256 `83a8c2b4b82b068d9f36c2a015e6e42c49b05fa2198e780d152c4d85c79ae0f4` before the merge, after the merge, and after the merge commit - byte-identical.

## Conflicts: exactly one (W01.02, W01.09)

Pre-merge watch-list: of the 264 files the fork has customized since the merge-base, upstream also changed exactly 4: `agent/redact.py`, `pm/extras.py`, `pyproject.toml`, `uv.lock`. Three auto-merged cleanly and were hand-verified to keep the fork side (pyyaml==6.0.3 line, `volmarr-ravens` extra + `[tool.uv.sources]` editable ravens paths, `pm.extras.ANCHORS` ravens row, the redact.py vault-comment union and the `redaction_scope` applier in `agent/secret_sources/registry.py`, the last untouched upstream this round).

1. `uv.lock`, one hunk in the hermes-agent dependency list. Fork side carried the `muninn` editable line (`extra == 'volmarr-ravens'`) plus the old `nemo-relay >=0.10,<0.11` specifier; upstream side carried the bumped `nemo-relay >=0.11,<0.12` specifier and no muninn line. Resolution: minimal union - keep the muninn editable line AND take the upstream nemo-relay bump (the merged lock package entry is nemo-relay 0.11.0, consistent). Neither side taken whole. Proof the union is a valid lock: `pm` installed the environment hash-verified via this uv.lock for every test run below, and both TOML files parse.

## Compatibility notes (roadmap 4.2; W01.03-W01.07)

- Single gateway-owned sessions: gateway/ changed 104 files and 6 `hermes_state_*` siblings changed (the `hermes_state.py` facade and `agent/prompt_builder.py` and `tools/memory_tool.py` did not change). The fork surfaces here are additive plugin hooks only; the full `tests/hermes_state` suite passes on the merged tree (below), and all Volmarr contract files pass except the known live-transport set. Live cross-surface session-owner wiring remains W05 work per WAVE_PLAN; nothing in this intake changes fork behavior there.
- Bot/group routing, rewind/fork, remote Desktop: upstream-owned surfaces; no fork file intersects them (fork-customized intersect was only the 4 files above). No fork change needed at intake; live verification belongs to the W05/W08 units that own those surfaces.
- Plugin lifecycle: upstream `plugins/` changes are platform adapters plus `plugins/memory/config_schema.py`; no volmarr-* or kista file was touched. Post-merge `hermes plugins list` discovers all 9 fork plugins as bundled at their frozen versions (volmarr-core 0.26.0, volmarr-voice 1.0.0, volmarr-astrology 0.7.0, volmarr-rpg 0.8.0, volmarr-seidr 0.4.0, volmarr-tarot 0.3.0, volmarr-hamr 0.4.0, volmarr-smidja 0.1.0, kista-secret-source 0.2.0).
- Paid-tool gates / telemetry: no fork customization intersects; Hermes accounting surfaces arrived with upstream and are inherited unchanged. RuneForge policy combination is later-wave work, not an intake edit.

## Verification (W01.06, W01.08) - all via scripts/run_tests.sh on purplelongship

- Volmarr/Kista contracts (117 files): 929 passed, 7 failed, 1 skipped. The 7 failures are in exactly 3 files (`test_volmarr_core_plugin.py` 5, `test_volmarr_verdandi_stimuli.py` 1, `test_volmarr_voice_runner.py` 1) and are live-transport tests (real Verdandi unix socket, real discovery, real loopback runner - no live Verdandi service runs on this laptop).
- Baseline proof: the same 3 files run on the untouched freeze tree on this host give 4 passed, 7 failed, with the 7 failed test names byte-identical to the merged tree. Zero intake regressions; the 7 are pre-existing environmental, as recorded in the 2026-10-30 campaign.
- Targeted upstream suites (redact + secret-scope/source files in tests/agent, plus all of tests/hermes_state): 222 files, 2,355 passed, 0 failed, 16 skipped.
- Native smoke: CLI entry runs on the merged tree (`Hermes Agent v0.22.5+3368.g281843f.dirty` pre-commit describe; exit 0) and plugin discovery passes (above). Environment staged hash-verified via pm + uv.lock from a tree directly under $HOME, so the `../ravens` editable binding resolves to the present `~/ravens` tree (HEAD fc761f0) - see Team 03 U2 audit for the location-relative staging caveat.

## Not in this intake / deferred honestly

- The full upstream test suite was not run (selected suites per the W01 gate were). W00.04 baseline for the remaining contract files and W00.07 offline-install recipe still close inside U2.
- `hermes pm lock` regeneration was not attempted; the lock was union-resolved by hand and then proven by hash-verified installs. The ravens release-age relock gate remains a U2 item.
- Nothing was pushed. Banking to main is the keeper/coordinator step after review.
