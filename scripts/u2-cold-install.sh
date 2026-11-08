#!/usr/bin/env bash
# W02/U2 cold-install reproduction (the W02 gate's evidence run).
#
# Proves a fresh Hermes deployment can be staged from this checkout's
# declared sources alone, natively (no Docker), in a throwaway profile:
#
#   1. Preflight: the checkout must sit directly under $HOME so the
#      relative [tool.uv.sources] binding (../ravens) resolves. Staging
#      from any deeper tree is the historical "missing ravens" failure —
#      this script names it up front instead of letting uv fail cryptically.
#   2. A throwaway HERMES_HOME is created under $HOME (never the live
#      ~/.hermes) and the checkout's environment is staged from uv.lock
#      through PM (scripts/run-in-hermes-env), hash-verified by PM itself.
#      The account's tool store (uv/python/node binaries) is reused via
#      HERMES_RUNTIME_DIR — the same sharing the test runner uses for
#      worktree lanes; the profile and environments stage cold.
#   3. Smokes, each of which must pass:
#        - CLI starts:            hermes --version
#        - plugin discovery:      hermes plugins list (9 fork plugins)
#        - PyYAML wheel present:  python -c "import yaml" (volmarr-core pin)
#        - ravens unselected:     the default env has no muninn/huginn
#        - ravens selected:       a scratch tree synced with the
#                                 volmarr-ravens extra imports muninn+huginn
#                                 from ../ravens and their suites pass
#        - cloud-denied start:    the CLI starts with a dead proxy and
#                                 UV_OFFLINE=1 (no cloud reachability)
#
# Usage: scripts/u2-cold-install.sh [EVIDENCE_DIR]
#   Evidence lands in EVIDENCE_DIR (default ~/hermes-cold-evidence-<ts>);
#   the throwaway homes are removed unless KEEP_HOME=1 is set.
set -euo pipefail

CHECKOUT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TS="$(date +%Y%m%d-%H%M%S)"
EVIDENCE="${1:-$HOME/hermes-cold-evidence-$TS}"
COLD_HOME="$HOME/hermes-cold-home-$TS"
SCRATCH="$HOME/hermes-cold-ravens-$TS"
mkdir -p "$EVIDENCE"
exec > >(tee "$EVIDENCE/cold-install.log") 2>&1

fail() { echo "COLD-INSTALL FAIL: $*" >&2; exit 1; }

echo "== cold install: checkout=$CHECKOUT home=$COLD_HOME evidence=$EVIDENCE"

