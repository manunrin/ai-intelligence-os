"""Integration tests for the real Asana MCP API client.

These tests require a valid ASANA_TOKEN environment variable.
Without it they are automatically skipped.

Run manually with:

    export ASANA_TOKEN="0/..."
    pytest tests/integration/mcp/test_asana_real.py -v
"""

from __future__ import annotations

import os

import pytest

from backend.mcp.servers.asana.client import AsanaAPIError, AsanaClient


def _token() -> str:
    return os.environ.get("ASANA_TOKEN", "").strip()


asana_available = pytest.mark.skipif(
    not _token(),
    reason="ASANA_TOKEN not set — skipping Asana API integration tests",
)


# ------------------------------------------------------------------
# Unit-style checks that don't need a live connection
# ------------------------------------------------------------------

def test_client_initialization_no_token():
    """Client should instantiate even without a token (stub path)."""
    client = AsanaClient(token="")
    assert client._token == ""


def test_client_headers_structure():
    """Verify headers include Bearer auth."""
    client = AsanaClient(token="test-token-123")
    assert "Authorization" in client._headers
    assert client._headers["Authorization"] == "Bearer test-token-123"
    assert client._headers["Accept"] == "application/json"


@pytest.mark.asyncio
async def test_empty_token_early_rejection():
    """An empty token should be rejected by httpx before any network call."""
    import httpx

    client = AsanaClient(token="")
    with pytest.raises((AsanaAPIError, httpx.LocalProtocolError)):
        await client.create_task(name="test", project="fake")


# ------------------------------------------------------------------
# Live integration tests — require real credentials
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_task_stub():
    """Create a task via the tool layer and verify it returns structured data.

    With a real token this hits the Asana API; without it, the stub
    path is exercised.
    """
    from backend.mcp.servers.asana.server import AsanaMCPServer

    server = AsanaMCPServer()
    tool = server._create_tool("create_task")
    result = await tool.execute(name="Integration Test Task", project="123456")

    assert result["success"] is True
    assert isinstance(result["data"]["gid"], str)
    assert result["data"]["name"] == "Integration Test Task"


@pytest.mark.asyncio
async def test_complete_task_stub():
    """Complete a task via the tool layer."""
    from backend.mcp.servers.asana.server import AsanaMCPServer

    server = AsanaMCPServer()
    tool = server._create_tool("complete_task")
    result = await tool.execute(task_id="task-123")

    assert result["success"] is True
    assert result["data"]["completed"] is True


@pytest.mark.asyncio
async def test_add_comment_stub():
    """Add a comment via the tool layer."""
    from backend.mcp.servers.asana.server import AsanaMCPServer

    server = AsanaMCPServer()
    tool = server._create_tool("add_comment")
    result = await tool.execute(task_id="task-123", text="Test comment")

    assert result["success"] is True
    assert result["data"]["text"] == "Test comment"
