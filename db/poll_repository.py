"""PollRepository — data access for polls, votes, and poll stats."""

import logging
from typing import Dict, List, Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.enums import FormStatus, QuestionType
from db.models import Form, Option, Question, Response

logger = logging.getLogger(__name__)


class PollRepository:
    """Data access for the Poll domain.

    Accepts an injected ``AsyncSession`` so callers can compose multiple
    repo calls within a single transaction.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def add_vote(
        self,
        username: str,
        user_id: int,
        question_id: int,
        option_id: Optional[int],
        question_type: QuestionType,
        text_answer: Optional[str] = None,
    ) -> bool:
        resp = Response(
            user_id=user_id,
            username=str(username)[:100],
            question_id=question_id,
            option_id=option_id,
            text_answer=text_answer,
            question_type=question_type,
        )
        self._s.add(resp)
        logger.info(
            f"Vote recorded (DB): user={username} ({user_id}) "
            f"question={question_id} option={option_id}"
        )
        return True

    async def add_poll_metadata(
        self,
        poll_id: int,
        question: str,
        options: List[str],
        channel_id: int,
        message_id: int,
        guild_id: int = 0,
        created_by: int = 0,
        description: str = "",
        poll_type: str = "poll",
    ) -> Optional[Dict]:
        """Create Form + Question + Options in a single transaction."""
        form = Form(
            id=poll_id,
            guild_id=guild_id,
            channel_id=channel_id,
            type=poll_type,
            title=description or question,
            created_by=created_by,
            status=FormStatus.active,
            anonymous=False,
        )
        self._s.add(form)
        await self._s.flush()

        q = Question(
            form_id=form.id,
            prompt=question,
            question_type=QuestionType.single_choice,
            order=0,
        )
        self._s.add(q)
        await self._s.flush()

        option_map: Dict[str, int] = {}
        for i, opt_text in enumerate(options):
            opt = Option(
                question_id=q.id,
                text=str(opt_text)[:500],
                order=i,
            )
            self._s.add(opt)
            await self._s.flush()
            option_map[opt_text] = opt.id

        logger.info(f"Poll metadata saved (DB): poll_id={poll_id}, question={question}")
        return {"question_id": q.id, "option_map": option_map}

    async def get_form_by_poll_id(self, poll_id: int) -> Optional[Form]:
        stmt = select(Form).where(Form.id == poll_id)
        result = await self._s.execute(stmt)
        return result.scalar_one_or_none()

    async def get_question_by_form_id(self, form_id: int) -> Optional[Question]:
        stmt = select(Question).where(Question.form_id == form_id)
        result = await self._s.execute(stmt)
        return result.scalar_one_or_none()

    async def get_options_by_question_id(self, question_id: int) -> List[Option]:
        stmt = (
            select(Option)
            .where(Option.question_id == question_id)
            .order_by(Option.order)
        )
        result = await self._s.execute(stmt)
        return list(result.scalars().all())

    async def get_option_by_question_and_text(
        self, question_id: int, text: str
    ) -> Optional[Option]:
        stmt = select(Option).where(
            and_(Option.question_id == question_id, Option.text == text)
        )
        result = await self._s.execute(stmt)
        return result.scalar_one_or_none()

    async def get_poll_metadata(self, poll_id: int) -> Optional[Dict]:
        form = await self.get_form_by_poll_id(poll_id)
        if not form:
            return None
        question = await self.get_question_by_form_id(form.id)
        if not question:
            return None
        options = await self.get_options_by_question_id(question.id)
        return {
            "poll_id": form.id,
            "question": question.prompt,
            "description": form.title,
            "options": [o.text for o in options],
            "channel_id": form.channel_id,
            "message_id": None,
            "timestamp": str(form.created_at),
        }

    async def get_poll_stats(self, poll_id: int) -> Optional[Dict]:
        form = await self.get_form_by_poll_id(poll_id)
        if not form:
            return None
        question = await self.get_question_by_form_id(form.id)
        if not question:
            return None

        stmt = (
            select(Response)
            .options(selectinload(Response.option))
            .where(Response.question_id == question.id)
        )
        result = await self._s.execute(stmt)
        responses = list(result.scalars().all())

        choices: Dict[str, int] = {}
        voters_by_choice: Dict[str, List[str]] = {}
        for resp in responses:
            if resp.option:
                choice = resp.option.text
                choices[choice] = choices.get(choice, 0) + 1
                voters_by_choice.setdefault(choice, []).append(resp.username)

        return {
            "total_votes": len(responses),
            "question": question.prompt,
            "choices": choices,
            "voters_by_choice": voters_by_choice,
        }

    async def get_all_polls(self) -> List[Dict]:
        stmt = (
            select(Form)
            .options(
                selectinload(Form.questions)
                .selectinload(Question.options)
                .selectinload(Option.responses)
                .selectinload(Response.option),
                selectinload(Form.questions)
                .selectinload(Question.responses)
                .selectinload(Response.option),
            )
            .order_by(Form.id.desc())
        )
        result = await self._s.execute(stmt)
        forms = list(result.scalars().unique().all())

        polls = []
        for form in forms:
            if not form.questions:
                continue
            question = form.questions[0]
            options = question.options

            option_counts: Dict[str, int] = {}
            for resp in question.responses:
                if resp.option:
                    option_counts[resp.option.text] = (
                        option_counts.get(resp.option.text, 0) + 1
                    )

            options_list = [
                {"name": o.text, "votes": option_counts.get(o.text, 0)}
                for o in options
            ]
            polls.append({
                "poll_id": form.id,
                "question": question.prompt,
                "options": options_list,
                "total_votes": sum(option_counts.values()),
                "timestamp": str(form.created_at),
            })

        return polls

    async def get_all_votes(self) -> List[Dict]:
        stmt = (
            select(Response)
            .options(selectinload(Response.question), selectinload(Response.option))
            .order_by(Response.submitted_at)
        )
        result = await self._s.execute(stmt)
        responses = list(result.scalars().all())

        votes = []
        for r in responses:
            q = r.question
            votes.append({
                "Timestamp": str(r.submitted_at),
                "Username": r.username,
                "User_ID": r.user_id,
                "Question": q.prompt if q else "",
                "Choice": r.option.text if r.option else "",
                "Poll_ID": q.form_id if q else "",
            })
        return votes

    async def get_summary_by_question(self) -> Dict:
        stmt = (
            select(Question)
            .options(
                selectinload(Question.responses)
                .selectinload(Response.option)
            )
        )
        result = await self._s.execute(stmt)
        questions = list(result.scalars().unique().all())

        summary = {}
        for q in questions:
            choice_counts: Dict[str, int] = {}
            for r in q.responses:
                if r.option:
                    choice_counts[r.option.text] = (
                        choice_counts.get(r.option.text, 0) + 1
                    )
            summary[q.prompt] = {
                "Total_Votes": len(q.responses),
                "choices": choice_counts,
            }
        return summary

    async def end_poll(self, poll_id: int) -> bool:
        stmt = select(Form).where(Form.id == poll_id)
        result = await self._s.execute(stmt)
        form = result.scalar_one_or_none()
        if not form:
            return False
        form.status = FormStatus.closed
        logger.info(f"Poll {poll_id} closed (DB)")
        return True

    async def is_poll_active_in_db(self, poll_id: int) -> bool:
        form = await self.get_form_by_poll_id(poll_id)
        return form is not None and form.status == FormStatus.active

    async def has_user_voted_in_db(self, poll_id: int, user_id: int) -> bool:
        stmt = (
            select(Response.id)
            .join(Question, Response.question_id == Question.id)
            .where(
                and_(
                    Question.form_id == poll_id,
                    Response.user_id == user_id,
                )
            )
            .limit(1)
        )
        result = await self._s.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def get_active_poll_ids(self) -> set:
        stmt = select(Form.id).where(Form.status == FormStatus.active)
        result = await self._s.execute(stmt)
        return set(result.scalars().all())
