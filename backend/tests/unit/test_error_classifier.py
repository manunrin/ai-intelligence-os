"""Unit tests for error_classifier.py."""

from __future__ import annotations

import pytest

from backend.workflows.error_classifier import ErrorCategory, classify_error


class TestClassifyErrorTransient:
    """Transient errors should trigger retries."""

    @pytest.mark.parametrize("message", [
        "TimeoutError: connection timed out",
        "ConnectionRefusedError: connection refused",
        "ConnectionResetError: connection reset",
        "error: timed out waiting for response",
        "rate limit exceeded",
        "throttled by server",
        "HTTP 503 Service Unavailable",
        "HTTP 504 Gateway Timeout",
        "service unavailable at endpoint",
        "gateway timeout on request",
    ])
    def test_transient_errors(self, message):
        assert classify_error(message) == ErrorCategory.TRANSIENT


class TestClassifyErrorPermanent:
    """Permanent errors should NOT be retried."""

    @pytest.mark.parametrize("message", [
        "ValueError: invalid input",
        "KeyError: missing key",
        "TypeError: expected str not int",
        "AttributeError: no such attribute",
        "AuthenticationError: invalid API key",
        "PermissionDenied: access denied",
        "invalid parameter provided",
        "not found: resource does not exist",
        "HTTP 400 Bad Request",
        "HTTP 401 Unauthorized",
        "HTTP 403 Forbidden",
        "HTTP 404 Not Found",
    ])
    def test_permanent_errors(self, message):
        assert classify_error(message) == ErrorCategory.PERMANENT


class TestClassifyErrorFallback:
    """Unknown errors default to PERMANENT (fail-safe)."""

    @pytest.mark.parametrize("message", [
        "some unknown error occurred",
        "random exception",
        "",
        "normal processing error",
    ])
    def test_unknown_defaults_to_permanent(self, message):
        assert classify_error(message) == ErrorCategory.PERMANENT


class TestClassifyErrorPriority:
    """Permanent patterns take priority over transient patterns."""

    def test_401_overrides_timeout(self):
        # "401" is permanent, "timeout" is transient — permanent wins
        assert classify_error("401 authentication timeout") == ErrorCategory.PERMANENT

    def test_invalid_overrides_connection(self):
        # "invalid" is permanent, "connection" is transient — permanent wins
        assert classify_error("invalid connection parameters") == ErrorCategory.PERMANENT
