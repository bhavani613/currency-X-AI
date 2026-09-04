"""Tests for Revenue Recovery - server-side payment verification and trustworthiness.

These tests verify that recovery cases are only marked as EXECUTED when:
1. A payment order was created by this backend for the authenticated user
2. The payment was verified through the backend's verify endpoint
3. The order is linked to the recovery case

Arbitrary fake demo IDs and cross-user attempts are rejected.
"""

import uuid

import pytest

from tests.helpers import register_and_login, auth_headers


@pytest.mark.asyncio
async def test_recovery_marked_executed_on_verified_payment(client):
    """A recovery case should be marked EXECUTED only after backend-verified payment."""
    token = await register_and_login(client)
    
    # Create a recovery case
    resp = await client.post(
        "/api/v1/recovery/analyze-failure",
        headers=auth_headers(token),
        json={
            "amount": 15000,
            "currency": "INR",
            "payment_method": "UPI",
            "failure_code": "INSUFFICIENT_FUNDS",
            "failure_message": "Insufficient balance.",
        },
    )
    assert resp.status_code == 200
    case_id = resp.json()["recommendation_id"]
    
    # Create a linked order
    resp = await client.post(
        "/api/v1/payments/create-order",
        json={
            "amount": 15000,
            "currency": "INR",
            "receipt": f"test_{uuid.uuid4().hex[:8]}",
            "payment_method": "UPI",
            "recovery_case_id": case_id,
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    order_id = resp.json()["order_id"]
    
    # Verify the payment
    resp = await client.post(
        "/api/v1/payments/verify",
        json={
            "razorpay_payment_id": "demo_payment_123",
            "razorpay_order_id": order_id,
            "razorpay_signature": "any_sig",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    assert resp.json()["recovery_updated"] is True
    
    # Check the recovery case is now EXECUTED
    resp = await client.get(
        "/api/v1/recovery/summary",
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    assert resp.json()["recovered_cases"] == 1
    assert resp.json()["recovered_revenue"] == 15000.0


@pytest.mark.asyncio
async def test_duplicate_verification_is_idempotent(client):
    """Verifying the same payment twice should not double-count recovered revenue."""
    token = await register_and_login(client)
    
    # Create a recovery case
    resp = await client.post(
        "/api/v1/recovery/analyze-failure",
        headers=auth_headers(token),
        json={
            "amount": 10000,
            "currency": "INR",
            "payment_method": "UPI",
            "failure_code": "INSUFFICIENT_FUNDS",
            "failure_message": "Insufficient balance.",
        },
    )
    assert resp.status_code == 200
    case_id = resp.json()["recommendation_id"]
    
    # Create a linked order
    resp = await client.post(
        "/api/v1/payments/create-order",
        json={
            "amount": 10000,
            "currency": "INR",
            "receipt": f"test_{uuid.uuid4().hex[:8]}",
            "payment_method": "UPI",
            "recovery_case_id": case_id,
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    order_id = resp.json()["order_id"]
    
    # Verify the payment twice
    for _ in range(2):
        resp = await client.post(
            "/api/v1/payments/verify",
            json={
                "razorpay_payment_id": "demo_payment_123",
                "razorpay_order_id": order_id,
                "razorpay_signature": "any_sig",
            },
            headers=auth_headers(token),
        )
        assert resp.status_code == 200
    
    # Check recovered revenue is counted only once
    resp = await client.get(
        "/api/v1/recovery/summary",
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    assert resp.json()["recovered_cases"] == 1
    assert resp.json()["recovered_revenue"] == 10000.0


@pytest.mark.asyncio
async def test_unlinked_order_does_not_mark_recovery_executed(client):
    """Verifying an order NOT linked to a recovery case should not mark any case as EXECUTED."""
    token = await register_and_login(client)
    
    # Create a recovery case
    resp = await client.post(
        "/api/v1/recovery/analyze-failure",
        headers=auth_headers(token),
        json={
            "amount": 5000,
            "currency": "INR",
            "payment_method": "UPI",
            "failure_code": "INSUFFICIENT_FUNDS",
            "failure_message": "Insufficient balance.",
        },
    )
    assert resp.status_code == 200
    
    # Create an order WITHOUT linking to recovery case
    resp = await client.post(
        "/api/v1/payments/create-order",
        json={
            "amount": 5000,
            "currency": "INR",
            "receipt": f"test_{uuid.uuid4().hex[:8]}",
            "payment_method": "UPI",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    order_id = resp.json()["order_id"]
    
    # Verify the payment
    resp = await client.post(
        "/api/v1/payments/verify",
        json={
            "razorpay_payment_id": "demo_payment_123",
            "razorpay_order_id": order_id,
            "razorpay_signature": "any_sig",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    assert resp.json()["recovery_updated"] is False
    
    # Check no recovery case was marked as EXECUTED
    resp = await client.get(
        "/api/v1/recovery/summary",
        headers=auth_headers(token),
    )
    assert resp.status_code == 200
    assert resp.json()["recovered_cases"] == 0
    assert resp.json()["recovered_revenue"] == 0.0


@pytest.mark.asyncio
async def test_cross_user_order_cannot_mark_recovery_executed(client):
    """User B cannot use their order to mark User A's recovery case as EXECUTED."""
    # Create two users
    token_a = await register_and_login(client, email="user_a_cross@example.com")
    token_b = await register_and_login(client, email="user_b_cross@example.com")
    
    # User A creates a recovery case
    resp = await client.post(
        "/api/v1/recovery/analyze-failure",
        headers=auth_headers(token_a),
        json={
            "amount": 8000,
            "currency": "INR",
            "payment_method": "UPI",
            "failure_code": "INSUFFICIENT_FUNDS",
            "failure_message": "Insufficient balance.",
        },
    )
    assert resp.status_code == 200
    case_id_a = resp.json()["recommendation_id"]
    
    # User B creates an order (trying to link to User A's case)
    resp = await client.post(
        "/api/v1/payments/create-order",
        json={
            "amount": 8000,
            "currency": "INR",
            "receipt": f"test_{uuid.uuid4().hex[:8]}",
            "payment_method": "UPI",
            "recovery_case_id": case_id_a,  # User A's case
        },
        headers=auth_headers(token_b),
    )
    # Should be rejected because the case doesn't belong to User B
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_arbitrary_fake_demo_order_rejected(client):
    """Arbitrary fake demo_order_* IDs should be rejected as proof of payment."""
    token = await register_and_login(client)
    
    resp = await client.post(
        "/api/v1/payments/verify",
        json={
            "razorpay_payment_id": "demo_payment_123",
            "razorpay_order_id": "demo_order_totally_fake_not_in_db",
            "razorpay_signature": "any_sig",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 400