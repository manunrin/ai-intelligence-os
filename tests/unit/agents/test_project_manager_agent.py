"""Tests for ProjectManagerAgent schemas and output parsing."""

import pytest

from backend.agents.project_manager.schemas import ProjectPlanInput, ProjectPlanOutput, TaskItem


def test_project_plan_input_validation():
    data = {"goal": "Build an API", "deadline": "2026-12-31"}
    input_model = ProjectPlanInput.model_validate(data)
    assert input_model.goal == "Build an API"
    assert input_model.deadline == "2026-12-31"


def test_project_plan_input_defaults():
    input_model = ProjectPlanInput(goal="Simple goal")
    assert input_model.knowledge == ""
    assert input_model.deadline == ""


def test_task_item_defaults():
    task = TaskItem(title="Install dependencies")
    assert task.description == ""
    assert task.priority == "medium"
    assert task.dependency == ""


def test_task_item_explicit_fields():
    task = TaskItem(title="Fix bug", priority="urgent", dependency="Setup project")
    assert task.priority == "urgent"
    assert task.dependency == "Setup project"


@pytest.mark.parametrize(
    ("raw", "expected_priority"),
    [
        ("URGENT: Fix the crash immediately", "urgent"),
        ("Deploy to production (blocker)", "urgent"),
        ("High priority: optimize queries", "high"),
        ("Medium: add logging", "medium"),
        ("Low: update docs", "low"),
        ("Nice to have: add favicon", "low"),
    ],
)
def test_priority_detection(raw: str, expected_priority: str):
    output = ProjectPlanOutput.from_llm_response(raw, goal="Test")
    assert len(output.tasks) >= 1
    assert output.tasks[0].priority == expected_priority


def test_project_plan_output_max_tasks():
    lines = "\n".join(f"- Task {i}" for i in range(100))
    output = ProjectPlanOutput.from_llm_response(lines, goal="Bulk test")
    assert len(output.tasks) <= 50


def test_project_plan_output_project_name():
    output = ProjectPlanOutput.from_llm_response("- Do something", goal="My Project Goal")
    assert output.project == "My Project Goal"
