"""Integration tests for the real Browser MCP API client.

These tests require BROWSER_API_URL and BROWSER_API_KEY environment
variables. Without them they are automatically skipped for live tests.

Run manually with:

    export BROWSER_API_URL="https://your-browser-service"
    export BROWSER_API_KEY="your-key"
    pytest tests/integration/mcp/test_browser_real.py -v
"""

from __future__ import annotations

import os

import pytest

from backend.mcp.servers.browser.client import BrowserAPIError, BrowserClient


def _has_config() -> bool:
    url = os.environ.get("BROWSER_API_URL", "").strip()
    key = os.environ.get("BROWSER_API_KEY", "").strip()
    return bool(url and key)


browser_available = pytest.mark.skipif(
    not _has_config(),
    reason="BROWSER_API_URL/BROWSER_API_KEY not set — skipping live Browser API tests",
)


# ------------------------------------------------------------------
# Unit-style checks that don't need a live connection
# ------------------------------------------------------------------

def test_client_initialization_no_config():
    """Client should instantiate even without config (stub path)."""
    client = BrowserClient(api_url="", api_key="")
    assert not client.is_configured


def test_client_headers_structure():
    """Verify headers include Bearer auth when configured."""
    client = BrowserClient(api_url="https://example.com", api_key="test-key")
    assert client.is_configured
    assert "Authorization" in client._headers
    assert client._headers["Authorization"] == "Bearer test-key"
    assert client._headers["Accept"] == "application/json"


@pytest.mark.asyncio
async def test_empty_config_early_rejection():
    """An unconfigured client should fail on any network call."""
    import httpx

    client = BrowserClient(api_url="", api_key="")
    with pytest.raises((BrowserAPIError, httpx.UnsupportedProtocol)):
        await client.search(query="test")


# ------------------------------------------------------------------
# Tool-layer stub tests (work without config)
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_stub():
    """Search via the tool layer — stub path when no config."""
    from backend.mcp.servers.browser.server import BrowserMCPServer

    server = BrowserMCPServer()
    tool = server._create_tool("search")
    result = await tool.execute(query="AI news")

    assert result["success"] is True
    assert result["data"]["query"] == "AI news"
    assert result["data"]["results"] == []


@pytest.mark.asyncio
async def test_fetch_stub():
    """Fetch via the tool layer — stub path when no config."""
    from backend.mcp.servers.browser.server import BrowserMCPServer

    server = BrowserMCPServer()
    tool = server._create_tool("fetch")
    result = await tool.execute(url="https://example.com")

    assert result["success"] is True
    assert result["data"]["url"] == "https://example.com"
    assert "<html>" in result["data"]["content"]


@pytest.mark.asyncio
async def test_extract_stub():
    """Extract via the tool layer — stub path when no config."""
    from backend.mcp.servers.browser.server import BrowserMCPServer

    server = BrowserMCPServer()
    tool = server._create_tool("extract")
    result = await tool.execute(url="https://example.com")

    assert result["success"] is True
    assert result["data"]["url"] == "https://example.com"
    assert result["data"]["extracted"] is True


# ------------------------------------------------------------------
# Live integration tests — require real credentials
# ------------------------------------------------------------------

@browser_available
@pytest.mark.asyncio
async def test_search_live():
    """Perform a real search via the tool layer."""
    from backend.mcp.servers.browser.server import BrowserMCPServer

    server = BrowserMCPServer()
    tool = server._create_tool("search")
    result = await tool.execute(query="test", max_results=3)

    assert result["success"] is True
    assert isinstance(result["data"]["results"], list)
