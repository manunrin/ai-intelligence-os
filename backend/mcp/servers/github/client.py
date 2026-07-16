"""Real GitHub API client using httpx."""

from __future__ import annotations

import base64
import logging
import os
from typing import Any, Self

import httpx

logger = logging.getLogger(__name__)

GITHUB_API_BASE = "https://api.github.com"


class GitHubAPIError(Exception):
    """Raised when the GitHub API returns an error."""

    def __init__(self, message: str, status_code: int = 0, data: dict[str, Any] | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.data = data or {}


class GitHubClient:
    """Async client for the GitHub REST API v3.

    Uses httpx under the hood with Bearer authentication.
    """

    def __init__(self, token: str | None = None) -> None:
        self._token = (token or os.environ.get("GITHUB_TOKEN", "")).strip()
        self._owner = (os.environ.get("GITHUB_OWNER", "")).strip()
        self._repo = (os.environ.get("GITHUB_REPOSITORY", "")).strip()
        self._http: httpx.AsyncClient | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @property
    def _client(self) -> httpx.AsyncClient:
        if self._http is None:
            self._http = httpx.AsyncClient(
                base_url=GITHUB_API_BASE,
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
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def _request(
        self, method: str, path: str, **kwargs: Any
    ) -> dict[str, Any]:
        resp = await self._client.request(method, path, **kwargs)
        body: dict[str, Any] = resp.json()

        if resp.status_code >= 400:
            raise GitHubAPIError(
                body.get("message", resp.text),
                status_code=resp.status_code,
                data=body,
            )

        return body

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def create_issue(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str | None = None,
        labels: list[str] | None = None,
        assignee: str | None = None,
    ) -> dict[str, Any]:
        """Create a new issue in a repository.

        Args:
            owner: Repository owner (user or org).
            repo: Repository name.
            title: Issue title.
            body: Markdown description.
            labels: List of label strings.
            assignee: Username to assign.

        Returns:
            Created issue object from the GitHub API.
        """
        body_data: dict[str, Any] = {"title": title}
        if body:
            body_data["body"] = body
        if labels:
            body_data["labels"] = labels
        if assignee:
            body_data["assignees"] = [assignee]

        return await self._request(
            "POST", f"/repos/{owner}/{repo}/issues", json=body_data
        )

    async def get_repository(self, owner: str, repo: str) -> dict[str, Any]:
        """Get repository metadata.

        Args:
            owner: Repository owner.
            repo: Repository name.

        Returns:
            Repository object from the GitHub API.
        """
        return await self._request("GET", f"/repos/{owner}/{repo}")

    async def create_branch(
        self,
        owner: str,
        repo: str,
        branch: str,
        from_ref: str | None = None,
    ) -> dict[str, Any]:
        """Create a new branch from a base ref (tag, branch, or SHA).

        Args:
            owner: Repository owner.
            repo: Repository name.
            branch: New branch name.
            from_ref: Base reference (defaults to main).

        Returns:
            Reference object from the GitHub API.
        """
        ref_type = "branches"
        base = from_ref or "main"

        # Get SHA of the base ref
        sha_resp = await self._request(
            "GET", f"/repos/{owner}/{repo}/git/ref/refs/{ref_type}/{base}"
        )
        base_sha = sha_resp["object"]["sha"]

        # Create new branch pointing to that SHA
        return await self._request(
            "POST",
            f"/repos/{owner}/{repo}/git/refs",
            json={"ref": f"refs/heads/{branch}", "sha": base_sha},
        )

    async def commit_file(
        self,
        owner: str,
        repo: str,
        branch: str,
        file_path: str,
        content: str,
        message: str,
    ) -> dict[str, Any]:
        """Commit a file to a repository.

        Args:
            owner: Repository owner.
            repo: Repository name.
            branch: Target branch.
            file_path: Path within the repository.
            content: File content (plain text; will be base64-encoded).
            message: Commit message.

        Returns:
            Commit object from the GitHub API.
        """
        encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")

        # Check if file already exists to get its current SHA
        try:
            existing = await self._request(
                "GET", f"/repos/{owner}/{repo}/contents/{file_path}",
                params={"ref": branch},
            )
            sha = existing.get("sha")
        except GitHubAPIError:
            sha = None

        return await self._request(
            "PUT",
            f"/repos/{owner}/{repo}/contents/{file_path}",
            json={
                "data": {
                    "message": message,
                    "content": encoded,
                    "branch": branch,
                    **(
                        {"sha": sha}
                        if sha
                        else {}
                    ),
                }
            },
        )

    async def get_branch(
        self, owner: str, repo: str, branch: str
    ) -> dict[str, Any]:
        """Get branch protection info.

        Args:
            owner: Repository owner.
            repo: Repository name.
            branch: Branch name.

        Returns:
            Branch object from the GitHub API.
        """
        return await self._request(
            "GET", f"/repos/{owner}/{repo}/branches/{branch}"
        )

    async def get_content(
        self, owner: str, repo: str, path: str, ref: str = "HEAD"
    ) -> dict[str, Any]:
        """Get file/directory content from a repository.

        Args:
            owner: Repository owner.
            repo: Repository name.
            path: Path within the repository.
            ref: Git reference (branch, tag, or SHA).

        Returns:
            Content object from the GitHub API.
        """
        return await self._request(
            "GET",
            f"/repos/{owner}/{repo}/contents/{path}",
            params={"ref": ref},
        )
