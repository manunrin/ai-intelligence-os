"""Shared state schema for the LangGraph intelligence pipeline."""

from __future__ import annotations

from typing import Any

from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


class IntelligenceState(BaseModel):
    """State that flows through the daily intelligence workflow.

    Each node reads from and writes to this state. Fields are merged
    on each step — partial updates are safe.
    """

    # ── Input (set by caller) ──────────────────────────────
    topic: str = Field(default="", description="Research topic")
    focus_areas: list[str] = Field(default_factory=list, description="Analysis focus areas")
    target_languages: list[str] = Field(default_factory=lambda: ["zh-CN", "ja"], description="Translation targets")
    source_language: str | None = Field(default=None, description="Original content language")

    # ── Stage outputs ─────────────────────────────────────
    research_result: dict[str, Any] | None = Field(default=None, description="ResearchAgent output")
    analysis_result: dict[str, Any] | None = Field(default=None, description="AnalystAgent output")
    translation_result: dict[str, Any] | None = Field(default=None, description="TranslatorAgent output")

    # ── Accumulators ──────────────────────────────────────
    errors: list[dict[str, str]] = Field(default_factory=list, description="Errors per stage")

    # ── LLM message history (LangGraph built-in) ──────────
    messages: Any = Field(default_factory=list, description="Chat messages for LLM context")

    def add_error(self, stage: str, error: str) -> None:
        """Record an error from a specific pipeline stage."""
        self.errors.append({"stage": stage, "error": error})
