from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.entities import Fact, Document
from app.schemas.facts import (
    FactResponse,
    FactListResponse,
    FactExtractionResponse,
)
from app.services.fact_extractor import FactExtractorService, FactExtractorError

router = APIRouter(tags=["Facts"])


@router.post(
    "/api/documents/{document_id}/extract",
    response_model=FactExtractionResponse,
    status_code=status.HTTP_200_OK
)
def extract_document_facts(
    document_id: str,
    db: Session = Depends(get_db),
):
    """Trigger grounded fact extraction on an ingested PDF document.
    
    Backend feeds valid evidence IDs to LLM, then validates that returned evidence IDs
    and verbatim quotes are grounded in source text before persisting facts.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found."
        )

    try:
        ext_status, facts, rejected_count = FactExtractorService.extract_facts_from_document(
            db=db,
            document_id=document_id,
        )

        return FactExtractionResponse(
            document_id=document_id,
            extraction_status=ext_status,
            extracted_facts_count=len(facts),
            rejected_facts_count=rejected_count,
            facts=facts,
        )

    except FactExtractorError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Fact extraction failed: {str(e)}"
        )


@router.get("/api/facts", response_model=FactListResponse)
def list_facts(
    document_id: Optional[str] = None,
    subject: Optional[str] = None,
    predicate: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """List extracted facts with optional filtering by document_id, subject, or predicate."""
    query = db.query(Fact)

    if document_id:
        query = query.filter(Fact.document_id == document_id)
    if subject:
        query = query.filter(Fact.subject.ilike(f"%{subject}%"))
    if predicate:
        query = query.filter(Fact.predicate.ilike(f"%{predicate}%"))

    total = query.count()
    facts = query.order_by(Fact.created_at.desc()).offset(skip).limit(limit).all()

    return FactListResponse(total=total, facts=facts)


@router.get("/api/facts/{fact_id}", response_model=FactResponse)
def get_fact(
    fact_id: str,
    db: Session = Depends(get_db),
):
    """Retrieve details and source evidence for a specific fact by ID."""
    fact = db.query(Fact).filter(Fact.id == fact_id).first()
    if not fact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fact with ID '{fact_id}' not found."
        )
    return fact


@router.get("/api/documents/{document_id}/facts", response_model=List[FactResponse])
def get_document_facts(
    document_id: str,
    db: Session = Depends(get_db),
):
    """Retrieve all extracted facts associated with a specific document."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found."
        )

    return (
        db.query(Fact)
        .filter(Fact.document_id == document_id)
        .order_by(Fact.page_number.asc(), Fact.created_at.asc())
        .all()
    )


from app.schemas.candidates import CandidateListResponse
from app.services.candidate_matcher import CandidateMatcherService, CandidateMatcherError


@router.get("/api/facts/{fact_id}/candidates", response_model=CandidateListResponse)
def get_fact_candidates(
    fact_id: str,
    limit: int = 10,
    min_similarity: float = 0.5,
    db: Session = Depends(get_db),
):
    """Retrieve top candidate matching facts across distinct documents based on 2-stage matching.
    
    1. Deterministic metadata pre-filtering (subject & predicate matching).
    2. Cosine vector similarity ranking using dense embeddings.
    """
    fact = db.query(Fact).filter(Fact.id == fact_id).first()
    if not fact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Fact with ID '{fact_id}' not found."
        )

    try:
        candidates = CandidateMatcherService.find_candidate_matches(
            db=db,
            target_fact_id=fact_id,
            limit=limit,
            min_similarity=min_similarity,
        )

        return CandidateListResponse(
            target_fact_id=fact_id,
            total_candidates=len(candidates),
            candidates=candidates,
        )

    except CandidateMatcherError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Candidate matching failed: {str(e)}"
        )
