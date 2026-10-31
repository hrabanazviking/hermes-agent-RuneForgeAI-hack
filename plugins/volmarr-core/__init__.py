"""Composition root for Volmarr-specific Hermes integrations."""

from __future__ import annotations

from functools import partial

from .affective_bridge import AffectiveBridge
from .agency import AgencyBridge
from .agency_routines import AgencyRoutineBridge
from .autonomy import AutonomyBridge
from .background_research import BackgroundResearchBridge
from .cli import health_command, register_cli
from .consolidation import register_sleep_tool
from .curiosity import CuriosityBridge
from .drives import DriveBridge
from .goals import GoalBridge, register_goal_tools
from .heartbeat import HeartbeatBridge, register_heartbeat_tool
from .identity import IdentityBridge
from .intrinsic_goals import IntrinsicGoalBridge
from .lifecycle import LifecycleBridge
from .local_autonomy import LocalAutonomyBridge
from .mempalace_retrieval import MemPalaceRetrievalBridge
from .metacognition import MetacognitionBridge
from .openviking_retrieval import OpenVikingRetrievalBridge
from .present_state import PresentStateBridge
from .relationships import RelationshipBridge, register_relationship_tools
from .self_improvement import SelfImprovementBridge
from .awareness import AwarenessBridge
from .self_model_layers import LayeredSelfModelBridge
from .motivation_lifecycle import MotivationLifecycleBridge
from .reflection_detail import ReflectionDetailBridge
from .curiosity_detail import CuriosityDetailBridge
from .autonomy_detail import AutonomyDetailBridge
from .agency_cycle_detail import AgencyCycleDetailBridge
from .self_state import SelfStateBridge
from .subjective_report import SubjectiveReportBridge
from .timescales import TimescaleBridge
from .self_model import SelfModelBridge
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
    intrinsic_goals = IntrinsicGoalBridge(ctx)
    for hook_name, callback in intrinsic_goals.hooks():
        ctx.register_hook(hook_name, callback)
    self_model = SelfModelBridge(ctx)
    for hook_name, callback in self_model.hooks():
        ctx.register_hook(hook_name, callback)
    drives = DriveBridge(ctx)
    for hook_name, callback in drives.hooks():
        ctx.register_hook(hook_name, callback)
    metacognition = MetacognitionBridge(ctx)
    for hook_name, callback in metacognition.hooks():
        ctx.register_hook(hook_name, callback)
    curiosity = CuriosityBridge(ctx)
    for hook_name, callback in curiosity.hooks():
        ctx.register_hook(hook_name, callback)
    autonomy = AutonomyBridge(ctx)
    for hook_name, callback in autonomy.hooks():
        ctx.register_hook(hook_name, callback)
    agency = AgencyBridge(ctx)
    agency_routine = AgencyRoutineBridge(ctx)
    local_autonomy = LocalAutonomyBridge(ctx)
    background_research = BackgroundResearchBridge(ctx)
    self_improvement = SelfImprovementBridge(ctx)
    timescales = TimescaleBridge(ctx)
    self_model_layers = LayeredSelfModelBridge(ctx)
    awareness = AwarenessBridge(ctx)
    for hook_name, callback in awareness.hooks():
        ctx.register_hook(hook_name, callback)
    subjective_report = SubjectiveReportBridge(ctx)
    motivation_lifecycle = MotivationLifecycleBridge(ctx)
    reflection_detail = ReflectionDetailBridge(ctx)
    curiosity_detail = CuriosityDetailBridge(ctx)
    autonomy_detail = AutonomyDetailBridge(ctx)
    agency_cycle_detail = AgencyCycleDetailBridge(ctx)
    self_state = SelfStateBridge(ctx)
    heartbeat = HeartbeatBridge(ctx)
    for hook_name, callback in heartbeat.hooks():
        ctx.register_hook(hook_name, callback)
    affective = AffectiveBridge(ctx)
    for hook_name, callback in affective.hooks():
        ctx.register_hook(hook_name, callback)
    wyrd_context = WyrdContextBridge(ctx)
    mempalace_retrieval = MemPalaceRetrievalBridge(ctx)
    openviking_retrieval = OpenVikingRetrievalBridge(ctx)
    present_state = PresentStateBridge(
        ctx,
        packet_sources=(
            affective.packet_items,
            wyrd_context.packet_items,
            mempalace_retrieval.packet_items,
            openviking_retrieval.packet_items,
            self_model.packet_items,
            drives.packet_items,
            metacognition.packet_items,
            curiosity.packet_items,
            autonomy.packet_items,
            agency.packet_items,
            agency_routine.packet_items,
            local_autonomy.packet_items,
            intrinsic_goals.packet_items,
            background_research.packet_items,
            self_improvement.packet_items,
            timescales.packet_items,
            self_model_layers.packet_items,
            awareness.packet_items,
            subjective_report.packet_items,
            motivation_lifecycle.packet_items,
            reflection_detail.packet_items,
            curiosity_detail.packet_items,
            autonomy_detail.packet_items,
            agency_cycle_detail.packet_items,
            self_state.packet_items,
        ),
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
