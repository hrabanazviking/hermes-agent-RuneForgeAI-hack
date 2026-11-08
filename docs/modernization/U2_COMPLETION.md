# U2 / W02 completion record — dependency + deployment safety

Team 03, branch `yrsa/hermes-team-03`, built on the banked W01 head
`1cd7d59015cb46775cc666655a99a44b9b0a1aa3`. All work on purplelongship.
The audit draft (`U2_AUDIT_DRAFT.md`) governed; this record says what
was implemented, what the evidence shows, and what honestly remains.

## Implemented

### 1. PM release-age gate scoped to registry sources — commit `2e809aba89`

`pm/environment.py`:

- `local_source_packages(source)` derives the local-source package set
  from the project's `[tool.uv.sources]` — only entries carrying a
  `path`/`editable` key or `workspace = true`. Git, URL, index and
  registry sources stay gated. The set is derived, never hand-listed.
- `PythonEnvironment._lock_command` builds the `uv lock` argv with
  `--exclude-newer-package <name>=false` for exactly those names, for
  that invocation only. `[tool.uv] exclude-newer-package` in
  pyproject is untouched (pm law: reserved for CA trust stores) and
  the `exclude-newer = "3 days"` quarantine applies in full to every
  registry package.
- `classify_uv_failure(..., local_packages=...)`: when every package
  blamed by an undated ("has no publish time") failure is a local
  source, the verdict is the new `UNDATED_LOCAL_HINT` — it names the
  local binding and the sibling-tree staging rule instead of wrongly
  blaming the index. Mixed local+registry blame keeps the index
  verdict; callers without local context see no change.

Tests: `tests/pm/test_u2_release_age_scope.py`, 9 tests.

**Reproduction honesty.** The draft's §3 refusal was flagged in the
draft itself as not re-run end-to-end. On this host (uv 0.13.5) plain
`uv lock` paths — check, targeted re-resolve, seeded-lock regen — all
pass; the end-to-end PM refusal did **not** reproduce. What is proven:
(a) the mechanism is in the source (the classifier mapped any undated
outcome to an index fault, and the lock path never scoped the gate);
(b) `hermes pm lock` on the real tree reports the lock current,
rc 0; (c) an incremental relock through PM in a scratch tree (one
dependency added) succeeds, rc 0, lock updated, unrelated pins
preserved; (d) the unit tests pin the scoped behavior both ways.

**Discovered while verifying (pre-existing, not caused by this fix):**
a from-scratch relock with no `uv.lock` — equivalently `uv lock
--upgrade` — fails: fresh resolution selects spacy 2.0.17 (via
kittentts), whose sdist cannot build on Python 3.14
(`cannot import name 'msvccompiler' from 'distutils'`). Reproduced
with plain uv before the patch existed. The committed lock is
therefore load-bearing: it must never be deleted as a "clean regen"
step. Recorded as ticket T1 below.

### 2. Ravens staging comment corrected — commit `492aedf008`

pyproject's `[tool.uv.sources]` comment named the VM layout
(`~/workspace/ravens`) as the sibling. It now states the relative
law: the ravens tree must be the checkout's sibling — `~/ravens`
beside the `~/hermes-*` checkouts on purplelongship,
`~/workspace/ravens` beside the checkouts on the VM — and that
checkouts/test envs must be staged from trees beside the ravens
tree. Comment-only; bindings untouched; `uv lock --check` clean.

### 3. SBOM + audit tooling — `scripts/generate_sbom.py`

CycloneDX 1.5 SBOM generated from `uv.lock`
(`docs/modernization/SBOM.cdx.json`): **358 components — 352 registry,
3 editable-local (hermes-agent root, muninn, huginn), 2 git (misaki,
psutil), 1 archive-url (kittentts)**. The generator exits 1 if muninn
or huginn ever appears with a non-local source, so a lock that would
install the unrelated PyPI packages of those names fails loudly.
(One classification fix during the run: direct-URL sources use uv's
`url` key and are now classed `archive-url`, not `other`.)

### 4. Upper-bound audit re-run against the post-intake tree

