"""LLM Provider abstraction package."""
from app.services.llm.base import LLMProvider
from app.services.llm.mock import MockLLMProvider
from app.services.llm.openai_provider import OpenAILLMProvider
from app.config import settings


def get_llm_provider(provider_name: str = None) -> LLMProvider:
    """Factory method to return the configured LLMProvider instance."""
    provider = provider_name or getattr(settings, "LLM_PROVIDER", "mock")
    provider = provider.lower()

    if provider == "openai":
        return OpenAILLMProvider()
    
    # Default fallback to MockLLMProvider if requested provider is unavailable/not configured
    return MockLLMProvider()


__all__ = ["LLMProvider", "MockLLMProvider", "OpenAILLMProvider", "get_llm_provider"]

