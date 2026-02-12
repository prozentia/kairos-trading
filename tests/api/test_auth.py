"""Tests for authentication endpoints (register, login, refresh, protect).

Uses httpx AsyncClient with SQLite in-memory database.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_register_success(client: AsyncClient, test_user_data: dict):
    """POST /auth/register should create a new user."""
    response = await client.post("/auth/register", json=test_user_data)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == test_user_data["email"]
    assert data["username"] == test_user_data["username"]
    assert data["is_active"] is True
    assert "id" in data
    # Password must not be in response
    assert "password" not in data
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient, test_user_data: dict):
    """POST /auth/register with existing email should return 409."""
    await client.post("/auth/register", json=test_user_data)
    response = await client.post("/auth/register", json=test_user_data)
    assert response.status_code == 409
    assert "already registered" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_register_duplicate_username(client: AsyncClient, test_user_data: dict):
    """POST /auth/register with existing username should return 409."""
    await client.post("/auth/register", json=test_user_data)
    # Same username, different email
    dup = test_user_data.copy()
    dup["email"] = "other@kairos.dev"
    response = await client.post("/auth/register", json=dup)
    assert response.status_code == 409
    assert "username" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_register_weak_password(client: AsyncClient):
    """POST /auth/register with short password should return 422."""
    response = await client.post("/auth/register", json={
        "email": "weak@kairos.dev",
        "password": "short",
        "username": "weakuser",
    })
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_user_data: dict):
    """POST /auth/login should return tokens for valid credentials."""
    # Register first
    await client.post("/auth/register", json=test_user_data)
    # Login
    response = await client.post("/auth/login", json={
        "email": test_user_data["email"],
        "password": test_user_data["password"],
    })
    assert response.status_code == 200
    data = response.json()
    assert "tokens" in data
    assert data["tokens"]["access_token"]
    assert data["tokens"]["refresh_token"]
    assert data["tokens"]["token_type"] == "bearer"
    assert data["tokens"]["expires_in"] > 0
    assert "user" in data
    assert data["user"]["email"] == test_user_data["email"]


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, test_user_data: dict):
    """POST /auth/login with wrong password should return 401."""
    await client.post("/auth/register", json=test_user_data)
    response = await client.post("/auth/login", json={
        "email": test_user_data["email"],
        "password": "WrongPassword123!",
    })
    assert response.status_code == 401
    assert "invalid" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_nonexistent_email(client: AsyncClient):
    """POST /auth/login with unknown email should return 401."""
    response = await client.post("/auth/login", json={
        "email": "nobody@kairos.dev",
        "password": "SecureP@ss123",
    })
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Token refresh
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient, test_user_data: dict):
    """POST /auth/refresh should return new tokens from a valid refresh token."""
    # Register and login
    await client.post("/auth/register", json=test_user_data)
    login_resp = await client.post("/auth/login", json={
        "email": test_user_data["email"],
        "password": test_user_data["password"],
    })
    refresh_token = login_resp.json()["tokens"]["refresh_token"]

    # Refresh
    response = await client.post("/auth/refresh", json={
        "refresh_token": refresh_token,
    })
    assert response.status_code == 200
    data = response.json()
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["expires_in"] > 0


@pytest.mark.asyncio
async def test_refresh_with_access_token_fails(client: AsyncClient, test_user_data: dict):
    """POST /auth/refresh with an access token (not refresh) should fail."""
    await client.post("/auth/register", json=test_user_data)
    login_resp = await client.post("/auth/login", json={
        "email": test_user_data["email"],
        "password": test_user_data["password"],
    })
    access_token = login_resp.json()["tokens"]["access_token"]

    response = await client.post("/auth/refresh", json={
        "refresh_token": access_token,
    })
    assert response.status_code == 401
    assert "not a refresh token" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Protected endpoints
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_protected_endpoint_without_token(client: AsyncClient):
    """Accessing a protected endpoint without a token should return 401."""
    response = await client.get("/trades/")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_with_invalid_token(client: AsyncClient):
    """Accessing a protected endpoint with an invalid token should return 401."""
    response = await client.get(
        "/trades/",
        headers={"Authorization": "Bearer invalid-token-here"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_with_valid_token(client: AsyncClient, test_user_data: dict):
    """Accessing a protected endpoint with a valid token should succeed."""
    await client.post("/auth/register", json=test_user_data)
    login_resp = await client.post("/auth/login", json={
        "email": test_user_data["email"],
        "password": test_user_data["password"],
    })
    access_token = login_resp.json()["tokens"]["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}

    response = await client.get("/trades/", headers=headers)
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Profile
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_me(client: AsyncClient, test_user_data: dict):
    """GET /auth/me should return the current user profile."""
    await client.post("/auth/register", json=test_user_data)
    login_resp = await client.post("/auth/login", json={
        "email": test_user_data["email"],
        "password": test_user_data["password"],
    })
    token = login_resp.json()["tokens"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = await client.get("/auth/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user_data["email"]
    assert data["username"] == test_user_data["username"]


@pytest.mark.asyncio
async def test_change_password(client: AsyncClient, test_user_data: dict):
    """POST /auth/change-password should update the password."""
    await client.post("/auth/register", json=test_user_data)
    login_resp = await client.post("/auth/login", json={
        "email": test_user_data["email"],
        "password": test_user_data["password"],
    })
    token = login_resp.json()["tokens"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Change password
    response = await client.post("/auth/change-password", json={
        "current_password": test_user_data["password"],
        "new_password": "NewSecureP@ss456",
    }, headers=headers)
    assert response.status_code == 200

    # Login with new password should work
    response = await client.post("/auth/login", json={
        "email": test_user_data["email"],
        "password": "NewSecureP@ss456",
    })
    assert response.status_code == 200

    # Login with old password should fail
    response = await client.post("/auth/login", json={
        "email": test_user_data["email"],
        "password": test_user_data["password"],
    })
    assert response.status_code == 401
