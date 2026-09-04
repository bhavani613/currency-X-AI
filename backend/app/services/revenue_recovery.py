"""Revenue Recovery intelligence engine (Phase 1 — deterministic rules).

A modular failure-categorization + recommendation engine built on
deterministic business rules so results are consistent and demoable.
The :class:`RevenueRecoveryEngine` abstraction is intentionally narrow so a
future LLM-based agent, Razorpay webhook events, or behavioural history can
replace/extend the rule layer without touching the API or models.

Phase 1 only GENERATES recommendations — nothing is retried, charged, or
sent to customers.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.revenue_recovery import PaymentAttempt, RecoveryRecommendation
from app.services.payment_analyzer import PAYMENT_METHOD_CONFIG


@dataclass(frozen=True)
class CategoryRule:
    category: str
    normalized_reason: str
    severity: str
    recommended_action: str
    retry_delay_hours: int | None
    alternative_method: str | None
    recovery_probability: int
    reasoning: str
    keywords: tuple[str, ...]
    codes: tuple[str, ...]


RULES: tuple[CategoryRule, ...] = (
    CategoryRule(
        category="INSUFFICIENT_FUNDS",
        normalized_reason="Payment could not be completed because of insufficient balance.",
        severity="MEDIUM",
        recommended_action="RETRY_LATER",
        retry_delay_hours=24,
        alternative_method="UPI",
        recovery_probability=82,
        reasoning=(
            "The payment failed due to insufficient funds. Immediate retries may "
            "fail again. A delayed retry gives the customer time to add funds, "
            "which historically recovers most of these payments."
        ),
        keywords=("insufficient", "no funds", "low balance", "nsf", "balance"),
        codes=("INSUFFICIENT_FUNDS", "NSF", "NO_FUNDS", "LOW_BALANCE"),
    ),
    CategoryRule(
        category="CARD_DECLINED",
        normalized_reason="The customer's card was declined by the issuing bank.",
        severity="HIGH",
        recommended_action="REQUEST_ALTERNATIVE_PAYMENT_METHOD",
        retry_delay_hours=None,
        alternative_method="UPI",
        recovery_probability=62,
        reasoning=(
            "The issuing bank declined the card. Retrying the same card usually "
            "fails, so offering an alternative method such as UPI recovers more "
            "revenue."
        ),
        keywords=("declined", "do not honor", "do_not_honor", "blocked"),
        codes=("CARD_DECLINED", "DECLINED", "DO_NOT_HONOR", "ISSUER_DECLINED"),
    ),
    CategoryRule(
        category="CARD_EXPIRED",
        normalized_reason="The card used has expired and cannot be charged.",
        severity="MEDIUM",
        recommended_action="REQUEST_ALTERNATIVE_PAYMENT_METHOD",
        retry_delay_hours=None,
        alternative_method="UPI",
        recovery_probability=68,
        reasoning=(
            "The card has expired, so the same card can never succeed. Asking "
            "the customer for a different method (e.g. UPI) is the fastest path "
            "to recovery."
        ),
        keywords=("expired",),
        codes=("CARD_EXPIRED", "EXPIRED_CARD"),
    ),
    CategoryRule(
        category="UPI_FAILURE",
        normalized_reason="The UPI collect request failed before completion.",
        severity="MEDIUM",
        recommended_action="RETRY_SOON",
        retry_delay_hours=1,
        alternative_method="Bank Transfer",
        recovery_probability=72,
        reasoning=(
            "UPI failures are often transient (app/server issues at the bank). "
            "A short-delay retry frequently succeeds; fall back to another "
            "method if the retry fails."
        ),
        keywords=("upi", "vpa"),
        codes=("UPI_FAILURE", "UPI_DECLINED", "UPI_TIMEOUT"),
    ),
    CategoryRule(
        category="BANK_TIMEOUT",
        normalized_reason="The customer's bank did not respond in time.",
        severity="LOW",
        recommended_action="RETRY_SOON",
        retry_delay_hours=1,
        alternative_method="UPI",
        recovery_probability=75,
        reasoning=(
            "Bank timeouts are usually temporary congestion. The payment may "
            "even settle later; a retry after a short wait is safe and effective."
        ),
        keywords=("timeout", "timed out", "bank unavailable", "gateway down"),
        codes=("BANK_TIMEOUT", "TIMEOUT", "GATEWAY_TIMEOUT"),
    ),
    CategoryRule(
        category="NETWORK_ERROR",
        normalized_reason="A network interruption stopped the payment from completing.",
        severity="LOW",
        recommended_action="RETRY_IMMEDIATELY",
        retry_delay_hours=None,
        alternative_method=None,
        recovery_probability=88,
        reasoning=(
            "No funds movement is confirmed, and the failure was purely a "
            "connectivity problem. An immediate retry has the highest recovery "
            "probability."
        ),
        keywords=("network", "connection", "internet", "unreachable"),
        codes=("NETWORK_ERROR", "CONNECTION_FAILED", "NETWORK_TIMEOUT"),
    ),
    CategoryRule(
        category="AUTHENTICATION_FAILED",
        normalized_reason="The customer could not complete payment authentication.",
        severity="MEDIUM",
        recommended_action="REQUEST_ALTERNATIVE_PAYMENT_METHOD",
        retry_delay_hours=None,
        alternative_method="UPI",
        recovery_probability=55,
        reasoning=(
            "Authentication (OTP/3DS) failed or was cancelled. Retry conversion "
            "is low; offering another method performs better."
        ),
        keywords=("authentication", "otp", "3ds", "3d secure", "not authorized"),
        codes=("AUTHENTICATION_FAILED", "OTP_FAILED", "THREEDS_FAILED"),
    ),
    CategoryRule(
        category="PAYMENT_ABANDONED",
        normalized_reason="The customer left the checkout before completing payment.",
        severity="MEDIUM",
        recommended_action="SEND_RECOVERY_REMINDER",
        retry_delay_hours=None,
        alternative_method="UPI",
        recovery_probability=45,
        reasoning=(
            "The customer showed intent but abandoned checkout. A gentle "
            "reminder with a one-click retry link recovers a meaningful share "
            "of abandoned payments."
        ),
        keywords=("abandoned", "cancelled checkout", "dropped off", "left checkout"),
        codes=("PAYMENT_ABANDONED", "CHECKOUT_ABANDONED", "USER_DROPPED"),
    ),
    CategoryRule(
        category="DUPLICATE_PAYMENT",
        normalized_reason="A payment with the same reference was already completed.",
        severity="LOW",
        recommended_action="DO_NOT_RETRY",
        retry_delay_hours=None,
        alternative_method=None,
        recovery_probability=0,
        reasoning=(
            "This looks like a duplicate submission — a completed payment with "
            "the same reference already exists. Retrying would double-charge "
            "the customer, so no recovery action is recommended."
        ),
        keywords=("duplicate", "already paid", "already processed"),
        codes=("DUPLICATE_PAYMENT", "ALREADY_PAID"),
    ),
# __RULES_END__
)


# ---------------------------------------------------------------------------
# Deterministic Recovery Intelligence Engine
# ---------------------------------------------------------------------------

#: Fallback category used when nothing else matches.
UNKNOWN_RULE: CategoryRule = CategoryRule(
    category="UNKNOWN",
    normalized_reason="The payment could not be completed, but the exact cause is unclear.",
    severity="MEDIUM",
    recommended_action="REVIEW_PAYMENT_DETAILS",
    retry_delay_hours=None,
    alternative_method="UPI",
    recovery_probability=50,
    reasoning=(
        "The failure did not match a known error pattern. Review the payment "
        "details with the customer before attempting another method."
    ),
    keywords=(),
    codes=(),
)


def _match_rule(
    failure_code: str | None,
    failure_message: str | None,
    payment_method: str,
) -> CategoryRule:
    """Match a failure to the best rule using: exact code, code words, message keywords,then method-aware fallback."""
    code_norm = (failure_code or "").strip().upper().replace(" ", "_")
    msg_norm = (failure_message or "").lower()

    # 1. Exact / normalized code match
    for rule in RULES:
        if code_norm in rule.codes:
            return rule

    # 2. Message-keyword match
    for rule in RULES:
        if any(k in msg_norm for k in rule.keywords):
            return rule

    # 3. Method-aware fallback
    if payment_method in ("Credit Card", "Debit Card"):
        return next((r for r in RULES if r.category == "CARD_DECLINED"), UNKNOWN_RULE)
    if payment_method == "UPI":
        return next((r for r in RULES if r.category == "UPI_FAILURE"), UNKNOWN_RULE)

    if payment_method == "Bank Transfer":
        return next((r for r in RULES if r.category == "BANK_TIMEOUT"), UNKNOWN_RULE)

    return UNKNOWN_RULE


def _amount_factor(amount: float) -> int:
    """Deterministic modifier: small/medium/large amounts adjust probability."""
    if amount <= 0:
        return 0
    if amount < 10000:
        return -5
    if amount >= 50000:
        return 5
    if amount >= 20000:
        return 3
    return 0
class RevenueRecoveryEngine:
    """Deterministic failure-categorization and recommendation engine (Phase 1)."""

    def analyze_failure(
        self,
        *,
        failure_code: str | None = None,
        failure_message: str | None = None,
        payment_method: str,
        amount: float,
        currency: str,
        retry_delay_hours: int | None = None,
    ) -> dict:
        """Return a structured, deterministic failure analysis."""
        rule = _match_rule(failure_code, failure_message, payment_method)
        delay_hours = rule.retry_delay_hours if retry_delay_hours is None else retry_delay_hours
        probability = max(0, min(100, rule.recovery_probability + _amount_factor(amount)))

        alternative = self.recommend_alternative_method(payment_method, rule)

        return {
            "failure_category": rule.category,
            "normalized_reason": rule.normalized_reason,
            "severity": rule.severity,
            "risk_level": rule.severity,
            "recommended_action": rule.recommended_action,
            "suggested_retry_delay_hours": delay_hours,
            "alternative_payment_method": alternative,
            "recovery_probability": probability,
            "reasoning": rule.reasoning,
        }

    def recommend_alternative_method(
        self, payment_method: str, rule: CategoryRule,
    ) -> str | None:
        """Pick an alternative method —the rule's hint, or the cheapest available."""
        if rule.alternative_method:
            return rule.alternative_method

        alternative = None
        best_fee: float | None = None
        for name, cfg in PAYMENT_METHOD_CONFIG.items():
            if name == payment_method:
                continue
            fee = float(cfg["fee_percentage"])
            if best_fee is None or fee < best_fee:
                best_fee = fee
                alternative = name
        return alternative
