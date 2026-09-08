import io
import pytest
import pymupdf as fitz

from app.models.entities import Document, Fact, FactRelationship
from app.services.fact_extractor import FactExtractorService
from app.services.candidate_matcher import CandidateMatcherService
from app.services.relationship_reasoner import RelationshipReasonerService


def create_sample_pdf(text_content: str) -> bytes:
    """Helper to generate PDF bytes with custom text content."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), text_content)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def test_incremental_document_processing_does_not_reextract_existing_facts(client, db_session):
    """Test proving incremental processing:
    1. Document A is processed.
    2. Document B is added later.
    3. Document A facts are NOT re-extracted (IDs and timestamps stay identical).
    4. Document B facts are matched incrementally against Document A's existing facts.
    """
    text_A = "Delhivery revenue was INR 4,600 Cr in FY24."
    text_B = "Delhivery revenue was INR 4,600 Cr in FY24."

    # 1. Upload & Process Document A
    res_A = client.post(
        "/api/documents",
        files={"file": ("doc_A.pdf", io.BytesIO(create_sample_pdf(text_A)), "application/pdf")}
    )
    doc_A_id = res_A.json()["id"]

    # Process Document A
    proc_A_res = client.post(f"/api/documents/{doc_A_id}/process_incremental")
    assert proc_A_res.status_code == 200
    assert proc_A_res.json()["new_facts_extracted"] >= 1

    # Record Document A's extracted facts, fact IDs, and creation timestamps
    facts_A_before = db_session.query(Fact).filter(Fact.document_id == doc_A_id).all()
    fact_A_ids_before = {f.id for f in facts_A_before}
    fact_A_timestamps_before = {f.id: f.created_at for f in facts_A_before}

    assert len(fact_A_ids_before) >= 1

    # 2. Upload Document B later
    res_B = client.post(
        "/api/documents",
        files={"file": ("doc_B.pdf", io.BytesIO(create_sample_pdf(text_B)), "application/pdf")}
    )
    doc_B_id = res_B.json()["id"]

    # 3. Process Document B incrementally
    proc_B_res = client.post(f"/api/documents/{doc_B_id}/process_incremental")
    assert proc_B_res.status_code == 200
    proc_B_data = proc_B_res.json()
    assert proc_B_data["new_facts_extracted"] >= 1
    assert proc_B_data["new_relationships_formed"] >= 1

    # 4. Prove Document A facts were NOT re-extracted
    facts_A_after = db_session.query(Fact).filter(Fact.document_id == doc_A_id).all()
    fact_A_ids_after = {f.id for f in facts_A_after}
    fact_A_timestamps_after = {f.id: f.created_at for f in facts_A_after}

    # Verify fact IDs match exactly
    assert fact_A_ids_before == fact_A_ids_after

    # Verify fact creation timestamps were unchanged
    for fid in fact_A_ids_before:
        assert fact_A_timestamps_before[fid] == fact_A_timestamps_after[fid]

    # 5. Verify new relationships comparing Document B against Document A were generated
    new_rels = proc_B_data["new_relationships"]
    assert len(new_rels) >= 1
    rel = new_rels[0]
    assert rel["relationship_type"] == "CORROBORATED"
