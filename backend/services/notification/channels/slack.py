"""Slack notification channel (incoming webhook)."""

from __future__ import annotations

import logging

import httpx

from ....config import get_settings
from .base import ChannelBase, DeliveryResult

logger = logging.getLogger(__name__)


class SlackChannel(ChannelBase):
    name = "slack"

    @property
    def is_enabled(self) -> bool:
        s = get_settings()
        return bool(s.slack_webhook_url.strip())

    async def send(self, content: str) -> DeliveryResult:
        s = get_settings()
        if not self.is_enabled:
            return DeliveryResult(
                success=False,
                channel=self.name,
                message="Slack channel disabled (missing webhook URL)",
            )

        url = s.slack_webhook_url.strip()
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, json={"text": content})

            if resp.status_code == 200:
                return DeliveryResult(success=True, channel=self.name, message="sent")

            logger.warning("Slack webhook returned %s: %s", resp.status_code, resp.text[:200])
            return DeliveryResult(
                success=False,
                channel=self.name,
                message=f"{resp.status_code}: {resp.text[:200]}",
            )
        except httpx.HTTPError as exc:
            logger.warning("Slack delivery failed: %s", exc)
            return DeliveryResult(success=False, channel=self.name, message=str(exc))
        except Exception as exc:
            logger.error("Unexpected Slack error: %s", exc)
            return DeliveryResult(success=False, channel=self.name, message=str(exc))
