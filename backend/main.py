"""AI Intelligence OS Backend — FastAPI Application Entry Point."""

from contextlib import asynccontextmanager

import logging
import os

from fastapi import FastAPI

from .app.bootstrap import ApplicationBootstrap
from .routers.api import api_router, register_exception_handlers, setup_middleware
from .database.connection import create_engine_for_settings, get_session_factory

logger = logging.getLogger(__name__)

_bootstrap: ApplicationBootstrap | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management."""
    global _bootstrap

    from .config import get_settings

    logger.info("Starting AI Intelligence OS backend...")

    # Initialize engine explicitly at startup (not lazily)
    engine = create_engine_for_settings(get_settings())

    # Initialize MCP servers, tool registry, and agents
    _bootstrap = ApplicationBootstrap()
    _bootstrap.initialize()

    app.state.mcp_registry = _bootstrap.mcp_registry
    app.state.tool_registry = _bootstrap.tool_registry

    logger.info("Backend startup complete — MCP servers: %s", list(_bootstrap.mcp_registry.list_servers().keys()))

    yield

    # Shutdown
    if _bootstrap:
        await _bootstrap.mcp_registry.shutdown_all()
    await engine.dispose()
    logger.info("Backend shutdown complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="AI Intelligence OS",
        version="0.1.0",
        description="Enterprise AI Intelligence Operating System",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        lifespan=lifespan,
    )

    # Register centralized exception handlers and middleware
    register_exception_handlers(app)
    setup_middleware(app)

    # Allow frontend dev server to call backend APIs
    from starlette.middleware.cors import CORSMiddleware

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[os.getenv("NEXT_PUBLIC_API_URL", "http://localhost:3000")],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register the single aggregated API router
    app.include_router(api_router, prefix="/api/v1")

    @app.get("/api/health", tags=["health"], summary="Health check", description="Health check endpoint for container orchestration.")
    async def health_check():
        return {"status": "ok"}

    return app


app = create_app()
