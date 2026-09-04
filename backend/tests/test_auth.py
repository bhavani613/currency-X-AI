"""Tests for authentication password validation.

Tests the server-side password policy WITHOUT exposing or logging passwords.
All password strings are local test values that never touch a real database.
"""

import pytest


# ---------------------------------------------------------------------------
# Password validation tests — test the SignupRequest schema validator directly
# and through the API endpoint.
# ---------------------------------------------------------------------------

def test_weak_password_rejected():
    """A short, simple password must be rejected."""
    from app.schemas.auth import SignupRequest

    with pytest.raises(Exception):
        SignupRequest(
            full_name="Test User",
            email="weak@example.com",
            password="weak",
        )


def test_password_without_uppercase_rejected():
    """Password with no uppercase letter must be rejected."""
    from app.schemas.auth import SignupRequest

    with pytest.raises(Exception):
        SignupRequest(
            full_name="Test User",
            email="nouppercase@example.com",
            password="lowercase123!",
        )


def test_password_without_lowercase_rejected():
    """Password with no lowercase letter must be rejected."""
    from app.schemas.auth import SignupRequest

    with pytest.raises(Exception):
        SignupRequest(
            full_name="Test User",
            email="nolower@example.com",
            password="UPPERCASE123!",
        )


def test_password_without_number_rejected():
    """Password with no digit must be rejected."""
    from app.schemas.auth import SignupRequest

    with pytest.raises(Exception):
        SignupRequest(
            full_name="Test User",
            email="nopnum@example.com",
            password="NoNumber!",
        )


def test_password_without_special_char_rejected():
    """Password with no special character must be rejected."""
    from app.schemas.auth import SignupRequest

    with pytest.raises(Exception):
        SignupRequest(
            full_name="Test User",
            email="nospecial@example.com",
            password="NoSpecial123",
        )


def test_password_with_spaces_rejected():
    """Password containing whitespace must be rejected."""
    from app.schemas.auth import SignupRequest

    with pytest.raises(Exception):
        SignupRequest(
            full_name="Test User",
            email="spaces@example.com",
            password="Str0ng! Pass",
        )


def test_valid_strong_password_accepted():
    """A password meeting all criteria must be accepted."""
    from app.schemas.auth import SignupRequest

    req = SignupRequest(
        full_name="Test User",
        email="valid@example.com",
        password="Str0ng!Pass",
    )
    assert req.password == "Str0ng!Pass"
