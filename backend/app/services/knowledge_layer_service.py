import uuid
from datetime import datetime, timezone
from typing import List, Tuple, Optional
from sqlalchemy.orm import Session
from app.models.entities import KnowledgeLayer, Document
from app.services.document_service import DocumentService, DuplicateDocumentError, DocumentServiceError
from app.services.evidence_service import EvidenceService
from app.services.pdf_parser import PdfParserError


class KnowledgeLayerNotFoundError(Exception):
    def __init__(self, kl_id: str):
        super().__init__(f"Knowledge layer with ID '{kl_id}' not found.")


class KnowledgeLayerService:
    """Manages knowledge layers, multi-document batch uploads, and DB lifecycle."""

    @staticmethod
    def create_knowledge_layer(db: Session, name: str, description: Optional[str] = None) -> KnowledgeLayer:
        """Create a new knowledge layer."""
        kl = KnowledgeLayer(
            id=str(uuid.uuid4()),
            name=name.strip(),
            description=description.strip() if description else None,
        )
        db.add(kl)
        db.commit()
        db.refresh(kl)
        return kl

    @staticmethod
    def get_knowledge_layer(db: Session, kl_id: str) -> Optional[KnowledgeLayer]:
        """Fetch single knowledge layer by ID."""
        return db.query(KnowledgeLayer).filter(KnowledgeLayer.id == kl_id).first()

    @staticmethod
    def list_knowledge_layers(db: Session, skip: int = 0, limit: int = 50) -> Tuple[int, List[KnowledgeLayer]]:
        """List knowledge layers ordered by created_at descending."""
        query = db.query(KnowledgeLayer)
        total = query.count()
        kls = query.order_by(KnowledgeLayer.created_at.desc()).offset(skip).limit(limit).all()
        return total, kls

    @staticmethod
    def delete_knowledge_layer(db: Session, kl_id: str) -> bool:
        """Delete a knowledge layer and cascade delete its documents and evidence."""
        kl = db.query(KnowledgeLayer).filter(KnowledgeLayer.id == kl_id).first()
        if not kl:
            return False
        db.delete(kl)
        db.commit()
        return True

    @classmethod
    def upload_and_process_documents(
        cls,
        db: Session,
        kl_id: str,
        files_data: List[Tuple[bytes, str]]
    ) -> List[Document]:
        """Upload and process multiple PDF files into a knowledge layer independently.
        
        If processing fails for one PDF, it records the failure on that document, while 
        allowing other PDFs in the batch to process and complete successfully.
        """
        kl = cls.get_knowledge_layer(db, kl_id)
        if not kl:
            raise KnowledgeLayerNotFoundError(kl_id)

        processed_docs: List[Document] = []

        for file_bytes, filename in files_data:
            try:
                # 1. Process upload & create DB document record
                doc = DocumentService.process_pdf_upload(
                    db=db,
                    file_bytes=file_bytes,
                    original_filename=filename,
                    knowledge_layer_id=kl_id,
                )

                # 2. Extract page-by-page evidence
                try:
                    EvidenceService.ingest_and_extract_evidence(db=db, document=doc)
                except Exception as ext_err:
                    # Individual evidence extraction failure
                    DocumentService.update_status(db, doc.id, "failed", str(ext_err))

                db.refresh(doc)
                processed_docs.append(doc)

            except DuplicateDocumentError as dup_err:
                # Retain existing duplicate document in response
                processed_docs.append(dup_err.existing_document)

            except (DocumentServiceError, PdfParserError) as doc_err:
                # Validation error prior to document record creation
                failed_doc = Document(
                    id=str(uuid.uuid4()),
                    knowledge_layer_id=kl_id,
                    filename=f"failed_{uuid.uuid4().hex[:8]}.pdf",
                    original_filename=filename,
                    file_size=len(file_bytes),
                    file_hash="",
                    page_count=0,
                    processing_status="failed",
                    error_message=str(doc_err),
                )
                db.add(failed_doc)
                db.commit()
                db.refresh(failed_doc)
                processed_docs.append(failed_doc)

        return processed_docs
