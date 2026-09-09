from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class FactResponse(BaseModel):
    id: str
    document_id: str
    knowledge_layer_id: Optional[str] = None
    evidence_id: str
    evidence_ids: List[str] = Field(default_factory=list)
    page_number: int
    subject: str
    predicate: str
    value: str
    normalized_value: Optional[float] = None
    value_type: str
    unit: Optional[str] = None
    currency: Optional[str] = None
    temporal_context: Optional[str] = None
    geographic_scope: Optional[str] = None
    operating_scope: Optional[str] = None
    qualifiers: Dict[str, Any] = Field(default_factory=dict)
    verbatim_quote: str
    is_inferred: bool
    extraction_confidence: float
    extraction_status: str
    confidence_level: str = "HIGH"
    needs_review: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class FactListResponse(BaseModel):
    total: int
    facts: List[FactResponse]


class FactExtractionResponse(BaseModel):
    document_id: str
    extraction_status: str
    extracted_facts_count: int
    rejected_facts_count: int
    facts: List[FactResponse]
    run_id: Optional[str] = None
    error_message: Optional[str] = None


class ExtractionRunResponse(BaseModel):
    id: str
    document_id: str
    status: str
    provider: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    facts_created: int
    rejected_facts: int

    model_config = ConfigDict(from_attributes=True)

