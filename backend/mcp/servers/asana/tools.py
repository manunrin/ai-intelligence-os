"""Asana tool implementations (mocked for Phase 5-A)."""

from __future__ import annotations

from typing import Any

from ...base import MCPTool
from ...schemas import MCPToolDefinition


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
        return {
            "gid": "mock-task-id",
            "name": kwargs.get("name", ""),
            "resource_type": "task",
            "completed": False,
        }


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
        return {
            "task_id": kwargs.get("task_id"),
            "status": kwargs.get("status"),
            "updated": True,
        }


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
        return {
            "task_id": kwargs.get("task_id"),
            "completed": True,
        }


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
        return {
            "gid": "mock-comment-id",
            "task_id": kwargs.get("task_id"),
            "text": kwargs.get("text", ""),
            "created": True,
        }
