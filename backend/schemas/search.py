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
    hybrid: bool = Field(default=True, description="Enable hybrid vector+keyword search")
    dense_weight: float = Field(default=1.0, ge=0.0, le=10.0, description="Weight for dense vector branch in RRF fusion")
    keyword_weight: float = Field(default=0.8, ge=0.0, le=10.0, description="Weight for keyword branch in RRF fusion")


class SearchResult(BaseModel):
    """Single search result with metadata."""

    knowledge_id: str
    title: str
    content: str
    kind: str
    score: Optional[float] = None
    tags: list[str] = []
    hybrid_score: Optional[float] = None
    dense_score: Optional[float] = None
    keyword_score: Optional[float] = None


class SearchResponse(BaseModel):
    """Search response data."""

    results: list[SearchResult]
