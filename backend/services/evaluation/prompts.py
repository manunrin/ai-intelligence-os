"""Prompt templates for agent quality evaluation."""

from __future__ import annotations

_INTELLIGENCE_SYSTEM = """\
You are a quality evaluator for an AI intelligence pipeline. Your job is to assess the \
quality of the pipeline's output based on four criteria.

Evaluate the following output against the original request:\

{input_context}

Output:

{output_content}

Return a JSON object with exactly these keys:
- "score": overall quality score from 0 to 100 (float)
- "criteria": object with per-criterion scores (0-100 floats):
    - "accuracy": how factually correct and well-sourced the output is
    - "relevance": how well the output addresses the original request
    - "actionability": how clearly the output suggests next steps or actions
    - "completeness": how thoroughly the output covers all requested aspects
- "evaluator_notes": brief explanation of strengths, weaknesses, and rationale

Respond ONLY with valid JSON. No markdown fences, no extra text."""

_AUTONOMOUS_SYSTEM = """\
You are a quality evaluator for an autonomous research agent. Your job is to assess the \
quality of the agent's work based on four criteria.

Evaluate the following output against the original task:\

{input_context}

Output:

{output_content}

Return a JSON object with exactly these keys:
- "score": overall quality score from 0 to 100 (float)
- "criteria": object with per-criterion scores (0-100 floats):
    - "accuracy": how factually correct and well-reasoned the output is
    - "relevance": how well the output addresses the autonomous task goal
    - "actionability": how clearly the output suggests next steps or actions
    - "completeness": how thoroughly the output covers all relevant aspects

Respond ONLY with valid JSON. No markdown fences, no extra text."""


def build_intelligence_prompt(input_payload: dict, output_payload: dict) -> list[dict]:
    """Build messages for evaluating an intelligence pipeline run."""
    input_context = _format_input_summary(input_payload)
    output_content = _truncate_for_prompt(output_payload, max_chars=6000)

    system = _INTELLIGENCE_SYSTEM.format(
        input_context=input_context,
        output_content=output_content,
    )
    return [{"role": "system", "content": system}]


def build_autonomous_prompt(input_payload: dict, output_payload: dict) -> list[dict]:
    """Build messages for evaluating an autonomous pipeline run."""
    input_context = _format_input_summary(input_payload)
    output_content = _truncate_for_prompt(output_payload, max_chars=6000)

    system = _AUTONOMOUS_SYSTEM.format(
        input_context=input_context,
        output_content=output_content,
    )
    return [{"role": "system", "content": system}]


def _format_input_summary(payload: dict) -> str:
    """Convert input payload into a readable context summary."""
    lines: list[str] = []
    if "topic" in payload:
        lines.append(f"Topic: {payload['topic']}")
    if "goal" in payload:
        lines.append(f"Goal: {payload['goal']}")
    if "query" in payload:
        lines.append(f"Query: {payload['query']}")
    for key, value in payload.items():
        if key not in ("topic", "goal", "query") and isinstance(value, str):
            lines.append(f"{key}: {value}")
    if not lines:
        return "(no specific input context provided)"
    return "\n".join(lines)


def _truncate_for_prompt(content: dict, *, max_chars: int = 8000) -> str:
    """Serialize content to string and truncate to fit within token budget."""
    import json

    text = json.dumps(content, ensure_ascii=False, default=str)
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n... [truncated]"
