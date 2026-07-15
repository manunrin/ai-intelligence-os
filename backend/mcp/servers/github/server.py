"""GitHub MCP server — exposes repository operations as discoverable tools."""

from __future__ import annotations

from typing import Type

from ...base import MCPServerBase, MCPTool
from ...schemas import MCPToolDefinition
from .tools import (
    GitHubCommitFile,
    GitHubCreateBranch,
    GitHubCreateIssue,
    GitHubGetRepository,
)


class GitHubMCPServer(MCPServerBase):
    """MCP server for the GitHub API.

    Exposes tools for issue management, branch operations, and file commits.
    """

    name = "github"
    version = "0.1.0"
    description = "GitHub integration — issues, repositories, branches, commits"

    _tools: dict[str, Type[MCPTool]] = {
        "create_issue": GitHubCreateIssue,
        "get_repository": GitHubGetRepository,
        "create_branch": GitHubCreateBranch,
        "commit_file": GitHubCommitFile,
    }

    def available_tools(self) -> list[MCPToolDefinition]:
        return [
            MCPToolDefinition(
                name="create_issue",
                description="Create a new GitHub issue in a repository.",
                parameters={
                    "type": "object",
                    "properties": {
                        "owner": {
                            "type": "string",
                            "description": "Repository owner (org or user).",
                        },
                        "repo": {
                            "type": "string",
                            "description": "Repository name.",
                        },
                        "title": {
                            "type": "string",
                            "description": "Issue title.",
                        },
                        "body": {
                            "type": "string",
                            "description": "Issue body (Markdown).",
                        },
                        "labels": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Labels to apply.",
                        },
                    },
                    "required": ["owner", "repo", "title"],
                },
            ),
            MCPToolDefinition(
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
            ),
            MCPToolDefinition(
                name="create_branch",
                description="Create a new branch from a base ref.",
                parameters={
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string"},
                        "repo": {"type": "string"},
                        "branch": {
                            "type": "string",
                            "description": "New branch name.",
                        },
                        "from_ref": {
                            "type": "string",
                            "description": "Base branch or SHA to branch from.",
                        },
                    },
                    "required": ["owner", "repo", "branch"],
                },
            ),
            MCPToolDefinition(
                name="commit_file",
                description="Commit a file to a GitHub repository.",
                parameters={
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string"},
                        "repo": {"type": "string"},
                        "branch": {"type": "string"},
                        "path": {
                            "type": "string",
                            "description": "File path in the repo.",
                        },
                        "content": {
                            "type": "string",
                            "description": "File content (base64 or plain text).",
                        },
                        "message": {
                            "type": "string",
                            "description": "Commit message.",
                        },
                    },
                    "required": ["owner", "repo", "branch", "path", "content", "message"],
                },
            ),
        ]

    def _create_tool(self, tool_name: str) -> MCPTool | None:
        cls = self._tools.get(tool_name)
        if cls is None:
            return None
        instance = cls()
        instance.server = self
        return instance
