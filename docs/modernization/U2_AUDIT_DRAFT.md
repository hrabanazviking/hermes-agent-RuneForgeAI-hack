# U2 Audit Draft — Phase U2: Dependencies, Trust and Deployment

Team 03 (W02 prep), 2026-11-07. Status: DRAFT, uncommitted, in worktree
`~/hermes-team-03` (branch `yrsa/hermes-team-03`; WAVE_PLAN.md names the
branch `team-03/w02-u2-deps` — the one existing team branch on disk,
team-09's, uses the `yrsa/hermes-team-NN` form, and this draft follows
that precedent; the keeper should reconcile the naming once).

Scope note: W02 formally follows W01 (Team 02's guarded upstream
intake, in flight in parallel). Nothing in this draft changes
`pyproject.toml` or `uv.lock`. All findings below were verified from
disk/git on purplelongship on 2026-11-07 unless marked otherwise.

## 0. Headline findings

1. The ravens blocker is already cleared on this machine — see §1.
   `uv lock --check` and `uv lock --dry-run` both pass in a scratch
   copy of the fork's pyproject/uv.lock (358 packages resolved, no
   lockfile changes). The remaining lock problem is only the
   `hermes pm lock` release-age gate (§3).
2. PyYAML: upstream v0.23.0 carries no PyYAML at all; the fork's
   `pyyaml==6.0.3` core pin exists solely for volmarr-core. Its
   6.0.3 wheels cover x86_64 and ARM64 on the 3.14 line, so keeping
   the pin is wheel-safe today (§2).
3. There is still no launch recipe on the laptop: no `hermes` on
   PATH, no systemd user unit, and `~/.hermes` is a dormant profile
   (SOUL.md dated 2026-05-24). A native recipe is designed in §4,
   design only — nothing was installed.

## 1. Ravens tree: present, byte-identical, tests green

The brief for this run said no ravens tree exists on purplelongship.
Live disk says otherwise — checked before any transfer was attempted,
and nothing was overwritten:

- `~/ravens` exists on purplelongship (landed 2026-10-30/31, the
  original integration era). `git rev-parse HEAD` =
  `fc761f020b39f9be875310d271aac7423239d5f8`, identical to the
  canonical VM tree at `~/workspace/ravens`.
- Full manifest comparison (all 72 non-`.git` files, sha256 per file,
  `LC_ALL=C sort -k2` on both sides): identical manifest hash
  `4bc71fad19039edd56810d48ec41e4e34466bcd9421840d6d5fcb2c1ca517f65`
  on both machines. (An unsorted/first-pass comparison differed only
  by locale collation order, not by any file hash.)
- Both trees carry the same single uncommitted change:
  `BUILD_STATE.md` +14 lines (the 2026-10-31 GitHub publication note).
- Package versions: muninn 1.0.0, huginn 1.0.0 (both pyprojects),
  zero runtime dependencies each.
- Test suites run ON THE LAPTOP in a fresh venv
  `~/ravens/.venv-laptop` (uv-managed CPython 3.12.13, pytest 8.4.2,
  both packages installed editable from the local paths only):
  muninn **36 passed**, huginn **27 passed** — the canonical counts
  from BUILD_NOTES.md. First run failed at collection only because
  the src-layout packages were not yet installed into the venv;
  recorded here so nobody re-chases it.

The fork binds the ravens from `~/hermes-hack-forge` as
`../ravens` = `~/ravens` (§ verified), and Team 03's own worktree
`~/hermes-team-03` and Team 02's `~/hermes-team-02` sit at the same
depth, so the relative binding resolves identically there.

Probable cause of the original "missing tree" report: the binding is
location-relative and the comment in `pyproject.toml` says
"~/workspace/ravens beside this checkout", which is the VM layout;
on the laptop the sibling is `~/ravens`. Any staging attempt run
from a tree NOT placed directly under `$HOME` (or from a deeper
scratch path) breaks the relative path and presents exactly like a
missing tree.

## 2. (a) pyyaml==6.0.3 reconciliation

Facts:

- Upstream `NousResearch/hermes-agent` at tag `v0.23.0` (fetched
  2026-11-07 from raw.githubusercontent.com): its `pyproject.toml`
  contains **no PyYAML**. The YAML stack is `ruamel.yaml==0.18.16`
  plus `ruamel.yaml.clib==0.2.15` (both with
  `python_version >= '3.14'` markers), behind the `hermes_yaml`
  wrapper; the comments record why (0.18.17's clib lacks a Windows
  ARM64 wheel; pure-Python parsing cost ~5 s of gateway startup).
