from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.entities import FactRelationship, Fact
from app.schemas.relationships import (
    RelationshipResponse,
    RelationshipListResponse,
    RelationshipAnalysisRequest,
    RelationshipAnalysisResponse,
)
from app.services.relationship_reasoner import (
    RelationshipReasonerService,
    RelationshipReasonerError,
)

router = APIRouter(prefix="/api/relationships", tags=["Relationships"])


@router.post(
    "/analyze",
    response_model=RelationshipAnalysisResponse,
    status_code=status.HTTP_200_OK
)
def analyze_relationships(
    request: Optional[RelationshipAnalysisRequest] = None,
    db: Session = Depends(get_db),
):
    """Run cross-document relationship analysis and classify fact pairs into the 4 mandatory cases."""
    doc_ids = request.document_ids if request else None

    try:
        relationships = RelationshipReasonerService.analyze_cross_document_relationships(
            db=db,
            document_ids=doc_ids,
        )

        return RelationshipAnalysisResponse(
            analyzed_relationships_count=len(relationships),
            relationships=relationships,
        )

    except RelationshipReasonerError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Relationship reasoning analysis failed: {str(e)}"
        )


@router.get("", response_model=RelationshipListResponse)
def list_relationships(
    relationship_type: Optional[str] = None,
    document_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """List analyzed relationships with optional filtering by category or document_id."""
    query = db.query(FactRelationship)

    if relationship_type:
        query = query.filter(FactRelationship.relationship_type.ilike(relationship_type))
    
    if document_id:
        # Join facts to filter relationships where source or target fact belongs to document
        query = query.join(Fact, FactRelationship.source_fact_id == Fact.id).filter(
            Fact.document_id == document_id
        )

    total = query.count()
    relationships = query.order_by(FactRelationship.created_at.desc()).offset(skip).limit(limit).all()

    return RelationshipListResponse(total=total, relationships=relationships)


@router.get("/{relationship_id}", response_model=RelationshipResponse)
def get_relationship(
    relationship_id: str,
    db: Session = Depends(get_db),
):
    """Retrieve details and reasoning trace for a specific cross-document relationship."""
    rel = db.query(FactRelationship).filter(FactRelationship.id == relationship_id).first()
    if not rel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Relationship with ID '{relationship_id}' not found."
        )
    return rel
