"""Error classification for retry logic.

Classifies error messages into TRANSIENT (retryable) or PERMANENT (not retryable).
This is a heuristic MVP — future versions should classify typed exceptions directly
and integrate with LiteLLM's exception hierarchy for provider-level accuracy.

Retry semantics depend on LangGraph checkpoint semantics: retries only help when
downstream tools are idempotent. Non-idempotent side-effect tools may produce
duplicate effects across retries.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class ErrorCategory(str):
    TRANSIENT = "transient"
    PERMANENT = "permanent"


# Permanent error patterns checked FIRST to avoid false positives on transient matching.
_PERMANENT_PATTERNS = [
    "valueerror",
    "keyerror",
    "typeerror",
    "attributeerror",
    "authenticationerror",
    "permissiondenied",
    "invalid",
    "not found",
    "400",
    "401",
    "403",
    "404",
]

# Transient error patterns checked after permanent (permanent takes priority).
_TRANSIENT_PATTERNS = [
    "timeout",
    "timed out",
    "connection refused",
    "connection reset",
    "connection error",
    "rate limit",
    "throttl",
    "503",
    "504",
    "service unavailable",
    "gateway timeout",
]


def classify_error(error_message: str) -> ErrorCategory:
    """Classify an error by its message string.

    Checks permanent patterns first, then transient patterns.
    Unknown errors default to PERMANENT (fail-safe).

    Args:
        error_message: The error message string from a failed RunResult
            or a caught exception.

    Returns:
        ErrorCategory.TRANSIENT if the error is likely recoverable.
        ErrorCategory.PERMANENT otherwise.
    """
    lower = error_message.lower()

    # Check permanent patterns first (higher priority).
    for pattern in _PERMANENT_PATTERNS:
        if pattern in lower:
            return ErrorCategory.PERMANENT

    # Check transient patterns.
    for pattern in _TRANSIENT_PATTERNS:
        if pattern in lower:
            return ErrorCategory.TRANSIENT

    # Default: fail-safe — do not retry unknown errors.
    return ErrorCategory.PERMANENT
