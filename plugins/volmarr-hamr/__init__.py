"""Hermes registration boundary for Volmarr's local Hamr tools."""

from __future__ import annotations

from .tools import register_tools


def register(ctx) -> None:
    """Register read-only Hamr validation without Blender or build authority."""
    register_tools(ctx)
