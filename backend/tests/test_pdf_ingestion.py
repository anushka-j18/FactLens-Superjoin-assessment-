import io
import os
import pymupdf as fitz
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.session import Base, get_db

from sqlalchemy.pool import StaticPool

# Setup in-memory SQLite database for testing with StaticPool
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_database():
    """Create fresh database tables before each test."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def create_sample_pdf(num_pages: int = 1, text_content: str = "FactLens evidence test page.") -> bytes:
    """Helper function to dynamically generate valid PDF bytes using PyMuPDF."""
    doc = fitz.open()
    for i in range(num_pages):
        page = doc.new_page()
        page.insert_text((50, 50), f"{text_content} Page {i + 1}")
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def test_valid_pdf_upload():
    """Test uploading a valid single-page PDF document."""
    pdf_bytes = create_sample_pdf(num_pages=1, text_content="Single page evidence quote.")
    response = client.post(
        "/api/documents",
        files={"file": ("test_single.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["original_filename"] == "test_single.pdf"
    assert data["page_count"] == 1
    assert data["processing_status"] == "completed"
    assert "file_hash" in data


def test_multi_page_pdf_ingestion():
    """Test multi-page PDF ingestion, page numbering (1-indexed), and evidence persistence."""
    pdf_bytes = create_sample_pdf(num_pages=3, text_content="Multi page test data.")
    response = client.post(
        "/api/documents",
        files={"file": ("test_multi.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    )
    assert response.status_code == 201
    doc_data = response.json()
    doc_id = doc_data["id"]
    assert doc_data["page_count"] == 3

    # Fetch document detail and evidence units
    detail_res = client.get(f"/api/documents/{doc_id}")
    assert detail_res.status_code == 200
    detail_data = detail_res.json()
    assert len(detail_data["evidence_units"]) == 3

    # Verify 1-indexed page numbers and verbatim text preservation
    evidence_list = detail_data["evidence_units"]
    for idx, evidence in enumerate(evidence_list):
        expected_page_num = idx + 1
        assert evidence["page_number"] == expected_page_num
        assert f"Page {expected_page_num}" in evidence["raw_text"]
        assert "location_metadata" in evidence
        assert "blocks" in evidence["location_metadata"]


def test_empty_and_corrupt_pdf_rejection():
    """Test rejection of 0-byte files, non-PDF headers, and corrupt files."""
    # 0-byte file
    res_empty = client.post(
        "/api/documents",
        files={"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")}
    )
    assert res_empty.status_code == 400

    # Non-PDF text file header
    res_text = client.post(
        "/api/documents",
        files={"file": ("fake.pdf", io.BytesIO(b"Hello world! Not a PDF"), "application/pdf")}
    )
    assert res_text.status_code == 400
    assert "not a valid PDF" in res_text.json()["detail"]


def test_invalid_file_extension():
    """Test rejection of files without .pdf extension."""
    response = client.post(
        "/api/documents",
        files={"file": ("data.csv", io.BytesIO(b"%PDF-1.4 header text"), "text/csv")}
    )
    assert response.status_code == 400
    assert "Only PDF files" in response.json()["detail"]


def test_duplicate_document_rejection():
    """Test duplicate document detection using SHA-256 file hash."""
    pdf_bytes = create_sample_pdf(num_pages=1, text_content="Duplicate test content.")
    
    # First upload -> Success
    res1 = client.post(
        "/api/documents",
        files={"file": ("doc1.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    )
    assert res1.status_code == 201

    # Second upload with exact same content -> 409 Conflict
    res2 = client.post(
        "/api/documents",
        files={"file": ("doc2_same_content.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    )
    assert res2.status_code == 409
    assert "Duplicate document" in res2.json()["detail"]["error"]


def test_starter_dataset_pdf_ingestion():
    """Test ingesting a real PDF from starter-datasets if present on disk."""
    sample_path = "data/starter-datasets/delhivery/03-delhivery-q4-fy24-earnings-presentation.pdf"
    if not os.path.exists(sample_path):
        sample_path = "../data/starter-datasets/delhivery/03-delhivery-q4-fy24-earnings-presentation.pdf"

    if os.path.exists(sample_path):
        with open(sample_path, "rb") as f:
            pdf_bytes = f.read()

        response = client.post(
            "/api/documents",
            files={"file": ("delhivery_q4.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["page_count"] > 0
        assert data["processing_status"] == "completed"

        # Verify evidence endpoints return page units
        evidence_res = client.get(f"/api/documents/{data['id']}/evidence")
        assert evidence_res.status_code == 200
        units = evidence_res.json()
        assert len(units) == data["page_count"]
