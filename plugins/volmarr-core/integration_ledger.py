"""E0 integration ledger: the promoted, verified engine lock (W08).

Read-only operator surface over ``docs/modernization/integration-lock.json``
(the lock promoted from its Phase 0 DRAFT in W08) and the human ledger in
``docs/modernization/INTEGRATION_MATRIX.md``. This module is the lock's
first live caller: before W08 the lock was a file no code read, so its
rows could rot silently (the draft carried a ravens-absent claim for a
day after the tree had landed on this host). The registry

- loads and schema-validates the promoted lock (a DRAFT lock is refused
  by name -- an unverified lock must never be served as verified);
- checks the seven E0 first pins byte-for-byte (they were established
  by Team 09 at E0 on 2026-11-07 and must never drift silently);
- refuses the superseded ravens-absent claim anywhere in a ravens row
  (disk proof, W02: ``~/ravens`` at fc761f0 is present on
  purplelongship, byte-identical to the VM canonical tree);
- verifies, locally and without network or subprocesses, that each
  row's declared adapter files exist in this tree and that the local
  ravens tree HEAD matches the lock's recorded tree pin;
- reports every row's evidence stage under the roadmap section 28.3
  hierarchy and its verification state exactly as recorded -- nothing
  here promotes a row, moves a pin, or fakes an installed engine.

No network, no subprocess, no mutation: absence and unverified rows
are reported as what they are.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

LOCK_RELATIVE_PATH = Path("docs") / "modernization" / "integration-lock.json"
MATRIX_RELATIVE_PATH = Path("docs") / "modernization" / "INTEGRATION_MATRIX.md"

ADAPTER_MODES = frozenset(
    {
        "documented",
        "probe-only",
        "read-only",
        "deterministic tool",
        "full read-write",
        "realtime",
        "prototype",
        "design-only",
    }
)

EVIDENCE_STAGES = (
    "documented only",
    "contract implemented",
    "installed integration",
    "end-to-end working",
    "production qualified",
    "deferred/blocked",
)

VERIFICATION_STATES = frozenset(
    {"verified", "partially_verified", "unverified", "blocked"}
)

# First pins established at E0 (Team 09, 2026-11-07, git ls-remote on
# purplelongship; re-measured identical at W08 promotion, 2026-11-08).
# These engines had NO pin recorded anywhere in this fork before E0;
# they are first pins, not long-standing pins, and must never be
# presented as such -- or drift without a new lock revision.
FIRST_PINS = {
    "RuneTarotEngine": "432e461136ba58cb3e507bb9cd86b4bb2faba80b",
    "Seidr Engine": "fdc2b3c85c62982a4550dfe476751287d723519d",
    "Hamr": "f77aa588601b38a69b6c1fc0a6733ed5e95dffa8",
    "Seidr-Smidja": "32cdbd7a87358bc1f6f046c4e1449c35f4d5d40a",
    "AIAvatarKit": "9295e096169316ec19e9fa712e52733d912fd5e7",
    "OmniVoice": "a4068c820f21307df337e34f67d3dda443735ad4",
    "ChatIndex": "7df2c9208db6f113f85a6c09295bec7f0f2114e7",
}

RAVENS_TREE_HEAD = "fc761f020b39f9be875310d271aac7423239d5f8"
RAVENS_NAMES = frozenset({"Muninn", "Huginn"})
_STALE_ABSENCE_CLAIM = "absent on purplelongship"


class IntegrationLedgerError(Exception):
    """Named, honest ledger failure (missing/invalid/still-draft lock)."""

    def __init__(self, name: str, detail: str) -> None:
        super().__init__(detail)
        self.name = name
        self.detail = detail


def repo_root(module_file: str | Path | None = None) -> Path:
    """Repository root for this plugin (plugins/volmarr-core -> root)."""
    return Path(module_file or __file__).resolve().parents[2]


def default_lock_path(root: Path | None = None) -> Path:
    return (root or repo_root()) / LOCK_RELATIVE_PATH


def load_lock(path: Path | None = None) -> dict[str, Any]:
    """Load the promoted lock; refuse missing, invalid, or DRAFT locks."""
    lock_path = Path(path) if path is not None else default_lock_path()
    if not lock_path.is_file():
        raise IntegrationLedgerError(
            "lock_missing", f"integration lock not found at {lock_path}"
        )
    try:
        payload = json.loads(lock_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise IntegrationLedgerError(
            "lock_invalid", f"integration lock at {lock_path} is unreadable: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise IntegrationLedgerError(
            "lock_invalid", "integration lock must be a JSON object"
        )
    status = str(payload.get("status", ""))
    if status.strip().upper().startswith("DRAFT"):
        raise IntegrationLedgerError(
            "lock_still_draft",
            "integration lock is still marked DRAFT; an unverified lock "
            "is never served as the verified lock",
        )
    engines = payload.get("engines")
    if not isinstance(engines, list) or not engines:
        raise IntegrationLedgerError(
            "lock_invalid", "integration lock carries no engine rows"
        )
    return payload


def validate_lock(lock: dict[str, Any]) -> list[str]:
    """Structural + honesty checks over a loaded lock. Returns problems."""
    problems: list[str] = []
    engines = lock.get("engines")
    if not isinstance(engines, list):
        return ["engines: not a list"]
    seen: set[str] = set()
    for index, row in enumerate(engines):
        if not isinstance(row, dict):
            problems.append(f"row {index}: not an object")
            continue
        name = row.get("name")
        if not isinstance(name, str) or not name:
            problems.append(f"row {index}: missing name")
            continue
        if name in seen:
            problems.append(f"{name}: duplicate row")
        seen.add(name)
        adapter = row.get("adapter")
        if not isinstance(adapter, dict):
            problems.append(f"{name}: missing adapter record")
        else:
            mode = adapter.get("mode")
            if mode not in ADAPTER_MODES:
                problems.append(f"{name}: adapter mode {mode!r} not classified")
            paths = adapter.get("paths")
            if not isinstance(paths, list) or not paths:
                problems.append(f"{name}: adapter paths missing")
        if row.get("evidence_stage") not in EVIDENCE_STAGES:
            problems.append(
                f"{name}: evidence stage {row.get('evidence_stage')!r} "
                "is not a section 28.3 stage"
            )
        verification = row.get("verification")
        if not isinstance(verification, dict) or (
            verification.get("status") not in VERIFICATION_STATES
        ):
            problems.append(f"{name}: verification state missing or unknown")
        if name in FIRST_PINS and row.get("pinned") != FIRST_PINS[name]:
            problems.append(
                f"{name}: pin {row.get('pinned')!r} differs from the E0 "
                f"first pin {FIRST_PINS[name]}"
            )
        if name in RAVENS_NAMES:
            blob = json.dumps(row, sort_keys=True).lower()
            if _STALE_ABSENCE_CLAIM in blob:
                problems.append(
                    f"{name}: row repeats the superseded ravens-absent "
                    "claim (disk proof W02: ~/ravens is present on "
                    "purplelongship at fc761f0)"
                )
    for name in FIRST_PINS:
        if name not in seen:
            problems.append(f"{name}: first-pin engine row missing")
    return problems


def _git_head(tree: Path) -> str | None:
    """Resolve a checkout's HEAD SHA by reading .git only (no subprocess)."""
    git_dir = tree / ".git"
    if git_dir.is_file():
        # Worktree: .git is a pointer file ("gitdir: <path>").
        try:
            text = git_dir.read_text(encoding="utf-8").strip()
        except OSError:
            return None
        if not text.startswith("gitdir:"):
            return None
        git_dir = Path(text.split(":", 1)[1].strip())
    if not git_dir.is_dir():
        return None
    try:
        head = (git_dir / "HEAD").read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not head.startswith("ref:"):
        return head or None
    ref = head.split(":", 1)[1].strip()
    ref_path = git_dir / ref
    if ref_path.is_file():
        try:
            return ref_path.read_text(encoding="utf-8").strip() or None
        except OSError:
            return None
    packed = git_dir / "packed-refs"
    if packed.is_file():
        try:
            for line in packed.read_text(encoding="utf-8").splitlines():
                sha, _, name = line.partition(" ")
                if name.strip() == ref:
                    return sha.strip() or None
        except OSError:
            return None
    return None


