"""Async database connection, session factory, and initialization helpers.

The SQLAlchemy async engine is created from the ``DATABASE_URL`` setting.
If no URL is configured the engine is ``None`` and the application runs
in a degraded (demo-only) mode where database operations are skipped.
"""

import logging

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.config import settings

logger = logging.getLogger(__name__)

DATABASE_URL: str = settings.DATABASE_URL

if DATABASE_URL:
    engine: AsyncEngine = create_async_engine(
        DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        pool_recycle=300,
    )
    AsyncSessionLocal: sessionmaker[AsyncSession] = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
else:
    engine = None  # type: ignore[assignment]
    AsyncSessionLocal = None  # type: ignore[assignment]
    logger.warning("DATABASE_URL is not set — database features will be disabled.")


async def get_session() -> AsyncSession | None:
    """FastAPI dependency that yields an :class:`AsyncSession`.

    Returns ``None`` when the database is not configured, allowing
    routes to gracefully degrade.
    """
    if AsyncSessionLocal is None:
        yield None
        return
    async with AsyncSessionLocal() as session:
        yield session


async def init_db() -> None:
    """Create all tables defined on :data:`Base.metadata` if they don't exist.

    A database outage must never prevent the API from starting —
    failures are logged and the API continues in degraded mode.
    """
    from app.database.base import Base  # local import avoids circular deps
    from app.models import (  # noqa: F401
        PaymentAnalysis,
        PaymentMethodComparison,
        PaymentAttempt,
        RecoveryRecommendation,
        User,
    )

    if engine is None:
        logger.warning("Skipping table creation — DATABASE_URL not configured.")
        return

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created/verified successfully.")
    except Exception as exc:  # noqa: BLE001 — any DB failure is non-fatal
        logger.error("Database initialization failed — running degraded: %s", exc)