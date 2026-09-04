"""Optional SMTP email delivery for password-reset links.

Design rules:
- If SMTP is not configured, ``send_reset_email`` returns False and the
  caller falls back to the existing development-only reset-token behavior.
- Delivery failures are logged WITHOUT exception details (SMTP error text
  can contain credentials) and never propagate — the API must not crash.
- Credentials are read from environment variables only:

    SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD,
    SMTP_FROM_EMAIL, SMTP_USE_TLS, FRONTEND_URL
"""

import logging
import os
import smtplib
from email.message import EmailMessage

logger = logging.getLogger(__name__)


def smtp_configured() -> bool:
    """True when the minimum required SMTP settings are present."""
    return bool(os.getenv("SMTP_HOST") and os.getenv("SMTP_FROM_EMAIL"))


def send_reset_email(to_email: str, reset_token: str) -> bool:
    """Send a password-reset email containing a one-time reset link.

    Returns True when the email was sent, False otherwise (including when
    SMTP is unconfigured). Never raises.
    """
    if not smtp_configured():
        return False

    try:
        host = os.getenv("SMTP_HOST")
        port = int(os.getenv("SMTP_PORT", "587"))
        username = os.getenv("SMTP_USERNAME") or None
        password = os.getenv("SMTP_PASSWORD") or None
        from_email = os.getenv("SMTP_FROM_EMAIL")
        use_tls = os.getenv("SMTP_USE_TLS", "true").strip().lower() in ("1", "true", "yes")

        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip("/")
        reset_link = f"{frontend_url}/forgot-password?token={reset_token}"

        msg = EmailMessage()
        msg["Subject"] = "CurrencyX AI — Password Reset"
        msg["From"] = from_email
        msg["To"] = to_email
        msg.set_content(
            "We received a request to reset your CurrencyX AI password.\n\n"
            f"Reset your password: {reset_link}\n\n"
            "This link is valid for a limited time and can be used only once.\n"
            "If you did not request a password reset, you can safely ignore "
            "this email — your current password remains active."
        )

        with smtplib.SMTP(host, port, timeout=10) as server:
            if use_tls:
                server.starttls()
            if username and password:
                server.login(username, password)
            server.send_message(msg)

        return True
    except Exception as exc:  # noqa: BLE001 — email delivery must never crash the API
        # Log only the exception TYPE: SMTP error messages can echo credentials.
        logger.warning("Password-reset email delivery failed: %s", type(exc).__name__)
        return False