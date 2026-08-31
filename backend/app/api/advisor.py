"""Thin route handler for the AI Advisor.

Endpoint:
  * POST /api/v1/advisor/analyze - rule-based advisor insights derived from
    the existing payment analysis engine.

All logic lives in :class:`app.services.advisor.AdvisorService`; the route
only validates input and delegates.
"""

from fastapi import APIRouter, HTTPException

from app.schemas.advisor import AdvisorRequest, AdvisorResponse
from app.services.advisor import AdvisorService

router = APIRouter()

# Single shared instance — the service holds no request-scoped state.
_advisor = AdvisorService()


@router.post(
    "/advisor/analyze",
    response_model=AdvisorResponse,
    summary="Get AI-style payment insights (rule-based)",
    description=(
        "Runs the existing payment analysis and derives a structured "
        "advisor response: summary, recommended method, potential savings, "
        "key insights, risk level and smart tips. No external AI API required."
    ),
)
async def analyze_advice(request: AdvisorRequest) -> AdvisorResponse:
    """Return rule-based advisor insights for a payment request."""
    try:
        return _advisor.analyze(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc