"""Shared helpers for repository operations with injected sessions."""

from db.session import get_session
from db.poll_repository import PollRepository
from db.tour_repository import TourRepository


async def poll_op(method_name, *args, **kwargs):
    """Run a PollRepository method with a session-scoped transaction."""
    async with get_session() as session:
        return await getattr(PollRepository(session), method_name)(*args, **kwargs)


async def tour_op(method_name, *args, **kwargs):
    """Run a TourRepository method with a session-scoped transaction."""
    async with get_session() as session:
        return await getattr(TourRepository(session), method_name)(*args, **kwargs)
