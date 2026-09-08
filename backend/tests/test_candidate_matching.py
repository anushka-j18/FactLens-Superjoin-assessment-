import io
import pymupdf as fitz
import pytest

from app.services.embeddings.mock import MockEmbeddingProvider
from app.services.candidate_matcher import CandidateMatcherService


def create_sample_pdf(text_content: str) -> bytes:
    """Helper to generate PDF bytes with custom text content."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), text_content)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def test_embedding_generation_and_cosine_similarity():
    """Test MockEmbeddingProvider vector generation and cosine similarity math."""
    provider = MockEmbeddingProvider()
    vec1 = provider.embed_text("Delhivery revenue was INR 4,600 Cr in FY24.")
    vec2 = provider.embed_text("Delhivery total sales was INR 4,600 Cr in FY24.")
    vec3 = provider.embed_text("India GDP growth rate was 6.5 percent.")

    assert len(vec1) == 64
    assert len(vec2) == 64

    sim_similar = CandidateMatcherService.cosine_similarity(vec1, vec2)
    sim_different = CandidateMatcherService.cosine_similarity(vec1, vec3)

    assert sim_similar > sim_different
    assert 0.0 <= sim_similar <= 1.0


def test_staged_candidate_retrieval(client):
    """Test 2-stage candidate fact retrieval across distinct documents."""
    text1 = "Delhivery revenue was INR 4,600 Cr in FY24."
    text2 = "Delhivery total sales was INR 4,600 Cr in FY24."
    text3 = "India inflation rate was 5.4 percent in FY24."

    # Upload Doc 1 & extract
    res1 = client.post("/api/documents", files={"file": ("cand_doc_1.pdf", io.BytesIO(create_sample_pdf(text1)), "application/pdf")})
    doc1_id = res1.json()["id"]
    client.post(f"/api/documents/{doc1_id}/extract")

    # Upload Doc 2 & extract
    res2 = client.post("/api/documents", files={"file": ("cand_doc_2.pdf", io.BytesIO(create_sample_pdf(text2)), "application/pdf")})
    doc2_id = res2.json()["id"]
    client.post(f"/api/documents/{doc2_id}/extract")

    # Upload Doc 3 & extract
    res3 = client.post("/api/documents", files={"file": ("cand_doc_3.pdf", io.BytesIO(create_sample_pdf(text3)), "application/pdf")})
    doc3_id = res3.json()["id"]
    client.post(f"/api/documents/{doc3_id}/extract")

    # Fetch facts for Doc 1
    doc1_facts = client.get(f"/api/documents/{doc1_id}/facts").json()
    assert len(doc1_facts) >= 1
    target_fact_id = doc1_facts[0]["id"]

    # Test GET /api/facts/{fact_id}/candidates endpoint
    cand_res = client.get(f"/api/facts/{target_fact_id}/candidates")
    assert cand_res.status_code == 200
    cand_data = cand_res.json()

    assert cand_data["target_fact_id"] == target_fact_id
    assert cand_data["total_candidates"] >= 1

    top_cand = cand_data["candidates"][0]
    assert top_cand["candidate_fact"]["document_id"] != doc1_id  # Must be from distinct document
    assert "revenue" in top_cand["candidate_fact"]["predicate"].lower() or "sales" in top_cand["candidate_fact"]["predicate"].lower()
    assert top_cand["similarity_score"] > 0.5
    assert "matching_criteria" in top_cand


def test_document_agnostic_prefiltering(client):
    """Test candidate matching operates on domain-agnostic properties without hardcoded names."""
    text1 = "Acme Corp employees 1200 in 2024."
    text2 = "Acme Corp workforce 1.2K in 2024."

    res1 = client.post("/api/documents", files={"file": ("acme_1.pdf", io.BytesIO(create_sample_pdf(text1)), "application/pdf")})
    doc1_id = res1.json()["id"]
    client.post(f"/api/documents/{doc1_id}/extract")

    res2 = client.post("/api/documents", files={"file": ("acme_2.pdf", io.BytesIO(create_sample_pdf(text2)), "application/pdf")})
    doc2_id = res2.json()["id"]
    client.post(f"/api/documents/{doc2_id}/extract")

    doc1_facts = client.get(f"/api/documents/{doc1_id}/facts").json()
    target_fact_id = doc1_facts[0]["id"]

    cand_res = client.get(f"/api/facts/{target_fact_id}/candidates")
    assert cand_res.status_code == 200
    cand_data = cand_res.json()
    assert cand_data["total_candidates"] >= 1
