"""Tests for KnowledgeAgent schemas and output parsing."""

import pytest

from backend.agents.knowledge.schemas import KnowledgeInput, KnowledgeOutput


def test_knowledge_input_validation():
    data = {"title": "AI News", "content": "Test content", "source": "blog"}
    input_model = KnowledgeInput.model_validate(data)
    assert input_model.title == "AI News"
    assert input_model.source == "blog"


def test_knowledge_input_defaults():
    input_model = KnowledgeInput(title="Only title")
    assert input_model.content == ""
    assert input_model.tags == []


@pytest.mark.parametrize(
    ("raw", "expected_kind"),
    [
        ("This is a tutorial on how to use LLMs", "tutorial"),
        ("Research paper findings show improved accuracy", "research"),
        ("Announcing the new release of Model X", "news"),
        ("Here is some general information about the topic", "article"),
    ],
)
def test_knowledge_output_kind_detection(raw: str, expected_kind: str):
    output = KnowledgeOutput.from_llm_response(raw, title="Test", source="test")
    assert output.kind == expected_kind


def test_knowledge_output_summary_fallback():
    output = KnowledgeOutput.from_llm_response("Some random text", title="My Title", source="blog")
    assert "My Title" in output.summary


def test_knowledge_output_key_points_extraction():
    raw = """Summary: This is about AI.
- Point one
- Point two
- Point three"""
    output = KnowledgeOutput.from_llm_response(raw, title="Test", source="test")
    assert len(output.key_points) >= 2


def test_knowledge_output_notion_structure():
    raw = "Key insight about machine learning."
    output = KnowledgeOutput.from_llm_response(raw, title="ML Insight", source="test")
    assert "ML Insight" in output.notion_structure
    assert output.notion_structure.startswith("## ML Insight")
