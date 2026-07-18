"""Tests for the API response schema models."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from backend.schemas.agent_run import AgentRunResponse
from backend.schemas.article import ArticleResponse
from backend.schemas.error import ErrorResponse
from backend.schemas.knowledge import KnowledgeItemResponse
from backend.schemas.report import IntelligenceReportResponse
from backend.schemas.response import APIResponse
from backend.schemas.task import TaskResponse


# ------------------------------------------------------------------
#  APIResponse envelope
# ------------------------------------------------------------------

class TestAPIResponse:
    def test_success_with_data(self) -> None:
        resp = APIResponse(success=True, data=[1, 2], error=None)
        assert resp.success is True
        assert resp.data == [1, 2]
        assert resp.error is None

    def test_error_without_data(self) -> None:
        resp = APIResponse(success=False, data=None, error=ErrorResponse(code="UNKNOWN", message="bad"))
        assert resp.success is False
        assert resp.error is not None
        assert resp.error.message == "bad"


# ------------------------------------------------------------------
#  ArticleResponse
# ------------------------------------------------------------------

class TestArticleResponse:
    def test_from_str_id(self) -> None:
        fake_id = str(uuid4())
        now = datetime.now(timezone.utc)
        article = {
            "id": fake_id,
            "title": "Test",
            "summary": "Summary",
            "content": "Content",
            "url": "http://example.com",
            "source": "rss",
            "language": "en",
            "tags": ["a", "b"],
            "status": "raw",
            "fetched_at": now.isoformat(),
            "published_at": now.isoformat(),
        }
        resp = ArticleResponse.model_validate(article)
        assert resp.id == fake_id
        assert resp.title == "Test"
        assert resp.status == "raw"

    def test_all_fields_serializable(self) -> None:
        article = {
            "id": str(uuid4()),
            "title": "T",
            "summary": None,
            "content": None,
            "url": None,
            "source": "manual",
            "language": "zh-CN",
            "tags": [],
            "status": "analyzed",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "published_at": None,
        }
        data = ArticleResponse.model_validate(article).model_dump(mode="json")
        assert "id" in data
        assert "published_at" in data  # may be null


# ------------------------------------------------------------------
#  KnowledgeItemResponse
# ------------------------------------------------------------------

class TestKnowledgeItemResponse:
    def test_from_dict(self) -> None:
        item = {
            "id": str(uuid4()),
            "title": "KI Title",
            "content": "KI Content",
            "kind": "research",
            "article_id": str(uuid4()),
            "tags": ["tag1"],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        resp = KnowledgeItemResponse.model_validate(item)
        assert resp.kind == "research"
        assert resp.tags == ["tag1"]

    @pytest.mark.parametrize("kind", ["article", "research", "analysis", "translation"])
    def test_valid_kinds(self, kind: str) -> None:
        item = {
            "id": str(uuid4()),
            "title": "T",
            "content": "C",
            "kind": kind,
            "tags": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        resp = KnowledgeItemResponse.model_validate(item)
        assert resp.kind == kind


# ------------------------------------------------------------------
#  TaskResponse
# ------------------------------------------------------------------

class TestTaskResponse:
    def test_defaults(self) -> None:
        task = {
            "id": str(uuid4()),
            "title": "Do thing",
            "description": "Desc",
            "priority": "high",
            "status": "todo",
            "dependency": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        resp = TaskResponse.model_validate(task)
        assert resp.priority == "high"
        assert resp.status == "todo"


# ------------------------------------------------------------------
#  AgentRunResponse
# ------------------------------------------------------------------

class TestAgentRunResponse:
    def test_full(self) -> None:
        run = {
            "id": str(uuid4()),
            "agent_id": str(uuid4()),
            "workflow_id": str(uuid4()),
            "status": "completed",
            "input_payload": {"key": "val"},
            "output_payload": {"result": "ok"},
            "error_message": None,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "finished_at": datetime.now(timezone.utc).isoformat(),
        }
        resp = AgentRunResponse.model_validate(run)
        assert resp.status == "completed"


# ------------------------------------------------------------------
#  IntelligenceReportResponse
# ------------------------------------------------------------------

class TestIntelligenceReportResponse:
    def test_full(self) -> None:
        report = {
            "id": str(uuid4()),
            "topic": "AI Report",
            "research_result": {},
            "analysis_result": {},
            "translation_result": {},
            "knowledge_items": [],
            "tasks": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        resp = IntelligenceReportResponse.model_validate(report)
        assert resp.topic == "AI Report"
