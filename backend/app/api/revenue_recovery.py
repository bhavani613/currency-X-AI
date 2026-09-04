"""Revenue Recovery Agent API (Phase 1 — rule-based recovery intelligence).

Endpoints (all require JWT auth; users only see their own data):
  * POST   /recovery/payment-attempts   - record a payment attempt
  * POST   /recovery/analyze-failure    - analyze a failed attempt + persist recommendation
  * GET    /recovery/summary            - recovery overview for the user
  * GET    /recovery/cases              - list the user's recovery cases
  * GET    /recovery/cases/{case_id}    - fetch a case detail
  * POST   /recovery/cases/{case_id}/retry   - accept a recommendation (prepares a real
                                              retry via the existing checkout flow; never
                                              fakes a payment success)
  * POST   /recovery/cases/{case_id}/dismiss - dismiss a recommendation
  * GET    /recovery/recommendations    - alias for /recovery/cases
  * PATCH  /recovery/recommendations/{case_id}/status - update recommendation status
  * POST   /recovery/dev/demo-cases     - development-only seed helper (5 sample failures;
                                          disabled via RECOVERY_DEMO_ENABLED=false)

Phase 1 only generates recommendations — no retries, charges, or notifications.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.deps import get_current_user
from app.database.connection import get_session
from app.models import User
from app.schemas.revenue_recovery import (
    AnalyzeFailureResponse,
    FailureAnalysis,
    FailureAnalysisRequest,
    PaymentAttemptCreate,
    PaymentAttemptResponse,
    RecommendationItem,
    RecommendationStatusUpdate,
    RecoverySummary,
)
from app.services.revenue_recovery import RecoveryRepository, engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/recovery", tags=["revenue-recovery"])

DEMO_CASES: tuple[dict, ...] = (
    {"amount": 25000, "currency": "INR", "payment_method": "UPI", "failure_code": "INSUFFICIENT_FUNDS", "failure_message": "Insufficient balance in your account.", "status": "FAILED"},
    {"amount": 8500, "currency": "INR", "payment_method": "Credit Card", "failure_code": "CARD_DECLINED", "failure_message": "Your card was declined by the issuing bank.", "status": "FAILED"},
    {"amount": 50000, "currency": "INR", "payment_method": "Bank Transfer", "failure_code": "BANK_TIMEOUT", "failure_message": "Your bank did not respond in time.", "status": "FAILED"},
    {"amount": 2000, "currency": "INR", "payment_method": "Debit Card", "failure_code": "CARD_EXPIRED", "failure_message": "Your card has expired.", "status": "FAILED"},
    {"amount": 15000, "currency": "INR", "payment_method": "UPI", "failure_code": "PAYMENT_ABANDONED", "failure_message": "Checkout was abandoned before completion.", "status": "PAYMENT_ABANDONED"},
)


def _db_unavailable() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Database is unavailable. Please check the backend database configuration.",
    )


def _serialize_case(attempt) -> RecommendationItem:
    """Flatten an attempt + its recommendation into a case item."""
    rec = attempt.recommendation
    return RecommendationItem(
        id=rec.id if rec else attempt.id,
        payment_attempt_id=attempt.id,
        amount=float(attempt.amount or 0),
        currency=attempt.currency,
        payment_method=attempt.payment_method,
        attempt_status=attempt.status,
        failure_category=attempt.failure_category or "",
        normalized_reason=rec.normalized_reason if rec else "Payment could not be completed.",
        failure_message=attempt.failure_message,
        recovery_probability=rec.recovery_probability if rec else 0,
        risk_level=rec.risk_level if rec else "LOW",
        severity=rec.risk_level if rec else "LOW",
        recommended_action=rec.recommended_action if rec else "REVIEW_PAYMENT_DETAILS",
        alternative_payment_method=rec.alternative_payment_method if rec else None,
        retry_after=rec.retry_after if rec else None,
        reasoning=rec.reasoning if rec else "",
        status=rec.status if rec else "PENDING",
        created_at=attempt.created_at,
    )


def _attempt_response(attempt) -> PaymentAttemptResponse:
    return PaymentAttemptResponse(
        id=attempt.id,
        user_id=attempt.user_id,
        amount=float(attempt.amount or 0),
        currency=attempt.currency,
        payment_method=attempt.payment_method,
        status=attempt.status,
        failure_code=attempt.failure_code,
        failure_message=attempt.failure_message,
        failure_category=attempt.failure_category,
        gateway_payment_id=attempt.gateway_payment_id,
        gateway_order_id=attempt.gateway_order_id,
        created_at=attempt.created_at,
        updated_at=attempt.updated_at,
    )


def _analysis_from_attempt(attempt) -> FailureAnalysis:
    """Rebuild the FailureAnalysis payload from a persisted attempt+recommendation.

    Used by the idempotent failure-ingestion path so re-reporting the same
    gateway payment failure returns the original deterministic recommendation
    instead of creating a duplicate case.
    """
    rec = attempt.recommendation
    delay_hours = None
    if rec is not None and rec.retry_after is not None:
        try:
            delta_hours = (rec.retry_after - attempt.created_at).total_seconds() / 3600
            delay_hours = max(1, round(delta_hours))
        except (TypeError, ValueError, OSError):
            delay_hours = None
    return FailureAnalysis(
        failure_category=attempt.failure_category or "UNKNOWN",
        normalized_reason=rec.normalized_reason if rec else "Payment could not be completed.",
        severity=rec.risk_level if rec else "LOW",
        recommended_action=rec.recommended_action if rec else "REVIEW_PAYMENT_DETAILS",
        suggested_retry_delay_hours=delay_hours,
        alternative_payment_method=rec.alternative_payment_method if rec else None,
        recovery_probability=rec.recovery_probability if rec else 0,
        reasoning=rec.reasoning if rec else "",
    )


# ---------------------------------------------------------------------------
# Payment attempts
# ---------------------------------------------------------------------------


@router.post("/payment-attempts", response_model=PaymentAttemptResponse)
async def create_payment_attempt(
    payload: PaymentAttemptCreate,
    user: User = Depends(get_current_user),
    session: AsyncSession | None = Depends(get_session),
):
    """Record a payment attempt (created / pending / failed / abandoned)."""
    if session is None:
        raise _db_unavailable()
    repo = RecoveryRepository(session, user.id)
    attempt = await repo.create_attempt(payload)
    return _attempt_response(attempt)


@router.post("/analyze-failure", response_model=AnalyzeFailureResponse)
async def analyze_failure(
    payload: FailureAnalysisRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession | None = Depends(get_session),
):
    """Analyze a failed payment and persist the deterministic recommendation."""
    if session is None:
        raise _db_unavailable()

    repo = RecoveryRepository(session, user.id)

    # Idempotency — the same gateway payment failure (same provider reference)
    # must not create duplicate recovery cases. When the event was already
    # recorded for this user, return the existing deterministic analysis.
    if payload.gateway_payment_id:
        existing = await repo.get_attempt_by_gateway_payment_id(payload.gateway_payment_id)
        if existing is not None and existing.recommendation is not None:
            return AnalyzeFailureResponse(
                success=True,
                payment_attempt_id=existing.id,
                recommendation_id=existing.recommendation.id,
                analysis=_analysis_from_attempt(existing),
                duplicate=True,
            )

    analysis = engine.analyze_failure(
        failure_code=payload.failure_code,
        failure_message=payload.failure_message,
        payment_method=payload.payment_method,
        amount=payload.amount,
        currency=payload.currency,
    )

    repo = RecoveryRepository(session, user.id)
    attempt = await repo.create_attempt(
        PaymentAttemptCreate(
            amount=payload.amount,
            currency=payload.currency,
            payment_method=payload.payment_method,
            # Map the engine category back onto the attempt status.
            status=("PAYMENT_ABANDONED" if analysis["failure_category"] == "PAYMENT_ABANDONED" else "FAILED"),
            failure_code=payload.failure_code,
            failure_message=payload.failure_message,
            gateway_payment_id=payload.gateway_payment_id,
            gateway_order_id=payload.gateway_order_id,
        )
    )
    await repo.attach_recommendation(attempt.id, analysis)

    return AnalyzeFailureResponse(
        success=True,
        payment_attempt_id=attempt.id,
        recommendation_id=attempt.recommendation.id,
        analysis=FailureAnalysis(
            failure_category=analysis["failure_category"],
            normalized_reason=analysis["normalized_reason"],
            severity=analysis["severity"],
            recommended_action=analysis["recommended_action"],
            suggested_retry_delay_hours=analysis["suggested_retry_delay_hours"],
            alternative_payment_method=analysis["alternative_payment_method"],
            recovery_probability=analysis["recovery_probability"],
            reasoning=analysis["reasoning"],
        ),
    )


# ---------------------------------------------------------------------------
# Recovery cases
# ---------------------------------------------------------------------------


@router.get("/summary", response_model=RecoverySummary)
async def recovery_summary(
    user: User = Depends(get_current_user),
    session: AsyncSession | None = Depends(get_session),
):
    """Recovery overview for the current user (runs stale-pending detection first)."""
    if session is None:
        raise _db_unavailable()
    repo = RecoveryRepository(session, user.id)
    summary = await repo.get_summary()
    return RecoverySummary(**summary)


@router.get("/cases", response_model=list[RecommendationItem])
async def list_recovery_cases(
    attempt_status: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    session: AsyncSession | None = Depends(get_session),
):
    """List the current user's recovery cases (newest first)."""
    if session is None:
        raise _db_unavailable()
    repo = RecoveryRepository(session, user.id)
    await repo.detect_abandoned()
    attempts = await repo.get_cases(status=attempt_status, limit=limit, offset=offset)
    return [_serialize_case(a) for a in attempts if a.recommendation is not None]


