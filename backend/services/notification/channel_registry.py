"""Channel registry — instantiate enabled channels and dispatch notifications."""

from __future__ import annotations

import logging

from .channels.base import ChannelBase, DeliveryResult
from .channels.email import EmailChannel
from .channels.slack import SlackChannel
from .channels.telegram import TelegramChannel

logger = logging.getLogger(__name__)

_CHANNEL_MAP: dict[str, type[ChannelBase]] = {
    "email": EmailChannel,
    "telegram": TelegramChannel,
    "slack": SlackChannel,
}


def get_enabled_channels() -> list[ChannelBase]:
    """Return all configured-and-enabled channel instances in a deterministic order."""
    channels: list[ChannelBase] = []
    for name, cls in _CHANNEL_MAP.items():
        inst = cls()
        if inst.is_enabled:
            channels.append(inst)
            logger.info("Enabled notification channel: %s", name)
    return channels


async def send_notifications(
    content: str,
    requested_channels: list[str],
) -> dict[str, str]:
    """Send content to each requested channel that is enabled.

    Returns a per-channel status map: {"email": "sent", "telegram": "failed: ..."}
    """
    enabled = get_enabled_channels()
    if not enabled:
        logger.debug("No notification channels enabled — skipping delivery")
        return {}

    status: dict[str, str] = {}
    for ch in enabled:
        if ch.name not in requested_channels:
            continue
        result = await ch.send(content)
        status[ch.name] = "sent" if result.success else f"failed: {result.message}"
        if not result.success:
            logger.warning("Notification to '%s' failed: %s", ch.name, result.message)
    return status
