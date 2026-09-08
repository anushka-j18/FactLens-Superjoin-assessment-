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

## Grounded Fact Extraction Pipeline

FactLens converts unstructured evidence units into structured numerical and semantic facts while enforcing strict backend provenance verification.

### Key Features
1. **Dynamic Fact Schema**: Subject-predicate-value triple representation supporting arbitrary domain metrics (revenue, employees, CEO, headquarters, market share, inflation rates, etc.) without schema migrations.
2. **LLM Provider Abstraction**: Provider interface (`LLMProvider`) supporting `MockLLMProvider` for offline testing without API keys, as well as production LLM providers.
3. **Anti-Hallucination Guardrails**:
   - Backend injects valid `evidence_id`s into prompt.
   - Rejects candidate facts with invalid/hallucinated evidence IDs.
   - Verifies `verbatim_quote` substrings against raw source text before saving.
4. **Deterministic Value Normalization**: Standardizes Indian scales (`Cr`, `Lakh`), Western scales (`million`, `billion`), percentages, and currency units into floats (`normalized_value`).

### Fact Extraction API Endpoints
- `POST /api/documents/{document_id}/extract`: Trigger grounded fact extraction on a document.
- `GET /api/facts`: List all extracted facts with optional filtering (`document_id`, `subject`, `predicate`).
- `GET /api/facts/{fact_id}`: Retrieve details and verbatim source evidence for a specific fact.
- `GET /api/documents/{document_id}/facts`: Retrieve all facts extracted from a specific document.

---

## Fact Normalization & Context Preservation

FactLens normalizes equivalent representations without losing context:
- **Scales**: `$10M`, `$10 million`, `USD 10,000,000` $\rightarrow$ `10000000.0 USD`.
- **Units**: `1,200 employees`, `workforce of 1.2K` $\rightarrow$ `1200.0 employees`.
- **Currencies**: `$`, `USD`, `₹`, `INR`, `€`, `EUR`, `£`, `GBP`.
- **Periods**: `FY24`, `FY 2024`, `2023-24` $\rightarrow$ `FY2024`; `Q1 FY24` $\rightarrow$ `Q1 FY2024`.
- **Context Preservation**: Facts with matching values in different periods (e.g. `$10M in FY2024` vs `$10M in Q1 2024`) or regions (e.g. `$10M in North America` vs `$10M globally`) remain **distinct facts** with explicit context metadata.

---

## Cross-Document Relationship Reasoning Engine (4 Mandatory Cases)

FactLens pairs candidate facts across distinct documents and classifies each relationship into one of four mandatory outcome categories:

1. **`CORROBORATED`**: Facts with matching subjects, predicates, timeframes, and consistent values across documents.
2. **`CONTRADICTED`**: Facts with matching subjects, predicates, and timeframes, but mutually exclusive numerical values or conflicting statements.
3. **`CONTEXTUALLY_RECONCILED`**: Surface discrepancies resolved by temporal scope (FY22 vs FY24), operating scope (Standalone vs Consolidated), or currencies.
4. **`REASONING_FAILURE`**: Ambiguous evidence or low extraction confidence preventing explicit linking.

### Relationship API Endpoints
- `POST /api/relationships/analyze`: Run cross-document relationship analysis.
- `GET /api/relationships`: List all analyzed relationships with filters (`relationship_type`, `document_id`).
- `GET /api/relationships/{relationship_id}`: Retrieve single relationship details with source/target evidence quotes.

---

## Candidate Fact Matching & Retrieval

FactLens uses a 2-stage retrieval strategy to efficiently match candidate facts across documents without quadratic $O(N^2)$ LLM pairwise explosion:

1. **Stage 1 (Deterministic Property Filtering)**: Pre-filters candidate facts sharing compatible normalized subjects, predicates, value types, and units.
2. **Stage 2 (Cosine Vector Similarity)**: Ranks candidates using dense vector embeddings generated via `EmbeddingProvider` (`MockEmbeddingProvider` or `OpenAIEmbeddingProvider`).

### Candidate Retrieval Endpoint
- `GET /api/facts/{fact_id}/candidates`: Retrieve ranked candidate matching facts for a given fact with similarity scores and matching criteria metadata.

---

## Incremental Document Processing & Knowledge Updates

FactLens supports **incremental processing** (`POST /api/documents/{document_id}/process_incremental`) when adding new documents to an existing knowledge base:

1. **Zero Re-Extraction**: Ingesting Document B extracts facts **only** for Document B. Existing facts from Document A remain untouched.
2. **Targeted Knowledge Pairing**: Newly extracted facts are compared against existing facts across prior documents ($O(K \cdot N)$ complexity).
3. **Immutable Provenance**: Fact IDs and creation timestamps for older documents remain strictly unchanged.

---

## Reliability, Failure Handling & Honest Auditing

FactLens prioritizes honesty and audit transparency when extraction or reasoning is uncertain:

### 1. Failure Taxonomies
- **Extraction Failures**:
  - `no_meaningful_facts`: No structured facts identified in text.
  - `malformed_llm_output`: LLM response failed schema parsing.
  - `unsupported_claim`: Verbatim quote not grounded in source page text.
  - `invalid_evidence_id`: LLM hallucinated an unknown evidence ID.
- **Reasoning Failures**:
  - `insufficient_context`: Missing context needed to reconcile values.
  - `conflicting_temporal_information`: Conflicting or non-overlapping timeframes.
  - `ambiguous_scope`: Unclear geographic or operating scope.

### 2. Discrete Semantic Confidence Tiers
Confidence is presented as semantic categories rather than false mathematical probabilities:
- **`HIGH`** ($\ge 0.85$): Strong evidence grounding and deterministic match.
- **`MEDIUM`** ($0.50 \le c < 0.85$): Grounded facts with partial context overlap.
- **`LOW`** ($< 0.50$): Low confidence or ambiguous claims (flags `needs_review: true`).

### 3. Graceful Degradation & Privacy
- If AI extraction fails, the PDF document remains fully ingested in SQLite DB with evidence units accessible.
- Structured logger (`app.core.logging`) automatically sanitizes API keys and sensitive tokens (`OPENAI_API_KEY`, `Bearer`, `sk-...`) from log traces.

### 4. System Evaluation Metrics Endpoint
- `GET /api/evaluation/metrics`: Returns exact audit counts for system health:
  - `facts_extracted`
  - `grounded_facts`
  - `ungrounded_facts`
  - `relationships_classified`
  - `uncertain_relationships`
  - `extraction_failures`

---

## Starter Datasets

The repository includes two curated starter datasets under `data/starter-datasets/`:
- `delhivery/`: Corporate filings, prospectus, and earnings presentations.
- `india-macroeconomy/`: Macroeconomic reports from the Economic Survey, RBI, and IMF.

---

## License & Notes

Developed for engineering internship evaluation. All source evidence and reasoning traces are retained strictly for auditability.

