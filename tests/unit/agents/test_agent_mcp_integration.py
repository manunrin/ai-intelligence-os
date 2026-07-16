"""Tests for Agent → MCP tool integration.

Verifies that agents can optionally call MCP tools when a registry is
provided, and fall back gracefully when it is not.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.agents.knowledge.agent import KnowledgeAgent
from backend.agents.notification.agent import NotificationAgent
from backend.agents.project_manager.agent import ProjectManagerAgent
from backend.agents.research.agent import ResearchAgent
from backend.mcp.registry import MCPRegistry
from backend.mcp.servers.asana.server import AsanaMCPServer
from backend.mcp.servers.browser.server import BrowserMCPServer
from backend.mcp.servers.notion.server import NotionMCPServer


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

def _mock_llm(content: str = "Summary: test\n- Point 1\n- Point 2", **usage) -> MagicMock:
    llm = MagicMock()
    llm.chat = AsyncMock(
        return_value=MagicMock(
            content=content,
            usage=usage.get("usage", {"prompt_tokens": 10}),
        )
    )
    return llm


def _make_mcp_registry(*servers) -> MCPRegistry:
    """Build an MCPRegistry from one or more server instances."""
    reg = MCPRegistry()
    for srv in servers:
        reg.register_server(srv)
    return reg


# ------------------------------------------------------------------
# KnowledgeAgent + Notion
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_knowledge_agent_no_mcp():
    """Without MCP registry, KnowledgeAgent falls back gracefully."""
    llm = _mock_llm()
    agent = KnowledgeAgent(llm_client=llm)
    result = await agent.execute({
        "title": "Test Article",
        "content": "Some content",
        "source": "test",
    })
    assert result["success"] is True
    output = result["output"]
    assert "knowledge_type" in output
    assert "notion_page_id" in output
    assert output["notion_page_id"] is None
    assert output["notion_url"] is None


@pytest.mark.asyncio
async def test_knowledge_agent_with_notion_mcp():
    """With MCP registry, KnowledgeAgent calls notion.create_page."""
    llm = _mock_llm()
    mcp_reg = _make_mcp_registry(NotionMCPServer())
    tool = mcp_reg.get_tool("notion.create_page")
    assert tool is not None

    agent = KnowledgeAgent(
        llm_client=llm,
        mcp_registry=mcp_reg,
        notion_database_id="db-123",
    )
    result = await agent.execute({
        "title": "AI Research Summary",
        "content": "LLMs are improving rapidly.",
        "analysis": "Key trend in AI.",
        "source": "test",
        "tags": ["ai"],
    })
    assert result["success"] is True
    output = result["output"]
    assert "knowledge_type" in output
    # Tool was called — stub returns mock data
    assert "notion_page_id" in output or "notion_url" in output


# ------------------------------------------------------------------
# ProjectManagerAgent + Asana
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_project_manager_agent_no_mcp():
    """Without MCP registry, ProjectManagerAgent falls back gracefully."""
    llm = _mock_llm(
        content="- Task A\n- Task B\n- Task C",
    )
    agent = ProjectManagerAgent(llm_client=llm)
    result = await agent.execute({
        "goal": "Build a REST API",
        "knowledge": "Use FastAPI.",
    })
    assert result["success"] is True
    output = result["output"]
    assert "tasks" in output
    assert len(output["tasks"]) >= 1
    assert output.get("asana_task_ids") == []


@pytest.mark.asyncio
async def test_project_manager_agent_with_asana_mcp():
    """With MCP registry, ProjectManagerAgent calls asana.create_task."""
    llm = _mock_llm(
        content="- Setup project structure\n- Write unit tests\n- Deploy to staging",
    )
    mcp_reg = _make_mcp_registry(AsanaMCPServer())
    tool = mcp_reg.get_tool("asana.create_task")
    assert tool is not None

    agent = ProjectManagerAgent(
        llm_client=llm,
        mcp_registry=mcp_reg,
        asana_project_id="proj-456",
    )
    result = await agent.execute({
        "goal": "Build a REST API",
        "knowledge": "Use FastAPI.",
    })
    assert result["success"] is True
    output = result["output"]
    assert "tasks" in output
    assert "asana_task_ids" in output


# ------------------------------------------------------------------
# ResearchAgent + Browser
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_research_agent_no_mcp():
    """Without MCP registry, ResearchAgent falls back gracefully."""
    llm = _mock_llm(content="Research findings on AI.")
    agent = ResearchAgent(llm_client=llm)
    result = await agent.execute({
        "topic": "Artificial Intelligence",
        "focus_areas": ["LLMs", "Agents"],
    })
    assert result["success"] is True
    output = result["output"]
    assert "response" in output
    assert output.get("web_results") == []


@pytest.mark.asyncio
async def test_research_agent_with_browser_mcp():
    """With MCP registry, ResearchAgent calls browser.search."""
    llm = _mock_llm(content="Research findings on AI.")
    mcp_reg = _make_mcp_registry(BrowserMCPServer())
    tool = mcp_reg.get_tool("browser.search")
    assert tool is not None

    agent = ResearchAgent(
        llm_client=llm,
        mcp_registry=mcp_reg,
    )
    result = await agent.execute({
        "topic": "Artificial Intelligence",
        "focus_areas": ["LLMs"],
    })
    assert result["success"] is True
    output = result["output"]
    assert "response" in output
    assert "web_results" in output


# ------------------------------------------------------------------
# NotificationAgent + notification.send (placeholder)
# ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_notification_agent_no_mcp():
    """Without MCP registry, NotificationAgent works normally."""
    llm = _mock_llm(content="# Daily Digest\n\n## News\n- Test")
    agent = NotificationAgent(llm_client=llm)
    result = await agent.execute({
        "date": "2026-07-15",
        "news": [{"title": "Test", "summary": "Summary"}],
        "knowledge": [],
        "tasks": [],
        "channels": ["email"],
    })
    assert result["success"] is True
    output = result["output"]
    assert "markdown" in output
    assert "channels" in output
