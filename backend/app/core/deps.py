"""Shared FastAPI dependencies (current-user resolution from JWT)."""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import jwt, settings
from app.database.connection import get_session
from app.models import User

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession | None = Depends(get_session),
) -> User:
    """Resolve the current user from the ``Authorization: Bearer`` JWT.

    Raises 401 when the token is missing/invalid or the user no longer
    exists.  Returns ``None`` for the user when the database is degraded —
    callers treat that as 503.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Please login.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = jwt.decode(
            credentials.credentials, settings.JWT_SECRET, algorithms=["HS256"]
        )
        user_id = payload.get("sub")
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session. Please login again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable. Please check backend configuration.",
        )

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists. Please signup again.",
        )
    return user
async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession | None = Depends(get_session),
) -> User | None:
    """Resolve the current user when a valid JWT is provided; ``None`` otherwise.

    Unlike :func:`get_current_user` this never raises for a missing/invalid token —
    it returns ``None`` so optional-event endpoints (e.g. payment tracking) can
    associate records with the user when authenticated without breaking anonymous calls.
    """
    if credentials is None or session is None:
        return None
    try:
        payload = jwt.decode(
            credentials.credentials, settings.JWT_SECRET, algorithms=["HS256"]
        )
        user_id = payload.get("sub")
    except jwt.PyJWTError:
        return None
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        return None
    return user


# ---------------------------------------------------------------------------
# Simple in-memory fixed-window rate limiting (per client IP).
# Suitable for a single-process prototype; NOT suitable for multi-worker
# deployments — use a shared store (e.g. Redis) for that.
# ---------------------------------------------------------------------------

import time

from fastapi import Request

_RATE_BUCKETS: dict[str, list[float]] = {}


def rate_limit(max_requests: int, window_seconds: int):
    """Return a dependency that allows ``max_requests`` per ``window_seconds`` per IP."""

    async def _limit(request: Request) -> None:
        client_ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        bucket = _RATE_BUCKETS.setdefault(client_ip, [])
        # Drop entries outside the current window.
        bucket[:] = [ts for ts in bucket if now - ts < window_seconds]
        if len(bucket) >= max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again shortly.",
            )
        bucket.append(now)

    return _limit