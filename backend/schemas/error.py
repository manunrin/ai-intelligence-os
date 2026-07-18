"""Standardized API error response schema."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Structured error response returned in all API error envelopes.

    Fields:
        code: Machine-readable error code (e.g. VALIDATION_ERROR, USER_NOT_FOUND).
        message: Human-readable error description.
        details: Optional per-field or per-cause detail entries.
    """

    code: str
    message: str
    details: list[dict[str, Any]] | None = None

    @classmethod
    def from_http_exception(cls, exc: "HTTPException") -> "ErrorResponse":
        """Derive ErrorResponse from a FastAPI HTTPException."""
        code_map: dict[int, str] = {
            400: "BAD_REQUEST",
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            409: "CONFLICT",
            422: "VALIDATION_ERROR",
            429: "RATE_LIMIT_EXCEEDED",
            500: "INTERNAL_SERVER_ERROR",
            503: "SERVICE_UNAVAILABLE",
        }
        return cls(
            code=code_map.get(exc.status_code, "ERROR"),
            message=exc.detail,
        )

    @classmethod
    def from_validation_error(cls, exc: "RequestValidationError") -> "ErrorResponse":
        """Derive ErrorResponse from a FastAPI RequestValidationError."""
        errors: list[dict[str, Any]] = []
        for error in exc.errors():
            loc = ".".join(str(p) for p in error.get("loc", ()))
            errors.append({"field": loc, "message": error.get("msg", "")})
        return cls(code="VALIDATION_ERROR", message="Validation failed", details=errors)

    @classmethod
    def from_rate_limit_exceeded(cls) -> "ErrorResponse":
        """Derive ErrorResponse from a slowapi rate limit hit."""
        return cls(code="RATE_LIMIT_EXCEEDED", message="Rate limit exceeded. Please try again later.")

    @classmethod
    def from_unhandled_exception(cls, exc: Exception) -> "ErrorResponse":
        """Derive ErrorResponse from an unexpected exception — never leak internals."""
        return cls(code="INTERNAL_SERVER_ERROR", message="Internal server error")
