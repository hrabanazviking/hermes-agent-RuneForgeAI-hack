"""Composition root for Volmarr-specific Hermes integrations."""

from __future__ import annotations

from functools import partial

from .affective_bridge import AffectiveBridge
from .cli import health_command, register_cli
from .consolidation import register_sleep_tool
from .goals import GoalBridge, register_goal_tools
from .heartbeat import HeartbeatBridge, register_heartbeat_tool
from .identity import IdentityBridge
from .lifecycle import LifecycleBridge
from .present_state import PresentStateBridge
from .relationships import RelationshipBridge, register_relationship_tools
from .wyrd_tools import register_wyrd_tools
from .wyrd_context import WyrdContextBridge


def register(ctx) -> None:
    """Register the first Volmarr vertical slice without modifying Hermes core."""
    bridge = LifecycleBridge(ctx)
    for hook_name, callback in bridge.hooks():
        ctx.register_hook(hook_name, callback)
    identity = IdentityBridge(ctx)
    for hook_name, callback in identity.hooks():
        ctx.register_hook(hook_name, callback)
    relationships = RelationshipBridge(ctx)
    for hook_name, callback in relationships.hooks():
        ctx.register_hook(hook_name, callback)
    goals = GoalBridge(ctx)
    for hook_name, callback in goals.hooks():
        ctx.register_hook(hook_name, callback)
    heartbeat = HeartbeatBridge(ctx)
    for hook_name, callback in heartbeat.hooks():
        ctx.register_hook(hook_name, callback)
    affective = AffectiveBridge(ctx)
    for hook_name, callback in affective.hooks():
        ctx.register_hook(hook_name, callback)
    wyrd_context = WyrdContextBridge(ctx)
    present_state = PresentStateBridge(
        ctx,
        packet_sources=(affective.packet_items, wyrd_context.packet_items),
    )
    for hook_name, callback in present_state.hooks():
        ctx.register_hook(hook_name, callback)
    register_wyrd_tools(ctx)
    register_relationship_tools(ctx)
    register_goal_tools(ctx)
    register_heartbeat_tool(ctx)
    register_sleep_tool(ctx)
    ctx.register_cli_command(
        name="volmarr",
        help="Inspect Volmarr's Hermes integrations",
        setup_fn=register_cli,
        handler_fn=partial(health_command, ctx=ctx),
        description="Profile-aware operator commands for Volmarr's Hermes integrations.",
    )