@router.get("/cases/{case_id}", response_model=RecommendationItem)
async def get_recovery_case(
    case_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession | None = Depends(get_session),
):
    """Fetch a single recovery case. 404 when it does not exist or is not owned by the user."""
    if session is None:
        raise _db_unavailable()
    repo = RecoveryRepository(session, user.id)
    attempt = await repo.get_case(case_id)
    if attempt is None or attempt.recommendation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recovery case not found.")
    return _serialize_case(attempt)


@router.post("/cases/{case_id}/retry")
async def retry_recovery_case(
    case_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession | None = Depends(get_session),
):
    """Accept the recommendation and prepare a REAL retry via the existing checkout flow.

    This never fakes a payment success — it only flips the recommendation to ACCEPTED
    and returns the original payment details so the frontend can restart the normal
    Analyze -> Checkout -> Razorpay flow. The returned ``case_id`` should be stored
    by the frontend and passed to ``/cases/{case_id}/complete`` after verified
    payment success so the recovery can be marked as recovered.
    """
    if session is None:
        raise _db_unavailable()
    repo = RecoveryRepository(session, user.id)
    attempt = await repo.get_case(case_id)
    if attempt is None or attempt.recommendation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recovery case not found.")
    try:
        rec = await repo.update_recommendation_status(case_id, "ACCEPTED")
    except ValueError as exc:
        # DISMISSED/EXECUTED cases cannot be retried (strict state machine).
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return {
        "success": True,
        "case_id": case_id,
        "payment_attempt_id": attempt.id,
        "recommendation_id": attempt.recommendation.id,
        "message": "Recommendation accepted. Restart the payment through the normal checkout flow.",
        "recommendation_status": rec.status if rec else "ACCEPTED",
        "retry_payment": {
            "amount": float(attempt.amount or 0),
            "currency": attempt.currency,
            "payment_method": attempt.payment_method,
            "suggested_method": attempt.recommendation.alternative_payment_method,
        },
    }


