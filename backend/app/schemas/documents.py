from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, ConfigDict


class EvidenceUnitResponse(BaseModel):
    id: str
    document_id: str
    page_number: int
    raw_text: str
    clean_text: str
    location_metadata: Dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentResponse(BaseModel):
    id: str
    knowledge_layer_id: Optional[str] = None
    filename: str
    original_filename: str
    file_size: int
    file_hash: str
    page_count: int
    processing_status: str
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


from app.schemas.facts import FactResponse


class DocumentDetailResponse(DocumentResponse):
    evidence_units: List[EvidenceUnitResponse] = []
    facts: List[FactResponse] = []


class DocumentListResponse(BaseModel):
    total: int
    documents: List[DocumentResponse]
