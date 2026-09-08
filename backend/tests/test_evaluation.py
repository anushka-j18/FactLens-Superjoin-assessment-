import io
import pytest
import pymupdf as fitz

from app.models.entities import Document, EvidenceUnit, Fact, FactRelationship
from app.services.fact_extractor import FactExtractorService
from app.services.relationship_reasoner import RelationshipReasonerService
from app.services.llm import LLMProvider


def create_sample_pdf(text_content: str) -> bytes:
    """Helper to generate PDF bytes with custom text content."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), text_content)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


class MalformedLLMProvider(LLMProvider):
    """Mock LLM provider that simulates malformed JSON output."""
    def generate_completion(self, prompt: str, system_prompt=None) -> str:
        return "Not valid JSON {"

    def generate_structured(self, prompt: str, schema: dict, system_prompt=None) -> dict:
        raise ValueError("Malformed LLM response format.")


class UngroundedQuoteLLMProvider(LLMProvider):
    """Mock LLM provider returning ungrounded quote and invalid evidence ID."""
    def generate_completion(self, prompt: str, system_prompt=None) -> str:
        return ""

    def generate_structured(self, prompt: str, schema: dict, system_prompt=None) -> dict:
        return {
            "facts": [
                {
                    "evidence_id": "invalid-evidence-id-123",
                    "subject": "Delhivery",
                    "predicate": "revenue",
                    "value": "INR 9,999 Cr",
                    "verbatim_quote": "Fabricated quote that does not exist",
                    "extraction_confidence": 0.90,
                }
            ]
        }


def test_eval_case_1_corroboration(client):
    """Evaluation Fixture Case 1: Equivalent facts across documents -> CORROBORATED."""
    text1 = "Delhivery reported FY24 Revenue of INR 4,600 Cr."
    text2 = "Delhivery reported FY24 Revenue of INR 4,600 Cr."

    res1 = client.post("/api/documents", files={"file": ("eval_doc_1.pdf", io.BytesIO(create_sample_pdf(text1)), "application/pdf")})
    res2 = client.post("/api/documents", files={"file": ("eval_doc_2.pdf", io.BytesIO(create_sample_pdf(text2)), "application/pdf")})

    d1_id = res1.json()["id"]
    d2_id = res2.json()["id"]

    client.post(f"/api/documents/{d1_id}/extract")
    client.post(f"/api/documents/{d2_id}/extract")

    an_res = client.post("/api/relationships/analyze", json={"document_ids": [d1_id, d2_id]})
    assert an_res.status_code == 200
    rels = an_res.json()["relationships"]
    corroborated = [r for r in rels if r["relationship_type"] == "CORROBORATED"]
    assert len(corroborated) >= 1
    assert corroborated[0]["confidence_level"] == "HIGH"
    assert corroborated[0]["needs_review"] is False


def test_eval_case_2_contradiction(client):
    """Evaluation Fixture Case 2: Conflicting numbers for exact same timeframe -> CONTRADICTED."""
    text1 = "Delhivery FY24 Net Profit was INR 100 Cr."
    text2 = "Delhivery FY24 Net Profit was INR 250 Cr."

    res1 = client.post("/api/documents", files={"file": ("eval_doc_3.pdf", io.BytesIO(create_sample_pdf(text1)), "application/pdf")})
    res2 = client.post("/api/documents", files={"file": ("eval_doc_4.pdf", io.BytesIO(create_sample_pdf(text2)), "application/pdf")})

    d1_id = res1.json()["id"]
    d2_id = res2.json()["id"]

    client.post(f"/api/documents/{d1_id}/extract")
    client.post(f"/api/documents/{d2_id}/extract")

    an_res = client.post("/api/relationships/analyze", json={"document_ids": [d1_id, d2_id]})
    assert an_res.status_code == 200
    rels = an_res.json()["relationships"]
    contradicted = [r for r in rels if r["relationship_type"] == "CONTRADICTED"]
    assert len(contradicted) >= 1
    assert contradicted[0]["confidence_level"] == "HIGH"
    assert contradicted[0]["needs_review"] is False


def test_eval_case_3_contextual_reconciliation(client):
    """Evaluation Fixture Case 3: Surface discrepancy resolved by timeframe difference -> CONTEXTUALLY_RECONCILED."""
    text1 = "Delhivery reported FY22 Revenue of INR 3,800 Cr."
    text2 = "Delhivery reported FY24 Revenue of INR 4,600 Cr."

    res1 = client.post("/api/documents", files={"file": ("eval_doc_5.pdf", io.BytesIO(create_sample_pdf(text1)), "application/pdf")})
    res2 = client.post("/api/documents", files={"file": ("eval_doc_6.pdf", io.BytesIO(create_sample_pdf(text2)), "application/pdf")})

    d1_id = res1.json()["id"]
    d2_id = res2.json()["id"]

    client.post(f"/api/documents/{d1_id}/extract")
    client.post(f"/api/documents/{d2_id}/extract")

    an_res = client.post("/api/relationships/analyze", json={"document_ids": [d1_id, d2_id]})
    assert an_res.status_code == 200
    rels = an_res.json()["relationships"]
    reconciled = [r for r in rels if r["relationship_type"] == "CONTEXTUALLY_RECONCILED"]
    assert len(reconciled) >= 1
    assert reconciled[0]["confidence_level"] == "HIGH"


def test_eval_case_4_extraction_and_reasoning_failure(client, db_session):
    """Evaluation Fixture Case 4: Malformed output and ungrounded claims result in honest failure status."""
    text = "Delhivery operating updates FY24."
    res = client.post("/api/documents", files={"file": ("eval_fail.pdf", io.BytesIO(create_sample_pdf(text)), "application/pdf")})
    doc_id = res.json()["id"]

    # Test malformed LLM provider
    status_res, facts, rejected = FactExtractorService.extract_facts_from_document(
        db=db_session,
        document_id=doc_id,
        llm_provider=MalformedLLMProvider()
    )
    assert status_res == "failed"
    assert len(facts) == 0

    doc_in_db = db_session.query(Document).filter(Document.id == doc_id).first()
    assert doc_in_db.extraction_status == "failed"
    assert "malformed_llm_output" in doc_in_db.error_message

    # Test ungrounded quote / invalid evidence ID provider
    status_res2, facts2, rejected2 = FactExtractorService.extract_facts_from_document(
        db=db_session,
        document_id=doc_id,
        llm_provider=UngroundedQuoteLLMProvider()
    )
    assert status_res2 == "completed"
    assert len(facts2) == 0
    assert rejected2 == 1


def test_evaluation_metrics_endpoint(client):
    """Test GET /api/evaluation/metrics reporting exact audit metrics."""
    res = client.get("/api/evaluation/metrics")
    assert res.status_code == 200
    metrics = res.json()
    assert "facts_extracted" in metrics
    assert "grounded_facts" in metrics
    assert "ungrounded_facts" in metrics
    assert "relationships_classified" in metrics
    assert "uncertain_relationships" in metrics
    assert "extraction_failures" in metrics
    assert metrics["documents_processed"] >= 0
