"""Application configuration loaded from environment variables.

Uses ``pydantic-settings`` to read a ``.env`` file (if present) and
environment variables.  The only required setting for now is the
PostgreSQL connection string.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the CurrencyX AI backend."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    DATABASE_URL: str = ""

    # Razorpay TEST MODE credentials. Loaded from .env — never hard-coded.
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""


settings = Settings()