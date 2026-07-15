"""AI Intelligence OS Backend — FastAPI Application Entry Point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management."""
    # Startup: initialize DB pools, connect to Redis/Qdrant, warm caches
    yield
    # Shutdown: close connections, drain queues


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
