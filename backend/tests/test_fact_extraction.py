import io
import os
import pymupdf as fitz
import pytest

from app.services.llm.mock import MockLLMProvider, MockProviderError
from app.services.fact_extractor import FactExtractorService, FactExtractorError
from app.models.entities import Document, Fact, EvidenceUnit, KnowledgeLayer, ExtractionRun


def create_sample_pdf(text_content: str = "Delhivery revenue was INR 4,600 Cr in FY24.") -> bytes:
    """Helper to generate a valid test PDF document using PyMuPDF."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), text_content)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def test_grounded_fact_extraction(client):
    """1. Test successful fact extraction."""
    text = "Delhivery revenue was INR 4,600 Cr in FY24."
    pdf_bytes = create_sample_pdf(text)
    
    up_res = client.post(
        "/api/documents",
        files={"file": ("delhivery_financials.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    )
    assert up_res.status_code == 201
    doc_id = up_res.json()["id"]

    ext_res = client.post(f"/api/documents/{doc_id}/extract")
    assert ext_res.status_code == 200
    ext_data = ext_res.json()

    assert ext_data["extraction_status"] == "completed"
    assert ext_data["extracted_facts_count"] >= 1
    assert ext_data["rejected_facts_count"] == 0

    facts = ext_data["facts"]
    rev_fact = next(f for f in facts if "revenue" in f["predicate"].lower())
    assert rev_fact["document_id"] == doc_id
    assert "4,600 Cr" in rev_fact["value"]
    assert rev_fact["normalized_value"] == 46000000000.0
    assert rev_fact["value_type"] == "currency"
    assert rev_fact["unit"] == "INR"
    assert rev_fact["temporal_context"] == "FY2024"
    assert rev_fact["extraction_status"] == "grounded"
    assert "revenue was" in rev_fact["verbatim_quote"]


def test_multiple_facts_from_one_document(client):
    """2. Test extracting multiple facts from a single document."""
    text = "Delhivery revenue was INR 4,600 Cr in FY24. India GDP growth was 6.4% in FY25. Total staff 2450 employees."
    pdf_bytes = create_sample_pdf(text)
    
    up_res = client.post(
        "/api/documents",
        files={"file": ("multi_fact_doc.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    )
    doc_id = up_res.json()["id"]

    ext_res = client.post(f"/api/documents/{doc_id}/extract")
    assert ext_res.status_code == 200
    facts = ext_res.json()["facts"]
    assert len(facts) >= 2


def test_fact_references_valid_evidence(client, db_session):
    """3. Test every extracted fact references valid, existing evidence IDs."""
    text = "Company reported 14% market share."
    pdf_bytes = create_sample_pdf(text)
    
    up_res = client.post(
        "/api/documents",
        files={"file": ("valid_ev.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    )
    doc_id = up_res.json()["id"]

    ext_res = client.post(f"/api/documents/{doc_id}/extract")
    facts = ext_res.json()["facts"]
    
    for f in facts:
        assert f["evidence_id"] is not None
        ev = db_session.query(EvidenceUnit).filter(EvidenceUnit.id == f["evidence_id"]).first()
        assert ev is not None
        assert ev.document_id == doc_id


def test_hallucinated_evidence_id_rejection(client, db_session):
    """4. Test backend deterministically rejects hallucinated evidence IDs."""
    text = "Delhivery revenue was INR 4,600 Cr."
    pdf_bytes = create_sample_pdf(text)
    
    up_res = client.post(
        "/api/documents",
        files={"file": ("test_hallucination.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    )
    doc_id = up_res.json()["id"]

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


def test_fact_without_evidence_is_rejected(client, db_session):
    """5. Test fact with empty or missing evidence reference is rejected."""
    text = "Company reported 14% market share."
    pdf_bytes = create_sample_pdf(text)

    up_res = client.post(
        "/api/documents",
        files={"file": ("no_ev_ref.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    )
    doc_id = up_res.json()["id"]

    class NoEvidenceLLMProvider(MockLLMProvider):
        def generate_structured(self, prompt, schema, system_prompt=None):
            return {
                "facts": [
                    {
                        "subject": "Company",
                        "predicate": "market share",
                        "value": "14%",
                        "verbatim_quote": "Company reported 14% market share.",
                    }
                ]
            }

    ext_status, valid_facts, rejected_count = FactExtractorService.extract_facts_from_document(
        db=db_session,
        document_id=doc_id,
        llm_provider=NoEvidenceLLMProvider()
    )

    assert len(valid_facts) == 0
    assert rejected_count == 1


def test_llm_returns_malformed_json(client, db_session):
    """6. Test handling when LLM provider raises an exception/malformed output."""
    text = "Some document text."
    pdf_bytes = create_sample_pdf(text)

    up_res = client.post(
        "/api/documents",
        files={"file": ("malformed.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    )
    doc_id = up_res.json()["id"]

    class BrokenLLMProvider(MockLLMProvider):
        def generate_structured(self, prompt, schema, system_prompt=None):
            raise ValueError("Malformed JSON response from model.")

    ext_status, valid_facts, rejected_count = FactExtractorService.extract_facts_from_document(
        db=db_session,
        document_id=doc_id,
        llm_provider=BrokenLLMProvider()
    )

    assert ext_status == "failed"
    assert len(valid_facts) == 0


def test_llm_provider_failure(client, db_session):
    """7. Test handling when LLM provider throws a network/runtime error."""
    text = "Another document."
    pdf_bytes = create_sample_pdf(text)

    up_res = client.post(
        "/api/documents",
        files={"file": ("network_err.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    )
    doc_id = up_res.json()["id"]

    class FailingLLMProvider(MockLLMProvider):
        def generate_structured(self, prompt, schema, system_prompt=None):
            raise RuntimeError("API Connection timeout.")

    ext_status, valid_facts, rejected_count = FactExtractorService.extract_facts_from_document(
        db=db_session,
        document_id=doc_id,
        llm_provider=FailingLLMProvider()
    )

    assert ext_status == "failed"
    assert len(valid_facts) == 0


def test_empty_evidence(db_session):
    """8. Test extracting facts from a document with zero evidence units fails gracefully."""
    doc = Document(
        filename="empty.pdf",
        original_filename="empty.pdf",
        file_size=100,
        file_hash="dummyhash123",
        page_count=0,
    )
    db_session.add(doc)
    db_session.commit()

    with pytest.raises(FactExtractorError):
        FactExtractorService.extract_facts_from_document(db=db_session, document_id=doc.id)


def test_reextraction_idempotency_no_duplicates(client, db_session):
    """9. Test repeated fact extraction on same document replaces prior facts without duplicates."""
    text = "Delhivery revenue was INR 4,600 Cr in FY24."
    pdf_bytes = create_sample_pdf(text)
    
    up_res = client.post(
        "/api/documents",
        files={"file": ("idempotent.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    )
    doc_id = up_res.json()["id"]

    # First extraction
    client.post(f"/api/documents/{doc_id}/extract")
    facts1 = db_session.query(Fact).filter(Fact.document_id == doc_id).all()
    count1 = len(facts1)

    # Second extraction (re-extract)
    client.post(f"/api/documents/{doc_id}/extract")
    facts2 = db_session.query(Fact).filter(Fact.document_id == doc_id).all()
    count2 = len(facts2)

    assert count1 > 0
    assert count1 == count2  # No duplicate growth!


def test_mock_provider_behavior():
    """10. Test MockLLMProvider raises MockProviderError in non-test mode."""
    provider = MockLLMProvider(allow_mock_extraction=False)
    # Temporarily remove test env var
    old_test = os.environ.pop("PYTEST_CURRENT_TEST", None)
    try:
        with pytest.raises(MockProviderError):
            provider.generate_structured("prompt", {})
    finally:
        if old_test:
            os.environ["PYTEST_CURRENT_TEST"] = old_test


def test_facts_association_single_document(client):
    """11. Test extracted facts remain correctly associated with target document."""
    text = "Delhivery revenue was INR 4,600 Cr in FY24."
    pdf_bytes = create_sample_pdf(text)

    up_res = client.post(
        "/api/documents",
        files={"file": ("single_doc_assoc.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    )
    doc_id = up_res.json()["id"]

    client.post(f"/api/documents/{doc_id}/extract")

    doc_facts_res = client.get(f"/api/documents/{doc_id}/facts")
    assert doc_facts_res.status_code == 200
    for f in doc_facts_res.json():
        assert f["document_id"] == doc_id


def test_facts_association_multiple_documents(client):
    """12. Test facts from multiple documents remain correctly isolated per document."""
    pdf1 = create_sample_pdf("Delhivery revenue was INR 4,600 Cr in FY24.")
    pdf2 = create_sample_pdf("India GDP growth was 6.4% in FY25.")

    doc1_id = client.post("/api/documents", files={"file": ("doc1.pdf", io.BytesIO(pdf1), "application/pdf")}).json()["id"]
    doc2_id = client.post("/api/documents", files={"file": ("doc2.pdf", io.BytesIO(pdf2), "application/pdf")}).json()["id"]

    client.post(f"/api/documents/{doc1_id}/extract")
    client.post(f"/api/documents/{doc2_id}/extract")

    facts1 = client.get(f"/api/documents/{doc1_id}/facts").json()
    facts2 = client.get(f"/api/documents/{doc2_id}/facts").json()

    for f in facts1:
        assert f["document_id"] == doc1_id
    for f in facts2:
        assert f["document_id"] == doc2_id


def test_isolated_batch_extraction_failure(client, db_session):
    """13. Test failed extraction for one document does not remove facts from another document."""
    kl_res = client.post("/api/knowledge-layers", json={"name": "Test KL Batch"})
    kl_id = kl_res.json()["id"]

    pdf1 = create_sample_pdf("Delhivery revenue was INR 4,600 Cr in FY24.")
    pdf2 = create_sample_pdf("Document 2 text.")

    docs_res = client.post(
        f"/api/knowledge-layers/{kl_id}/documents",
        files=[
            ("files", ("good_doc.pdf", io.BytesIO(pdf1), "application/pdf")),
            ("files", ("bad_doc.pdf", io.BytesIO(pdf2), "application/pdf")),
        ]
    )
    docs = docs_res.json()
    doc1_id = docs[0]["id"]
    doc2_id = docs[1]["id"]

    # Extract for doc 1 successfully
    client.post(f"/api/documents/{doc1_id}/extract")
    initial_facts1 = client.get(f"/api/documents/{doc1_id}/facts").json()
    assert len(initial_facts1) >= 1

    # Simulate extraction failure on doc 2 using broken provider
    class FailingLLMProvider(MockLLMProvider):
        def generate_structured(self, prompt, schema, system_prompt=None):
            raise RuntimeError("Doc 2 failed")

    FactExtractorService.extract_facts_from_document(
        db=db_session,
        document_id=doc2_id,
        llm_provider=FailingLLMProvider()
    )

    # Verify doc 1 facts remain intact
    post_facts1 = client.get(f"/api/documents/{doc1_id}/facts").json()
    assert len(post_facts1) == len(initial_facts1)
