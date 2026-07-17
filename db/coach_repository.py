"""CoachRepository — data access for coach authentication and lookup."""

import logging
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Coach

logger = logging.getLogger(__name__)


class CoachRepository:
    """Data access for the Coach domain."""

    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def get_coach_by_email(self, email: str) -> Optional[Coach]:
        stmt = select(Coach).where(Coach.email == email)
        result = await self._s.execute(stmt)
        return result.scalar_one_or_none()

    async def get_coach_by_id(self, coach_id: int) -> Optional[Coach]:
        stmt = select(Coach).where(Coach.id == coach_id)
        result = await self._s.execute(stmt)
        return result.scalar_one_or_none()

    async def create_coach(
        self,
        email: str,
        password_hash: str,
        name: str,
    ) -> Coach:
        coach = Coach(
            email=email,
            password_hash=password_hash,
            name=name,
        )
        self._s.add(coach)
        await self._s.flush()
        logger.info(f"Coach created (DB): {email}")
        return coach
