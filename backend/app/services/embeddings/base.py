from abc import ABC, abstractmethod
from typing import List


class EmbeddingProvider(ABC):
    """Abstract base class for semantic embedding providers.
    
    Provides vector representations for extracted facts to support
    fast semantic candidate matching across documents.
    """
    
    @abstractmethod
    async def embed_text(self, text: str) -> List[float]:
        """Embed a single text string into a float vector."""
        pass
        
    @abstractmethod
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed a batch of text strings into float vectors."""
        pass
