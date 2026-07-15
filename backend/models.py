"""Shared Pydantic models."""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"


class ErrorResponse(BaseModel):
    detail: str = Field(description="Error description")
    code: str = Field(description="Machine-readable error code")
