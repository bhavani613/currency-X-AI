"""Tests that JWT-protected Revenue Recovery endpoints reject unauthenticated access.

Every /recovery/* route is user-scoped and must return 401 without a valid
Authorization header. This suite verifies the guard, not the business logic.
"""

import pytest


@pytest.mark.asyncio
async def test_recovery_cases_requires_auth(client):
    """GET /recovery/cases without a token → 401."""
    resp = await client.get("/api/v1/recovery/cases")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_recovery_summary_requires_auth(client):
    """GET /recovery/summary without a token → 401."""
    resp = await client.get("/api/v1/recovery/summary")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_analyze_failure_requires_auth(client):
    """POST /recovery/analyze-failure without a token → 401."""
    resp = await client.post(
        "/api/v1/recovery/analyze-failure",
        json={
            "amount": 1000,
            "currency": "INR",
            "payment_method": "UPI",
            "failure_code": "INSUFFICIENT_FUNDS",
            "failure_message": "Insufficient balance.",
        },
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_payment_attempts_requires_auth(client):
    """POST /recovery/payment-attempts without a token → 401."""
    resp = await client.post(
        "/api/v1/recovery/payment-attempts",
        json={
            "amount": 1000,
            "currency": "INR",
            "payment_method": "UPI",
        },
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_retry_requires_auth(client):
    """POST /recovery/cases/{id}/retry without a token → 401."""
    resp = await client.post("/api/v1/recovery/cases/some-random-id/retry")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_invalid_token_rejected(client):
    """A malformed/garbage JWT must be rejected with 401 (not 500)."""
    resp = await client.get(
        "/api/v1/recovery/cases",
        headers={"Authorization": "Bearer definitely.not.a.valid.jwt"},
    )
    assert resp.status_code == 401