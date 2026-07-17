"""Centralized exception handlers for the API layer."""

from __future__ import annotations

import logging
import time
import uuid

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


def register_exception_handlers(app: FastAPI) -> None:
    """Register centralized exception handlers on the given FastAPI app."""

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"success": False, "data": None, "error": str(exc)},
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"success": False, "data": None, "error": exc.detail},
            headers=exc.headers,
        )

    @app.exception_handler(Exception)
    async def generic_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", "unknown")
        logger = logging.getLogger(__name__)
        logger.error("Unhandled exception: %s", exc, exc_info=True, extra={"request_id": request_id})
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "data": None, "error": "Internal server error"},
        )


def setup_middleware(app: FastAPI) -> None:
    """Add request logging middleware to the app."""

    class LogMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next) -> JSONResponse:
            request_id = request.headers.get(
                "X-Request-ID", str(uuid.uuid4())
            )
            request.state.request_id = request_id

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
