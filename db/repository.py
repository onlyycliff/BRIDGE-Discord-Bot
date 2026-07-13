import logging
from typing import Dict, List, Optional

from sqlalchemy import and_, select

from db.enums import FormStatus, PollType, QuestionType
from db.models import Coach, Form, IndustryTour, Option, Question, Response, TourFeedback
from db.session import get_session

logger = logging.getLogger(__name__)


async def add_vote(
    username: str,
    user_id: int,
    question_id: int,
    option_id: Optional[int],
    question_type: QuestionType,
    text_answer: Optional[str] = None,
) -> bool:
    async with get_session() as session:
        resp = Response(
            user_id=user_id,
            username=str(username)[:100],
            question_id=question_id,
            option_id=option_id,
            text_answer=text_answer,
            question_type=question_type,
        )
        session.add(resp)
        logger.info(
            f"Vote recorded (DB): user={username} ({user_id}) "
            f"question={question_id} option={option_id}"
        )
        return True


async def add_poll_metadata(
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
    """Create Form + Question + Options in a single transaction.

    Returns dict with {question_id, option_map} on success, None on failure.
    """
    async with get_session() as session:
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
        session.add(form)
        await session.flush()

        q = Question(
            form_id=form.id,
            prompt=question,
            question_type=QuestionType.single_choice,
            order=0,
        )
        session.add(q)
        await session.flush()

        option_map: Dict[str, int] = {}
        for i, opt_text in enumerate(options):
            opt = Option(
                question_id=q.id,
                text=str(opt_text)[:500],
                order=i,
            )
            session.add(opt)
            await session.flush()
            option_map[opt_text] = opt.id

        logger.info(f"Poll metadata saved (DB): poll_id={poll_id}, question={question}")
        return {"question_id": q.id, "option_map": option_map}


async def get_form_by_poll_id(poll_id: int) -> Optional[Form]:
    async with get_session() as session:
        stmt = select(Form).where(Form.id == poll_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


async def get_question_by_form_id(form_id: int) -> Optional[Question]:
    async with get_session() as session:
        stmt = select(Question).where(Question.form_id == form_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


async def get_options_by_question_id(question_id: int) -> List[Option]:
    async with get_session() as session:
        stmt = (
            select(Option)
            .where(Option.question_id == question_id)
            .order_by(Option.order)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())


async def get_option_by_question_and_text(
    question_id: int, text: str
) -> Optional[Option]:
    async with get_session() as session:
        stmt = select(Option).where(
            and_(Option.question_id == question_id, Option.text == text)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


async def get_poll_metadata(poll_id: int) -> Optional[Dict]:
    form = await get_form_by_poll_id(poll_id)
    if not form:
        return None
    question = await get_question_by_form_id(form.id)
    if not question:
        return None
    options = await get_options_by_question_id(question.id)
    return {
        "poll_id": form.id,
        "question": question.prompt,
        "description": form.title,
        "options": [o.text for o in options],
        "channel_id": form.channel_id,
        "message_id": None,
        "timestamp": str(form.created_at),
    }


async def get_poll_stats(poll_id: int) -> Optional[Dict]:
    form = await get_form_by_poll_id(poll_id)
    if not form:
        return None

    question = await get_question_by_form_id(form.id)
    if not question:
        return None

    async with get_session() as session:
        stmt = select(Response).where(Response.question_id == question.id)
        result = await session.execute(stmt)
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


async def get_all_polls() -> List[Dict]:
    async with get_session() as session:
        stmt = select(Form).order_by(Form.id.desc())
        result = await session.execute(stmt)
        forms = list(result.scalars().all())

        polls = []
        for form in forms:
            question = await get_question_by_form_id(form.id)
            if not question:
                continue
            options = await get_options_by_question_id(question.id)

            resp_stmt = select(Response).where(Response.question_id == question.id)
            resp_result = await session.execute(resp_stmt)
            responses = list(resp_result.scalars().all())

            option_counts: Dict[str, int] = {}
            for r in responses:
                if r.option:
                    option_counts[r.option.text] = (
                        option_counts.get(r.option.text, 0) + 1
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


async def get_all_votes() -> List[Dict]:
    async with get_session() as session:
        stmt = select(Response).order_by(Response.submitted_at)
        result = await session.execute(stmt)
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


async def get_summary_by_question() -> Dict:
    async with get_session() as session:
        stmt = select(Question)
        result = await session.execute(stmt)
        questions = list(result.scalars().all())

        summary = {}
        for q in questions:
            resp_stmt = select(Response).where(Response.question_id == q.id)
            resp_result = await session.execute(resp_stmt)
            responses = list(resp_result.scalars().all())

            choice_counts: Dict[str, int] = {}
            for r in responses:
                if r.option:
                    choice_counts[r.option.text] = (
                        choice_counts.get(r.option.text, 0) + 1
                    )

            summary[q.prompt] = {
                "Total_Votes": len(responses),
                "choices": choice_counts,
            }

        return summary


async def end_poll(poll_id: int) -> bool:
    async with get_session() as session:
        stmt = select(Form).where(Form.id == poll_id)
        result = await session.execute(stmt)
        form = result.scalar_one_or_none()
        if not form:
            return False
        form.status = FormStatus.closed
        logger.info(f"Poll {poll_id} closed (DB)")
        return True


# ---------------------------------------------------------------------------
# Industry Tour Feedback
# ---------------------------------------------------------------------------


async def create_tour(
    name: str,
    date,
    company: str,
) -> IndustryTour:
    async with get_session() as session:
        import time
        tour = IndustryTour(
            id=int(time.time() * 1000),
            name=name,
            date=date,
            company=company,
        )
        session.add(tour)
        await session.flush()
        logger.info(f"Tour created (DB): {name} at {company}")
        return tour


async def get_tour(tour_id: int) -> Optional[IndustryTour]:
    async with get_session() as session:
        stmt = select(IndustryTour).where(IndustryTour.id == tour_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


async def get_all_tours() -> List[Dict]:
    async with get_session() as session:
        stmt = select(IndustryTour).order_by(IndustryTour.date.desc())
        result = await session.execute(stmt)
        tours = result.scalars().all()
        return [
            {
                "id": t.id,
                "name": t.name,
                "date": str(t.date),
                "company": t.company,
                "feedback_count": len(t.feedback),
            }
            for t in tours
        ]


async def submit_tour_feedback(
    tour_id: int,
    student_id: int,
    student_name: str,
    rating: Optional[int] = None,
    comments: Optional[str] = None,
) -> TourFeedback:
    async with get_session() as session:
        tour = await session.get(IndustryTour, tour_id)
        if not tour:
            raise ValueError(f"Tour {tour_id} not found")

        fb = TourFeedback(
            tour_id=tour_id,
            student_id=student_id,
            student_name=str(student_name)[:100],
            rating=rating,
            comments=comments,
        )
        session.add(fb)
        await session.flush()
        logger.info(f"Feedback submitted (DB): student={student_name} tour={tour_id}")
        return fb


async def get_tour_feedback(tour_id: int) -> List[Dict]:
    async with get_session() as session:
        stmt = (
            select(TourFeedback)
            .where(TourFeedback.tour_id == tour_id)
            .order_by(TourFeedback.submitted_at)
        )
        result = await session.execute(stmt)
        feedback = result.scalars().all()
        return [
            {
                "id": f.id,
                "student_id": f.student_id,
                "student_name": f.student_name,
                "rating": f.rating,
                "comments": f.comments,
                "submitted_at": str(f.submitted_at),
            }
            for f in feedback
        ]


# ---------------------------------------------------------------------------
# Coaches
# ---------------------------------------------------------------------------


async def get_coach_by_email(email: str) -> Optional[Coach]:
    async with get_session() as session:
        stmt = select(Coach).where(Coach.email == email)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


async def create_coach(
    email: str,
    password_hash: str,
    name: str,
) -> Coach:
    async with get_session() as session:
        coach = Coach(
            email=email,
            password_hash=password_hash,
            name=name,
        )
        session.add(coach)
        await session.flush()
        logger.info(f"Coach created (DB): {email}")
        return coach
