"""Tests for database models — structure, constraints, cascade behaviour."""

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from db.enums import FormStatus, QuestionType
from db.models import Base, Form, Option, Question, Response


class TestModelSchema:
    """Verify table structure matches expectations (no DB needed)."""

    def test_tables_registered(self):
        tables = Base.metadata.tables
        assert "forms" in tables
        assert "questions" in tables
        assert "options" in tables
        assert "responses" in tables

    def test_enum_values(self):
        assert list(FormStatus) == [
            FormStatus.draft, FormStatus.active, FormStatus.closed,
        ]
        assert list(QuestionType) == [
            QuestionType.single_choice,
            QuestionType.multi_choice,
            QuestionType.text,
        ]

    def test_foreign_key_columns(self):
        fk_map = {}
        for fk in Form.__table__.foreign_key_constraints:
            for col in fk.columns:
                fk_map[col.name] = fk
        question_fks = {
            col.name for col in Question.__table__.columns
            if col.foreign_keys
        }
        option_fks = {
            col.name for col in Option.__table__.columns
            if col.foreign_keys
        }
        response_fks = {
            col.name for col in Response.__table__.columns
            if col.foreign_keys
        }
        assert "form_id" in question_fks
        assert "question_id" in option_fks
        assert "question_id" in response_fks
        assert "option_id" in response_fks

    def test_response_indexes(self):
        indexes = {i.name for i in Response.__table__.indexes}
        assert "uq_response_single_per_user" in indexes
        assert "uq_response_option_per_user" in indexes
        assert "ix_responses_question_id" in indexes
        assert "ix_responses_option_id" in indexes

    def test_ondelete_cascade_question(self):
        for fk in Question.__table__.foreign_key_constraints:
            cols = {c.name for c in fk.columns}
            if "form_id" in cols:
                assert fk.ondelete == "CASCADE"
                return
        pytest.fail("No FK on questions.form_id found")

    def test_ondelete_cascade_option(self):
        for fk in Option.__table__.foreign_key_constraints:
            cols = {c.name for c in fk.columns}
            if "question_id" in cols:
                assert fk.ondelete == "CASCADE"
                return
        pytest.fail("No FK on options.question_id found")

    def test_ondelete_cascade_response(self):
        for fk in Response.__table__.foreign_key_constraints:
            cols = {c.name for c in fk.columns}
            if "question_id" in cols:
                assert fk.ondelete == "CASCADE"
                return
        pytest.fail("No FK on responses.question_id found")

    def test_ondelete_set_null_response_option(self):
        for fk in Response.__table__.foreign_key_constraints:
            cols = {c.name for c in fk.columns}
            if "option_id" in cols:
                assert fk.ondelete == "SET NULL"
                return
        pytest.fail("No FK on responses.option_id found")


