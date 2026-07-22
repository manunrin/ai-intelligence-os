"""add agent run persistence columns for LangGraph checkpoint support

Revision ID: 0007_add_agent_run_persistence
Revises: 0006_add_agent_runtime_tracking
Create Date: 2026-07-22
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0007_add_agent_run_persistence"
down_revision: Union[str, None] = "0006_add_agent_runtime_tracking"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add thread_id column for LangGraph checkpoint thread identification
    op.add_column(
        "agent_runs",
        sa.Column(
            "thread_id",
            sa.String(128),
            nullable=True,
        ),
    )

    # Add index on thread_id for lookup performance
    op.create_index(
        op.f("ix_agent_runs_thread_id"),
        "agent_runs",
        ["thread_id"],
        unique=False,
    )

    # Add recovered_at column to track when stale runs were recovered
    op.add_column(
        "agent_runs",
        sa.Column(
            "recovered_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("agent_runs", "recovered_at")
    op.drop_index(op.f("ix_agent_runs_thread_id"), table_name="agent_runs")
    op.drop_column("agent_runs", "thread_id")
