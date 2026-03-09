"""Initial schema — all core tables.

Revision ID: 0001
Revises:
Create Date: 2026-03-09
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "runs",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("current_stage", sa.String(50), server_default="theme_intake"),
        sa.Column("status", sa.String(20), server_default="pending"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.Column("checkpoint_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("job_id", sa.String(100), nullable=True),
    )

    op.create_table(
        "companies",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=False), nullable=False, index=True),
        sa.Column("canonical_name", sa.String(500), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("disposition", sa.String(30), server_default="primary"),
        sa.Column("ownership_tier", sa.String(20), server_default="unknown"),
        sa.Column("total_score", sa.Float(), nullable=True),
        sa.Column("eligible_for_outreach", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("workflow_stage", sa.String(50), server_default="name_generation"),
        sa.Column("review_required", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()")),
    )

    op.create_table(
        "theme_recommendations",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=False), nullable=False, index=True),
        sa.Column("subvertical_name", sa.String(300), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("recommendation_status", sa.String(30), server_default="watchlist"),
        sa.Column("total_recommendation_score", sa.Float(), server_default="0.0"),
        sa.Column("user_selected", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("user_added", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
    )

    op.create_table(
        "source_recommendations",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=False), nullable=False, index=True),
        sa.Column("source_name", sa.String(500), nullable=False),
        sa.Column("source_type", sa.String(100), server_default=""),
        sa.Column("data", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("user_selected", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("user_added", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
    )

    op.create_table(
        "checkpoints",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=False), nullable=False, index=True),
        sa.Column("stage", sa.String(50), nullable=False),
        sa.Column("company_count", sa.Integer(), server_default="0"),
        sa.Column("artifact_path", sa.Text(), server_default=""),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
    )

    op.create_table(
        "review_queue",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=False), nullable=False, index=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("reason", sa.String(50), nullable=False),
        sa.Column("details", sa.Text(), server_default=""),
        sa.Column("data", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("resolved", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("resolution", sa.String(100), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
    )

    op.create_table(
        "export_manifests",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=False), nullable=False, index=True),
        sa.Column("data", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
    )

    op.create_table(
        "company_evidence",
        sa.Column("id", postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column("company_id", postgresql.UUID(as_uuid=False), nullable=False, index=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=False), nullable=False, index=True),
        sa.Column("connector_name", sa.String(100), nullable=False),
        sa.Column("raw_evidence", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("ai_provenance", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("company_evidence")
    op.drop_table("export_manifests")
    op.drop_table("review_queue")
    op.drop_table("checkpoints")
    op.drop_table("source_recommendations")
    op.drop_table("theme_recommendations")
    op.drop_table("companies")
    op.drop_table("runs")
