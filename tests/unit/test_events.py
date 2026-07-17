"""Tests for AuditLogEvent and AuditAction."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from backend.events.event import AuditAction, AuditLogEvent


class TestAuditAction:
    def test_create_value(self):
        assert AuditAction.CREATE.value == "create"

    def test_update_value(self):
        assert AuditAction.UPDATE.value == "update"

    def test_delete_value(self):
        assert AuditAction.DELETE.value == "delete"

    def test_agent_run_value(self):
        assert AuditAction.AGENT_RUN.value == "agent_run"

    def test_login_value(self):
        assert AuditAction.LOGIN.value == "login"


class TestAuditLogEvent:
    def test_default_action_is_create(self):
        event = AuditLogEvent()
        assert event.action == AuditAction.CREATE

    def test_source_property(self):
        event = AuditLogEvent(action=AuditAction.CREATE)
        assert event.source == "audit"

    def test_all_fields_set(self):
        user_id = uuid.uuid4()
        resource_id = uuid.uuid4()
        event = AuditLogEvent(
            action=AuditAction.UPDATE,
            resource_type="article",
            resource_id=resource_id,
            user_id=user_id,
            ip_address="192.168.1.1",
            user_agent="TestBrowser/1.0",
            metadata={"key": "value"},
        )
        assert event.action == AuditAction.UPDATE
        assert event.resource_type == "article"
        assert event.resource_id == resource_id
        assert event.user_id == user_id
        assert event.ip_address == "192.168.1.1"
        assert event.user_agent == "TestBrowser/1.0"
        assert event.metadata == {"key": "value"}

    def test_event_id_is_uuid(self):
        event = AuditLogEvent()
        assert isinstance(event.event_id, uuid.UUID)

    def test_occurred_at_is_utc(self):
        event = AuditLogEvent()
        assert event.occurred_at.tzinfo is not None
