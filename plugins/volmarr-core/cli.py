"""Operator CLI for the opt-in Volmarr composition plugin."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .cognition import probe_aesir
from .health import probe_verdandi
from .routing import CognitionRequest, CognitionRouter, RoutingRequestError


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
    cognition_route = cognition_subcommands.add_parser(
        "route",
        help="Choose a cognition tier from a metadata-only JSON request",
    )
    cognition_route.add_argument(
        "--request",
        default="-",
        help="JSON request file, or - for standard input",
    )


def _load_route_request(source: str) -> dict:
    if source == "-":
        raw = sys.stdin.read(64 * 1024 + 1)
    else:
        raw = Path(source).read_text(encoding="utf-8")
    if len(raw.encode("utf-8")) > 64 * 1024:
        raise RoutingRequestError("routing request exceeds 64 KiB")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RoutingRequestError("routing request is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise RoutingRequestError("routing request must be a JSON object")
    return payload


def health_command(args: argparse.Namespace, *, ctx) -> int:
    action = getattr(args, "volmarr_action", None)
    if action == "cognition":
        cognition_action = getattr(args, "cognition_action", None)
        if cognition_action == "route":
            try:
                request = CognitionRequest.from_mapping(
                    _load_route_request(getattr(args, "request", "-"))
                )
                decision = CognitionRouter.from_plugin_context(ctx).decide(request)
            except (OSError, UnicodeError, RoutingRequestError) as exc:
                print(
                    json.dumps(
                        {"error": "invalid_routing_request", "detail": str(exc)},
                        sort_keys=True,
                    ),
                    file=sys.stderr,
                )
                return 2
            print(json.dumps(decision.as_dict(), sort_keys=True))
            return 0
        if cognition_action != "health":
            print("Usage: hermes volmarr cognition {health|route} [options]")
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
