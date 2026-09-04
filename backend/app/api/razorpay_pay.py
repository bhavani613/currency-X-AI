"""Razorpay payment operations (TEST MODE only).

Endpoints:
  * POST /payments/create-order - create a Razorpay order and return safe data
  * POST /payments/verify       - verify the Razorpay checkout signature

The secret key never leaves the backend; only the public ``key_id`` is
returned to the frontend so it can open Razorpay Checkout.
"""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.deps import get_optional_user
from app.database.connection import get_session
from app.models import User, PaymentOrder
from app.core.deps import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(
    dependencies=[Depends(get_current_user)],
)

# Currencies Razorpay accepts in test mode for this prototype.
SUPPORTED_CURRENCIES = {"INR"}


class CreateOrderRequest(BaseModel):
    """Incoming payload for POST /payments/create-order."""

    amount: float = Field(..., gt=0, description="Amount in major currency units, e.g. 1000 for ₹1000.")
    currency: str = Field("INR", description="Currency code, e.g. INR.")
    receipt: str = Field(..., min_length=1, description="Unique receipt id for the order.")
    payment_method: str = Field(
        "Smart Payment", max_length=50, description="User-selected payment method (tracking only)."
    )
    # Optional: link this order to a recovery case for retry flow
    recovery_case_id: str | None = Field(
        None, description="Recovery case ID if this order is a retry for a failed payment."
    )


class CreateOrderResponse(BaseModel):
    """Safe order data returned to the frontend (never includes the secret)."""

    success: bool
    order_id: str
    amount: int  # smallest currency unit (paise for INR)
    currency: str
    key_id: str
    # When True, this is a simulated DEMO order (no real Razorpay checkout).
    demo: bool = False


class VerifyPaymentRequest(BaseModel):
    """Incoming payload for POST /payments/verify (Razorpay handler response)."""

    razorpay_payment_id: str = Field(..., min_length=1)
    razorpay_order_id: str = Field(..., min_length=1)
    razorpay_signature: str = Field(..., min_length=1)


def _get_client():
    """Return a Razorpay client, or raise a safe HTTP error if unusable."""
    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        raise HTTPException(
            status_code=503,
            detail=(
                "Razorpay is not configured on the server. "
                "Please set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET."
            ),
        )
    try:
        import razorpay
    except ImportError as exc:
        logger.error("razorpay SDK not installed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="Payment service is unavailable. Razorpay SDK is not installed.",
        ) from exc
    return razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )


