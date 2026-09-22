"""Hermes registration boundary for Volmarr's local Seidr-Smidja tools."""

from __future__ import annotations

from .tools import register_tools


def register(ctx) -> None:
    """Register read-only Loom validation without forge authority."""
    register_tools(ctx)
