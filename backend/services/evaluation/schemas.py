"""Pydantic schemas for the evaluation API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class EvaluationRequest(BaseModel):
    pipeline_type: str = Field(description="Pipeline type, e.g. 'intelligence' or 'autonomous'")
    output_payload: dict = Field(description="Agent run output payload to evaluate")
    input_payload: dict = Field(description="Original input payload that triggered the run")


class EvaluationResponse(BaseModel):
    score: float | None = Field(default=None, description="Overall quality score 0-100")
    criteria: dict[str, float] | None = Field(
        default=None, description="Per-criterion scores"
    )
    evaluator_notes: str | None = Field(
        default=None, description="Human-readable evaluation notes"
    )
