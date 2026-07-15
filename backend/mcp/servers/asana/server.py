"""Asana MCP server — exposes Asana task management as discoverable tools."""

from __future__ import annotations

from typing import Type

from ...base import MCPServerBase, MCPTool
from ...schemas import MCPToolDefinition
from .tools import (
    AsanaAddComment,
    AsanaCompleteTask,
    AsanaCreateTask,
    AsanaUpdateTaskStatus,
)


class AsanaMCPServer(MCPServerBase):
    """MCP server for the Asana API.

    Exposes tools for task creation, status updates, completion, and commenting.
    """

    name = "asana"
    version = "0.1.0"
    description = "Asana integration — tasks, projects, comments"

    _tools: dict[str, Type[MCPTool]] = {
        "create_task": AsanaCreateTask,
        "update_task_status": AsanaUpdateTaskStatus,
        "complete_task": AsanaCompleteTask,
        "add_comment": AsanaAddComment,
    }

    def available_tools(self) -> list[MCPToolDefinition]:
        return [
            MCPToolDefinition(
                name="create_task",
                description="Create a new Asana task within a project.",
                parameters={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Task name.",
                        },
                        "description": {
                            "type": "string",
                            "description": "Task description.",
                        },
                        "project": {
                            "type": "string",
                            "description": "Project ID to add the task to.",
                        },
                        "due_date": {
                            "type": "string",
                            "description": "ISO 8601 date string (YYYY-MM-DD).",
                        },
                        "priority": {
                            "type": "string",
                            "enum": ["low", "medium", "high", "urgent"],
                            "description": "Task priority level.",
                        },
                    },
                    "required": ["name", "project"],
                },
            ),
            MCPToolDefinition(
                name="update_task_status",
                description="Update the status of an existing Asana task.",
                parameters={
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "Task to update.",
                        },
                        "status": {
                            "type": "string",
                            "enum": ["todo", "in_progress", "done", "blocked"],
                            "description": "New task status.",
                        },
                    },
                    "required": ["task_id", "status"],
                },
            ),
            MCPToolDefinition(
                name="complete_task",
                description="Mark an Asana task as completed.",
                parameters={
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "Task to complete.",
                        },
                    },
                    "required": ["task_id"],
                },
            ),
            MCPToolDefinition(
                name="add_comment",
                description="Add a comment to an Asana task.",
                parameters={
                    "type": "object",
                    "properties": {
                        "task_id": {
                            "type": "string",
                            "description": "Task to comment on.",
                        },
                        "text": {
                            "type": "string",
                            "description": "Comment text.",
                        },
                    },
                    "required": ["task_id", "text"],
                },
            ),
        ]

    def _create_tool(self, tool_name: str) -> MCPTool | None:
        cls = self._tools.get(tool_name)
        if cls is None:
            return None
        instance = cls()
        instance.server = self
        return instance
