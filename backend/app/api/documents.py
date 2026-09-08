from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session

from app.db.session import get_db, Base, engine
from app.models.entities import Document
from app.schemas.documents import (
    DocumentResponse,
    DocumentDetailResponse,
    DocumentListResponse,
    EvidenceUnitResponse,
)
from app.services.document_service import (
    DocumentService,
    DocumentServiceError,
    DuplicateDocumentError,
)
from app.services.evidence_service import EvidenceService
from app.services.pdf_parser import PdfParserError

# Ensure DB tables exist
Base.metadata.create_all(bind=engine)

router = APIRouter(prefix="/api/documents", tags=["Documents"])


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload and ingest a PDF document.
    
    Validates PDF format, integrity, file size, and duplicates before extracting
    verbatim page evidence units.
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided in upload request."
        )

    try:
        contents = await file.read()
        
        # Process upload and store document metadata
        doc = DocumentService.process_pdf_upload(
            db=db,
            file_bytes=contents,
            original_filename=file.filename,
        )

        # Ingest pages and extract evidence units
        EvidenceService.ingest_and_extract_evidence(db=db, document=doc)

        return doc

    except DuplicateDocumentError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "Duplicate document detected",
                "message": str(e),
                "existing_document_id": e.existing_document.id,
            }
        )
    except (DocumentServiceError, PdfParserError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during ingestion: {str(e)}"
        )


@router.get("", response_model=DocumentListResponse)
def list_documents(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """List all uploaded PDF documents."""
    total, docs = DocumentService.list_documents(db=db, skip=skip, limit=limit)
    return DocumentListResponse(total=total, documents=docs)


@router.get("/{document_id}", response_model=DocumentDetailResponse)
def get_document(
    document_id: str,
    db: Session = Depends(get_db),
):
    """Get single document details and metadata."""
    doc = DocumentService.get_document_by_id(db, document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found."
        )
    
    evidence_units = EvidenceService.get_evidence_by_document(db, document_id)
    
    return DocumentDetailResponse(
        id=doc.id,
        filename=doc.filename,
        original_filename=doc.original_filename,
        file_size=doc.file_size,
        file_hash=doc.file_hash,
        page_count=doc.page_count,
        processing_status=doc.processing_status,
        error_message=doc.error_message,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
        evidence_units=evidence_units,
    )


@router.get("/{document_id}/evidence", response_model=List[EvidenceUnitResponse])
def get_document_evidence(
    document_id: str,
    db: Session = Depends(get_db),
):
    """Retrieve evidence units (pages) extracted for a specific document."""
    doc = DocumentService.get_document_by_id(db, document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found."
        )
        
    return EvidenceService.get_evidence_by_document(db, document_id)


from app.services.fact_extractor import FactExtractorService
from app.services.candidate_matcher import CandidateMatcherService
from app.services.relationship_reasoner import RelationshipReasonerService


@router.post("/{document_id}/process_incremental")
def process_document_incremental(
    document_id: str,
    db: Session = Depends(get_db),
):
    """Incrementally process a newly ingested PDF document against existing knowledge.
    
    Extracts facts only for this document, generates embeddings, and compares new claims against 
    existing facts across prior documents without re-extracting or re-evaluating older files.
    """
    doc = DocumentService.get_document_by_id(db, document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found."
        )

    # 1. Fact Extraction for new document ONLY
    ext_status, new_facts, rejected_count = FactExtractorService.extract_facts_from_document(
        db=db,
        document_id=document_id,
    )

    # 2. Vector Embedding Generation for new facts
    for fact in new_facts:
        CandidateMatcherService.generate_and_store_embedding(db, fact)

    # 3. Incremental Relationship Reasoning against existing knowledge base
    new_relationships = RelationshipReasonerService.analyze_incremental_document_relationships(
        db=db,
        new_document_id=document_id,
    )

    return {
        "document_id": document_id,
        "status": "completed",
        "new_facts_extracted": len(new_facts),
        "rejected_facts": rejected_count,
        "new_relationships_formed": len(new_relationships),
        "new_relationships": new_relationships,
    }
