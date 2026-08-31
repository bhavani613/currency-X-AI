"""
Payment analysis service.

Contains all the **business logic** for calculating fees, exchange rates,
recipient amounts, and recommendations.  The FastAPI route layer stays thin
and simply delegates to :class:`PaymentAnalyzer`.

The configuration (exchange rates and fee models) is stored at module level
so it can be swapped out or loaded from a database / external API later
without touching the calculation code.
"""

from app.schemas.payment import (
    CostBreakdown,
    PaymentAnalysisRequest,
    PaymentAnalysisResponse,
    PaymentInfo,
    PaymentMethodComparison,
    RecipientInfo,
    Recommendation,
)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

#: Exchange rates expressed as *destination currency per 1 unit of source
#: currency*.  For this prototype the source currency is **INR**.
#: e.g. ``"GBP": 0.0088`` means 1 INR = 0.0088 GBP.
EXCHANGE_RATES: dict[str, float] = {
    "GBP": 0.0088,
    "USD": 0.0116,
    "AED": 0.044,
    "AUD": 0.018,
    "CAD": 0.0158,
}

#: Fee configuration for every supported payment method.
#:
#: ``fee_percentage`` is the **total** fee as a percentage of the source
#: amount.  The remaining keys break that total into meaningful sub-components
#: (FX markup, processing fee, other charges) so the response can be shown
#: transparently.  The three sub-percentages must sum to ``fee_percentage``.
PAYMENT_METHOD_CONFIG: dict[str, dict[str, float]] = {
    "Smart Payment": {
        "fee_percentage": 2.0,
        "fx_markup_percentage": 1.2,
        "processing_fee_percentage": 0.5,
        "other_charges_percentage": 0.3,
    },
    "Bank Transfer": {
        "fee_percentage": 3.2,
        "fx_markup_percentage": 2.0,
        "processing_fee_percentage": 0.7,
        "other_charges_percentage": 0.5,
    },
    "Debit Card": {
        "fee_percentage": 4.1,
        "fx_markup_percentage": 2.5,
        "processing_fee_percentage": 1.0,
        "other_charges_percentage": 0.6,
    },
    "Credit Card": {
        "fee_percentage": 5.0,
        "fx_markup_percentage": 3.0,
        "processing_fee_percentage": 1.2,
        "other_charges_percentage": 0.8,
    },
}

DISCLAIMER: str = (
    "Rates and fees shown are estimates based on prototype configuration "
    "and are not live provider quotes."
)


class PaymentAnalyzer:
    """Service that performs payment cost analysis and recommendations."""

    def __init__(
        self,
        exchange_rates: dict[str, float] | None = None,
        method_config: dict[str, dict[str, float]] | None = None,
    ) -> None:
        """Initialise the analyzer with optional custom configuration.

        Parameters
        ----------
        exchange_rates:
            Mapping of destination currency code to exchange rate.
            Defaults to :data:`EXCHANGE_RATES`.
        method_config:
            Mapping of payment method name to fee configuration.
            Defaults to :data:`PAYMENT_METHOD_CONFIG`.
        """
        self._exchange_rates: dict[str, float] = (
            exchange_rates if exchange_rates is not None else EXCHANGE_RATES
        )
        self._method_config: dict[str, dict[str, float]] = (
            method_config if method_config is not None else PAYMENT_METHOD_CONFIG
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_exchange_rate(self, destination_currency: str) -> float | None:
        """Return the configured exchange rate for *destination_currency*."""
        return self._exchange_rates.get(destination_currency)

    @staticmethod
    def _percent(amount: float, rate: float) -> float:
        """Return ``amount * rate / 100`` rounded to 2 decimal places."""
        return round(amount * rate / 100, 2)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(self, request: PaymentAnalysisRequest) -> PaymentAnalysisResponse:
        """Analyse a payment request and return a full cost breakdown.

        Raises
        ------
        ValueError
            If no exchange rate is configured for the requested destination
            currency.
        """
        amount: float = request.amount
        dest_currency: str = request.destination_currency

        exchange_rate = self._get_exchange_rate(dest_currency)
        if exchange_rate is None:
            raise ValueError(
                f"No exchange rate configured for destination currency "
                f"'{dest_currency}'. Supported currencies: "
                f"{sorted(self._exchange_rates.keys())}."
            )

        # --- Build a summary entry for every payment method ---------------
        method_summaries: list[dict[str, float | str]] = []
        for name, config in self._method_config.items():
            fee = self._percent(amount, config["fee_percentage"])
            method_summaries.append(
                {
                    "name": name,
                    "estimated_fee": fee,
                    "estimated_total": round(amount + fee, 2),
                    "config": config,
                }
            )

        # --- Dynamically pick the best and worst methods ------------------
        # Lowest estimated total cost wins; savings are measured against the
        # most expensive option.
        best: dict[str, float | str] = min(
            method_summaries, key=lambda m: m["estimated_total"]  # type: ignore[arg-type]
        )
        worst: dict[str, float | str] = max(
            method_summaries, key=lambda m: m["estimated_total"]  # type: ignore[arg-type]
        )
        potential_savings = round(
            worst["estimated_total"] - best["estimated_total"], 2  # type: ignore[operator]
        )

        # --- Detailed cost breakdown for the recommended method -----------
        best_config: dict[str, float] = best["config"]  # type: ignore[assignment]
        fx_markup = self._percent(amount, best_config["fx_markup_percentage"])
        processing_fee = self._percent(amount, best_config["processing_fee_percentage"])
        other_charges = self._percent(amount, best_config["other_charges_percentage"])

        # Guard against rounding drift — make the sum exact.
        total_fees = round(fx_markup + processing_fee + other_charges, 2)
        total_cost = round(amount + total_fees, 2)

        # --- Recipient amount (full source amount is converted) -----------
        recipient_amount = round(amount * exchange_rate, 2)

        # ------------------------------------------------------------------
        # Assemble the response using the Pydantic schemas
        # ------------------------------------------------------------------
        return PaymentAnalysisResponse(
            success=True,
            payment=PaymentInfo(
                amount=request.amount,
                source_currency=request.source_currency,
                destination_country=request.destination_country,
                destination_currency=request.destination_currency,
                purpose=request.purpose,
            ),
            exchange_rate=exchange_rate,
            cost_breakdown=CostBreakdown(
                fx_markup=fx_markup,
                processing_fee=processing_fee,
                other_charges=other_charges,
                total_fees=total_fees,
                total_cost=total_cost,
            ),
            recipient=RecipientInfo(
                currency=dest_currency,
                estimated_amount=recipient_amount,
            ),
            payment_methods=[
                PaymentMethodComparison(
                    name=str(m["name"]),
                    estimated_fee=m["estimated_fee"],  # type: ignore[arg-type]
                    estimated_total=m["estimated_total"],  # type: ignore[arg-type]
                )
                for m in method_summaries
            ],
            recommendation=Recommendation(
                method=str(best["name"]),
                potential_savings=potential_savings,
                reason=(
                    f"{best['name']} has the lowest estimated total cost "
                    f"among the configured payment methods."
                ),
            ),
            disclaimer=DISCLAIMER,
        )
