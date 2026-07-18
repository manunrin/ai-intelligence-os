"""Report business logic service."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..events.event import AuditAction, AuditLogEvent
from ..repositories.report_repository import IntelligenceReportRepository
from ..schemas.report_create import ReportCreate, ReportUpdate

logger = logging.getLogger(__name__)


class ReportService:
    """Business logic for report operations."""

    def __init__(self, session: AsyncSession, event_publisher=None) -> None:
        self._repo = IntelligenceReportRepository(session)
        self._publisher = event_publisher

    async def list_reports(
        self, offset: int = 0, limit: int = 20, user_id: uuid.UUID | None = None
    ) -> list[dict[str, Any]]:
        """Return paginated reports filtered by user_id if provided."""
        if user_id is not None:
            reports = await self._repo.list_by_user(user_id, offset=offset, limit=limit)
        else:
            reports = await self._repo.list_all(offset=offset, limit=limit)
        return [self._to_dict(r) for r in reports]

    async def get_report(
        self, report_id: str, user_id: uuid.UUID | None = None
    ) -> dict[str, Any] | None:
        """Return a single report by ID if owned by user_id, or None."""
        report = await self._repo.get_by_id(uuid.UUID(report_id))
        if report is None or report.user_id != user_id:
            return None
        return self._to_dict(report)

    async def create_report(self, data: ReportCreate, user_id: uuid.UUID) -> dict[str, Any]:
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
            "user_id": user_id,
        }
        report = await self._repo.create(**kwargs)
        await self._publish_audit(AuditAction.CREATE, str(report.id), user_id=user_id)
        return self._to_dict(report)

    async def update_report(
        self, report_id: str, data: ReportUpdate, user_id: uuid.UUID | None = None
    ) -> dict[str, Any] | None:
        """Update an existing report if owned by user_id. Returns None if not found."""
        existing = await self._repo.get_by_id(uuid.UUID(report_id))
        if existing is None or existing.user_id != user_id:
            return None
        update_data = data.model_dump(exclude_unset=True)
        if "article_ids" in update_data and update_data["article_ids"] is not None:
            update_data["article_ids"] = [uuid.UUID(aid) for aid in update_data["article_ids"]]
        updated = await self._repo.update(uuid.UUID(report_id), **update_data)
        if updated is not None:
            await self._publish_audit(AuditAction.UPDATE, report_id, user_id=user_id)
        return self._to_dict(updated)

    @staticmethod
    def _to_dict(report: Any) -> dict[str, Any]:
        """Convert ORM model to serializable dict."""
        return {
            "id": str(report.id),
            "topic": report.title,
            "created_at": report.created_at.isoformat() if report.created_at else None,
            "user_id": str(report.user_id) if report.user_id else None,
        }

    async def _publish_audit(self, action: AuditAction, resource_id: str, *, user_id: uuid.UUID | None = None) -> None:
        if self._publisher is None:
            return
        try:
            from ..context_vars import ip_address as _ip_ctx, user_agent as _ua_ctx
            await self._publisher.publish(AuditLogEvent(
                action=action,
                resource_type="report",
                resource_id=uuid.UUID(resource_id),
                user_id=user_id,
                ip_address=_ip_ctx.get(),
                user_agent=_ua_ctx.get(),
                metadata={"resource_id": resource_id},
            ))
        except Exception:
            logger.error("Failed to publish audit event for %s report %s", action.value, resource_id, exc_info=True)
