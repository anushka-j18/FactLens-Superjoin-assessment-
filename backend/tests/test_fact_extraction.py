import io
import os
import pymupdf as fitz
import pytest

from app.services.llm.mock import MockLLMProvider
from app.services.fact_extractor import FactExtractorService


def create_sample_pdf(text_content: str = "Delhivery revenue was INR 4,600 Cr in FY24.") -> bytes:
    """Helper to generate a valid test PDF document using PyMuPDF."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), text_content)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def test_grounded_fact_extraction(client):
    """Test full grounded fact extraction flow using MockLLMProvider."""
    text = "Delhivery revenue was INR 4,600 Cr in FY24. Total employees 2450."
    pdf_bytes = create_sample_pdf(text)
    
    # 1. Upload PDF
    up_res = client.post(
        "/api/documents",
        files={"file": ("delhivery_financials.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    )
    assert up_res.status_code == 201
    doc_id = up_res.json()["id"]

    # 2. Trigger Extraction
    ext_res = client.post(f"/api/documents/{doc_id}/extract")
    assert ext_res.status_code == 200
    ext_data = ext_res.json()

    assert ext_data["extraction_status"] == "completed"
    assert ext_data["extracted_facts_count"] >= 1
    assert ext_data["rejected_facts_count"] == 0

    # 3. Verify Grounded Facts structure
    facts = ext_data["facts"]
    rev_fact = next(f for f in facts if "revenue" in f["predicate"].lower())
    assert rev_fact["document_id"] == doc_id
    assert "4,600 Cr" in rev_fact["value"]
    assert rev_fact["normalized_value"] == 46000000000.0  # 4,600 Cr -> 46,000,000,000.0
    assert rev_fact["value_type"] == "currency"
    assert rev_fact["unit"] == "INR"
    assert rev_fact["temporal_context"] == "FY24"
    assert rev_fact["extraction_status"] == "grounded"
    assert "revenue was" in rev_fact["verbatim_quote"]


def test_hallucinated_evidence_id_rejection(client, db_session):
    """Test backend deterministically rejects hallucinated evidence IDs."""
    text = "Delhivery revenue was INR 4,600 Cr."
    pdf_bytes = create_sample_pdf(text)
    
    up_res = client.post(
        "/api/documents",
        files={"file": ("test_hallucination.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    )
    doc_id = up_res.json()["id"]

    # Custom mock provider that injects a fake evidence_id
    class HallucinatingLLMProvider(MockLLMProvider):
        def generate_structured(self, prompt, schema, system_prompt=None):
            return {
                "facts": [
                    {
                        "evidence_id": "fake-hallucinated-uuid-12345",
                        "subject": "Delhivery",
                        "predicate": "revenue",
                        "value": "INR 4,600 Cr",
                        "verbatim_quote": "Delhivery revenue was INR 4,600 Cr.",
                        "is_inferred": False,
                    }
                ]
            }

    ext_status, valid_facts, rejected_count = FactExtractorService.extract_facts_from_document(
        db=db_session,
        document_id=doc_id,
        llm_provider=HallucinatingLLMProvider()
    )

    assert ext_status == "completed"
    assert len(valid_facts) == 0  # Fake evidence_id rejected!
    assert rejected_count == 1


def test_hallucinated_quote_rejection(client, db_session):
    """Test backend deterministically rejects quotes not grounded in evidence text."""
    text = "Company reported 14% market share."
    pdf_bytes = create_sample_pdf(text)

    up_res = client.post(
        "/api/documents",
        files={"file": ("test_quote.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    )
    doc_id = up_res.json()["id"]

    # Retrieve valid evidence ID for doc
    doc_detail = client.get(f"/api/documents/{doc_id}").json()
    valid_ev_id = doc_detail["evidence_units"][0]["id"]

    class FakeQuoteLLMProvider(MockLLMProvider):
        def generate_structured(self, prompt, schema, system_prompt=None):
            return {
                "facts": [
                    {
                        "evidence_id": valid_ev_id,
                        "subject": "Company",
                        "predicate": "revenue",
                        "value": "$500 million",
                        "verbatim_quote": "Completely fake quote that does not exist in the source document.",
                        "is_inferred": False,
                    }
                ]
            }

    ext_status, valid_facts, rejected_count = FactExtractorService.extract_facts_from_document(
        db=db_session,
        document_id=doc_id,
        llm_provider=FakeQuoteLLMProvider()
    )

    assert ext_status == "completed"
    assert len(valid_facts) == 0  # Ungrounded quote rejected!
    assert rejected_count == 1


def test_get_facts_and_filtering(client):
    """Test GET /api/facts and GET /api/documents/{document_id}/facts endpoints."""
    text = "Delhivery revenue was INR 4,600 Cr in FY24."
    pdf_bytes = create_sample_pdf(text)
    
    up_res = client.post(
        "/api/documents",
        files={"file": ("delhivery_filter.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    )
    doc_id = up_res.json()["id"]

    # Extract facts
    client.post(f"/api/documents/{doc_id}/extract")

    # Fetch document facts
    doc_facts_res = client.get(f"/api/documents/{doc_id}/facts")
    assert doc_facts_res.status_code == 200
    doc_facts = doc_facts_res.json()
    assert len(doc_facts) >= 1

    fact_id = doc_facts[0]["id"]

    # Fetch single fact
    single_res = client.get(f"/api/facts/{fact_id}")
    assert single_res.status_code == 200
    assert single_res.json()["id"] == fact_id

    # List all facts with predicate filter
    filter_res = client.get("/api/facts?predicate=revenue")
    assert filter_res.status_code == 200
    filter_data = filter_res.json()
    assert filter_data["total"] >= 1
