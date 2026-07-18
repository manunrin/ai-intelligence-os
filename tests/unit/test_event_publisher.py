"""Tests for EventPublisher — subscribe, publish, handler dispatch."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from backend.events.event import ArticleCreatedEvent, AuditAction, AuditLogEvent, BaseEvent
from backend.events.publisher import EventPublisher


class TestEventPublisherSubscribe:
    def test_subscribe_creates_entry(self):
        pub = EventPublisher()
        pub.subscribe(ArticleCreatedEvent, lambda e: None)
        assert len(pub._subscribers[ArticleCreatedEvent]) == 1

    def test_subscribe_appends_multiple_handlers(self):
        pub = EventPublisher()
        pub.subscribe(ArticleCreatedEvent, lambda e: None)
        pub.subscribe(ArticleCreatedEvent, lambda e: None)
        assert len(pub._subscribers[ArticleCreatedEvent]) == 2


class TestEventPublisherPublish:
    @pytest.mark.asyncio
    async def test_publish_calls_sync_handler(self):
        pub = EventPublisher()
        received = []
        pub.subscribe(AuditLogEvent, lambda e: received.append(e))
        event = AuditLogEvent(action=AuditAction.CREATE)
        await pub.publish(event)
        assert len(received) == 1
        assert received[0] is event

    @pytest.mark.asyncio
    async def test_publish_calls_async_handler(self):
        pub = EventPublisher()
        received = []

        async def async_handler(event):
            received.append(event)

        pub.subscribe(AuditLogEvent, async_handler)
        event = AuditLogEvent(action=AuditAction.UPDATE)
        await pub.publish(event)
        assert len(received) == 1
        assert received[0].action == AuditAction.UPDATE

    @pytest.mark.asyncio
    async def test_publish_no_handlers_returns_immediately(self):
        pub = EventPublisher()
        event = ArticleCreatedEvent(title="Test")
        # Should not raise
        await pub.publish(event)

    @pytest.mark.asyncio
    async def test_publish_does_not_call_unregistered_handlers(self):
        pub = EventPublisher()
        call_count = [0]

        def counter(_):
            call_count[0] += 1

        pub.subscribe(AuditLogEvent, counter)
        # Publish ArticleCreatedEvent — no handler registered for it
        await pub.publish(ArticleCreatedEvent())
        assert call_count[0] == 0

    @pytest.mark.asyncio
    async def test_handler_exception_does_not_stop_other_handlers(self):
        pub = EventPublisher()
        results = []

        def bad_handler(_):
            raise ValueError("boom")

        def good_handler(e):
            results.append(e)

        pub.subscribe(AuditLogEvent, bad_handler)
        pub.subscribe(AuditLogEvent, good_handler)
        event = AuditLogEvent(action=AuditAction.DELETE)
        await pub.publish(event)
        assert len(results) == 1
