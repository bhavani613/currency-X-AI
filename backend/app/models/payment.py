"""SQLAlchemy ORM models for payment analysis records.

All monetary fields use :class:`~decimal.Decimal` backed by PostgreSQL
``NUMERIC`` columns so that no floating-point precision is lost.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class PaymentAnalysis(Base):
    """Stores a single payment analysis and its calculated cost breakdown."""

    __tablename__ = "payment_analyses"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Link to the user who created this analysis (nullable for backward compat)
    user_id: Mapped[str | None] = mapped_column(
        PG_UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    source_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    destination_country: Mapped[str] = mapped_column(String(100), nullable=False)
    destination_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    purpose: Mapped[str] = mapped_column(String(100), nullable=False)
    exchange_rate: Mapped[Decimal] = mapped_column(Numeric(15, 6), nullable=False)
    fx_markup: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    processing_fee: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    other_charges: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    total_fees: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    total_cost: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    recipient_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    recommended_method: Mapped[str] = mapped_column(String(100), nullable=False)
    potential_savings: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # One-to-many: one analysis → many payment-method comparisons
    payment_methods: Mapped[list["PaymentMethodComparison"]] = relationship(
        back_populates="payment_analysis",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_payment_analyses_created_at_desc", text("created_at DESC")),
    )


class PaymentMethodComparison(Base):
    """Stores a single payment-method comparison row linked to an analysis."""

    __tablename__ = "payment_method_comparisons"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    payment_analysis_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("payment_analyses.id", ondelete="CASCADE"),
        nullable=False,
    )
    method_name: Mapped[str] = mapped_column(String(100), nullable=False)
    estimated_fee: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    estimated_total: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)

    payment_analysis: Mapped[PaymentAnalysis] = relationship(
        back_populates="payment_methods",
    )

    __table_args__ = (
        Index(
            "ix_payment_method_comparisons_analysis_id",
            "payment_analysis_id",
        ),
    )