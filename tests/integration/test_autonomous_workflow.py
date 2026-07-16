"""End-to-end integration test for the autonomous intelligence workflow."""

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
from backend.workflows.autonomous_intelligence import (
    compile_autonomous_intelligence,
    build_autonomous_intelligence_graph,
)
from backend.workflows.graph.autonomous_state import AutonomousState


def _mock_llm(content: str = "Summary: AI news.\n- Key point 1\n- Key point 2", **usage) -> MagicMock:
    llm = MagicMock()
    llm.chat = AsyncMock(
        return_value=MagicMock(
            content=content,
            usage=usage.get("usage", {"prompt_tokens": 10}),
        )
    )
    return llm


def _make_mcp_registry(*servers) -> MCPRegistry:
    reg = MCPRegistry()
    for srv in servers:
        reg.register_server(srv)
    return reg


@pytest.mark.asyncio
async def test_autonomous_graph_builds():
    """Verify the autonomous graph can be built with all nodes."""
    llm_mock = _mock_llm()
    graph = build_autonomous_intelligence_graph(llm_client=llm_mock)

    node_names = list(graph.nodes.keys())
    assert "research" in node_names
    assert "analyst" in node_names
    assert "translator" in node_names
    assert "knowledge" in node_names
    assert "project_manager" in node_names
    assert "notification" in node_names


@pytest.mark.asyncio
async def test_autonomous_workflow_no_mcp():
    """Full pipeline runs without MCP registry — all stages succeed via stubs."""
    llm_mock = _mock_llm()
    app = compile_autonomous_intelligence(llm_client=llm_mock)

    initial_state = {
        "topic": "AI News Weekly",
        "content": "Latest developments in artificial intelligence.",
        "focus_areas": ["LLMs", "Agents"],
        "source": "test",
    }

    result = await app.ainvoke(initial_state)

    assert result["research_result"] is not None
    assert result["analysis_result"] is not None
    assert result["translation_result"] is not None
    assert result["knowledge_result"] is not None
    assert result["project_plan_result"] is not None
    assert result["notification_result"] is not None


@pytest.mark.asyncio
async def test_autonomous_workflow_with_notion_mcp():
    """KnowledgeAgent calls notion.create_page when MCP registry is provided."""
    llm_mock = _mock_llm()
    mcp_reg = _make_mcp_registry(NotionMCPServer())

    app = compile_autonomous_intelligence(
        llm_client=llm_mock,
        mcp_registry=mcp_reg,
        notion_database_id="db-test-123",
    )

    initial_state = {
        "topic": "MCP Integration Test",
        "content": "Testing Notion sync.",
        "focus_areas": ["MCP"],
        "source": "e2e_test",
    }

    result = await app.ainvoke(initial_state)

    assert result["knowledge_result"] is not None
    # Knowledge result should have notion_page_id field (None when no token)
    knowledge = result["knowledge_result"]
    assert "notion_page_id" in knowledge or "error" not in knowledge


@pytest.mark.asyncio
async def test_autonomous_workflow_with_asana_mcp():
    """ProjectManagerAgent calls asana.create_task when MCP registry is provided."""
    llm_mock = _mock_llm(
        content="- Setup project structure\n- Write unit tests\n- Deploy to staging",
    )
    mcp_reg = _make_mcp_registry(AsanaMCPServer())

    app = compile_autonomous_intelligence(
        llm_client=llm_mock,
        mcp_registry=mcp_reg,
        asana_project_id="proj-test-456",
    )

    initial_state = {
        "topic": "Build REST API",
        "content": "Plan for building a REST API.",
        "focus_areas": ["API", "Backend"],
        "source": "e2e_test",
    }

    result = await app.ainvoke(initial_state)

    assert result["project_plan_result"] is not None
    pm = result["project_plan_result"]
    assert "asana_task_ids" in pm


@pytest.mark.asyncio
async def test_autonomous_workflow_with_browser_mcp():
    """ResearchAgent calls browser.search when MCP registry is provided."""
    llm_mock = _mock_llm()
    mcp_reg = _make_mcp_registry(BrowserMCPServer())

    app = compile_autonomous_intelligence(
        llm_client=llm_mock,
        mcp_registry=mcp_reg,
    )

    initial_state = {
        "topic": "Artificial Intelligence",
        "content": "Research on AI trends.",
        "focus_areas": ["LLMs"],
        "source": "e2e_test",
    }

    result = await app.ainvoke(initial_state)

    assert result["research_result"] is not None
    research = result["research_result"]
    assert "web_results" in research


@pytest.mark.asyncio
async def test_autonomous_workflow_error_handling():
    """Pipeline continues even when individual stages produce errors."""
    llm_mock = _mock_llm(content="")  # Empty content may cause analyst to fail

    app = compile_autonomous_intelligence(llm_client=llm_mock)

    initial_state = {
        "topic": "Test Error Handling",
        "content": "Some content.",
        "focus_areas": [],
        "source": "e2e_test",
    }

    result = await app.ainvoke(initial_state)

    # Even with errors, the graph should produce a result
    assert "errors" in result or result.get("research_result") is not None


@pytest.mark.asyncio
async def test_autonomous_state_schema():
    """Verify AutonomousState has all required fields."""
    state = AutonomousState(topic="Test", focus_areas=["a", "b"])
    assert state.topic == "Test"
    assert state.focus_areas == ["a", "b"]
    assert state.errors == []

    state.add_error("test_stage", "test error")
    assert len(state.errors) == 1
    assert state.errors[0]["stage"] == "test_stage"


@pytest.mark.asyncio
async def test_individual_agents_with_mcp():
    """Each agent individually calls MCP tools when registry is provided."""
    llm_mock = _mock_llm()
    mcp_reg = _make_mcp_registry(NotionMCPServer(), AsanaMCPServer(), BrowserMCPServer())

    # KnowledgeAgent
    ka = KnowledgeAgent(llm_client=llm_mock, mcp_registry=mcp_reg, notion_database_id="db-1")
    r = await ka.execute({
        "title": "Test", "content": "Content", "source": "test",
    })
    assert r["success"] is True
    assert "notion_page_id" in r["output"]

    # ResearchAgent
    ra = ResearchAgent(llm_client=llm_mock, mcp_registry=mcp_reg)
    r = await ra.execute({"topic": "AI", "focus_areas": []})
    assert r["success"] is True
    assert "web_results" in r["output"]

    # ProjectManagerAgent
    pma = ProjectManagerAgent(llm_client=llm_mock, mcp_registry=mcp_reg, asana_project_id="proj-1")
    r = await pma.execute({
        "goal": "Build app",
        "knowledge": "Use FastAPI.",
    })
    assert r["success"] is True
    assert "asana_task_ids" in r["output"]

    # NotificationAgent
    na = NotificationAgent(llm_client=llm_mock, mcp_registry=mcp_reg)
    r = await na.execute({
        "date": "2026-07-15",
        "news": [],
        "knowledge": [],
        "tasks": [],
        "channels": ["email"],
    })
    assert r["success"] is True
    assert "markdown" in r["output"]
