"""Authentication endpoints — real PostgreSQL-backed auth."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.deps import rate_limit
from app.core.deps import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.database.connection import get_session
from app.models import PasswordResetToken, User
from app.schemas.auth import (
    AuthResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    PasswordVerifyRequest,
    PasswordVerifyResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
    SignupRequest,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])

# Brute-force protection for credential endpoints (per client IP).
_auth_rate_limit = rate_limit(max_requests=10, window_seconds=60)


def _db_unavailable() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Database is unavailable. Please check the backend database configuration.",
    )


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    payload: SignupRequest,
    session: AsyncSession | None = Depends(get_session),
    _rl: None = Depends(_auth_rate_limit),
):
    if session is None:
        raise _db_unavailable()

    email = payload.email.lower()
    existing = await session.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists. Please login.",
        )

    user = User(
        full_name=payload.full_name.strip(),
        email=email,
        password_hash=hash_password(payload.password),
    )
    session.add(user)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists. Please login.",
        )
    await session.refresh(user)

    return AuthResponse(
        success=True,
        user=UserResponse(id=user.id, full_name=user.full_name, email=user.email),
        access_token=create_access_token(user.id, user.email),
    )


@router.post("/verify-password", response_model=PasswordVerifyResponse)
async def verify_password_endpoint(
    payload: PasswordVerifyRequest,
    user: User = Depends(get_current_user),
    _rl: None = Depends(_auth_rate_limit),
):
    """Verify the current user's password before authorizing a sensitive action
    (e.g. executing a payment).

    - Requires a valid JWT (``Authorization: Bearer <token>``).
    - Verifies the supplied plaintext password against the stored bcrypt hash
      using the existing :func:`verify_password` helper.
    - Returns ``{"success": true}`` only on a match; ``401`` otherwise.
    - Never returns or logs the hash or the plaintext password.
    """
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password.",
        )
    return PasswordVerifyResponse(success=True)


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: LoginRequest,
    session: AsyncSession | None = Depends(get_session),
    _rl: None = Depends(_auth_rate_limit),
):
    if session is None:
        raise _db_unavailable()

    email = payload.email.lower()
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    return AuthResponse(
        success=True,
        user=UserResponse(id=user.id, full_name=user.full_name, email=user.email),
        access_token=create_access_token(user.id, user.email),
    )


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(
    payload: ForgotPasswordRequest,
    session: AsyncSession | None = Depends(get_session),
    _rl: None = Depends(_auth_rate_limit),
):
    """Start a password reset.

    Security properties:
    - NEVER reveals whether the email exists (identical response either way).
    - The reset token is cryptographically random (``secrets.token_urlsafe``).
    - Only a SHA-256 hash of the token is persisted; the raw token would be
      delivered by email in production (SMTP config is a later-phase concern).
    - Any previously issued unused tokens are invalidated.
    """
    if session is None:
        raise _db_unavailable()

    email = payload.email.lower()
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    message = (
        "If an account with that email exists, a password reset link has been sent."
    )
    dev_reset_token: str | None = None

    if user is not None:
        now = datetime.now(timezone.utc)
        # Invalidate any previous outstanding tokens for this user.
        outstanding = await session.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.user_id == user.id,
                PasswordResetToken.used_at.is_(None),
            )
        )
        for old in outstanding.scalars():
            old.used_at = now

        raw_token = secrets.token_urlsafe(32)
        session.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
                expires_at=now + timedelta(minutes=settings.PASSWORD_RESET_TOKEN_MINUTES),
            )
        )
        await session.commit()

        # Dev/demo only — never in production (see Settings docstring).
        if settings.EXPOSE_RESET_TOKEN_IN_RESPONSE:
            dev_reset_token = raw_token

    return ForgotPasswordResponse(
        success=True, message=message, dev_reset_token=dev_reset_token
    )


@router.post("/reset-password", response_model=ResetPasswordResponse)
async def reset_password(
    payload: ResetPasswordRequest,
    session: AsyncSession | None = Depends(get_session),
    _rl: None = Depends(_auth_rate_limit),
):
    """Complete a password reset using a valid, unused, unexpired token.

    - The token is single-use: it is marked used atomically with the password
      change and is invalid on any subsequent attempt.
    - All other outstanding tokens for the user are invalidated.
    - The new password must satisfy the same strong-password policy as signup.
    - Never reveals or logs password material or hashes.
    """
    if session is None:
        raise _db_unavailable()

    token_hash = hashlib.sha256(payload.token.encode()).hexdigest()
    result = await session.execute(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
    )
    reset_token = result.scalar_one_or_none()

    invalid = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid or expired reset token.",
    )
    if reset_token is None or reset_token.used_at is not None:
        raise invalid

    expires_at = reset_token.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise invalid

    user_result = await session.execute(
        select(User).where(User.id == reset_token.user_id)
    )
    user = user_result.scalar_one_or_none()
    if user is None:
        raise invalid

    now = datetime.now(timezone.utc)
    user.password_hash = hash_password(payload.password)
    reset_token.used_at = now
    # Invalidate any other outstanding tokens for this user.
    outstanding = await session.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        )
    )
    for old in outstanding.scalars():
        old.used_at = now
    await session.commit()

    return ResetPasswordResponse(
        success=True,
        message="Password has been reset successfully. You can now login with your new password.",
    )