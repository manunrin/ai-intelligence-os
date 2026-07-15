"""Tests for agent registry and mock LLM execution."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.agents.registry import AgentRegistry
from backend.agents.knowledge.agent import KnowledgeAgent
from backend.agents.pronunciation.agent import PronunciationAgent
from backend.agents.project_manager.agent import ProjectManagerAgent
from backend.agents.notification.agent import NotificationAgent


def test_all_agents_registered():
    """All four new agents must be auto-registered."""
    all_agents = AgentRegistry.list_all()
    names = list(all_agents.keys())
    assert "knowledge" in names
    assert "pronunciation" in names
    assert "project_manager" in names
    assert "notification" in names


def test_instantiate_by_name():
    llm_mock = MagicMock()
    agent = AgentRegistry.instantiate("knowledge", llm_client=llm_mock)
    assert isinstance(agent, KnowledgeAgent)
    assert agent.name == "knowledge"


def test_unknown_agent_returns_none():
    result = AgentRegistry.instantiate("nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_knowledge_agent_with_mock_llm():
    llm_mock = MagicMock()
    llm_mock.chat = AsyncMock(
        return_value=MagicMock(content="Summary: Test content.\n- Key point one\n- Key point two", usage={"prompt_tokens": 10})
    )

    agent = KnowledgeAgent(llm_client=llm_mock)
    result = await agent.execute({
        "title": "Test Article",
        "content": "Some content here",
        "analysis": "This is important.",
        "source": "test",
        "tags": ["test"],
    })

    assert result["success"] is True
    output = result["output"]
    assert "knowledge_type" in output
    assert "summary" in output
    assert "key_points" in output
    assert "tags" in output
    assert output["knowledge_type"] == "article"


@pytest.mark.asyncio
async def test_pronunciation_agent_with_mock_llm():
    llm_mock = MagicMock()
    llm_mock.chat = AsyncMock(
        return_value=MagicMock(
            content='{"zh": {"text": "你好", "pinyin": "ni3 hao3"}}',
            usage={"prompt_tokens": 5},
        )
    )

    agent = PronunciationAgent(llm_client=llm_mock)
    result = await agent.execute({
        "text": "Hello world",
        "languages": ["zh"],
    })

    assert result["success"] is True
    output = result["output"]
    assert "translations" in output
    assert "zh" in output["translations"]


@pytest.mark.asyncio
async def test_project_manager_agent_with_mock_llm():
    llm_mock = MagicMock()
    llm_mock.chat = AsyncMock(
        return_value=MagicMock(
            content="- Setup project structure\n- Write unit tests\n- Deploy to staging",
            usage={"prompt_tokens": 15},
        )
    )

    agent = ProjectManagerAgent(llm_client=llm_mock)
    result = await agent.execute({
        "goal": "Build a REST API",
        "knowledge": "Use FastAPI with SQLAlchemy.",
        "deadline": "2026-12-31",
    })

    assert result["success"] is True
    output = result["output"]
    assert "project" in output
    assert "tasks" in output
    assert len(output["tasks"]) >= 1


@pytest.mark.asyncio
async def test_notification_agent_with_mock_llm():
    llm_mock = MagicMock()
    llm_mock.chat = AsyncMock(
        return_value=MagicMock(
            content="# Daily Digest\n\n## News\n- AI Update\n\n## Tasks\n- Fix bug",
            usage={"prompt_tokens": 20},
        )
    )

    agent = NotificationAgent(llm_client=llm_mock)
    result = await agent.execute({
        "date": "2026-07-15",
        "news": [{"title": "AI Update", "summary": "New model"}],
        "knowledge": [{"title": "Knowledge 1", "kind": "research"}],
        "tasks": [{"title": "Fix bug", "priority": "high"}],
    })

    assert result["success"] is True
    output = result["output"]
    assert "markdown" in output
    assert "channels" in output
    assert "Daily Digest" in output["markdown"]
