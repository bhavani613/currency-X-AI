"""Rule-based AI Advisor service with optional LLM explanation layer.

Generates intelligent, structured insights from the existing
:class:`PaymentAnalyzer` results.  The deterministic logic is the source of
truth and always runs.  When ``AI_ENABLED=true`` and a valid API key is
configured, an optional LLM layer enhances the user-facing explanation on top
of the deterministic result.

The route layer is untouched — ``analyze()`` still returns ``AdvisorResponse``.
"""

import logging

from app.schemas.advisor import AdvisorInsight, AdvisorResponse
from app.schemas.payment import PaymentAnalysisRequest, PaymentAnalysisResponse
from app.services.payment_analyzer import DISCLAIMER, PaymentAnalyzer

logger = logging.getLogger(__name__)

#: Source-currency symbol used when composing human-readable text.
CURRENCY_SYMBOLS = {
    "INR": "₹",
    "USD": "$",
    "GBP": "£",
    "EUR": "€",
    "AED": "AED ",
    "AUD": "A$",
    "CAD": "C$",
}

#: Purposes that are considered time-sensitive / lower risk by default.
LOW_RISK_PURPOSES = {"education", "tuition", "medical", "family support"}

#: Purposes that involve more regulatory/complexity considerations.
HIGHER_RISK_PURPOSES = {"investment", "business", "property", "real estate"}


class AdvisorService:
    """Builds advisor insights on top of the payment analysis engine."""

    def __init__(self, analyzer: PaymentAnalyzer | None = None) -> None:
        self._analyzer = analyzer if analyzer is not None else PaymentAnalyzer()

    def analyze(self, request: PaymentAnalysisRequest) -> AdvisorResponse:
        """Run the payment analysis and derive advisor guidance from it.

        The deterministic analysis always runs first. If the optional LLM layer
        is configured and available, the response is enhanced with an AI-generated
        explanation. Any LLM failure silently falls back to the deterministic result.
        """
        analysis: PaymentAnalysisResponse = self._analyzer.analyze(request)
        response = self._compose(request, analysis)
        return self._maybe_enhance_with_ai(request, analysis, response)

    def _maybe_enhance_with_ai(
        self,
        request: PaymentAnalysisRequest,
        analysis: PaymentAnalysisResponse,
        response: AdvisorResponse,
    ) -> AdvisorResponse:
        """Optionally enhance the deterministic response with an LLM explanation.

        Never raises — any failure returns the deterministic response unchanged.
        """
        try:
            from app.services.ai_provider import enhance_advisor_explanation
        except ImportError:
            return response

        symbol = CURRENCY_SYMBOLS.get(request.source_currency, f"{request.source_currency} ")
        amount_text = f"{symbol}{request.amount:,.0f}"
        dest_text = f"{request.destination_country} ({request.destination_currency})"
        insight_descriptions = [i.description for i in response.insights]

        ai_result = enhance_advisor_explanation(
            analysis_summary=response.summary,
            insights=insight_descriptions,
            recommended_method=response.recommended_method,
            risk_level=response.risk_level,
            amount=amount_text,
            source_currency=request.source_currency,
            destination=dest_text,
        )
        if ai_result is None:
            return response

        # Merge AI explanation into the response — deterministic fields stay authoritative
        response.ai_enhanced = True
        response.ai_summary = ai_result.get("summary")
        response.ai_key_insight = ai_result.get("key_insight")
        response.ai_recommended_action = ai_result.get("recommended_action")
        response.ai_risk_note = ai_result.get("risk_note")
        return response

    def _risk_level(
        self, request: PaymentAnalysisRequest, fee_pct: float
    ) -> str:
        """Simple transparent rules for the risk indicator."""
        purpose = request.purpose.lower()
        if purpose in HIGHER_RISK_PURPOSES or request.amount > 1_000_000:
            return "high" if request.amount > 5_000_000 else "medium"
        if purpose in LOW_RISK_PURPOSES or fee_pct < 3:
            return "low"
        return "medium"

    def _compose(
        self, request: PaymentAnalysisRequest, a: PaymentAnalysisResponse
    ) -> AdvisorResponse:
        symbol = CURRENCY_SYMBOLS.get(request.source_currency, f"{request.source_currency} ")
        dest_symbol = CURRENCY_SYMBOLS.get(request.destination_currency, f"{request.destination_currency} ")
        rec = a.recommendation
        fees = a.cost_breakdown
        amount_text = f"{symbol}{request.amount:,.0f}"
        fee_pct = (fees.total_fees / a.payment.amount * 100) if a.payment.amount else 0

        summary = (
            f"For sending {amount_text} from {request.source_currency} to "
            f"{request.destination_country}, {rec.method} is currently the "
            f"most cost-effective option."
        )

        purpose_note = (
            "For this purpose, speed may matter as much as cost. If the "
            "payment has a deadline, weigh each method's transfer time "
            "against the fee difference before deciding."
            if request.purpose.lower() in LOW_RISK_PURPOSES
            else (
                "For this purpose, documentation and compliance checks may "
                "apply. Keep supporting documents ready and confirm any "
                "limits with your provider before transferring."
            )
        )

        insights = [
            AdvisorInsight(
                title="Best Option",
                description=(
                    f"{rec.method} has the lowest estimated total cost "
                    f"({dest_symbol}{a.recipient.estimated_amount:,.2f} reaches the "
                    f"recipient). {rec.reason}"
                ),
            ),
            AdvisorInsight(
                title="Fee Impact",
                description=(
                    f"Total estimated fees are {symbol}{fees.total_fees:,.2f} "
                    f"({fee_pct:.1f}% of the amount) — FX markup "
                    f"{symbol}{fees.fx_markup:,.2f}, processing "
                    f"{symbol}{fees.processing_fee:,.2f}, other charges "
                    f"{symbol}{fees.other_charges:,.2f}."
                ),
            ),
            AdvisorInsight(
                title="Exchange Rate",
                description=(
                    f"The estimated rate is {a.exchange_rate} "
                    f"{request.destination_currency} per {request.source_currency}. "
                    f"Even a small rate shift changes the final recipient amount, "
                    f"so confirm the rate at payment time."
                ),
            ),
            AdvisorInsight(
                title="Method Comparison",
                description=(
                    f"Across {len(a.payment_methods)} available methods, choosing "
                    f"{rec.method} instead of the most expensive option saves "
                    f"about {symbol}{rec.potential_savings:,.2f}."
                ),
            ),
            AdvisorInsight(
                title=f"Purpose: {request.purpose.title()}",
                description=purpose_note,
            ),
        ]

        tips = [
            "Compare the final recipient amount before confirming payment.",
            "Check whether exchange rates change before completing the transfer.",
            "Review all fees — including hidden FX markup — before proceeding.",
            f"Keep receipts of the transaction for your {request.purpose} records.",
        ]
        if self._risk_level(request, fee_pct) != "low":
            tips.append(
                "For larger transfers, consider splitting the payment into "
                "smaller instalments to reduce timing and rate risk."
            )

        return AdvisorResponse(
            success=True,
            summary=summary,
            recommended_method=rec.method,
            potential_savings=rec.potential_savings,
            insights=insights,
            risk_level=self._risk_level(request, fee_pct),
            tips=tips,
            disclaimer=DISCLAIMER,
        )