"""Notification Agent — generates formatted push content."""

from __future__ import annotations

import logging
from typing import Any

from ...agents.base import AgentBase
from ...agents.notification.schemas import NotificationInput, NotificationOutput
from ...mcp.registry import MCPRegistry
from ...services.llm.base import ChatMessage, ChatRole
from ...services.llm.client import LLMClient

logger = logging.getLogger(__name__)


class NotificationAgent(AgentBase):
    """Generates formatted notification content from daily data.

    Input:  {"date": str, "news": list[dict], "knowledge": list[dict], "tasks": list[dict]}
    Output: {"markdown": str, "channels": list[str]}
    """

    name = "notification"
    version = "0.1.0"
    description = "Generates formatted Markdown daily digest from news, knowledge, and tasks"

    def __init__(
        self,
        llm_client: LLMClient,
        mcp_registry: MCPRegistry | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._llm_client = llm_client
        self._mcp_registry = mcp_registry

    async def _execute_impl(self, input_data: dict[str, Any]) -> dict[str, Any]:
        validated = NotificationInput.model_validate(input_data)

        messages = [
            ChatMessage(
                role=ChatRole.SYSTEM,
                content=(
                    "You are a daily digest generator. Given today's news, knowledge entries, and tasks, "
                    "produce a well-formatted Markdown notification summary."
                ),
            ),
            ChatMessage(
                role=ChatRole.USER,
                content=self._build_prompt(validated),
            ),
        ]

        response = await self._llm_client.chat(messages, task="summary")

        output = NotificationOutput.from_llm_response(
            raw=response.content or "",
            channels=validated.channels,
        )

        # ── Notification tool dispatch (placeholder for future channels) ─
        await self._dispatch_notifications(output, validated)

        return {
            "markdown": output.markdown,
            "channels": output.channels,
            "usage": response.usage,
        }

    async def _dispatch_notifications(
        self,
        output: NotificationOutput,
        input_data: NotificationInput,
    ) -> None:
        """Dispatch notifications via configured channels.

        Each enabled channel (email, telegram, slack) is invoked independently.
        Failures are logged as warnings and recorded in delivery_status.
        """
        from ...services.notification.channel_registry import send_notifications

        status = await send_notifications(output.markdown, output.channels)
        output.delivery_status = status

    @staticmethod
    def _build_prompt(data: NotificationInput) -> str:
        parts: list[str] = []
        parts.append(f"Date: {data.date}")
        parts.append(f"Channels: {', '.join(data.channels)}")

        if data.news:
            parts.append("\n--- News ---")
            for item in data.news[:10]:
                title = item.get("title", "Untitled")
                summary = item.get("summary", "")
                parts.append(f"- [{title}] {summary}")

        if data.knowledge:
            parts.append("\n--- Knowledge ---")
            for item in data.knowledge[:10]:
                title = item.get("title", "Untitled")
                kind = item.get("kind", "")
                parts.append(f"- [{kind}] {title}")

        if data.tasks:
            parts.append("\n--- Tasks ---")
            for item in data.tasks[:10]:
                title = item.get("title", "Untitled")
                status = item.get("status", "")
                priority = item.get("priority", "")
                parts.append(f"- [{priority}] {title} ({status})")

        return "\n".join(parts)
