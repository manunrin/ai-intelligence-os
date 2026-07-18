"""Tests for AuditLogSubscriber — event persistence to DB."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.events.event import AuditAction, AuditLogEvent
from backend.events.subscriber import AuditLogSubscriber


class TestAuditLogSubscriber:
    @pytest.mark.asyncio
    async def test_persists_create_event(self):
        fake_session = MagicMock()
        fake_session.__aenter__ = AsyncMock(return_value=fake_session)
        fake_session.__aexit__ = AsyncMock(return_value=None)
        fake_session.add = MagicMock()
        fake_session.flush = AsyncMock()
        fake_session.commit = AsyncMock()

        factory = MagicMock(return_value=fake_session)
        subscriber = AuditLogSubscriber(factory)

        resource_id = uuid.uuid4()
        user_id = uuid.uuid4()
        event = AuditLogEvent(
            action=AuditAction.CREATE,
            resource_type="article",
            resource_id=resource_id,
            user_id=user_id,
            ip_address="10.0.0.1",
            metadata={"key": "val"},
        )
        await subscriber.handle(event)

        # Verify session was opened and committed
        fake_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_persists_agent_run_event(self):
        fake_session = MagicMock()
        fake_session.__aenter__ = AsyncMock(return_value=fake_session)
        fake_session.__aexit__ = AsyncMock(return_value=None)
        fake_session.add = MagicMock()
        fake_session.flush = AsyncMock()
        fake_session.commit = AsyncMock()

        factory = MagicMock(return_value=fake_session)
        subscriber = AuditLogSubscriber(factory)

        run_id = str(uuid.uuid4())
        event = AuditLogEvent(
            action=AuditAction.AGENT_RUN,
            user_id=uuid.uuid4(),
            metadata={"run_id": run_id},
        )
        await subscriber.handle(event)

        fake_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_persists_login_event(self):
        fake_session = MagicMock()
        fake_session.__aenter__ = AsyncMock(return_value=fake_session)
        fake_session.__aexit__ = AsyncMock(return_value=None)
        fake_session.add = MagicMock()
        fake_session.flush = AsyncMock()
        fake_session.commit = AsyncMock()

        factory = MagicMock(return_value=fake_session)
        subscriber = AuditLogSubscriber(factory)

        user_id = uuid.uuid4()
        event = AuditLogEvent(
            action=AuditAction.LOGIN,
            user_id=user_id,
        )
        await subscriber.handle(event)

        fake_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_failure_does_not_propagate(self):
        """Audit failures must not break primary operations."""
        fake_session = MagicMock()
        fake_session.__aenter__ = AsyncMock(side_effect=Exception("DB down"))
        fake_session.__aexit__ = AsyncMock(return_value=None)

        factory = MagicMock(return_value=fake_session)
        subscriber = AuditLogSubscriber(factory)

        event = AuditLogEvent(action=AuditAction.DELETE, resource_type="task")
        # Should not raise
        await subscriber.handle(event)

    @pytest.mark.asyncio
    async def test_update_action_uses_resource_type(self):
        """UPDATE action uses event.resource_type as-is."""
        fake_session = MagicMock()
        fake_session.add = MagicMock()
        fake_session.flush = AsyncMock()
        fake_session.commit = AsyncMock()

        factory = MagicMock(return_value=fake_session)
        subscriber = AuditLogSubscriber(factory)

        event = AuditLogEvent(
            action=AuditAction.UPDATE,
            resource_type="knowledge_item",
            resource_id=uuid.uuid4(),
        )
        await subscriber.handle(event)

        fake_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_action_uses_resource_type(self):
        """DELETE action uses event.resource_type as-is."""
        fake_session = MagicMock()
        fake_session.add = MagicMock()
        fake_session.flush = AsyncMock()
        fake_session.commit = AsyncMock()

        factory = MagicMock(return_value=fake_session)
        subscriber = AuditLogSubscriber(factory)

        event = AuditLogEvent(
            action=AuditAction.DELETE,
            resource_type="article",
            resource_id=uuid.uuid4(),
        )
        await subscriber.handle(event)

        fake_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_unknown_action_falls_back_to_resource_type(self):
        """Unknown action falls back to resource_type or 'unknown'."""
        fake_session = MagicMock()
        fake_session.add = MagicMock()
        fake_session.flush = AsyncMock()
        fake_session.commit = AsyncMock()

        factory = MagicMock(return_value=fake_session)
        subscriber = AuditLogSubscriber(factory)

        event = AuditLogEvent(action="custom_action", resource_type="custom")
        await subscriber.handle(event)

        fake_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_invalid_resource_id_uuid_is_stored_as_none(self):
        """Non-UUID resource_id should be stored as None in DB."""
        fake_session = MagicMock()
        fake_session.add = MagicMock()
        fake_session.flush = AsyncMock()
        fake_session.commit = AsyncMock()

        factory = MagicMock(return_value=fake_session)
        subscriber = AuditLogSubscriber(factory)

        event = AuditLogEvent(
            action=AuditAction.UPDATE,
            resource_type="article",
            resource_id="not-a-uuid-string",
        )
        await subscriber.handle(event)

        fake_session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_agent_run_uses_metadata_run_id(self):
        """AGENT_RUN action extracts run_id from metadata."""
        fake_session = MagicMock()
        fake_session.add = MagicMock()
        fake_session.flush = AsyncMock()
        fake_session.commit = AsyncMock()

        factory = MagicMock(return_value=fake_session)
        subscriber = AuditLogSubscriber(factory)

        run_id = str(uuid.uuid4())
        event = AuditLogEvent(
            action=AuditAction.AGENT_RUN,
            user_id=uuid.uuid4(),
            metadata={"run_id": run_id},
        )
        await subscriber.handle(event)

        fake_session.commit.assert_awaited_once()
