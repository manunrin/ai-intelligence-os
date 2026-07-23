"""Evaluation criteria configuration for agent quality assessment."""

from __future__ import annotations

DEFAULT_THRESHOLD = 0.6


def get_criteria() -> list[str]:
    """Return the ordered list of evaluation criteria."""
    return ["accuracy", "relevance", "actionability", "completeness"]


def get_threshold() -> float:
    """Return the default quality threshold for pass/fail decisions."""
    return DEFAULT_THRESHOLD
