"""Razorpay payment operations (TEST MODE only).

Endpoints:
  * POST /payments/create-order - create a Razorpay order and return safe data
  * POST /payments/verify       - verify the Razorpay checkout signature

The secret key never leaves the backend; only the public ``key_id`` is
returned to the frontend so it can open Razorpay Checkout.
"""

import logging
import uuid

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

# Currencies Razorpay accepts in test mode for this prototype.
SUPPORTED_CURRENCIES = {"INR"}


class CreateOrderRequest(BaseModel):
    """Incoming payload for POST /payments/create-order."""

    amount: float = Field(..., gt=0, description="Amount in major currency units, e.g. 1000 for ₹1000.")
    currency: str = Field("INR", description="Currency code, e.g. INR.")
    receipt: str = Field(..., min_length=1, description="Unique receipt id for the order.")


class CreateOrderResponse(BaseModel):
    """Safe order data returned to the frontend (never includes the secret)."""

    success: bool
    order_id: str
    amount: int  # smallest currency unit (paise for INR)
    currency: str
    key_id: str


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
async def create_order(request: CreateOrderRequest) -> CreateOrderResponse:
    """Create a Razorpay order and return only safe data to the frontend."""
    currency = request.currency.strip().upper()
    if currency not in SUPPORTED_CURRENCIES:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported currency '{currency}'. Supported: {sorted(SUPPORTED_CURRENCIES)}.",
        )
    if not request.receipt.strip():
        raise HTTPException(status_code=422, detail="A receipt id is required.")

    # Razorpay expects the amount in the smallest currency unit (paise for INR).
    amount_paise = int(round(request.amount * 100))
    if amount_paise <= 0:
        raise HTTPException(status_code=422, detail="Amount must be greater than 0.")

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
async def verify_payment(request: VerifyPaymentRequest) -> dict:
    """Verify the checkout signature using the official Razorpay SDK.

    On failure a safe HTTP error is returned; the payment is never
    falsely marked as successful.
    """
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

    return {"success": True, "message": "Payment verified successfully"}