"""add user_id ownership columns

Revision ID: 0004_add_user_ownership
Revises: 0003_add_users_table
Create Date: 2026-07-16
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004_add_user_ownership"
down_revision: Union[str, None] = "0003_add_users_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add user_id to articles
    op.add_column(
        "articles",
        sa.Column(
            "user_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_index(op.f("ix_articles_user_id"), "articles", ["user_id"], unique=False)
    op.create_foreign_key(
        op.f("fk_articles_user_id_users"),
        "articles",
        "users",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Add user_id to tasks
    op.add_column(
        "tasks",
        sa.Column(
            "user_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_index(op.f("ix_tasks_user_id"), "tasks", ["user_id"], unique=False)
    op.create_foreign_key(
        op.f("fk_tasks_user_id_users"),
        "tasks",
        "users",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Add user_id to knowledge_items
    op.add_column(
        "knowledge_items",
        sa.Column(
            "user_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_index(op.f("ix_knowledge_items_user_id"), "knowledge_items", ["user_id"], unique=False)
    op.create_foreign_key(
        op.f("fk_knowledge_items_user_id_users"),
        "knowledge_items",
        "users",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Add user_id to intelligence_reports
    op.add_column(
        "intelligence_reports",
        sa.Column(
            "user_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_index(op.f("ix_intelligence_reports_user_id"), "intelligence_reports", ["user_id"], unique=False)
    op.create_foreign_key(
        op.f("fk_intelligence_reports_user_id_users"),
        "intelligence_reports",
        "users",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Add user_id to agent_runs
    op.add_column(
        "agent_runs",
        sa.Column(
            "user_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_index(op.f("ix_agent_runs_user_id"), "agent_runs", ["user_id"], unique=False)
    op.create_foreign_key(
        op.f("fk_agent_runs_user_id_users"),
        "agent_runs",
        "users",
        ["user_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("fk_agent_runs_user_id_users"), "agent_runs", type_="foreignkey")
    op.drop_index(op.f("ix_agent_runs_user_id"), table_name="agent_runs")
    op.drop_column("agent_runs", "user_id")

    op.drop_constraint(op.f("fk_intelligence_reports_user_id_users"), "intelligence_reports", type_="foreignkey")
    op.drop_index(op.f("ix_intelligence_reports_user_id"), table_name="intelligence_reports")
    op.drop_column("intelligence_reports", "user_id")

    op.drop_constraint(op.f("fk_knowledge_items_user_id_users"), "knowledge_items", type_="foreignkey")
    op.drop_index(op.f("ix_knowledge_items_user_id"), table_name="knowledge_items")
    op.drop_column("knowledge_items", "user_id")

    op.drop_constraint(op.f("fk_tasks_user_id_users"), "tasks", type_="foreignkey")
    op.drop_index(op.f("ix_tasks_user_id"), table_name="tasks")
    op.drop_column("tasks", "user_id")

    op.drop_constraint(op.f("fk_articles_user_id_users"), "articles", type_="foreignkey")
    op.drop_index(op.f("ix_articles_user_id"), table_name="articles")
    op.drop_column("articles", "user_id")
