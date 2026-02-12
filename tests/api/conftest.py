"""API test fixtures.

Provides an async test client, authentication helpers, and a test database
session. Uses SQLite in-memory for fast, isolated tests.
"""

from __future__ import annotations

import asyncio
import os
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Set test database URL BEFORE importing app modules
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-jwt-signing"
os.environ["INTERNAL_API_TOKEN"] = "test-internal-token"

from adapters.database.models import Base
from api.auth.jwt import create_access_token, create_refresh_token
from api.deps import get_db
from api.main import app


# ---------------------------------------------------------------------------
# Database engine for tests (SQLite in-memory)
# ---------------------------------------------------------------------------

_test_engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
_test_session_factory = async_sessionmaker(
    _test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def _override_get_db() -> AsyncGenerator[AsyncSession, None]:
    """Override the get_db dependency with the test session."""
    async with _test_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


# Override the DB dependency globally for tests
app.dependency_overrides[get_db] = _override_get_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Create all tables before each test and drop them after."""
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    """Provide a test database session."""
    async with _test_session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Provide an httpx AsyncClient for the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def test_user_data() -> dict:
    """Return test user registration data."""
    return {
        "email": "test@kairos.dev",
        "password": "SecureP@ss123",
        "username": "testuser",
    }


@pytest.fixture
def auth_token() -> str:
    """Return a valid JWT access token for testing."""
    return create_access_token({
        "sub": "test-user-uuid",
        "email": "test@kairos.dev",
        "username": "testuser",
    })


@pytest.fixture
def auth_headers(auth_token: str) -> dict[str, str]:
    """Return Authorization headers with a valid test JWT."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def refresh_token() -> str:
    """Return a valid refresh token for testing."""
    return create_refresh_token({
        "sub": "test-user-uuid",
        "email": "test@kairos.dev",
        "username": "testuser",
    })


@pytest.fixture
def internal_headers() -> dict[str, str]:
    """Return headers with internal API token for engine-to-API calls."""
    return {"x-internal-token": "test-internal-token"}
