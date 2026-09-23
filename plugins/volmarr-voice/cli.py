"""Operator CLI boundary for the gated avatar presentation feed."""

from __future__ import annotations

import argparse
import json

from .presentation import CONTRACT_VERSION


def register_cli(parser: argparse.ArgumentParser) -> None:
    subcommands = parser.add_subparsers(dest="volmarr_voice_action")
    status = subcommands.add_parser(
        "status",
        help="Report the avatar feed gate without loading secrets or binding sockets",
    )
    status.add_argument("--json", action="store_true", dest="json_output")


def _status() -> dict[str, object]:
    return {
        "success": True,
        "contract": CONTRACT_VERSION,
        "serve_enabled": False,
        "runtime_registered": False,
        "listener_started": False,
        "producer": "operator-stdin-only",
        "automatic_voice_mirroring": False,
        "reason": "serve action remains gated pending operator-runner contracts",
    }


def voice_command(args: argparse.Namespace) -> int:
    if getattr(args, "volmarr_voice_action", None) != "status":
        print("Usage: hermes volmarr-voice status [--json]")
        return 1
    status = _status()
    if getattr(args, "json_output", False):
        print(json.dumps(status, sort_keys=True))
    else:
        print("Avatar presentation feed: gated")
        print(f"Contract: {status['contract']}")
        print("Listener started: no")
        print("Automatic Hermes voice mirroring: unavailable")
    return 0
