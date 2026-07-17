"""Tests for AgentEvent abstraction and SSE serialization."""

from __future__ import annotations

import json
import uuid

import pytest

from backend.events.agent_event import AgentEvent, EventType


class TestAgentEventSSE:
    def test_stage_start_sse_format(self):
        run_id = uuid.uuid4()
        event = AgentEvent.stage_start(run_id, "research")
        sse = event.to_sse()
        assert sse.startswith("event: stage_start\n")
        assert '"type": "stage_start"' in sse
        assert f'"run_id": "{run_id}"' in sse
        assert '"stage_name": "research"' in sse
        assert '"status": "executing"' in sse

    def test_stage_complete_sse_format(self):
        run_id = uuid.uuid4()
        event = AgentEvent.stage_complete(run_id, "research", duration_ms=1234, output_summary={"result": "data"})
        sse = event.to_sse()
        assert "event: stage_complete" in sse
        assert '"duration_ms": 1234' in sse
        assert '"output_summary": {"result": "data"}' in sse

    def test_run_failed_sse_format(self):
        run_id = uuid.uuid4()
        event = AgentEvent.run_failed(run_id, "connection error")
        sse = event.to_sse()
        assert "event: run_failed" in sse
        assert '"error_message": "connection error"' in sse

    def test_heartbeat_sse_format(self):
        run_id = uuid.uuid4()
        event = AgentEvent.heartbeat(run_id)
        sse = event.to_sse()
        assert "event: heartbeat" in sse
        assert '"type": "heartbeat"' in sse

    def test_extra_fields_serialized(self):
        run_id = uuid.uuid4()
        event = AgentEvent(type=EventType.RUN_COMPLETE, run_id=run_id, extra={"custom": "value"})
        sse = event.to_sse()
        assert '"extra": {"custom": "value"}' in sse

    def test_all_event_types_have_factory_methods(self):
        run_id = uuid.uuid4()
        # Verify each factory method produces a valid event
        e1 = AgentEvent.stage_start(run_id, "test")
        assert e1.type == EventType.STAGE_START

        e2 = AgentEvent.stage_complete(run_id, "test")
        assert e2.type == EventType.STAGE_COMPLETE

        e3 = AgentEvent.stage_failed(run_id, "test", "error")
        assert e3.type == EventType.STAGE_FAILED

        e4 = AgentEvent.run_complete(run_id)
        assert e4.type == EventType.RUN_COMPLETE

        e5 = AgentEvent.run_failed(run_id, "error")
        assert e5.type == EventType.RUN_FAILED

        e6 = AgentEvent.run_cancelled(run_id)
        assert e6.type == EventType.RUN_CANCELLED

        e7 = AgentEvent.heartbeat(run_id)
        assert e7.type == EventType.HEARTBEAT

    def test_json_decodable(self):
        """Verify SSE data is valid JSON that can be decoded."""
        run_id = uuid.uuid4()
        event = AgentEvent.stage_complete(run_id, "research", duration_ms=500, output_summary={"key": "val"})
        sse = event.to_sse()
        lines = sse.strip().split("\n")
        data_line = [l for l in lines if l.startswith("data:")][0]
        payload = json.loads(data_line[5:])
        assert payload["type"] == "stage_complete"
        assert payload["duration_ms"] == 500
        assert payload["output_summary"]["key"] == "val"
