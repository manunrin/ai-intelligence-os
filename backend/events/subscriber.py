"""Audit log subscriber — persists AuditLogEvent to the database."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from ..events.event import AuditAction, AuditLogEvent
from ..repositories.audit_repository import AuditRepository

logger = logging.getLogger(__name__)


class AuditLogSubscriber:
    """Listens for AuditLogEvent and persists records to audit_logs table.

    Failure to persist is logged but never re-raised — audit logging must not
    break primary business operations.
    """

    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    async def handle(self, event: AuditLogEvent) -> None:
        if event.action == AuditAction.CREATE:
            resource_type = "article"
            resource_id = event.metadata.get("resource_id") if event.metadata else None
        elif event.action == AuditAction.UPDATE:
            resource_type = event.resource_type or "unknown"
            resource_id = event.resource_id
        elif event.action == AuditAction.DELETE:
            resource_type = event.resource_type or "unknown"
            resource_id = event.resource_id
        elif event.action == AuditAction.AGENT_RUN:
            resource_type = "agent_run"
            resource_id = event.metadata.get("run_id") if event.metadata else None
        elif event.action == AuditAction.LOGIN:
            resource_type = "auth"
            resource_id = event.user_id
        else:
            resource_type = event.resource_type or "unknown"
            resource_id = event.resource_id

        try:
            # Validate resource_id is a valid UUID before storing
            resource_id_uuid = None
            if resource_id:
                try:
                    resource_id_uuid = uuid.UUID(resource_id)
                except (ValueError, AttributeError):
                    resource_id_uuid = None

            session = self._session_factory()
            repo = AuditRepository(session)
            await repo.create(
                user_id=event.user_id,
                action=event.action.value if isinstance(event.action, AuditAction) else event.action,
                resource_type=resource_type,
                resource_id=resource_id_uuid,
                metadata_=event.metadata,
                ip_address=event.ip_address,
                user_agent=event.user_agent,
                created_at=event.occurred_at,
            )
            await session.commit()
            await session.close()
        except Exception:
            logger.error(
                "Failed to persist audit log for %s %s",
                event.action,
                resource_type,
                exc_info=True,
            )
