"""AI Intelligence OS Backend — FastAPI Application Entry Point."""

from contextlib import asynccontextmanager

import logging

from fastapi import FastAPI

from .app.bootstrap import ApplicationBootstrap
from .database.connection import get_engine

logger = logging.getLogger(__name__)

_bootstrap: ApplicationBootstrap | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management."""
    global _bootstrap

    logger.info("Starting AI Intelligence OS backend...")

    # Initialize MCP servers, tool registry, and agents
    _bootstrap = ApplicationBootstrap()
    _bootstrap.initialize()

    app.state.mcp_registry = _bootstrap.mcp_registry
    app.state.tool_registry = _bootstrap.tool_registry

    engine = get_engine()
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
    return app


app = create_app()


@app.get("/api/health")
async def health_check():
    """Health check endpoint for container orchestration."""
    return {"status": "ok"}
