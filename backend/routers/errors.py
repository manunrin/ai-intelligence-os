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


def setup_middleware(app: FastAPI) -> None:
    """Add request logging middleware to the app."""

    class LogMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next) -> JSONResponse:
            from ..context_vars import ip_address as _ip_ctx, user_agent as _ua_ctx

            request_id = request.headers.get(
                "X-Request-ID", str(uuid.uuid4())
            )
            request.state.request_id = request_id

            _ip_ctx.set(request.headers.get("x-forwarded-for"))
            _ua_ctx.set(request.headers.get("user-agent"))

            start = time.monotonic()
            response = await call_next(request)
            elapsed = time.monotonic() - start

            from ..logging_config import make_request_log_record

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
