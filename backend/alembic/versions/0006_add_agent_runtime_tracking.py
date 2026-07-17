"""add agent runtime tracking columns and stage progress table

Revision ID: 0006_add_agent_runtime_tracking
Revises: 0005_add_audit_logs
Create Date: 2026-07-17
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0006_add_agent_runtime_tracking"
down_revision: Union[str, None] = "0005_add_audit_logs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Widen status column from VARCHAR(16) to VARCHAR(32)
    op.alter_column(
        "agent_runs",
        "status",
        type_=sa.String(32),
        existing_type=sa.String(16),
    )

    # Add stage column
    op.add_column(
        "agent_runs",
        sa.Column(
            "stage",
            sa.String(64),
            nullable=False,
            server_default="initializing",
        ),
    )

    # Create agent_stage_progress table
    op.create_table(
        "agent_stage_progress",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.func.gen_random_uuid(),
        ),
        sa.Column(
            "agent_run_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agent_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("stage_name", sa.String(64), nullable=False),
        sa.Column("stage_order", sa.Integer, nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("input_summary", sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column("output_summary", sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Integer, nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "finished_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.UniqueConstraint("agent_run_id", "stage_name"),
    )

    op.create_index(
        op.f("ix_agent_stage_progress_run"),
        "agent_stage_progress",
        ["agent_run_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_agent_stage_progress_run"), table_name="agent_stage_progress")
    op.drop_table("agent_stage_progress")

    op.drop_column("agent_runs", "stage")

    op.alter_column(
        "agent_runs",
        "status",
        type_=sa.String(16),
        existing_type=sa.String(32),
    )
