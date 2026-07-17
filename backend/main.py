"""AI Intelligence OS Backend — FastAPI Application Entry Point."""

from contextlib import asynccontextmanager

import logging
import os

from fastapi import Depends, FastAPI, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from .app.bootstrap import ApplicationBootstrap
from .routers.api import api_router, register_exception_handlers, setup_middleware
from .routers.deps import get_db
from .database.connection import create_engine_for_settings

logger = logging.getLogger(__name__)

_bootstrap: ApplicationBootstrap | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management."""
    global _bootstrap

    from .config import get_settings

    logger.info("Starting AI Intelligence OS backend...")

    # Initialize engine explicitly at startup (not lazily)
    engine, session_factory = create_engine_for_settings(get_settings())

    # Initialize MCP servers, tool registry, and agents
    _bootstrap = ApplicationBootstrap(session_factory)
    _bootstrap.initialize()

    app.state.bootstrap = _bootstrap
    app.state.mcp_registry = _bootstrap.mcp_registry
    app.state.tool_registry = _bootstrap.tool_registry
    app.state.event_publisher = _bootstrap.event_publisher
    app.state.session_factory = session_factory

    logger.info("Backend startup complete — MCP servers: %s", list(_bootstrap.mcp_registry.list_servers().keys()))

    yield

    # Shutdown
    if _bootstrap:
        await _bootstrap.mcp_registry.shutdown_all()
    await engine.dispose()
    logger.info("Backend shutdown complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    # Configure structured JSON logging before any other imports that log
    from .logging_config import setup_logging

    setup_logging(os.getenv("LOG_LEVEL", "INFO"))

    app = FastAPI(
        title="AI Intelligence OS",
        version="0.1.0",
        description="Enterprise AI Intelligence Operating System",
        docs_url="/api/docs" if os.getenv("APP_ENV", "development") != "production" else None,
        redoc_url="/api/redoc" if os.getenv("APP_ENV", "development") != "production" else None,
        lifespan=lifespan,
    )

    # Register Bearer JWT security scheme in OpenAPI spec
    http_bearer = HTTPBearer()

    original_openapi = app.openapi

    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        openapi_schema = original_openapi()
        openapi_schema["components"] = openapi_schema.get("components") or {}
        openapi_schema["components"]["securitySchemes"] = {
            "Bearer": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "Enter JWT token obtained from /api/v1/auth/login endpoint.",
            }
        }
        # Public endpoints that should NOT require authentication
        public_paths = {"/api/v1/auth/register", "/api/v1/auth/login", "/api/health", "/api/live"}
        for path, methods in openapi_schema.get("paths", {}).items():
            for method in ("get", "post", "put", "delete", "patch"):
                if method not in methods:
                    continue
                if path in public_paths:
                    methods[method].pop("security", None)
                else:
                    methods[method]["security"] = [{"Bearer": []}]
        return openapi_schema

    app.openapi = custom_openapi

    # Register centralized exception handlers and middleware
    register_exception_handlers(app)
    setup_middleware(app)

    # CORS configuration — environment-aware
    from starlette.middleware.cors import CORSMiddleware

    cors_origins_str = os.getenv("CORS_ALLOWED_ORIGINS", "")
    if cors_origins_str.strip():
        allowed_origins = [o.strip() for o in cors_origins_str.split(",") if o.strip()]
    else:
        # Development default: localhost only
        allowed_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept"],
        max_age=600,
    )

    # Security headers middleware — enable HSTS in production/HTTPS mode
    from .routers.security_headers import SecurityHeadersMiddleware

    force_https = os.getenv("FORCE_HTTPS", "").lower() in ("1", "true", "yes")
    app.add_middleware(SecurityHeadersMiddleware, force_https=force_https)

    # Rate limiting with slowapi (uses shared limiter from rate_limiter module)
    from slowapi.errors import RateLimitExceeded
    from slowapi import _rate_limit_exceeded_handler
    from .rate_limiter import limiter

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Register the single aggregated API router
    app.include_router(api_router, prefix="/api/v1")

    # Health check endpoints — liveness + readiness with DB connectivity
    @app.get("/api/live", tags=["health"], summary="Liveness check")
    async def live_check():
        """Always returns 200 if process is alive (Kubernetes liveness probe)."""
        return {"status": "ok"}

    @app.get(
        "/api/health",
        tags=["health"],
        summary="Readiness check",
        description="Checks database connectivity and bootstrap state.",
    )
    async def health_check():
        """Readiness probe — verifies dependencies are healthy."""
        checks = {}

        # Database connectivity — use asyncpg directly since we use asyncpg driver
        db_status = "unhealthy: no database configured"
        try:
            from urllib.parse import urlparse

            from .config import get_settings
            import asyncpg

            settings = get_settings()
            url = settings.database_url
            parsed = urlparse(url)
            port = parsed.port or 5432
            host = parsed.hostname or "localhost"

            conn = await asyncpg.connect(
                database=parsed.path.lstrip("/"),
                user=parsed.username or "postgres",
                password=parsed.password or "",
                host=host,
                port=port,
            )
            await conn.fetchval("SELECT 1")
            await conn.close()
            db_status = "healthy"
        except Exception as exc:
            db_status = f"unhealthy: {exc}"
        checks["database"] = db_status

        # Bootstrap state
        checks["bootstrap"] = "ready" if _bootstrap else "initializing"

        overall = "healthy" if all(v == "healthy" or v == "ready" for v in checks.values()) else "unhealthy"
        status_code = status.HTTP_200_OK if overall == "healthy" else status.HTTP_503_SERVICE_UNAVAILABLE

        return JSONResponse(
            content={"status": overall, "checks": checks},
            status_code=status_code,
        )

    return app


app = create_app()
