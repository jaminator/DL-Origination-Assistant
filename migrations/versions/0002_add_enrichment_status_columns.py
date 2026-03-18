"""Add enrichment status columns to companies table.

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-18
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: str = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "companies",
        sa.Column("bizapi_status", sa.String(20), server_default="pending"),
    )
    op.add_column(
        "companies",
        sa.Column("ciq_status", sa.String(20), server_default="pending"),
    )
    op.add_column(
        "companies",
        sa.Column("bizapi_duns", sa.String(20), nullable=True),
    )
    op.add_column(
        "companies",
        sa.Column("ciq_entity_id", sa.String(50), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("companies", "ciq_entity_id")
    op.drop_column("companies", "bizapi_duns")
    op.drop_column("companies", "ciq_status")
    op.drop_column("companies", "bizapi_status")
