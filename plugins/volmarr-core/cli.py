"""Operator CLI for the opt-in Volmarr composition plugin."""

from __future__ import annotations

import argparse
import json

from .cognition import probe_aesir
from .health import probe_verdandi


def register_cli(parser: argparse.ArgumentParser) -> None:
    subcommands = parser.add_subparsers(dest="volmarr_action")
    health = subcommands.add_parser(
        "health",
        help="Probe the active profile's Verðandi transport",
    )
    health.add_argument("--json", action="store_true", dest="json_output")
    cognition = subcommands.add_parser(
        "cognition",
        help="Inspect the local reflex-cognition endpoint",
    )
    cognition_subcommands = cognition.add_subparsers(dest="cognition_action")
    cognition_health = cognition_subcommands.add_parser(
        "health",
        help="Probe the configured A.E.S.I.R. model catalog",
    )
    cognition_health.add_argument("--json", action="store_true", dest="json_output")


def health_command(args: argparse.Namespace, *, ctx) -> int:
    action = getattr(args, "volmarr_action", None)
    if action == "cognition":
        if getattr(args, "cognition_action", None) != "health":
            print("Usage: hermes volmarr cognition health [--json]")
            return 2
        report = probe_aesir(ctx)
        label = "A.E.S.I.R."
    elif action == "health":
        report = probe_verdandi(ctx)
        label = "Verðandi"
    else:
        print("Usage: hermes volmarr {health|cognition health} [--json]")
        return 2

    if getattr(args, "json_output", False):
        print(json.dumps(report.as_dict(), sort_keys=True))
    else:
        mark = "healthy" if report.healthy else report.status.replace("_", " ")
        print(f"{label}: {mark}")
        location = getattr(report, "socket_path", None) or getattr(report, "base_url", "")
        print(f"Endpoint: {location}")
        if report.latency_ms is not None:
            print(f"Latency: {report.latency_ms} ms")
        if getattr(report, "sequence", None) is not None:
            print(f"Sequence: {report.sequence}")
        if getattr(report, "uptime_seconds", None) is not None:
            print(f"Uptime: {report.uptime_seconds} s")
        if getattr(report, "models", ()):
            print(f"Models: {', '.join(report.models)}")
        if report.error_type:
            print(f"Error type: {report.error_type}")
    return 0 if report.healthy else 1
