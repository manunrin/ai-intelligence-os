"""Project Manager Agent — converts knowledge into actionable tasks.

Analyzes goals and knowledge entries to produce structured project plans
with prioritized, dependency-ordered tasks. Does NOT call external APIs.
"""

from __future__ import annotations

import logging
from typing import Any

from ...agents.base import AgentBase
from ...agents.project_manager.schemas import ProjectPlanInput, ProjectPlanOutput
from ...services.llm.base import ChatMessage, ChatRole
from ...services.llm.client import LLMClient

logger = logging.getLogger(__name__)


class ProjectManagerAgent(AgentBase):
    """Converts knowledge and goals into structured project plans.

    Input:  {"goal": str, "knowledge": str, "deadline": str}
    Output: {"project": str, "tasks": [{"title", "description", "priority", "dependency"}]}
    """

    name = "project_manager"
    version = "0.1.0"
    description = "Converts knowledge and goals into structured project plans with prioritized tasks"

    def __init__(self, llm_client: LLMClient, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._llm_client = llm_client

    async def _execute_impl(self, input_data: dict[str, Any]) -> dict[str, Any]:
        validated = ProjectPlanInput.model_validate(input_data)

        messages = [
            ChatMessage(
                role=ChatRole.SYSTEM,
                content=(
                    "You are a project manager AI. Given a goal and relevant knowledge, produce an actionable "
                    "project plan with prioritized tasks and dependencies."
                ),
            ),
            ChatMessage(
                role=ChatRole.USER,
                content=self._build_prompt(validated),
            ),
        ]

        response = await self._llm_client.chat(messages, task="analysis")

        output = ProjectPlanOutput.from_llm_response(
            raw=response.content or "",
            goal=validated.goal,
        )

        return {
            "project": output.project,
            "tasks": [t.model_dump() for t in output.tasks],
            "usage": response.usage,
        }

    @staticmethod
    def _build_prompt(data: ProjectPlanInput) -> str:
        parts: list[str] = []
        parts.append(f"Goal: {data.goal}")
        if data.deadline:
            parts.append(f"Deadline: {data.deadline}")
        if data.knowledge:
            parts.append(f"Relevant knowledge:\n{data.knowledge}")
        return "\n".join(parts)
