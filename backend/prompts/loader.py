"""Prompt template loader — reads from markdown/yaml files."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


def load_prompt(name: str, **variables: Any) -> str:
    """Load a prompt template from a .md file and render with variables.

    Templates live in backend/prompts/<name>.md.
    Variables are injected via Python f-string style {{ var }} syntax.

    Example:
        Template file: backend/prompts/research.md
        Content: "Research the following topic: {{topic}}. Focus on: {{focus_areas}}"

        Usage:
            prompt = load_prompt("research", topic="AI agents", focus_areas=["security", "performance"])
    """
    template_path = _PROMPTS_DIR / f"{name}.md"
    if not template_path.exists():
        raise FileNotFoundError(f"Prompt template not found: {template_path}")

    content = template_path.read_text(encoding="utf-8")
    return content.format(**variables)


def list_available_prompts() -> list[str]:
    """Return names of all available prompt templates."""
    if not _PROMPTS_DIR.exists():
        return []
    return [p.stem for p in _PROMPTS_DIR.glob("*.md")]
