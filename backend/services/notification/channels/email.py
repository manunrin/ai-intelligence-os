"""SMTP email notification channel."""

from __future__ import annotations

import logging

import aiosmtplib
from aiosmtplib import SMTPException

from ....config import get_settings
from .base import ChannelBase, DeliveryResult

logger = logging.getLogger(__name__)


class EmailChannel(ChannelBase):
    name = "email"

    @property
    def is_enabled(self) -> bool:
        s = get_settings()
        return bool(s.smtp_from and s.smtp_user and s.smtp_password)

    async def send(self, content: str) -> DeliveryResult:
        s = get_settings()
        if not self.is_enabled:
            return DeliveryResult(
                success=False,
                channel=self.name,
                message="Email channel disabled (missing config)",
            )

        recipients = [r.strip() for r in s.smtp_to.split(",") if r.strip()] or [s.smtp_from]

        try:
            await aiosmtplib.send(
                message=_build_email(content, s.smtp_from, recipients),
                hostname=s.smtp_host,
                port=s.smtp_port,
                username=s.smtp_user,
                password=s.smtp_password,
                use_tls=s.smtp_use_tls,
            )
            logger.info("Email notification sent from=%s to=%s", s.smtp_from, ", ".join(recipients))
            return DeliveryResult(success=True, channel=self.name, message="sent")
        except SMTPException as exc:
            logger.warning("Email delivery failed: %s", exc)
            return DeliveryResult(success=False, channel=self.name, message=str(exc))
        except Exception as exc:
            logger.error("Unexpected email error: %s", exc)
            return DeliveryResult(success=False, channel=self.name, message=str(exc))


def _build_email(content: str, from_addr: str, to_addrs: list[str]) -> "Email":
    """Build a multipart/plain+html email message."""
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "AI Intelligence OS — Daily Digest"
    msg["From"] = from_addr
    msg["To"] = ", ".join(to_addrs)

    # Strip leading/trailing whitespace and truncate to reasonable length
    plain = content[:8000]
    html = f"<pre>{_escape_html(plain)}</pre>"

    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))
    return msg  # type: ignore[return-value]


def _escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
