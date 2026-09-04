"""Security hardening tests: recovery state machine + payment endpoint auth."""
import uuid

import pytest

from tests.helpers import register_and_login, auth_headers


def test_production_rejects_short_jwt_secret(monkeypatch):
    """ENVIRONMENT=production must refuse to boot with a JWT secret < 32 bytes."""
    from app.config import Settings

    with pytest.raises(Exception):
        Settings(
            ENVIRONMENT="production",
            JWT_SECRET="short-secret",
            _env_file=None,
        )


def test_production_accepts_strong_jwt_secret():
    """A properly-sized secret boots cleanly in production."""
    from app.config import Settings

    s = Settings(
        ENVIRONMENT="production",
        JWT_SECRET="x" * 48,
        _env_file=None,
    )
    assert s.ENVIRONMENT == "production"


def test_development_allows_short_jwt_secret():
    """Dev/demo environments are unaffected by the 32-byte rule."""
    from app.config import Settings

    s = Settings(ENVIRONMENT="development", JWT_SECRET="short-secret", _env_file=None)
    assert s.JWT_SECRET == "short-secret"


@pytest.mark.asyncio
async def test_create_order_without_auth_rejected(client):
    """create-order must require authentication."""
    resp = await client.post(
        "/api/v1/payments/create-order",
        json={"amount": 1000, "currency": "INR", "payment_method": "upi"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_verify_without_auth_rejected(client):
    """verify must require authentication."""
    resp = await client.post(
        "/api/v1/payments/verify",
        json={"razorpay_order_id": "demo_order_x", "razorpay_payment_id": "demo_payment_x", "razorpay_signature": "sig"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_authenticated_demo_create_order_succeeds(client):
    """Demo Mode still works for authenticated users."""
    token = await register_and_login(client)
    resp = await client.post(
        "/api/v1/payments/create-order",
        json={
            "amount": 1000,
            "currency": "INR",
            "receipt": f"sec_{uuid.uuid4().hex[:8]}",
            "payment_method": "UPI",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    assert resp.json().get("order_id", "").startswith("demo_order_")


@pytest.mark.asyncio
async def test_patch_cannot_set_executed_from_pending(client):
    """Generic PATCH must not fabricate recovered revenue (PENDING -> EXECUTED forbidden)."""
    token = await register_and_login(client)
    headers = auth_headers(token)
    # Create a failed payment -> recovery case
    resp = await client.post(
        "/api/v1/recovery/analyze-failure",
        json={
            "gateway_payment_id": f"pay_sec_{uuid.uuid4().hex[:10]}",
            "amount": 5000,
            "currency": "INR",
            "payment_method": "UPI",
            "failure_code": "INSUFFICIENT_FUNDS",
            "failure_message": "Not enough balance",
        },
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    rec_id = data.get("recommendation_id") or data.get("recommendation", {}).get("id")
    if not rec_id:
        cases = (await client.get("/api/v1/recovery/cases", headers=headers)).json()
        rec_id = cases["cases"][0]["id"]

    # Try to set EXECUTED directly via PATCH
    resp = await client.patch(
        f"/api/v1/recovery/recommendations/{rec_id}/status",
        json={"status": "EXECUTED"},
        headers=headers,
    )
    assert resp.status_code in (400, 403, 409), f"EXECUTED via PATCH should be forbidden, got {resp.status_code}"

    # Summary must show zero recovered
    summary = (await client.get("/api/v1/recovery/summary", headers=headers)).json()
    assert summary.get("recovered_revenue", 0) == 0
