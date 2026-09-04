"""Tests for Revenue Recovery - isolation and retry/dismiss actions."""

import pytest


@pytest.mark.asyncio
async def test_user_cannot_access_other_users_recovery_case(
    client, auth_headers
):
    """A user should not see another user's recovery cases."""

    resp = await client.post(
        "/api/v1/recovery/analyze-failure",
        headers=auth_headers,
        json={
            "amount": 25000,
            "currency": "INR",
            "payment_method": "UPI",
            "failure_code": "INSUFFICIENT_FUNDS",
            "failure_message": "Insufficient balance.",
        },
    )
    assert resp.status_code == 200
    case_id = resp.json()["recommendation_id"]

    resp = await client.post(
        "/api/v1/auth/signup",
        json={
            "full_name": "Other User",
            "email": f"other_{case_id[:8]}@example.com",
            "password": "Str0ng!Pass",
        },
    )
    assert resp.status_code == 201
    token_2 = resp.json()["access_token"]
    headers_2 = {"Authorization": f"Bearer {token_2}"}

    resp = await client.get(
        f"/api/v1/recovery/cases/{case_id}",
        headers=headers_2,
    )
    assert resp.status_code == 404

    resp = await client.get(
        "/api/v1/recovery/cases",
        headers=headers_2,
    )
    assert resp.status_code == 200
    assert resp.json() == []

    resp = await client.post(
        f"/api/v1/recovery/cases/{case_id}/complete",
        headers=headers_2,
        json={"recovered_amount": 25000},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_retry_action_works(client, auth_headers):
    """Retry should return original payment details for restoration."""
    resp = await client.post(
        "/api/v1/recovery/analyze-failure",
        headers=auth_headers,
        json={
            "amount": 25000,
            "currency": "INR",
            "payment_method": "UPI",
            "failure_code": "INSUFFICIENT_FUNDS",
            "failure_message": "Insufficient balance.",
        },
    )
    assert resp.status_code == 200
    case_id = resp.json()["recommendation_id"]

    resp = await client.post(
        f"/api/v1/recovery/cases/{case_id}/retry",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "retry_payment" in data
    assert data["retry_payment"]["amount"] == 25000
    assert data["case_id"] == case_id
    assert data["payment_attempt_id"]


@pytest.mark.asyncio
async def test_dismiss_action_works(client, auth_headers):
    """Dismiss should mark the recommendation as DISMISSED."""
    resp = await client.post(
        "/api/v1/recovery/analyze-failure",
        headers=auth_headers,
        json={
            "amount": 15000,
            "currency": "INR",
            "payment_method": "Credit Card",
            "failure_code": "CARD_DECLINED",
            "failure_message": "Card declined by bank.",
        },
    )
    assert resp.status_code == 200
    case_id = resp.json()["recommendation_id"]

    resp = await client.post(
        f"/api/v1/recovery/cases/{case_id}/dismiss",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True

    resp = await client.get(
        f"/api/v1/recovery/cases/{case_id}",
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "DISMISSED"
