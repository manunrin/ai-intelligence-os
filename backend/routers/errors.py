"""Centralized exception handlers for the API layer."""

from __future__ import annotations

import logging
import time
import uuid

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware

from ..schemas.error import ErrorResponse


def register_exception_handlers(app: FastAPI) -> None:
    """Register centralized exception handlers on the given FastAPI app."""

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        error = ErrorResponse.from_validation_error(exc)
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=error.model_dump(),
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        error = ErrorResponse.from_http_exception(exc)
        return JSONResponse(
            status_code=exc.status_code,
            content=error.model_dump(),
            headers=exc.headers,
        )

    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
        error = ErrorResponse.from_rate_limit_exceeded()
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content=error.model_dump(),
        )

    @app.exception_handler(Exception)
    async def generic_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "unknown")
        logger = logging.getLogger(__name__)
        logger.error("Unhandled exception: %s", exc, exc_info=True, extra={"request_id": request_id})
        error = ErrorResponse.from_unhandled_exception(exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error.model_dump(),
        )


def _normalize_path(path: str) -> str:
    """Replace UUID-like path segments with <uuid> to prevent cardinality explosion.

    E.g. /api/v1/agents/runs/550e8400-e29b-41d4-a716-446655440000/stream
         → /api/v1/agents/runs/<uuid>/stream
    """
    import re

    # Match UUIDs (with or without hyphens) in path segments
    return re.sub(
        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
        "<uuid>",
        path,
    )


def setup_middleware(app: FastAPI) -> None:
    """Add request logging middleware to the app."""

    class TraceMiddleware(BaseHTTPMiddleware):
        """Extract W3C traceparent header and inject tracecontext into responses."""

        async def dispatch(self, request: Request, call_next) -> JSONResponse:
            from ..context_vars import trace_span as _trace_ctx
            from ..trace import start_span

            traceparent = request.headers.get("traceparent", "")
            tracestate = request.headers.get("tracestate", "")

            span_attrs = {
                "http.method": request.method,
                "http.target": str(request.url.path),
            }

            with start_span(f"{request.method} {request.url.path}", attributes=span_attrs) as span:
                _trace_ctx.set(span)
                try:
                    response = await call_next(request)
                    return response
                finally:
                    _trace_ctx.set(None)

    app.add_middleware(TraceMiddleware)

    class LogMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next) -> JSONResponse:
            from ..context_vars import ip_address as _ip_ctx, request_id as _req_ctx, user_agent as _ua_ctx

            request_id = request.headers.get(
                "X-Request-ID", str(uuid.uuid4())
            )
            request.state.request_id = request_id
            _req_ctx.set(request_id)

            _ip_ctx.set(request.headers.get("x-forwarded-for"))
            _ua_ctx.set(request.headers.get("user-agent"))

            start = time.monotonic()
            response = await call_next(request)
            elapsed = time.monotonic() - start

            from ..logging_config import make_request_log_record
            from ..metrics import counter, histogram

            status_str = str(response.status_code)
            method_str = request.method
            path_str = _normalize_path(str(request.url.path))

            counter("http_requests_total", labels={"method": method_str, "status": status_str, "path": path_str})
            histogram("http_request_duration_seconds", elapsed, labels={"method": method_str, "status": status_str, "path": path_str})

            log_record = make_request_log_record(
                method=request.method,
                path=str(request.url.path),
                status_code=response.status_code,
                elapsed_seconds=elapsed,
                request_id=request_id,
            )
            logger = logging.getLogger(__name__)
            logger.handle(log_record)

            response.headers["X-Request-ID"] = request_id
            return response

    app.add_middleware(LogMiddleware)
