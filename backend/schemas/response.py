"""Shared API response envelope."""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel

from .error import ErrorResponse

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    """Standard API response envelope.

    All endpoints return this structure for consistency.
    On success: {success: true, data: T, error: None}
    On error:   {success: false, data: None, error: ErrorResponse}
    """

    success: bool
    data: T | None
    error: ErrorResponse | None = None
