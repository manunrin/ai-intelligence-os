"""Single API router that aggregates all sub-routers."""

from __future__ import annotations

from fastapi import APIRouter

from .agents import router as agents_router
from .articles import router as articles_router
from .audit import router as audit_router
from .auth import router as auth_router
from .errors import register_exception_handlers, setup_middleware
from .knowledge import router as knowledge_router
from .reports import router as reports_router
from .scheduler import router as scheduler_router
from .tasks import router as tasks_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(articles_router)
api_router.include_router(knowledge_router)
api_router.include_router(tasks_router)
api_router.include_router(agents_router, prefix="/agents")
api_router.include_router(scheduler_router)
api_router.include_router(reports_router)
api_router.include_router(audit_router)

__all__ = ["api_router", "register_exception_handlers", "setup_middleware"]
