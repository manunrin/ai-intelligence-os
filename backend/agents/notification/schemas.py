"""Notification Agent schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class NotificationInput(BaseModel):
    """Input schema for NotificationAgent."""

    date: str = Field(description="Date for the digest (YYYY-MM-DD)")
    news: list[dict[str, str]] = Field(default_factory=list, description="Today's news items")
    knowledge: list[dict[str, str]] = Field(default_factory=list, description="Today's knowledge entries")
    tasks: list[dict[str, str]] = Field(default_factory=list, description="Today's tasks")
    channels: list[str] = Field(
        default=["wechat", "telegram", "email"],
        description="Target delivery channels",
    )


class NotificationOutput(BaseModel):
    """Structured output from NotificationAgent."""

    markdown: str = Field(description="Markdown-formatted notification content")
    channels: list[str] = Field(description="Target channels")

    @classmethod
    def from_llm_response(cls, raw: str, channels: list[str]) -> "NotificationOutput":
        """Parse LLM response into NotificationOutput."""
        return cls(markdown=raw, channels=channels)
