"""Extended state schema for the autonomous intelligence workflow."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AutonomousState(BaseModel):
    """State that flows through the full autonomous intelligence pipeline.

    Extends OperationsState with article-level fields and project-manager outputs.
    """

    # ── Input ────────────────────────────────────────────────
    article_id: str = Field(default="", description="Source article UUID")
    topic: str = Field(default="", description="Research topic / article title")
    content: str = Field(default="", description="Article content for knowledge extraction")
    focus_areas: list[str] = Field(default_factory=list)
    target_languages: list[str] = Field(default_factory=lambda: ["zh-CN", "ja"])
    source_language: str | None = Field(default=None)
    tags: list[str] = Field(default_factory=list)
    source: str = Field(default="", description="Data source name")

    # ── Intelligence stage outputs ──────────────────────────
    research_result: dict[str, Any] | None = Field(default=None)
    analysis_result: dict[str, Any] | None = Field(default=None)
    translation_result: dict[str, Any] | None = Field(default=None)

    # ── Operations stage outputs ────────────────────────────
    knowledge_result: dict[str, Any] | None = Field(default=None)
    project_plan_result: dict[str, Any] | None = Field(default=None)
    notification_result: dict[str, Any] | None = Field(default=None)

    # ── Accumulators ────────────────────────────────────────
    errors: list[dict[str, str]] = Field(default_factory=list)

    def add_error(self, stage: str, error: str) -> None:
        self.errors.append({"stage": stage, "error": error})
