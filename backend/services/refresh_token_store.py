"""Redis-backed opaque refresh token store.

Tokens are stored as SHA-256 hashes so the plaintext never appears in Redis.
Lookup is O(1) by hashing the incoming token and checking the hash key.
"""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)


def _hash_token(token: str) -> str:
    """Return the hex-encoded SHA-256 digest of *token*."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class RefreshTokenStore:
    """Store and validate opaque refresh tokens in Redis.

    Keys are prefixed ``rt:{sha256_hash}``.
    Values are JSON: ``{"user_id": str, "created_at": ISO8601, "exp_epoch": float}``.
    TTL is set to the token's expiry so Redis auto-cleans expired entries.
    """

    def __init__(self, redis_client: aioredis.Redis, expire_days: int = 7) -> None:
        self._redis = redis_client
        self._expire_seconds = expire_days * 86_400

    # -- public API --

    async def store(self, user_id: str, token_plaintext: str) -> None:
        """Store a new refresh token with TTL-based expiry."""
        key = self._key(token_plaintext)
        now = datetime.now(timezone.utc)
        payload = {
            "user_id": str(user_id),
            "created_at": now.isoformat(),
            "exp_epoch": now.timestamp() + self._expire_seconds,
        }
        await self._redis.set(key, json.dumps(payload), ex=self._expire_seconds)

    async def validate(self, token_plaintext: str) -> str | None:
        """Return user_id if the token exists and is not expired, else None."""
        key = self._key(token_plaintext)
        raw = await self._redis.get(key)
        if raw is None:
            return None
        data = json.loads(raw) if isinstance(raw, bytes) else raw
        if datetime.now(timezone.utc).timestamp() > float(data["exp_epoch"]):
            await self._redis.delete(key)
            return None
        return data["user_id"]

    async def revoke(self, token_plaintext: str) -> bool:
        """Revoke a single refresh token. Returns True if a key was deleted."""
        key = self._key(token_plaintext)
        result = await self._redis.delete(key)
        return result > 0

    async def revoke_all_user_tokens(self, user_id: str) -> int:
        """Revoke every refresh token for a user. Returns count revoked."""
        count = 0
        pattern = "rt:*"
        async for key in self._redis.scan_iter(match=pattern, type="string"):
            try:
                raw = await self._redis.get(key)
                if raw is None:
                    continue
                data = json.loads(raw) if isinstance(raw, bytes) else raw
                if data.get("user_id") == str(user_id):
                    await self._redis.delete(key)
                    count += 1
            except Exception:
                logger.warning("Failed to revoke refresh token %s", key, exc_info=True)
        return count

    async def rotate(self, old_token: str, new_token: str, user_id: str) -> None:
        """Invalidate old token and store a new one (one-use rotation)."""
        await self.revoke(old_token)
        await self.store(user_id, new_token)

    # -- internals --

    @staticmethod
    def _key(token: str) -> str:
        return f"rt:{_hash_token(token)}"

    @classmethod
    def from_url(cls, url: str, expire_days: int = 7) -> RefreshTokenStore:
        """Create a store from a Redis URL string."""
        return cls(aioredis.from_url(url, decode_responses=False), expire_days=expire_days)
