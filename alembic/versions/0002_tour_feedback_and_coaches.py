"""Add industry_tours, tour_feedback, and coaches tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-13 14:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "industry_tours",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("company", sa.String(200), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "tour_feedback",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("tour_id", sa.BigInteger(), nullable=False),
        sa.Column("student_id", sa.BigInteger(), nullable=False),
        sa.Column("student_name", sa.String(100), nullable=False, server_default=""),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column("comments", sa.Text(), nullable=True),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tour_id"], ["industry_tours.id"],
            name="fk_tour_feedback_tour_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_tour_feedback_tour_id"), "tour_feedback", ["tour_id"]
    )
    op.create_index(
        op.f("ix_tour_feedback_student_id"), "tour_feedback", ["student_id"]
    )

    op.create_table(
        "coaches",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_coaches_email"),
    )


def downgrade() -> None:
    op.drop_table("coaches")
    op.drop_index(op.f("ix_tour_feedback_student_id"), table_name="tour_feedback")
    op.drop_index(op.f("ix_tour_feedback_tour_id"), table_name="tour_feedback")
    op.drop_table("tour_feedback")
    op.drop_table("industry_tours")
