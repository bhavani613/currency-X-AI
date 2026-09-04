"""Tests for the Revenue Recovery engine - failure analysis and duplicate prevention.

Tests verify:
- Failed payment → recovery recommendation
- Duplicate prevention
"""

import pytest


@pytest.mark.asyncio
async def test_failure_analysis_creates_recommendation(client, auth_headers):
    """A failed payment should produce a recovery recommendation."""
    resp = await client.post(
        "/api/v1/recovery/analyze-failure",
        headers=auth_headers,
        json={
            "amount": 25000,
            "currency": "INR",
            "payment_method": "UPI",
            "failure_code": "INSUFFICIENT_FUNDS",
            "failure_message": "Insufficient balance in your account.",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["recommendation_id"]
    assert data["payment_attempt_id"]
    assert data["duplicate"] is False
    assert data["analysis"]["failure_category"] == "INSUFFICIENT_FUNDS"
    assert data["analysis"]["recovery_probability"] > 0


@pytest.mark.asyncio
async def test_duplicate_gateway_payment_id_not_duplicated(
    client, auth_headers
):
    """Same gateway payment ID should return existing case, not create new one."""

    resp = await client.post(
        "/api/v1/recovery/analyze-failure",
        headers=auth_headers,
        json={
            "amount": 25000,
            "currency": "INR",
            "payment_method": "UPI",
            "failure_code": "INSUFFICIENT_FUNDS",
            "failure_message": "Insufficient balance in your account.",
            "gateway_payment_id": "pay_test_dup_123",
        },
    )
    assert resp.status_code == 200
    first = resp.json()

    resp = await client.post(
        "/api/v1/recovery/analyze-failure",
        headers=auth_headers,
        json={
            "amount": 25000,
            "currency": "INR",
            "payment_method": "UPI",
            "failure_code": "INSUFFICIENT_FUNDS",
            "failure_message": "Insufficient balance in your account.",
            "gateway_payment_id": "pay_test_dup_123",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["duplicate"] is True
    assert data["recommendation_id"] == first["recommendation_id"]
