"""Tests for NotificationAgent schemas and output parsing."""

import pytest

from backend.agents.notification.schemas import NotificationInput, NotificationOutput


def test_notification_input_validation():
    data = {
        "date": "2026-07-15",
        "news": [{"title": "AI Update", "summary": "New model released"}],
        "channels": ["telegram"],
    }
    input_model = NotificationInput.model_validate(data)
    assert input_model.date == "2026-07-15"
    assert len(input_model.news) == 1
    assert input_model.channels == ["telegram"]


def test_notification_input_defaults():
    input_model = NotificationInput(date="2026-01-01")
    assert input_model.news == []
    assert input_model.channels == ["wechat", "telegram", "email"]


def test_notification_output_from_llm():
    raw = "# Daily Digest\n\nHere is your summary..."
    output = NotificationOutput.from_llm_response(raw, channels=["email"])
    assert output.markdown == raw
    assert output.channels == ["email"]


def test_notification_build_prompt_with_data():
    """Verify _build_prompt includes all sections when data is provided."""
    from backend.agents.notification.agent import NotificationAgent

    data = NotificationInput(
        date="2026-07-15",
        news=[{"title": "News 1", "summary": "Summary 1"}],
        knowledge=[{"title": "Knowledge 1", "kind": "research"}],
        tasks=[{"title": "Task 1", "priority": "high", "status": "pending"}],
    )
    prompt = NotificationAgent._build_prompt(data)
    assert "News 1" in prompt
    assert "Knowledge 1" in prompt
    assert "Task 1" in prompt
    assert "[high]" in prompt
