"""Pydantic schemas for authentication endpoints."""

import re

from pydantic import BaseModel, EmailStr, Field, field_validator


def validate_strong_password(value: str) -> str:
    """Shared signup/reset password policy (server-side only).

    Rules: min 8 chars, at least one uppercase, one lowercase, one digit,
    one special character, and no whitespace.
    """
    if re.search(r"\s", value):
        raise ValueError("Password must not contain spaces.")
    if not re.search(r"[A-Z]", value):
        raise ValueError("Password must contain at least one uppercase letter.")
    if not re.search(r"[a-z]", value):
        raise ValueError("Password must contain at least one lowercase letter.")
    if not re.search(r"\d", value):
        raise ValueError("Password must contain at least one number.")
    if not re.search(r"[^A-Za-z0-9]", value):
        raise ValueError("Password must contain at least one special character (!@#$%^&*).")
    return value


class SignupRequest(BaseModel):
    full_name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def _strong_password(cls, value: str) -> str:
        """Enforce the signup password policy server-side.

        Existing users are never affected — this only runs when creating a
        NEW account.
        """
        return validate_strong_password(value)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserResponse(BaseModel):
    id: str
    full_name: str
    email: str


class AuthResponse(BaseModel):
    success: bool
    user: UserResponse
    access_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    success: bool
    message: str
    # Dev/test-only convenience: the raw reset token is returned ONLY when
    # EXPOSE_RESET_TOKEN_IN_RESPONSE=true (no SMTP/email delivery configured).
    # Production default is False — tokens are never sent in API responses.
    dev_reset_token: str | None = None


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=16, max_length=128)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def _strong_password(cls, value: str) -> str:
        return validate_strong_password(value)


class ResetPasswordResponse(BaseModel):
    success: bool
    message: str
    token_type: str = "bearer"


class PasswordVerifyRequest(BaseModel):
    password: str = Field(min_length=1, max_length=128)


class PasswordVerifyResponse(BaseModel):
    success: bool