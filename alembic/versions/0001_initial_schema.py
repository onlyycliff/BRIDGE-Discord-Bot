"""Initial database schema — forms, questions, options, responses

Revision ID: 0001
Revises:
Create Date: 2026-07-07 11:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "forms",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("guild_id", sa.BigInteger(), nullable=False),
        sa.Column("channel_id", sa.BigInteger(), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("created_by", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("draft", "active", "closed", name="formstatus"),
            nullable=False,
            server_default="active",
        ),
        sa.Column("anonymous", sa.Boolean(), nullable=False, server_default="false"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_forms_guild_id"), "forms", ["guild_id"])

    op.create_table(
        "questions",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("form_id", sa.BigInteger(), nullable=False),
        sa.Column("prompt", sa.String(1000), nullable=False),
        sa.Column(
            "question_type",
            sa.Enum(
                "single_choice", "multi_choice", "text",
                name="questiontype",
            ),
            nullable=False,
        ),
        sa.Column("order", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(
            ["form_id"], ["forms.id"],
            name="fk_questions_form_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_questions_form_id"), "questions", ["form_id"])

    op.create_table(
        "options",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("question_id", sa.BigInteger(), nullable=False),
        sa.Column("text", sa.String(500), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(
            ["question_id"], ["questions.id"],
            name="fk_options_question_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_options_question_id"), "options", ["question_id"])

    op.create_table(
        "responses",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("question_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(100), nullable=False, server_default=""),
        sa.Column("option_id", sa.BigInteger(), nullable=True),
        sa.Column("text_answer", sa.Text(), nullable=True),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "question_type",
            sa.Enum(
                "single_choice", "multi_choice", "text",
                name="questiontype",
            ),
            nullable=False,
            comment="Denormalised from questions table for partial-index enforcement",
        ),
        sa.ForeignKeyConstraint(
            ["question_id"], ["questions.id"],
            name="fk_responses_question_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["option_id"], ["options.id"],
            name="fk_responses_option_id",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_responses_question_id"), "responses", ["question_id"])
    op.create_index(op.f("ix_responses_option_id"), "responses", ["option_id"])

    op.create_index(
        "uq_response_single_per_user",
        "responses",
        ["question_id", "user_id"],
        unique=True,
        postgresql_where=sa.text(
            "question_type IN ('single_choice', 'text')"
        ),
    )
    op.create_index(
        "uq_response_option_per_user",
        "responses",
        ["question_id", "user_id", "option_id"],
        unique=True,
        postgresql_where=sa.text("option_id IS NOT NULL"),
    )

    op.create_index(
        "ix_responses_user_id",
        "responses",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_responses_user_id", table_name="responses")
    op.drop_index("uq_response_option_per_user", table_name="responses")
    op.drop_index("uq_response_single_per_user", table_name="responses")
    op.drop_index(op.f("ix_responses_option_id"), table_name="responses")
    op.drop_index(op.f("ix_responses_question_id"), table_name="responses")
    op.drop_table("responses")
    op.drop_index(op.f("ix_options_question_id"), table_name="options")
    op.drop_table("options")
    op.drop_index(op.f("ix_questions_form_id"), table_name="questions")
    op.drop_table("questions")
    op.drop_index(op.f("ix_forms_guild_id"), table_name="forms")
    op.drop_table("forms")

    op.execute("DROP TYPE IF EXISTS questiontype")
    op.execute("DROP TYPE IF EXISTS formstatus")
