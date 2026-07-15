"""Repository — backward-compatible facade.

All functions here delegate to the domain-specific repository classes.
New code should import from ``db.poll_repository``, ``db.tour_repository``,
or ``db.coach_repository`` directly and inject an ``AsyncSession``.
"""

from typing import Dict, List, Optional, Set

from db.enums import QuestionType
from db.models import Coach, Form, IndustryTour, TourFeedback
from db.session import get_session


# ---------------------------------------------------------------------------
# Poll functions
# ---------------------------------------------------------------------------

async def add_vote(
    username: str,
    user_id: int,
    question_id: int,
    option_id: Optional[int],
    question_type: QuestionType,
    text_answer: Optional[str] = None,
) -> bool:
    from db.poll_repository import PollRepository
    async with get_session() as session:
        return await PollRepository(session).add_vote(
            username=username, user_id=user_id, question_id=question_id,
            option_id=option_id, question_type=question_type,
            text_answer=text_answer,
        )


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
    from db.poll_repository import PollRepository
    async with get_session() as session:
        return await PollRepository(session).add_poll_metadata(
            poll_id=poll_id, question=question, options=options,
            channel_id=channel_id, message_id=message_id,
            guild_id=guild_id, created_by=created_by,
            description=description, poll_type=poll_type,
        )


async def get_form_by_poll_id(poll_id: int):
    from db.poll_repository import PollRepository
    async with get_session() as session:
        return await PollRepository(session).get_form_by_poll_id(poll_id)


async def get_question_by_form_id(form_id: int):
    from db.poll_repository import PollRepository
    async with get_session() as session:
        return await PollRepository(session).get_question_by_form_id(form_id)


async def get_options_by_question_id(question_id: int):
    from db.poll_repository import PollRepository
    async with get_session() as session:
        return await PollRepository(session).get_options_by_question_id(question_id)


async def get_option_by_question_and_text(question_id: int, text: str):
    from db.poll_repository import PollRepository
    async with get_session() as session:
        return await PollRepository(session).get_option_by_question_and_text(question_id, text)


async def get_poll_metadata(poll_id: int) -> Optional[Dict]:
    from db.poll_repository import PollRepository
    async with get_session() as session:
        return await PollRepository(session).get_poll_metadata(poll_id)


async def get_poll_stats(poll_id: int) -> Optional[Dict]:
    from db.poll_repository import PollRepository
    async with get_session() as session:
        return await PollRepository(session).get_poll_stats(poll_id)


async def get_all_polls() -> List[Dict]:
    from db.poll_repository import PollRepository
    async with get_session() as session:
        return await PollRepository(session).get_all_polls()


async def get_all_votes() -> List[Dict]:
    from db.poll_repository import PollRepository
    async with get_session() as session:
        return await PollRepository(session).get_all_votes()


async def get_summary_by_question() -> Dict:
    from db.poll_repository import PollRepository
    async with get_session() as session:
        return await PollRepository(session).get_summary_by_question()


async def end_poll(poll_id: int) -> bool:
    from db.poll_repository import PollRepository
    async with get_session() as session:
        return await PollRepository(session).end_poll(poll_id)


async def is_poll_active_in_db(poll_id: int) -> bool:
    from db.poll_repository import PollRepository
    async with get_session() as session:
        return await PollRepository(session).is_poll_active_in_db(poll_id)


async def has_user_voted_in_db(poll_id: int, user_id: int) -> bool:
    from db.poll_repository import PollRepository
    async with get_session() as session:
        return await PollRepository(session).has_user_voted_in_db(poll_id, user_id)


async def get_active_poll_ids() -> Set[int]:
    from db.poll_repository import PollRepository
    async with get_session() as session:
        return await PollRepository(session).get_active_poll_ids()


# ---------------------------------------------------------------------------
# Tour functions
# ---------------------------------------------------------------------------

async def create_tour(name: str, date, company: str) -> IndustryTour:
    from db.tour_repository import TourRepository
    async with get_session() as session:
        return await TourRepository(session).create_tour(name, date, company)


async def get_tour(tour_id: int):
    from db.tour_repository import TourRepository
    async with get_session() as session:
        return await TourRepository(session).get_tour(tour_id)


async def get_all_tours() -> List[Dict]:
    from db.tour_repository import TourRepository
    async with get_session() as session:
        return await TourRepository(session).get_all_tours()


async def submit_tour_feedback(
    tour_id: int, student_id: int, student_name: str,
    rating: Optional[int] = None, comments: Optional[str] = None,
) -> TourFeedback:
    from db.tour_repository import TourRepository
    async with get_session() as session:
        return await TourRepository(session).submit_tour_feedback(
            tour_id=tour_id, student_id=student_id,
            student_name=student_name, rating=rating, comments=comments,
        )


async def get_tour_feedback(tour_id: int) -> List[Dict]:
    from db.tour_repository import TourRepository
    async with get_session() as session:
        return await TourRepository(session).get_tour_feedback(tour_id)


# ---------------------------------------------------------------------------
# Coach functions
# ---------------------------------------------------------------------------

async def get_coach_by_email(email: str):
    from db.coach_repository import CoachRepository
    async with get_session() as session:
        return await CoachRepository(session).get_coach_by_email(email)


async def create_coach(email: str, password_hash: str, name: str) -> Coach:
    from db.coach_repository import CoachRepository
    async with get_session() as session:
        return await CoachRepository(session).create_coach(email, password_hash, name)
