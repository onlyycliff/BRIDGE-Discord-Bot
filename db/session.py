import os
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession, async_sessionmaker, create_async_engine,
)
from sqlalchemy.pool import NullPool

logger = logging.getLogger(__name__)

_engine = None
_async_session_factory = None


def create_engine_from_url(database_url: str | None = None):
    global _engine, _async_session_factory

    url = database_url or os.getenv("DATABASE_URL")
    if not url:
        raise ValueError(
            "DATABASE_URL environment variable is required. "
            "Set it in .env locally or in Railway environment variables."
        )

    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    elif "asyncpg" not in url:
        url = url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
        if "asyncpg" not in url:
            url = f"postgresql+asyncpg://{url.split('://', 1)[1]}" if "://" in url else url

    _engine = create_async_engine(url, poolclass=NullPool, echo=False)
    _async_session_factory = async_sessionmaker(
        _engine, class_=AsyncSession, expire_on_commit=False,
    )
    logger.info("Database engine created (asyncpg)")
    return _engine


def get_factory():
    if _async_session_factory is None:
        create_engine_from_url()
    return _async_session_factory


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    factory = get_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_db() -> bool:
    """Verify the database is reachable with a lightweight query.

    Returns True if the connection succeeds, False otherwise.
    """
    try:
        factory = get_factory()
        async with factory() as session:
            from sqlalchemy import text
            await session.execute(text("SELECT 1"))
            logger.info("Database connectivity check passed")
            return True
    except Exception as e:
        logger.error(f"Database connectivity check failed: {e}")
        return False


async def ensure_db(timeout: float = 15.0) -> None:
    """Block until the database is reachable, raising on timeout.

    Called at startup so the application never serves requests before
    the database is ready (particularly important on Railway where the
    Postgres container may still be provisioning).
    """
    import asyncio
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        ok = await check_db()
        if ok:
            return
        await asyncio.sleep(1)


async def dispose_engine():
    global _engine
    if _engine:
        await _engine.dispose()
        _engine = None
        _async_session_factory = None
        logger.info("Database engine disposed")
