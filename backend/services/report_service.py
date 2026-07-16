"""Report business logic service."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..repositories.report_repository import IntelligenceReportRepository
from ..schemas.report_create import ReportCreate, ReportUpdate


class ReportService:
    """Business logic for report operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._repo = IntelligenceReportRepository(session)

    async def list_reports(self, offset: int = 0, limit: int = 20) -> list[dict[str, Any]]:
        """Return paginated reports as dicts for response serialization."""
        reports = await self._repo.list_all(offset=offset, limit=limit)
        return [self._to_dict(r) for r in reports]

    async def get_report(self, report_id: str) -> dict[str, Any] | None:
        """Return a single report by ID, or None if not found."""
        report = await self._repo.get_by_id(uuid.UUID(report_id))
        if report is None:
            return None
        return self._to_dict(report)

    async def create_report(self, data: ReportCreate) -> dict[str, Any]:
        """Create and persist a new report from validated schema data."""
        article_ids = [uuid.UUID(aid) for aid in data.article_ids] if data.article_ids else []
        kwargs: dict[str, Any] = {
            "title": data.title,
            "body": data.body,
            "category": data.category,
            "importance_score": data.importance_score,
            "article_ids": article_ids,
            "agent_run_id": uuid.UUID(data.agent_run_id) if data.agent_run_id else None,
            "generated_by": data.generated_by,
            "created_at": datetime.now(timezone.utc),
        }
        report = await self._repo.create(**kwargs)
        return self._to_dict(report)

    async def update_report(self, report_id: str, data: ReportUpdate) -> dict[str, Any] | None:
        """Update an existing report. Returns None if not found."""
        existing = await self._repo.get_by_id(uuid.UUID(report_id))
        if existing is None:
            return None
        update_data = data.model_dump(exclude_unset=True)
        if "article_ids" in update_data and update_data["article_ids"] is not None:
            update_data["article_ids"] = [uuid.UUID(aid) for aid in update_data["article_ids"]]
        updated = await self._repo.update(uuid.UUID(report_id), **update_data)
        return self._to_dict(updated)

    @staticmethod
    def _to_dict(report: Any) -> dict[str, Any]:
        """Convert ORM model to serializable dict."""
        return {
            "id": str(report.id),
            "topic": report.title,
            "research_result": None,
            "analysis_result": None,
            "translation_result": None,
            "knowledge_items": [],
            "tasks": [],
            "created_at": report.created_at.isoformat() if report.created_at else None,
        }
