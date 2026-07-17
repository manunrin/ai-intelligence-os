"""Standardized API error response schema."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Structured error response matching all exception handlers."""

    code: str
    message: str
    details: list[dict[str, Any]] | None = None
