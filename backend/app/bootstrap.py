"""Application bootstrap — initializes MCP, Agents, Tools, and EventPublisher."""

from __future__ import annotations

import logging
from typing import Any, Callable

from backend.database.connection import AsyncSession
from backend.events.publisher import EventPublisher
from backend.mcp.registry import MCPRegistry
from backend.mcp.servers.asana.server import AsanaMCPServer
from backend.mcp.servers.browser.server import BrowserMCPServer
from backend.mcp.servers.github.server import GitHubMCPServer
from backend.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class ApplicationBootstrap:
    """Wires up the full application infrastructure at startup.

    Creates and configures:
    - MCPRegistry with all MCP servers
    - ToolRegistry linked to MCPRegistry
    - Agents with MCP registry injection
    - EventPublisher with AuditLogSubscriber registered
    """

    def __init__(self, session_factory: Callable[[], AsyncSession]) -> None:
        self._session_factory = session_factory
        self.mcp_registry = MCPRegistry()
        self.tool_registry = ToolRegistry()
        self.event_publisher = EventPublisher()

    def initialize(self) -> None:
        """Register all MCP servers, tools, and event subscribers."""
        # Register all MCP servers
        for server_cls in (NotionMCPServer, AsanaMCPServer, BrowserMCPServer, GitHubMCPServer):
            server = server_cls()
            self.mcp_registry.register_server(server)

        # Wire ToolRegistry to MCPRegistry
        self.tool_registry.set_mcp_registry(self.mcp_registry)

        # Register audit log subscriber
        from backend.events.subscriber import AuditLogSubscriber

        subscriber = AuditLogSubscriber(self._session_factory)
        self.event_publisher.subscribe(
            type("AuditLogEvent", (), {"__name__": "AuditLogEvent"}), subscriber.handle
        )
        # Also register by the actual event class for runtime dispatch
        from backend.events.event import AuditLogEvent

        self.event_publisher.subscribe(AuditLogEvent, subscriber.handle)

        logger.info(
            "Bootstrapped %d MCP servers, %d tools, event publisher ready",
            len(self.mcp_registry.list_servers()),
            len(self.mcp_registry.list_tools()),
        )

    async def shutdown(self) -> None:
        """Gracefully shut down all MCP servers."""
        await self.mcp_registry.shutdown_all()

    def get_agents_with_mcp(self) -> dict[str, object]:
        """Return a dict of agent_name → agent_instance with MCP registry injected.

        Agents are instantiated with the shared MCP registry so they can
        call MCP tools when available.
        """
        from backend.agents.knowledge.agent import KnowledgeAgent
        from backend.agents.notification.agent import NotificationAgent
        from backend.agents.project_manager.agent import ProjectManagerAgent
        from backend.agents.research.agent import ResearchAgent
        from backend.services.llm.client import LLMClient
        from backend.services.llm.router import LLMRouter

        router = LLMRouter()
        llm_client = LLMClient(router)

        return {
            "knowledge": KnowledgeAgent(
                llm_client=llm_client,
                mcp_registry=self.mcp_registry,
                notion_database_id="",  # set from env/config
            ),
            "research": ResearchAgent(
                llm_client=llm_client,
                mcp_registry=self.mcp_registry,
            ),
            "project_manager": ProjectManagerAgent(
                llm_client=llm_client,
                mcp_registry=self.mcp_registry,
                asana_project_id="",  # set from env/config
            ),
            "notification": NotificationAgent(
                llm_client=llm_client,
                mcp_registry=self.mcp_registry,
            ),
        }
