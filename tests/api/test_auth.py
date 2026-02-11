"""Tests for authentication endpoints (register, login, refresh, protect).

All tests are skipped until the API router and database are wired up.
The test structure follows the expected endpoint contracts.
"""

import pytest


@pytest.mark.skip(reason="API auth endpoints not implemented yet")
def test_register(client):
    """POST /auth/register should create a new user and return tokens."""
    # response = await client.post("/auth/register", json={
    #     "email": "new@kairos.dev",
    #     "password": "SecureP@ss123",
    #     "username": "newuser",
    # })
    # assert response.status_code == 201
    # data = response.json()
    # assert "tokens" in data
    # assert data["tokens"]["token_type"] == "bearer"
    # assert "user" in data
    # assert data["user"]["email"] == "new@kairos.dev"


@pytest.mark.skip(reason="API auth endpoints not implemented yet")
def test_login(client):
    """POST /auth/login should return tokens for valid credentials."""
    # # First register
    # await client.post("/auth/register", json={
    #     "email": "login@kairos.dev",
    #     "password": "SecureP@ss123",
    #     "username": "loginuser",
    # })
    # # Then login
    # response = await client.post("/auth/login", json={
    #     "email": "login@kairos.dev",
    #     "password": "SecureP@ss123",
    # })
    # assert response.status_code == 200
    # data = response.json()
    # assert "tokens" in data
    # assert data["tokens"]["access_token"]
    # assert data["tokens"]["refresh_token"]


@pytest.mark.skip(reason="API auth endpoints not implemented yet")
def test_login_wrong_password(client):
    """POST /auth/login with wrong password should return 401."""
    # await client.post("/auth/register", json={
    #     "email": "wrong@kairos.dev",
    #     "password": "SecureP@ss123",
    #     "username": "wronguser",
    # })
    # response = await client.post("/auth/login", json={
    #     "email": "wrong@kairos.dev",
    #     "password": "WrongPassword!",
    # })
    # assert response.status_code == 401


@pytest.mark.skip(reason="API auth endpoints not implemented yet")
def test_refresh_token(client):
    """POST /auth/refresh should return new tokens from a valid refresh token."""
    # # Register and login to get tokens
    # await client.post("/auth/register", json={
    #     "email": "refresh@kairos.dev",
    #     "password": "SecureP@ss123",
    #     "username": "refreshuser",
    # })
    # login_resp = await client.post("/auth/login", json={
    #     "email": "refresh@kairos.dev",
    #     "password": "SecureP@ss123",
    # })
    # refresh_token = login_resp.json()["tokens"]["refresh_token"]
    #
    # response = await client.post("/auth/refresh", json={
    #     "refresh_token": refresh_token,
    # })
    # assert response.status_code == 200
    # data = response.json()
    # assert data["tokens"]["access_token"]


@pytest.mark.skip(reason="API auth endpoints not implemented yet")
def test_protected_endpoint_without_token(client):
    """Accessing a protected endpoint without a token should return 401."""
    # response = await client.get("/trades/")
    # assert response.status_code == 401
    # assert "detail" in response.json()
