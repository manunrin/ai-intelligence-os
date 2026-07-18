"""Context variables for request-scoped audit metadata."""

from __future__ import annotations

import contextvars

ip_address: contextvars.ContextVar[str | None] = contextvars.ContextVar("ip_address", default=None)
user_agent: contextvars.ContextVar[str | None] = contextvars.ContextVar("user_agent", default=None)
request_id: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="unknown")
agent_run_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("agent_run_id", default=None)
