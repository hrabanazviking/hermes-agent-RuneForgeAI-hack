"""Composition root for Volmarr-specific Hermes integrations."""

from __future__ import annotations

from .lifecycle import LifecycleBridge


def register(ctx) -> None:
    """Register the first Volmarr vertical slice without modifying Hermes core."""
    bridge = LifecycleBridge(ctx)
    for hook_name, callback in bridge.hooks():
        ctx.register_hook(hook_name, callback)
