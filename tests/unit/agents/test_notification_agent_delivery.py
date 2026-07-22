"""Tests for NotificationAgent delivery integration."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.agents.notification.schemas import NotificationInput, NotificationOutput


def test_notification_output_has_delivery_status():
    """NotificationOutput includes delivery_status field with default empty dict."""
    raw = "# Daily Digest"
    output = NotificationOutput.from_llm_response(raw, channels=["email"])
    assert output.markdown == raw
    assert output.channels == ["email"]
    assert output.delivery_status == {}


def test_notification_output_delivery_status_update():
    """delivery_status can be updated after creation."""
    output = NotificationOutput(markdown="# Digest", channels=["email"])
    output.delivery_status = {"email": "sent"}
    assert output.delivery_status == {"email": "sent"}


@pytest.fixture
def _mock_channels():
    """Patch all channel classes so they don't actually call network."""
    with patch("backend.services.notification.channel_registry.EmailChannel") as mock_email_cls, \
         patch("backend.services.notification.channel_registry.TelegramChannel") as mock_tg_cls, \
         patch("backend.services.notification.channel_registry.SlackChannel") as mock_slack_cls:

        for cname in ("email", "telegram", "slack"):
            cls = {"email": mock_email_cls, "telegram": mock_tg_cls, "slack": mock_slack_cls}[cname]
            cls.return_value.is_enabled = True
            cls.return_value.name = cname

        yield mock_email_cls, mock_tg_cls, mock_slack_cls


@pytest.fixture
def agent(_mock_channels):
    from backend.agents.notification.agent import NotificationAgent

    mock_llm = MagicMock()
    mock_llm.chat = AsyncMock(return_value=MagicMock(content="# Daily Digest", usage={}))
    mock_mcp = MagicMock()
    return NotificationAgent(llm_client=mock_llm, mcp_registry=mock_mcp)


@pytest.mark.asyncio
async def test_agent_dispatches_to_channels(agent):
    """_dispatch_notifications calls send_notifications and sets delivery_status."""
    mock_email_result = MagicMock(success=True, channel="email", message="sent")
    mock_tg_result = MagicMock(success=False, channel="telegram", message="bot not found")

    with patch("backend.services.notification.channel_registry.send_notifications") as mock_send:
        mock_send.return_value = {"email": "sent", "telegram": "failed: bot not found"}

        output = NotificationOutput(markdown="# Daily Digest", channels=["email", "telegram"])
        input_data = NotificationInput(date="2026-07-15", channels=["email", "telegram"])

        await agent._dispatch_notifications(output, input_data)

        assert output.delivery_status["email"] == "sent"
        assert "failed" in output.delivery_status["telegram"]
        mock_send.assert_called_once_with("# Daily Digest", ["email", "telegram"])


@pytest.mark.asyncio
async def test_agent_execution_returns_markdown(agent):
    """Full _execute_impl returns markdown, channels, and usage."""
    result = await agent._execute_impl({
        "date": "2026-07-15",
        "news": [{"title": "AI Update", "summary": "New model released"}],
        "channels": ["email"],
    })

    assert "markdown" in result
    assert result["markdown"] == "# Daily Digest"
    assert "channels" in result
    assert "usage" in result


def test_notification_input_backward_compat():
    """NotificationInput works without channels field (uses defaults)."""
    data = {"date": "2026-07-15"}
    inp = NotificationInput.model_validate(data)
    assert inp.channels == ["wechat", "telegram", "email"]


def test_notification_input_with_custom_channels():
    """NotificationInput accepts custom channel list."""
    data = {"date": "2026-07-15", "channels": ["email", "slack"]}
    inp = NotificationInput.model_validate(data)
    assert inp.channels == ["email", "slack"]
