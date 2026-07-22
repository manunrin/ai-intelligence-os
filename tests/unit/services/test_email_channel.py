"""Tests for EmailChannel notification delivery."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.services.notification.channels.email import EmailChannel


@pytest.fixture(autouse=True)
def _mock_settings():
    with patch("backend.services.notification.channels.email.get_settings") as fn:
        s = MagicMock()
        s.smtp_host = "smtp.gmail.com"
        s.smtp_port = 587
        s.smtp_user = "test@example.com"
        s.smtp_password = "secret"
        s.smtp_from = "test@example.com"
        s.smtp_to = "recipient@example.com"
        s.smtp_use_tls = True
        fn.return_value = s
        yield fn


@pytest.fixture
def channel():
    return EmailChannel()


async def test_is_enabled_when_configured():
    ch = EmailChannel()
    assert ch.is_enabled is True


async def test_is_enabled_without_smtp_from():
    with patch("backend.services.notification.channels.email.get_settings") as fn:
        s = MagicMock()
        s.smtp_from = ""
        s.smtp_user = "x"
        s.smtp_password = "y"
        fn.return_value = s
        assert EmailChannel().is_enabled is False


async def test_send_success(channel):
    with patch("backend.services.notification.channels.email.aiosmtplib.send", new_callable=AsyncMock) as mock_send:
        result = await channel.send("# Daily Digest")
        assert result.success is True
        assert result.channel == "email"
        assert result.message == "sent"
        mock_send.assert_called_once()


async def test_send_smtp_exception(channel):
    with patch("backend.services.notification.channels.email.aiosmtplib.send", side_effect=Exception("connection refused")) as mock_send:
        result = await channel.send("# Daily Digest")
        assert result.success is False
        assert "connection refused" in result.message
        mock_send.assert_called_once()


async def test_send_falls_back_to_from_when_no_recipients():
    """When smtp_to is empty, email is sent to smtp_from."""
    with patch("backend.services.notification.channels.email.get_settings") as fn:
        s = MagicMock()
        s.smtp_host = "smtp.gmail.com"
        s.smtp_port = 587
        s.smtp_user = "test@example.com"
        s.smtp_password = "secret"
        s.smtp_from = "sender@example.com"
        s.smtp_to = ""
        s.smtp_use_tls = True
        fn.return_value = s

        with patch("backend.services.notification.channels.email.aiosmtplib.send", new_callable=AsyncMock) as mock_send:
            ch = EmailChannel()
            result = await ch.send("# Digest")
            assert result.success is True
            # Verify the message was built with sender as recipient
            call_kwargs = mock_send.call_args[1]
            msg = call_kwargs["message"]
            assert "sender@example.com" in str(msg["To"])
