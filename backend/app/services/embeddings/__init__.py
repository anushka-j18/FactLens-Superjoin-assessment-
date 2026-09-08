"""Embedding Provider abstraction package."""
from app.services.embeddings.base import EmbeddingProvider
from app.services.embeddings.mock import MockEmbeddingProvider
from app.config import settings


def get_embedding_provider(provider_name: str = None) -> EmbeddingProvider:
    """Factory method to return configured EmbeddingProvider instance."""
    provider = provider_name or settings.EMBEDDING_PROVIDER
    provider = provider.lower()

    if provider == "mock":
        return MockEmbeddingProvider()

    # Default fallback to MockEmbeddingProvider
    return MockEmbeddingProvider()


__all__ = ["EmbeddingProvider", "MockEmbeddingProvider", "get_embedding_provider"]
