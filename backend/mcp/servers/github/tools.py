"""GitHub tool implementations — wired to the real GitHub API."""

from __future__ import annotations

import logging
import os
from typing import Any

from ...base import MCPTool
from ...schemas import MCPToolDefinition
from .client import GitHubAPIError, GitHubClient

logger = logging.getLogger(__name__)


def _has_token() -> bool:
    """Check whether a valid GitHub token is configured."""
    return len(os.environ.get("GITHUB_TOKEN", "").strip()) > 0


# ------------------------------------------------------------------
# Tool: create_issue
# ------------------------------------------------------------------

class GitHubCreateIssue(MCPTool):
    @property
    def tool_definition(self) -> MCPToolDefinition:
        return MCPToolDefinition(
            name="create_issue",
            description="Create a new GitHub issue in a repository.",
            parameters={
                "type": "object",
                "properties": {
                    "owner": {"type": "string"},
                    "repo": {"type": "string"},
                    "title": {"type": "string"},
                    "body": {"type": "string"},
                    "labels": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["owner", "repo", "title"],
            },
        )

    async def _execute_impl(self, **kwargs: Any) -> Any:
        owner = kwargs.get("owner", "")
        repo = kwargs.get("repo", "")
        title = kwargs.get("title", "")
        body = kwargs.get("body")
        labels = kwargs.get("labels")

        if not _has_token():
            logger.debug("GitHubCreateIssue: no token configured, returning stub")
            return {
                "number": 42,
                "title": title,
                "state": "open",
                "html_url": f"https://github.com/{owner}/{repo}/issues/42",
            }

        client = GitHubClient()
        try:
            issue = await client.create_issue(
                owner=owner, repo=repo, title=title,
                body=body, labels=labels,
            )
            return {
                "number": issue.get("number"),
                "title": title,
                "state": issue.get("state", "open"),
                "html_url": issue.get("html_url", ""),
                "raw": issue,
            }
        except GitHubAPIError as exc:
            logger.warning("GitHub create_issue failed: %s", exc)
            return {
                "number": 0,
                "title": title,
                "state": "error",
                "html_url": "",
                "error": str(exc),
            }


# ------------------------------------------------------------------
# Tool: get_repository
# ------------------------------------------------------------------

class GitHubGetRepository(MCPTool):
    @property
    def tool_definition(self) -> MCPToolDefinition:
        return MCPToolDefinition(
            name="get_repository",
            description="Get metadata about a GitHub repository.",
            parameters={
                "type": "object",
                "properties": {
                    "owner": {"type": "string"},
                    "repo": {"type": "string"},
                },
                "required": ["owner", "repo"],
            },
        )

    async def _execute_impl(self, **kwargs: Any) -> Any:
        owner = kwargs.get("owner", "")
        repo = kwargs.get("repo", "")

        if not _has_token():
            logger.debug("GitHubGetRepository: no token configured, returning stub")
            return {
                "full_name": f"{owner}/{repo}",
                "description": "Mock repository",
                "stargazers_count": 0,
                "forks_count": 0,
                "default_branch": "main",
            }

        client = GitHubClient()
        try:
            repo_data = await client.get_repository(owner=owner, repo=repo)
            return {
                "full_name": repo_data.get("full_name", f"{owner}/{repo}"),
                "description": repo_data.get("description", ""),
                "stargazers_count": repo_data.get("stargazers_count", 0),
                "forks_count": repo_data.get("forks_count", 0),
                "default_branch": repo_data.get("default_branch", "main"),
                "raw": repo_data,
            }
        except GitHubAPIError as exc:
            logger.warning("GitHub get_repository failed: %s", exc)
            return {
                "full_name": f"{owner}/{repo}",
                "description": "Error fetching repository",
                "stargazers_count": 0,
                "forks_count": 0,
                "default_branch": "main",
                "error": str(exc),
            }


# ------------------------------------------------------------------
# Tool: create_branch
# ------------------------------------------------------------------

class GitHubCreateBranch(MCPTool):
    @property
    def tool_definition(self) -> MCPToolDefinition:
        return MCPToolDefinition(
            name="create_branch",
            description="Create a new branch from a base ref.",
            parameters={
                "type": "object",
                "properties": {
                    "owner": {"type": "string"},
                    "repo": {"type": "string"},
                    "branch": {"type": "string"},
                    "from_ref": {"type": "string"},
                },
                "required": ["owner", "repo", "branch"],
            },
        )

    async def _execute_impl(self, **kwargs: Any) -> Any:
        owner = kwargs.get("owner", "")
        repo = kwargs.get("repo", "")
        branch = kwargs.get("branch", "")
        from_ref = kwargs.get("from_ref")

        if not _has_token():
            logger.debug("GitHubCreateBranch: no token configured, returning stub")
            return {
                "ref": f"refs/heads/{branch}",
                "created": True,
            }

        client = GitHubClient()
        try:
            result = await client.create_branch(
                owner=owner, repo=repo, branch=branch, from_ref=from_ref,
            )
            return {
                "ref": result.get("ref", f"refs/heads/{branch}"),
                "created": True,
                "raw": result,
            }
        except GitHubAPIError as exc:
            logger.warning("GitHub create_branch failed: %s", exc)
            return {
                "ref": f"refs/heads/{branch}",
                "created": False,
                "error": str(exc),
            }


# ------------------------------------------------------------------
# Tool: commit_file
# ------------------------------------------------------------------

class GitHubCommitFile(MCPTool):
    @property
    def tool_definition(self) -> MCPToolDefinition:
        return MCPToolDefinition(
            name="commit_file",
            description="Commit a file to a GitHub repository.",
            parameters={
                "type": "object",
                "properties": {
                    "owner": {"type": "string"},
                    "repo": {"type": "string"},
                    "branch": {"type": "string"},
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                    "message": {"type": "string"},
                },
                "required": ["owner", "repo", "branch", "path", "content", "message"],
            },
        )

    async def _execute_impl(self, **kwargs: Any) -> Any:
        owner = kwargs.get("owner", "")
        repo = kwargs.get("repo", "")
        branch = kwargs.get("branch", "")
        file_path = kwargs.get("path", "")
        content = kwargs.get("content", "")
        message = kwargs.get("message", "")

        if not _has_token():
            logger.debug("GitHubCommitFile: no token configured, returning stub")
            return {
                "sha": "mock-commit-sha",
                "file_path": file_path,
                "committed": True,
            }

        client = GitHubClient()
        try:
            result = await client.commit_file(
                owner=owner, repo=repo, branch=branch,
                file_path=file_path, content=content, message=message,
            )
            commit = result.get("commit", {})
            return {
                "sha": commit.get("sha", ""),
                "file_path": file_path,
                "committed": True,
                "raw": result,
            }
        except GitHubAPIError as exc:
            logger.warning("GitHub commit_file failed: %s", exc)
            return {
                "sha": "",
                "file_path": file_path,
                "committed": False,
                "error": str(exc),
            }
