from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from app.schemas.documents import DocumentResponse


class KnowledgeLayerCreate(BaseModel):
    name: str
    description: Optional[str] = None


class KnowledgeLayerResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    document_count: Optional[int] = 0

    model_config = ConfigDict(from_attributes=True)


class KnowledgeLayerDetailResponse(KnowledgeLayerResponse):
    documents: List[DocumentResponse] = []


class KnowledgeLayerListResponse(BaseModel):
    total: int
    knowledge_layers: List[KnowledgeLayerResponse]
