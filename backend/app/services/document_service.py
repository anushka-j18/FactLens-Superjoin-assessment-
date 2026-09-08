import hashlib
import os
import uuid
from typing import Tuple, Optional, List
from sqlalchemy.orm import Session
from app.models.entities import Document
from app.services.pdf_parser import PdfParserService, PdfParserError

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB limit
STORAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "storage", "uploads")


class DocumentServiceError(Exception):
    pass


class DuplicateDocumentError(DocumentServiceError):
    def __init__(self, existing_document: Document):
        self.existing_document = existing_document
        super().__init__(f"Duplicate document detected (Hash: {existing_document.file_hash}). Document ID: {existing_document.id}")


class DocumentService:
    """Manages document upload, validation, storage, and database lifecycle."""

    @staticmethod
    def ensure_storage_dir():
        """Ensure storage directory exists."""
        os.makedirs(STORAGE_DIR, exist_ok=True)

    @classmethod
    def process_pdf_upload(cls, db: Session, file_bytes: bytes, original_filename: str) -> Document:
        """Validate, store, and create DB record for an uploaded PDF file."""
        cls.ensure_storage_dir()

        # 1. Validate file extension and size
        if not original_filename.lower().endswith(".pdf"):
            raise DocumentServiceError("Invalid file extension: Only PDF files (.pdf) are accepted.")

        file_size = len(file_bytes)
        if file_size > MAX_FILE_SIZE:
            raise DocumentServiceError(f"File size exceeds maximum limit of {MAX_FILE_SIZE // (1024 * 1024)}MB.")

        # 2. Compute SHA-256 hash for duplicate check
        file_hash = hashlib.sha256(file_bytes).hexdigest()

        # 3. Check for existing duplicate document in DB
        existing_doc = db.query(Document).filter(Document.file_hash == file_hash).first()
        if existing_doc:
            raise DuplicateDocumentError(existing_doc)

        # 4. Validate PDF structure via PyMuPDF
        fitz_doc = PdfParserService.validate_and_open(file_bytes)

        # 5. Save file to disk with unique UUID filename
        doc_id = str(uuid.uuid4())
        stored_filename = f"{doc_id}.pdf"
        file_path = os.path.join(STORAGE_DIR, stored_filename)

        with open(file_path, "wb") as f:
            f.write(file_bytes)

        # 6. Create Document record in DB with 'uploaded' status
        doc_record = Document(
            id=doc_id,
            filename=stored_filename,
            original_filename=original_filename,
            file_size=file_size,
            file_hash=file_hash,
            page_count=fitz_doc.page_count,
            processing_status="uploaded",
        )
        db.add(doc_record)
        db.commit()
        db.refresh(doc_record)

        return doc_record

    @staticmethod
    def get_document_by_id(db: Session, document_id: str) -> Optional[Document]:
        """Fetch single document by UUID."""
        return db.query(Document).filter(Document.id == document_id).first()

    @staticmethod
    def list_documents(db: Session, skip: int = 0, limit: int = 50) -> Tuple[int, List[Document]]:
        """List documents sorted by created_at descending."""
        query = db.query(Document)
        total = query.count()
        documents = query.order_by(Document.created_at.desc()).offset(skip).limit(limit).all()
        return total, documents

    @staticmethod
    def update_status(db: Session, document_id: str, status: str, error_message: Optional[str] = None):
        """Update processing status of a document."""
        doc = db.query(Document).filter(Document.id == document_id).first()
        if doc:
            doc.processing_status = status
            if error_message:
                doc.error_message = error_message
            db.commit()
            db.refresh(doc)
