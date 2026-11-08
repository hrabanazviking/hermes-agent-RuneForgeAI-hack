# W00.06 — Public/Private Repository Boundary Review (Team 01)

Campaign: Hermes Modernization (2026-11-07). Wave W00 closure slice.
Base tree: banked main f7f6a56a2442661896fe8b4fbb54aa2e21c95de0.
Host: purplelongship, worktree ~/hermes-team-01 (branch
 yrsa/hermes-team-01, fast-forwarded to banked main before audit).
Date: 2026-11-08. Method: git ls-files / git grep / tree diffs
against the upstream v0.23.0 pin 2bd378ed1b8d6bf2192cb26e0a55ff3091e6bd19.
This review reports COUNTS and PATHS only — no secret value was
copied into this document, any commit, or any log.

## Verdict

CLEAN, with one minor hardening recommendation (§2). No real secret,
credential, private key, database, or archive is tracked in git. No
boundary defect requiring a code change was found; no code was
changed by this slice.

## 1. What the fork adds to upstream (the boundary surface)

`git diff --name-only 2bd378ed1b HEAD` = 333 files. Breakdown:

- plugins/: 117 files — 100% inside the nine fork plugins
  (volmarr-core 79, volmarr-voice 10, volmarr-hamr 7,
  volmarr-tarot 4, volmarr-smidja 4, volmarr-seidr 4, volmarr-rpg 3,
  volmarr-astrology 3, kista-secret-source 3). ZERO upstream plugin
  files differ from the pin. §0.2 confinement holds exactly.
- tests/: 139 files — 137 in tests/plugins/ (the fork contract
  suites), 1 in tests/scripts/, 1 in tests/pm/ (guarded-intake / U2
  test touches, ledgered).
- docs/: 27 files — 26 under docs/modernization/ (this campaign's
  own record) + integration-lock.json; website/: 2 files, the fork's
  secret-source plugin documentation pages.
- Core (non-plugin, non-test, non-doc): exactly 10 files —
  agent/redact.py, agent/secret_sources/registry.py,
  pm/environment.py, pm/extras.py, pyproject.toml, uv.lock,
  scripts/generate_sbom.py, scripts/sync_upstream.py,
  scripts/u2-cold-install.sh, scripts/verify_wyrd_persistence.py.
  Each is a guarded-intake, dependency-safety (U2), or SBOM touch,
  and each carries a CUSTOMIZATIONS.md ledger row (spot-verified:
  the intake union row, the PyYAML restoration row, the ravens
  declaration row naming pm/extras.py + pyproject.toml + uv.lock).
- Repo root: Volmarr's own authored documents (the four roadmaps,
  MYTHIC_ENGINEERING.md, the Heathen Third Path canon documents,
  the Cyber-Viking design lawbook + codex, his writings/philosophy
  file, and 2 author images). These are his writings in his personal
  fork, tracked by design — the §0.2 ground rule is that authored
  documents are never silently trimmed. They contain no credentials
  (see §3/§4) and their presence is his own publishing choice on his
  own repository; this review records the fact and makes no change.

## 2. .gitignore coverage

The tracked .gitignore is byte-identical to the upstream pin and is
strong: .env + .env.local/.development/.test/.production variants,
*.pem, *.ppk, privvy*, /auth.json, /.anthropic_oauth.json,
/google_token.json, /slack_tokens.json, /config.yaml, /credentials/,
/vault.key, /vault.json.enc, /mcp-tokens/, root *.db + WAL/SHM
sidecars, /profiles/, /memories/, /backups/, *.tar.gz, node_modules,
.hermes/ runtime state, and the flat-install runtime-state block are
all covered.

Minor gap (recommendation, not a defect): there is no GENERIC
*.key, id_rsa*, or *.p12 pattern — coverage is by specific name
(vault.key) and sibling patterns (*.pem, *.ppk). Present exposure is
zero (§3: no such file is tracked), and runtime key material lands
in the name-covered paths above. Recommendation for a future
upstream-side or ledgered fork-side touch: add *.key, *.p12,
id_rsa* to .gitignore. Not changed here: .gitignore is upstream's
file, and altering it is a core divergence that belongs in a
ledgered slice, not an audit slice.

