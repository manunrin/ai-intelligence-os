"""Tests for database model extensions."""

import uuid

from backend.database.models.knowledge_item import KnowledgeItem
from backend.database.models.task import Task


def test_knowledge_item_has_language_data():
    """Verify language_data column exists on KnowledgeItem."""
    item = KnowledgeItem(
        title="Test",
        content="Content",
        kind="article",
        language_data={"zh": {"pinyin": "shi4"}},
    )
    assert item.language_data == {"zh": {"pinyin": "shi4"}}


def test_knowledge_item_has_learning_notes():
    """Verify learning_notes column exists on KnowledgeItem."""
    item = KnowledgeItem(
        title="Test",
        content="Content",
        kind="reference",
        learning_notes="Important concept",
    )
    assert item.learning_notes == "Important concept"


def test_task_has_generated_by_agent():
    """Verify generated_by_agent column exists on Task."""
    agent_id = uuid.uuid4()
    task = Task(title="Test task", generated_by_agent=agent_id)
    assert task.generated_by_agent == agent_id
