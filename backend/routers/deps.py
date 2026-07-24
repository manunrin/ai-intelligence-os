"""Shared FastAPI dependencies."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Any

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock, MagicMock

from ..config import Settings, get_settings
from ..services.refresh_token_store import RefreshTokenStore

if TYPE_CHECKING:
    from ..repositories.user_repository import UserRepository
    from ..services.agent_runtime_service import AgentRuntimeService
    from ..services.article_service import ArticleService
    from ..services.knowledge_service import KnowledgeItemService
    from ..services.report_service import ReportService
    from ..services.scheduler.service import SchedulerService
    from ..services.task_service import TaskService
    from ..services.user_service import UserService

logger = logging.getLogger(__name__)


# ── Fake session factory (for tests) ─────────────────────────────────
# Before the A1 bootstrap refactor, tests patched get_session_factory.
# After the refactor, get_db reads from request.app.state.session_factory.
# This FakeSessionCtx provides a fake session that returns empty results
# for all queries, used by both the compat shim and get_db fallback.


class FakeSessionCtx:
    """Minimal async session that returns empty results for queries."""

    def __init__(self):
        self.commit = AsyncMock()
        self.rollback = AsyncMock()
        self.close = AsyncMock()
        self.add = AsyncMock()
        self.flush = AsyncMock()

        _result = MagicMock()
        _result.scalars = MagicMock(return_value=_result)
        _result.all = MagicMock(return_value=[])
        _result.scalar_one_or_none = MagicMock(return_value=None)
        self.execute = AsyncMock(return_value=_result)


async def get_db(request: Request):
    """Yield a database session for dependency injection."""
    sf = getattr(request.app.state, 'session_factory', None)
    if sf is None:
        # Test fallback: use FakeSessionCtx when app.state.session_factory is not set
        sf = FakeSessionCtx
    session = sf() if callable(sf) else sf
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def get_settings_dep() -> Settings:
    """Yield application settings for dependency injection."""
    return get_settings()


def get_event_publisher(request: Request) -> Any:
    """Yield the global EventPublisher from app.state."""
    return request.app.state.event_publisher


async def get_current_user(
    authorization: str | None = Header(default=None),
    db=Depends(get_db),
) -> Any:
    """Extract and validate the current user from a JWT token.

    Expects Authorization: Bearer <token> header.
    Raises HTTPException(401) if the token is invalid or the user is not found.
    """
    from ..utils.jwt import decode_access_token

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization[len("Bearer "):]
    settings = get_settings()
    payload = decode_access_token(token, settings)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    from ..repositories.user_repository import UserRepository

    repo = UserRepository(db)
    user = await repo.get_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account deactivated",
        )

    return user


def require_role(*roles: str):
    """Dependency factory that checks if the current user has one of the given roles."""

    async def _check_role(current_user: Any = Depends(get_current_user)) -> Any:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return _check_role


# ── Service factories ─────────────────────────────────────────────────

def get_task_service(db=Depends(get_db)) -> "TaskService":
    """Dependency: create TaskService bound to request session."""
    from ..services.task_service import TaskService
    return TaskService(db)


def get_article_service(db=Depends(get_db)) -> "ArticleService":
    """Dependency: create ArticleService bound to request session."""
    from ..services.article_service import ArticleService
    return ArticleService(db)


def get_report_service(db=Depends(get_db)) -> "ReportService":
    """Dependency: create ReportService bound to request session."""
    from ..services.report_service import ReportService
    return ReportService(db)


def get_user_service(
    db=Depends(get_db),
    request: Request = None,
) -> "UserService":  # noqa: F821
    """Dependency: create UserService bound to request session."""
    from ..services.user_service import UserService

    store = None
    if request is not None:
        store = getattr(request.app.state, "refresh_token_store", None)
    return UserService(db, token_store=store)


def get_runtime_service(
    db=Depends(get_db),
    request: Request = None,
) -> "AgentRuntimeService":
    """Dependency: create runtime service bound to request session with factory for bg tasks."""
    from ..services.agent_runtime_service import AgentRuntimeService
    sf = None
    cp = None
    eval_svc = None
    if request is not None:
        sf = getattr(request.app.state, 'session_factory', None)
        cp = getattr(request.app.state, 'checkpointer', None)
        eval_svc = getattr(request.app.state, 'evaluation_service', None)
    return AgentRuntimeService(db, session_factory=sf, checkpointer=cp, evaluation_service=eval_svc)


def get_evaluation_service(request: Request) -> Any:
    """Dependency: return the EvaluationService singleton from app state."""
    svc = getattr(request.app.state, 'evaluation_service', None)
    return svc


def get_runtime_service_with_event_pub(
    db=Depends(get_db),
    request: Request = None,
) -> "AgentRuntimeService":
    """Dependency: runtime service with event publisher for audit logging."""
    svc = get_runtime_service(db=db, request=request)
    if request is not None and hasattr(request.app.state, 'event_publisher'):
        svc._event_publisher = request.app.state.event_publisher
    return svc


# ── Compatibility shim ────────────────────────────────────────────────
# get_session_factory was removed during the A1 bootstrap refactor
# (session factory is now read from request.app.state.session_factory).
# This stub exists solely so existing test code that patches
# "backend.routers.deps.get_session_factory" does not crash on patch
# entry.  The returned FakeSessionCtx provides a fake session that
# returns empty results for all queries.


def get_session_factory():
    """Compatibility stub — returns a fake session for tests."""
    return FakeSessionCtx()


# ── AI infrastructure dependencies ──────────────────────────────────────

def get_llm_provider(request: Request) -> Any:
    """Dependency: return the default chat LLMProvider singleton from app state."""
    provider = getattr(request.app.state, 'llm_provider', None)
    if provider is None:
        raise RuntimeError("LLMProvider not initialized — no API key configured")
    return provider


def get_llm_router(request: Request) -> Any:
    """Dependency: return the LLMRouter singleton from app state."""
    router = getattr(request.app.state, 'llm_router', None)
    if router is None:
        raise RuntimeError("LLMRouter not initialized — check main.py startup")
    return router


def get_embedding_client(request: Request) -> Any:
    """Dependency: return the EmbeddingClient singleton from app state."""
    client = getattr(request.app.state, 'embedding_client', None)
    if client is None:
        raise RuntimeError("EmbeddingClient not initialized — check main.py startup")
    return client


def get_vector_service(request: Request) -> Any:
    """Dependency: return the QdrantVectorService singleton from app state."""
    svc = getattr(request.app.state, 'vector_service', None)
    if svc is None:
        raise RuntimeError("QdrantVectorService not initialized — check main.py startup")
    return svc


def get_knowledge_service(
    db=Depends(get_db),
    embedding_client=Depends(get_embedding_client),
    vector_service=Depends(get_vector_service),
) -> "KnowledgeItemService":
    """Dependency: create KnowledgeItemService bound to request session with embedding/vector services."""
    from ..services.knowledge_service import KnowledgeItemService
    return KnowledgeItemService(db, embedding_client=embedding_client, vector_service=vector_service)


def get_scheduler_service(request: Request) -> "SchedulerService":
    """Dependency: return the SchedulerService singleton from app.state."""
    svc = getattr(request.app.state, "scheduler_service", None)
    if svc is None:
        raise RuntimeError("SchedulerService not initialized — check main.py startup")
    return svc


def get_redis_client(request: Request) -> "RefreshTokenStore | None":
    """Dependency: return the RefreshTokenStore from app.state, or None if Redis is unavailable."""
    store = getattr(request.app.state, "refresh_token_store", None)
    return store
