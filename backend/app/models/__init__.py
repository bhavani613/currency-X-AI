"""SQLAlchemy ORM models for CurrencyX AI.

Importing the models here ensures they are registered on the shared
:class:`~app.database.base.Base` metadata, so ``Base.metadata.create_all``
can discover them during startup.
"""

from app.models.password_reset import PasswordResetToken
from app.models.payment import PaymentAnalysis, PaymentMethodComparison
from app.models.revenue_recovery import PaymentAttempt, RecoveryRecommendation
from app.models.user import User

__all__ = [
    "PasswordResetToken",
    "PaymentAnalysis",
    "PaymentMethodComparison",
    "PaymentAttempt",
    "RecoveryRecommendation",
    "User",
]