engine = RevenueRecoveryEngine()


def recoverable_statuses() -> tuple[str, ...]:
    return ("PENDING", "FAILED", "ABANDONED", "RECOVERY_RECOMMENDED")


class RecoveryRepository:
    """Async persistence for the Revenue Recovery Agent."""

    def __init__(self, session: AsyncSession, user_id: str):
        self._session = session
        self._user_id = user_id

    # -- Write -----------------------------------------------------------

    async def create_attempt(self, payload) -> PaymentAttempt:
        """Record a payment attempt for the current user."""
        attempt = PaymentAttempt(
            user_id=self._user_id,
            amount=payload.amount,
            currency=payload.currency.upper(),
            payment_method=payload.payment_method,
            status=payload.status or "CREATED",
            failure_code=payload.failure_code,
            failure_message=payload.failure_message,
            gateway_payment_id=payload.gateway_payment_id,
            gateway_order_id=payload.gateway_order_id,
        )
        self._session.add(attempt)
        await self._session.commit()
        await self._session.refresh(attempt)
        return attempt

    async def attach_recommendation(self, attempt_id: str, analysis: dict) -> RecoveryRecommendation:
        """Persist an engine analysis as the attempt's one-to-one recommendation."""
        retry_after = None
        delay = analysis.get("suggested_retry_delay_hours")
        if delay:
            retry_after = datetime.now(timezone.utc) + timedelta(hours=int(delay))

        rec = RecoveryRecommendation(
            payment_attempt_id=attempt_id,
            recommended_action=analysis["recommended_action"],
            normalized_reason=analysis["normalized_reason"],
            alternative_payment_method=analysis.get("alternative_payment_method"),
            retry_after=retry_after,
            recovery_probability=analysis["recovery_probability"],
            risk_level=analysis["risk_level"],
            reasoning=analysis["reasoning"],
            status="PENDING",
        )
        self._session.add(rec)

        # Keep the attempt status in sync so the case shows as a recovery candidate.
        await self._session.execute(
            update(PaymentAttempt)
            .where(PaymentAttempt.id == attempt_id, PaymentAttempt.user_id == self._user_id)
            .values(status="RECOVERY_RECOMMENDED", failure_category=analysis["failure_category"])
        )
        await self._session.commit()
        await self._session.refresh(rec)
        # Reload the attempt so its (selectin-loaded) recommendation
        # relationship reflects the newly attached record — without this the
        # caller sees attempt.recommendation as a stale None.
        attempt = await self._session.get(PaymentAttempt, attempt_id)
        if attempt is not None:
            await self._session.refresh(attempt)
        return rec

    # -- Abandonment detection (request-time) -------------------------------

    async def detect_abandoned(self) -> None:
        """Stale PAYMENT_PENDING records from the current user older than the configured
        timeout (default 30 minutes) are transitioned to PAYMENT_ABANDONED."""
        cutoff = datetime.now(timezone.utc) - timedelta(
            minutes=settings.RECOVERY_ABANDON_TIMEOUT_MINUTES
        )
        await self._session.execute(
            update(PaymentAttempt)
            .where(
                PaymentAttempt.user_id == self._user_id,
                PaymentAttempt.status == "PAYMENT_PENDING",
                PaymentAttempt.updated_at < cutoff,
            )
            .values(status="PAYMENT_ABANDONED", updated_at=datetime.now(timezone.utc))
        )
        await self._session.commit()
