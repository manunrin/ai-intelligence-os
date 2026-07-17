"""Audit log repository — persistence and admin queries."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.models.audit_log import AuditLog


class AuditRepository:
    """Data access for audit log records."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, **kwargs: Any) -> AuditLog:
        instance = AuditLog(**kwargs)
        self._session.add(instance)
        await self._session.flush()
        return instance

    async def query_logs(
        self,
        *,
        action: str | None = None,
        resource_type: str | None = None,
        user_id: uuid.UUID | None = None,
        resource_id: uuid.UUID | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> list[AuditLog]:
        stmt = select(AuditLog)
        if action is not None:
            stmt = stmt.where(AuditLog.action == action)
        if resource_type is not None:
            stmt = stmt.where(AuditLog.resource_type == resource_type)
        if user_id is not None:
            stmt = stmt.where(AuditLog.user_id == user_id)
        if resource_id is not None:
            stmt = stmt.where(AuditLog.resource_id == resource_id)
        if start_date is not None:
            stmt = stmt.where(AuditLog.created_at >= start_date)
        if end_date is not None:
            stmt = stmt.where(AuditLog.created_at <= end_date)
        stmt = stmt.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def action_counts(self, days: int = 7) -> dict[str, int]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        stmt = (
            select(AuditLog.action, func.count().cast("integer"))
            .where(AuditLog.created_at >= cutoff)
            .group_by(AuditLog.action)
        )
        result = await self._session.execute(stmt)
        return {row[0]: row[1] for row in result.all()}

    async def daily_trend(self, days: int = 7) -> list[dict[str, Any]]:
        from sqlalchemy import cast, column, extract, func as sql_func

        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        stmt = (
            select(
                sql_func.date(AuditLog.created_at).label("day"),
                sql_func.count().cast(column("integer")).label("cnt"),
            )
            .where(AuditLog.created_at >= cutoff)
            .group_by(sql_func.date(AuditLog.created_at))
            .order_by(sql_func.date(AuditLog.created_at).asc())
        )
        result = await self._session.execute(stmt)
        return [{"date": row.day.isoformat(), "count": row.cnt} for row in result.all()]
