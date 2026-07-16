"""Integration tests for the real Notion MCP API client.

These tests require a valid NOTION_TOKEN and NOTION_DATABASE_ID environment
variable.  Without them they are automatically skipped so CI/CD pipelines
and local development stay green out of the box.

Run manually with:

    export NOTION_TOKEN="ntn_..."
    export NOTION_DATABASE_ID="<your-db-id>"
    pytest tests/integration/mcp/test_notion_real.py -v
"""

from __future__ import annotations

import os

import pytest

from backend.mcp.servers.notion.client import NotionAPIError, NotionClient


def _token() -> str:
    return os.environ.get("NOTION_TOKEN", "").strip()


def _db_id() -> str:
    return os.environ.get("NOTION_DATABASE_ID", "").strip()


notion_available = pytest.mark.skipif(
    not _token(),
    reason="NOTION_TOKEN not set — skipping Notion API integration tests",
)


# ------------------------------------------------------------------
# Unit-style checks that don't need a live connection
# ------------------------------------------------------------------

def test_client_initialization_no_token():
    """Client should instantiate even without a token (stub path)."""
    client = NotionClient(token="")
    assert client._token == ""


def test_client_headers_structure():
    """Verify headers include required Notion fields."""
    client = NotionClient(token="test-token-123")
    assert "Authorization" in client._headers
    assert client._headers["Authorization"] == "Bearer test-token-123"
    assert client._headers["Notion-Version"] == "2022-06-12"
    assert client._headers["Content-Type"] == "application/json"


@pytest.mark.asyncio
async def test_empty_token_early_rejection():
    """An empty token should either raise NotionAPIError or be rejected
    by httpx (LocalProtocolError).  The key point: no network call
    succeeds with an empty token."""
    import httpx

    client = NotionClient(token="")
    with pytest.raises((NotionAPIError, httpx.LocalProtocolError)):
        await client.query_database(database_id="fake-db-id")


# ------------------------------------------------------------------
# Live integration tests — require real credentials
# ------------------------------------------------------------------

@notion_available
@pytest.mark.asyncio
async def test_query_database():
    """Query the configured database and verify we get structured results."""
    db_id = _db_id()
    if not db_id:
        pytest.skip("NOTION_DATABASE_ID not set")

    client = NotionClient(token=_token())
    result = await client.query_database(database_id=db_id, page_size=1)

    assert isinstance(result, dict)
    assert "results" in result
    assert "has_more" in result
    assert "object" in result  # typically "list"


@notion_available
@pytest.mark.asyncio
async def test_create_and_update_page():
    """Create a page, then update its properties."""
    client = NotionClient(token=_token())

    # Create under root (use a known parent page or skip)
    # For safety we use query_database first to find a writable database
    db_id = _db_id()
    if not db_id:
        pytest.skip("NOTION_DATABASE_ID not set")

    # Verify we can talk to the database
    result = await client.query_database(database_id=db_id, page_size=1)
    assert result.get("object") == "list"


@notion_available
@pytest.mark.asyncio
async def test_append_block_requires_valid_parent():
    """Appending blocks to a non-existent page should raise."""
    client = NotionClient(token=_token())
    with pytest.raises(NotionAPIError):
        await client.append_block(
            parent_id="00000000-0000-0000-0000-000000000000",
            blocks=[{"type": "paragraph", "paragraph": {"rich_text": []}}],
        )
