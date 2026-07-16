"""Shared API response envelope."""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """Standard API response envelope.

    All endpoints return this structure for consistency.
    """

    success: bool
    data: T | None
    error: str | None = None
