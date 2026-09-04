"""Tests for the payment analysis endpoint.

Tests use the TestClient with an in-memory SQLite database.
No real payment providers are called.
"""

import pytest

from tests.helpers import register_and_login


def _valid_payload(**overrides):
    """Return a valid payment analysis request payload with optional overrides."""
    base = {
        "amount": 10000,
        "source_currency": "INR",
        "destination_country": "United Kingdom",
        "destination_currency": "GBP",
        "purpose": "Education",
    }
    base.update(overrides)
    return base


@pytest.mark.asyncio
async def test_valid_payment_analysis_succeeds(client, auth_headers):
    """A valid payment analysis request should return 200 with analysis."""
    resp = await client.post(
        "/api/v1/payments/analyze",
        headers=auth_headers,
        json=_valid_payload(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["payment"]["amount"] == 10000
    assert data["payment"]["source_currency"] == "INR"
    assert data["payment"]["destination_currency"] == "GBP"
    assert data["recommendation"]["method"]
    assert data["recommendation"]["potential_savings"] >= 0


@pytest.mark.asyncio
async def test_analyze_requires_auth(client):
    """POST /payments/analyze without a token → 401."""
    resp = await client.post(
        "/api/v1/payments/analyze",
        json=_valid_payload(),
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_invalid_currency_rejected(client, auth_headers):
    """An invalid source currency code should be rejected with 422."""
    resp = await client.post(
        "/api/v1/payments/analyze",
        headers=auth_headers,
        json=_valid_payload(source_currency="XX"),
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_negative_amount_rejected(client, auth_headers):
    """A negative amount should be rejected."""
    resp = await client.post(
        "/api/v1/payments/analyze",
        headers=auth_headers,
        json=_valid_payload(amount=-100),
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_zero_amount_rejected(client, auth_headers):
    """A zero amount should be rejected."""
    resp = await client.post(
        "/api/v1/payments/analyze",
        headers=auth_headers,
        json=_valid_payload(amount=0),
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_payment_recommendation_returned(client, auth_headers):
    """The response should include a valid recommendation with savings."""
    resp = await client.post(
        "/api/v1/payments/analyze",
        headers=auth_headers,
        json=_valid_payload(),
    )
    assert resp.status_code == 200
    data = resp.json()
    rec = data["recommendation"]
    assert "method" in rec
    assert "potential_savings" in rec
    assert rec["potential_savings"] >= 0
    assert data["recipient"]["estimated_amount"] > 0


@pytest.mark.asyncio
async def test_calculation_output_valid(client, auth_headers):
    """Verify key calculation fields are present and valid."""
    resp = await client.post(
        "/api/v1/payments/analyze",
        headers=auth_headers,
        json=_valid_payload(),
    )
    assert resp.status_code == 200
    data = resp.json()

    # Cost breakdown should have all expected fields
    cb = data["cost_breakdown"]
    assert "fx_markup" in cb
    assert "processing_fee" in cb
    assert "other_charges" in cb
    assert "total_fees" in cb
    assert "total_cost" in cb

    # Total fees should equal sum of components (within rounding)
    computed_total = cb["fx_markup"] + cb["processing_fee"] + cb["other_charges"]
    assert abs(computed_total - cb["total_fees"]) < 0.01

    # Exchange rate must be a positive number
    assert data["exchange_rate"] > 0


@pytest.mark.asyncio
async def test_history_requires_auth(client):
    """GET /payments/history without a token → 401."""
    resp = await client.get("/api/v1/payments/history")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_history_returns_only_own_analyses(client):
    """Users should only see their own analyses in history."""
    # Create two users
    token1 = await register_and_login(client, email="user1_history@example.com")
    token2 = await register_and_login(client, email="user2_history@example.com")

    # User 1 creates an analysis
    resp = await client.post(
        "/api/v1/payments/analyze",
        headers={"Authorization": f"Bearer {token1}"},
        json=_valid_payload(amount=5000),
    )
    assert resp.status_code == 200

    # User 2 creates an analysis
    resp = await client.post(
        "/api/v1/payments/analyze",
        headers={"Authorization": f"Bearer {token2}"},
        json=_valid_payload(amount=10000),
    )
    assert resp.status_code == 200

    # User 1's history should only show their own analysis
    resp = await client.get(
        "/api/v1/payments/history",
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["amount"] == 5000


@pytest.mark.asyncio
async def test_detail_requires_auth(client):
    """GET /payments/{id} without a token → 401."""
    resp = await client.get("/api/v1/payments/some-random-id")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_detail_cross_user_forbidden(client):
    """A user should not be able to access another user's analysis."""
    # Create two users
    token1 = await register_and_login(client, email="user1_detail@example.com")
    token2 = await register_and_login(client, email="user2_detail@example.com")

    # User 1 creates an analysis
    resp = await client.post(
        "/api/v1/payments/analyze",
        headers={"Authorization": f"Bearer {token1}"},
        json=_valid_payload(),
    )
    assert resp.status_code == 200
    analysis_id = resp.json()["id"]

    # User 2 tries to access User 1's analysis → 404
    resp = await client.get(
        f"/api/v1/payments/{analysis_id}",
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert resp.status_code == 404
