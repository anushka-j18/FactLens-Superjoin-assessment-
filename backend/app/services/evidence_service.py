import os
from typing import List
from sqlalchemy.orm import Session
import pymupdf as fitz
from app.models.entities import Document, EvidenceUnit
from app.services.pdf_parser import PdfParserService
from app.services.document_service import STORAGE_DIR, DocumentService


class EvidenceService:
    """Service responsible for extracting page evidence units and persisting provenance."""

    @classmethod
    def ingest_and_extract_evidence(cls, db: Session, document: Document) -> List[EvidenceUnit]:
        """Parse PDF document from storage, extract evidence units per page, and save to DB."""
        file_path = os.path.join(STORAGE_DIR, document.filename)
        
        if not os.path.exists(file_path):
            DocumentService.update_status(db, document.id, "failed", f"File not found on disk: {file_path}")
            raise FileNotFoundError(f"PDF file not found on disk: {file_path}")

        try:
            # Update status to processing
            DocumentService.update_status(db, document.id, "processing")

            # Open PDF with PyMuPDF
            with open(file_path, "rb") as f:
                file_bytes = f.read()

            fitz_doc = PdfParserService.validate_and_open(file_bytes)
            page_count, pages_data = PdfParserService.parse_document(fitz_doc)

            evidence_units = []
            for p_data in pages_data:
                unit = EvidenceUnit(
                    document_id=document.id,
                    page_number=p_data["page_number"],
                    raw_text=p_data["raw_text"],
                    clean_text=p_data["clean_text"],
                    location_metadata=p_data["location_metadata"],
                )
                db.add(unit)
                evidence_units.append(unit)

            # Update document page count and set status to completed
            document.page_count = page_count
            document.processing_status = "completed"
            db.commit()
            
            for u in evidence_units:
                db.refresh(u)

            return evidence_units

        except Exception as e:
            db.rollback()
            DocumentService.update_status(db, document.id, "failed", str(e))
            raise e

    @staticmethod
    def get_evidence_by_document(db: Session, document_id: str) -> List[EvidenceUnit]:
        """Retrieve all evidence units (pages) for a document ordered by page_number."""
        return (
            db.query(EvidenceUnit)
            .filter(EvidenceUnit.document_id == document_id)
            .order_by(EvidenceUnit.page_number.asc())
            .all()
        )
