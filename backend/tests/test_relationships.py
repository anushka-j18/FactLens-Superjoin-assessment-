import io
import pymupdf as fitz
import pytest

from app.models.entities import Fact, FactRelationship
from app.services.relationship_reasoner import RelationshipReasonerService


def create_sample_pdf(text_content: str) -> bytes:
    """Helper to generate PDF bytes with custom text content."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), text_content)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def test_corroborated_relationship_case(client):
    """Test 1: CORROBORATED case when both documents report identical values for the same timeframe."""
    text1 = "Delhivery revenue was INR 4,600 Cr in FY24."
    text2 = "Delhivery revenue was INR 4,600 Cr in FY24."

    # Upload Doc 1 & extract facts
    res1 = client.post("/api/documents", files={"file": ("doc_a.pdf", io.BytesIO(create_sample_pdf(text1)), "application/pdf")})
    doc1_id = res1.json()["id"]
    client.post(f"/api/documents/{doc1_id}/extract")

    # Upload Doc 2 & extract facts
    res2 = client.post("/api/documents", files={"file": ("doc_b.pdf", io.BytesIO(create_sample_pdf(text2)), "application/pdf")})
    doc2_id = res2.json()["id"]
    client.post(f"/api/documents/{doc2_id}/extract")

    # Run relationship analysis
    an_res = client.post("/api/relationships/analyze")
    assert an_res.status_code == 200
    an_data = an_res.json()
    assert an_data["analyzed_relationships_count"] >= 1

    corroborated_rels = [r for r in an_data["relationships"] if r["relationship_type"] == "CORROBORATED"]
    assert len(corroborated_rels) >= 1
    assert "Corroborated:" in corroborated_rels[0]["reasoning_summary"]


def test_contradicted_relationship_case(client):
    """Test 2: CONTRADICTED case when documents report conflicting values for the exact same timeframe."""
    text1 = "Delhivery revenue was INR 4,600 Cr in FY24."
    text2 = "Delhivery revenue was INR 5,200 Cr in FY24."

    res1 = client.post("/api/documents", files={"file": ("doc_c.pdf", io.BytesIO(create_sample_pdf(text1)), "application/pdf")})
    doc1_id = res1.json()["id"]
    client.post(f"/api/documents/{doc1_id}/extract")

    res2 = client.post("/api/documents", files={"file": ("doc_d.pdf", io.BytesIO(create_sample_pdf(text2)), "application/pdf")})
    doc2_id = res2.json()["id"]
    client.post(f"/api/documents/{doc2_id}/extract")

    an_res = client.post("/api/relationships/analyze", json={"document_ids": [doc1_id, doc2_id]})
    assert an_res.status_code == 200
    an_data = an_res.json()

    contradicted_rels = [r for r in an_data["relationships"] if r["relationship_type"] == "CONTRADICTED"]
    assert len(contradicted_rels) >= 1
    assert "Contradicted:" in contradicted_rels[0]["reasoning_summary"]


def test_contextually_reconciled_relationship_case(client):
    """Test 3: CONTEXTUALLY_RECONCILED case when values differ due to different timeframes (FY22 vs FY24)."""
    text1 = "Delhivery revenue was INR 3,800 Cr in FY22."
    text2 = "Delhivery revenue was INR 4,600 Cr in FY24."

    res1 = client.post("/api/documents", files={"file": ("doc_e.pdf", io.BytesIO(create_sample_pdf(text1)), "application/pdf")})
    doc1_id = res1.json()["id"]
    client.post(f"/api/documents/{doc1_id}/extract")

    res2 = client.post("/api/documents", files={"file": ("doc_f.pdf", io.BytesIO(create_sample_pdf(text2)), "application/pdf")})
    doc2_id = res2.json()["id"]
    client.post(f"/api/documents/{doc2_id}/extract")

    an_res = client.post("/api/relationships/analyze", json={"document_ids": [doc1_id, doc2_id]})
    assert an_res.status_code == 200
    an_data = an_res.json()

    reconciled_rels = [r for r in an_data["relationships"] if r["relationship_type"] == "CONTEXTUALLY_RECONCILED"]
    assert len(reconciled_rels) >= 1
    assert "Contextually Reconciled:" in reconciled_rels[0]["reasoning_summary"]


def test_reasoning_failure_case(client, db_session):
    """Test 4: REASONING_FAILURE case when evidence extraction confidence is below threshold."""
    # Create two facts directly in DB with low extraction confidence
    doc_a_id = "doc-test-1"
    doc_b_id = "doc-test-2"

    f1 = Fact(
        id="fact-1",
        document_id=doc_a_id,
        evidence_id="ev-1",
        page_number=1,
        subject="Delhivery",
        predicate="revenue",
        value="INR 4,600 Cr",
        verbatim_quote="Ambiguous revenue quote",
        extraction_confidence=0.30,  # Low confidence
        extraction_status="unverified",
    )
    f2 = Fact(
        id="fact-2",
        document_id=doc_b_id,
        evidence_id="ev-2",
        page_number=1,
        subject="Delhivery",
        predicate="revenue",
        value="INR 5,000 Cr",
        verbatim_quote="Another ambiguous quote",
        extraction_confidence=0.40,  # Low confidence
        extraction_status="unverified",
    )

    db_session.add(f1)
    db_session.add(f2)
    db_session.commit()

    rel = RelationshipReasonerService._classify_fact_pair(
        db=db_session,
        f1=f1,
        f2=f2,
        comp={"is_comparable": True, "temporal_match": True, "geographic_match": True}
    )

    assert rel is not None
    assert rel.relationship_type == "REASONING_FAILURE"
    assert "Reasoning Failure" in rel.reasoning_summary


def test_list_and_get_relationships_endpoints(client):
    """Test GET /api/relationships and GET /api/relationships/{relationship_id} endpoints."""
    text1 = "Delhivery revenue was INR 4,600 Cr in FY24."
    text2 = "Delhivery revenue was INR 4,600 Cr in FY24."

    res1 = client.post("/api/documents", files={"file": ("doc_g.pdf", io.BytesIO(create_sample_pdf(text1)), "application/pdf")})
    doc1_id = res1.json()["id"]
    client.post(f"/api/documents/{doc1_id}/extract")

    res2 = client.post("/api/documents", files={"file": ("doc_h.pdf", io.BytesIO(create_sample_pdf(text2)), "application/pdf")})
    doc2_id = res2.json()["id"]
    client.post(f"/api/documents/{doc2_id}/extract")

    client.post("/api/relationships/analyze")

    # List relationships
    list_res = client.get("/api/relationships?relationship_type=CORROBORATED")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert list_data["total"] >= 1

    rel_id = list_data["relationships"][0]["id"]

    # Get single relationship detail
    single_res = client.get(f"/api/relationships/{rel_id}")
    assert single_res.status_code == 200
    assert single_res.json()["id"] == rel_id
