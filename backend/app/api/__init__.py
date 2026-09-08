"""API endpoints package."""
from app.api.documents import router as documents_router
from app.api.facts import router as facts_router
from app.api.relationships import router as relationships_router

__all__ = ["documents_router", "facts_router", "relationships_router"]
