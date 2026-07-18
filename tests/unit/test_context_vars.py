"""Tests for context variables used in request/agent scoping."""

from __future__ import annotations

import pytest


class TestContextVars:
    """Test that context vars are properly isolated per async task."""

    def test_request_id_default(self):
        """request_id defaults to 'unknown' when not set."""
        from backend.context_vars import request_id as _ctx

        val = _ctx.get()
        assert val == "unknown"

    def test_request_id_set_and_get(self):
        """Setting a request_id is visible within the same context."""
        from backend.context_vars import request_id as _ctx

        _ctx.set("req-abc-123")
        assert _ctx.get() == "req-abc-123"

    def test_agent_run_id_default(self):
        """agent_run_id defaults to None when not set."""
        from backend.context_vars import agent_run_id as _ctx

        assert _ctx.get() is None

    def test_agent_run_id_set_and_get(self):
        """Setting an agent_run_id is visible within the same context."""
        from backend.context_vars import agent_run_id as _ctx

        run_id = str(__import__("uuid").uuid4())
        _ctx.set(run_id)
        assert _ctx.get() == run_id

    def test_context_isolation(self):
        """Changing one context var doesn't affect others."""
        from backend.context_vars import (
            agent_run_id,
            ip_address,
            request_id,
            user_agent,
        )

        request_id.set("my-request-id")
        ip_address.set("10.0.0.1")
        user_agent.set("test-agent")
        agent_run_id.set("run-xyz")

        assert request_id.get() == "my-request-id"
        assert ip_address.get() == "10.0.0.1"
        assert user_agent.get() == "test-agent"
        assert agent_run_id.get() == "run-xyz"
