# Upstream Sync

## Invariant

`README.md` is owned by Volmarr's personal fork. Upstream Hermes must never replace, merge into,
or rewrite it.

The invariant is enforced by `scripts/sync_upstream.py`, which:

- refuses to run with a dirty working tree;
- records the starting commit and README bytes;
- fetches the selected upstream branch;
- performs a no-commit, no-fast-forward merge;
- restores `README.md` from the starting personal-fork commit;
- verifies the file is byte-for-byte unchanged;
- leaves the merge uncommitted for review and testing;
- reports remaining non-README conflicts without discarding the merge state.

## One-Time Remote Setup

```bash
git remote add upstream git@github.com:NousResearch/hermes-agent.git
git remote -v
```

Do not change `origin`; it remains the personal RuneForgeAI fork.

## Intake Procedure

Start from a clean personal branch, then run:

```bash
python scripts/sync_upstream.py
```

If the merge is clean:

1. Inspect `git status` and the staged merge diff.
2. Confirm `README.md` is unchanged.
3. Read the upstream commits and identify behavior or migration changes.
4. Run relevant Hermes tests through `scripts/run_tests.sh`.
5. Run all Volmarr contract tests affected by the intake.
6. Smoke-test the local runtime.
7. Commit the reviewed merge.

If conflicts remain, the script has already restored `README.md`. Resolve only the other files,
or run `git merge --abort`.

## Protected Files

The executable protected-path list lives in `scripts/sync_upstream.py`. It currently contains:

```text
README.md
```

Add another file only when the fork truly owns it and upstream must never contribute to it.
Ordinary personal documents do not need protection when they have no upstream counterpart.

## Branch Shape

```text
upstream/main
      ↓ guarded intake
integration/upstream-YYYY-MM-DD
      ↓ tests and review
personal main
```

Feature work branches from the tested personal `main`, never directly from `upstream/main`.
