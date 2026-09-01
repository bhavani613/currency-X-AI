from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request schema
# ---------------------------------------------------------------------------

class PaymentAnalysisRequest(BaseModel):
    """Incoming payload for the payment analysis endpoint."""

    amount: float = Field(
        ...,
        gt=0,
        description="Amount to send in the source currency (must be > 0).",
    )
    source_currency: str = Field(
        ...,
        min_length=3,
        max_length=3,
        pattern=r"^[A-Z]{3}$",
        description="3-letter ISO 4217 source currency code, e.g. INR.",
    )
    destination_country: str = Field(
        ...,
        min_length=1,
        description="Name of the destination country, e.g. 'United Kingdom'.",
    )
    destination_currency: str = Field(
        ...,
        min_length=3,
        max_length=3,
        pattern=r"^[A-Z]{3}$",
        description="3-letter ISO 4217 destination currency code, e.g. GBP.",
    )
    purpose: str = Field(
        ...,
        min_length=1,
        description="Purpose of the international payment, e.g. 'education'.",
    )


# ---------------------------------------------------------------------------
# Response schema components
# ---------------------------------------------------------------------------

class PaymentInfo(BaseModel):
    """Echoes back the payment details from the original request."""

    amount: float
    source_currency: str
    destination_country: str
    destination_currency: str
    purpose: str


class CostBreakdown(BaseModel):
    """Detailed cost breakdown for the recommended payment method."""

    fx_markup: float
    processing_fee: float
    other_charges: float
    total_fees: float
    total_cost: float


class RecipientInfo(BaseModel):
    """Estimated amount the recipient will receive."""

    currency: str
    estimated_amount: float


class PaymentMethodComparison(BaseModel):
    """Comparison entry for a single payment method."""

    name: str
    estimated_fee: float
    estimated_total: float


class Recommendation(BaseModel):
    """Recommended payment method and potential savings."""

    method: str
    potential_savings: float
    reason: str


class PaymentAnalysisResponse(BaseModel):
    """Full response schema for the payment analysis endpoint."""

    id: UUID | None = None
    success: bool
    payment: PaymentInfo
    exchange_rate: float
    cost_breakdown: CostBreakdown
    recipient: RecipientInfo
    payment_methods: list[PaymentMethodComparison]
    recommendation: Recommendation
    #: Prototype convenience fields: the source amount and the recommended
    #: total cost expressed in INR (Razorpay checkout settles in INR).
    amount_in_inr: float | None = None
    total_cost_in_inr: float | None = None
    disclaimer: str


# ---------------------------------------------------------------------------
# History / detail response schemas (with persisted fields)
# ---------------------------------------------------------------------------

class PaymentMethodComparisonDetail(BaseModel):
    """Payment-method comparison row as stored, with its generated ID."""

    id: UUID
    method_name: str
    estimated_fee: float
    estimated_total: float


class PaymentHistoryItem(BaseModel):
    """Compact summary of an analysis for the listing endpoint."""

    id: UUID
    amount: float
    source_currency: str
    destination_currency: str
    destination_country: str
    purpose: str
    total_cost: float
    recipient_amount: float
    recommended_method: str
    potential_savings: float
    created_at: datetime


class PaymentAnalysisDetailResponse(BaseModel):
    """Full detail of a persisted analysis (includes DB-generated fields)."""

    id: UUID
    success: bool
    payment: PaymentInfo
    exchange_rate: float
    cost_breakdown: CostBreakdown
    recipient: RecipientInfo
    payment_methods: list[PaymentMethodComparisonDetail]
    recommendation: Recommendation
    disclaimer: str
    created_at: datetime