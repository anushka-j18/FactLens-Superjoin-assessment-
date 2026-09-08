from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.documents import DocumentResponse
from app.schemas.knowledge_layer import (
    KnowledgeLayerCreate,
    KnowledgeLayerResponse,
    KnowledgeLayerDetailResponse,
    KnowledgeLayerListResponse,
)
from app.services.knowledge_layer_service import (
    KnowledgeLayerService,
    KnowledgeLayerNotFoundError,
)

router = APIRouter(prefix="/api/knowledge-layers", tags=["Knowledge Layers"])


@router.post("", response_model=KnowledgeLayerResponse, status_code=status.HTTP_201_CREATED)
def create_knowledge_layer(
    payload: KnowledgeLayerCreate,
    db: Session = Depends(get_db),
):
    """Create a new Knowledge Layer to group multi-document analysis."""
    if not payload.name or not payload.name.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Knowledge layer name cannot be empty."
        )
    
    kl = KnowledgeLayerService.create_knowledge_layer(
        db=db,
        name=payload.name,
        description=payload.description,
    )
    return KnowledgeLayerResponse(
        id=kl.id,
        name=kl.name,
        description=kl.description,
        created_at=kl.created_at,
        updated_at=kl.updated_at,
        document_count=len(kl.documents),
    )


@router.get("", response_model=KnowledgeLayerListResponse)
def list_knowledge_layers(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """List all Knowledge Layers."""
    total, kls = KnowledgeLayerService.list_knowledge_layers(db=db, skip=skip, limit=limit)
    response_items = [
        KnowledgeLayerResponse(
            id=kl.id,
            name=kl.name,
            description=kl.description,
            created_at=kl.created_at,
            updated_at=kl.updated_at,
            document_count=len(kl.documents),
        )
        for kl in kls
    ]
    return KnowledgeLayerListResponse(total=total, knowledge_layers=response_items)


@router.get("/{kl_id}", response_model=KnowledgeLayerDetailResponse)
def get_knowledge_layer(
    kl_id: str,
    db: Session = Depends(get_db),
):
    """Get single Knowledge Layer details with its document list."""
    kl = KnowledgeLayerService.get_knowledge_layer(db, kl_id)
    if not kl:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Knowledge Layer with ID '{kl_id}' not found."
        )

    doc_responses = [DocumentResponse.model_validate(d) for d in kl.documents]

    return KnowledgeLayerDetailResponse(
        id=kl.id,
        name=kl.name,
        description=kl.description,
        created_at=kl.created_at,
        updated_at=kl.updated_at,
        document_count=len(kl.documents),
        documents=doc_responses,
    )


@router.delete("/{kl_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_knowledge_layer(
    kl_id: str,
    db: Session = Depends(get_db),
):
    """Delete a Knowledge Layer and all its associated documents and evidence."""
    success = KnowledgeLayerService.delete_knowledge_layer(db, kl_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Knowledge Layer with ID '{kl_id}' not found."
        )
    return None


@router.post("/{kl_id}/documents", response_model=List[DocumentResponse], status_code=status.HTTP_201_CREATED)
async def upload_documents_to_knowledge_layer(
    kl_id: str,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
):
    """Upload one or MULTIPLE PDF files into a Knowledge Layer.
    
    Processes each PDF independently. If an individual file fails, its status 
    is set to 'failed' while other files in the batch continue processing.
    """
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one PDF file must be provided."
        )

    files_data: List[tuple[bytes, str]] = []
    for file in files:
        filename = file.filename or "unnamed.pdf"
        contents = await file.read()
        files_data.append((contents, filename))

    try:
        docs = KnowledgeLayerService.upload_and_process_documents(
            db=db,
            kl_id=kl_id,
            files_data=files_data,
        )
        return [DocumentResponse.model_validate(d) for d in docs]

    except KnowledgeLayerNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/{kl_id}/documents", response_model=List[DocumentResponse])
def get_knowledge_layer_documents(
    kl_id: str,
    db: Session = Depends(get_db),
):
    """Get all documents belonging to a specific Knowledge Layer."""
    kl = KnowledgeLayerService.get_knowledge_layer(db, kl_id)
    if not kl:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Knowledge Layer with ID '{kl_id}' not found."
        )
    return [DocumentResponse.model_validate(d) for d in kl.documents]
