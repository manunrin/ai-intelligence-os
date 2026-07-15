"""LLM gateway architecture."""

from __future__ import annotations

from enum import Enum
from typing import Any


class TaskCategory(str, Enum):
    """Standard task categories for model routing."""
    SUMMARY = "summary"
    TRANSLATION = "translation"
    RESEARCH = "research"
    ANALYSIS = "analysis"
    LOCAL = "local"
    EMBEDDING = "embedding"


def resolve_task_category(input_data: dict[str, Any]) -> TaskCategory:
    """Infer the task category from input metadata.

    Agents can pass a 'task' key in their input dict to explicitly
    specify the category. Otherwise, the router falls back to defaults.
    """
    task = input_data.get("task")
    if task and task in TaskCategory.__members__:
        return TaskCategory(task)
    return TaskCategory.SUMMARY  # default
