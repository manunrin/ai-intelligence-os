"""Search request/response schemas."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """Semantic search request body."""

    query: str = Field(..., min_length=1, description="Search query")
    limit: int = Field(default=5, ge=1, le=50, description="Maximum number of results")
    kind_filter: Optional[str] = Field(default=None, description="Filter by item kind")
    tag_filter: Optional[str] = Field(default=None, description="Filter by tag")
    score_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Minimum similarity score")


class SearchResult(BaseModel):
    """Single search result with metadata."""

    knowledge_id: str
    title: str
    content: str
    kind: str
    score: Optional[float] = None
    tags: list[str] = []


class SearchResponse(BaseModel):
    """Search response data."""

    results: list[SearchResult]
