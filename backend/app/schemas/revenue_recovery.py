"""Pydantic schemas for the Revenue Recovery Agent (Phase 1)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

PaymentMethod = Literal[
    "Smart Payment", "Bank Transfer", "UPI", "Debit Card", "Credit Card"
]
AttemptStatus = Literal[
    "CREATED", "PENDING", "SUCCESS", "FAILED", "ABANDONED", "RECOVERY_RECOMMENDED"
]
RecommendationStatus = Literal["PENDING", "ACCEPTED", "DISMISSED", "EXECUTED"]


class PaymentAttemptCreate(BaseModel):
    """Request to record a payment attempt."""

    amount: float = Field(gt=0, description="Amount in the payment currency.")
    currency: str = Field(
        default="INR",
        min_length=3,
        max_length=3,
        pattern=r"^[A-Z]{3}$",
        description="ISO 4217 currency code.",
    )
    payment_method: PaymentMethod
    status: AttemptStatus = "CREATED"
    failure_code: str | None = None
    failure_message: str | None = None
    gateway_payment_id: str | None = None
    gateway_order_id: str | None = None


class PaymentAttemptResponse(BaseModel):
    id: str
    user_id: str
    amount: float
    currency: str
    payment_method: str
    status: str
    failure_code: str | None = None
    failure_message: str | None = None
    failure_category: str | None = None
    gateway_payment_id: str | None = None
    gateway_order_id: str | None = None
    created_at: datetime
    updated_at: datetime


class FailureAnalysisRequest(BaseModel):
    """Request to analyze a failed payment and generate a recommendation."""

    amount: float = Field(gt=0)
    currency: str = Field(default="INR", min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
    payment_method: PaymentMethod
    failure_code: str | None = Field(default=None, max_length=80)
    failure_message: str | None = Field(default=None, max_length=500)
    gateway_payment_id: str | None = None
    gateway_order_id: str | None = None


class FailureAnalysis(BaseModel):
    failure_category: str
    normalized_reason: str
    severity: Literal["LOW", "MEDIUM", "HIGH"]
    recommended_action: str
    suggested_retry_delay_hours: int | None = None
    alternative_payment_method: str | None = None
    recovery_probability: int = Field(ge=0, le=100)
    reasoning: str


class AnalyzeFailureResponse(BaseModel):
    success: bool
    payment_attempt_id: str
    recommendation_id: str
    analysis: FailureAnalysis
    # True when the failure event was already recorded (same gateway payment
    # reference) and the existing case was returned instead of a new one.
    duplicate: bool = False


class RecommendationItem(BaseModel):
    id: str
    payment_attempt_id: str
    amount: float
    currency: str
    payment_method: str
    attempt_status: str
    failure_category: str
    normalized_reason: str
    failure_message: str | None = None
    recovery_probability: int
    risk_level: str
    severity: str
    recommended_action: str
    alternative_payment_method: str | None = None
    retry_after: datetime | None = None
    reasoning: str
    status: str
    created_at: datetime


class RecommendationStatusUpdate(BaseModel):
    status: Literal["ACCEPTED", "DISMISSED", "EXECUTED"]


class RecoverySummary(BaseModel):
    failed_payments: int
    potential_recoverable_revenue: float
    recovered_revenue: float = 0
    recovered_cases: int = 0
    average_recovery_probability: int
    high_priority_recoveries: int
    total_cases: int = 0