"""Rate limiter shared across the application."""

from __future__ import annotations

import os

from starlette.requests import Request

from slowapi import Limiter
from slowapi.util import get_remote_address

_default = f"{os.getenv('RATE_LIMIT_REQUESTS', '100')} per {os.getenv('RATE_LIMIT_WINDOW_SECONDS', '3600')} seconds"

_redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")


def _get_proxy_address(request: Request):
    """Extract real client IP from X-Forwarded-For when behind a reverse proxy."""
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return get_remote_address(request)


limiter = Limiter(
    key_func=_get_proxy_address,
    default_limits=[_default],
    storage_uri=_redis_url,
    in_memory_fallback=[_default],
)
