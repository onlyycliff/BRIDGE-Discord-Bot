"""
Seed test data into PostgreSQL for development and testing.

Usage:
    python scripts/seed_test_data.py

Requires DATABASE_URL to be set in the environment (or .env).

What it does:
  1. Creates sample industry tours
  2. Creates a default coach account (coach@bridge2026.org / bridge2026)
  3. Prints summary of seeded data
"""

import asyncio
from pathlib import Path

from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

from db.session import create_engine_from_url, get_factory, dispose_engine
from db.models import IndustryTour, Coach, TourFeedback


load_dotenv(Path(__file__).resolve().parent.parent / ".env")
load_dotenv(Path(__file__).resolve().parent.parent / "bridge_bot" / ".env")


async def seed():
    create_engine_from_url()
    factory = get_factory()

    async with factory() as session:
        # ---- Tours ----
        tours_data = [
            {"name": "Cigna Tour", "company": "Cigna Healthcare", "date": "2026-06-15"},
            {"name": "Travelers Tour", "company": "Travelers Insurance", "date": "2026-06-22"},
            {"name": "Hartford HealthCare Tour", "company": "Hartford HealthCare", "date": "2026-06-29"},
            {"name": "Pratt & Whitney Tour", "company": "Pratt & Whitney", "date": "2026-07-06"},
        ]

        from datetime import datetime
        import time

        created_tours = 0
        for t in tours_data:
            existing = await session.get(IndustryTour, hash(t["name"]) % 10**12)
            tour = IndustryTour(
                id=int(time.time() * 1000) + created_tours,
                name=t["name"],
                company=t["company"],
                date=datetime.strptime(t["date"], "%Y-%m-%d"),
            )
            session.add(tour)
            created_tours += 1

        # ---- Coach ----
        existing_coach = None
        from sqlalchemy import select
        stmt = select(Coach).where(Coach.email == "coach@bridge2026.org")
        result = await session.execute(stmt)
        existing_coach = result.scalar_one_or_none()

        if not existing_coach:
            coach = Coach(
                email="coach@bridge2026.org",
                password_hash=generate_password_hash("bridge2026"),
                name="Default Coach",
            )
            session.add(coach)
            print("  Coach created: coach@bridge2026.org / bridge2026")
        else:
            print("  Coach already exists, skipping")

        await session.commit()
        print(f"\nSeeding complete:")
        print(f"  Tours created: {created_tours}")
        print(f"  Coach: coach@bridge2026.org / bridge2026")

    await dispose_engine()


def main():
    print("Seeding test data...")
    asyncio.run(seed())


if __name__ == "__main__":
    main()
