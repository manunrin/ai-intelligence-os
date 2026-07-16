"""API router package."""

from .api import api_router, register_exception_handlers, setup_middleware

__all__ = ["api_router", "register_exception_handlers", "setup_middleware"]
