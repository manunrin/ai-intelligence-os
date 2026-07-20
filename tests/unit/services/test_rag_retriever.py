"""Tests for RAG retriever hybrid search functionality."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.services.rag.retriever import RagRetriever, RetrievalResult


def _make_result(knowledge_id: str, score: float | None = None, dense_score: float | None = None, keyword_score: float | None = None) -> RetrievalResult:
    """Helper to create RetrievalResult instances for testing."""
    return RetrievalResult(
        knowledge_id=knowledge_id,
        title=f"Title {knowledge_id}",
        content=f"Content {knowledge_id}",
        kind="note",
        score=score,
        tags=[],
        dense_score=dense_score,
        keyword_score=keyword_score,
    )


class TestRRFFusion:
    """Test Reciprocal Rank Fusion implementation."""

    def test_rrf_basic_fusion(self):
        """Test basic RRF fusion of two ranked lists."""
        retriever = RagRetriever(
            session=MagicMock(),
            embedding_client=MagicMock(),
            vector_service=MagicMock(),
        )

        dense_results = [
            _make_result("id1", dense_score=0.9),
            _make_result("id2", dense_score=0.8),
            _make_result("id3", dense_score=0.7),
        ]

        keyword_results = [
            _make_result("id2", keyword_score=0.5),
            _make_result("id4", keyword_score=0.4),
            _make_result("id1", keyword_score=0.3),
        ]

        results = retriever._fuse_results(
            dense_results=dense_results,
            keyword_results=keyword_results,
            limit=5,
            score_threshold=None,
            dense_weight=1.0,
            keyword_weight=0.8,
        )

        # id2 should rank highest (rank 2 in both)
        assert len(results) == 4
        assert results[0].knowledge_id == "id2"
        assert results[0].score > results[1].score
        assert results[0].dense_score == 0.8
        assert results[0].keyword_score == 0.5

    def test_rrf_deduplicates_results(self):
        """Test that duplicate knowledge_ids are merged."""
        retriever = RagRetriever(
            session=MagicMock(),
            embedding_client=MagicMock(),
            vector_service=MagicMock(),
        )

        dense_results = [
            _make_result("id1", dense_score=0.9),
            _make_result("id2", dense_score=0.8),
        ]

        keyword_results = [
            _make_result("id1", keyword_score=0.7),
            _make_result("id3", keyword_score=0.6),
        ]

        results = retriever._fuse_results(
            dense_results=dense_results,
            keyword_results=keyword_results,
            limit=5,
            score_threshold=None,
            dense_weight=1.0,
            keyword_weight=0.8,
        )

        # Should have 3 unique results, not 4
        assert len(results) == 3
        ids = [r.knowledge_id for r in results]
        assert "id1" in ids
        assert "id2" in ids
        assert "id3" in ids

    def test_rrf_applies_limit(self):
        """Test that final limit is respected."""
        retriever = RagRetriever(
            session=MagicMock(),
            embedding_client=MagicMock(),
            vector_service=MagicMock(),
        )

        dense_results = [_make_result(f"id{i}", dense_score=0.9 - i * 0.1) for i in range(5)]
        keyword_results = []

        results = retriever._fuse_results(
            dense_results=dense_results,
            keyword_results=keyword_results,
            limit=2,
            score_threshold=None,
            dense_weight=1.0,
            keyword_weight=0.8,
        )

        assert len(results) == 2

    def test_rrf_applies_score_threshold(self):
        """Test that score threshold filters results."""
        retriever = RagRetriever(
            session=MagicMock(),
            embedding_client=MagicMock(),
            vector_service=MagicMock(),
        )

        dense_results = [
            _make_result("id1", dense_score=0.9),
            _make_result("id2", dense_score=0.1),
        ]
        keyword_results = []

        # RRF score for id1 at rank 1: 1.0 / (60 + 1) ≈ 0.0164
        # Set threshold above id2's score (rank 2: ~0.0161) but below id1's
        results = retriever._fuse_results(
            dense_results=dense_results,
            keyword_results=keyword_results,
            limit=10,
            score_threshold=0.0163,
            dense_weight=1.0,
            keyword_weight=0.8,
        )

        # Only id1 should remain (higher fused score)
        assert len(results) == 1
        assert results[0].knowledge_id == "id1"

    def test_rrf_empty_results(self):
        """Test fusion with empty input lists."""
        retriever = RagRetriever(
            session=MagicMock(),
            embedding_client=MagicMock(),
            vector_service=MagicMock(),
        )

        results = retriever._fuse_results(
            dense_results=[],
            keyword_results=[],
            limit=5,
            score_threshold=None,
            dense_weight=1.0,
            keyword_weight=0.8,
        )

        assert results == []

    def test_rrf_only_dense_results(self):
        """Test fusion when only dense branch has results."""
        retriever = RagRetriever(
            session=MagicMock(),
            embedding_client=MagicMock(),
            vector_service=MagicMock(),
        )

        dense_results = [
            _make_result("id1", dense_score=0.9),
            _make_result("id2", dense_score=0.8),
        ]

        results = retriever._fuse_results(
            dense_results=dense_results,
            keyword_results=[],
            limit=5,
            score_threshold=None,
            dense_weight=1.0,
            keyword_weight=0.8,
        )

        assert len(results) == 2
        assert results[0].knowledge_id == "id1"
        assert results[0].dense_score == 0.9
        assert results[0].keyword_score is None

    def test_rrf_only_keyword_results(self):
        """Test fusion when only keyword branch has results."""
        retriever = RagRetriever(
            session=MagicMock(),
            embedding_client=MagicMock(),
            vector_service=MagicMock(),
        )

        keyword_results = [
            _make_result("id1", keyword_score=0.7),
            _make_result("id2", keyword_score=0.6),
        ]

        results = retriever._fuse_results(
            dense_results=[],
            keyword_results=keyword_results,
            limit=5,
            score_threshold=None,
            dense_weight=1.0,
            keyword_weight=0.8,
        )

        assert len(results) == 2
        assert results[0].knowledge_id == "id1"
        assert results[0].dense_score is None
        assert results[0].keyword_score == 0.7

    def test_rrf_custom_weights(self):
        """Test RRF with custom weights."""
        retriever = RagRetriever(
            session=MagicMock(),
            embedding_client=MagicMock(),
            vector_service=MagicMock(),
        )

        dense_results = [_make_result("id1", dense_score=0.9)]
        keyword_results = [_make_result("id1", keyword_score=0.7)]

        results_default = retriever._fuse_results(
            dense_results=dense_results,
            keyword_results=keyword_results,
            limit=5,
            score_threshold=None,
            dense_weight=1.0,
            keyword_weight=0.8,
        )

        results_custom = retriever._fuse_results(
            dense_results=dense_results,
            keyword_results=keyword_results,
            limit=5,
            score_threshold=None,
            dense_weight=0.5,
            keyword_weight=1.5,
        )

        # Custom weights should produce different fused scores
        assert results_default[0].score != results_custom[0].score


class TestHybridRetrievalFlow:
    """Test hybrid retrieval execution flow."""

    @pytest.mark.asyncio
    async def test_hybrid_mode_runs_both_branches(self):
        """Test that hybrid mode runs both dense and keyword branches."""
        mock_embedding = AsyncMock()
        mock_vector = AsyncMock()
        mock_session = MagicMock()
        mock_session.execute = AsyncMock()

        retriever = RagRetriever(
            session=mock_session,
            embedding_client=mock_embedding,
            vector_service=mock_vector,
        )

        # Mock successful embeddings and searches
        mock_embedding.embed = AsyncMock(return_value=MagicMock(embedding=[0.1] * 1536))
        mock_vector.search = AsyncMock(return_value=[{"id": "id1", "score": 0.9}])

        # Mock DB result for _fetch_and_rank
        mock_result = MagicMock()
        mock_item = MagicMock()
        mock_item.id = "id1"
        mock_item.title = "Title id1"
        mock_item.content = "Content id1"
        mock_item.kind = "note"
        mock_item.tags = []
        mock_result.scalars().all.return_value = [mock_item]
        mock_session.execute.return_value = mock_result

        with patch.object(retriever, '_fts_search', new_callable=AsyncMock, return_value=[_make_result("id1", keyword_score=0.5)]):
            with patch.object(retriever, '_ilike_search', new_callable=AsyncMock, return_value=[]):
                results = await retriever.retrieve(
                    query="test query",
                    limit=5,
                    hybrid=True,
                )

                # Should have results from fusion
                assert len(results) >= 1

    @pytest.mark.asyncio
    async def test_non_hybrid_mode_skips_keyword(self):
        """Test that hybrid=False uses dense-only path."""
        mock_embedding = AsyncMock()
        mock_vector = AsyncMock()
        mock_session = MagicMock()
        mock_session.execute = AsyncMock()

        retriever = RagRetriever(
            session=mock_session,
            embedding_client=mock_embedding,
            vector_service=mock_vector,
        )

        mock_embedding.embed = AsyncMock(return_value=MagicMock(embedding=[0.1] * 1536))
        mock_vector.search = AsyncMock(return_value=[{"id": "id1", "score": 0.9}])

        # Mock DB result for _fetch_and_rank
        mock_result = MagicMock()
        mock_item = MagicMock()
        mock_item.id = "id1"
        mock_item.title = "Title id1"
        mock_item.content = "Content id1"
        mock_item.kind = "note"
        mock_item.tags = []
        mock_result.scalars().all.return_value = [mock_item]
        mock_session.execute.return_value = mock_result

        results = await retriever.retrieve(
            query="test query",
            limit=5,
            hybrid=False,
        )

        # Should use dense-only path
        assert len(results) >= 1
        assert results[0].dense_score is not None
        assert results[0].keyword_score is None


class TestBranchFailureIsolation:
    """Test that branch failures don't affect the other branch."""

    @pytest.mark.asyncio
    async def test_vector_search_failure_returns_keyword_results(self):
        """Test that vector search failure doesn't prevent keyword results."""
        mock_embedding = AsyncMock()
        mock_vector = AsyncMock()
        mock_session = MagicMock()

        retriever = RagRetriever(
            session=mock_session,
            embedding_client=mock_embedding,
            vector_service=mock_vector,
        )

        # Mock embedding success but vector search failure
        mock_embedding.embed = AsyncMock(return_value=MagicMock(embedding=[0.1] * 1536))
        mock_vector.search = AsyncMock(side_effect=Exception("Qdrant unavailable"))

        with patch.object(retriever, '_fts_search', new_callable=AsyncMock, return_value=[_make_result("id1", keyword_score=0.5)]):
            with patch.object(retriever, '_ilike_search', new_callable=AsyncMock, return_value=[]):
                results = await retriever.retrieve(
                    query="test query",
                    limit=5,
                    hybrid=True,
                )

                # Should still get keyword results
                assert len(results) >= 1
                assert results[0].keyword_score is not None

    @pytest.mark.asyncio
    async def test_keyword_search_failure_returns_dense_results(self):
        """Test that keyword search failure doesn't prevent dense results."""
        mock_embedding = AsyncMock()
        mock_vector = AsyncMock()
        mock_session = MagicMock()
        mock_session.execute = AsyncMock()

        retriever = RagRetriever(
            session=mock_session,
            embedding_client=mock_embedding,
            vector_service=mock_vector,
        )

        mock_embedding.embed = AsyncMock(return_value=MagicMock(embedding=[0.1] * 1536))
        mock_vector.search = AsyncMock(return_value=[{"id": "id1", "score": 0.9}])

        # Mock DB result for _fetch_and_rank
        mock_result = MagicMock()
        mock_item = MagicMock()
        mock_item.id = "id1"
        mock_item.title = "Title id1"
        mock_item.content = "Content id1"
        mock_item.kind = "note"
        mock_item.tags = []
        mock_result.scalars().all.return_value = [mock_item]
        mock_session.execute.return_value = mock_result

        # Mock FTS failure
        with patch.object(retriever, '_fts_search', new_callable=AsyncMock, side_effect=Exception("FTS unavailable")):
            with patch.object(retriever, '_ilike_search', new_callable=AsyncMock, return_value=[]):
                results = await retriever.retrieve(
                    query="test query",
                    limit=5,
                    hybrid=True,
                )

                # Should still get dense results
                assert len(results) >= 1
                assert results[0].dense_score is not None

    @pytest.mark.asyncio
    async def test_both_branches_fail_returns_empty(self):
        """Test that if both branches fail, empty list is returned."""
        mock_embedding = AsyncMock()
        mock_vector = AsyncMock()
        mock_session = MagicMock()

        retriever = RagRetriever(
            session=mock_session,
            embedding_client=mock_embedding,
            vector_service=mock_vector,
        )

        # Mock both branches failing
        mock_embedding.embed = AsyncMock(side_effect=Exception("Embedding failed"))
        mock_vector.search = AsyncMock(side_effect=Exception("Vector search failed"))

        with patch.object(retriever, '_fts_search', new_callable=AsyncMock, side_effect=Exception("FTS failed")):
            with patch.object(retriever, '_ilike_search', new_callable=AsyncMock, side_effect=Exception("ILIKE failed")):
                results = await retriever.retrieve(
                    query="test query",
                    limit=5,
                    hybrid=True,
                )

                # Should return empty list
                assert results == []
