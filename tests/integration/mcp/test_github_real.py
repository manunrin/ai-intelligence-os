"""Integration tests for the real GitHub MCP API client.

These tests require a valid GITHUB_TOKEN environment variable.
Without it they are automatically skipped.

Run manually with:

    export GITHUB_TOKEN="ghp_..."
    pytest tests/integration/mcp/test_github_real.py -v
"""

from __future__ import annotations

import os

import pytest

from backend.mcp.servers.github.client import GitHubAPIError, GitHubClient


def _token() -> str:
    return os.environ.get("GITHUB_TOKEN", "").strip()


github_available = pytest.mark.skipif(
    not _token(),
    reason="GITHUB_TOKEN not set — skipping GitHub API integration tests",
)


# ------------------------------------------------------------------
# Unit-style checks that don't need a live connection
# ------------------------------------------------------------------

def test_client_initialization_no_token():
    """Client should instantiate even without a token (stub path)."""
    client = GitHubClient(token="")
    assert client._token == ""


def test_client_headers_structure():
    """Verify headers include Bearer auth and GitHub version."""
    client = GitHubClient(token="test-token-123")
    assert "Authorization" in client._headers
    assert client._headers["Authorization"] == "Bearer test-token-123"
    assert client._headers["Accept"] == "application/vnd.github.v3+json"
    assert client._headers["X-GitHub-Api-Version"] == "2022-11-28"


@pytest.mark.asyncio
async def test_empty_token_early_rejection():
    """An empty token should be rejected by httpx before any network call."""
    import httpx

    client = GitHubClient(token="")
    with pytest.raises((GitHubAPIError, httpx.LocalProtocolError)):
        await client.get_repository(owner="test", repo="test")


# ------------------------------------------------------------------
# Tool-layer stub tests (work without a token)
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_issue_stub():
    """Create issue via the tool layer — stub path when no token."""
    from backend.mcp.servers.github.server import GitHubMCPServer

    server = GitHubMCPServer()
    tool = server._create_tool("create_issue")
    result = await tool.execute(owner="user", repo="repo", title="Test Issue")

    assert result["success"] is True
    assert result["data"]["title"] == "Test Issue"
    assert result["data"]["state"] == "open"


@pytest.mark.asyncio
async def test_get_repository_stub():
    """Get repository via the tool layer — stub path when no token."""
    from backend.mcp.servers.github.server import GitHubMCPServer

    server = GitHubMCPServer()
    tool = server._create_tool("get_repository")
    result = await tool.execute(owner="user", repo="repo")

    assert result["success"] is True
    assert result["data"]["full_name"] == "user/repo"
    assert result["data"]["default_branch"] == "main"


@pytest.mark.asyncio
async def test_create_branch_stub():
    """Create branch via the tool layer — stub path when no token."""
    from backend.mcp.servers.github.server import GitHubMCPServer

    server = GitHubMCPServer()
    tool = server._create_tool("create_branch")
    result = await tool.execute(owner="user", repo="repo", branch="feature/test")

    assert result["success"] is True
    assert result["data"]["ref"] == "refs/heads/feature/test"
    assert result["data"]["created"] is True


@pytest.mark.asyncio
async def test_commit_file_stub():
    """Commit file via the tool layer — stub path when no token."""
    from backend.mcp.servers.github.server import GitHubMCPServer

    server = GitHubMCPServer()
    tool = server._create_tool("commit_file")
    result = await tool.execute(
        owner="user", repo="repo", branch="main",
        path="docs/test.md", content="# Hello", message="Add test doc",
    )

    assert result["success"] is True
    assert result["data"]["file_path"] == "docs/test.md"
    assert result["data"]["committed"] is True


# ------------------------------------------------------------------
# Live integration tests — require real credentials
# ------------------------------------------------------------------

@github_available
@pytest.mark.asyncio
async def test_get_repository_live():
    """Fetch a real repository metadata via the tool layer."""
    owner = os.environ.get("GITHUB_OWNER", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if not owner or not repo:
        pytest.skip("GITHUB_OWNER and/or GITHUB_REPOSITORY not set")

    from backend.mcp.servers.github.server import GitHubMCPServer

    server = GitHubMCPServer()
    tool = server._create_tool("get_repository")
    result = await tool.execute(owner=owner, repo=repo)

    assert result["success"] is True
    assert result["data"]["full_name"] == f"{owner}/{repo}"
    assert isinstance(result["data"]["stargazers_count"], int)
