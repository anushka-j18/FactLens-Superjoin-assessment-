import math
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models.entities import Fact, FactEmbedding, Document
from app.services.embeddings import get_embedding_provider, EmbeddingProvider
from app.services.normalizer import FactNormalizer


class CandidateMatcherError(Exception):
    pass


class CandidateMatcherService:
    """Staged candidate matching and semantic retrieval service for FactLens.
    
    Combines Step 1 (Deterministic Metadata Filtering) with Step 2 (Cosine Vector Similarity)
    to retrieve candidate fact matches across documents without pairwise LLM invocations.
    """

    @classmethod
    def generate_and_store_embedding(
        cls,
        db: Session,
        fact: Fact,
        provider: Optional[EmbeddingProvider] = None
    ) -> FactEmbedding:
        """Compute dense vector representation for a fact statement and persist to DB."""
        embedder = provider or get_embedding_provider()
        
        statement = f"{fact.subject} {fact.predicate} {fact.value} {fact.temporal_context or ''} {fact.geographic_scope or ''} {fact.unit or ''}"
        vector = embedder.embed_text(statement)

        existing = db.query(FactEmbedding).filter(FactEmbedding.fact_id == fact.id).first()
        if existing:
            existing.vector = vector
            db.commit()
            db.refresh(existing)
            return existing

        embedding_rec = FactEmbedding(
            fact_id=fact.id,
            vector=vector,
        )
        db.add(embedding_rec)
        db.commit()
        db.refresh(embedding_rec)

        return embedding_rec

    @classmethod
    def find_candidate_matches(
        cls,
        db: Session,
        target_fact_id: str,
        limit: int = 10,
        min_similarity: float = 0.5,
        provider: Optional[EmbeddingProvider] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve top candidate matching facts across distinct documents.
        
        Returns candidates ranked by cosine similarity with deterministic matching metadata.
        """
        target_fact = db.query(Fact).filter(Fact.id == target_fact_id).first()
        if not target_fact:
            raise CandidateMatcherError(f"Fact with ID '{target_fact_id}' not found.")

        # Ensure target fact has an embedding stored
        target_emb = db.query(FactEmbedding).filter(FactEmbedding.fact_id == target_fact_id).first()
        if not target_emb:
            target_emb = cls.generate_and_store_embedding(db, target_fact, provider=provider)

        target_vec = target_emb.vector
        target_dict = cls._fact_to_dict(target_fact)

        # STEP 1: Query potential candidates from distinct documents
        candidate_facts = (
            db.query(Fact)
            .filter(
                Fact.document_id != target_fact.document_id,
                Fact.extraction_status == "grounded"
            )
            .all()
        )

        ranked_candidates: List[Dict[str, Any]] = []

        for cand in candidate_facts:
            cand_dict = cls._fact_to_dict(cand)

            # Step 1 Deterministic Metadata Comparison
            comp = FactNormalizer.are_facts_comparable(target_dict, cand_dict)
            if not comp["is_comparable"]:
                continue

            # Ensure candidate has an embedding
            cand_emb = db.query(FactEmbedding).filter(FactEmbedding.fact_id == cand.id).first()
            if not cand_emb:
                cand_emb = cls.generate_and_store_embedding(db, cand, provider=provider)

            # STEP 2 & 3: Compute Cosine Similarity
            sim_score = cls.cosine_similarity(target_vec, cand_emb.vector)

            if sim_score >= min_similarity:
                ranked_candidates.append({
                    "candidate_fact_id": cand.id,
                    "candidate_fact": cand,
                    "similarity_score": round(sim_score, 4),
                    "matching_criteria": comp,
                    "relevant_context": {
                        "target_document": target_fact.document.original_filename,
                        "candidate_document": cand.document.original_filename,
                        "temporal_overlap": comp["temporal_match"],
                        "geographic_overlap": comp["geographic_match"],
                    }
                })

        # STEP 4: Sort candidates by similarity score descending
        ranked_candidates.sort(key=lambda x: x["similarity_score"], reverse=True)

        return ranked_candidates[:limit]

    @staticmethod
    def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Compute cosine similarity between two float vectors."""
        if not vec1 or not vec2 or len(vec1) != len(vec2):
            return 0.0

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot_product / (norm1 * norm2)

    @staticmethod
    def _fact_to_dict(fact: Fact) -> Dict[str, Any]:
        return {
            "subject": fact.subject,
            "predicate": fact.predicate,
            "value": fact.value,
            "normalized_value": fact.normalized_value,
            "unit": fact.unit,
            "currency": fact.currency,
            "temporal_context": fact.temporal_context,
            "geographic_scope": fact.geographic_scope,
            "operating_scope": fact.operating_scope,
        }
