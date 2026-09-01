"""Authentication endpoints — real PostgreSQL-backed auth."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password, verify_password
from app.database.connection import get_session
from app.models import User
from app.schemas.auth import AuthResponse, LoginRequest, SignupRequest, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


def _db_unavailable() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Database is unavailable. Please check the backend database configuration.",
    )


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def signup(payload: SignupRequest, session: AsyncSession | None = Depends(get_session)):
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


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest, session: AsyncSession | None = Depends(get_session)):
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