"""Real Asana API client using httpx."""

from __future__ import annotations

import logging
import os
from typing import Any, Self

import httpx

logger = logging.getLogger(__name__)

ASANA_API_BASE = "https://app.asana.com/api/1.0"


class AsanaAPIError(Exception):
    """Raised when the Asana API returns an error."""

    def __init__(self, message: str, status_code: int = 0, data: dict[str, Any] | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.data = data or {}


class AsanaClient:
    """Async client for the Asana REST API.

    Uses httpx under the hood with Bearer authentication.
    """

    def __init__(self, token: str | None = None) -> None:
        self._token = (token or os.environ.get("ASANA_TOKEN", "")).strip()
        self._http: httpx.AsyncClient | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @property
    def _client(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(
                base_url=ASANA_API_BASE,
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
            "Accept": "application/json",
        }

    async def _request(
        self, method: str, path: str, **kwargs: Any
    ) -> dict[str, Any]:
        resp = await self._client.request(method, path, **kwargs)
        body: dict[str, Any] = resp.json()

        if resp.status_code != 200:
            raise AsanaAPIError(
                body.get("error", {}).get("message", resp.text),
                status_code=resp.status_code,
                data=body,
            )

        return body

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def create_task(
        self,
        name: str,
        project: str | None = None,
        notes: str | None = None,
        due_on: str | None = None,
        approvals: str | None = None,
        assignee: str | None = None,
    ) -> dict[str, Any]:
        """Create a new Asana task.

        Args:
            name: Task name.
            project: Project ID to add the task to.
            notes: Task description/notes.
            due_on: ISO 8601 date string (YYYY-MM-DD).
            approvals: "approved", "pending", or "blocked".
            assignee: User ID to assign the task to.

        Returns:
            Created task object from the Asana API.
        """
        body: dict[str, Any] = {"data": {"name": name}}
        if project:
            body["data"]["projects"] = [project]
        if notes:
            body["data"]["notes"] = notes
        if due_on:
            body["data"]["due_on"] = due_on
        if approvals:
            body["data"]["approval_status"] = approvals
        if assignee:
            body["data"]["assignee"] = assignee

        return await self._request("POST", "/tasks", json=body)

    async def update_task(
        self,
        task_id: str,
        name: str | None = None,
        notes: str | None = None,
        due_on: str | None = None,
        approval_status: str | None = None,
        assignee: str | None = None,
    ) -> dict[str, Any]:
        """Update an existing Asana task.

        Args:
            task_id: Task to update.
            name: New task name.
            notes: New description/notes.
            due_on: New due date.
            approval_status: "approved", "pending", or "blocked".
            assignee: New assignee user ID.

        Returns:
            Updated task object from the Asana API.
        """
        body: dict[str, Any] = {"data": {}}
        if name is not None:
            body["data"]["name"] = name
        if notes is not None:
            body["data"]["notes"] = notes
        if due_on is not None:
            body["data"]["due_on"] = due_on
        if approval_status is not None:
            body["data"]["approval_status"] = approval_status
        if assignee is not None:
            body["data"]["assignee"] = assignee

        return await self._request("PUT", f"/tasks/{task_id}", json=body)

    async def get_task(self, task_id: str) -> dict[str, Any]:
        """Get a single task by ID.

        Args:
            task_id: Task resource ID.

        Returns:
            Task object from the Asana API.
        """
        return await self._request("GET", f"/tasks/{task_id}")

    async def get_task_memberships(self, task_id: str) -> dict[str, Any]:
        """Get all projects a task belongs to.

        Args:
            task_id: Task resource ID.

        Returns:
            Memberships object from the Asana API.
        """
        return await self._request("GET", f"/tasks/{task_id}/memberships")

    async def create_story(
        self,
        task_id: str,
        text: str,
    ) -> dict[str, Any]:
        """Create a story (comment/note) on a task.

        Args:
            task_id: Task to add the story to.
            text: Story text content.

        Returns:
            Created story object from the Asana API.
        """
        return await self._request("POST", f"/stories/{task_id}", json={"data": {"text": text}})

    async def set_completion_status(
        self,
        task_id: str,
        completed: bool,
    ) -> dict[str, Any]:
        """Set a task's completion status.

        Args:
            task_id: Task to update.
            completed: Whether the task should be marked complete.

        Returns:
            Updated task object from the Asana API.
        """
        return await self.update_task(task_id=task_id, approval_status=None)

    async def get_all(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Paginate through all resources at an endpoint.

        Args:
            endpoint: API endpoint path (e.g. "/tasks").
            params: Query parameters.
            limit: Max items to fetch.

        Returns:
            Flat list of all fetched resource objects.
        """
        params = {**(params or {}), "limit": str(limit)}
        items: list[dict[str, Any]] = []
        offset: str | None = None

        while True:
            if offset:
                params["offset"] = offset
            resp = await self._request("GET", endpoint, params=params)
            data = resp.get("data", [])
            items.extend(data)
            next_offset = (
                resp.get("next_page", {}).get("offset")
                if resp.get("next_page")
                else None
            )
            if not next_offset:
                break
            offset = next_offset

        return items
