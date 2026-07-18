"""User authentication service."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..events.event import AuditAction, AuditLogEvent
from ..repositories.user_repository import UserRepository
from ..schemas.user import UserCreate, UserLogin, UserResponse
from ..utils.auth import hash_password, verify_password

logger = logging.getLogger(__name__)


class UserService:
    """Business logic for user authentication."""

    def __init__(self, session: AsyncSession, event_publisher=None) -> None:
        self._repo = UserRepository(session)
        self._publisher = event_publisher

    async def register(self, data: UserCreate) -> UserResponse:
        """Register a new user. Raises ValueError if username or email exists."""
        existing = await self._repo.get_by_username(data.username)
        if existing is not None:
            raise ValueError(f"Username '{data.username}' already exists")

        existing_email = await self._repo.get_by_email(data.email)
        if existing_email is not None:
            raise ValueError(f"Email '{data.email}' already registered")

        now = datetime.now(timezone.utc)
        user = await self._repo.create(
            username=data.username,
            email=data.email,
            hashed_password=hash_password(data.password),
            role="user",
            is_active=True,
            last_login_at=None,
            created_at=now,
            updated_at=now,
        )
        await self._publish_audit(AuditAction.CREATE, str(user.id))
        return self._to_response(user)

    async def authenticate(self, data: UserLogin) -> UserResponse | None:
        """Authenticate a user by username and password.

        Returns user profile on success, None on failure.
        Updates last_login_at on successful login.
        """
        user = await self._repo.get_by_username(data.username)
        if user is None or not verify_password(data.password, user.hashed_password):
            return None

        user.last_login_at = datetime.now(timezone.utc)
        await self._repo.session.flush()
        await self._publish_audit(AuditAction.LOGIN, str(user.id))
        return self._to_response(user)

    async def get_user(self, user_id: str) -> UserResponse | None:
        """Get user by UUID."""
        user = await self._repo.get_by_id(uuid.UUID(user_id))
        if user is None:
            return None
        return self._to_response(user)

    async def _publish_audit(self, action: AuditAction, resource_id: str) -> None:
        if self._publisher is None:
            return
        try:
            from ..context_vars import ip_address as _ip_ctx, user_agent as _ua_ctx
            await self._publisher.publish(AuditLogEvent(
                action=action,
                resource_type="auth",
                resource_id=uuid.UUID(resource_id),
                user_id=uuid.UUID(resource_id),
                ip_address=_ip_ctx.get(),
                user_agent=_ua_ctx.get(),
                metadata={"resource_id": resource_id},
            ))
        except Exception:
            logger.error("Failed to publish audit event for %s auth %s", action.value, resource_id, exc_info=True)

    @staticmethod
    def _to_response(user: Any) -> UserResponse:
        """Convert ORM model to response schema."""
        return UserResponse(
            id=str(user.id),
            username=user.username,
            email=user.email,
            role=user.role,
            is_active=user.is_active,
            last_login_at=user.last_login_at,
            created_at=user.created_at,
        )
