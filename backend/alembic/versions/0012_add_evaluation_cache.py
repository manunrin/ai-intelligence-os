"""add evaluation_cache table and evaluator_confidence column

Evaluation cache stores deduplicated results for identical input/output payloads.
evaluator_confidence tracks LLM self-assessed confidence per evaluation.

Revision ID: 0012
Revises: 0011
Create Date: 2026-07-23
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create evaluation_cache table
    op.create_table(
        "evaluation_cache",
        sa.Column("id", sa.CHAR(32), nullable=False),
        sa.Column("content_hash", sa.CHAR(64), nullable=False),
        sa.Column("pipeline_type", sa.String(32), nullable=False),
        sa.Column("score", sa.Float, nullable=False),
        sa.Column("criteria", sa.dialects.postgresql.JSONB, nullable=False),
        sa.Column("evaluator_notes", sa.String(1024), nullable=True),
        sa.Column("model_used", sa.String(128), nullable=True),
        sa.Column(
            "evaluated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_evaluation_cache")),
        sa.UniqueConstraint("content_hash", name=op.f("uq_evaluation_cache_content_hash")),
    )
    op.create_index(
        op.f("ix_evaluation_cache_content_hash"),
        "evaluation_cache",
        ["content_hash"],
        unique=True,
    )

    # Add evaluator_confidence to agent_evaluations
    op.add_column(
        "agent_evaluations",
        sa.Column("evaluator_confidence", sa.Float, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("agent_evaluations", "evaluator_confidence")
    op.drop_index(op.f("ix_evaluation_cache_content_hash"), table_name="evaluation_cache")
    op.drop_table("evaluation_cache")
