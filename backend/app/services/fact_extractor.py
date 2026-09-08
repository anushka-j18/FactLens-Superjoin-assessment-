import re
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session

from app.models.entities import Document, EvidenceUnit, Fact
from app.services.llm import get_llm_provider, LLMProvider


class FactExtractorError(Exception):
    pass


class FactExtractorService:
    """Service responsible for extracting grounded facts and validating provenance."""

    @classmethod
    def extract_facts_from_document(
        cls,
        db: Session,
        document_id: str,
        llm_provider: Optional[LLMProvider] = None
    ) -> Tuple[str, List[Fact], int]:
        """Extract grounded facts from document evidence units and validate provenance.
        
        Returns:
            Tuple of (extraction_status, list_of_valid_facts, count_of_rejected_facts)
        """
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            raise FactExtractorError(f"Document with ID '{document_id}' not found.")

        # Update document extraction_status
        doc.extraction_status = "extracting"
        db.commit()

        provider = llm_provider or get_llm_provider()

        # Retrieve evidence units for document
        evidence_units = (
            db.query(EvidenceUnit)
            .filter(EvidenceUnit.document_id == document_id)
            .order_by(EvidenceUnit.page_number.asc())
            .all()
        )

        if not evidence_units:
            doc.extraction_status = "failed"
            doc.error_message = "No evidence units found for document."
            db.commit()
            raise FactExtractorError("Cannot extract facts: Document has no evidence units.")

        # Build map of valid evidence IDs to EvidenceUnit objects
        evidence_map: Dict[str, EvidenceUnit] = {eu.id: eu for eu in evidence_units}

        # Build prompt containing evidence chunks with explicit IDs
        prompt_parts = [
            "Extract structured facts supported by the following source evidence.",
            "IMPORTANT RULES:",
            "1. You MUST select a valid EVIDENCE_ID from the list below.",
            "2. You MUST include a verbatim_quote string extracted EXACTLY from the text.",
            "3. Do NOT invent missing values or page numbers.",
            "\nSOURCE EVIDENCE:\n"
        ]

        for eu in evidence_units:
            prompt_parts.append(f"EVIDENCE_ID: {eu.id}\nPAGE: {eu.page_number}\nTEXT:\n{eu.clean_text}\n")

        prompt = "\n".join(prompt_parts)

        # JSON schema hint
        schema = {
            "type": "object",
            "properties": {
                "facts": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "evidence_id": {"type": "string"},
                            "subject": {"type": "string"},
                            "predicate": {"type": "string"},
                            "value": {"type": "string"},
                            "value_type": {"type": "string"},
                            "unit": {"type": "string"},
                            "temporal_context": {"type": "string"},
                            "geographic_scope": {"type": "string"},
                            "qualifiers": {"type": "object"},
                            "verbatim_quote": {"type": "string"},
                            "is_inferred": {"type": "boolean"},
                            "extraction_confidence": {"type": "number"},
                        },
                        "required": ["evidence_id", "subject", "predicate", "value", "verbatim_quote"],
                    }
                }
            }
        }

        try:
            # Delete any existing facts for re-extraction
            db.query(Fact).filter(Fact.document_id == document_id).delete()
            db.commit()

            # Execute LLM structured extraction
            raw_result = provider.generate_structured(prompt, schema)
            candidate_facts = raw_result.get("facts", [])

            valid_facts: List[Fact] = []
            rejected_count = 0

            for cf in candidate_facts:
                ev_id = cf.get("evidence_id")
                verbatim_quote = cf.get("verbatim_quote", "").strip()

                # Rule 1: Validate evidence_id existence in backend
                if not ev_id or ev_id not in evidence_map:
                    rejected_count += 1
                    continue

                target_unit = evidence_map[ev_id]

                # Rule 2: Validate verbatim_quote grounding in source text
                if not verbatim_quote or not cls._is_quote_grounded(verbatim_quote, target_unit.clean_text, target_unit.raw_text):
                    rejected_count += 1
                    continue

                # Rule 3: Deterministic value normalization
                raw_val = str(cf.get("value", "")).strip()
                norm_val = cls.normalize_numeric_value(raw_val)

                fact_obj = Fact(
                    document_id=document_id,
                    evidence_id=target_unit.id,
                    page_number=target_unit.page_number,
                    subject=str(cf.get("subject", "General")).strip(),
                    predicate=str(cf.get("predicate", "fact")).strip(),
                    value=raw_val,
                    normalized_value=norm_val,
                    value_type=str(cf.get("value_type", "text")).strip(),
                    unit=cf.get("unit"),
                    temporal_context=cf.get("temporal_context"),
                    geographic_scope=cf.get("geographic_scope"),
                    qualifiers=cf.get("qualifiers", {}),
                    verbatim_quote=verbatim_quote,
                    is_inferred=bool(cf.get("is_inferred", False)),
                    extraction_confidence=float(cf.get("extraction_confidence", 1.0)),
                    extraction_status="grounded",
                )
                db.add(fact_obj)
                valid_facts.append(fact_obj)

            doc.extraction_status = "completed"
            db.commit()

            for f in valid_facts:
                db.refresh(f)

            return "completed", valid_facts, rejected_count

        except Exception as e:
            db.rollback()
            doc.extraction_status = "failed"
            doc.error_message = str(e)
            db.commit()
            raise FactExtractorError(f"Fact extraction failed: {str(e)}")

    @staticmethod
    def _is_quote_grounded(quote: str, clean_text: str, raw_text: str) -> bool:
        """Deterministically verify that verbatim quote exists in evidence text."""
        quote_clean = quote.lower().strip()
        if quote_clean in clean_text.lower() or quote_clean in raw_text.lower():
            return True
        
        # Substring / partial word match fallback
        tokens = [t for t in quote_clean.split() if len(t) > 2]
        if not tokens:
            return False
            
        matched = sum(1 for t in tokens if t in clean_text.lower())
        return (matched / len(tokens)) >= 0.85

    @staticmethod
    def normalize_numeric_value(value_str: str) -> Optional[float]:
        """Deterministically convert raw numeric string into a float value.
        
        Handles:
        - Currency symbols (₹, $, €, £)
        - Indian numbering (Cr/Crore, Lakh)
        - Western scales (million, billion, trillion)
        - Percentages (14% -> 0.14)
        """
        if not value_str:
            return None

        clean_s = value_str.replace(",", "").strip()

        # Handle percentage (e.g. "14%", "5.4%")
        pct_match = re.search(r'([\d\.]+)\s*%', clean_s)
        if pct_match:
            try:
                return round(float(pct_match.group(1)) / 100.0, 6)
            except ValueError:
                pass

        # Handle Indian & Western scaled amounts
        # e.g., ₹4,600 Cr -> 46000000000.0
        # e.g., $12.4 million -> 12400000.0
        scale_multipliers = {
            "cr": 10_000_000.0,
            "crore": 10_000_000.0,
            "crores": 10_000_000.0,
            "lakh": 100_000.0,
            "lakhs": 100_000.0,
            "k": 1_000.0,
            "m": 1_000_000.0,
            "million": 1_000_000.0,
            "b": 1_000_000_000.0,
            "billion": 1_000_000_000.0,
            "t": 1_000_000_000_000.0,
            "trillion": 1_000_000_000_000.0,
        }

        match = re.search(r'([\d\.]+)\s*([a-zA-Z]+)?', clean_s)
        if match:
            try:
                base_num = float(match.group(1))
                unit_str = match.group(2).lower() if match.group(2) else ""
                multiplier = scale_multipliers.get(unit_str, 1.0)
                return base_num * multiplier
            except (ValueError, TypeError):
                pass

        return None
