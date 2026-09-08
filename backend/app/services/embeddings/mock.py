import hashlib
import math
from typing import List
from app.services.embeddings.base import EmbeddingProvider


class MockEmbeddingProvider(EmbeddingProvider):
    """Mock Embedding Provider for offline testing and deterministic candidate retrieval.
    
    Generates unit-normalized 64-dimensional float vectors based on text token hashing
    and semantic token overlaps.
    """

    DIMENSION = 64

    def embed_text(self, text: str) -> List[float]:
        """Embed a single text string into a 64-dimensional float vector."""
        if not text:
            return [0.0] * self.DIMENSION

        clean = text.lower().strip()
        tokens = [t for t in clean.split() if len(t) > 1]
        
        vec = [0.0] * self.DIMENSION

        # Hash individual tokens into vector dimensions
        for tok in tokens:
            h = hashlib.sha256(tok.encode("utf-8")).hexdigest()
            for idx in range(self.DIMENSION):
                # Use sub-hash chunks to populate dimensions
                val = int(h[idx % len(h)], 16) - 8
                vec[idx] += val

        # L2 Unit Normalization
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [round(x / norm, 6) for x in vec]
        else:
            vec[0] = 1.0

        return vec

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed a batch of text strings."""
        return [self.embed_text(t) for t in texts]
