#!/usr/bin/env python3
"""Merge upstream Hermes while preserving this fork's sovereign files.

The command deliberately leaves a successful merge uncommitted so the intake can be
reviewed and tested before it becomes part of the personal fork.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
PROTECTED_PATHS = ("README.md",)
_REF_PART_RE = re.compile(r"^[A-Za-z0-9._/-]+$")


class SyncError(RuntimeError):
    """A precondition failed before an upstream merge could start."""


def _git(repo: Path, *args: str, check: bool = False) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if check and result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise SyncError(f"git {' '.join(args)} failed: {detail}")
    return result


def _validated_ref_part(value: str, label: str) -> str:
    if (
        not value
        or value.startswith("-")
        or ".." in value
        or not _REF_PART_RE.fullmatch(value)
    ):
        raise SyncError(f"invalid {label}: {value!r}")
    return value


def _require_clean_tree(repo: Path) -> None:
    status = _git(repo, "status", "--porcelain", "--untracked-files=normal", check=True)
    if status.stdout:
        raise SyncError(
            "working tree is not clean; commit or stash every change before upstream sync"
        )


def _restore_protected_paths(repo: Path, original_head: str) -> None:
    for rel_path in PROTECTED_PATHS:
        tracked = _git(repo, "cat-file", "-e", f"{original_head}:{rel_path}")
        if tracked.returncode != 0:
            raise SyncError(f"protected path is missing from the starting commit: {rel_path}")
        _git(
            repo,
            "restore",
            f"--source={original_head}",
            "--staged",
            "--worktree",
            "--",
            rel_path,
            check=True,
        )


def sync_upstream(
    repo: Path,
    remote: str,
    branch: str,
    *,
    fetch: bool = True,
) -> int:
    repo = repo.resolve()
    if not repo.is_dir():
        raise SyncError(f"repository directory does not exist: {repo}")

    _git(repo, "rev-parse", "--is-inside-work-tree", check=True)
    _require_clean_tree(repo)

    remote = _validated_ref_part(remote, "remote")
    branch = _validated_ref_part(branch, "branch")
    original_head = _git(repo, "rev-parse", "HEAD", check=True).stdout.strip()
    original_bytes = {
        rel_path: (repo / rel_path).read_bytes() for rel_path in PROTECTED_PATHS
    }

    if fetch:
        print(f"Fetching {remote}/{branch}...")
        _git(repo, "fetch", remote, branch, check=True)
        merge_target = "FETCH_HEAD"
    else:
        merge_target = f"{remote}/{branch}"

    merge = _git(repo, "merge", "--no-commit", "--no-ff", merge_target)
    _restore_protected_paths(repo, original_head)

    for rel_path, before in original_bytes.items():
        after = (repo / rel_path).read_bytes()
        if after != before:
            raise SyncError(f"protected path changed during upstream sync: {rel_path}")

    unresolved = [
        line
        for line in _git(repo, "diff", "--name-only", "--diff-filter=U", check=True)
        .stdout.splitlines()
        if line
    ]
    merge_in_progress = (
        _git(repo, "rev-parse", "--quiet", "--verify", "MERGE_HEAD").returncode == 0
    )

    if unresolved:
        print("Upstream merge has unresolved conflicts:", file=sys.stderr)
        for path in unresolved:
            print(f"  {path}", file=sys.stderr)
        print(
            "README.md has been restored. Resolve the remaining conflicts, or run "
            "`git merge --abort`.",
            file=sys.stderr,
        )
        return 2

    if not merge_in_progress:
        if merge.returncode != 0:
            detail = merge.stderr.strip() or merge.stdout.strip()
            raise SyncError(f"merge failed before it could start: {detail}")
        print("Already up to date; protected files are unchanged.")
        return 0

    print("Upstream changes are staged in an uncommitted merge.")
    print("Protected paths restored from the personal fork:")
    for rel_path in PROTECTED_PATHS:
        print(f"  {rel_path}")
    print("Review the diff, run the required tests, then commit the merge.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=REPO_ROOT)
    parser.add_argument("--remote", default="upstream")
    parser.add_argument("--branch", default="main")
    parser.add_argument(
        "--no-fetch",
        action="store_true",
        help="merge an existing <remote>/<branch> ref without fetching",
    )
    args = parser.parse_args(argv)

    try:
        return sync_upstream(
            args.repo,
            args.remote,
            args.branch,
            fetch=not args.no_fetch,
        )
    except (OSError, SyncError) as exc:
        print(f"upstream sync refused: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
