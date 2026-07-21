"""Add google_form_url and google_sheet_id to industry_tours

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-20 14:50:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "industry_tours",
        sa.Column("google_form_url", sa.String(500), nullable=True),
    )
    op.add_column(
        "industry_tours",
        sa.Column("google_sheet_id", sa.String(200), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("industry_tours", "google_sheet_id")
    op.drop_column("industry_tours", "google_form_url")
