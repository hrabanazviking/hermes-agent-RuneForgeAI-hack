# Native launch recipe — Hermes on Volmarr's machines (W02/U2)

Status: **documented and proven by the W02 cold-install reproduction**
(`scripts/u2-cold-install.sh`, evidence run 2026-11-07 on purplelongship).
The live deployment on purplelongship remains **dormant by choice** —
this recipe is what an operator runs when Volmarr gives the word.
Nothing here uses Docker; everything is native.

## 1. Layout law (read first)

- The checkout lives **directly under `$HOME`** (e.g. `~/hermes-hack-forge`).
- The ravens tree is the checkout's **sibling**: `~/ravens` beside the
  checkout, because `[tool.uv.sources]` binds `../ravens/muninn` and
  `../ravens/huginn`. A checkout staged anywhere else breaks that
  binding whenever the opt-in `volmarr-ravens` extra is selected.
- Deployment state lives under `HERMES_HOME` (default `~/.hermes`):
  staged environments in `installs/<repo-hash>/environments/<gen>/`,
  profiles in `profiles/<name>/`, the default profile at the root.
- The account tool store (`uv`, Python, node — under `~/.hermes/tools`)
  is shared between checkouts and profiles via `HERMES_RUNTIME_DIR`;
  environments and profiles are not shared.

## 2. Stage and activate

From the checkout:

```sh
source ./activate          # interactive shell: stages if needed, defines `hermes`
scripts/run-in-hermes-env hermes --version   # one-shot, no persistent shell state
```

Staging is PM's job (`setup-hermes.sh` under the hood): it verifies
`uv.lock` hashes, builds the generation venv, and prints
`Hermes Agent v0.23.0+… · upstream <sha> · local <sha>` on `--version`.
First stage on a cold home takes under a minute with a warm tool store.

## 3. Run

- Interactive: `hermes` (after `source ./activate`), profiles with
  `hermes -p <name> …`.
- Gateway (long-running): `hermes gateway run` in the foreground, or
  install the user service once, from the activated environment:

```sh
hermes gateway install     # writes the hermes-gateway user unit
hermes gateway start
hermes gateway status
```

  The unit is a **systemd user service** named `hermes-gateway.service`,
  managed entirely through `hermes gateway start|stop|restart|status`.
  Whether it starts at boot is the operator's decision:
  `loginctl enable-linger $USER` makes user services survive logout/boot;
  without linger it starts at login. That choice is Volmarr's, made at
  install time — the recipe takes no position.

## 4. Rollback

A deployment is pinned by two things, both in git: the **checkout
commit** and its **`uv.lock`**. Rollback never touches profile data
(state under `HERMES_HOME` is not code):

1. In the checkout: `git checkout <pinned-commit>` (or clone a second
   tree beside the first at the pinned commit — trees are cheap and
   the sibling-ravens law is satisfied by any tree under `$HOME`).
2. Re-activate (`source ./activate` or any `run-in-hermes-env` call):
   PM stages the generation that matches the pinned lock; earlier
   generations stay in the store until `hermes pm gc` reclaims them,
   so rolling forward again is instant.
3. `hermes gateway restart` (or `hermes gateway start` if stopped).

Verify after rollback with `hermes --version`: the banner names the
upstream pin and the local commit you should expect.

## 5. What the cold-install proof covered (2026-11-07)

`scripts/u2-cold-install.sh` in a throwaway `HERMES_HOME` under `$HOME`:
CLI banner, all 9 fork plugins discovered, PyYAML 6.0.3 importable,
ravens absent from the default environment, ravens present and green
(muninn 36 / huginn 27) when the `volmarr-ravens` extra is selected
from the same lock, and the staged venv's `hermes` binary starting
with cloud access denied (dead proxy, minimal environment).
Evidence: `~/hermes-cold-evidence-20261107-230016/` on purplelongship.
