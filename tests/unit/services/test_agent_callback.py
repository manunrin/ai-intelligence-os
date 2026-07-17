"""Tests for AgentRuntimeCallback — LangGraph integration."""

from __future__ import annotations

import uuid

import pytest

from backend.workflows.graph.callbacks import AgentRuntimeCallback, StageEvent


class TestAgentRuntimeCallback:
    def test_on_chain_start_records_event(self):
        run_id = uuid.uuid4()
        cb = AgentRuntimeCallback(run_id)
        cb.on_chain_start(
            serialized={"name": "research"},
            inputs={"topic": "AI"},
            run_id=uuid.uuid4(),
        )
        assert len(cb.events) == 1
        assert cb.events[0].phase == "start"
        assert cb.events[0].node_name == "research"

    def test_on_chain_end_records_event(self):
        run_id = uuid.uuid4()
        cb = AgentRuntimeCallback(run_id)
        cb.on_chain_start(serialized={"name": "research"}, inputs={}, run_id=uuid.uuid4())
        cb.on_chain_end(outputs={"result": "data"}, run_id=uuid.uuid4())
        assert len(cb.events) == 2
        assert cb.events[1].phase == "end"
        assert cb.events[1].outputs == {"result": "data"}

    def test_on_chain_error_records_event(self):
        run_id = uuid.uuid4()
        cb = AgentRuntimeCallback(run_id)
        cb.on_chain_start(serialized={"name": "analyst"}, inputs={}, run_id=uuid.uuid4())
        cb.on_chain_error(error=RuntimeError("fail"), run_id=uuid.uuid4())
        assert len(cb.events) == 2
        assert cb.events[1].phase == "error"
        assert cb.events[1].error_message == "fail"

    def test_tool_start_records_event(self):
        run_id = uuid.uuid4()
        cb = AgentRuntimeCallback(run_id)
        cb.on_tool_start(
            serialized={"name": "browser.search"},
            input={"query": "test"},
            run_id=uuid.uuid4(),
        )
        assert len(cb.events) >= 1
        # Tool events are recorded
        tool_events = [e for e in cb.events if e.node_name.startswith("tool:")]
        assert len(tool_events) >= 1

    def test_ignore_flags(self):
        cb = AgentRuntimeCallback(uuid.uuid4())
        assert cb.ignore_llm is True
        assert cb.ignore_retriever is True
        assert cb.ignore_agent is True

    def test_multiple_nodes_tracked_separately(self):
        run_id = uuid.uuid4()
        cb = AgentRuntimeCallback(run_id)
        cb.on_chain_start(serialized={"name": "research"}, inputs={}, run_id=uuid.uuid4())
        cb.on_chain_end(outputs={}, run_id=uuid.uuid4())
        cb.on_chain_start(serialized={"name": "analyst"}, inputs={}, run_id=uuid.uuid4())
        cb.on_chain_end(outputs={}, run_id=uuid.uuid4())
        assert len(cb.events) == 4
        names = [e.node_name for e in cb.events]
        assert names == ["research", "research", "analyst", "analyst"]


class TestStageEvent:
    def test_stage_event_dataclass(self):
        run_id = uuid.uuid4()
        event = StageEvent(
            run_id=run_id, node_name="test", phase="start",
            error_message=None, outputs=None,
        )
        assert event.run_id == run_id
        assert event.node_name == "test"
        assert event.phase == "start"