@router.post("/cases/{case_id}/dismiss")
async def dismiss_recovery_case(
    case_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession | None = Depends(get_session),
):
    """Dismiss a recovery recommendation (no payment side effects)."""
    if session is None:
        raise _db_unavailable()
    repo = RecoveryRepository(session, user.id)
    attempt = await repo.get_case(case_id)
    if attempt is None or attempt.recommendation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recovery case not found.")
    try:
        rec = await repo.update_recommendation_status(case_id, "DISMISSED")
    except ValueError as exc:
        # EXECUTED cases are terminal and cannot be dismissed afterwards.
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return {"success": True, "message": "Recommendation dismissed.", "recommendation_status": rec.status if rec else "DISMISSED"}


@router.post("/cases/{case_id}/complete")
async def complete_recovery_case(
    case_id: str,
    body: dict | None = None,
    user: User = Depends(get_current_user),
    session: AsyncSession | None = Depends(get_session),
):
    """Mark a recovery case as successfully recovered after verified payment.

    Call this endpoint from the frontend ONLY after the retried payment has
    been successfully verified through the existing Razorpay/demo verification
    flow. The ``recovered_amount`` (optional) should be the actual payment
    amount in the payment currency. Idempotent: calling this multiple times
    for the same case will not double-count the recovered revenue.
    """
    if session is None:
        raise _db_unavailable()

    # Validate case_id format
    try:
        from uuid import UUID
        UUID(case_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid case ID format.")

    repo = RecoveryRepository(session, user.id)
    attempt = await repo.get_case(case_id)
    if attempt is None or attempt.recommendation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recovery case not found.")

    # Validate the current status allows recovery
    if attempt.recommendation.status == "DISMISSED":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot recover a dismissed recommendation.",
        )
    if attempt.recommendation.status == "EXECUTED":
        # Idempotent: already recovered
        return {
            "success": True,
            "message": "Recovery was already marked as recovered.",
            "recommendation_status": "EXECUTED",
            "case_id": case_id,
            "already_recovered": True,
        }

    # Extract optional recovered_amount from body
    recovered_amount = None
    if body and isinstance(body, dict):
        recovered_amount = body.get("recovered_amount")
        if recovered_amount is not None:
            try:
                recovered_amount = float(recovered_amount)
                if recovered_amount <= 0:
                    recovered_amount = None
            except (TypeError, ValueError):
                recovered_amount = None

    rec = await repo.mark_recovered(case_id, recovered_amount=recovered_amount)
    if rec is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unable to mark recovery as recovered. The case may have been dismissed.",
        )

    return {
        "success": True,
        "message": "Recovery marked as successfully recovered.",
        "recommendation_status": "EXECUTED",
        "case_id": case_id,
        "payment_attempt_id": attempt.id,
        "recovered_amount": float(recovered_amount or attempt.amount or 0),
    }