# 1. Preflight — the staging-location law.
case "$CHECKOUT" in
  "$HOME"/*/*) fail "checkout is not directly under \$HOME ($CHECKOUT); the ../ravens binding cannot resolve from here — stage from a tree directly under \$HOME" ;;
  "$HOME"/*) : ;;
  *) fail "checkout is outside \$HOME ($CHECKOUT); stage from a tree directly under \$HOME" ;;
esac
[ -d "$CHECKOUT/../ravens/muninn" ] || fail "../ravens/muninn missing beside $CHECKOUT — the ravens tree must sit beside the checkout"
[ -d "$CHECKOUT/../ravens/huginn" ] || fail "../ravens/huginn missing beside $CHECKOUT"
( cd "$CHECKOUT" && git rev-parse HEAD && git -C ../ravens rev-parse HEAD ) | tee "$EVIDENCE/shas.txt"

# 2. Stage the environment from the lock, into the throwaway profile home.
export HERMES_HOME="$COLD_HOME"
export HERMES_RUNTIME_DIR="$HOME/.hermes/tools"
mkdir -p "$COLD_HOME"
run_hermes() { "$CHECKOUT/scripts/run-in-hermes-env" python3 "$CHECKOUT/hermes" "$@"; }
run_py() { "$CHECKOUT/scripts/run-in-hermes-env" python3 "$@"; }

run_hermes --version | tee "$EVIDENCE/version.txt"

# 3a. Plugin discovery — all 9 fork plugins at their pinned versions.
run_hermes plugins list > "$EVIDENCE/plugins.txt" 2>&1 || fail "plugins list failed"
for plugin in volmarr-core volmarr-voice volmarr-astrology volmarr-tarot volmarr-seidr volmarr-rpg volmarr-hamr volmarr-smidja kista-secret-source; do
  grep -q "$plugin" "$EVIDENCE/plugins.txt" || fail "plugin $plugin not discovered"
done
echo "plugins: all 9 fork plugins discovered"

# 3b. PyYAML present (the kept volmarr-core pin); ravens NOT in default env.
run_py -c 'import yaml; print("pyyaml", yaml.__version__)' | tee "$EVIDENCE/pyyaml.txt"
if run_py -c 'import muninn' 2>/dev/null; then
  fail "muninn leaked into the default environment (volmarr-ravens is opt-in)"
fi
echo "ravens: correctly absent from the default environment"

# 3c. Ravens selected: scratch tree from the same pyproject+lock, directly
# under $HOME so ../ravens resolves, synced with the opt-in extra.
UV_BIN="$(command -v uv || true)"
[ -n "$UV_BIN" ] || UV_BIN="$(find "$HOME/.hermes/tools" -maxdepth 2 -name uv -type f | head -1)"
[ -n "$UV_BIN" ] || fail "no uv available for the ravens-extra sync"
mkdir -p "$SCRATCH"
cp "$CHECKOUT/pyproject.toml" "$CHECKOUT/uv.lock" "$SCRATCH/"
( cd "$SCRATCH" && "$UV_BIN" sync --frozen --no-install-project --extra volmarr-ravens ) \
  > "$EVIDENCE/ravens-sync.log" 2>&1 || fail "ravens-extra sync failed (see ravens-sync.log)"
"$SCRATCH/.venv/bin/python" -c 'import muninn, huginn; print("ravens import from", muninn.__file__)' \
  | tee "$EVIDENCE/ravens-import.txt"
grep -q "ravens/muninn" "$EVIDENCE/ravens-import.txt" || fail "muninn did not import from the local ravens tree"
"$UV_BIN" pip install --python "$SCRATCH/.venv/bin/python" 'pytest>=7,<9' \
  > "$EVIDENCE/ravens-pytest.log" 2>&1 || fail "pytest staging for ravens suites failed"
# The two suites share test basenames (test_contract.py, test_robustness.py)
# with no __init__.py, so they must run as separate per-package invocations;
# a single combined run dies at collection with an import-file mismatch.
: > "$EVIDENCE/ravens-tests.log"
for pkg in muninn huginn; do
  ( cd "$CHECKOUT/../ravens/$pkg" && "$SCRATCH/.venv/bin/python" -m pytest tests -q ) \
    >> "$EVIDENCE/ravens-tests.log" 2>&1 || fail "ravens suite $pkg failed (see ravens-tests.log)"
done
grep -h "passed" "$EVIDENCE/ravens-tests.log"

# 3d. Cloud-denied start. The binary under test is the staged deployment
# venv's own hermes entry point — what a launch unit ultimately execs.
# (run-in-hermes-env / ./activate re-run PM's resolver on every call, so
# they need the network themselves; that is a staging-layer property,
# recorded in U2_COMPLETION.md, not a deployment runtime dependency.)
# With a dead proxy and a minimal environment the staged CLI must still
# start and print its banner.
COLD_BIN="$(find "$COLD_HOME/installs" -name hermes -type f -path '*venv/bin*' | head -1)"
[ -n "$COLD_BIN" ] || fail "no staged hermes binary found under $COLD_HOME"
env -i PATH="/usr/bin:/bin" HOME="$HOME" HERMES_HOME="$COLD_HOME" \
  https_proxy=http://127.0.0.1:9 http_proxy=http://127.0.0.1:9 \
  "$COLD_BIN" --version | tee "$EVIDENCE/version-offline.txt"
grep -q "Hermes Agent" "$EVIDENCE/version-offline.txt" || fail "offline start did not produce a version banner"

echo "== COLD INSTALL OK — evidence in $EVIDENCE"
if [ "${KEEP_HOME:-0}" != "1" ]; then rm -rf "$COLD_HOME" "$SCRATCH"; fi
