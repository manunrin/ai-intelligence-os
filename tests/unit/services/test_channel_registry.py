"""Tests for channel registry — enabled channels and dispatch."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.services.notification.channel_registry import send_notifications


@pytest.fixture(autouse=True)
def _mock_channels():
    """Patch all channel classes so they don't actually call network."""
    with patch("backend.services.notification.channel_registry.EmailChannel") as mock_email_cls, \
         patch("backend.services.notification.channel_registry.TelegramChannel") as mock_tg_cls, \
         patch("backend.services.notification.channel_registry.SlackChannel") as mock_slack_cls:

        # Each channel's is_enabled property returns True
        for cls, cname in ((mock_email_cls, "email"), (mock_tg_cls, "telegram"), (mock_slack_cls, "slack")):
            cls.return_value.is_enabled = True
            cls.return_value.name = cname

        yield mock_email_cls, mock_tg_cls, mock_slack_cls


async def test_send_notifications_dispatches_to_all(_mock_channels):
    mock_email_cls, mock_tg_cls, mock_slack_cls = _mock_channels
    mock_email = mock_email_cls.return_value
    mock_tg = mock_tg_cls.return_value
    mock_slack = mock_slack_cls.return_value

    for ch in (mock_email, mock_tg, mock_slack):
        ch.send = AsyncMock(return_value=MagicMock(success=True, channel=ch.name, message="sent"))

    # Patch get_enabled_channels to return our mocked instances
    with patch("backend.services.notification.channel_registry.get_enabled_channels", return_value=[mock_email, mock_tg, mock_slack]):
        status = await send_notifications("# Daily Digest", ["email", "telegram", "slack"])

    assert status["email"] == "sent"
    assert status["telegram"] == "sent"
    assert status["slack"] == "sent"
    mock_email.send.assert_called_once_with("# Daily Digest")
    mock_tg.send.assert_called_once()
    mock_slack.send.assert_called_once()


async def test_send_notifications_skips_disabled():
    """When no channels are enabled, returns empty dict."""
    with patch("backend.services.notification.channel_registry.get_enabled_channels", return_value=[]):
        status = await send_notifications("# Daily Digest", ["email"])
    assert status == {}


async def test_send_notifications_partial_failure():
    """One channel failure doesn't block others."""
    mock_email = MagicMock()
    mock_email.name = "email"
    mock_email.send = AsyncMock(
        return_value=MagicMock(success=False, channel="email", message="connection refused")
    )
    with patch("backend.services.notification.channel_registry.get_enabled_channels", return_value=[mock_email]):
        status = await send_notifications("# Digest", ["email"])

    assert status["email"] == "failed: connection refused"


async def test_send_notifications_ignores_unrequested_channel():
    """Only requested channels are dispatched to."""
    mock_email = MagicMock()
    mock_email.name = "email"
    mock_email.is_enabled = True
    mock_email.send = AsyncMock(
        return_value=MagicMock(success=True, channel="email", message="sent")
    )
    with patch("backend.services.notification.channel_registry.get_enabled_channels", return_value=[mock_email]):
        # Requesting only telegram — email should not be called
        status = await send_notifications("# Digest", ["telegram"])

    assert status == {}
    mock_email.send.assert_not_called()
