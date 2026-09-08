from typing import List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.facts import FactResponse


class CandidateMatchResponse(BaseModel):
    candidate_fact_id: str
    candidate_fact: FactResponse
    similarity_score: float
    matching_criteria: Dict[str, Any] = Field(default_factory=dict)
    relevant_context: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True)


class CandidateListResponse(BaseModel):
    target_fact_id: str
    total_candidates: int
    candidates: List[CandidateMatchResponse]
