from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    description="Evidence-first document intelligence platform for fact extraction and cross-document reasoning.",
    version="0.1.0",
)

from app.api.documents import router as documents_router
from app.api.facts import router as facts_router
from app.api.relationships import router as relationships_router
from app.api.evaluation import router as evaluation_router

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(documents_router)
app.include_router(facts_router)
app.include_router(relationships_router)
app.include_router(evaluation_router)


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint to verify backend operational status."""
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "environment": settings.ENVIRONMENT,
        "llm_provider": settings.LLM_PROVIDER,
        "embedding_provider": settings.EMBEDDING_PROVIDER,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.BACKEND_HOST,
        port=settings.BACKEND_PORT,
        reload=True,
    )
