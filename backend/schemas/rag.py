"""RAG question-answering request/response schemas."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class RAGRequest(BaseModel):
    """RAG question-answering request body."""

    query: str = Field(..., min_length=1, description="User's question")
    limit: int = Field(default=5, ge=1, le=20, description="Maximum context items to retrieve")
    system_prompt: Optional[str] = Field(default=None, description="Custom system prompt for the LLM")


class RAGSource(BaseModel):
    """Citation source for a RAG answer."""

    knowledge_id: str
    title: str


class RAGResponse(BaseModel):
    """RAG answer response data."""

    answer: str
    sources: list[RAGSource]
    query: str
