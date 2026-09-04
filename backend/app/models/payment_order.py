"""SQLAlchemy ORM model for tracking payment orders and their linkage to recovery cases.

This model stores demo orders created by the backend so that:
1. Demo orders can be verified as created by this backend for this user
2. Recovery cases can be linked to verified payments server-side
3. Arbitrary fake demo_order_* IDs are rejected
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class PaymentOrder(Base):
    """Tracks orders created by the backend for payment verification.
    
    This enables server-side verification that a payment was genuinely
    created by this backend for the authenticated user, preventing
    arbitrary fake demo IDs from being accepted as proof of payment.
    """

    __tablename__ = "payment_orders"

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        default=lambda: str(uuid.uuid4()),
    )
    # The order ID returned to the frontend (demo_order_* or real Razorpay order ID)
    order_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    # The user who created this order
    user_id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Amount in paise (Razorpay format)
    amount: Mapped[int] = mapped_column(nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    # Whether this is a demo order (no real payment)
    is_demo: Mapped[bool] = mapped_column(default=False, nullable=False)
    # Optional: link to a recovery case that this order is retrying
    recovery_recommendation_id: Mapped[str | None] = mapped_column(
        PG_UUID(as_uuid=False),
        ForeignKey("recovery_recommendations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Whether this order has been verified (payment completed)
    verified: Mapped[bool] = mapped_column(default=False, nullable=False)
    # Payment ID from Razorpay (or demo_payment_* for demo orders)
    payment_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)