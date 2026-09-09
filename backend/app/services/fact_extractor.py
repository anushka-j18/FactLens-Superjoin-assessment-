import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session

from app.models.entities import Document, EvidenceUnit, Fact, ExtractionRun
from app.services.normalizer import FactNormalizer
from app.services.llm import get_llm_provider, LLMProvider
from app.services.llm.mock import MockProviderError


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
        provider_name = provider.__class__.__name__

        # Initialize ExtractionRun record
        run = ExtractionRun(
            document_id=document_id,
            status="processing",
            provider=provider_name,
            started_at=datetime.now(timezone.utc),
        )
        db.add(run)
        db.commit()

        # Retrieve evidence units for document
        evidence_units = (
            db.query(EvidenceUnit)
            .filter(EvidenceUnit.document_id == document_id)
            .order_by(EvidenceUnit.page_number.asc())
            .all()
        )

        if not evidence_units:
            run.status = "failed"
            run.error_message = "No evidence units found for document."
            run.completed_at = datetime.now(timezone.utc)
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
                            "evidence_ids": {"type": "array", "items": {"type": "string"}},
                            "subject": {"type": "string"},
                            "predicate": {"type": "string"},
                            "value": {"type": "string"},
                            "value_type": {"type": "string"},
                            "unit": {"type": "string"},
                            "currency": {"type": "string"},
                            "temporal_context": {"type": "string"},
                            "geographic_scope": {"type": "string"},
                            "operating_scope": {"type": "string"},
                            "qualifiers": {"type": "object"},
                            "verbatim_quote": {"type": "string"},
                            "is_inferred": {"type": "boolean"},
                            "extraction_confidence": {"type": "number"},
                        },
                        "required": ["subject", "predicate", "value", "verbatim_quote"],
                    }
                }
            }
        }

        try:
            # Delete any existing facts for re-extraction idempotency
            db.query(Fact).filter(Fact.document_id == document_id).delete()
            db.commit()

            # Execute LLM structured extraction
            try:
                raw_result = provider.generate_structured(prompt, schema)
            except MockProviderError as mpe:
                msg = str(mpe)
                run.status = "failed"
                run.error_message = msg
                run.completed_at = datetime.now(timezone.utc)
                doc.extraction_status = "mock_configured"
                doc.error_message = msg
                db.commit()
                return "mock_configured", [], 0
            except Exception as llm_err:
                msg = f"Extraction failure [malformed_llm_output]: {str(llm_err)}"
                run.status = "failed"
                run.error_message = msg
                run.completed_at = datetime.now(timezone.utc)
                doc.extraction_status = "failed"
                doc.error_message = msg
                db.commit()
                return "failed", [], 0

            candidate_facts = raw_result.get("facts", [])
            if not candidate_facts:
                run.status = "completed"
                run.facts_created = 0
                run.completed_at = datetime.now(timezone.utc)
                doc.extraction_status = "no_facts_found"
                doc.error_message = "Extraction status [no_meaningful_facts]: No structural facts were identified by LLM."
                db.commit()
                return "no_facts_found", [], 0

            valid_facts: List[Fact] = []
            rejected_count = 0
            rejection_details = []

            for cf in candidate_facts:
                # Handle evidence_id vs evidence_ids
                ev_ids = cf.get("evidence_ids") or []
                if not ev_ids and cf.get("evidence_id"):
                    ev_ids = [cf["evidence_id"]]

                verbatim_quote = cf.get("verbatim_quote", "").strip()

                # Filter valid evidence unit objects
                valid_units = [evidence_map[eid] for eid in ev_ids if eid in evidence_map]

                # Rule 1: Validate evidence_id existence in backend
                if not valid_units:
                    rejected_count += 1
                    rejection_details.append("invalid_evidence_id")
                    continue

                primary_unit = valid_units[0]

                # Rule 2: Validate verbatim_quote grounding in source text
                is_grounded = any(
                    cls._is_quote_grounded(verbatim_quote, u.clean_text, u.raw_text)
                    for u in valid_units
                )
                if not verbatim_quote or not is_grounded:
                    rejected_count += 1
                    rejection_details.append("unsupported_claim")
                    continue

                # Rule 3: Deterministic value & context normalization
                raw_val = str(cf.get("value", "")).strip()
                norm_num, scale_unit = FactNormalizer.normalize_number(raw_val)
                currency = cf.get("currency") or FactNormalizer.normalize_currency(raw_val)
                unit = FactNormalizer.normalize_unit(cf.get("unit"), cf.get("predicate", ""))
                
                temp_dict = FactNormalizer.normalize_temporal_context(cf.get("temporal_context"))
                canonical_temp = temp_dict["canonical"] or cf.get("temporal_context")

                confidence = float(cf.get("extraction_confidence", 1.0))
                if confidence >= 0.85:
                    conf_level = "HIGH"
                elif confidence >= 0.60:
                    conf_level = "MEDIUM"
                else:
                    conf_level = "LOW"

                is_inferred = bool(cf.get("is_inferred", False))
                needs_review = conf_level == "LOW" or is_inferred

                fact_obj = Fact(
                    document_id=document_id,
                    knowledge_layer_id=doc.knowledge_layer_id,
                    evidence_id=primary_unit.id,
                    evidence_ids=[u.id for u in valid_units],
                    page_number=primary_unit.page_number,
                    subject=str(cf.get("subject", "General")).strip(),
                    predicate=str(cf.get("predicate", "fact")).strip(),
                    value=raw_val,
                    normalized_value=norm_num,
                    value_type=str(cf.get("value_type", "text")).strip(),
                    unit=unit,
                    currency=currency,
                    temporal_context=canonical_temp,
                    geographic_scope=cf.get("geographic_scope"),
                    operating_scope=cf.get("operating_scope"),
                    qualifiers=cf.get("qualifiers", {}),
                    verbatim_quote=verbatim_quote,
                    is_inferred=is_inferred,
                    extraction_confidence=confidence,
                    confidence_level=conf_level,
                    needs_review=needs_review,
                    extraction_status="grounded",
                )
                db.add(fact_obj)
                valid_facts.append(fact_obj)

            if rejected_count > 0 and valid_facts:
                doc.extraction_status = "partially_processed"
                doc.error_message = f"Extracted {len(valid_facts)} valid facts; rejected {rejected_count} ({', '.join(set(rejection_details))})."
            elif rejected_count > 0 and not valid_facts:
                doc.extraction_status = "completed"
                doc.error_message = f"Extraction completed: 0 valid facts extracted; rejected {rejected_count} ({', '.join(set(rejection_details))})."
            else:
                doc.extraction_status = "completed"
                doc.error_message = None

            run.status = "completed" if valid_facts else "no_facts_found"
            run.facts_created = len(valid_facts)
            run.rejected_facts = rejected_count
            run.completed_at = datetime.now(timezone.utc)

            db.commit()

            for f in valid_facts:
                db.refresh(f)

            return doc.extraction_status, valid_facts, rejected_count

        except Exception as e:
            db.rollback()
            run.status = "failed"
            run.error_message = str(e)
            run.completed_at = datetime.now(timezone.utc)
            doc.extraction_status = "failed"
            doc.error_message = str(e)
            db.commit()
            return "failed", [], 0

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
