"""Password reset (forgot password) flow tests.

Covers Priority 7: secure backend password-reset support.
- Generic response never reveals whether an email exists.
- Tokens are cryptographically secure, single-use, and short-lived.
- New password must satisfy the strong-password policy.
- Tokens are invalidated after use and by newer reset requests.
"""

import pytest

from app.config import settings

STRONG = "N3w!StrongPass"


@pytest.fixture
def expose_reset_token(monkeypatch):
    """Expose dev reset tokens in API responses for testing."""
    monkeypatch.setattr(settings, "EXPOSE_RESET_TOKEN_IN_RESPONSE", True)


@pytest.mark.asyncio
async def test_forgot_password_unknown_email_generic_response(client):
    """Unknown email must get the same generic 200 response (no enumeration)."""
    resp = await client.post(
        "/api/v1/auth/forgot-password", json={"email": "nobody@example.com"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "reset link" in data["message"].lower()
    assert data["dev_reset_token"] is None


@pytest.mark.asyncio
async def test_forgot_password_existing_user_gets_token(client, expose_reset_token):
    """A known email generates a reset token (exposed only in dev/test mode)."""
    email = "resetme@example.com"
    resp = await client.post(
        "/api/v1/auth/signup",
        json={"full_name": "Reset User", "email": email, "password": "Str0ng!Pass"},
    )
    assert resp.status_code == 201

    resp = await client.post("/api/v1/auth/forgot-password", json={"email": email})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["dev_reset_token"]  # non-empty token


@pytest.mark.asyncio
async def test_reset_password_with_valid_token_succeeds(client, expose_reset_token):
    """Full cycle: forgot → reset → old password rejected, new password works."""
    email = "cycle@example.com"
    old_password = "Str0ng!Pass"
    await client.post(
        "/api/v1/auth/signup",
        json={"full_name": "Cycle User", "email": email, "password": old_password},
    )

    resp = await client.post("/api/v1/auth/forgot-password", json={"email": email})
    token = resp.json()["dev_reset_token"]

    resp = await client.post(
        "/api/v1/auth/reset-password", json={"token": token, "password": STRONG}
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    # Old password must no longer work.
    resp = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": old_password}
    )
    assert resp.status_code == 401

    # New password must work.
    resp = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": STRONG}
    )
    assert resp.status_code == 200
    assert resp.json()["access_token"]


@pytest.mark.asyncio
async def test_reset_token_is_single_use(client, expose_reset_token):
    """A used token cannot reset the password a second time."""
    email = "single@example.com"
    await client.post(
        "/api/v1/auth/signup",
        json={"full_name": "Single User", "email": email, "password": "Str0ng!Pass"},
    )
    resp = await client.post("/api/v1/auth/forgot-password", json={"email": email})
    token = resp.json()["dev_reset_token"]

    first = await client.post(
        "/api/v1/auth/reset-password", json={"token": token, "password": STRONG}
    )
    assert first.status_code == 200

    second = await client.post(
        "/api/v1/auth/reset-password", json={"token": token, "password": "An0ther!Pass9"}
    )
    assert second.status_code == 400


@pytest.mark.asyncio
async def test_reset_rejects_weak_password(client, expose_reset_token):
    """Reset must enforce the same strong-password policy as signup."""
    email = "weak@example.com"
    await client.post(
        "/api/v1/auth/signup",
        json={"full_name": "Weak User", "email": email, "password": "Str0ng!Pass"},
    )
    resp = await client.post("/api/v1/auth/forgot-password", json={"email": email})
    token = resp.json()["dev_reset_token"]

    resp = await client.post(
        "/api/v1/auth/reset-password", json={"token": token, "password": "weakpass"}
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_new_forgot_request_invalidates_previous_token(client, expose_reset_token):
    """Requesting a new reset invalidates any earlier outstanding token."""
    email = "rotate@example.com"
    await client.post(
        "/api/v1/auth/signup",
        json={"full_name": "Rotate User", "email": email, "password": "Str0ng!Pass"},
    )
    first = (
        await client.post("/api/v1/auth/forgot-password", json={"email": email})
    ).json()["dev_reset_token"]
    second = (
        await client.post("/api/v1/auth/forgot-password", json={"email": email})
    ).json()["dev_reset_token"]
    assert first != second

    resp = await client.post(
        "/api/v1/auth/reset-password", json={"token": first, "password": STRONG}
    )
    assert resp.status_code == 400

    resp = await client.post(
        "/api/v1/auth/reset-password", json={"token": second, "password": STRONG}
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_reset_rejects_unknown_or_malformed_token(client):
    """Invalid tokens get a clean 400, never a 500."""
    resp = await client.post(
        "/api/v1/auth/reset-password",
        json={"token": "x" * 40, "password": STRONG},
    )
    assert resp.status_code == 400
