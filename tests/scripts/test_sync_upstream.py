"""Behavior contracts for the personal fork's guarded upstream intake."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "sync_upstream.py"


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=check,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def _commit(repo: Path, message: str) -> None:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)


def _init_repo(path: Path) -> None:
    path.mkdir()
    _git(path, "init", "-q", "-b", "main")
    _git(path, "config", "user.name", "Test User")
    _git(path, "config", "user.email", "test@example.com")
    _git(path, "config", "core.autocrlf", "false")


def _run_sync(repo: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--repo",
            str(repo),
            "--remote",
            "upstream",
            "--branch",
            "main",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )


def _upstream_and_fork(tmp_path: Path) -> tuple[Path, Path]:
    upstream = tmp_path / "upstream"
    fork = tmp_path / "fork"
    _init_repo(upstream)
    (upstream / "README.md").write_text("official upstream\n", encoding="utf-8")
    (upstream / "runtime.py").write_text("VERSION = 1\n", encoding="utf-8")
    _commit(upstream, "upstream base")

    _git(tmp_path, "clone", "-q", str(upstream), str(fork))
    _git(fork, "config", "user.name", "Test User")
    _git(fork, "config", "user.email", "test@example.com")
    _git(fork, "config", "core.autocrlf", "false")
    _git(fork, "remote", "rename", "origin", "upstream")
    return upstream, fork


def test_upstream_sync_preserves_fork_readme_and_imports_runtime_changes(tmp_path):
    upstream, fork = _upstream_and_fork(tmp_path)
    fork_readme = "# Volmarr's Hermes\n\nRuneForgeAI remains sovereign. ᚱ\n"
    (fork / "README.md").write_text(fork_readme, encoding="utf-8")
    _commit(fork, "personal README")

    (upstream / "README.md").write_text("official upstream revision\n", encoding="utf-8")
    (upstream / "runtime.py").write_text("VERSION = 2\n", encoding="utf-8")
    _commit(upstream, "upstream runtime and README update")

    result = _run_sync(fork)

    assert result.returncode == 0, f"{result.stdout}\n{result.stderr}"
    assert (fork / "README.md").read_text(encoding="utf-8") == fork_readme
    assert (fork / "runtime.py").read_text(encoding="utf-8") == "VERSION = 2\n"
    assert _git(fork, "rev-parse", "--verify", "MERGE_HEAD").returncode == 0
    assert not _git(
        fork, "diff", "--name-only", "--diff-filter=U"
    ).stdout.strip()


def test_upstream_sync_refuses_a_dirty_worktree_without_touching_readme(tmp_path):
    _upstream, fork = _upstream_and_fork(tmp_path)
    before = (fork / "README.md").read_bytes()
    (fork / "local-notes.txt").write_text("unfinished\n", encoding="utf-8")

    result = _run_sync(fork)

    assert result.returncode == 1
    assert "working tree is not clean" in result.stderr
    assert (fork / "README.md").read_bytes() == before
    assert _git(
        fork, "rev-parse", "--quiet", "--verify", "MERGE_HEAD", check=False
    ).returncode != 0
