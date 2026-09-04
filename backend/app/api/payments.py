"""API route handler for payment analysis.

Endpoints:
  * POST /api/v1/payments/analyze  - analyze a payment and persist the result
  * GET  /api/v1/payments/history  - list recent analyses
  * GET  /api/v1/payments/{id}    - retrieve a single analysis by ID

The route layer stays thin: it validates input via Pydantic schemas,
delegates calculation to :class:`PaymentAnalyzer`, optionally persists
the result via :class:`PaymentRepository`, and translates errors.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.database.connection import get_session
from app.models import User
from app.schemas.payment import (
    PaymentAnalysisDetailResponse,
    PaymentAnalysisRequest,
    PaymentAnalysisResponse,
    PaymentHistoryItem,
)
from app.services.payment_analyzer import PaymentAnalyzer
from app.services.payment_repository import PaymentRepository

logger = logging.getLogger(__name__)

router = APIRouter()

# A single shared instance - safe because the analyzer holds only
# immutable configuration and no request-scoped state.
_analyzer = PaymentAnalyzer()


@router.post(
    "/payments/analyze",
    response_model=PaymentAnalysisResponse,
    summary="Analyze an international payment",
    description=(
        "Receives an international payment request and returns a transparent "
        "cost breakdown, recipient amount, payment-method comparison, "
        "recommended option, and potential savings."
    ),
)
async def analyze_payment(
    request: PaymentAnalysisRequest,
    user: User = Depends(get_current_user),
    session: AsyncSession | None = Depends(get_session),
) -> PaymentAnalysisResponse:
    """Calculate an estimated cost breakdown for a cross-border payment.

    The calculation is performed inside :class:`PaymentAnalyzer`.  If a
    database session is available the result is persisted with the authenticated
    user's ID; database failures are logged but do **not** prevent the response
    from being returned.
    """
    try:
        result = _analyzer.analyze(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if session is not None:
        try:
            repo = PaymentRepository(session)
            db_record = await repo.save(result, user_id=user.id)
            result.id = db_record.id
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to persist payment analysis: %s", exc)

    return result


@router.get(
    "/payments/history",
    response_model=list[PaymentHistoryItem],
    summary="Get recent payment analyses",
    description=(
        "Returns up to ``limit`` recent payment analysis records for the "
        "authenticated user, ordered by creation date descending."
    ),
)
async def get_payment_history(
    limit: int = 10,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[PaymentHistoryItem]:
    """Return a list of recent payment analyses for the authenticated user."""
    if session is None:
        raise HTTPException(
            status_code=503, detail="Database is not configured."
        )
    repo = PaymentRepository(session)
    records = await repo.get_recent(limit=limit, user_id=user.id)
    return [PaymentRepository.to_history_item(r) for r in records]


@router.get(
    "/payments/{payment_id}",
    response_model=PaymentAnalysisDetailResponse,
    summary="Get a single payment analysis by ID",
    description=(
        "Returns the complete saved analysis including payment-method "
        "comparisons. Users can only access their own analyses."
    ),
)
async def get_payment_detail(
    payment_id: UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> PaymentAnalysisDetailResponse:
    """Retrieve a single payment analysis (only if owned by the authenticated user)."""
    if session is None:
        raise HTTPException(
            status_code=503, detail="Database is not configured."
        )
    repo = PaymentRepository(session)
    record = await repo.get_by_id(payment_id, user_id=user.id)
    if record is None:
        raise HTTPException(
            status_code=404,
            detail=f"Payment analysis with ID '{payment_id}' not found.",
        )
    return PaymentRepository.to_detail_response(record)