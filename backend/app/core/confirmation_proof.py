"""Short-lived, single-use password-confirmation proof.

Used by payment creation to enforce password confirmation on the backend,
so direct API calls cannot bypass the frontend password modal.

Security properties:
- The proof is a signed JWT containing ONLY the user id, a random jti,
  a type marker, and a short expiry (5 minutes).
- It never contains the password or password hash.
- It is bound to the authenticated user (``sub`` must match).
- It is single-use: the jti is recorded in an in-memory set on first use.
  (In-memory is intentional for a single-process deployment; a restart
  simply invalidates outstanding proofs, which is safe — fail closed.)
"""

import uuid
from datetime import datetime, timedelta, timezone

import jwt

from app.config import settings

_PROOF_TYPE = "password_confirmation"
_PROOF_TTL_SECONDS = 300  # 5 minutes

# jti values already consumed (single-use enforcement)
_used_jtis: set[str] = set()
_MAX_TRACKED = 10_000  # simple cap to bound memory


class ConfirmationProofError(Exception):
    """Raised when a confirmation proof is missing, invalid, expired, or reused."""


def create_confirmation_proof(user_id: str) -> str:
    """Issue a short-lived, single-use proof that this user confirmed their password."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "typ": _PROOF_TYPE,
        "jti": uuid.uuid4().hex,
        "iat": now,
        "exp": now + timedelta(seconds=_PROOF_TTL_SECONDS),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def consume_confirmation_proof(proof: str, user_id: str) -> None:
    """Validate and burn a confirmation proof.

    Raises :class:`ConfirmationProofError` if the proof is invalid, expired,
    belongs to a different user, or has already been used.
    """
    if not proof:
        raise ConfirmationProofError("Password confirmation required")

    try:
        payload = jwt.decode(
            proof,
            settings.SECRET_KEY,
            algorithms=["HS256"],
            options={"require": ["exp", "sub", "jti", "typ"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise ConfirmationProofError("Password confirmation expired, please confirm again") from exc
    except jwt.InvalidTokenError as exc:
        raise ConfirmationProofError("Invalid password confirmation") from exc

    if payload.get("typ") != _PROOF_TYPE:
        raise ConfirmationProofError("Invalid password confirmation")

    if payload.get("sub") != str(user_id):
        # Valid token but issued for a different user — reject without details.
        raise ConfirmationProofError("Invalid password confirmation")

    jti = payload["jti"]
    if jti in _used_jtis:
        raise ConfirmationProofError("Password confirmation already used, please confirm again")

    # Burn it (single-use). Bound memory by discarding oldest tracking via cap.
    if len(_used_jtis) >= _MAX_TRACKED:
        # Evict arbitrary items; proofs expire in 5 min so this is safe.
        for i, tracked in enumerate(list(_used_jtis)):
            if i >= _MAX_TRACKED // 2:
                break
            _used_jtis.discard(tracked)
    _used_jtis.add(jti)
