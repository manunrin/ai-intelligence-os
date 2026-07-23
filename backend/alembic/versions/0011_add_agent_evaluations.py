"""add agent_evaluations table

Revision ID: 0011
Revises: 0010
Create Date: 2026-07-23

Stores quality evaluation results for completed agent runs.
Evaluation runs outside the LangGraph pipeline, after executor
completion and before run finalization.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_evaluations",
        sa.Column("id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_run_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("pipeline_type", sa.String(32), nullable=False),
        sa.Column("score", sa.Float, nullable=False),
        sa.Column("criteria", sa.dialects.postgresql.JSONB, nullable=False),
        sa.Column(
            "evaluated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_agent_evaluations")),
        sa.ForeignKeyConstraint(
            ["agent_run_id"],
            ["agent_runs.id"],
            name=op.f("fk_agent_evaluations_agent_run_id"),
            ondelete="CASCADE",
        ),
    )
    op.create_index(
        op.f("ix_agent_evaluations_agent_run_id"),
        "agent_evaluations",
        ["agent_run_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_agent_evaluations_agent_run_id"),
        table_name="agent_evaluations",
    )
    op.drop_table("agent_evaluations")