- The fork's core list carries `pyyaml==6.0.3` (pyproject lines
  61–65) with the recorded reason: volmarr-core plugin modules
  import `yaml` directly for the entity ledgers; upstream dropped
  PyYAML in the ruamel migration; the pin was restored at intake
  2026-10-30 (see CUSTOMIZATIONS.md).
- Actual volmarr-core usage (grep, 2026-11-07): 9 modules import
  `yaml` — autonomy, curiosity, drives, goals, identity,
  persona_canon, persona_runtime, relationships, self_model —
  roughly 10 `yaml.safe_load` call sites and 10 `yaml.YAMLError`
  catches. No file under `agent/` or `hermes_cli/` imports PyYAML.
- Wheel coverage for `pyyaml==6.0.3`, verified against the PyPI
  JSON metadata (73 files): cp314 wheels exist for
  manylinux x86_64 and manylinux aarch64 (plus musllinux both
  arches, macOS arm64, win_arm64). The roadmap's x86_64 + ARM64
  wheel test therefore passes at the metadata level; an installed-
  wheel smoke on real ARM64 hardware remains a W02 ticket (Mimir
  is the house ARM64 box).

Options, ranked:

1. **Keep `pyyaml==6.0.3` as a fork-owned core pin (recommended
   for U2).** Zero code risk; wheels proven on both target arches;
   the divergence is one line plus its comment, already ledgered.
   The U2 gate is reproducibility, not minimalism.
2. **Demote PyYAML to a volmarr-core-scoped extra / PM-managed
   plugin dependency.** Cleaner upstream alignment, but plugin
   dependency staging is the surface with the release-age gate
   (§3) and the quarantine history; a staging miss means the
   plugin's entity ledgers fail at runtime. Revisit only after
   the §3 fix lands and plugin env staging is proven offline.
3. **Migrate the 9 modules to `hermes_yaml` (ruamel) and drop
   the pin.** Removes the divergence entirely, but ruamel's API
   and error types differ from PyYAML's, and these modules guard
   byte-sensitive entity stores (create-once, symlink/size
   validation). Highest risk of the three; would need the full
   volmarr contract battery per module. Not U2 work; a possible
   later P-phase cleanup, honestly recorded as such.

## 3. (b) The lock-regeneration gate (`hermes pm lock`)

The gate: `pyproject.toml` `[tool.uv]` sets
`exclude-newer = "3 days"` (the release-age quarantine; only
`certifi` is exempted via `exclude-newer-package`). uv's seeded-lock
diagnostic for an undated package is "has no publish time"
(`pm/environment.py` maps it to an index-fault error with
UNDATED_INDEX_HINT). The ravens' lock entries
(`source = { editable = "../ravens/..." }`) have no upload time by
construction — they are not index packages — so PM's lock path
refuses to regenerate a lock containing them. This was already the
recorded deviation of 2026-10-31: the lock on disk is the plain
resolver's own consistent output.

