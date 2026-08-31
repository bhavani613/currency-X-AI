"""Database persistence layer for payment analyses.

Converts between Pydantic response schemas and SQLAlchemy ORM models,
keeping database logic separate from business logic.
"""

import logging
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.payment import PaymentAnalysis, PaymentMethodComparison
from app.schemas.payment import (
    CostBreakdown,
    PaymentAnalysisDetailResponse,
    PaymentAnalysisResponse,
    PaymentHistoryItem,
    PaymentInfo,
    PaymentMethodComparisonDetail,
    Recommendation,
    RecipientInfo,
)
from app.services.payment_analyzer import DISCLAIMER

logger = logging.getLogger(__name__)


def _to_decimal(value: float | Decimal) -> Decimal:
    """Convert a float or Decimal to Decimal for database storage."""
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


class PaymentRepository:
    """Handles persistence and retrieval of payment analysis data."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, response: PaymentAnalysisResponse) -> PaymentAnalysis:
        """Persist a PaymentAnalysisResponse and return the saved model."""
        db = PaymentAnalysis(
            amount=_to_decimal(response.payment.amount),
            source_currency=response.payment.source_currency,
            destination_country=response.payment.destination_country,
            destination_currency=response.payment.destination_currency,
            purpose=response.payment.purpose,
            exchange_rate=_to_decimal(response.exchange_rate),
            fx_markup=_to_decimal(response.cost_breakdown.fx_markup),
            processing_fee=_to_decimal(response.cost_breakdown.processing_fee),
            other_charges=_to_decimal(response.cost_breakdown.other_charges),
            total_fees=_to_decimal(response.cost_breakdown.total_fees),
            total_cost=_to_decimal(response.cost_breakdown.total_cost),
            recipient_amount=_to_decimal(response.recipient.estimated_amount),
            recommended_method=response.recommendation.method,
            potential_savings=_to_decimal(response.recommendation.potential_savings),
        )

        for m in response.payment_methods:
            db.payment_methods.append(
                PaymentMethodComparison(
                    method_name=m.name,
                    estimated_fee=_to_decimal(m.estimated_fee),
                    estimated_total=_to_decimal(m.estimated_total),
                )
            )

        self._session.add(db)
        await self._session.commit()
        await self._session.refresh(db)
        return db

    # -- Read ---------------------------------------------------------------

    async def get_by_id(self, payment_id: UUID) -> PaymentAnalysis | None:
        """Retrieve a single analysis by ID, including its payment methods."""
        result = await self._session.execute(
            select(PaymentAnalysis)
            .where(PaymentAnalysis.id == payment_id)
            .options(selectinload(PaymentAnalysis.payment_methods))
        )
        return result.scalar_one_or_none()

    async def get_recent(self, limit: int = 10) -> list[PaymentAnalysis]:
        """Retrieve the most recent analyses ordered by creation date."""
        result = await self._session.execute(
            select(PaymentAnalysis)
            .order_by(PaymentAnalysis.created_at.desc())
            .limit(limit)
            .options(selectinload(PaymentAnalysis.payment_methods))
        )
        return list(result.scalars().all())

    # -- Serialization -------------------------------------------------------

    @staticmethod
    def to_detail_response(
        analysis: PaymentAnalysis,
    ) -> PaymentAnalysisDetailResponse:
        """Convert a model instance to a detail response schema."""
        return PaymentAnalysisDetailResponse(
            id=analysis.id,
            success=True,
            payment=PaymentInfo(
                amount=float(analysis.amount),
                source_currency=analysis.source_currency,
                destination_country=analysis.destination_country,
                destination_currency=analysis.destination_currency,
                purpose=analysis.purpose,
            ),
            exchange_rate=float(analysis.exchange_rate),
            cost_breakdown=CostBreakdown(
                fx_markup=float(analysis.fx_markup),
                processing_fee=float(analysis.processing_fee),
                other_charges=float(analysis.other_charges),
                total_fees=float(analysis.total_fees),
                total_cost=float(analysis.total_cost),
            ),
            recipient=RecipientInfo(
                currency=analysis.destination_currency,
                estimated_amount=float(analysis.recipient_amount),
            ),
            payment_methods=[
                PaymentMethodComparisonDetail(
                    id=m.id,
                    method_name=m.method_name,
                    estimated_fee=float(m.estimated_fee),
                    estimated_total=float(m.estimated_total),
                )
                for m in analysis.payment_methods
            ],
            recommendation=Recommendation(
                method=analysis.recommended_method,
                potential_savings=float(analysis.potential_savings),
                reason=(
                    f"{analysis.recommended_method} has the lowest estimated "
                    f"total cost among the configured payment methods."
                ),
            ),
            disclaimer=DISCLAIMER,
            created_at=analysis.created_at,
        )

    @staticmethod
    def to_history_item(analysis: PaymentAnalysis) -> PaymentHistoryItem:
        """Convert a model instance to a history list item."""
        return PaymentHistoryItem(
            id=analysis.id,
            amount=float(analysis.amount),
            source_currency=analysis.source_currency,
            destination_currency=analysis.destination_currency,
            destination_country=analysis.destination_country,
            purpose=analysis.purpose,
            total_cost=float(analysis.total_cost),
            recipient_amount=float(analysis.recipient_amount),
            recommended_method=analysis.recommended_method,
            potential_savings=float(analysis.potential_savings),
            created_at=analysis.created_at,
        )