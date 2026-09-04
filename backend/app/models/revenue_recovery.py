"""SQLAlchemy ORM models for the Revenue Recovery Agent (Phase 1).

A :class:`PaymentAttempt` records an attempted payment (successful or
failed).  When an attempt fails, the recovery engine produces a
:class:`RecoveryRecommendation` describing WHY it failed and WHAT to do.

No sensitive payment credentials (card numbers, UPI PINs, OTPs, bank
passwords) are ever stored on these models.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class PaymentAttempt(Base):
    """A single payment attempt made by a user."""

    __tablename__ = "payment_attempts"

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        default=lambda: str(uuid.uuid4()),
    )
    user_id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    amount: Mapped[float] = mapped_column(Numeric(15, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    payment_method: Mapped[str] = mapped_column(String(50), nullable=False)
    # CREATED | PENDING | SUCCESS | FAILED | ABANDONED | RECOVERY_RECOMMENDED
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="CREATED")
    failure_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    failure_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    failure_category: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    gateway_payment_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    gateway_order_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    recommendation: Mapped["RecoveryRecommendation | None"] = relationship(
        back_populates="payment_attempt",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_payment_attempts_user_created", "user_id", "created_at"),
        Index("ix_payment_attempts_status", "status"),
    )


class RecoveryRecommendation(Base):
    """Engine-generated recovery guidance for a failed payment attempt."""

    __tablename__ = "recovery_recommendations"

    id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        default=lambda: str(uuid.uuid4()),
    )
    payment_attempt_id: Mapped[str] = mapped_column(
        PG_UUID(as_uuid=False),
        ForeignKey("payment_attempts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    recommended_action: Mapped[str] = mapped_column(String(60), nullable=False)
    normalized_reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    alternative_payment_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    retry_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    recovery_probability: Mapped[int] = mapped_column(nullable=False)
    risk_level: Mapped[str] = mapped_column(String(10), nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    # PENDING | ACCEPTED | DISMISSED | EXECUTED
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    payment_attempt: Mapped[PaymentAttempt] = relationship(
        back_populates="recommendation",
    )

    __table_args__ = (
        Index("ix_recovery_recommendations_status", "status"),
    )