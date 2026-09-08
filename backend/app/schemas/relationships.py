from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.facts import FactResponse


class RelationshipResponse(BaseModel):
    id: str
    source_fact_id: str
    target_fact_id: str
    relationship_type: str  # CORROBORATED | CONTRADICTED | CONTEXTUALLY_RECONCILED | REASONING_FAILURE
    confidence_score: float
    confidence_level: str = "HIGH"
    needs_review: bool = False
    failure_reason: Optional[str] = None
    reasoning_summary: str
    reconciliation_context: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    source_fact: Optional[FactResponse] = None
    target_fact: Optional[FactResponse] = None

    model_config = ConfigDict(from_attributes=True)


class RelationshipListResponse(BaseModel):
    total: int
    relationships: List[RelationshipResponse]


class RelationshipAnalysisRequest(BaseModel):
    document_ids: Optional[List[str]] = None


class RelationshipAnalysisResponse(BaseModel):
    analyzed_relationships_count: int
    relationships: List[RelationshipResponse]
