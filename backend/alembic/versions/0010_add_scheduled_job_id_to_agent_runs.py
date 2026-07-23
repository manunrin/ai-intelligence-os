"""add scheduled_job_id to agent_runs

Revision ID: 0010
Revises: 0009
Create Date: 2026-07-23

Links agent_runs back to the ScheduledJob that triggered them, enabling
execution history queries without a separate history table.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agent_runs",
        sa.Column(
            "scheduled_job_id",
            sa.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_index(
        op.f("ix_agent_runs_scheduled_job_id"),
        "agent_runs",
        ["scheduled_job_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_agent_runs_scheduled_job_id",
        "agent_runs",
        "scheduled_jobs",
        ["scheduled_job_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_agent_runs_scheduled_job_id",
        "agent_runs",
        type_="foreignkey",
    )
    op.drop_index(op.f("ix_agent_runs_scheduled_job_id"), table_name="agent_runs")
    op.drop_column("agent_runs", "scheduled_job_id")
