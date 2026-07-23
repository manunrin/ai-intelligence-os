"""Tests for the evaluation service package."""

from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.services.evaluation.criteria import get_criteria, get_threshold
from backend.services.evaluation.prompts import (
    build_autonomous_prompt,
    build_intelligence_prompt,
)
from backend.services.evaluation.schemas import EvaluationRequest, EvaluationResponse
from backend.services.evaluation.service import EvaluationService


class TestCriteria:
    def test_returns_four_criteria(self):
        criteria = get_criteria()
        assert len(criteria) == 4
        assert criteria == ["accuracy", "relevance", "actionability", "completeness"]

    def test_default_threshold(self):
        assert get_threshold() == 0.6


class TestSchemas:
    def test_evaluation_response_with_all_fields(self):
        resp = EvaluationResponse(
            score=85.0,
            criteria={"accuracy": 90.0, "relevance": 80.0},
            evaluator_notes="Good output",
        )
        assert resp.score == 85.0
        assert resp.criteria["accuracy"] == 90.0
        assert resp.evaluator_notes == "Good output"

    def test_evaluation_response_defaults(self):
        resp = EvaluationResponse()
        assert resp.score is None
        assert resp.criteria is None
        assert resp.evaluator_notes is None

    def test_evaluation_request(self):
        req = EvaluationRequest(
            pipeline_type="intelligence",
            output_payload={"result": "data"},
            input_payload={"topic": "test"},
        )
        assert req.pipeline_type == "intelligence"


class TestPrompts:
    def test_build_intelligence_prompt(self):
        msgs = build_intelligence_prompt(
            {"topic": "AI trends", "query": "latest"},
            {"summary": "AI is growing fast.", "sources": 5},
        )
        assert len(msgs) == 1
        assert msgs[0]["role"] == "system"
        assert "AI trends" in msgs[0]["content"]
        assert "AI is growing fast" in msgs[0]["content"]

    def test_build_autonomous_prompt(self):
        msgs = build_autonomous_prompt(
            {"goal": "research quantum computing"},
            {"findings": "Quantum computing advances rapidly."},
        )
        assert len(msgs) == 1
        assert "quantum computing" in msgs[0]["content"]

    def test_truncates_long_output(self):
        long_payload = {"text": "x" * 20000}
        msgs = build_intelligence_prompt({}, long_payload)
        content = msgs[0]["content"]
        assert "... [truncated]" in content


class TestEvaluationServiceParse:
    @pytest.mark.asyncio
    async def test_parse_valid_json(self):
        svc = EvaluationService(MagicMock())
        response = svc._parse_response(
            json.dumps({
                "score": 85.5,
                "criteria": {"accuracy": 90.0, "relevance": 80.0},
                "evaluator_notes": "Strong output",
            })
        )
        assert response.score == 85.5
        assert response.criteria["accuracy"] == 90.0
        assert response.evaluator_notes == "Strong output"

    @pytest.mark.asyncio
    async def test_parse_integer_score(self):
        svc = EvaluationService(MagicMock())
        response = svc._parse_response(json.dumps({"score": 70}))
        assert response.score == 70.0

    @pytest.mark.asyncio
    async def test_parse_missing_score(self):
        svc = EvaluationService(MagicMock())
        response = svc._parse_response(json.dumps({"criteria": {}}))
        assert response.score is None

    @pytest.mark.asyncio
    async def test_parse_invalid_json(self):
        svc = EvaluationService(MagicMock())
        response = svc._parse_response("not json")
        assert response is None

    @pytest.mark.asyncio
    async def test_parse_none_content(self):
        svc = EvaluationService(MagicMock())
        response = svc._parse_response(None)
        assert response is None


class TestEvaluationServiceEvaluate:
    @pytest.mark.asyncio
    async def test_evaluate_calls_llm_and_parses(self):
        mock_router = MagicMock()
        mock_client = MagicMock()
        mock_client.chat = AsyncMock(
            return_value=MagicMock(content=json.dumps({
                "score": 92.0,
                "criteria": {"accuracy": 95.0, "relevance": 90.0, "actionability": 88.0, "completeness": 93.0},
                "evaluator_notes": "Excellent",
            }))
        )
        mock_client.get_router = MagicMock(return_value=mock_router)

        svc = EvaluationService(mock_client)
        result = await svc.evaluate(
            pipeline_type="intelligence",
            output_payload={"summary": "done"},
            input_payload={"topic": "test"},
        )
        assert result is not None
        assert result.score == 92.0
        assert "accuracy" in result.criteria

    @pytest.mark.asyncio
    async def test_evaluate_unknown_pipeline_returns_none(self):
        mock_client = MagicMock()
        svc = EvaluationService(mock_client)
        result = await svc.evaluate(
            pipeline_type="unknown_pipeline",
            output_payload={},
            input_payload={},
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_evaluate_timeout_returns_none(self):
        mock_client = MagicMock()
        import asyncio

        mock_client.chat = AsyncMock(side_effect=asyncio.TimeoutError())
        svc = EvaluationService(mock_client)
        with patch("backend.services.evaluation.service._TIMEOUT_SECONDS", 0.001):
            result = await svc.evaluate(
                pipeline_type="intelligence",
                output_payload={},
                input_payload={},
            )
        assert result is None

    @pytest.mark.asyncio
    async def test_evaluate_exception_returns_none(self):
        mock_client = MagicMock()
        mock_client.chat = AsyncMock(side_effect=RuntimeError("LLM down"))
        svc = EvaluationService(mock_client)
        result = await svc.evaluate(
            pipeline_type="intelligence",
            output_payload={},
            input_payload={},
        )
        assert result is None
