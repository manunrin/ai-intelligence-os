"""Project Manager Agent — converts knowledge into actionable tasks."""

from __future__ import annotations

import logging
from typing import Any

from ...agents.base import AgentBase
from ...agents.project_manager.schemas import ProjectPlanInput, ProjectPlanOutput
from ...mcp.registry import MCPRegistry
from ...services.llm.base import ChatMessage, ChatRole
from ...services.llm.client import LLMClient

logger = logging.getLogger(__name__)


class ProjectManagerAgent(AgentBase):
    """Converts knowledge and goals into structured project plans with prioritized tasks.

    Input:  {"goal": str, "knowledge": str, "deadline": str}
    Output: {"project": str, "tasks": [...], "asana_task_ids": list[str]}
    """

    name = "project_manager"
    version = "0.1.0"
    description = "Converts knowledge and goals into structured project plans with prioritized tasks"

    def __init__(
        self,
        llm_client: LLMClient,
        mcp_registry: MCPRegistry | None = None,
        asana_project_id: str = "",
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._llm_client = llm_client
        self._mcp_registry = mcp_registry
        self._asana_project_id = asana_project_id

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

        tasks = [t.model_dump() for t in output.tasks]

        # ── Asana integration ───────────────────────────────────────
        asana_ids = await self._sync_to_asana(tasks, validated.goal)

        return {
            "project": output.project,
            "tasks": tasks,
            "asana_task_ids": asana_ids,
            "usage": response.usage,
        }

    async def _sync_to_asana(
        self,
        tasks: list[dict[str, Any]],
        goal: str,
    ) -> list[str]:
        """Sync generated tasks to Asana via MCP tool.

        Returns list of created task IDs.
        """
        if self._mcp_registry is None:
            logger.debug("ProjectManagerAgent: no MCP registry configured, skipping Asana sync")
            return []

        tool = self._mcp_registry.get_tool("asana.create_task")
        if tool is None:
            logger.debug("ProjectManagerAgent: asana.create_task tool not registered")
            return []

        project_id = self._asana_project_id
        if not project_id:
            logger.debug("ProjectManagerAgent: no ASANA_PROJECT_ID set, skipping Asana sync")
            return []

        created_ids: list[str] = []
        for task in tasks[:10]:  # Cap at 10 tasks per run
            try:
                result = await tool.execute(
                    name=task["title"],
                    project=project_id,
                    description=task.get("description", ""),
                    priority=task.get("priority", "medium"),
                )
                data = result.get("data", {})
                gid = data.get("gid") or data.get("id")
                if gid:
                    created_ids.append(gid)
            except Exception as exc:
                logger.warning("ProjectManagerAgent: Asana create_task failed for '%s': %s", task.get("title"), exc)

        return created_ids

    @staticmethod
    def _build_prompt(data: ProjectPlanInput) -> str:
        parts: list[str] = []
        parts.append(f"Goal: {data.goal}")
        if data.deadline:
            parts.append(f"Deadline: {data.deadline}")
        if data.knowledge:
            parts.append(f"Relevant knowledge:\n{data.knowledge}")
        return "\n".join(parts)