def ravens_tree_status(home: Path | None = None) -> dict[str, Any]:
    """Local ravens tree truth: presence + HEAD vs the recorded tree pin."""
    base = Path(home) if home is not None else Path.home()
    tree = base / "ravens"
    present = tree.is_dir()
    head = _git_head(tree) if present else None
    return {
        "present": present,
        "path": str(tree),
        "head": head,
        "expected_head": RAVENS_TREE_HEAD,
        "matches_pin": bool(present and head == RAVENS_TREE_HEAD),
    }


def _row_status(
    row: dict[str, Any], root: Path, ravens: dict[str, Any]
) -> dict[str, Any]:
    adapter = row.get("adapter") or {}
    paths = adapter.get("paths") or []
    missing = [p for p in paths if not (root / p).exists()]
    record: dict[str, Any] = {
        "name": row.get("name"),
        "repo": row.get("repo"),
        "pinned": row.get("pinned"),
        "current_head": row.get("current_head"),
        "update_needed": row.get("update_needed"),
        "license": row.get("license"),
        "adapter_plugin": adapter.get("plugin"),
        "adapter_mode": adapter.get("mode"),
        "adapter_paths_present": not missing,
        "adapter_paths_missing": missing,
        "evidence_stage": row.get("evidence_stage"),
        "verification": (row.get("verification") or {}).get("status"),
        "verdict": row.get("verdict"),
    }
    if row.get("name") in RAVENS_NAMES:
        record["ravens_tree"] = ravens
    return record