## 3. Tracked files that look secret-adjacent (filename scan)

- 189 tracked paths match .env/secret/credential/.pem/.key/id_rsa
  name patterns. Inspection by path shows they are credential-
  HANDLING code, tests, and docs (agent/credential_*.py,
  agent/secret_sources/*, hermes_cli/secrets_cli.py, desktop
  credential UI, plugin-catalog secret-tool descriptors) — the
  subsystem that manages secrets, not secret values.
- Tracked .env*: exactly 2 files — .env.example and .envrc, both
  byte-identical to the upstream pin (templates, not live config).
- Tracked files with risky extensions (.db/.sqlite/.sqlite3/
  .tar.gz/.tgz/.zip/.pem/.key/.p12/.pfx/.ppk): 0.

## 4. Secret-value pattern scan (counts and paths only)

`git grep` over HEAD for seven high-signal value shapes:

| Pattern | Files |
|---|---|
| Private-key header (BEGIN ... PRIVATE KEY) | 8 |
| AWS access key id (AKIA + 16) | 6 |
| GitHub token (ghp_ + 30 or more) | 5 |
| GitHub fine-grained PAT (github_pat_) | 0 |
| OpenAI-style key (sk- + 32 or more) | 6 |
| Slack token (xox[baprs]-) | 19 |
| Google API key (AIza + 30 or more) | 1 |

41 unique files hit at least one pattern. EVERY hit file is test,
fake-provider, eval, or redaction-test material (tests/agent/
test_redact.py, tests/tools/test_*redaction*, tests/fakes/providers/*,
tests/gateway/test_slack*, tests/hermes_cli/test_auth_provider_gate.py,
apps/desktop notarize scripts and preview tests, and kin), and EVERY
hit file is byte-identical to the upstream v0.23.0 pin (verified by
per-file tree diff: zero differ). These are upstream's synthetic
canaries for its own redaction/auth test suites — the same class the
fork's Kista canary contracts plant deliberately. No hit file is
fork-authored or fork-modified, and no value was reproduced here.
Finding: no real secret is tracked. No rotation, history rewrite, or
removal is warranted — rewriting upstream test fixtures would itself
be an unledgered divergence and would break the redaction suites
that depend on the canaries.

## 5. Personal / private material checks

- Volmarr's email addresses in tracked Python code: 0 files
  (git grep over *.py for either address).
- Personal/fork code outside its boundary: none found — §1 shows
  plugin divergence confined to the nine fork plugins, campaign
  documents under docs/modernization/, and the 10 ledgered core
  files. Upstream code carries no Volmarr-private material: the
  only upstream-tree differences are the 10 ledgered files above,
  and the §4 canary files are upstream's own, byte-identical.
- Runtime/private state (profiles, memories, credentials, vault,
  databases) lives under ~/.hermes and the name-covered ignore
  rules in §2; the W00 backup of that deployment sits outside the
  repo at ~/hermes-backups/2026-11-07-w00/ (its encryption remainder
  is W00.03-ENC, out of scope for this slice and not re-asked here).

## 6. Honest remainders of this review

- Filename + pattern scanning cannot prove the absence of a secret
  in an unrecognised shape, an encoded form, or inside the 2 tracked
  author images / binary files; the scan covered text via git grep
  and names/extensions exhaustively. No such indication was found.
- Repository VISIBILITY (public vs private on GitHub) cannot be
  proven from the laptop checkout (blob:none partial clone, no gh
  query run in this slice); the boundary facts above hold either
  way, and visibility is Volmarr's own account setting.
- The §2 .gitignore hardening recommendation is the only follow-up
  this review raises; it is a recommendation, not a discovered leak.
