"""Optional AI/LLM explanation layer for the CurrencyX AI Advisor.

This module provides a minimal, safe wrapper around an LLM provider. The LLM is
used ONLY to generate user-friendly explanations of already-calculated
deterministic results from the payment analysis and recovery engines. It is
never used for calculations, verification, or any security-sensitive
operation.

Supported providers:
  - "openai"      : OpenAI API (requires OPENAI_API_KEY)
  - "ollama"      : Local LLM via Ollama (free, no API key needed)
  - "huggingface" : Hugging Face Inference API (free tier, optional key)

If AI_ENABLED=false, or if the provider is unavailable, or if the call fails,
all functions return None and the caller falls back to the deterministic advisor.
"""

import logging

from app.config import settings

logger = logging.getLogger(__name__)


def _client():
    """Return an OpenAI-compatible client and model, or (None, None) if not configured."""
    if not settings.AI_ENABLED:
        return None, None

    try:
        import openai
    except ImportError:
        logger.warning("openai SDK not installed — using deterministic fallback.")
        return None, None

    provider = settings.AI_PROVIDER.lower()

    if provider == "openai":
        if not settings.OPENAI_API_KEY:
            logger.info("AI_ENABLED=true but OPENAI_API_KEY is not set — using deterministic fallback.")
            return None, None
        try:
            client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
            return client, settings.OPENAI_MODEL
        except Exception as exc:
            logger.warning("Failed to initialize OpenAI client: %s", exc)
            return None, None

    elif provider == "ollama":
        # Ollama provides an OpenAI-compatible API at localhost:11434
        # No API key required — uses a dummy key for SDK compatibility
        try:
            client = openai.OpenAI(
                base_url=settings.OLLAMA_BASE_URL,
                api_key="ollama",
            )
            return client, settings.OLLAMA_MODEL
        except Exception as exc:
            logger.warning("Failed to initialize Ollama client: %s", exc)
            return None, None

    elif provider == "huggingface":
        # Hugging Face Inference API (OpenAI-compatible)
        # Free tier available, optional API key for higher rate limits
        try:
            api_key = settings.HUGGINGFACE_API_KEY or "hf_dummy"
            client = openai.OpenAI(
                base_url="https://api-inference.huggingface.co/v1",
                api_key=api_key,
            )
            return client, settings.HUGGINGFACE_MODEL
        except Exception as exc:
            logger.warning("Failed to initialize Hugging Face client: %s", exc)
            return None, None

    else:
        logger.warning("Unsupported AI provider: %s", settings.AI_PROVIDER)
        return None, None


def enhance_advisor_explanation(analysis_summary: str, insights: list[str],
                                recommended_method: str, risk_level: str,
                                amount: str, source_currency: str,
                                destination: str) -> dict | None:
    """Generate an AI-enhanced explanation of the deterministic analysis result.

    Args:
        analysis_summary: The deterministic advisor summary text.
        insights: List of insight descriptions from the deterministic advisor.
        recommended_method: The recommended payment method.
        risk_level: low/medium/high.
        amount: Human-readable amount string.
        source_currency: Source currency code.
        destination: Destination country/currency.

    Returns:
        A dict with AI-enhanced fields, or None if AI is unavailable or fails.
    """
    client, model = _client()
    if client is None:
        return None

    system_prompt = (
        "You are a helpful cross-border payment advisor for CurrencyX AI. "
        "You ONLY explain already-calculated analysis results. "
        "You MUST NOT invent fees, exchange rates, or payment outcomes. "
        "You MUST NOT claim certainty where the analysis provides estimates. "
        "Be concise, factual, and user-friendly. "
        "Respond in JSON format with keys: summary, key_insight, recommended_action, risk_note."
    )

    user_prompt = (
        f"Payment: {amount} {source_currency} -> {destination}\n"
        f"Recommended method: {recommended_method}\n"
        f"Risk level: {risk_level}\n"
        f"Analysis summary: {analysis_summary}\n"
        f"Key insights:\n" + "\n".join(f"- {i}" for i in insights) +
        "\n\nProvide a concise JSON response explaining this analysis to the user."
    )

    try:
        # Use JSON mode if supported (OpenAI), fallback to plain text for others
        kwargs = dict(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.7,
            max_tokens=500,
        )
        # Only OpenAI supports response_format json_object; for others we parse manually
        if settings.AI_PROVIDER.lower() == "openai":
            kwargs["response_format"] = {"type": "json_object"}

        resp = client.chat.completions.create(**kwargs)
        content = resp.choices[0].message.content
        if not content:
            return None

        import json
        # Try to parse as JSON; if not JSON, wrap the text
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            # For providers that don't support JSON mode, extract from text
            data = {"summary": content.strip()}

        if not isinstance(data, dict):
            return None

        return {
            "summary": str(data.get("summary", "")),
            "key_insight": str(data.get("key_insight", "")),
            "recommended_action": str(data.get("recommended_action", "")),
            "risk_note": str(data.get("risk_note", "")),
        }
    except Exception as exc:
        logger.warning("AI provider call failed: %s — using deterministic fallback.", exc)
        return None
