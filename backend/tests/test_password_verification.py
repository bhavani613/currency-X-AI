"""Tests for the POST /auth/verify-password endpoint.

Covers:
  - Unauthenticated requests are rejected (401).
  - Correct password is accepted (200, success=true).
  - Incorrect password is rejected (401).
  - The response never contains password hashes or plaintext.
"""

import pytest


@pytest.mark.asyncio
async def test_verify_password_requires_auth(client):
    """POST /auth/verify-password without a JWT → 401."""
    resp = await client.post(
        "/api/v1/auth/verify-password",
        json={"password": "Str0ng!Pass"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_verify_password_correct(client, auth_headers):
    """Correct password → 200 with success=true."""
    resp = await client.post(
        "/api/v1/auth/verify-password",
        headers=auth_headers,
        json={"password": "Str0ng!Pass"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True


@pytest.mark.asyncio
async def test_verify_password_incorrect(client, auth_headers):
    """Incorrect password → 401."""
    resp = await client.post(
        "/api/v1/auth/verify-password",
        headers=auth_headers,
        json={"password": "WrongPass!1"},
    )
    assert resp.status_code == 401
    data = resp.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_verify_password_never_returns_hash(client, auth_headers):
    """The response must never include the password hash or plaintext."""
    resp = await client.post(
        "/api/v1/auth/verify-password",
        headers=auth_headers,
        json={"password": "Str0ng!Pass"},
    )
    assert resp.status_code == 200
    body_text = resp.text.lower()
    assert "password_hash" not in body_text
    assert "str0ng!pass" not in body_text
    assert "$2b$" not in body_text  # bcrypt hash prefix


@pytest.mark.asyncio
async def test_verify_password_empty_rejected(client, auth_headers):
    """An empty password must be rejected by validation (422)."""
    resp = await client.post(
        "/api/v1/auth/verify-password",
        headers=auth_headers,
        json={"password": ""},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_verify_password_invalid_token_rejected(client):
    """A garbage JWT must be rejected with 401 (not 500)."""
    resp = await client.post(
        "/api/v1/auth/verify-password",
        headers={"Authorization": "Bearer definitely.not.a.valid.jwt"},
        json={"password": "Str0ng!Pass"},
    )
    assert resp.status_code == 401
