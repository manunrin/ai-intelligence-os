"""GitHub tool implementations (mocked for Phase 5-A)."""

from __future__ import annotations

from typing import Any

from ...base import MCPTool
from ...schemas import MCPToolDefinition


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
        return {
            "number": 42,
            "title": kwargs.get("title", ""),
            "state": "open",
            "html_url": f"https://github.com/{kwargs.get('owner', '')}/{kwargs.get('repo', '')}/issues/42",
        }


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
        return {
            "full_name": f"{kwargs.get('owner', '')}/{kwargs.get('repo', '')}",
            "description": "Mock repository",
            "stargazers_count": 0,
            "forks_count": 0,
            "default_branch": "main",
        }


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
        return {
            "ref": f"refs/heads/{kwargs.get('branch', '')}",
            "created": True,
        }


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
        return {
            "sha": "mock-commit-sha",
            "file_path": kwargs.get("path", ""),
            "committed": True,
        }
