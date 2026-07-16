"""Asana tool implementations — wired to the real Asana API."""

from __future__ import annotations

import logging
import os
from typing import Any

from ...base import MCPTool
from ...schemas import MCPToolDefinition
from .client import AsanaAPIError, AsanaClient

logger = logging.getLogger(__name__)


def _has_token() -> bool:
    """Check whether a valid Asana token is configured."""
    return len(os.environ.get("ASANA_TOKEN", "").strip()) > 0


# ------------------------------------------------------------------
# Tool: create_task
# ------------------------------------------------------------------

class AsanaCreateTask(MCPTool):
    @property
    def tool_definition(self) -> MCPToolDefinition:
        return MCPToolDefinition(
            name="create_task",
            description="Create a new Asana task within a project.",
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "project": {"type": "string"},
                    "due_date": {"type": "string"},
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "urgent"],
                    },
                },
                "required": ["name", "project"],
            },
        )

    async def _execute_impl(self, **kwargs: Any) -> Any:
        name = kwargs.get("name", "")
        project = kwargs.get("project", "")
        description = kwargs.get("description")
        due_date = kwargs.get("due_date")
        priority = kwargs.get("priority")

        if not _has_token():
            logger.debug("AsanaCreateTask: no token configured, returning stub")
            return {
                "gid": "mock-task-id",
                "name": name,
                "resource_type": "task",
                "completed": False,
            }

        client = AsanaClient()
        # Map priority to approval_status (closest Asana equivalent)
        approval_map = {
            "urgent": "blocked",
            "high": "pending",
            "medium": None,
            "low": None,
        }
        approvals = approval_map.get(priority) if priority else None

        try:
            task = await client.create_task(
                name=name,
                project=project,
                notes=description,
                due_on=due_date,
                approvals=approvals,
            )
            return {
                "gid": task.get("gid", ""),
                "name": name,
                "resource_type": task.get("resource_type", "task"),
                "completed": task.get("completed", False),
                "raw": task,
            }
        except AsanaAPIError as exc:
            logger.warning("Asana create_task failed: %s", exc)
            return {
                "gid": "",
                "name": name,
                "resource_type": "task",
                "completed": False,
                "error": str(exc),
            }


# ------------------------------------------------------------------
# Tool: update_task_status
# ------------------------------------------------------------------

class AsanaUpdateTaskStatus(MCPTool):
    @property
    def tool_definition(self) -> MCPToolDefinition:
        return MCPToolDefinition(
            name="update_task_status",
            description="Update the status of an existing Asana task.",
            parameters={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string"},
                    "status": {
                        "type": "string",
                        "enum": ["todo", "in_progress", "done", "blocked"],
                    },
                },
                "required": ["task_id", "status"],
            },
        )

    async def _execute_impl(self, **kwargs: Any) -> Any:
        task_id = kwargs.get("task_id", "")
        status = kwargs.get("status", "")

        if not _has_token():
            logger.debug("AsanaUpdateTaskStatus: no token configured, returning stub")
            return {
                "task_id": task_id,
                "status": status,
                "updated": True,
            }

        client = AsanaClient()
        try:
            # Map our status enum to Asana approval_status or completed flag
            task_data = await client.get_task(task_id)
            update_body: dict[str, Any] = {}

            if status == "done":
                # Asana doesn't have a direct "status" field; use completed
                update_body["completed"] = True
            elif status == "blocked":
                update_body["approval_status"] = "blocked"
            elif status == "in_progress":
                update_body["approval_status"] = "pending"
            # "todo" maps to None/default

            if update_body:
                updated_task = await client.update_task(
                    task_id=task_id,
                    **update_body,
                )
            else:
                updated_task = task_data

            return {
                "task_id": task_id,
                "status": status,
                "updated": True,
                "raw": updated_task,
            }
        except AsanaAPIError as exc:
            logger.warning("Asana update_task_status failed: %s", exc)
            return {
                "task_id": task_id,
                "status": status,
                "updated": False,
                "error": str(exc),
            }


# ------------------------------------------------------------------
# Tool: complete_task
# ------------------------------------------------------------------

class AsanaCompleteTask(MCPTool):
    @property
    def tool_definition(self) -> MCPToolDefinition:
        return MCPToolDefinition(
            name="complete_task",
            description="Mark an Asana task as completed.",
            parameters={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string"},
                },
                "required": ["task_id"],
            },
        )

    async def _execute_impl(self, **kwargs: Any) -> Any:
        task_id = kwargs.get("task_id", "")

        if not _has_token():
            logger.debug("AsanaCompleteTask: no token configured, returning stub")
            return {
                "task_id": task_id,
                "completed": True,
            }

        client = AsanaClient()
        try:
            task = await client.update_task(task_id=task_id, completed=True)
            return {
                "task_id": task_id,
                "completed": True,
                "raw": task,
            }
        except AsanaAPIError as exc:
            logger.warning("Asana complete_task failed: %s", exc)
            return {
                "task_id": task_id,
                "completed": False,
                "error": str(exc),
            }


# ------------------------------------------------------------------
# Tool: add_comment
# ------------------------------------------------------------------

class AsanaAddComment(MCPTool):
    @property
    def tool_definition(self) -> MCPToolDefinition:
        return MCPToolDefinition(
            name="add_comment",
            description="Add a comment to an Asana task.",
            parameters={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string"},
                    "text": {"type": "string"},
                },
                "required": ["task_id", "text"],
            },
        )

    async def _execute_impl(self, **kwargs: Any) -> Any:
        task_id = kwargs.get("task_id", "")
        text = kwargs.get("text", "")

        if not _has_token():
            logger.debug("AsanaAddComment: no token configured, returning stub")
            return {
                "gid": "mock-comment-id",
                "task_id": task_id,
                "text": text,
                "created": True,
            }

        client = AsanaClient()
        try:
            story = await client.create_story(task_id=task_id, text=text)
            return {
                "gid": story.get("gid", ""),
                "task_id": task_id,
                "text": text,
                "created": True,
                "raw": story,
            }
        except AsanaAPIError as exc:
            logger.warning("Asana add_comment failed: %s", exc)
            return {
                "gid": "",
                "task_id": task_id,
                "text": text,
                "created": False,
                "error": str(exc),
            }
