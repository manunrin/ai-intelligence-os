"""Project Manager Agent schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class TaskItem(BaseModel):
    """A single task within a project plan."""

    title: str = Field(description="Task title")
    description: str = Field(default="", description="Task description")
    priority: str = Field(default="medium", description="Priority: low | medium | high | urgent")
    dependency: str = Field(default="", description="Depends-on task title or empty")


class ProjectPlanInput(BaseModel):
    """Input schema for ProjectManagerAgent."""

    goal: str = Field(description="Project or action goal")
    knowledge: str = Field(default="", description="Relevant knowledge/context")
    deadline: str = Field(default="", description="ISO date string or empty")


class ProjectPlanOutput(BaseModel):
    """Structured output from ProjectManagerAgent."""

    project: str = Field(description="Generated project name")
    tasks: list[TaskItem] = Field(default_factory=list)

    @classmethod
    def from_llm_response(cls, raw: str, goal: str) -> "ProjectPlanOutput":
        """Parse LLM text response into ProjectPlanOutput.

        Falls back to a simple plan when parsing fails.
        """
        lines = [l.strip() for l in raw.splitlines() if l.strip()]
        tasks: list[TaskItem] = []
        project_name = goal

        for line in lines:
            lower = line.lower().strip()
            # Skip section headers
            if lower in ("task", "tasks", "action items", "steps"):
                continue

            priority = "medium"
            if any(w in lower for w in ("urgent", "critical", "p0", "blocker")):
                priority = "urgent"
            elif any(w in lower for w in ("high", "p1", "important")):
                priority = "high"
            elif any(w in lower for w in ("low", "p3", "nice", "optional")):
                priority = "low"

            desc = line.lstrip("-*0123456789. ").strip()
            if desc:
                tasks.append(TaskItem(title=desc, description=desc, priority=priority))

        return cls(project=project_name, tasks=tasks[:50])
