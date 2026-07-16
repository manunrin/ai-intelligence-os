"""Real Browser API client using httpx.

Supports external browser services (Browserless, Playwright service,
search API gateways) via configurable base URL and API key.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Self

import httpx

logger = logging.getLogger(__name__)


class BrowserAPIError(Exception):
    """Raised when the Browser API returns an error."""

    def __init__(self, message: str, status_code: int = 0, data: dict[str, Any] | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.data = data or {}


class BrowserClient:
    """Async client for external browser/search APIs.

    Supports generic HTTP-based browser services without requiring
    a full headless browser in-process.
    """

    def __init__(
        self,
        api_url: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self._api_url = (api_url or os.environ.get("BROWSER_API_URL", "")).strip()
        self._api_key = (api_key or os.environ.get("BROWSER_API_KEY", "")).strip()
        self._http: httpx.AsyncClient | None = None

    @property
    def is_configured(self) -> bool:
        return bool(self._api_url and self._api_key)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @property
    def _client(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(
                base_url=self._api_url,
                headers=self._headers,
                timeout=httpx.Timeout(30.0),
            )
        return self._http

    async def aclose(self) -> None:
        if self._http is not None:
            await self._http.aclose()
            self._http = None

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.aclose()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @property
    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Accept": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    async def _request(
        self, method: str, path: str, **kwargs: Any
    ) -> dict[str, Any]:
        resp = await self._client.request(method, path, **kwargs)
        body: dict[str, Any] = resp.json()

        if resp.status_code >= 400:
            raise BrowserAPIError(
                body.get("error", body.get("message", resp.text)),
                status_code=resp.status_code,
                data=body,
            )

        return body

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def search(self, query: str, max_results: int = 5) -> dict[str, Any]:
        """Perform a web search.

        Args:
            query: Search query string.
            max_results: Maximum number of results to return.

        Returns:
            Search results with title, url, snippet.
        """
        result = await self._request(
            "POST", "/search",
            json={"data": {"query": query, "max_results": max_results}},
        )
        return result

    async def fetch(self, url: str) -> dict[str, Any]:
        """Fetch a URL and return its rendered HTML content.

        Args:
            url: URL to fetch.

        Returns:
            Fetched page with url, status_code, content.
        """
        result = await self._request(
            "POST", "/fetch",
            json={"data": {"url": url}},
        )
        return result

    async def extract(
        self, url: str, selector: str | None = None
    ) -> dict[str, Any]:
        """Extract structured content from a URL.

        Args:
            url: URL to extract from.
            selector: Optional CSS/XPath selector.

        Returns:
            Extracted content with url and text fields.
        """
        payload: dict[str, Any] = {"data": {"url": url}}
        if selector:
            payload["data"]["selector"] = selector

        result = await self._request("POST", "/extract", json=payload)
        return result
