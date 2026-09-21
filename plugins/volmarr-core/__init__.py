"""Composition root for Volmarr-specific Hermes integrations."""

from __future__ import annotations

from functools import partial

from .cli import health_command, register_cli
from .lifecycle import LifecycleBridge


def register(ctx) -> None:
    """Register the first Volmarr vertical slice without modifying Hermes core."""
    bridge = LifecycleBridge(ctx)
    for hook_name, callback in bridge.hooks():
        ctx.register_hook(hook_name, callback)
    ctx.register_cli_command(
        name="volmarr",
        help="Inspect Volmarr's Hermes integrations",
        setup_fn=register_cli,
        handler_fn=partial(health_command, ctx=ctx),
        description="Profile-aware operator commands for Volmarr's Hermes integrations.",
    )
