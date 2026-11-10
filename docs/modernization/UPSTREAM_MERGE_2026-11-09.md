# Upstream merge 2026-11-09 — called-forward commission, workstream 1

Merge of upstream NousResearch/hermes-agent main 0e28218d19f04d7df0bcafbede975cfa73ce1794
into the fork, built on integration branch integration/upstream-2026-11-09 in
~/hermes-team-02 (never directly on main), following the W01 intake method.
Merge commit: 3d037759ddae16c434f9badad2bd7e979eb7f082
(parents: fork b24854a34ddc + upstream 0e28218d19). 2,722 files staged at merge.

## Conflict and ruling

Exactly ONE conflict: pm/environment.py, check_lock(). Both sides had rewritten
the same lines, so it was not a trivial union; the keeper stopped and Volmarr
ruled on 2026-11-09 (~20:35 EST): COMBINE BOTH behaviours.

Resolution as banked: check_lock builds its command through the fork's
_lock_command(source, check=True) — the W02 release-age gate stays scoped to
registry sources, local-path packages exempted by name — and upstream's
offline-first behaviour runs on that same command: an offline copy is tried
first and returns if it vouches for the lock; only a lock it cannot vouch for
goes online, where uv names what is stale.

README.md in the merged tree is byte-identical to origin/main's
(sha256 336813d11bbe5aa2ff745b4a4bc3abcf2a283cd13971c0c11d061377129db7f3).
uv.lock merged clean (no conflict).

## Gate evidence (all on the merged tree, laptop logs named)

- Contracts (the banking gate): scripts/run_tests.sh on
  tests/plugins/test_volmarr_*.py + tests/plugins/test_kista_*.py
  (~/upstream-merge-contracts.log): 137 files = 1,171 passed / 7 failed /
  1 skipped — exactly the banked baseline; the 7 failures are the known
  live-transport set in the same 3 files (5 core-plugin, 1 Verdandi stimuli,
  1 voice runner). ZERO regressions.
- Targeted pm check_lock battery (tests/pm/test_build_operations.py, run with
  real uv on PATH): 24 passed / 1 failed on the merged tree — IDENTICAL to a
  pristine upstream/main control run in the same environment (24 passed /
  the same 1 failed: test_check_lock_does_not_refetch_a_locked_direct_url_wheel,
  an environment-bound failure of upstream's own test on this laptop, not
  caused by the combined resolution; the control probe worktree was removed).
  The 3 test_check_lock_never_changes_source cases pass in the merged tree.
- Fork release-age scope: tests/pm/test_u2_release_age_scope.py +
  test_pnpm_release_age.py = 14 passed / 0 failed on the merged tree.
- Full tests/pm via the clean-env runner (~/upstream-merge-pm.log): 147 files,
  876 passed / 32 failed / 168 errors / 72 skipped. The errors are fixture-setup
  failures (the runner's clean env has no uv on PATH; fixtures require real uv)
  — the same environment limitation proven by the upstream control above.
  Recorded honestly; not claimed green.
- Smoke: CLI runs on the merged tree (Hermes Agent v0.23.0+361.gb24854a.dirty);
  plugins list discovers all 9 fork plugins (kista-secret-source, volmarr-core,
  volmarr-astrology, volmarr-hamr, volmarr-rpg, volmarr-seidr, volmarr-smidja,
  volmarr-tarot, volmarr-voice).

## Next

Workstream 2 follows in roadmap order: W08 ledger engine updates E.01-E.18,
then the fifteen ecosystem workstreams. Release scorecard still honestly
NOT releasable (0 met / 10 unmet / 5 deferred) — unchanged by this merge.
