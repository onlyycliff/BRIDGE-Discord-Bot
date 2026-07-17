"""Repository — backward-compatible re-exports.

All callers should import from ``db.poll_repository``, ``db.tour_repository``,
or ``db.coach_repository`` directly and inject an ``AsyncSession``.

This module exists only for backward compatibility with any external
code that still imports from ``db.repository``.
"""

from db.poll_repository import PollRepository  # noqa: F401
from db.tour_repository import TourRepository  # noqa: F401
from db.coach_repository import CoachRepository  # noqa: F401
