"""Admin audit log query endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query

from ..schemas.audit import AuditLogResponse, AuditStatsResponse
from ..schemas.response import APIResponse
from .deps import get_db, require_role

router = APIRouter(
    prefix="/admin/audit-logs",
    tags=["admin audit"],
)


@router.get(
    "",
    summary="List audit logs",
    description="Admin-only endpoint to browse audit log entries with filtering.",
    operation_id="listAuditLogs",
    response_model=APIResponse[list[AuditLogResponse]],
)
async def list_audit_logs(
    action: str | None = Query(default=None, description="Filter by action type"),
    resource_type: str | None = Query(default=None, description="Filter by resource type"),
    user_id: str | None = Query(default=None, description="Filter by user ID"),
    resource_id: str | None = Query(default=None, description="Filter by resource ID"),
    start_date: str | None = Query(default=None, description="Filter from timestamp (ISO 8601)"),
    end_date: str | None = Query(default=None, description="Filter to timestamp (ISO 8601)"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user=Depends(require_role("admin")),
    db=Depends(get_db),
):
    from ..repositories.audit_repository import AuditRepository

    repo = AuditRepository(db)

    parsed_user_id = uuid.UUID(user_id) if user_id else None
    parsed_resource_id = uuid.UUID(resource_id) if resource_id else None
    parsed_start = datetime.fromisoformat(start_date) if start_date else None
    parsed_end = datetime.fromisoformat(end_date) if end_date else None

    logs = await repo.query_logs(
        action=action,
        resource_type=resource_type,
        user_id=parsed_user_id,
        resource_id=parsed_resource_id,
        start_date=parsed_start,
        end_date=parsed_end,
        offset=offset,
        limit=limit,
    )
    return APIResponse(
        success=True,
        data=[
            AuditLogResponse(
                id=str(log.id),
                action=log.action,
                resource_type=log.resource_type,
                resource_id=str(log.resource_id) if log.resource_id else None,
                user_id=str(log.user_id) if log.user_id else None,
                ip_address=log.ip_address,
                user_agent=log.user_agent,
                metadata=log.metadata_,
                created_at=log.created_at,
            )
            for log in logs
        ],
        error=None,
    )


@router.get(
    "/stats",
    summary="Audit statistics",
    description="Admin-only endpoint returning aggregated audit statistics.",
    operation_id="getAuditStats",
    response_model=APIResponse[AuditStatsResponse],
)
async def audit_stats(
    period: str = Query(default="7d", description="Period: 24h, 7d, 30d, 90d"),
    current_user=Depends(require_role("admin")),
    db=Depends(get_db),
):
    from ..repositories.audit_repository import AuditRepository

    days_map = {"24h": 1, "7d": 7, "30d": 30, "90d": 90}
    days = days_map.get(period, 7)

    repo = AuditRepository(db)
    action_counts = await repo.action_counts(days=days)
    daily_trend = await repo.daily_trend(days=days)

    return APIResponse(
        success=True,
        data=AuditStatsResponse(
            action_counts=action_counts,
            top_users=[],
            daily_trend=daily_trend,
        ),
        error=None,
    )
