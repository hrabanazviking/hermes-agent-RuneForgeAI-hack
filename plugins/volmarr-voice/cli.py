"""Operator CLI boundary for the gated avatar presentation feed."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

from .presentation import CONTRACT_VERSION


def _unprivileged_port(value: str) -> int:
    try:
        port = int(value)
    except (TypeError, ValueError) as exc:
        raise argparse.ArgumentTypeError("port must be an integer") from exc
    if not 1024 <= port <= 65535:
        raise argparse.ArgumentTypeError("port must be from 1024 through 65535")
    return port


def register_cli(parser: argparse.ArgumentParser) -> None:
    subcommands = parser.add_subparsers(dest="volmarr_voice_action")
    status = subcommands.add_parser(
        "status",
        help="Report the avatar feed gate without loading secrets or binding sockets",
    )
    status.add_argument("--json", action="store_true", dest="json_output")
    serve = subcommands.add_parser(
        "serve",
        help="Run the operator-owned loopback feed from canonical stdin events",
    )
    serve.add_argument("--port", required=True, type=_unprivileged_port)


def _status() -> dict[str, object]:
    return {
        "success": True,
        "contract": CONTRACT_VERSION,
        "serve_enabled": True,
        "runtime_registered": False,
        "listener_started": False,
        "producer": "operator-stdin-only",
        "automatic_voice_mirroring": False,
        "reason": "serve is explicit and stdin-only; automatic voice mirroring is unavailable",
    }


def voice_command(args: argparse.Namespace) -> int:
    action = getattr(args, "volmarr_voice_action", None)
    if action == "serve":
        return _serve(args.port)
    if action != "status":
        print("Usage: hermes volmarr-voice {status|serve --port PORT}")
        return 1
    status = _status()
    if getattr(args, "json_output", False):
        print(json.dumps(status, sort_keys=True))
    else:
        print("Avatar presentation feed: operator-ready")
        print(f"Contract: {status['contract']}")
        print("Listener started: no")
        print("Automatic Hermes voice mirroring: unavailable")
    return 0


def _serve(port: int) -> int:
    """Run the explicit feed without exposing lifecycle control to a model."""

    from .admission import AvatarAdmissionError
    from .loopback import AvatarLoopbackError, AvatarLoopbackFeed
    from .runner import AvatarRunnerError, run_feed_from_stream

    stream = getattr(sys.stdin, "buffer", None)
    if stream is None:
        print("Avatar presentation feed refused: binary stdin is required", file=sys.stderr)
        return 1
    try:
        feed = AvatarLoopbackFeed(
            host="127.0.0.1",
            port=port,
            path="/v1/presentation",
            environ=os.environ,
        )
        published = asyncio.run(run_feed_from_stream(feed, stream))
    except KeyboardInterrupt:
        print("Avatar presentation feed stopped by operator", file=sys.stderr)
        return 130
    except (AvatarAdmissionError, AvatarLoopbackError, AvatarRunnerError, OSError):
        print("Avatar presentation feed failed", file=sys.stderr)
        return 1
    print(
        f"Avatar presentation feed stopped after {published} event(s)",
        file=sys.stderr,
    )
    return 0
