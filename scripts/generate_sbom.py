#!/usr/bin/env python3
"""Generate a CycloneDX SBOM from this checkout's uv.lock (W02/U2).

The SBOM is a deployment-trust artifact: every locked package is listed
with its version and, crucially, its *source class* — registry, editable
local path, git, direct URL, or virtual. The fork's supply-chain law is
checked, not just recorded: the unpublished raven packages (muninn,
huginn) must resolve from their local editable paths; if either ever
appears with a registry (or any non-local) source, this generator fails
loudly instead of blessing a lock that would install unrelated PyPI
software under those names.

Usage:
    scripts/generate_sbom.py [--lock uv.lock] [--out docs/modernization/SBOM.cdx.json]

Exit status: 0 when the SBOM was written and every supply-chain check
passed; 1 when a check failed (the SBOM is still written, marked with
the violations, so the failure is inspectable).
"""

from __future__ import annotations

import argparse
import json
import sys
import tomllib
from pathlib import Path

# Packages that must never come from an index (COMPONENT_LICENSES.md /
# CUSTOMIZATIONS.md ravens row): unpublished, and the bare names collide
# with unrelated PyPI projects.
LOCAL_ONLY = {"muninn", "huginn"}


def source_class(source: object) -> str:
    if not isinstance(source, dict) or not source:
        return "virtual"
    if "editable" in source:
        return "editable-local"
    if "registry" in source:
        return "registry"
    if "git" in source:
        return "git"
    if "url" in source:
        return "archive-url"
    if "archive" in source:
        return "archive-url"
    return "other"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lock", type=Path, default=Path("uv.lock"))
    parser.add_argument("--out", type=Path, default=Path("docs/modernization/SBOM.cdx.json"))
    args = parser.parse_args()

    with args.lock.open("rb") as handle:
        lock = tomllib.load(handle)

    components = []
    violations = []
    counts: dict[str, int] = {}
    for package in lock.get("package", []):
        name = package.get("name", "")
        version = package.get("version", "")
        cls = source_class(package.get("source"))
        counts[cls] = counts.get(cls, 0) + 1
        if name in LOCAL_ONLY and cls != "editable-local":
            violations.append(
                f"{name}=={version} has source class {cls!r}; the ravens must stay "
                "bound to their local editable paths ([tool.uv.sources]) and never "
                "resolve from an index"
            )
        component = {
            "type": "library",
            "name": name,
            "version": version,
            "purl": f"pkg:pypi/{name}@{version}" if cls == "registry" else None,
            "properties": [{"name": "hermes:source-class", "value": cls}],
        }
        components.append({k: v for k, v in component.items() if v is not None})
    components.sort(key=lambda c: c["name"])

    sbom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "version": 1,
        "metadata": {
            "tools": [{"name": "hermes generate_sbom.py", "version": "1"}],
            "component": {
                "type": "application",
                "name": "hermes-agent (RuneForgeAI fork)",
                "properties": [
                    {"name": "hermes:lockfile", "value": str(args.lock)},
                    {"name": "hermes:source-class-counts",
                     "value": json.dumps(counts, sort_keys=True)},
                ],
            },
        },
        "components": components,
    }
    if violations:
        sbom["metadata"]["component"]["properties"].append(
            {"name": "hermes:supply-chain-violations", "value": "; ".join(violations)}
        )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(sbom, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    print(f"SBOM: {len(components)} components -> {args.out}")
    print(f"source classes: {json.dumps(counts, sort_keys=True)}")
    for violation in violations:
        print(f"SUPPLY-CHAIN VIOLATION: {violation}", file=sys.stderr)
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
