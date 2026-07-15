"""Extended state schema for the knowledge pipeline — includes operations agent outputs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class OperationsState(BaseModel):
    """State that flows through the knowledge pipeline after the initial intelligence stages.

    Extends the base intelligence state with knowledge extraction, pronunciation,
    project planning, and notification generation outputs.
    """

    # ── Input (set by caller) ──────────────────────────────
    topic: str = Field(default="", description="Research topic")
    focus_areas: list[str] = Field(default_factory=list)
    target_languages: list[str] = Field(default_factory=lambda: ["zh-CN", "ja"])
    source_language: str | None = Field(default=None)

    # ── Intelligence stage outputs (from existing graph) ───
    research_result: dict[str, Any] | None = Field(default=None)
    analysis_result: dict[str, Any] | None = Field(default=None)
    translation_result: dict[str, Any] | None = Field(default=None)

    # ── Operations stage outputs ───────────────────────────
    knowledge_result: dict[str, Any] | None = Field(default=None, description="KnowledgeAgent output")
    pronunciation_result: dict[str, Any] | None = Field(default=None, description="PronunciationAgent output")
    project_plan_result: dict[str, Any] | None = Field(default=None, description="ProjectManagerAgent output")
    notification_result: dict[str, Any] | None = Field(default=None, description="NotificationAgent output")

    # ── Accumulators ──────────────────────────────────────
    errors: list[dict[str, str]] = Field(default_factory=list)

    # ── LLM message history ───────────────────────────────
    messages: Any = Field(default_factory=list)

    def add_error(self, stage: str, error: str) -> None:
        self.errors.append({"stage": stage, "error": error})
