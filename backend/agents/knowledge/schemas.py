"""Knowledge Agent schemas."""

from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import BaseModel, Field


class KnowledgeInput(BaseModel):
    """Input schema for KnowledgeAgent."""

    title: str = Field(description="Content title")
    content: str = Field(default="", description="Raw or processed content")
    analysis: str = Field(default="", description="Prior analysis results")
    source: str = Field(default="", description="Content source identifier")
    tags: list[str] = Field(default_factory=list, description="Content tags")


@dataclass
class KnowledgeOutput:
    """Structured output from KnowledgeAgent."""

    kind: str
    summary: str
    key_points: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    notion_structure: str = ""

    @classmethod
    def from_llm_response(cls, raw: str, title: str, source: str = "") -> "KnowledgeOutput":
        """Parse an LLM text response into a KnowledgeOutput.

        Falls back gracefully when the response is not in structured format.
        """
        lines = [l.strip() for l in raw.splitlines() if l.strip()]
        key_points: list[str] = []
        summary = ""
        kind = "article"

        for line in lines:
            lower = line.lower().strip()
            if lower.startswith(("summary", "tl;dr", "overview")):
                summary = line.split(":", 1)[-1].strip()
            elif lower.startswith(("point", "•", "-", "1.", "2.", "3.")):
                key_points.append(line.lstrip("•-0123456789. ").strip())
            else:
                key_points.append(line)

        if not summary:
            summary = f"Knowledge extracted from '{title}' ({source})"

        if any(w in raw.lower() for w in ("tutorial", "how-to", "guide", "learn")):
            kind = "tutorial"
        elif any(w in raw.lower() for w in ("research", "paper", "study", "analysis")):
            kind = "research"
        elif any(w in raw.lower() for w in ("news", "update", "release", "announcement")):
            kind = "news"

        notion_structure = f"## {title}\n\n{summary}\n\n### Key Points\n" + "\n".join(f"- {p}" for p in key_points[:10])

        return cls(
            kind=kind,
            summary=summary,
            key_points=key_points[:20],
            notion_structure=notion_structure,
        )
