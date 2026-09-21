"""Operator CLI for the opt-in Volmarr composition plugin."""

from __future__ import annotations

import argparse
import json

from .health import probe_verdandi


def register_cli(parser: argparse.ArgumentParser) -> None:
    subcommands = parser.add_subparsers(dest="volmarr_action")
    health = subcommands.add_parser(
        "health",
        help="Probe the active profile's Verðandi transport",
    )
    health.add_argument("--json", action="store_true", dest="json_output")


def health_command(args: argparse.Namespace, *, ctx) -> int:
    if getattr(args, "volmarr_action", None) != "health":
        print("Usage: hermes volmarr health [--json]")
        return 2

    report = probe_verdandi(ctx)
    if getattr(args, "json_output", False):
        print(json.dumps(report.as_dict(), sort_keys=True))
    else:
        mark = "healthy" if report.healthy else report.status.replace("_", " ")
        print(f"Verðandi: {mark}")
        print(f"Socket: {report.socket_path}")
        if report.latency_ms is not None:
            print(f"Latency: {report.latency_ms} ms")
        if report.sequence is not None:
            print(f"Sequence: {report.sequence}")
        if report.uptime_seconds is not None:
            print(f"Uptime: {report.uptime_seconds} s")
        if report.error_type:
            print(f"Error type: {report.error_type}")
    return 0 if report.healthy else 1
