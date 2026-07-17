"""Rate limiter shared across the application."""

from __future__ import annotations

import os

from slowapi import Limiter
from slowapi.util import get_remote_address

_default = f"{os.getenv('RATE_LIMIT_REQUESTS', '100')} per {os.getenv('RATE_LIMIT_WINDOW_SECONDS', '3600')} seconds"

_redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[_default],
    storage_uri=_redis_url,
    in_memory_fallback=[_default],
)
