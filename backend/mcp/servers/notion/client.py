"""Real Notion API client using httpx."""

from __future__ import annotations

import logging
import os
from typing import Any, Self

import httpx

logger = logging.getLogger(__name__)

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-12"


class NotionAPIError(Exception):
    """Raised when the Notion API returns an error."""

    def __init__(self, message: str, status_code: int = 0, code: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code


class NotionClient:
    """Async client for the Notion REST API.

    Uses httpx under the hood with proper Authorization and
    Notion-Version headers baked in.
    """

    def __init__(self, token: str | None = None) -> None:
        self._token = (token or os.environ.get("NOTION_TOKEN", "")).strip()
        self._http: httpx.AsyncClient | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @property
    def _client(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(
                base_url=NOTION_API_BASE,
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
        return {
            "Authorization": f"Bearer {self._token}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        }

    async def _request(
        self, method: str, path: str, **kwargs: Any
    ) -> dict[str, Any]:
        resp = await self._client.request(method, path, **kwargs)
        body: dict[str, Any] = resp.json()

        if resp.status_code != 200:
            code = body.get("code", "")
            message = body.get("message", resp.text)
            raise NotionAPIError(message, status_code=resp.status_code, code=code)

        if body.get("object") == "error":
            raise NotionAPIError(
                body.get("message", "Unknown Notion error"),
                code=body.get("type"),
            )

        return body

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def create_page(
        self,
        parent_id: str,
        title: str = "",
        properties: dict[str, Any] | None = None,
        content: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Create a new Notion page.

        Args:
            parent_id: Parent page or database ID.
            title: Page title (becomes first paragraph block).
            properties: Explicit Notion property dict (alternative to title).
            content: List of block objects to populate the page with.

        Returns:
            Full page object from the Notion API.
        """
        if properties is not None:
            props = properties
        elif title:
            props = {"title": [{"type": "text", "text": {"content": title}}]}
        else:
            props = {"title": [{"type": "text", "text": {"content": ""}}]}

        body: dict[str, Any] = {
            "parent": {"page_id": parent_id} if len(parent_id) <= 32 else {"database_id": parent_id},
            "properties": props,
        }

        if content:
            body["children"] = content

        return await self._request("POST", "/pages", json=body)

    async def update_page(
        self,
        page_id: str,
        properties: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Update an existing Notion page.

        Args:
            page_id: Page to update.
            properties: Property patch to apply.

        Returns:
            Updated page object from the Notion API.
        """
        body: dict[str, Any] = {}
        if properties:
            body["properties"] = properties

        return await self._request("PATCH", f"/pages/{page_id}", json=body)

    async def query_database(
        self,
        database_id: str,
        filter: dict[str, Any] | None = None,
        sorts: list[dict[str, Any]] | None = None,
        page_size: int | None = None,
        start_cursor: str | None = None,
    ) -> dict[str, Any]:
        """Query a Notion database.

        Args:
            database_id: Database to query.
            filter: Notion filter JSON object.
            sorts: Notion sort specification array.
            page_size: Number of results per page.
            start_cursor: Pagination cursor.

        Returns:
            Paginated result set from the Notion API.
        """
        body: dict[str, Any] = {}
        if filter is not None:
            body["filter"] = filter
        if sorts is not None:
            body["sorts"] = sorts
        if page_size is not None:
            body["page_size"] = page_size
        if start_cursor is not None:
            body["start_cursor"] = start_cursor

        return await self._request(
            "POST", f"/databases/{database_id}/query", json=body
        )

    async def append_block(
        self,
        parent_id: str,
        blocks: list[dict[str, Any]],
        after: str | None = None,
    ) -> dict[str, Any]:
        """Append blocks to an existing page.

        Args:
            parent_id: Page ID to append blocks to.
            blocks: Array of block objects.
            after: Optional block ID to append after (for inserting mid-page).

        Returns:
            Updated parent block object from the Notion API.
        """
        body: dict[str, Any] = {"children": blocks}
        if after:
            body["after"] = after

        return await self._request(
            "PATCH", f"/blocks/{parent_id}/children", json=body
        )