Reproduction status: the refusal was NOT re-run end-to-end in this
prep (running `hermes pm lock` needs a staged PM environment and
Team 02 owns the integration branch). The mechanism is fully
traceable in source, as above, and plain `uv lock` was proven as
the control case in scratch dir `~/hermes-u2-scratch` (copies of
the fork's pyproject.toml + uv.lock, nothing else touched):

- `uv lock --check` → exit 0, "Resolved 358 packages in 623ms"
- `uv lock --dry-run` → exit 0, "Resolved 358 packages in 379ms",
  "No lockfile changes detected"

So the editable sources resolve, from `~/ravens`, with no PyPI
fallback for the names muninn/huginn (SUPPLY-CHAIN LAW: the PyPI
projects of those names are unrelated software; the
`[tool.uv.sources]` binding is what makes fallback impossible,
and it must stay).

Fix shape (does NOT weaken supply-chain rules):

1. Short term (process): keep regenerating with plain `uv lock` +
   `uv lock --check`, and ledger the deviation in
   CUSTOMIZATIONS.md per intake, exactly as 2026-10-31 did. The
   release-age quarantine still applies to every registry package,
   because plain uv honours `[tool.uv] exclude-newer` for index
   sources; local sources were never datable and gain no new
   trust by being skipped.
2. Proper fix (in PM, a U2 slice of its own): teach the lock path
   to scope the age gate to registry sources only. Concretely,
   pre-flight the resolved source table; for each
   `[tool.uv.sources]` entry whose source is a local path, pass a
   per-package exemption (`exclude-newer-package` semantics) for
   that name only, and stop classifying its "has no publish time"
   outcome as an index fault. `pm/workspace.py` already has the
   text-level precedent (`_without_release_age`) for generated
   roots. The exemption list must be derived from the sources
   table — never hand-maintained, never name-based for index
   packages — so a future PyPI package can never slip through it.

## 4. (c) Launch-recipe design (DESIGN ONLY — nothing installed)

Current state on purplelongship (verified): `which hermes` empty;
no hermes unit in `~/.config/systemd/user/` (other Volmarr
services live there: aesir-brain, bifrost, samtal-worlds, …);
`~/.hermes` exists but is dormant (SOUL.md 2026-05-24; a couple of
cache/install dirs touched 2026-11-07, consistent with Team 01's
recon). No profiles beyond the default were found.

Proposed native recipe (no Docker, per standing law):

- **Tree + env**: canonical checkout `~/hermes-hack-forge`;
  environment staged by PM (`source ./activate` per the repo's
  AGENTS.md) into the checkout's managed env; never raw pip/uv
  mutation of a Hermes environment.
- **PATH entry**: a single symlink `~/.local/bin/hermes` →
  the checkout env's `hermes` entry point, so rollback is a
  re-point, not a reinstall.
- **HERMES_HOME**: default `~/.hermes` for the daily profile;
  named profiles under `~/.hermes/profiles/<name>` selected by
  unit instance, keeping profiles as islands (upstream invariant).
- **systemd user unit** `hermes-gateway.service`:
  `ExecStart=%h/.local/bin/hermes gateway run` (exact subcommand
  to be confirmed against the post-intake CLI in W01/W02, not
  assumed), `Restart=on-failure`, `Environment=HERMES_HOME=...`,
  logging to the user journal (no hand-rolled rotation), and
  `loginctl enable-linger` noted as an operator decision, not
  silently set.
- **Cold-install reproduction**: throwaway profile
  (`HERMES_HOME=/tmp/hermes-cold-$USER`), offline/cloud-denied
  run, ravens extra unselected AND selected, both must start;
  this is the W02 gate's "reproducible cold install" evidence.
- **Rollback**: previous lock + previous checkout commit pinned
  in the unit's drop-in; rollback = checkout the pinned commit,
  `hermes pm` re-stage from the pinned lock, restart unit.

## 5. (d) Dependency upper-bound audit summary

Method: exact-pin specifiers (`name==version`) extracted from the
fork's `pyproject.toml` (canonical tree at `281843f10f`) and from
upstream v0.23.0's, compared as sets, 2026-11-07.

- Fork: **115** exact pins. Upstream v0.23.0: **112**.
- Policy (both trees): core dependencies are exact-pinned `==`
  by design (recorded rationale: the 2026-05-12 Mini Shai-Hulud
  response); ranges appear only in extras/groups and carry upper
  bounds (`>=floor,<next_major`, e.g. the ravens' own
  `pytest>=7,<9`, `qdrant-client>=1.9,<2`). 17 range-style
  specifiers were counted in the fork, all in extras/groups.
- Fork-only pins: `muninn==1.0.0`, `huginn==1.0.0` (local,
  §1/§3), `pyyaml==6.0.3` (§2).
- Version drift vs v0.23.0 (fork behind by patch versions):
  `pyasn1` 0.6.4 vs 0.6.5, `pypdf` 6.21.2 vs 6.21.4,
  `setuptools` 83.0.0 vs 84.1.0. Expected: the fork's base is the
  2026-10-30 upstream-main intake, not the v0.23.0 tag; Team 02's
  W01 intake is what moves these, and W02 should re-run this
  comparison against the post-intake tree rather than treat the
  tag diff as a defect list.
- `requires-python = ">=3.11,<3.15"` in both trees.
- Nothing in the fork relaxes an upstream pin to a range, and no
  fork pin removes an upstream upper bound.

## 6. What U2 still owes (for the wave, not this prep)

- Adapter compatibility matrix (roadmap §5) — not started here.
- SBOM / license / leak / audit tooling integration — not started.
- Installed-wheel smoke for PyYAML on real ARM64 (Mimir).
- `hermes pm lock` end-to-end refusal capture + the §3 PM fix.
- Cold-install reproduction per §4 (needs the recipe approved as
  a design first, and W01 banked).
