import os
import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import (
    AsyncSession, async_sessionmaker, create_async_engine,
)

from db.models import Base

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/bridge_test",
)


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "integration: marks tests that require a real PostgreSQL database "
        "(skipped when TEST_DATABASE_URL is not set or unreachable)",
    )


def pytest_collection_modifyitems(config, items):
    if not _is_db_available():
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(
                    pytest.mark.skip(
                        reason="No PostgreSQL available. "
                        "Set TEST_DATABASE_URL to run integration tests."
                    )
                )


def _is_db_available() -> bool:
    try:
        import asyncpg  # noqa: F401
        return True
    except ImportError:
        return False


@pytest_asyncio.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def db_engine():
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    factory = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False,
    )
    async with factory() as session:
        yield session
        await session.rollback()
        await session.close()