def integration_status(
    lock_path: Path | None = None,
    *,
    root: Path | None = None,
    home: Path | None = None,
) -> dict[str, Any]:
    """Full read-only E0 status: lock validation + local adapter truth."""
    lock = load_lock(lock_path)
    base = Path(root) if root is not None else repo_root()
    problems = validate_lock(lock)
    ravens = ravens_tree_status(home)
    rows = [_row_status(row, base, ravens) for row in lock["engines"]]
    for row in rows:
        if row["adapter_paths_missing"]:
            problems.append(
                f"{row['name']}: adapter paths missing in this tree: "
                + ", ".join(row["adapter_paths_missing"])
            )
    if any(r["name"] in RAVENS_NAMES for r in rows) and not ravens["matches_pin"]:
        problems.append(
            "ravens tree: ~/ravens is absent or its HEAD differs from "
            f"the recorded tree pin {RAVENS_TREE_HEAD}"
        )
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["verification"]] = counts.get(row["verification"], 0) + 1
    fork = lock.get("fork") or {}
    return {
        "status": "ok" if not problems else "problems",
        "lock_status": lock.get("status"),
        "fork_head_at_promotion": fork.get("head"),
        "readme_sha256_at_promotion": fork.get("readme_sha256"),
        "engine_count": len(rows),
        "verification_counts": counts,
        "first_pins": dict(FIRST_PINS),
        "ravens_tree": ravens,
        "problems": problems,
        "engines": rows,
    }


def find_engine(lock: dict[str, Any], name: str) -> dict[str, Any] | None:
    """One raw lock row by name (case-insensitive); None when absent."""
    wanted = name.strip().lower()
    for row in lock.get("engines") or []:
        if isinstance(row, dict) and str(row.get("name", "")).lower() == wanted:
            return row
    return None
