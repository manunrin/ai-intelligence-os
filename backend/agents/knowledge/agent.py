"""Knowledge Agent — converts analyzed content into structured knowledge."""

from __future__ import annotations

import logging
from typing import Any

from ...agents.base import AgentBase
from ...agents.knowledge.schemas import KnowledgeInput, KnowledgeOutput
from ...mcp.registry import MCPRegistry
from ...services.llm.base import ChatMessage, ChatRole
from ...services.llm.client import LLMClient

logger = logging.getLogger(__name__)


class KnowledgeAgent(AgentBase):
    """Converts research/analysis content into structured knowledge entries.

    Input:  {"title": str, "content": str, "analysis": str, "source": str, "tags": list[str]}
    Output: {"knowledge_type": str, "summary": str, "key_points": list[str], "tags": list[str],
              "notion_page_id": str | None, "notion_url": str | None}
    """

    name = "knowledge"
    version = "0.1.0"
    description = "Converts analyzed content into structured knowledge with summaries and key points"

    def __init__(
        self,
        llm_client: LLMClient,
        mcp_registry: MCPRegistry | None = None,
        notion_database_id: str = "",
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._llm_client = llm_client
        self._mcp_registry = mcp_registry
        self._notion_database_id = notion_database_id

    async def _execute_impl(self, input_data: dict[str, Any]) -> dict[str, Any]:
        validated = KnowledgeInput.model_validate(input_data)

        messages = [
            ChatMessage(
                role=ChatRole.SYSTEM,
                content="You are a knowledge extraction engine. Convert raw content into structured, searchable knowledge entries.",
            ),
            ChatMessage(
                role=ChatRole.USER,
                content=self._build_prompt(validated),
            ),
        ]

        response = await self._llm_client.chat(messages, task="analysis")

        output = KnowledgeOutput.from_llm_response(
            raw=response.content or "",
            title=validated.title,
            source=validated.source,
        )

        result: dict[str, Any] = {
            "knowledge_type": output.kind,
            "summary": output.summary,
            "key_points": output.key_points,
            "tags": output.tags,
            "notion_structure": output.notion_structure,
            "usage": response.usage,
            "notion_page_id": None,
            "notion_url": None,
        }

        # ── Notion integration ──────────────────────────────────────
        page_id, url = await self._sync_to_notion(output, validated)
        result["notion_page_id"] = page_id
        result["notion_url"] = url

        return result

    async def _sync_to_notion(
        self,
        output: KnowledgeOutput,
        input_data: KnowledgeInput,
    ) -> tuple[str | None, str | None]:
        """Sync knowledge entry to Notion via MCP tool.

        Returns (page_id, url) — both None if MCP is unavailable.
        """
        if self._mcp_registry is None:
            logger.debug("KnowledgeAgent: no MCP registry configured, skipping Notion sync")
            return None, None

        tool = self._mcp_registry.get_tool("notion.create_page")
        if tool is None:
            logger.debug("KnowledgeAgent: notion.create_page tool not registered")
            return None, None

        parent_id = self._notion_database_id or ""
        if not parent_id:
            logger.debug("KnowledgeAgent: no NOTION_DATABASE_ID set, skipping Notion sync")
            return None, None

        try:
            result = await tool.execute(
                title=input_data.title,
                parent_id=parent_id,
                content=output.summary,
            )
            data = result.get("data", {})
            return data.get("id"), data.get("url")
        except Exception as exc:
            logger.warning("KnowledgeAgent: Notion sync failed: %s", exc)
            return None, None

    @staticmethod
    def _build_prompt(data: KnowledgeInput) -> str:
        parts: list[str] = []
        parts.append(f"Title: {data.title}")
        if data.content:
            parts.append(f"Content:\n{data.content}")
        if data.analysis:
            parts.append(f"Analysis:\n{data.analysis}")
        if data.tags:
            parts.append(f"Tags: {', '.join(data.tags)}")
        parts.append(f"Source: {data.source}")
        return "\n".join(parts)
