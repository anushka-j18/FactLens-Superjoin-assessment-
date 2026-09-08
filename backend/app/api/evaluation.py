from typing import Dict, Any, List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.session import get_db
from app.models.entities import Document, Fact, FactRelationship
from pydantic import BaseModel

router = APIRouter(prefix="/api/evaluation", tags=["Evaluation"])


class EvaluationMetricsResponse(BaseModel):
    facts_extracted: int
    grounded_facts: int
    ungrounded_facts: int
    relationships_classified: int
    uncertain_relationships: int
    extraction_failures: int
    documents_processed: int
    documents_failed: int


@router.get("/metrics", response_model=EvaluationMetricsResponse)
def get_evaluation_metrics(db: Session = Depends(get_db)):
    """Return explicit system audit metrics without inventing accuracy percentages.
    
    Tracks:
    - facts_extracted
    - grounded_facts
    - ungrounded_facts
    - relationships_classified
    - uncertain_relationships
    - extraction_failures
    """
    total_facts = db.query(Fact).count()
    grounded_facts = db.query(Fact).filter(Fact.extraction_status == "grounded").count()
    ungrounded_facts = total_facts - grounded_facts

    total_relationships = db.query(FactRelationship).count()
    
    # Relationships with REASONING_FAILURE or confidence < 0.50
    uncertain_relationships = (
        db.query(FactRelationship)
        .filter(
            (FactRelationship.relationship_type == "REASONING_FAILURE") |
            (FactRelationship.confidence_score < 0.50)
        )
        .count()
    )

    documents_processed = db.query(Document).count()
    documents_failed = (
        db.query(Document)
        .filter(Document.extraction_status.in_(["failed", "no_facts_found"]))
        .count()
    )

    return EvaluationMetricsResponse(
        facts_extracted=total_facts,
        grounded_facts=grounded_facts,
        ungrounded_facts=ungrounded_facts,
        relationships_classified=total_relationships,
        uncertain_relationships=uncertain_relationships,
        extraction_failures=documents_failed,
        documents_processed=documents_processed,
        documents_failed=documents_failed,
    )
