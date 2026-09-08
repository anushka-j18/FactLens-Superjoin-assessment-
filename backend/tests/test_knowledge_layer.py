import io
import fitz
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def create_minimal_pdf_bytes(text: str = "Test document content page 1", num_pages: int = 1) -> bytes:
    doc = fitz.open()
    for i in range(num_pages):
        page = doc.new_page(width=595, height=842)
        page.insert_text((50, 100 + i * 20), f"{text} (Page {i+1})")
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def test_create_knowledge_layer():
    response = client.post("/api/knowledge-layers", json={
        "name": "Delhivery FY24 Analysis",
        "description": "Multi-document corporate dataset analysis"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Delhivery FY24 Analysis"
    assert data["description"] == "Multi-document corporate dataset analysis"
    assert "id" in data
    assert data["document_count"] == 0


def test_list_knowledge_layers():
    client.post("/api/knowledge-layers", json={"name": "Layer 1"})
    client.post("/api/knowledge-layers", json={"name": "Layer 2"})

    response = client.get("/api/knowledge-layers")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 2
    assert len(data["knowledge_layers"]) >= 2


def test_upload_single_pdf_to_knowledge_layer():
    kl_res = client.post("/api/knowledge-layers", json={"name": "Single Upload KL"})
    kl_id = kl_res.json()["id"]

    pdf1 = create_minimal_pdf_bytes("Prospectus revenue data", num_pages=2)
    
    upload_res = client.post(
        f"/api/knowledge-layers/{kl_id}/documents",
        files=[("files", ("prospectus.pdf", pdf1, "application/pdf"))]
    )
    assert upload_res.status_code == 201
    docs = upload_res.json()
    assert len(docs) == 1
    assert docs[0]["original_filename"] == "prospectus.pdf"
    assert docs[0]["knowledge_layer_id"] == kl_id
    assert docs[0]["page_count"] == 2
    assert docs[0]["processing_status"] == "completed"


def test_upload_multiple_pdfs_to_knowledge_layer():
    kl_res = client.post("/api/knowledge-layers", json={"name": "Multi Upload KL"})
    kl_id = kl_res.json()["id"]

    pdf1 = create_minimal_pdf_bytes("Document A text", num_pages=1)
    pdf2 = create_minimal_pdf_bytes("Document B text", num_pages=3)
    pdf3 = create_minimal_pdf_bytes("Document C text", num_pages=2)

    upload_res = client.post(
        f"/api/knowledge-layers/{kl_id}/documents",
        files=[
            ("files", ("doc_a.pdf", pdf1, "application/pdf")),
            ("files", ("doc_b.pdf", pdf2, "application/pdf")),
            ("files", ("doc_c.pdf", pdf3, "application/pdf")),
        ]
    )
    assert upload_res.status_code == 201
    docs = upload_res.json()
    assert len(docs) == 3
    
    # Verify all belong to same knowledge layer
    for d in docs:
        assert d["knowledge_layer_id"] == kl_id
        assert d["processing_status"] == "completed"

    # Verify document list for knowledge layer
    kl_docs_res = client.get(f"/api/knowledge-layers/{kl_id}/documents")
    assert kl_docs_res.status_code == 200
    assert len(kl_docs_res.json()) == 3


def test_two_knowledge_layers_remain_independent():
    kl1_res = client.post("/api/knowledge-layers", json={"name": "Delhivery"})
    kl1_id = kl1_res.json()["id"]

    kl2_res = client.post("/api/knowledge-layers", json={"name": "India Macroeconomy"})
    kl2_id = kl2_res.json()["id"]

    pdf_delhivery = create_minimal_pdf_bytes("Delhivery revenue 4600 Cr")
    pdf_macro = create_minimal_pdf_bytes("India GDP growth 8.2 percent")

    client.post(
        f"/api/knowledge-layers/{kl1_id}/documents",
        files=[("files", ("delhivery.pdf", pdf_delhivery, "application/pdf"))]
    )

    client.post(
        f"/api/knowledge-layers/{kl2_id}/documents",
        files=[("files", ("macro.pdf", pdf_macro, "application/pdf"))]
    )

    docs1 = client.get(f"/api/knowledge-layers/{kl1_id}/documents").json()
    docs2 = client.get(f"/api/knowledge-layers/{kl2_id}/documents").json()

    assert len(docs1) == 1
    assert docs1[0]["original_filename"] == "delhivery.pdf"

    assert len(docs2) == 1
    assert docs2[0]["original_filename"] == "macro.pdf"


def test_page_level_evidence_preservation():
    kl_res = client.post("/api/knowledge-layers", json={"name": "Evidence Test KL"})
    kl_id = kl_res.json()["id"]

    pdf_multi_page = create_minimal_pdf_bytes("Page specific quote text", num_pages=4)
    upload_res = client.post(
        f"/api/knowledge-layers/{kl_id}/documents",
        files=[("files", ("multi_page.pdf", pdf_multi_page, "application/pdf"))]
    )
    doc_id = upload_res.json()[0]["id"]

    ev_res = client.get(f"/api/documents/{doc_id}/evidence")
    assert ev_res.status_code == 200
    evidence_units = ev_res.json()
    assert len(evidence_units) == 4
    
    page_numbers = [ev["page_number"] for ev in evidence_units]
    assert page_numbers == [1, 2, 3, 4]
    
    for ev in evidence_units:
        assert ev["document_id"] == doc_id
        assert "Page specific quote text" in ev["raw_text"]


def test_document_identity_preservation():
    kl_res = client.post("/api/knowledge-layers", json={"name": "Identity Test KL"})
    kl_id = kl_res.json()["id"]

    pdf1 = create_minimal_pdf_bytes("Annual Report revenue")
    pdf2 = create_minimal_pdf_bytes("Earnings Presentation revenue")

    upload_res = client.post(
        f"/api/knowledge-layers/{kl_id}/documents",
        files=[
            ("files", ("annual_report.pdf", pdf1, "application/pdf")),
            ("files", ("earnings_presentation.pdf", pdf2, "application/pdf")),
        ]
    )
    docs = upload_res.json()
    doc1_id = docs[0]["id"]
    doc2_id = docs[1]["id"]

    ev1 = client.get(f"/api/documents/{doc1_id}/evidence").json()
    ev2 = client.get(f"/api/documents/{doc2_id}/evidence").json()

    assert all(unit["document_id"] == doc1_id for unit in ev1)
    assert all(unit["document_id"] == doc2_id for unit in ev2)
    assert not any(unit["document_id"] == doc2_id for unit in ev1)


def test_duplicate_pdf_handling():
    kl_res = client.post("/api/knowledge-layers", json={"name": "Duplicate Test KL"})
    kl_id = kl_res.json()["id"]

    pdf_bytes = create_minimal_pdf_bytes("Unique checksum text for duplicate test")

    res1 = client.post(
        f"/api/knowledge-layers/{kl_id}/documents",
        files=[("files", ("first_upload.pdf", pdf_bytes, "application/pdf"))]
    )
    assert res1.status_code == 201
    doc1 = res1.json()[0]

    # Re-upload exact same PDF file bytes to same knowledge layer
    res2 = client.post(
        f"/api/knowledge-layers/{kl_id}/documents",
        files=[("files", ("second_upload.pdf", pdf_bytes, "application/pdf"))]
    )
    assert res2.status_code == 201
    doc2 = res2.json()[0]
    
    # Returns existing document without duplicating records
    assert doc2["id"] == doc1["id"]


def test_invalid_pdf_handling():
    kl_res = client.post("/api/knowledge-layers", json={"name": "Invalid PDF KL"})
    kl_id = kl_res.json()["id"]

    invalid_bytes = b"This is not a PDF file structure"

    res = client.post(
        f"/api/knowledge-layers/{kl_id}/documents",
        files=[("files", ("corrupt.pdf", invalid_bytes, "application/pdf"))]
    )
    assert res.status_code == 201
    docs = res.json()
    assert len(docs) == 1
    assert docs[0]["processing_status"] == "failed"
    assert docs[0]["error_message"] is not None


def test_one_failed_pdf_does_not_fail_other_pdfs():
    kl_res = client.post("/api/knowledge-layers", json={"name": "Partial Failure KL"})
    kl_id = kl_res.json()["id"]

    valid_pdf = create_minimal_pdf_bytes("Valid document content")
    invalid_pdf = b"NOT_A_VALID_PDF_STREAM"

    res = client.post(
        f"/api/knowledge-layers/{kl_id}/documents",
        files=[
            ("files", ("valid.pdf", valid_pdf, "application/pdf")),
            ("files", ("corrupt.pdf", invalid_pdf, "application/pdf")),
        ]
    )
    assert res.status_code == 201
    docs = res.json()
    assert len(docs) == 2
    
    statuses = {d["original_filename"]: d["processing_status"] for d in docs}
    assert statuses["valid.pdf"] == "completed"
    assert statuses["corrupt.pdf"] == "failed"


def test_delete_knowledge_layer():
    kl_res = client.post("/api/knowledge-layers", json={"name": "Delete Me KL"})
    kl_id = kl_res.json()["id"]

    del_res = client.delete(f"/api/knowledge-layers/{kl_id}")
    assert del_res.status_code == 204

    get_res = client.get(f"/api/knowledge-layers/{kl_id}")
    assert get_res.status_code == 404
