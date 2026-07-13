"""Provider factory with a test/override hook.

Production uses the configured OpenAI-compatible provider. Tests (or local dev
without a key) can inject a provider via :func:`set_provider`.
"""

from __future__ import annotations

from app.agents.llm.base import LLMProvider
from app.agents.llm.openai_provider import build_default_provider
from app.core.config import settings
from app.core.exceptions import ValidationError

_override: LLMProvider | None = None


def set_provider(provider: LLMProvider) -> None:
    """Install a provider override (used by tests and offline dev)."""
    global _override
    _override = provider


def reset_provider() -> None:
    global _override
    _override = None


def get_provider() -> LLMProvider:
    if _override is not None:
        return _override
    if not settings.AI_API_KEY:
        raise ValidationError(
            "AI provider is not configured (set AI_API_KEY).",
            error_code="ai_not_configured",
        )
    return build_default_provider()
