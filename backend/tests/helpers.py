"""Shared helpers for tests that need multiple authenticated users.

``conftest.py`` provides ``auth_token`` / ``auth_headers`` fixtures for the
single-user case; these helpers allow a test to register additional users
on demand (e.g. cross-user isolation tests).
"""

import uuid

STRONG_PASSWORD = "Str0ng!Pass"


async def register_and_login(client, email: str | None = None, password: str = STRONG_PASSWORD) -> str:
    """Register a fresh user via the API and return their JWT access token."""
    if email is None:
        email = f"test_{uuid.uuid4().hex[:8]}@example.com"

    resp = await client.post(
        "/api/v1/auth/signup",
        json={
            "full_name": "Test User",
            "email": email,
            "password": password,
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    return data["access_token"]


def auth_headers(token: str) -> dict:
    """Return headers dict with JWT bearer token for authenticated requests."""
    return {"Authorization": f"Bearer {token}"}


async def login(client, email: str, password: str = STRONG_PASSWORD) -> str:
    """Log in an existing user and return their JWT access token."""
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]