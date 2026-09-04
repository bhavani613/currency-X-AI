"""Schemas for the AI Advisor endpoint (rule-based, no external AI API)."""

from pydantic import BaseModel, Field

from app.schemas.payment import PaymentAnalysisRequest

# The advisor accepts exactly the same payload as payment analysis, so the
# existing request schema is reused — one source of truth for validation.
AdvisorRequest = PaymentAnalysisRequest


class AdvisorInsight(BaseModel):
    """A single key insight card."""

    title: str = Field(..., min_length=1, description="Short insight heading.")
    description: str = Field(..., min_length=1, description="Detailed explanation.")


class AdvisorResponse(BaseModel):
    """Structured advisor response generated from payment analysis results."""

    success: bool
    summary: str
    recommended_method: str
    potential_savings: float
    insights: list[AdvisorInsight]
    risk_level: str = Field(..., pattern=r"^(low|medium|high)$")
    tips: list[str]
    disclaimer: str
    # True when the response was enhanced by the optional LLM layer
    ai_enhanced: bool = False
    # AI-generated explanation fields (only present when ai_enhanced=true)
    ai_summary: str | None = None
    ai_key_insight: str | None = None
    ai_recommended_action: str | None = None
    ai_risk_note: str | None = None