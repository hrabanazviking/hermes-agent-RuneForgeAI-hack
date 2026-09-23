"""Hermes registration boundary for Volmarr voice and presentation contracts."""

from __future__ import annotations

from .cli import register_cli, voice_command
from .tools import register_tools


def register(ctx) -> None:
    """Register the non-operating voice readiness probe."""
    register_tools(ctx)
    ctx.register_cli_command(
        name="volmarr-voice",
        help="Inspect Volmarr's voice and avatar presentation boundary",
        setup_fn=register_cli,
        handler_fn=voice_command,
        description="Operator-owned voice and avatar presentation commands.",
    )
