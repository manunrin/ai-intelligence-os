"""Tests for RAG streaming endpoint — POST /api/v1/knowledge/rag/stream."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from backend.main import create_app


class MockLLMProvider:
    """Minimal mock LLM provider that streams tokens."""

    name = "mock_llm"

    def __init__(self, tokens=None):
        self.tokens = tokens or ["Hello ", "world", "!"]

    async def stream(self, messages, model, **kwargs):
        for token in self.tokens:
            yield token

    async def chat(self, messages, model, **kwargs):
        return MagicMock(content="".join(self.tokens))

    async def embedding(self, text, model="text-embedding-3-small", **kwargs):
        return MagicMock(embeddings=[], usage={})

    async def health_check(self):
        return True


def _make_retrieval_result(kid, title):
    """Create a RetrievalResult-like object."""
    result = MagicMock()
    result.knowledge_id = kid
    result.title = title
    result.content = f"Content about {title}"
    result.kind = "note"
    result.score = 0.9
    result.tags = []
    result.dense_score = 0.85
    result.keyword_score = 0.7
    return result


@pytest.fixture
def client_with_mocks():
    """TestClient with mocked LLM provider and retriever."""
    fake_user = MagicMock()
    fake_user.id = "test-user-id"
    fake_user.username = "testuser"
    fake_user.role = "user"
    fake_user.is_active = True

    app = create_app()

    from backend.routers.deps import get_current_user, get_llm_provider, get_db, get_embedding_client, get_vector_service

    async def mock_get_current_user():
        return fake_user

    async def mock_get_llm_provider():
        return MockLLMProvider(["Hello ", "world", "!"])

    # Mock AI infrastructure dependencies that require app startup
    async def mock_get_embedding_client():
        return MagicMock()

    async def mock_get_vector_service():
        return MagicMock()

    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_llm_provider] = mock_get_llm_provider
    app.dependency_overrides[get_embedding_client] = mock_get_embedding_client
    app.dependency_overrides[get_vector_service] = mock_get_vector_service

    # Mock retriever by monkey-patching RagRetriever.retrieve
    from backend.services.rag.retriever import RagRetriever
    original_init = RagRetriever.__init__
    original_retrieve = RagRetriever.retrieve

    async def mock_retrieve(self, query, limit=5, score_threshold=None, kind_filter=None, tag_filter=None, hybrid=True, dense_weight=1.0, keyword_weight=0.8):
        return [_make_retrieval_result("kid-1", "AI Overview"), _make_retrieval_result("kid-2", "Machine Learning Basics")]

    RagRetriever.__init__ = lambda self, session, embedding_client, vector_service: None
    RagRetriever.retrieve = mock_retrieve

    yield TestClient(app)

    app.dependency_overrides.clear()
    RagRetriever.__init__ = original_init
    RagRetriever.retrieve = original_retrieve


def test_stream_returns_sse_format(client_with_mocks):
    """Verify streaming response uses SSE format."""
    resp = client_with_mocks.post(
        "/api/v1/knowledge/rag/stream",
        json={"query": "What is AI?", "limit": 2},
    )

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "text/event-stream; charset=utf-8"

    body = resp.text
    lines = [line for line in body.split("\n") if line.strip()]

    # Should have multiple data lines (one per token + final done event)
    assert len(lines) >= 3

    # Verify SSE format
    for line in lines:
        assert line.startswith("data: ")


def test_stream_tokens_incremental(client_with_mocks):
    """Verify tokens arrive incrementally."""
    resp = client_with_mocks.post(
        "/api/v1/knowledge/rag/stream",
        json={"query": "What is AI?", "limit": 2},
    )

    body = resp.text
    lines = [line for line in body.split("\n") if line.strip()]

    token_events = []
    for line in lines:
        data = json.loads(line[len("data: "):])
        if data["type"] == "token":
            token_events.append(data["content"])

    assert len(token_events) == 3
    assert "".join(token_events) == "Hello world!"


def test_stream_done_event_has_sources(client_with_mocks):
    """Verify done event contains sources array."""
    resp = client_with_mocks.post(
        "/api/v1/knowledge/rag/stream",
        json={"query": "What is AI?", "limit": 2},
    )

    body = resp.text
    lines = [line for line in body.split("\n") if line.strip()]

    last_line = lines[-1]
    last_data = json.loads(last_line[len("data: "):])

    assert last_data["type"] == "done"
    assert "sources" in last_data
    assert isinstance(last_data["sources"], list)
    assert len(last_data["sources"]) == 2
    assert last_data["sources"][0]["knowledge_id"] == "kid-1"
    assert last_data["sources"][1]["knowledge_id"] == "kid-2"


def test_stream_empty_context(client_with_mocks):
    """Verify empty context returns minimal SSE event."""
    from backend.services.rag.retriever import RagRetriever

    async def mock_retrieve_empty(self, query, limit=5, score_threshold=None, kind_filter=None, tag_filter=None, hybrid=True, dense_weight=1.0, keyword_weight=0.8):
        return []

    original_retrieve = RagRetriever.retrieve
    RagRetriever.retrieve = mock_retrieve_empty

    try:
        resp = client_with_mocks.post(
            "/api/v1/knowledge/rag/stream",
            json={"query": "What is AI?", "limit": 2},
        )

        assert resp.status_code == 200
        body = resp.text
        assert "data:" in body
    finally:
        RagRetriever.retrieve = original_retrieve


def test_stream_error_handling(client_with_mocks):
    """Verify error events are properly formatted."""
    from backend.routers.deps import get_llm_provider
    from backend.services.rag.retriever import RagRetriever

    class FailingProvider(MockLLMProvider):
        async def stream(self, messages, model, **kwargs):
            raise RuntimeError("LLM service unavailable")

    async def mock_get_failing_provider():
        return FailingProvider([])

    client_with_mocks.app.dependency_overrides[get_llm_provider] = mock_get_failing_provider

    resp = client_with_mocks.post(
        "/api/v1/knowledge/rag/stream",
        json={"query": "What is AI?", "limit": 2},
    )

    assert resp.status_code == 200
    body = resp.text
    lines = [line for line in body.split("\n") if line.strip()]

    # Should contain an error event
    error_found = False
    for line in lines:
        data = json.loads(line[len("data: "):])
        if data.get("type") == "error":
            error_found = True
            assert "message" in data
            break

    assert error_found
