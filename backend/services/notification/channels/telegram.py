"""Telegram notification channel."""

from __future__ import annotations

import logging

import httpx

from ....config import get_settings
from .base import ChannelBase, DeliveryResult

TELEGRAM_API_BASE = "https://api.telegram.org"
_MAX_TELEGRAM_MSG = 4096
_TRUNCATION_NOTICE = "\n\n[truncated]"
logger = logging.getLogger(__name__)


class TelegramChannel(ChannelBase):
    name = "telegram"

    @property
    def is_enabled(self) -> bool:
        s = get_settings()
        return bool(s.telegram_bot_token.strip())

    async def send(self, content: str) -> DeliveryResult:
        s = get_settings()
        if not self.is_enabled:
            return DeliveryResult(
                success=False,
                channel=self.name,
                message="Telegram channel disabled (missing bot token)",
            )

        token = s.telegram_bot_token.strip()
        chat_ids = [cid.strip() for cid in s.telegram_chat_ids.split(",") if cid.strip()]
        if not chat_ids:
            return DeliveryResult(
                success=False,
                channel=self.name,
                message="Telegram channel disabled (no chat IDs configured)",
            )

        url = f"{TELEGRAM_API_BASE}/bot{token}/sendMessage"

        # Truncate to Telegram's 4096 char limit (minus truncation notice)
        truncated = len(content) > _MAX_TELEGRAM_MSG
        body = content[:_MAX_TELEGRAM_MSG - len(_TRUNCATION_NOTICE)] if truncated else content
        if truncated:
            body += _TRUNCATION_NOTICE

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                errors: list[str] = []
                for chat_id in chat_ids:
                    resp = await client.post(url, json={"text": body, "parse_mode": "MarkdownV2", "chat_id": chat_id})
                    if resp.status_code != 200:
                        err_body = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                        msg = err_body.get("description", resp.text)[:200]
                        errors.append(f"chat={chat_id}: {msg}")

            if errors:
                detail = "; ".join(errors)
                logger.warning("Telegram partial delivery failure: %s", detail)
                return DeliveryResult(
                    success=False,
                    channel=self.name,
                    message=detail,
                )

            return DeliveryResult(success=True, channel=self.name, message=f"sent to {len(chat_ids)} recipient(s)")
        except httpx.HTTPError as exc:
            logger.warning("Telegram delivery failed: %s", exc)
            return DeliveryResult(success=False, channel=self.name, message=str(exc))
        except Exception as exc:
            logger.error("Unexpected Telegram error: %s", exc)
            return DeliveryResult(success=False, channel=self.name, message=str(exc))
