"""Hermes registration boundary for Volmarr's local astrology tools."""

from __future__ import annotations

from .tools import register_tools


def register(ctx) -> None:
    """Register deterministic calculations without prompts, state, or providers."""
    register_tools(ctx)
