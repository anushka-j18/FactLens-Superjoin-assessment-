# FactLens — Evidence-First Document Intelligence

FactLens is an evidence-first document intelligence platform that ingests multiple PDF documents, extracts meaningful numerical and semantic facts, links every fact to exact source evidence (page numbers and verbatim quotes), and determines cross-document relationships:

1. **CORROBORATED**: Claims/numbers that align across documents.
2. **CONTRADICTED / LIKELY CONTRADICTION**: Claims/numbers that conflict directly.
3. **CONTEXTUALLY RECONCILED**: Apparent differences resolved by context (timeframe, accounting scope, currency).
4. **EXTRACTION / REASONING FAILURE**: Facts that cannot be linked due to missing evidence or ambiguity.

---

## Architecture Overview

For a detailed breakdown of the system architecture, boundaries, database entity schemas, and AI vs. deterministic responsibilities, see [ARCHITECTURE.md](file:///Users/anushka/Desktop/Summer%20Work%202026/Superjoin%20assessment/FactLens-Superjoin-assessment-/ARCHITECTURE.md).

---

## Development Setup

### Prerequisites
- **Python**: 3.11+
- **Node.js**: 18+
- **npm**: 9+

---

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create and activate a Python virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Copy environment configuration:
   ```bash
   cp ../.env.example .env
   ```

5. Start the FastAPI development server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

   The API health check endpoint will be available at `http://localhost:8000/health`.

---

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the Vite development server:
   ```bash
   npm run dev
   ```

   The web interface will be available at `http://localhost:5173`.

---

## PDF Ingestion & Evidence Extraction Pipeline

FactLens uses a deterministic parsing pipeline powered by PyMuPDF (`fitz`) to extract raw text and location metadata page-by-page.

### Processing Workflow
1. **Upload & Validation** (`POST /api/documents`):
   - Accepts `.pdf` files up to 50MB.
   - Validates `%PDF` binary header and PyMuPDF structure integrity.
   - Computes SHA-256 hash to detect duplicate documents (returns HTTP 409 Conflict if duplicate).
2. **Document Lifecycle States**:
   - `uploaded`: File saved on disk under `backend/storage/uploads/` with UUID filename.
   - `processing`: PyMuPDF parses page-by-page.
   - `completed`: All pages extracted into `EvidenceUnit` database records.
   - `failed`: Capture error message if file is corrupted or empty.
3. **Evidence Unit Provenance**:
   - Stores 1-indexed `page_number`, exact `raw_text`, normalized `clean_text`, and JSON `location_metadata` (page dimensions & block-level bounding boxes).
   - Source text is never paraphrased or lost.

### API Endpoints
- `POST /api/documents`: Upload a PDF file.
- `GET /api/documents`: List all uploaded documents with status and metadata.
- `GET /api/documents/{document_id}`: Get metadata and page evidence units for a document.
- `GET /api/documents/{document_id}/evidence`: Retrieve page-level evidence units.

---

## Starter Datasets

The repository includes two curated starter datasets under `data/starter-datasets/`:
- `delhivery/`: Corporate filings, prospectus, and earnings presentations.
- `india-macroeconomy/`: Macroeconomic reports from the Economic Survey, RBI, and IMF.

---

## License & Notes

Developed for engineering internship evaluation. All source evidence and reasoning traces are retained strictly for auditability.
