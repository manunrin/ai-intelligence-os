"""Security headers middleware for API responses."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add standard security headers to every API response."""

    def __init__(self, app, force_https: bool = False) -> None:
        super().__init__(app)
        self.force_https = force_https

    def _get_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Cache-Control": "no-store",
            "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
        }
        if self.force_https:
            headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        return headers

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)
        for key, value in self._get_headers().items():
            response.headers[key] = value
        return response