# -- Read --------------------------------------------------------------

    async def get_cases(self, *, status: str | None = None, limit: int = 20, offset: int = 0) -> list[PaymentAttempt]:
        """List the user's attempts (newest first) with their recommendation."""
        query = (
            select(PaymentAttempt)
            .where(PaymentAttempt.user_id == self._user_id)
            .order_by(PaymentAttempt.created_at.desc())
            .limit(limit).offset(offset)
        )
        if status:
            query = query.where(PaymentAttempt.status == status.upper())
        result = await self._session.execute(query)
        return list(result.scalars().all())

    async def get_case(self, case_id: str) -> PaymentAttempt | None:
        """Fetch a single attempt — always scoped to the current user.

        The ``case_id`` may be either a ``PaymentAttempt.id`` or its linked
        ``RecoveryRecommendation.id`` (the API returns the recommendation id
        as the case ``id`` in :func:`_serialize_case`), so we match either.
        """
        from sqlalchemy import or_

        result = await self._session.execute(
            select(PaymentAttempt)
            .where(
                PaymentAttempt.user_id == self._user_id,
            )
            .where(
                or_(
                    PaymentAttempt.id == case_id,
                    PaymentAttempt.recommendation.has(id=case_id),
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_attempt_by_gateway_payment_id(self, gateway_payment_id: str) -> PaymentAttempt | None:
        """Find an existing attempt for the same provider payment reference.

        Used for idempotency: the same Razorpay failure event (identified by
        ``gateway_payment_id``) must not create duplicate recovery cases.
        Always scoped to the current user.
        """
        result = await self._session.execute(
            select(PaymentAttempt)
            .where(
                PaymentAttempt.gateway_payment_id == gateway_payment_id,
                PaymentAttempt.user_id == self._user_id,
            )
            .order_by(PaymentAttempt.created_at.desc())
        )
        return result.scalars().first()

    async def mark_recovered(self, case_id: str, recovered_amount: float | None = None) -> RecoveryRecommendation | None:
        """Mark a recovery case as successfully recovered (EXECUTED).

        Idempotent: if the case is already EXECUTED, returns the existing
        recommendation without double-counting. Only ACCEPTED cases can
        transition to EXECUTED.
        """
        case = await self.get_case(case_id)
        if case is None or case.recommendation is None:
            return None
        rec = case.recommendation
        if rec.status == "EXECUTED":
            return rec  # already recovered — do not double-count
        if rec.status not in ("ACCEPTED", "PENDING"):
            return None  # cannot recover a dismissed/rejected case
        rec.status = "EXECUTED"
        if recovered_amount is not None and recovered_amount > 0:
            # Store the actual recovered amount on the attempt for accurate tracking
            case.amount = recovered_amount
        await self._session.commit()
        await self._session.refresh(rec)
        await self._session.refresh(case)
        return rec

    # Allowed recommendation status transitions (strict state machine):
    #   PENDING  -> ACCEPTED | DISMISSED
    #   ACCEPTED -> EXECUTED | DISMISSED
    #   DISMISSED and EXECUTED are terminal.
    _ALLOWED_TRANSITIONS: dict[str, set[str]] = {
        "PENDING": {"ACCEPTED", "DISMISSED"},
        "ACCEPTED": {"EXECUTED", "DISMISSED"},
        "DISMISSED": set(),
        "EXECUTED": set(),
    }

    async def update_recommendation_status(self, case_id: str, status: str) -> RecoveryRecommendation | None:
        """Update the recommendation status for a case (scoped to user).

        Enforces the strict state machine above; raises ``ValueError`` for an
        invalid transition so callers can map it to a 4xx API error.
        """
        case = await self.get_case(case_id)
        if case is None or case.recommendation is None:
            return None
        rec = case.recommendation
        allowed = self._ALLOWED_TRANSITIONS.get(rec.status, set())
        if status != rec.status and status not in allowed:
            raise ValueError(
                f"Invalid status transition: {rec.status} -> {status}. "
                f"Allowed next statuses: {sorted(allowed) or 'none (terminal)'}"
            )
        rec.status = status
        await self._session.commit()
        await self._session.refresh(rec)
        return rec

    # -- Summary -----------------------------------------------------------

    async def get_summary(self) -> dict:
        """Compute the user's recovery overview (deterministic, from real data)."""
        await self.detect_abandoned()
        cases = await self.get_cases(limit=1000)
        failed = [c for c in cases if c.status in recoverable_statuses()]
        recs = [c for c in failed if c.recommendation is not None]
        at_risk = sum(float(c.amount) or 0 for c in recs)

        # Recovered revenue: cases with EXECUTED recommendation status
        recovered_cases = [c for c in cases if c.recommendation is not None and c.recommendation.status == "EXECUTED"]
        recovered_revenue = sum(float(c.amount) or 0 for c in recovered_cases)

        probs = [c.recommendation.recovery_probability for c in recs]
        avg_prob = round(sum(probs) / len(probs)) if probs else 0
        high_priority = sum(
            1 for c in recs
            if (c.recommendation.risk_level in ("HIGH", "CRITICAL"))
                or (c.recommendation.recovery_probability >= 70 and c.status == "FAILED")
        )
        return {
            "failed_payments": len(failed),
            "potential_recoverable_revenue": round(at_risk, 2),
            "recovered_revenue": round(recovered_revenue, 2),
            "recovered_cases": len(recovered_cases),
            "average_recovery_probability": avg_prob,
            "high_priority_recoveries": high_priority,
            "total_cases": len(cases),
        }