"""Reusable pagination dependency."""

from __future__ import annotations

from pydantic import BaseModel, Field


class PaginationParams(BaseModel):
    """Pagination parameters shared across all list endpoints."""

    offset: int = Field(default=0, ge=0, description="Number of items to skip")
    limit: int = Field(default=20, ge=1, le=100, description="Number of items to return (max 100)")


def get_pagination(
    offset: int = 0,
    limit: int = 20,
) -> PaginationParams:
    """FastAPI dependency that provides pagination params.

    Usage::

        @router.get("/items")
        async def list_items(pagination: PaginationParams = Depends(get_pagination)):
            ...
    """
    return PaginationParams(offset=offset, limit=limit)
