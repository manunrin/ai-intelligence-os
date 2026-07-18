"""Contract tests for the unified error response envelope.

Validates that every error path produces {code, message, details} and that
ErrorResponse factory methods return deterministic mappings.
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException, status
from fastapi.exceptions import RequestValidationError
from slowapi.errors import RateLimitExceeded

from backend.schemas.error import ErrorResponse


# ------------------------------------------------------------------
#  1. ErrorResponse.from_http_exception — deterministic code mapping
# ------------------------------------------------------------------

class TestFromHttpexception:
    @pytest.mark.parametrize(
        "status_code,expected_code",
        [
            (400, "BAD_REQUEST"),
            (401, "UNAUTHORIZED"),
            (403, "FORBIDDEN"),
            (404, "NOT_FOUND"),
            (409, "CONFLICT"),
            (422, "VALIDATION_ERROR"),
            (429, "RATE_LIMIT_EXCEEDED"),
            (500, "INTERNAL_SERVER_ERROR"),
            (503, "SERVICE_UNAVAILABLE"),
        ],
    )
    def test_known_status_codes_map(self, status_code, expected_code):
        exc = HTTPException(status_code=status_code, detail="boom")
        err = ErrorResponse.from_http_exception(exc)
        assert err.code == expected_code
        assert err.message == "boom"
        assert err.details is None

    def test_unknown_status_code_falls_back_to_error(self):
        exc = HTTPException(status_code=418, detail="I'm a teapot")
        err = ErrorResponse.from_http_exception(exc)
        assert err.code == "ERROR"
        assert err.message == "I'm a teapot"

    def test_headers_not_in_serialized_output(self):
        """ErrorResponse serializes only code/message/details; headers are
        added by the handler layer, not by the factory."""
        err = ErrorResponse.from_http_exception(
            HTTPException(status_code=400, detail="bad", headers={"x-foo": "bar"})
        )
        dumped = err.model_dump()
        assert set(dumped.keys()) == {"code", "message", "details"}


# ------------------------------------------------------------------
#  2. ErrorResponse.from_validation_error — per-field details
# ------------------------------------------------------------------

class TestFromValidationError:
    def test_single_field_error(self):
        exc = RequestValidationError(
            [{"type": "too_short", "loc": ("body", "title"), "msg": "Field required"}]
        )
        err = ErrorResponse.from_validation_error(exc)
        assert err.code == "VALIDATION_ERROR"
        assert err.message == "Validation failed"
        assert len(err.details) == 1
        assert err.details[0]["field"] == "body.title"
        assert err.details[0]["message"] == "Field required"

    def test_multiple_field_errors(self):
        exc = RequestValidationError([
            {"type": "value_error", "loc": ("body", "email"), "msg": "Invalid email"},
            {"type": "too_short", "loc": ("body", "password"), "msg": "Too short"},
        ])
        err = ErrorResponse.from_validation_error(exc)
        assert len(err.details) == 2
        assert err.details[0]["field"] == "body.email"
        assert err.details[1]["field"] == "body.password"

    def test_nested_path_in_location(self):
        exc = RequestValidationError([
            {"type": "model_attributes_type", "loc": ("body", "items", 0, "name"), "msg": "Invalid type"}
        ])
        err = ErrorResponse.from_validation_error(exc)
        assert err.details[0]["field"] == "body.items.0.name"


# ------------------------------------------------------------------
#  3. ErrorResponse.from_rate_limit_exceeded
# ------------------------------------------------------------------

class TestFromRateLimitExceeded:
    def test_rate_limit_error_shape(self):
        """from_rate_limit_exceeded() is a no-arg factory — it always
        returns the same shape regardless of the RateLimitExceeded instance."""
        err = ErrorResponse.from_rate_limit_exceeded()
        assert err.code == "RATE_LIMIT_EXCEEDED"
        assert err.message == "Rate limit exceeded. Please try again later."
        assert err.details is None

    def test_rate_limit_serialization(self):
        dumped = ErrorResponse.from_rate_limit_exceeded().model_dump()
        assert set(dumped.keys()) == {"code", "message", "details"}
        assert dumped["code"] == "RATE_LIMIT_EXCEEDED"


# ------------------------------------------------------------------
#  4. ErrorResponse.from_unhandled_exception — never leak internals
# ------------------------------------------------------------------

class TestFromUnhandledException:
    def test_generic_message_no_leak(self):
        exc = RuntimeError("database connection refused")
        err = ErrorResponse.from_unhandled_exception(exc)
        assert err.code == "INTERNAL_SERVER_ERROR"
        assert err.message == "Internal server error"
        assert "database" not in err.message.lower()

    def test_value_error_same_behaviour(self):
        exc = ValueError("bad input")
        err = ErrorResponse.from_unhandled_exception(exc)
        assert err.code == "INTERNAL_SERVER_ERROR"
        assert err.message == "Internal server error"

    def test_serialization_safe(self):
        err = ErrorResponse.from_unhandled_exception(RuntimeError("crash"))
        dumped = err.model_dump()
        assert "crash" not in str(dumped)
        assert "RuntimeError" not in str(dumped)


# ------------------------------------------------------------------
#  5. Router exception boundaries — real endpoints, no mocks
# ------------------------------------------------------------------

class TestRouterExceptionBoundaries:
    """Verify that real router endpoints produce correct ErrorResponse
    shapes at key exception boundaries. No dependency overrides needed."""

    def _make_client(self):
        from fastapi.testclient import TestClient
        from backend.main import create_app
        return TestClient(create_app())

    def test_auth_me_without_token_returns_401(self):
        """GET /auth/me without Authorization header → 401 UNAUTHORIZED."""
        client = self._make_client()
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 401
        body = resp.json()
        assert body["code"] == "UNAUTHORIZED"
        assert body["message"] is not None
        assert body["message"] != ""

    def test_auth_register_missing_fields_returns_422(self):
        """POST /auth/register with empty body → 422 VALIDATION_ERROR."""
        client = self._make_client()
        resp = client.post("/api/v1/auth/register", json={})
        assert resp.status_code == 422
        body = resp.json()
        assert body["code"] == "VALIDATION_ERROR"
        assert body["message"] == "Validation failed"
        assert isinstance(body["details"], list)
        assert len(body["details"]) > 0
        for detail in body["details"]:
            assert "field" in detail
            assert "message" in detail

    def test_register_weak_password_returns_422(self):
        """POST /auth/register with short password → 422 VALIDATION_ERROR."""
        client = self._make_client()
        resp = client.post("/api/v1/auth/register", json={
            "username": "newuser",
            "email": "new@example.com",
            "password": "short",
        })
        assert resp.status_code == 422
        body = resp.json()
        assert body["code"] == "VALIDATION_ERROR"
        assert body["message"] == "Validation failed"
