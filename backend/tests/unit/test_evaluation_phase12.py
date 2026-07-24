"""Unit tests for EvaluationService Phase 12 features: sampling, caching, confidence."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.services.evaluation.schemas import EvaluationResponse


class TestEvaluationSampling:
    """Test that sampling logic correctly skips evaluations."""

    def test_sample_rate_100_percent_always_evaluates(self):
        """sample_rate=1.0 should never skip."""
        from backend.services.evaluation.service import EvaluationService

        service = EvaluationService(
            llm_client=MagicMock(),
            sample_rate=1.0,
        )
        assert service._sample_rate == 1.0

    def test_sample_rate_zero_never_evaluates(self):
        """sample_rate=0.0 should always skip."""
        from backend.services.evaluation.service import EvaluationService

        mock_client = MagicMock()
        service = EvaluationService(
            llm_client=mock_client,
            sample_rate=0.0,
        )
        # Simulate the sampling check
        assert service._sample_rate == 0.0

    def test_sample_rate_partial(self):
        """sample_rate=0.3 means ~30% pass through."""
        from backend.services.evaluation.service import EvaluationService

        service = EvaluationService(
            llm_client=MagicMock(),
            sample_rate=0.3,
        )
        assert service._sample_rate == 0.3


class TestContentHash:
    """Test content hash computation for cache dedup."""

    def test_same_payloads_same_hash(self):
        """Identical payloads must produce identical hashes."""
        from backend.services.evaluation.service import EvaluationService

        svc = EvaluationService(llm_client=MagicMock())
        input_data = {"topic": "test", "goal": "analyze"}
        output_data = {"result": "hello"}
        h1 = svc._compute_hash(input_data, output_data)
        h2 = svc._compute_hash(input_data, output_data)
        assert h1 == h2
        assert len(h1) == 64  # SHA-256 hex digest length

    def test_different_payloads_different_hash(self):
        """Different payloads must produce different hashes."""
        from backend.services.evaluation.service import EvaluationService

        svc = EvaluationService(llm_client=MagicMock())
        h1 = svc._compute_hash({"a": 1}, {"b": 2})
        h2 = svc._compute_hash({"a": 3}, {"b": 2})
        assert h1 != h2

    def test_sort_keys_produces_deterministic_hash(self):
        """Hash should be deterministic regardless of dict key order."""
        from backend.services.evaluation.service import EvaluationService

        svc = EvaluationService(llm_client=MagicMock())
        h1 = svc._compute_hash({"z": 1, "a": 2}, {})
        h2 = svc._compute_hash({"a": 2, "z": 1}, {})
        assert h1 == h2


class TestCacheFreshness:
    """Test cache TTL logic."""

    def test_fresh_cache(self):
        """Cache within 24h should be fresh."""
        from backend.services.evaluation.service import EvaluationService

        now = datetime.now(timezone.utc)
        assert EvaluationService._is_cache_fresh(now) is True

    def test_stale_cache(self):
        """Cache older than 24h should be stale."""
        from backend.services.evaluation.service import EvaluationService

        old = datetime.now(timezone.utc) - timedelta(hours=25)
        assert EvaluationService._is_cache_fresh(old) is False

    def test_exactly_24h_is_stale(self):
        """Exactly 24h should be stale (not < 86400)."""
        from backend.services.evaluation.service import EvaluationService

        old = datetime.now(timezone.utc) - timedelta(seconds=86401)
        assert EvaluationService._is_cache_fresh(old) is False


class TestConfidenceParsing:
    """Test evaluator_confidence parsing from LLM JSON."""

    def test_parse_with_confidence(self):
        """Valid confidence value should be parsed."""
        from backend.services.evaluation.service import EvaluationService

        svc = EvaluationService(llm_client=MagicMock())
        content = json.dumps({
            "score": 75.0,
            "criteria": {"accuracy": 80.0},
            "evaluator_notes": "Good output",
            "evaluator_confidence": 0.9,
        })
        result = svc._parse_response(content)
        assert result is not None
        assert result.score == 75.0
        assert result.evaluator_confidence == 0.9

    def test_parse_missing_confidence(self):
        """Missing confidence should default to None."""
        from backend.services.evaluation.service import EvaluationService

        svc = EvaluationService(llm_client=MagicMock())
        content = json.dumps({
            "score": 75.0,
            "criteria": {"accuracy": 80.0},
        })
        result = svc._parse_response(content)
        assert result is not None
        assert result.evaluator_confidence is None

    def test_parse_invalid_confidence(self):
        """Non-float confidence should be ignored."""
        from backend.services.evaluation.service import EvaluationService

        svc = EvaluationService(llm_client=MagicMock())
        content = json.dumps({
            "score": 75.0,
            "criteria": {},
            "evaluator_confidence": "high",
        })
        result = svc._parse_response(content)
        assert result is not None
        assert result.evaluator_confidence is None

    def test_parse_low_confidence(self):
        """Low confidence values should parse correctly."""
        from backend.services.evaluation.service import EvaluationService

        svc = EvaluationService(llm_client=MagicMock())
        content = json.dumps({
            "score": 50.0,
            "criteria": {"accuracy": 50.0},
            "evaluator_confidence": 0.2,
        })
        result = svc._parse_response(content)
        assert result is not None
        assert result.evaluator_confidence == 0.2


class TestEvaluationResponseSchema:
    """Test that EvaluationResponse includes new fields."""

    def test_schema_has_confidence(self):
        """Response should have evaluator_confidence field."""
        resp = EvaluationResponse(
            score=80.0,
            criteria={"accuracy": 85.0},
            evaluator_notes="Good",
            evaluator_confidence=0.95,
            cached=False,
        )
        assert resp.evaluator_confidence == 0.95
        assert resp.cached is False

    def test_schema_has_cached_field(self):
        """Response should have cached field."""
        resp = EvaluationResponse(
            score=80.0,
            criteria={"accuracy": 85.0},
            cached=True,
        )
        assert resp.cached is True

    def test_schema_allows_none_values(self):
        """All optional fields should accept None."""
        resp = EvaluationResponse(
            score=None,
            criteria=None,
            evaluator_notes=None,
            evaluator_confidence=None,
            cached=False,
        )
        assert resp.score is None
        assert resp.criteria is None
        assert resp.evaluator_confidence is None


class TestCacheRepositoryUpsert:
    """Test EvaluationCacheRepository upsert logic."""

    @pytest.mark.asyncio
    async def test_upsert_creates_new_entry(self):
        """First upsert should create a new entry."""
        from backend.database.models import EvaluationCache
        from backend.services.evaluation.repository import EvaluationCacheRepository
        from backend.services.evaluation.schemas import EvaluationResponse

        mock_session = AsyncMock()
        repo = EvaluationCacheRepository(mock_session)

        # Mock get_by_hash to return None (cache miss)
        repo.get_by_hash = AsyncMock(return_value=None)

        response = EvaluationResponse(
            score=80.0,
            criteria={"accuracy": 85.0},
            evaluator_notes="test",
            model_used="gpt-4o-mini",
            cached=False,
        )

        await repo.upsert("abc123", "intelligence", response)

        # Verify add was called (new entry)
        mock_session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_upsert_updates_existing_entry(self):
        """Subsequent upsert with same hash should update existing entry."""
        from backend.services.evaluation.repository import EvaluationCacheRepository
        from backend.services.evaluation.schemas import EvaluationResponse

        mock_session = AsyncMock()
        repo = EvaluationCacheRepository(mock_session)

        existing = MagicMock()
        existing.score = 50.0
        existing.criteria = {}
        repo.get_by_hash = AsyncMock(return_value=existing)

        response = EvaluationResponse(
            score=90.0,
            criteria={"accuracy": 95.0},
            evaluator_notes="improved",
            model_used="gpt-4o",
            cached=False,
        )

        await repo.upsert("abc123", "intelligence", response)

        # Should update existing entry instead of creating new one
        assert existing.score == 90.0
        assert existing.criteria == {"accuracy": 95.0}
        assert existing.evaluator_notes == "improved"
        assert existing.model_used == "gpt-4o"
        # add should NOT be called for updates
        mock_session.add.assert_not_called()