@router.post(
    "/payments/create-order",
    response_model=CreateOrderResponse,
    summary="Create a Razorpay order (TEST MODE)",
)
async def create_order(
    request: CreateOrderRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession | None = Depends(get_session),
) -> CreateOrderResponse:
    """Create a Razorpay order and return only safe data to the frontend.
    
    When a recovery_case_id is provided, the order is linked to that recovery
    case so that successful verification can mark the case as recovered.
    """
    currency = request.currency.strip().upper()
    if currency not in SUPPORTED_CURRENCIES:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported currency '{currency}'. Supported: {sorted(SUPPORTED_CURRENCIES)}.",
        )
    if not request.receipt.strip():
        raise HTTPException(status_code=422, detail="A receipt id is required.")
    if session is None:
        raise HTTPException(
            status_code=503, detail="Database is not configured."
        )

    # Razorpay expects the amount in the smallest currency unit (paise for INR).
    amount_paise = int(round(request.amount * 100))
    if amount_paise <= 0:
        raise HTTPException(status_code=422, detail="Amount must be greater than 0.")

    # Validate recovery case if provided (must belong to authenticated user)
    if request.recovery_case_id:
        from app.services.revenue_recovery import RecoveryRepository
        repo = RecoveryRepository(session, user.id)
        case = await repo.get_case(request.recovery_case_id)
        if case is None:
            raise HTTPException(
                status_code=404,
                detail="Recovery case not found or does not belong to you.",
            )

    # --- DEMO MODE ------------------------------------------------------
    # When RAZORPAY_DEMO_MODE=true we return a clearly-identifiable simulated
    # order (demo_order_*) instead of calling the real Razorpay API. No keys
    # are required and no money ever moves.
    if settings.RAZORPAY_DEMO_MODE:
        demo_order_id = f"demo_order_{uuid.uuid4().hex[:12]}"
        # Store the demo order in the database for later verification
        order = PaymentOrder(
            order_id=demo_order_id,
            user_id=user.id,
            amount=amount_paise,
            currency=currency,
            is_demo=True,
            recovery_recommendation_id=request.recovery_case_id,
        )
        session.add(order)
        await session.commit()
        return CreateOrderResponse(
            success=True,
            order_id=demo_order_id,
            amount=amount_paise,
            currency=currency,
            key_id="demo",  # public placeholder — never used to open real checkout
            demo=True,
        )

    client = _get_client()
    receipt = request.receipt.strip() or f"currencyx-{uuid.uuid4().hex[:10]}"
    try:
        order = client.order.create(
            {
                "amount": amount_paise,
                "currency": currency,
                "receipt": receipt,
            }
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Razorpay order creation failed: %s", exc)
        raise HTTPException(
            status_code=502,
            detail="Failed to create payment order with Razorpay. Please try again.",
        ) from exc

    # Store the real order in the database for later verification
    db_order = PaymentOrder(
        order_id=order["id"],
        user_id=user.id,
        amount=order["amount"],
        currency=order["currency"],
        is_demo=False,
        recovery_recommendation_id=request.recovery_case_id,
    )
    session.add(db_order)
    await session.commit()

    return CreateOrderResponse(
        success=True,
        order_id=order["id"],
        amount=order["amount"],
        currency=order["currency"],
        key_id=settings.RAZORPAY_KEY_ID,  # public key only — safe to expose
    )


@router.post(
    "/payments/verify",
    summary="Verify a Razorpay payment signature",
)
async def verify_payment(
    request: VerifyPaymentRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession | None = Depends(get_session),
) -> dict:
    """Verify the checkout signature using the official Razorpay SDK.
    
    In DEMO MODE, simulated payments (order id ``demo_order_*`` and payment
    id ``demo_payment_*``) are accepted as verified ONLY if the order was
    created by this backend for the authenticated user. This prevents
    arbitrary fake demo IDs from being accepted as proof of payment.
    
    When the verified order is linked to a recovery case, the case is
    marked as EXECUTED server-side (idempotently).
    
    Real TEST MODE verification is untouched and only used when keys exist.
    """
    if session is None:
        raise HTTPException(
            status_code=503, detail="Database is not configured."
        )

    is_demo = request.razorpay_order_id.startswith("demo_order_")

    if is_demo:
        # Verify the demo order exists and belongs to the authenticated user
        result = await session.execute(
            select(PaymentOrder).where(
                PaymentOrder.order_id == request.razorpay_order_id,
                PaymentOrder.user_id == user.id,
                PaymentOrder.is_demo == True,
            )
        )
        order = result.scalar_one_or_none()
        if order is None:
            raise HTTPException(
                status_code=400,
                detail="Demo order not found. Only orders created by this backend can be verified.",
            )
        if not request.razorpay_payment_id.startswith("demo_payment_"):
            raise HTTPException(
                status_code=400,
                detail="Invalid demo payment ID format.",
            )
    else:
        # Real Razorpay verification
        client = _get_client()
        try:
            client.utility.verify_payment_signature(
                {
                    "razorpay_payment_id": request.razorpay_payment_id,
                    "razorpay_order_id": request.razorpay_order_id,
                    "razorpay_signature": request.razorpay_signature,
                }
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Razorpay signature verification failed: %s", exc)
            raise HTTPException(
                status_code=400,
                detail="Payment verification failed. The payment signature is invalid.",
            ) from exc

        # Look up the order to check for recovery linkage
        result = await session.execute(
            select(PaymentOrder).where(
                PaymentOrder.order_id == request.razorpay_order_id,
                PaymentOrder.user_id == user.id,
            )
        )
        order = result.scalar_one_or_none()

    # Mark the order as verified
    if order is not None and not order.verified:
        order.verified = True
        order.payment_id = request.razorpay_payment_id
        from datetime import datetime, timezone
        order.verified_at = datetime.now(timezone.utc)
        await session.commit()

    # If the order is linked to a recovery case, mark it as EXECUTED
    recovery_updated = False
    if order is not None and order.recovery_recommendation_id:
        from app.services.revenue_recovery import RecoveryRepository
        repo = RecoveryRepository(session, user.id)
        rec = await repo.mark_recovered(order.recovery_recommendation_id, recovered_amount=order.amount / 100)
        if rec is not None:
            recovery_updated = True
            await session.commit()

    response = {
        "success": True,
        "message": "Payment verified successfully",
        "demo": is_demo,
        "recovery_updated": recovery_updated,
    }
    return response