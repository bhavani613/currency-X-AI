"""Tests for the AI Advisor deterministic fallback.

These tests verify the advisor works WITHOUT any OpenAI/LLM API key:
- The `/advisor/analyze` endpoint succeeds and returns the deterministic
  rule-based response.
- `ai_enhanced` stays false when no provider is configured.
- Missing key (AI_ENABLED=true + empty key) does not crash.
- A raising provider fails safely back to deterministic output.

No real AI provider is ever called.
"""

import pytest

from app.services.ai_provider import enhance_advisor_explanation


def _payload(**overrides):
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
async def test_advisor_endpoint_succeeds_without_ai_key(client):
    """With AI disabled the advisor returns the deterministic response."""
    resp = await client.post("/api/v1/advisor/analyze", json=_payload())
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["ai_enhanced"] is False
    assert data["ai_summary"] is None
    assert data["recommended_method"]
    assert data["risk_level"] in ("low", "medium", "high")
    assert len(data["insights"]) > 0
    assert data["summary"]
    assert data["disclaimer"]


@pytest.mark.asyncio
async def test_advisor_invalid_payload_rejected(client):
    """Invalid source currency must be rejected with 422 (validation intact)."""
    resp = await client.post(
        "/api/v1/advisor/analyze", json=_payload(source_currency="XYZ")
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_advisor_ai_enabled_without_key_falls_back(client, monkeypatch):
    """AI_ENABLED=true with an empty OPENAI_API_KEY must not crash or fail."""
    from app.services import ai_provider

    monkeypatch.setattr(ai_provider.settings, "AI_ENABLED", True)
    monkeypatch.setattr(ai_provider.settings, "AI_PROVIDER", "openai")
    monkeypatch.setattr(ai_provider.settings, "OPENAI_API_KEY", "")

    resp = await client.post("/api/v1/advisor/analyze", json=_payload())
    assert resp.status_code == 200
    data = resp.json()
    # Deterministic fallback — no AI explanation layer.
    assert data["ai_enhanced"] is False
    assert data["recommended_method"]
    assert data["summary"]


class _FakeCompletions:
    def create(self, **_kwargs):
        raise RuntimeError("simulated provider outage")


class _FakeChat:
    completions = _FakeCompletions()


class _FakeClient:
    chat = _FakeChat()


@pytest.mark.asyncio
async def test_advisor_provider_failure_falls_back(client, monkeypatch):
    """A raising AI provider must fall back to the deterministic response."""
    from app.services import ai_provider

    monkeypatch.setattr(ai_provider.settings, "AI_ENABLED", True)
    monkeypatch.setattr(ai_provider.settings, "AI_PROVIDER", "openai")
    monkeypatch.setattr(ai_provider.settings, "OPENAI_API_KEY", "sk-fake-for-test")
    monkeypatch.setattr(ai_provider, "_client", lambda: (_FakeClient(), "fake-model"))

    resp = await client.post("/api/v1/advisor/analyze", json=_payload())
    assert resp.status_code == 200
    data = resp.json()
    assert data["ai_enhanced"] is False
    assert data["recommended_method"]
    assert data["summary"]


def test_enhance_returns_none_when_disabled(monkeypatch):
    """Direct call: when AI_ENABLED=false, enhance returns None (no provider call)."""
    from app.services import ai_provider

    monkeypatch.setattr(ai_provider.settings, "AI_ENABLED", False)

    result = enhance_advisor_explanation(
        analysis_summary="summary",
        insights=["insight"],
        recommended_method="UPI",
        risk_level="low",
        amount="₹10,000",
        source_currency="INR",
        destination="United Kingdom (GBP)",
    )
    assert result is None