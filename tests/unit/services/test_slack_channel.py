"""Tests for SlackChannel notification delivery."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.services.notification.channels.slack import SlackChannel


@pytest.fixture(autouse=True)
def _mock_settings():
    with patch("backend.services.notification.channels.slack.get_settings") as fn:
        s = MagicMock()
        s.slack_webhook_url = "https://hooks.slack.com/services/T00/B00/x"
        fn.return_value = s
        yield fn


@pytest.fixture
def channel():
    return SlackChannel()


async def test_is_enabled_when_configured():
    ch = SlackChannel()
    assert ch.is_enabled is True


async def test_is_enabled_without_url():
    with patch("backend.services.notification.channels.slack.get_settings") as fn:
        s = MagicMock()
        s.slack_webhook_url = ""
        fn.return_value = s
        assert SlackChannel().is_enabled is False


async def test_send_success(channel):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "ok"

    with patch("backend.services.notification.channels.slack.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        result = await channel.send("# Daily Digest")
        assert result.success is True
        assert result.channel == "slack"
        assert result.message == "sent"


async def test_send_failure(channel):
    mock_resp = MagicMock()
    mock_resp.status_code = 403
    mock_resp.text = "channel_not_found"

    with patch("backend.services.notification.channels.slack.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        result = await channel.send("# Daily Digest")
        assert result.success is False
        assert "403" in result.message
