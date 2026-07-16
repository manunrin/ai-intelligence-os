"""Single API router that aggregates all sub-routers."""

from __future__ import annotations

from fastapi import APIRouter

from .agents import router as agents_router
from .articles import router as articles_router
from .errors import register_exception_handlers, setup_middleware
from .knowledge import router as knowledge_router
from .reports import router as reports_router
from .tasks import router as tasks_router

api_router = APIRouter()
api_router.include_router(articles_router)
api_router.include_router(knowledge_router)
api_router.include_router(tasks_router)
api_router.include_router(agents_router)
api_router.include_router(reports_router)

__all__ = ["api_router", "register_exception_handlers", "setup_middleware"]
