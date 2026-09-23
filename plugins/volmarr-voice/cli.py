"""Operator CLI boundary for the gated avatar presentation feed."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from .presentation import (
    CONTRACT_VERSION,
    MAX_WAV_BYTES,
    PresentationContractError,
    build_presentation_event,
)


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
    encode = subcommands.add_parser(
        "encode",
        help="Encode one complete WAV as a canonical presentation event",
    )
    encode.add_argument("--audio", required=True)
    encode.add_argument("--session", required=True)
    encode.add_argument("--transaction", required=True)
    encode.add_argument("--sequence", type=int, default=0)
    encode.add_argument("--face")
    encode.add_argument("--animation")


def _status() -> dict[str, object]:
    return {
        "success": True,
        "contract": CONTRACT_VERSION,
        "serve_enabled": True,
        "runtime_registered": False,
        "listener_started": False,
        "producer": "operator-encoded-ndjson",
        "automatic_voice_mirroring": False,
        "reason": "serve is explicit and stdin-only; automatic voice mirroring is unavailable",
    }


def voice_command(args: argparse.Namespace) -> int:
    action = getattr(args, "volmarr_voice_action", None)
    if action == "serve":
        return _serve(args.port)
    if action == "encode":
        return _encode(args)
    if action != "status":
        print("Usage: hermes volmarr-voice {status|serve|encode} ...")
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


def _encode(args: argparse.Namespace) -> int:
    """Encode an operator-selected WAV without touching feed credentials or sockets."""

    try:
        source = Path(args.audio).expanduser()
        if source.is_symlink() or not source.is_file():
            raise OSError("audio source is not a regular file")
        size = source.stat().st_size
        if not 0 < size <= MAX_WAV_BYTES:
            raise OSError("audio source exceeds the presentation bound")
        event = build_presentation_event(
            kind="speech",
            session_id=args.session,
            transaction_id=args.transaction,
            sequence=args.sequence,
            audio_data=source.read_bytes(),
            face_name=args.face,
            animation_name=args.animation,
        )
    except (OSError, PresentationContractError, ValueError):
        print("Avatar presentation event encoding failed", file=sys.stderr)
        return 1
    print(json.dumps(event, separators=(",", ":"), ensure_ascii=True))
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
