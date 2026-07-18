"""Tests for security headers middleware."""

from __future__ import annotations

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from backend.routers.security_headers import SecurityHeadersMiddleware


def _make_client(force_https: bool = False):
    async def homepage(request: Request):
        return PlainTextResponse("ok")

    app = Starlette(routes=[Route("/", homepage)])
    app.add_middleware(SecurityHeadersMiddleware, force_https=force_https)
    return TestClient(app)


class TestSecurityHeadersMiddleware:
    def test_basic_security_headers(self):
        client = _make_client()
        response = client.get("/")
        assert response.status_code == 200
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["x-frame-options"] == "DENY"
        assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
        assert response.headers["cache-control"] == "no-store"
        assert (
            response.headers["permissions-policy"]
            == "camera=(), microphone=(), geolocation=()"
        )

    def test_csp_report_only_header_present(self):
        client = _make_client()
        response = client.get("/")
        csp = response.headers.get("content-security-policy-report-only", "")
        assert "default-src 'self'" in csp
        assert "script-src 'self'" in csp
        assert "style-src 'self' 'unsafe-inline'" in csp
        assert "img-src 'self' data: blob:" in csp
        assert "connect-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp
        assert "object-src 'none'" in csp

    def test_hsts_when_force_https(self):
        client = _make_client(force_https=True)
        response = client.get("/")
        assert (
            response.headers["strict-transport-security"]
            == "max-age=31536000; includeSubDomains"
        )

    def test_no_hsts_without_force_https(self):
        client = _make_client(force_https=False)
        response = client.get("/")
        assert "strict-transport-security" not in response.headers