154 dependency specifiers in pyproject: **137 exact `==` pins, 17
range-style**, all ranges in extras/groups and all upper-bounded —
the fork's posture is unchanged and nothing relaxes an upstream pin.
The draft's three drift rows were absorbed by the W01 intake itself:
pyasn1 0.6.5, pypdf 6.21.4, setuptools 84.1.0 now match upstream
v0.23.0 exactly. Fork-only pins remain exactly three: `muninn==1.0.0`,
`huginn==1.0.0` (path-bound, never index), `pyyaml==6.0.3` (kept per
the audit's recommendation; imported by 9 volmarr-core modules).

### 5. Launch recipe — `docs/modernization/LAUNCH_RECIPE.md`

Native layout, PM activation, `hermes gateway install` → the
`hermes-gateway.service` user unit, profiles, and the rollback recipe
(pinned commit + pinned lock; profile data untouched). The laptop's
live `~/.hermes` deployment stays dormant: the recipe is documented
and cold-proven, not installed — installing is an operator step at
Volmarr's word.

### 6. Cold-install reproduction — `scripts/u2-cold-install.sh` (the W02 gate)

Full pass, evidence in `~/hermes-cold-evidence-20261107-230016/`
on purplelongship (checkout `492aedf008`, ravens `fc761f020b39`):

- environment staged from the lock by PM in a throwaway `HERMES_HOME`
  directly under `$HOME`; banner `Hermes Agent v0.23.0+290.g492aedf`
- all 9 fork plugins discovered
- PyYAML 6.0.3 importable in the staged env
- muninn correctly absent from the default environment
- ravens selected via the `volmarr-ravens` extra from the same
  pyproject+lock: muninn imports from `~/ravens/muninn/src/...`;
  suites **36 passed (muninn) + 27 passed (huginn)**
- staged venv `hermes` binary starts with cloud access denied
  (dead proxy, minimal env) and prints its banner

Two script defects were found and fixed during the runs, both
recorded in the script: the ravens suites must run as separate
per-package pytest invocations (shared test basenames, no
`__init__.py` — a combined run dies at collection), and the
cloud-denied step must exec the staged venv binary directly
(`run-in-hermes-env`/`./activate` re-run PM's resolver per call and
need network themselves — a staging-layer property, not a runtime
dependency). This closes W00.07.

## Test evidence (counts from logs on purplelongship)

- `tests/pm/test_u2_release_age_scope.py`: **9 passed**
  (`~/team03-pm-tests.log`)
- `tests/pm/test_workspace.py` + `tests/pm/test_environment_build.py`:
  **53 passed, 0 failed** (`~/team03-pm-tests2.log`; the first run's
  38 fixture errors were `uv` missing from PATH — the
  `locked_project` fixture requires uv on PATH; with
  `~/.local/bin` on PATH the files are fully green)
- Contract battery (117 plugin contract files): see the W02 banking
  note appended at the end of this file for the final count.
- Ravens suites: 36 + 27 passed (cold-install evidence).

## Remaining W02 tickets

- **T1 (discovered defect, dependency decision):** from-scratch lock
  regeneration fails on spacy 2.0.17's sdist under Python 3.14 (via
  kittentts). Needs a constraint decision on the kittentts/spacy line
  (pin floor, alternate source, or upstream bump) — a dependency
  change beyond W02's safety scope; the committed lock is
  load-bearing until then.
- **T2:** PyYAML 6.0.3 installed-wheel smoke on real ARM64 hardware
  (Mimir). Wheels exist for cp314 ARM64; the smoke itself has not
  run on the Pi.
- **T3:** First-party ravens publication route — design only:
  a dedicated repository created by Volmarr (repo creation is his
  job alone), the `[tool.uv.sources]` binding re-pointed at a pinned
  git tag of that repo, names never published to PyPI. Until then
  the sibling-tree binding + the W02 PM gate fix is the mechanism.
- **T4:** License/leak audit tooling beyond the SBOM: the SBOM and
  `COMPONENT_LICENSES.md`/`COMPONENT_NOTICES.md` exist; an automated
  license-scan + secret-leak sweep over the lock set is not built.
- Carried from W00, not Team 03's: integration-lock promotion and
  boundary review (Team 09/W08); backup encryption decision
  (W00.03-ENC) awaits Volmarr's key/passphrase word — not re-asked.

## Banking note (final battery, 2026-11-07)

Full contract battery on this branch (`~/team03-contracts.log`):
**117 files, 929 passed / 7 failed / 1 skipped** — identical counts to
the W01 baseline gate, and the 7 failures are name-identical to the
known live-transport set (5 Verdandi socket/discovery contracts in
`test_volmarr_core_plugin.py`, 1 Verdandi stimuli contract, 1
voice-runner loopback contract). No regressions from W02's changes.
README.md untouched: sha256
`336813d11bbe5aa2ff745b4a4bc3abcf2a283cd13971c0c11d061377129db7f3`,
matching the banked main. Nothing merged, nothing pushed — the
keeper banks this branch serially.
