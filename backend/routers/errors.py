"""Centralized exception handlers for the API layer."""

from __future__ import annotations

import logging
import time
from collections.abc import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class NotFoundException(Exception):
    """Raised when a requested resource is not found."""

    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(message)
        self.message = message


class BadRequestException(Exception):
    """Raised when a request contains invalid parameters."""

    def __init__(self, message: str = "Bad request") -> None:
        super().__init__(message)
        self.message = message


async def _log_request(request: Request, call_next) -> JSONResponse:
    """Middleware that logs request path and execution time."""
    start = time.monotonic()
    response = await call_next(request)
    elapsed = time.monotonic() - start
    logger.info(
        "%s %s %d %.3fs",
        request.method,
        request.url.path,
        response.status_code,
        elapsed,
    )
    return response


def register_exception_handlers(app: FastAPI) -> None:
    """Register centralized exception handlers on the given FastAPI app."""

    @app.exception_handler(NotFoundException)
    async def not_found_handler(request: Request, exc: NotFoundException) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"success": False, "data": None, "error": exc.message},
        )

    @app.exception_handler(BadRequestException)
    async def bad_request_handler(request: Request, exc: BadRequestException) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"success": False, "data": None, "error": exc.message},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"success": False, "data": None, "error": str(exc)},
        )

    @app.exception_handler(Exception)
    async def generic_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error("Unhandled exception: %s", exc, exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"success": False, "data": None, "error": "Internal server error"},
        )


def setup_middleware(app: FastAPI) -> None:
    """Add structured logging middleware to the app."""
    from starlette.middleware.base import BaseHTTPMiddleware

    class LogMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next) -> JSONResponse:
            return await _log_request(request, call_next)

    app.add_middleware(LogMiddleware)
