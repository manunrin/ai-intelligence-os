"""Tests for TelegramChannel notification delivery."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.services.notification.channels.telegram import TelegramChannel


@pytest.fixture(autouse=True)
def _mock_settings():
    with patch("backend.services.notification.channels.telegram.get_settings") as fn:
        s = MagicMock()
        s.telegram_bot_token = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
        s.telegram_chat_ids = "123456789,@testuser"
        fn.return_value = s
        yield fn


@pytest.fixture
def channel():
    return TelegramChannel()


async def test_is_enabled_when_configured():
    ch = TelegramChannel()
    assert ch.is_enabled is True


async def test_is_enabled_without_token():
    with patch("backend.services.notification.channels.telegram.get_settings") as fn:
        s = MagicMock()
        s.telegram_bot_token = ""
        s.telegram_chat_ids = "123"
        fn.return_value = s
        assert TelegramChannel().is_enabled is False


async def test_send_success(channel):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"content-type": "application/json"}
    mock_resp.json.return_value = {}

    with patch("backend.services.notification.channels.telegram.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        result = await channel.send("# Daily Digest")
        assert result.success is True
        assert result.channel == "telegram"
        assert "sent to 2" in result.message
        # Verify chat_id was included in each call
        assert mock_client.post.call_count == 2


async def test_send_api_error(channel):
    """When a chat_id call fails, error is captured."""
    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.headers = {"content-type": "application/json"}
    mock_resp.json.return_value = {"description": "Chat not found"}
    mock_resp.text = "Bad Request"

    with patch("backend.services.notification.channels.telegram.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        result = await channel.send("# Daily Digest")
        assert result.success is False
        assert "chat not found" in result.message.lower()


async def test_send_no_chat_ids():
    """When no chat IDs are configured, send returns failure."""
    with patch("backend.services.notification.channels.telegram.get_settings") as fn:
        s = MagicMock()
        s.telegram_bot_token = "123:abc"
        s.telegram_chat_ids = ""
        fn.return_value = s

        result = await TelegramChannel().send("# Digest")
        assert result.success is False
        assert "no chat ids configured" in result.message.lower()


async def test_send_truncates_long_content(channel):
    """Content over 4096 chars should be truncated with notice."""
    long_content = "#" * 5000
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.headers = {"content-type": "application/json"}
    mock_resp.json.return_value = {}

    with patch("backend.services.notification.channels.telegram.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        result = await channel.send(long_content)
        assert result.success is True
        call_args = mock_client.post.call_args
        sent_text = call_args[1]["json"]["text"]
        assert len(sent_text) <= 4096
        assert "[truncated]" in sent_text
