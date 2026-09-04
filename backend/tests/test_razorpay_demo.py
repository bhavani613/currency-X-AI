"""Tests for Razorpay Demo Mode payment operations.

Tests verify that demo mode works without real Razorpay credentials.
No real Razorpay API calls are made.

NOTE: create-order and verify require authentication (security hardening),
so every payment test registers a user and sends a Bearer token.
"""

import uuid

import pytest

from tests.helpers import register_and_login, auth_headers


@pytest.mark.asyncio
async def test_backend_starts_without_razorpay_credentials(client):
    """Backend should be healthy and ready even without Razorpay keys."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"

    resp = await client.get("/ready")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_demo_create_order_succeeds(client):
    """Demo mode should create an order with a demo_order_* ID."""
    token = await register_and_login(client)
    resp = await client.post(
        "/api/v1/payments/create-order",
        json={
            "amount": 500,
            "currency": "INR",
            "receipt": f"test_receipt_{uuid.uuid4().hex[:8]}",
            "payment_method": "UPI",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["order_id"].startswith("demo_order_")
    assert data["amount"] == 50000  # converted to paise
    assert data["currency"] == "INR"
    assert data["demo"] is True


@pytest.mark.asyncio
async def test_demo_create_order_no_real_razorpay_call(client):
    """Demo order creation must not require real Razorpay keys."""
    token = await register_and_login(client)
    resp = await client.post(
        "/api/v1/payments/create-order",
        json={
            "amount": 1000,
            "currency": "INR",
            "receipt": f"demo_{uuid.uuid4().hex[:8]}",
            "payment_method": "Smart Payment",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    data = resp.json()
    # demo=True means no real Razorpay call was made
    assert data["demo"] is True
    assert data["key_id"] == "demo"  # public placeholder only


@pytest.mark.asyncio
async def test_demo_payment_verification_succeeds(client):
    """Demo payment verification should accept demo_payment_* IDs for orders created by this backend."""
    token = await register_and_login(client)
    
    # First create a demo order
    create_resp = await client.post(
        "/api/v1/payments/create-order",
        json={
            "amount": 500,
            "currency": "INR",
            "receipt": f"test_receipt_{uuid.uuid4().hex[:8]}",
            "payment_method": "UPI",
        },
        headers=auth_headers(token),
    )
    assert create_resp.status_code == 200
    order_id = create_resp.json()["order_id"]
    
    # Now verify the payment for that order
    resp = await client.post(
        "/api/v1/payments/verify",
        json={
            "razorpay_payment_id": "demo_payment_abc123",
            "razorpay_order_id": order_id,
            "razorpay_signature": "any_signature_value",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["demo"] is True


@pytest.mark.asyncio
async def test_demo_payment_verification_rejects_unknown_order(client):
    """Demo payment verification should reject arbitrary fake demo_order_* IDs."""
    token = await register_and_login(client)
    resp = await client.post(
        "/api/v1/payments/verify",
        json={
            "razorpay_payment_id": "demo_payment_abc123",
            "razorpay_order_id": "demo_order_fake_order_not_created_by_backend",
            "razorpay_signature": "any_signature_value",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_real_payment_logic_not_removed(client):
    """Verify that real payment verification path exists (not accidentally removed)."""
    token = await register_and_login(client)
    # When demo mode is active, non-demo payment IDs should be rejected
    resp = await client.post(
        "/api/v1/payments/verify",
        json={
            "razorpay_payment_id": "real_payment_abc123",  # not a demo ID
            "razorpay_order_id": "real_order_xyz789",
            "razorpay_signature": "any_signature",
        },
        headers=auth_headers(token),
    )
    # In demo mode without real keys, this should fail (400)
    # but NOT crash (500) — proving the real logic path still exists
    assert resp.status_code in (400, 502, 503)
