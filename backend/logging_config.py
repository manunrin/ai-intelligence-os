"""Structured JSON logging configuration."""

from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime, timezone


class RequestIDFilter(logging.Filter):
    """Automatically inject request_id into every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        from .context_vars import request_id as _ctx

        record.request_id = _ctx.get() or "unknown"
        return True


class JSONFormatter(logging.Formatter):
    """Format log records as JSON for log aggregation systems."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "unknown"),
        }
        if hasattr(record, "duration_ms") and record.duration_ms is not None:
            log_entry["duration_ms"] = round(record.duration_ms, 2)
        if hasattr(record, "method"):
            log_entry["method"] = record.method
        if hasattr(record, "path"):
            log_entry["path"] = record.path
        if hasattr(record, "status_code"):
            log_entry["status_code"] = record.status_code
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, default=str)


def setup_logging(level: str = "INFO") -> None:
    """Configure structured JSON logging for the application."""
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Attach request_id filter to every logger
    request_filter = RequestIDFilter()
    root_logger.addFilter(request_filter)
    for name in ("uvicorn", "fastapi"):
        logging.getLogger(name).addFilter(request_filter)

    # Silence noisy third-party loggers
    for logger_name in ("uvicorn.access", "sqlalchemy.engine", "httpx"):
        logging.getLogger(logger_name).setLevel("WARNING")


def make_request_log_record(
    method: str,
    path: str,
    status_code: int,
    elapsed_seconds: float,
    request_id: str,
) -> logging.LogRecord:
    """Create a structured LogRecord for HTTP request logging."""
    logger = logging.getLogger(__name__)
    record = logger.makeRecord(
        logger.name,
        logging.INFO,
        "",
        0,
        f"{method} {path} {status_code}",
        (),
        None,
    )
    record.request_id = request_id
    record.duration_ms = elapsed_seconds * 1000
    record.method = method
    record.path = path
    record.status_code = status_code
    return record
