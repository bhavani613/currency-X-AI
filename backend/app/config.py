"""Application configuration loaded from environment variables.

Uses ``pydantic-settings`` to read a ``.env`` file (if present) and
environment variables.  The only required setting for now is the
PostgreSQL connection string.
"""

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the CurrencyX AI backend."""

    # extra="ignore" tolerates additional keys in .env (e.g. JWT_SECRET_KEY)
    # instead of crashing the whole backend on startup.
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    DATABASE_URL: str = ""

    # JWT auth settings. JWT_SECRET should be overridden in .env for production.
    # Accepts either JWT_SECRET or JWT_SECRET_KEY (both names have been used).
    JWT_SECRET: str = Field(
        default="currencyx-dev-secret-change-me",
        validation_alias=AliasChoices("JWT_SECRET", "JWT_SECRET_KEY"),
    )
    JWT_ALGORITHM: str = "HS256"
    # Deployment environment. Set ENVIRONMENT=production in production deploys;
    # production enforces a cryptographically strong JWT secret (>= 32 bytes).
    ENVIRONMENT: str = Field(default="development", alias="ENVIRONMENT")

    # Razorpay TEST MODE credentials. Loaded from .env — never hard-coded.
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""

    # Razorpay DEMO MODE — lets the app run a fully simulated payment flow
    # (demo_order_*/demo_payment_* ids, no real money) without needing valid
    # Razorpay credentials. When False, the real TEST MODE flow is required.
    RAZORPAY_DEMO_MODE: bool = True

    # --- Optional AI/LLM Enhancement -------------------------------------------
    # When AI_ENABLED=true and a valid provider is configured, the AI Advisor
    # adds an LLM-generated explanation layer on top of the deterministic
    # analysis. The deterministic engine remains the source of truth; the LLM
    # only explains already-calculated results. When AI_ENABLED=false or the
    # provider is unavailable, the advisor falls back to its rule-based response.
    #
    # Supported providers:
    #   - "openai"   : OpenAI API (requires OPENAI_API_KEY)
    #   - "ollama"   : Local LLM via Ollama (free, no key needed)
    #   - "huggingface" : Hugging Face Inference API (free tier, optional key)
    AI_ENABLED: bool = False
    AI_PROVIDER: str = "ollama"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    # Ollama settings (free local LLM)
    OLLAMA_BASE_URL: str = "http://localhost:11434/v1"
    OLLAMA_MODEL: str = "llama3.2"
    # Hugging Face settings (free tier)
    HUGGINGFACE_API_KEY: str = ""
    HUGGINGFACE_MODEL: str = "meta-llama/Llama-3.2-3B-Instruct"

    # Forgot Password — dev/test-only token exposure.
    # When no SMTP/email infrastructure is configured, the raw reset token
    # would otherwise be undeliverable. Setting EXPOSE_RESET_TOKEN_IN_RESPONSE
    # =true (development/demo ONLY) returns it in the API response so the flow
    # is testable end-to-end. Production MUST keep this False and deliver the
    # token via email (SMTP config is a later-phase concern).
    EXPOSE_RESET_TOKEN_IN_RESPONSE: bool = False
    #: Password reset token lifetime in minutes.
    PASSWORD_RESET_TOKEN_MINUTES: int = 30

    # Revenue Recovery Agent (Phase 1).
    #: After this many minutes a PAYMENT_PENDING attempt becomes ABANDONED.
    RECOVERY_ABANDON_TIMEOUT_MINUTES: int = 30
    #: Development-only seed helper for demo cases.

    RECOVERY_DEMO_ENABLED: bool = True

    # CORS origins allowed to call this API (comma-separated).
    # Keep this an explicit allowlist — never use "*" together with credentials.
    CORS_ORIGINS: str = (
        "http://localhost:5173,"
        "http://127.0.0.1:5173,"
        "http://localhost:5174,"
        "http://127.0.0.1:5174"
    )

    @property
    def cors_origins(self) -> list[str]:
        """Parsed, normalized CORS origin allowlist.

        Accepts a comma-separated string from the environment, trims
        whitespace, removes trailing slashes, drops empty entries, and
        de-duplicates while preserving order.
        """
        seen: list[str] = []
        for raw in self.CORS_ORIGINS.split(","):
            origin = raw.strip().rstrip("/")
            if origin and origin not in seen:
                seen.append(origin)
        return seen

    @model_validator(mode="after")
    def _validate_production_secrets(self) -> "Settings":
        """Refuse to boot in production with a weak JWT secret.

        The JWT secret must be at least 32 bytes when ``ENVIRONMENT=production``
        (HS256 needs >= 256 bits of key material; shorter secrets are brute-
        forcible). Development/demo environments are unaffected.
        """
        if self.ENVIRONMENT.lower() == "production" and len(self.JWT_SECRET.encode()) < 32:
            raise ValueError(
                "JWT_SECRET must be at least 32 bytes in production. "
                "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(48))\""
            )
        return self


settings = Settings()