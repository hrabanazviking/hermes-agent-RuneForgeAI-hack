"""N2 project-context packets: live repo facts, never stale (W10).

Roadmap section 21 (Phase N2) asks Hermes to build "external
project context packets" retrieved from the current README /
ROADMAP / CAMPAIGN_STATE and source of a repository, rather than
stale single hardcoded project facts, and its acceptance requires
that Hermes can inspect, plan and prepare a patch against a
project "without writing to another active agent's checkout".

This module is the contract+adapter slice of that, plugin-side in
volmarr-core, built on the W09 capability bus: the packet builder
is read-only and describes itself through a capability descriptor
whose provenance rules it reuses. Honest stage:

- a packet is measured live from disk at build time: source paths,
  byte sizes and SHA-256 of the files that exist, plus the commit
  HEAD read from the target's own .git directory (loose ref,
  packed-refs or detached HEAD) -- nothing is hardcoded, and a
  missing file is NAMED in the packet, never invented;
- the builder never writes anywhere; patch preparation is a
  separate, explicit operation whose caller-chosen output path
  must resolve OUTSIDE the target repository -- an inside path is
  refused by name before anything is written;
- no GitHub / Samverk adapter is claimed here: this is the local
  packet + write-containment contract those adapters will use.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

SCHEMA = "runeforge.project-context.v1"

DESCRIPTOR = {
    "schema": "runeforge.capability.v1",
    "service": "volmarr-project-context",
    "version": "0.26.0",
    "owner": "volmarr",
    "actions": ["read", "propose"],
    "transport": "in-process",
    "auth": "scoped",
    "side_effects": False,
    "privacy_classes": ["public", "shared", "local-private"],
    "availability": "contract-implemented",
    "timeout_ms": 2000,
}

# (kind, exact name or root glob) in packet order.
SOURCE_KINDS = (
    ("readme", "README.md"),
    ("roadmap", "ROADMAP*.md"),
    ("campaign_state", "CAMPAIGN_STATE*.md"),
)


class ProjectContextError(Exception):
    """Named, honest project-context failure."""

    def __init__(self, name: str, detail: str) -> None:
        super().__init__(detail)
        self.name = name
        self.detail = detail


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_head(repo: Path) -> str | None:
    """Commit HEAD read from the repo's own .git, or None.

    Handles a plain .git directory, a worktree .git file pointing
    at the real gitdir, loose refs, packed-refs and a detached
    HEAD. Pure file reads: no subprocess, no mutation.
    """
    dotgit = repo / ".git"
    gitdir: Path | None = None
    if dotgit.is_dir():
        gitdir = dotgit
    elif dotgit.is_file():
        try:
            text = dotgit.read_text(encoding="utf-8").strip()
        except OSError:
            return None
        if text.startswith("gitdir:"):
            target = text.split(":", 1)[1].strip()
            candidate = Path(target)
            gitdir = candidate if candidate.is_absolute() else repo / candidate
    if gitdir is None:
        return None
    try:
        head = (gitdir / "HEAD").read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not head.startswith("ref:"):
        return head or None
    ref = head.split(":", 1)[1].strip()
    loose = gitdir / ref
    if loose.is_file():
        value = loose.read_text(encoding="utf-8").strip()
        return value or None
    # Worktrees keep shared refs in the common gitdir.
    commondir = gitdir / "commondir"
    roots = [gitdir]
    if commondir.is_file():
        rel = commondir.read_text(encoding="utf-8").strip()
        roots.append((gitdir / rel).resolve())
    for root in roots:
        packed = root / "packed-refs"
        if packed.is_file():
            for line in packed.read_text(encoding="utf-8").splitlines():
                if line.startswith("#") or " " not in line:
                    continue
                sha, name = line.split(" ", 1)
                if name.strip() == ref:
                    return sha.strip()
    return None


def build_project_packet(repo_path: str | Path, *, recorded_at: str) -> dict[str, Any]:
    """Measure a live context packet from a LOCAL repository.

    Read-only. Files that exist are hashed from disk now; kinds
    with no matching file are named in ``missing`` -- never
    invented, never defaulted from another project.
    """
    if not recorded_at or not str(recorded_at).strip():
        raise ProjectContextError("validation_failure", "recorded_at_required")
    repo = Path(repo_path).expanduser()
    if not repo.exists():
        raise ProjectContextError("unavailable", f"repo_missing:{repo}")
    if not repo.is_dir():
        raise ProjectContextError("validation_failure", f"repo_not_a_directory:{repo}")
    repo = repo.resolve()
    sources: list[dict[str, Any]] = []
    missing: list[str] = []
    for kind, pattern in SOURCE_KINDS:
        if "*" in pattern:
            found = sorted(p for p in repo.glob(pattern) if p.is_file())
        else:
            candidate = repo / pattern
            found = [candidate] if candidate.is_file() else []
        if not found:
            missing.append(kind)
            continue
        for path in found:
            sources.append({
                "kind": kind,
                "name": path.name,
                "path": path.relative_to(repo).as_posix(),
                "size_bytes": path.stat().st_size,
                "sha256": _sha256_file(path),
            })
    return {
        "schema": SCHEMA,
        "service": DESCRIPTOR["service"],
        "repo_path": str(repo),
        "head": read_head(repo),
        "sources": sources,
        "missing": missing,
        "provenance": {
            "service": DESCRIPTOR["service"],
            "version": DESCRIPTOR["version"],
            "source_ref": f"repo:{repo}",
            "recorded_at": recorded_at,
            "confidentiality": "local-private",
        },
    }


def resolve_patch_output(target_repo: str | Path, output_path: str | Path) -> Path:
    """Resolve a patch-preparation output path, refusing any path
    inside (or equal to) the target repository by name."""
    target = Path(target_repo).expanduser().resolve()
    output = Path(output_path).expanduser()
    if not output.is_absolute():
        output = (Path.cwd() / output)
    output = output.resolve()
    if output == target or target in output.parents:
        raise ProjectContextError(
            "validation_failure",
            f"patch_output_inside_target_repo:{output}",
        )
    if output.is_dir():
        raise ProjectContextError(
            "validation_failure", f"patch_output_is_directory:{output}")
    return output


def write_patch_preparation(
    target_repo: str | Path,
    output_path: str | Path,
    *,
    content: str,
    recorded_at: str,
) -> dict[str, Any]:
    """Write prepared patch material OUTSIDE the target repo.

    The containment check runs before any write; the target
    repository is only ever read (its HEAD, for the receipt).
    """
    if not recorded_at or not str(recorded_at).strip():
        raise ProjectContextError("validation_failure", "recorded_at_required")
    target = Path(target_repo).expanduser()
    if not target.is_dir():
        raise ProjectContextError("unavailable", f"repo_missing:{target}")
    target = target.resolve()
    output = resolve_patch_output(target, output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(content, encoding="utf-8")
    return {
        "schema": SCHEMA,
        "output_path": str(output),
        "size_bytes": output.stat().st_size,
        "sha256": _sha256_file(output),
        "target_repo": str(target),
        "target_head": read_head(target),
        "provenance": {
            "service": DESCRIPTOR["service"],
            "version": DESCRIPTOR["version"],
            "source_ref": f"repo:{target}",
            "recorded_at": recorded_at,
            "confidentiality": "local-private",
        },
    }
