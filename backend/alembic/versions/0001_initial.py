"""Initial schema — all core tables.

Generated from backend/database/models/*.py
"""

from alembic import op
import sqlalchemy as sa


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- sources ---
    op.create_table(
        "sources",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("source_type", sa.String(16), nullable=True, comment="official | community | paper | news | social"),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name=op.f("sources_pkey")),
        sa.UniqueConstraint("url", name=op.f("sources_url_key")),
    )
    op.create_index(op.f("idx_sources_kind"), "sources", ["kind"], unique=False)

    # --- articles ---
    op.create_table(
        "articles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("language", sa.String(8), server_default=sa.text("'en'")),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("status", sa.String(16), server_default=sa.text("'raw'")),
        sa.Column("metadata_", sa.JSON(), server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name=op.f("articles_pkey")),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], name=op.f("articles_source_id_fkey")),
    )
    op.create_index(op.f("idx_articles_source"), "articles", ["source_id"], unique=False)
    op.create_index(op.f("idx_articles_status"), "articles", ["status"], unique=False)
    op.create_index(op.f("idx_articles_language"), "articles", ["language"], unique=False)
    op.create_index(op.f("idx_articles_published"), "articles", ["published_at"], unique=False, postgresql_ops={"published_at": "DESC"})

    # --- intelligence_reports ---
    op.create_table(
        "intelligence_reports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("category", sa.String(64), nullable=True),
        sa.Column("importance_score", sa.Float(), nullable=True),
        sa.Column("article_ids", sa.ARRAY(sa.Uuid()), nullable=True),
        sa.Column("agent_run_id", sa.Uuid(), nullable=True),
        sa.Column("generated_by", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name=op.f("intelligence_reports_pkey")),
        sa.CheckConstraint("importance_score >= 0 AND importance_score <= 10", name=op.f("chk_report_score_range")),
        sa.ForeignKeyConstraint(["agent_run_id"], ["agent_runs.id"], name=op.f("intelligence_reports_agent_run_id_fkey")),
    )
    op.create_index(op.f("idx_reports_category"), "intelligence_reports", ["category"], unique=False)
    op.create_index(op.f("idx_reports_importance"), "intelligence_reports", ["importance_score"], unique=False, postgresql_ops={"importance_score": "DESC"})

    # --- knowledge_items ---
    op.create_table(
        "knowledge_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=True),
        sa.Column("article_id", sa.Uuid(), nullable=True),
        sa.Column("report_id", sa.Uuid(), nullable=True),
        sa.Column("tags", sa.ARRAY(sa.String(128)), server_default=sa.text("ARRAY[]::varchar[]")),
        sa.Column("embedding", sa.String(255), nullable=True),
        sa.Column("embedding_model", sa.String(128), nullable=True, comment="Model used for this embedding"),
        sa.Column("embedding_dimension", sa.Integer(), nullable=True, comment="Dimension of the stored vector"),
        sa.Column("external_url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name=op.f("knowledge_items_pkey")),
        sa.ForeignKeyConstraint(["source_id"], ["sources.id"], name=op.f("knowledge_items_source_id_fkey")),
        sa.ForeignKeyConstraint(["article_id"], ["articles.id"], name=op.f("knowledge_items_article_id_fkey")),
        sa.ForeignKeyConstraint(["report_id"], ["intelligence_reports.id"], name=op.f("knowledge_items_report_id_fkey")),
    )
    op.create_index(op.f("idx_knowledge_kind"), "knowledge_items", ["kind"], unique=False)
    op.create_index(op.f("idx_knowledge_article"), "knowledge_items", ["article_id"], unique=False)
    op.create_index(op.f("idx_knowledge_source"), "knowledge_items", ["source_id"], unique=False)
    op.create_index(
        op.f("idx_knowledge_tags"), "knowledge_items", ["tags"], unique=False, postgresql_using="gin"
    )

    # --- tasks ---
    op.create_table(
        "tasks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(16), server_default=sa.text("'pending'")),
        sa.Column("priority", sa.String(8), server_default=sa.text("'medium'")),
        sa.Column("external_id", sa.String(128), nullable=True),
        sa.Column("external_url", sa.Text(), nullable=True),
        sa.Column("agent_run_id", sa.Uuid(), nullable=True),
        sa.Column("knowledge_item_id", sa.Uuid(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name=op.f("tasks_pkey")),
        sa.ForeignKeyConstraint(["agent_run_id"], ["agent_runs.id"], name=op.f("tasks_agent_run_id_fkey")),
        sa.ForeignKeyConstraint(["knowledge_item_id"], ["knowledge_items.id"], name=op.f("tasks_knowledge_item_id_fkey")),
    )
    op.create_index(op.f("idx_tasks_status"), "tasks", ["status"], unique=False)
    op.create_index(op.f("idx_tasks_priority"), "tasks", ["priority"], unique=False)
    op.create_index(op.f("idx_tasks_agent_run"), "tasks", ["agent_run_id"], unique=False)

    # --- agents ---
    op.create_table(
        "agents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("display_name", sa.String(128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("graph_def", sa.JSON(), nullable=False),
        sa.Column("version", sa.String(16), server_default=sa.text("'1.0.0'")),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name=op.f("agents_pkey")),
        sa.UniqueConstraint("name", name=op.f("agents_name_key")),
    )
    op.create_index(op.f("idx_agents_enabled"), "agents", ["enabled"], unique=False, postgresql_where=sa.text("enabled = true"))

    # --- agent_runs ---
    op.create_table(
        "agent_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("agent_id", sa.Uuid(), nullable=False),
        sa.Column("workflow_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(16), server_default=sa.text("'running'")),
        sa.Column("input_payload", sa.JSON(), server_default=sa.text("'{}'::jsonb")),
        sa.Column("output_payload", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.BigInteger(), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("agent_runs_pkey")),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], name=op.f("agent_runs_agent_id_fkey")),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflows.id"], name=op.f("agent_runs_workflow_id_fkey")),
    )
    op.create_index(op.f("idx_runs_agent"), "agent_runs", ["agent_id"], unique=False)
    op.create_index(op.f("idx_runs_workflow"), "agent_runs", ["workflow_id"], unique=False)
    op.create_index(op.f("idx_runs_status"), "agent_runs", ["status"], unique=False)
    op.create_index(op.f("idx_runs_started"), "agent_runs", ["started_at"], unique=False, postgresql_ops={"started_at": "DESC"})

    # --- workflows ---
    op.create_table(
        "workflows",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("schedule_cron", sa.String(64), nullable=True),
        sa.Column("graph_def", sa.JSON(), nullable=False),
        sa.Column("version", sa.String(16), server_default=sa.text("'1.0.0'")),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name=op.f("workflows_pkey")),
    )
    op.create_index(op.f("idx_workflows_enabled"), "workflows", ["enabled"], unique=False, postgresql_where=sa.text("enabled = true"))

    # --- user_preferences ---
    op.create_table(
        "user_preferences",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.String(128), nullable=False),
        sa.Column("key", sa.String(64), nullable=False),
        sa.Column("value", sa.JSON(), nullable=False),
        sa.Column("scope", sa.String(16), server_default=sa.text("'user'")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name=op.f("user_preferences_pkey")),
    )
    op.create_index(op.f("idx_prefs_user_key"), "user_preferences", ["user_id", "key"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("idx_prefs_user_key"), table_name="user_preferences")
    op.drop_table("user_preferences")
    op.drop_index(op.f("idx_workflows_enabled"), table_name="workflows")
    op.drop_table("workflows")
    op.drop_index(op.f("idx_runs_started"), table_name="agent_runs")
    op.drop_index(op.f("idx_runs_status"), table_name="agent_runs")
    op.drop_index(op.f("idx_runs_workflow"), table_name="agent_runs")
    op.drop_index(op.f("idx_runs_agent"), table_name="agent_runs")
    op.drop_table("agent_runs")
    op.drop_index(op.f("idx_agents_enabled"), table_name="agents")
    op.drop_table("agents")
    op.drop_index(op.f("idx_tasks_agent_run"), table_name="tasks")
    op.drop_index(op.f("idx_tasks_priority"), table_name="tasks")
    op.drop_index(op.f("idx_tasks_status"), table_name="tasks")
    op.drop_table("tasks")
    op.drop_index(op.f("idx_knowledge_tags"), table_name="knowledge_items")
    op.drop_index(op.f("idx_knowledge_source"), table_name="knowledge_items")
    op.drop_index(op.f("idx_knowledge_article"), table_name="knowledge_items")
    op.drop_index(op.f("idx_knowledge_kind"), table_name="knowledge_items")
    op.drop_table("knowledge_items")
    op.drop_index(op.f("idx_reports_importance"), table_name="intelligence_reports")
    op.drop_index(op.f("idx_reports_category"), table_name="intelligence_reports")
    op.drop_table("intelligence_reports")
    op.drop_index(op.f("idx_articles_published"), table_name="articles")
    op.drop_index(op.f("idx_articles_language"), table_name="articles")
    op.drop_index(op.f("idx_articles_status"), table_name="articles")
    op.drop_index(op.f("idx_articles_source"), table_name="articles")
    op.drop_table("articles")
    op.drop_index(op.f("idx_sources_kind"), table_name="sources")
    op.drop_table("sources")