@pytest.mark.integration
class TestIntegrityConstraints:
    """Run against a real PostgreSQL instance (TEST_DATABASE_URL)."""

    async def _seed_question(self, session, question_type: QuestionType):
        form = Form(
            id=1,
            guild_id=100,
            channel_id=200,
            type="poll",
            title="Test",
            created_by=300,
            status=FormStatus.active,
            anonymous=False,
        )
        session.add(form)
        await session.flush()

        q = Question(
            id=10,
            form_id=form.id,
            prompt="Test question?",
            question_type=question_type,
            order=0,
        )
        session.add(q)

        if question_type in (QuestionType.single_choice, QuestionType.multi_choice):
            opts = [
                Option(id=100, question_id=q.id, text="Option A", order=0),
                Option(id=101, question_id=q.id, text="Option B", order=1),
            ]
            session.add_all(opts)
            await session.flush()
            return form, q, opts

        await session.flush()
        return form, q, None

    async def test_single_choice_duplicate_rejected(self, db_session):
        form, q, opts = await self._seed_question(
            db_session, QuestionType.single_choice
        )
        r1 = Response(
            id=1000, question_id=q.id, user_id=1,
            option_id=opts[0].id, question_type=QuestionType.single_choice,
        )
        db_session.add(r1)
        await db_session.commit()

        r2 = Response(
            id=1001, question_id=q.id, user_id=1,
            option_id=opts[1].id, question_type=QuestionType.single_choice,
        )
        db_session.add(r2)
        with pytest.raises(IntegrityError):
            await db_session.commit()

    async def test_multi_choice_duplicate_option_rejected(self, db_session):
        form, q, opts = await self._seed_question(
            db_session, QuestionType.multi_choice
        )
        r1 = Response(
            id=2000, question_id=q.id, user_id=1,
            option_id=opts[0].id, question_type=QuestionType.multi_choice,
        )
        db_session.add(r1)
        await db_session.commit()

        r2 = Response(
            id=2001, question_id=q.id, user_id=1,
            option_id=opts[0].id, question_type=QuestionType.multi_choice,
        )
        db_session.add(r2)
        with pytest.raises(IntegrityError):
            await db_session.commit()

    async def test_multi_choice_different_option_allowed(self, db_session):
        form, q, opts = await self._seed_question(
            db_session, QuestionType.multi_choice
        )
        r1 = Response(
            id=3000, question_id=q.id, user_id=1,
            option_id=opts[0].id, question_type=QuestionType.multi_choice,
        )
        r2 = Response(
            id=3001, question_id=q.id, user_id=1,
            option_id=opts[1].id, question_type=QuestionType.multi_choice,
        )
        db_session.add_all([r1, r2])
        await db_session.commit()
        rows = (await db_session.execute(
            select(Response).where(Response.question_id == q.id)
        )).scalars().all()
        assert len(rows) == 2

    async def test_text_duplicate_rejected(self, db_session):
        form, q, _ = await self._seed_question(db_session, QuestionType.text)
        r1 = Response(
            id=4000, question_id=q.id, user_id=1,
            text_answer="First", question_type=QuestionType.text,
        )
        db_session.add(r1)
        await db_session.commit()

        r2 = Response(
            id=4001, question_id=q.id, user_id=1,
            text_answer="Second", question_type=QuestionType.text,
        )
        db_session.add(r2)
        with pytest.raises(IntegrityError):
            await db_session.commit()

    async def test_different_users_allowed(self, db_session):
        form, q, opts = await self._seed_question(
            db_session, QuestionType.single_choice
        )
        r1 = Response(
            id=5000, question_id=q.id, user_id=1,
            option_id=opts[0].id, question_type=QuestionType.single_choice,
        )
        r2 = Response(
            id=5001, question_id=q.id, user_id=2,
            option_id=opts[1].id, question_type=QuestionType.single_choice,
        )
        db_session.add_all([r1, r2])
        await db_session.commit()
        assert True


@pytest.mark.integration
class TestCascade:
    """Verify ON DELETE CASCADE cleans up child rows."""

    async def _seed_full_form(self, session):
        form = Form(
            id=9999,
            guild_id=100,
            channel_id=200,
            type="poll",
            title="Cascade test",
            created_by=300,
            status=FormStatus.active,
            anonymous=False,
        )
        session.add(form)
        await session.flush()

        q = Question(
            id=999,
            form_id=form.id,
            prompt="Cascade?",
            question_type=QuestionType.single_choice,
            order=0,
        )
        session.add(q)
        await session.flush()

        opt = Option(id=999, question_id=q.id, text="Yes", order=0)
        session.add(opt)
        await session.flush()

        resp = Response(
            id=9999, question_id=q.id, user_id=1,
            option_id=opt.id, question_type=QuestionType.single_choice,
        )
        session.add(resp)
        await session.commit()
        return form.id

    async def test_delete_form_cascades_to_responses(self, db_session):
        form_id = await self._seed_full_form(db_session)

        await db_session.execute(text(f"DELETE FROM forms WHERE id = {form_id}"))
        await db_session.commit()

        remaining = (
            await db_session.execute(
                select(Response).where(Response.question_id == 999)
            )
        ).scalar()
        assert remaining is None, "Responses should have been deleted by CASCADE"

    async def test_delete_question_sets_option_null(self, db_session):
        form = Form(
            id=8888, guild_id=100, channel_id=200,
            type="poll", title="Null test",
            created_by=300, status=FormStatus.active, anonymous=False,
        )
        db_session.add(form)
        await db_session.flush()

        q = Question(
            id=888, form_id=form.id,
            prompt="Null?",
            question_type=QuestionType.single_choice,
            order=0,
        )
        db_session.add(q)
        await db_session.flush()

        opt = Option(id=888, question_id=q.id, text="Yes", order=0)
        db_session.add(opt)
        await db_session.flush()

        resp = Response(
            id=8888, question_id=q.id, user_id=1,
            option_id=opt.id, question_type=QuestionType.single_choice,
        )
        db_session.add(resp)
        await db_session.commit()

        await db_session.execute(text("DELETE FROM options WHERE id = 888"))
        await db_session.commit()

        row = (
            await db_session.execute(
                select(Response).where(Response.id == 8888)
            )
        ).scalar_one()
        assert row.option_id is None, "option_id should be SET NULL on option delete"
