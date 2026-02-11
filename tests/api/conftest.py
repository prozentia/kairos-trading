"""API test fixtures.

Provides a test client, authentication headers, and a test database
session for API endpoint tests. Uses httpx.AsyncClient for async
FastAPI testing.
"""

import pytest

# These imports will work once the API module is fully implemented.
# For now they serve as the expected interface.
# from httpx import AsyncClient, ASGITransport
# from api.main import app
# from api.auth.jwt import create_access_token


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Return Authorization headers with a valid test JWT.

    Uses a deterministic token for test user "testuser@kairos.dev".
    """
    # Once jwt module is wired up:
    # token = create_access_token({"sub": "testuser@kairos.dev", "user_id": 1})
    # return {"Authorization": f"Bearer {token}"}
    return {"Authorization": "Bearer test-token-placeholder"}


@pytest.fixture
def db_session():
    """Provide a test database session with automatic rollback.

    Creates a fresh SQLite in-memory database for each test,
    runs migrations, and rolls back after the test completes.
    """
    # TODO: Implement once SQLAlchemy models and Alembic are set up
    # from sqlalchemy import create_engine
    # from sqlalchemy.orm import sessionmaker
    # engine = create_engine("sqlite:///:memory:")
    # Base.metadata.create_all(engine)
    # Session = sessionmaker(bind=engine)
    # session = Session()
    # yield session
    # session.rollback()
    # session.close()
    yield None


@pytest.fixture
def client():
    """Provide an httpx TestClient for the FastAPI app.

    Uses ASGITransport to test the full ASGI stack without
    starting a real server.
    """
    # TODO: Implement once api.main is fully wired
    # transport = ASGITransport(app=app)
    # async with AsyncClient(transport=transport, base_url="http://test") as ac:
    #     yield ac
    yield None
