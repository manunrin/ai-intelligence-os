"""Tests for structured JSON logging and request ID filter."""

from __future__ import annotations

import json
import logging
import sys
import uuid

import pytest


class TestRequestIDFilter:
    """Test that RequestIDFilter injects request_id from context vars."""

    def test_filter_injects_request_id(self):
        """RequestIDFilter sets record.request_id from context var."""
        from backend.context_vars import request_id as _ctx
        from backend.logging_config import RequestIDFilter

        _ctx.set("test-req-123")
        f = RequestIDFilter()

        logger = logging.getLogger(__name__)
        record = logger.makeRecord(
            logger.name, logging.INFO, "", 0, "test message", (), None,
        )
        assert not hasattr(record, "request_id")

        f.filter(record)
        assert record.request_id == "test-req-123"

    def test_filter_defaults_to_unknown(self):
        """When no context var is set, defaults to 'unknown'."""
        from backend.context_vars import request_id as _ctx
        from backend.logging_config import RequestIDFilter

        _ctx.set(None)
        f = RequestIDFilter()

        logger = logging.getLogger(__name__)
        record = logger.makeRecord(
            logger.name, logging.INFO, "", 0, "test", (), None,
        )
        f.filter(record)
        assert record.request_id == "unknown"


class TestJSONFormatter:
    """Test JSON log output format."""

    def test_basic_fields(self):
        """JSONFormatter outputs timestamp, level, logger, message, request_id."""
        from backend.logging_config import JSONFormatter

        fmt = JSONFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="hello world",
            args=(),
            exc_info=None,
        )
        record.request_id = "abc-123"
        output = fmt.format(record)
        parsed = json.loads(output)

        assert parsed["message"] == "hello world"
        assert parsed["level"] == "INFO"
        assert parsed["logger"] == "test.logger"
        assert parsed["request_id"] == "abc-123"
        assert "timestamp" in parsed

    def test_extra_fields(self):
        """JSONFormatter includes method, path, status_code when present."""
        from backend.logging_config import JSONFormatter

        fmt = JSONFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="GET /api", args=(), exc_info=None,
        )
        record.method = "GET"
        record.path = "/api/v1/articles"
        record.status_code = 200
        record.duration_ms = 45.678

        output = fmt.format(record)
        parsed = json.loads(output)

        assert parsed["method"] == "GET"
        assert parsed["path"] == "/api/v1/articles"
        assert parsed["status_code"] == 200
        assert parsed["duration_ms"] == 45.68  # rounded to 2 decimals

    def test_exception_included(self):
        """JSONFormatter includes exception details when exc_info is set."""
        from backend.logging_config import JSONFormatter

        fmt = JSONFormatter()
        try:
            raise ValueError("test error")
        except ValueError as exc:
            record = logging.LogRecord(
                name="test", level=logging.ERROR, pathname="", lineno=0,
                msg="error occurred", args=(), exc_info=sys.exc_info(),
            )
            output = fmt.format(record)
            parsed = json.loads(output)
            assert "exception" in parsed
            assert "ValueError: test error" in parsed["exception"]
