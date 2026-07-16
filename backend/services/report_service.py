"""Report business logic service."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..repositories.report_repository import IntelligenceReportRepository


class ReportService:
    """Business logic for report operations."""

    def __init__(self, session: AsyncSession) -> None:
        self._repo = IntelligenceReportRepository(session)

    async def list_reports(self, offset: int = 0, limit: int = 20) -> list[dict[str, Any]]:
        """Return paginated reports as dicts for response serialization."""
        reports = await self._repo.list_all(offset=offset, limit=limit)
        return [self._to_dict(r) for r in reports]

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
