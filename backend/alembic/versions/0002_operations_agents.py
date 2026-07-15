"""Alembic migration — add language_data and learning_notes to knowledge_items,
generated_by_agent to tasks."""

from alembic import op
import sqlalchemy as sa

revision = "0002_operations_agents"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # knowledge_items: add language_data (JSONB) and learning_notes (TEXT)
    op.add_column(
        "knowledge_items",
        sa.Column("language_data", sa.JSON(), nullable=True),
    )
    op.add_column(
        "knowledge_items",
        sa.Column("learning_notes", sa.Text(), nullable=True),
    )

    # tasks: add generated_by_agent (UUID FK to agents.id)
    op.add_column(
        "tasks",
        sa.Column("generated_by_agent", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        op.f("tasks_generated_by_agent_fkey"),
        "tasks",
        "agents",
        ["generated_by_agent"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(op.f("tasks_generated_by_agent_fkey"), "tasks", type_="foreignkey")
    op.drop_column("tasks", "generated_by_agent")
    op.drop_column("knowledge_items", "learning_notes")
    op.drop_column("knowledge_items", "language_data")