# ---------------------------------------------------------------------------
# Recommendation aliases + status updates
# ---------------------------------------------------------------------------


@router.get("/recommendations", response_model=list[RecommendationItem])
async def list_recommendations(
    attempt_status: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    session: AsyncSession | None = Depends(get_session),
):
    """Alias for GET /recovery/cases."""
    return await list_recovery_cases(
        attempt_status=attempt_status, limit=limit, offset=offset, user=user, session=session
    )


@router.patch("/recommendations/{case_id}/status")
async def update_recommendation_status(
    case_id: str,
    payload: RecommendationStatusUpdate,
    user: User = Depends(get_current_user),
    session: AsyncSession | None = Depends(get_session),
):
    """Update a recommendation status (ACCEPTED / DISMISSED / EXECUTED).

    Enforces the strict state machine:
      PENDING -> ACCEPTED | DISMISSED;  ACCEPTED -> EXECUTED | DISMISSED.
    DISMISSED and EXECUTED are terminal. Invalid transitions return 409.
    """
    if session is None:
        raise _db_unavailable()
    repo = RecoveryRepository(session, user.id)
    attempt = await repo.get_case(case_id)
    if attempt is None or attempt.recommendation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recovery case not found.")
    try:
        rec = await repo.update_recommendation_status(case_id, payload.status)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return {"success": True, "recommendation_status": rec.status if rec else payload.status}


# ---------------------------------------------------------------------------
# Development-only demo seeding
# ---------------------------------------------------------------------------


@router.post("/dev/demo-cases")
async def create_demo_cases(
    user: User = Depends(get_current_user),
    session: AsyncSession | None = Depends(get_session),
):
    """DEV ONLY: seed the 5 sample failed payments (disabled in production).

    Each demo failure runs through the real engine, so recommendations are the
    genuine deterministic results — no hard-coded analysis output.
    """
    if not settings.RECOVERY_DEMO_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo seeding is disabled (RECOVERY_DEMO_ENABLED=false).",
        )
    if session is None:
        raise _db_unavailable()

    repo = RecoveryRepository(session, user.id)
    created: list[RecommendationItem] = []
    for demo in DEMO_CASES:
        analysis = engine.analyze_failure(
            failure_code=demo["failure_code"],
            failure_message=demo["failure_message"],
            payment_method=demo["payment_method"],
            amount=demo["amount"],
            currency=demo["currency"],
        )
        attempt = await repo.create_attempt(
            PaymentAttemptCreate(
                amount=demo["amount"],
                currency=demo["currency"],
                payment_method=demo["payment_method"],
                status=demo["status"],
                failure_code=demo["failure_code"],
                failure_message=demo["failure_message"],
            )
        )
        await repo.attach_recommendation(attempt.id, analysis)
        await session.refresh(attempt)
        created.append(_serialize_case(attempt))

    return {"success": True, "created": len(created), "cases": created}