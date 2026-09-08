import re
import pymupdf as fitz
from typing import List, Dict, Any, Tuple


class PdfParserError(Exception):
    """Custom exception raised when PDF parsing fails."""
    pass


class PdfParserService:
    """Deterministic PDF parsing service using PyMuPDF (fitz).
    
    Responsible for extracting verbatim page text, preserving page boundaries,
    and capturing block-level bounding boxes for exact source provenance.
    """

    @staticmethod
    def validate_and_open(file_bytes: bytes) -> fitz.Document:
        """Validate PDF file header, structure, and readability."""
        if not file_bytes:
            raise PdfParserError("File is empty (0 bytes).")
            
        if not file_bytes.startswith(b"%PDF"):
            raise PdfParserError("Invalid file header: File is not a valid PDF document.")
            
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
        except Exception as e:
            raise PdfParserError(f"Corrupt or unreadable PDF document: {str(e)}")
            
        if doc.is_encrypted:
            # Try opening with empty password if encrypted
            if not doc.authenticate(""):
                raise PdfParserError("PDF is password protected or encrypted.")

        if doc.page_count == 0:
            raise PdfParserError("PDF contains 0 pages.")

        return doc

    @classmethod
    def parse_document(cls, doc: fitz.Document) -> Tuple[int, List[Dict[str, Any]]]:
        """Extract text and location metadata page-by-page from a fitz Document."""
        page_count = doc.page_count
        pages_data = []

        for page_idx in range(page_count):
            page = doc.load_page(page_idx)
            page_num = page_idx + 1  # 1-indexed page numbering
            
            # Extract raw verbatim text
            raw_text = page.get_text("text") or ""
            
            # Clean text artifact normalization while preserving verbatim quotes
            clean_text = cls.normalize_text_artifacts(raw_text)
            
            # Extract block-level layout coordinates
            # page.get_text("blocks") returns list of tuples: (x0, y0, x1, y1, "text", block_no, block_type)
            blocks_raw = page.get_text("blocks") or []
            blocks_metadata = []
            
            for b in blocks_raw:
                if len(b) >= 7 and b[6] == 0:  # block_type 0 = text block
                    blocks_metadata.append({
                        "bbox": [round(b[0], 2), round(b[1], 2), round(b[2], 2), round(b[3], 2)],
                        "block_no": b[5],
                        "text_snippet": b[4].strip()[:100],  # preview
                    })
                    
            rect = page.rect
            location_metadata = {
                "page_width": round(rect.width, 2),
                "page_height": round(rect.height, 2),
                "block_count": len(blocks_metadata),
                "blocks": blocks_metadata,
            }

            pages_data.append({
                "page_number": page_num,
                "raw_text": raw_text,
                "clean_text": clean_text,
                "location_metadata": location_metadata,
            })

        return page_count, pages_data

    @staticmethod
    def normalize_text_artifacts(text: str) -> str:
        """Normalize minor extraction artifacts (e.g. null bytes, hyphen split words).
        
        Preserves original verbatim words while cleaning formatting glitches.
        """
        if not text:
            return ""
            
        # Strip null bytes
        cleaned = text.replace("\x00", "")
        
        # Replace non-breaking spaces with standard space
        cleaned = cleaned.replace("\xa0", " ")
        
        # De-hyphenate line breaks (e.g., "infor-\nmation" -> "information")
        cleaned = re.sub(r'(\w+)-\n(\w+)', r'\1\2', cleaned)
        
        # Collapse multiple horizontal spaces
        cleaned = re.sub(r'[ \t]+', ' ', cleaned)
        
        # Collapse 3+ newlines into double newline
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        
        return cleaned.strip()
