"""Context variables for request-scoped audit metadata."""

from __future__ import annotations

import contextvars

ip_address: contextvars.ContextVar[str | None] = contextvars.ContextVar("ip_address", default=None)
user_agent: contextvars.ContextVar[str | None] = contextvars.ContextVar("user_agent", default=None)
