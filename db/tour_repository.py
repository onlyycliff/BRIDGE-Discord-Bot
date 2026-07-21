"""TourRepository — data access for industry tours and feedback."""

import logging
import time
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from db.models import IndustryTour, TourFeedback

logger = logging.getLogger(__name__)


class TourRepository:
    """Data access for the Tour domain."""

    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def create_tour(
        self,
        name: str,
        date,
        company: str,
        google_form_url: Optional[str] = None,
        google_sheet_id: Optional[str] = None,
    ) -> IndustryTour:
        tour = IndustryTour(
            id=int(time.time() * 1000),
            name=name,
            date=date,
            company=company,
            google_form_url=google_form_url,
            google_sheet_id=google_sheet_id,
        )
        self._s.add(tour)
        await self._s.flush()
        logger.info(f"Tour created (DB): {name} at {company}")
        return tour

    async def get_tour(self, tour_id: int) -> Optional[IndustryTour]:
        stmt = select(IndustryTour).where(IndustryTour.id == tour_id)
        result = await self._s.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_tours(self) -> List[Dict]:
        stmt = (
            select(IndustryTour)
            .options(selectinload(IndustryTour.feedback))
            .order_by(IndustryTour.date.desc())
        )
        result = await self._s.execute(stmt)
        tours = result.scalars().all()
        return [
            {
                "id": t.id,
                "name": t.name,
                "date": str(t.date),
                "company": t.company,
                "google_form_url": t.google_form_url,
                "google_sheet_id": t.google_sheet_id,
                "feedback_count": len(t.feedback),
            }
            for t in tours
        ]

    async def submit_tour_feedback(
        self,
        tour_id: int,
        student_id: int,
        student_name: str,
        rating: Optional[int] = None,
        comments: Optional[str] = None,
    ) -> TourFeedback:
        tour = await self._s.get(IndustryTour, tour_id)
        if not tour:
            raise ValueError(f"Tour {tour_id} not found")

        fb = TourFeedback(
            tour_id=tour_id,
            student_id=student_id,
            student_name=str(student_name)[:100],
            rating=rating,
            comments=comments,
        )
        self._s.add(fb)
        await self._s.flush()
        logger.info(f"Feedback submitted (DB): student={student_name} tour={tour_id}")
        return fb

    async def get_tour_feedback(self, tour_id: int) -> List[Dict]:
        stmt = (
            select(TourFeedback)
            .where(TourFeedback.tour_id == tour_id)
            .order_by(TourFeedback.submitted_at)
        )
        result = await self._s.execute(stmt)
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
