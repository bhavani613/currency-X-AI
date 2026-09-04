"""Shared pytest fixtures for CurrencyX AI backend tests.

Test isolation strategy:
- Uses a fresh in-memory SQLite database per test function (async).
- Tests NEVER touch the development PostgreSQL database.
- The FastAPI app runs with the DB dependency overridden to the test session.
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.deps import _RATE_BUCKETS
from app.database.base import Base
from app.database.connection import get_session
from main import app

# ---------------------------------------------------------------------------
# In-memory SQLite engine — tests NEVER touch PostgreSQL.
# ---------------------------------------------------------------------------
_TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="function")
def _engine() -> AsyncEngine:
    """Create a fresh in-memory SQLite engine for each test function."""
    engine = create_async_engine(
        _TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    yield engine


@pytest.fixture(scope="function")
async def _async_session(_engine) -> AsyncSession:
    """Create all tables, yield a session, then drop everything."""
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(
        _engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
async def client(_async_session):
    """FastAPI test client with overridden DB dependency."""

    async def _override_get_session():
        yield _async_session

    app.dependency_overrides[get_session] = _override_get_session
    # Reset the in-memory rate-limiter buckets so tests are isolated from
    # each other (all test requests share the same source IP).
    _RATE_BUCKETS.clear()

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def auth_token(client):
    """Register a user via the API and return a JWT access token."""

    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    password = "Str0ng!Pass"

    resp = await client.post(
        "/api/v1/auth/signup",
        json={
            "full_name": "Test User",
            "email": email,
            "password": password,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    return data["access_token"]


@pytest.fixture(scope="function")
async def auth_headers(auth_token):
    """Return headers dict with JWT bearer token for authenticated requests."""
    return {"Authorization": f"Bearer {auth_token}"}