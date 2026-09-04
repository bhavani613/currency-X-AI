"""Tests for Revenue Recovery - completion, idempotency, and revenue tracking."""

import pytest


@pytest.mark.asyncio
async def test_complete_recovery_works(client, auth_headers):
    """Completing a recovery should mark it as EXECUTED."""
    resp = await client.post(
        "/api/v1/recovery/analyze-failure",
        headers=auth_headers,
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

    resp = await client.post(
        f"/api/v1/recovery/cases/{case_id}/complete",
        headers=auth_headers,
        json={"recovered_amount": 15000},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["recommendation_status"] == "EXECUTED"
    assert data["recovered_amount"] == 15000.0


@pytest.mark.asyncio
async def test_complete_recovery_is_idempotent(client, auth_headers):
    """Completing the same recovery twice should not double-count."""
    resp = await client.post(
        "/api/v1/recovery/analyze-failure",
        headers=auth_headers,
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

    resp = await client.post(
        f"/api/v1/recovery/cases/{case_id}/complete",
        headers=auth_headers,
        json={"recovered_amount": 10000},
    )
    assert resp.status_code == 200
    assert resp.json()["recommendation_status"] == "EXECUTED"

    resp = await client.post(
        f"/api/v1/recovery/cases/{case_id}/complete",
        headers=auth_headers,
        json={"recovered_amount": 10000},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["already_recovered"] is True

    resp = await client.get(
        "/api/v1/recovery/summary",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    summary = resp.json()
    assert summary["recovered_revenue"] == 10000.0
    assert summary["recovered_cases"] == 1


@pytest.mark.asyncio
async def test_dismissed_case_cannot_be_completed(client, auth_headers):
    """A dismissed case should not be marked as recovered."""
    resp = await client.post(
        "/api/v1/recovery/analyze-failure",
        headers=auth_headers,
        json={
            "amount": 5000,
            "currency": "INR",
            "payment_method": "UPI",
            "failure_code": "INSUFFICIENT_FUNDS",
            "failure_message": "Insufficient balance.",
        },
    )
    assert resp.status_code == 200
    case_id = resp.json()["recommendation_id"]

    await client.post(
        f"/api/v1/recovery/cases/{case_id}/dismiss",
        headers=auth_headers,
    )

    resp = await client.post(
        f"/api/v1/recovery/cases/{case_id}/complete",
        headers=auth_headers,
        json={"recovered_amount": 5000},
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_recovery_summary_includes_recovered_revenue(client, auth_headers):
    """Summary should include recovered_revenue and recovered_cases fields."""
    resp = await client.get(
        "/api/v1/recovery/summary",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "recovered_revenue" in data
    assert "recovered_cases" in data
    assert "total_cases" in data
