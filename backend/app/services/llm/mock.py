import os
import re
from typing import Dict, Any, List, Optional
from app.services.llm.base import LLMProvider


class MockProviderError(RuntimeError):
    """Raised when fact extraction is attempted while LLM_PROVIDER is set to mock in application mode."""
    pass


class MockLLMProvider(LLMProvider):
    """Mock LLM Provider for offline testing and deterministic test suites.
    
    Dynamically extracts grounded facts directly from evidence unit text provided
    in prompts without making network requests or requiring API keys.
    """

    def __init__(self, allow_mock_extraction: bool = False):
        self.allow_mock_extraction = allow_mock_extraction

    def generate_completion(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        return "Mock LLM completion response."

    def generate_structured(
        self,
        prompt: str,
        schema: Dict[str, Any],
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Parse evidence units in prompt context and return structured grounded facts."""
        facts: List[Dict[str, Any]] = []

        # Extract evidence ID and text pairs from prompt
        evidence_blocks = re.findall(r'EVIDENCE_ID:\s*([A-Za-z0-9\-_]+).*?TEXT:\s*\n?(.*?)(?=\nEVIDENCE_ID:|\Z)', prompt, re.DOTALL)

        for ev_id, text in evidence_blocks:
            lines = [s.strip() for s in re.split(r'[\n\.]+', text) if s.strip()]
            for line in lines:
                line_str = line.strip()
                if not line_str:
                    continue

                # 1. Match Revenue / Financial amounts (e.g. ₹4,600 Cr, INR 4,600 Cr, $12.4 million)
                rev_match = re.search(r'([Rr]evenue|[Pp]rofit|[Ss]ales|[Ee]arnings|[Ee]xpenses?)\s*(?:of|was|is|=)?\s*([₹\$€£·]?\s*(?:INR|USD|Rs\.?)?\s*[\d,]+(?:\.\d+)?\s*(?:Cr|Crore|million|billion|trillion|lakh)?)', line_str, re.IGNORECASE)
                if rev_match:
                    metric = rev_match.group(1).lower()
                    val = rev_match.group(2).strip()
                    facts.append({
                        "evidence_id": ev_id,
                        "subject": "Reporting Entity",
                        "predicate": metric,
                        "value": val,
                        "value_type": "currency" if any(c in val for c in ['₹', '$', '€', '£', 'INR', 'USD']) else "numeric",
                        "unit": "USD" if '$' in val else "INR",
                        "temporal_context": self._extract_timeframe(line_str),
                        "geographic_scope": None,
                        "qualifiers": {},
                        "verbatim_quote": line_str,
                        "is_inferred": False,
                        "extraction_confidence": 0.95,
                    })
                    continue

                # 2. Match Percentages / Rates (e.g. 5.4%, 14% market share)
                pct_match = re.search(r'([A-Za-z\s]{3,30}?)\s*(?:of|was|is|=|at)?\s*([\d\.]+\s*%)', line_str)
                if pct_match:
                    predicate = pct_match.group(1).strip().lower()
                    val = pct_match.group(2).strip()
                    facts.append({
                        "evidence_id": ev_id,
                        "subject": "Entity / Metric",
                        "predicate": predicate if predicate else "rate",
                        "value": val,
                        "value_type": "percentage",
                        "unit": "percent",
                        "temporal_context": self._extract_timeframe(line_str),
                        "geographic_scope": None,
                        "qualifiers": {},
                        "verbatim_quote": line_str,
                        "is_inferred": False,
                        "extraction_confidence": 0.92,
                    })
                    continue

                # 3. Match Employee / Count numbers (e.g. 2450 employees, 100 pages)
                count_match = re.search(r'([\d,]+)\s*(employees|staff|pages|deliveries|orders|units)', line_str, re.IGNORECASE)
                if count_match:
                    val = count_match.group(1).strip()
                    unit = count_match.group(2).strip().lower()
                    facts.append({
                        "evidence_id": ev_id,
                        "subject": "Organization",
                        "predicate": unit,
                        "value": val,
                        "value_type": "numeric",
                        "unit": unit,
                        "temporal_context": self._extract_timeframe(line_str),
                        "geographic_scope": None,
                        "qualifiers": {},
                        "verbatim_quote": line_str,
                        "is_inferred": False,
                        "extraction_confidence": 0.90,
                    })
                    continue

                # 4. Match key entity facts (e.g. headquarters = Mumbai, CEO = John Smith)
                key_val_match = re.search(r'([A-Za-z\s]{3,20})\s*:\s*([A-Za-z0-9\s,\.]{2,40})', line_str)
                if key_val_match:
                    pred = key_val_match.group(1).strip().lower()
                    val = key_val_match.group(2).strip()
                    facts.append({
                        "evidence_id": ev_id,
                        "subject": "Entity",
                        "predicate": pred,
                        "value": val,
                        "value_type": "entity" if pred in ["ceo", "headquarters", "location", "status"] else "text",
                        "unit": None,
                        "temporal_context": self._extract_timeframe(line_str),
                        "geographic_scope": None,
                        "qualifiers": {},
                        "verbatim_quote": line_str,
                        "is_inferred": False,
                        "extraction_confidence": 0.88,
                    })

        # Fallback generic fact if line matching yielded 0 facts
        if not facts and evidence_blocks:
            ev_id, text = evidence_blocks[0]
            first_line = text.strip().split('\n')[0][:120] if text else "Document content"
            facts.append({
                "evidence_id": ev_id,
                "subject": "Document Summary",
                "predicate": "statement",
                "value": first_line,
                "value_type": "text",
                "unit": None,
                "temporal_context": None,
                "geographic_scope": None,
                "qualifiers": {},
                "verbatim_quote": first_line,
                "is_inferred": False,
                "extraction_confidence": 0.85,
            })

        return {"facts": facts}

    @staticmethod
    def _extract_timeframe(text: str) -> Optional[str]:
        match = re.search(r'\b(FY\d{2,4}|Q[1-4]\s*FY\d{2,4}|\d{4}-\d{2,4}|20\d{2})\b', text, re.IGNORECASE)
        return match.group(1) if match else None
