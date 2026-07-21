
from sqlalchemy import (
    BigInteger, Boolean, Column, DateTime, Enum, ForeignKey,
    Index, Integer, String, Text, text,
)
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func

from db.enums import FormStatus, QuestionType


class Base(DeclarativeBase):
    pass


class Form(Base):
    __tablename__ = "forms"

    id = Column(BigInteger, primary_key=True)
    guild_id = Column(BigInteger, nullable=False, index=True)
    channel_id = Column(BigInteger, nullable=False)
    type = Column(String(50), nullable=False)
    title = Column(String(500), nullable=False)
    created_by = Column(BigInteger, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    status = Column(Enum(FormStatus), nullable=False, default=FormStatus.active)
    anonymous = Column(Boolean, nullable=False, default=False)

    questions = relationship(
        "Question", back_populates="form",
        cascade="all, delete-orphan", passive_deletes=True,
        order_by="Question.order",
    )


class Question(Base):
    __tablename__ = "questions"

    id = Column(BigInteger, primary_key=True)
    form_id = Column(ForeignKey("forms.id", ondelete="CASCADE"), nullable=False, index=True)
    prompt = Column(String(1000), nullable=False)
    question_type = Column(Enum(QuestionType), nullable=False)
    order = Column(Integer, nullable=False, default=0)

    form = relationship("Form", back_populates="questions")
    options = relationship(
        "Option", back_populates="question",
        cascade="all, delete-orphan", passive_deletes=True,
        order_by="Option.order",
    )
    responses = relationship(
        "Response", back_populates="question",
        cascade="all, delete-orphan", passive_deletes=True,
    )


class Option(Base):
    __tablename__ = "options"

    id = Column(BigInteger, primary_key=True)
    question_id = Column(ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)
    text = Column(String(500), nullable=False)
    order = Column(Integer, nullable=False, default=0)

    question = relationship("Question", back_populates="options")
    responses = relationship("Response", back_populates="option")


class Response(Base):
    """
    Stores user responses to questions.

    Constraint strategy:
      - single_choice / text: one row per (question_id, user_id).
        Enforced by partial unique index uq_response_single_per_user.
      - multi_choice: multiple rows per (question_id, user_id), one per
        chosen option. Enforced by partial unique index
        uq_response_option_per_user which prevents the same user voting
        for the same option twice.

    question_type is denormalised here so the partial unique indexes can
    reference it without a join.  The application sets it on insert; a
    DB trigger mirrors it from the parent question as a safety net.
    """

    __tablename__ = "responses"

    id = Column(BigInteger, primary_key=True)
    question_id = Column(ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(BigInteger, nullable=False)
    username = Column(String(100), nullable=False, server_default="")
    option_id = Column(ForeignKey("options.id", ondelete="SET NULL"), nullable=True, index=True)
    text_answer = Column(Text, nullable=True)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    question_type = Column(
        Enum(QuestionType),
        nullable=False,
        comment="Denormalised from questions table for partial-index enforcement",
    )

    question = relationship("Question", back_populates="responses")
    option = relationship("Option", back_populates="responses")

    __table_args__ = (
        Index(
            "uq_response_single_per_user",
            "question_id", "user_id",
            unique=True,
            postgresql_where=text(
                "question_type IN ('single_choice', 'text')"
            ),
        ),
        Index(
            "uq_response_option_per_user",
            "question_id", "user_id", "option_id",
            unique=True,
            postgresql_where=text("option_id IS NOT NULL"),
        ),
    )


class IndustryTour(Base):
    __tablename__ = "industry_tours"

    id = Column(BigInteger, primary_key=True)
    name = Column(String(200), nullable=False)
    date = Column(DateTime(timezone=True), nullable=False)
    company = Column(String(200), nullable=False)
    google_form_url = Column(String(500), nullable=True)
    google_sheet_id = Column(String(200), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    feedback = relationship(
        "TourFeedback", back_populates="tour",
        cascade="all, delete-orphan", passive_deletes=True,
    )


class TourFeedback(Base):
    __tablename__ = "tour_feedback"

    id = Column(BigInteger, primary_key=True)
    tour_id = Column(ForeignKey("industry_tours.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(BigInteger, nullable=False, index=True)
    student_name = Column(String(100), nullable=False, server_default="")
    rating = Column(Integer, nullable=True)
    comments = Column(Text, nullable=True)
    submitted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    tour = relationship("IndustryTour", back_populates="feedback")


class Coach(Base):
    __tablename__ = "coaches"

    id = Column(BigInteger, primary_key=True)
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
