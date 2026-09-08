# FactLens

> Evidence-first document intelligence for discovering, grounding, and comparing facts across PDFs.

---

## Problem

Enterprise intelligence, financial research, and policy analysis require comparing facts extracted across multiple PDF documents (prospectuses, annual reports, economic surveys, earnings filings). Today, this process suffers from five structural failure modes:

1. **Scattered Information**: Related metrics are buried across different pages, sections, or separate PDF filings.
2. **Syntactic Variation**: The same underlying claim is expressed differently across documents (e.g., `INR 4,600 Cr`, `₹46 billion`, `46,000,000,000`).
3. **Apparent Contradictions**: Facts appear conflicting on the surface, but are actually consistent when accounting for contextual parameters such as reporting period (FY22 vs FY24), scope (Standalone vs Consolidated), accounting standards (IndAS vs IFRS), or geographic region.
4. **LLM Hallucinations**: Standard RAG pipelines and direct LLM prompts paraphrase quotes, invent missing numbers, or cite non-existent page numbers.
5. **Quadratic Scaling Costs**: Comparing every extracted fact against every other fact using LLMs scales at $O(N^2)$, making multi-document analysis cost-prohibitive.

---

## Solution

FactLens provides an **evidence-first document intelligence architecture** that decouples document parsing, grounded fact extraction, value normalization, staged candidate retrieval, and cross-document relationship reasoning.

```
┌──────────────┐     ┌────────────────────────┐     ┌───────────────────────┐
│ PDF Upload   ├────►│ PyMuPDF Text & Page    ├────►│ Grounded Fact         │
│ Document     │     │ Evidence Extraction    │     │ Extraction (LLM + ID) │
└──────────────┘     └────────────────────────┘     └───────────┬───────────┘
                                                                │
                                                                ▼
┌──────────────┐     ┌────────────────────────┐     ┌───────────────────────┐
│ Evidence-    │     │ 4-Case Cross-Document  │     │ Deterministic Value   │
│ First UI     │◄────┤ Relationship Reasoning │◄────┤ & Context             │
│ Inspector    │     │ Classifier             │     │ Normalization         │
└──────────────┘     └────────────────────────┘     └───────────────────────┘
```

---

## Key Capabilities

- **PDF Ingestion & Provenance**: Accepts `.pdf` files up to 50MB, validates PDF binary headers, calculates SHA-256 hashes to prevent duplicate ingestion, and extracts page-level text with bounding box coordinates.
- **Grounded Fact Extraction**: Extracts subject-predicate-value triples using schema-guided LLM structured generation, enforced by backend evidence ID whitelisting and verbatim quote verification.
- **Context-Aware Normalization**: Zero-LLM deterministic standardization of scales (Lakh, Crore, Million, Billion), percentages (`14%` $\rightarrow$ `0.14`), currencies (`USD`, `INR`, `EUR`), and fiscal periods (`FY24` $\rightarrow$ `FY2024`).
- **2-Stage Staged Candidate Matching**: Combines Stage 1 deterministic property filtering (subject/predicate aliases) with Stage 2 dense vector embedding similarity (OpenAI or Mock provider) to reduce matching complexity from $O(N^2)$ to $O(K \cdot N)$.
- **4-Case Relationship Reasoning**: Categorizes cross-document fact pairings into four mandatory outcomes:
  1. `CORROBORATED`: Consistent facts for the same context.
  2. `CONTRADICTED`: Conflicting values for identical context.
  3. `CONTEXTUALLY_RECONCILED`: Surface differences explained by timeframe, scope, or currency.
  4. `REASONING_FAILURE`: Ambiguous context or ungrounded evidence.
- **Discrete Semantic Confidence Tiers**: Classifies confidence into discrete semantic tiers (`HIGH`, `MEDIUM`, `LOW`) with explicit `needs_review` flags rather than presenting false mathematical probabilities.
- **Incremental Knowledge Processing**: Processes new PDF uploads incrementally (`POST /api/documents/{id}/process_incremental`) against existing database knowledge without re-extracting or re-processing previously ingested documents.
- **Structured Error Logging**: Automatically redacts API keys (`OPENAI_API_KEY`, `Bearer`, `sk-...`) from all application log traces.

---

## Architecture

FactLens follows a clean decoupled client-server architecture:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          FactLens Web Client                                │
│       React 18 + TypeScript + Vite + Developer-Tool Design System          │
│  - Document Inspector (Split-view PDF text & derived grounded facts)       │
│  - Relationship Matrix (Side-by-side claim comparison & audit trail)        │
│  - System Audit Dashboard (Grounded vs ungrounded metrics & review items)  │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ REST API (JSON)
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                           FastAPI Backend                                   │
│ ┌───────────────────────┐ ┌────────────────────────┐ ┌────────────────────┐ │
│ │ Document Ingestion    │ │ Fact Extractor         │ │ Candidate Matcher  │ │
│ │ (PyMuPDF Parser)      │ │ (LLM + Provenance)     │ │ (Vector Embeddings)│ │
│ └───────────┬───────────┘ └───────────┬────────────┘ └─────────┬──────────┘ │
│             │                         │                        │            │
│ ┌───────────▼───────────┐ ┌───────────▼────────────┐ ┌─────────▼──────────┐ │
│ │ Fact Normalizer       │ │ Relationship Reasoner  │ │ System Logger      │ │
│ │ (Deterministic Rules) │ │ (4-Case Classifier)    │ │ (Data Sanitization)│ │
│ └───────────────────────┘ └────────────────────────┘ └────────────────────┘ │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ SQLAlchemy ORM
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                            Storage Layer                                    │
│   SQLite Database (Documents, EvidenceUnits, Facts, Embeddings, Rels)       │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Subsystem Boundaries:
- **Frontend**: Single-page application built with React 18, TypeScript, and Vite. Implements high-density tables, split-view document inspection, and side-by-side relationship audit cards.
- **Backend API**: FastAPI framework exposing REST endpoints for PDF upload, evidence retrieval, fact extraction, candidate retrieval, and relationship reasoning.
- **PDF Extraction Engine**: Powered by PyMuPDF (`fitz`). Converts binary PDF pages into structured `EvidenceUnit` records with clean text and line-level bounding box maps.
- **LLM Provider Layer**: Abstracted via `LLMProvider` interface. Supports `MockLLMProvider` for offline testing without API keys and `OpenAILLMProvider` (GPT-4o-mini) with exponential backoff retries.
- **Embedding Provider Layer**: Abstracted via `EmbeddingProvider` interface. Supports `MockEmbeddingProvider` (64-dimensional token hashing) and `OpenAIEmbeddingProvider` (`text-embedding-3-small`).
- **Reasoning Engine**: Combines deterministic rules for numeric and context matching with LLM structured decision-making for complex context reconciliation.

---

## Fact Model

Every fact extracted by FactLens is bound to exact source evidence. Below is a representative JSON output returned by `GET /api/facts/{fact_id}`:

```json
{
  "id": "7c9b8e21-4f32-4a1d-9e12-881b4f02a11b",
  "document_id": "c9ebca84-89c6-6abb-3f4d-dd27bcdd06cc",
  "evidence_id": "ev-3a12-4b98-9012",
  "page_number": 1,
  "subject": "Delhivery",
  "predicate": "revenue",
  "value": "INR 4,600 Cr",
  "normalized_value": 46000000000.0,
  "value_type": "currency",
  "unit": "INR",
  "currency": "INR",
  "temporal_context": "FY2024",
  "geographic_scope": "India",
  "operating_scope": "consolidated",
  "qualifiers": {
    "accounting_standard": "IndAS"
  },
  "verbatim_quote": "Delhivery revenue was INR 4,600 Cr in FY24.",
  "is_inferred": false,
  "extraction_confidence": 0.95,
  "extraction_status": "grounded",
  "confidence_level": "HIGH",
  "needs_review": false,
  "created_at": "2026-09-09T01:45:00Z"
}
```

---

## Relationship Model

FactLens pairs candidate facts across distinct documents and classifies each relationship into one of four mandatory outcome categories.

### 1. CORROBORATED
```json
{
  "id": "rel-01",
  "source_fact_id": "fact-docA-rev",
  "target_fact_id": "fact-docB-rev",
  "relationship_type": "CORROBORATED",
  "confidence_score": 0.95,
  "confidence_level": "HIGH",
  "needs_review": false,
  "reasoning_summary": "Corroborated: Document 'delhivery_fy24.pdf' and Document 'delhivery_investor_presentation.pdf' consistently report revenue as 'INR 4,600 Cr' for FY2024.",
  "reconciliation_context": {
    "matched_predicate": "revenue",
    "matched_value": "INR 4,600 Cr",
    "temporal_context": "FY2024"
  }
}
```

### 2. CONTRADICTED
```json
{
  "id": "rel-02",
  "source_fact_id": "fact-docA-profit",
  "target_fact_id": "fact-docB-profit",
  "relationship_type": "CONTRADICTED",
  "confidence_score": 0.90,
  "confidence_level": "HIGH",
  "needs_review": false,
  "reasoning_summary": "Contradicted: Document 'delhivery_draft_filing.pdf' states Net Profit was 'INR 100 Cr' while Document 'delhivery_audited_report.pdf' states 'INR 250 Cr' for FY2024.",
  "reconciliation_context": {
    "conflict_type": "value_mismatch",
    "source_value": "INR 100 Cr",
    "target_value": "INR 250 Cr"
  }
}
```

### 3. CONTEXTUALLY_RECONCILED
```json
{
  "id": "rel-03",
  "source_fact_id": "fact-docA-fy22",
  "target_fact_id": "fact-docB-fy24",
  "relationship_type": "CONTEXTUALLY_RECONCILED",
  "confidence_score": 0.88,
  "confidence_level": "HIGH",
  "needs_review": false,
  "reasoning_summary": "Contextually Reconciled: Surface difference between 'INR 3,800 Cr' and 'INR 4,600 Cr' is explained by timeframe difference (FY2022 vs FY2024).",
  "reconciliation_context": {
    "reconciliation_reasons": ["timeframe difference (FY2022 vs FY2024)"]
  }
}
```

### 4. REASONING_FAILURE / NEEDS REVIEW
```json
{
  "id": "rel-04",
  "source_fact_id": "fact-docA-ambiguous",
  "target_fact_id": "fact-docB-ambiguous",
  "relationship_type": "REASONING_FAILURE",
  "confidence_score": 0.40,
  "confidence_level": "LOW",
  "needs_review": true,
  "failure_reason": "insufficient_context",
  "reasoning_summary": "Extraction / Reasoning Failure [insufficient_context]: Unable to conclusively reconcile values due to ambiguous context.",
  "reconciliation_context": {
    "failure_reason": "insufficient_context"
  }
}
```

---

## Evidence Grounding & Anti-Hallucination Guardrails

In standard LLM pipelines, model hallucinations invent quotes, fabricate evidence IDs, or misattribute source page numbers. FactLens enforces an **Evidence-First Architecture** where LLM candidate outputs are validated deterministically by backend code:

1. **Backend ID Whitelisting**: Before triggering extraction, the backend compiles a list of valid database `evidence_id`s for that document and injects them into the LLM prompt. Upon receiving LLM output, the backend verifies that every returned `evidence_id` belongs to an existing `EvidenceUnit` of that document. Any hallucinated ID results in immediate rejection.
2. **Verbatim Quote Verification**: The backend deterministically matches `verbatim_quote` strings against `clean_text` and `raw_text` of the source page. If the quote is missing or paraphrased beyond an 85% token overlap threshold, the fact is rejected.
3. **Deterministic Value Normalization**: Numeric values are normalized in Python (`FactNormalizer`) rather than relying on LLM arithmetic.

---

## Reasoning Approach

FactLens executes a multi-step hybrid reasoning pipeline:

1. **Normalized Property Comparison**: Subject and predicate strings are matched against alias dictionaries (`revenue` $\approx$ `sales` $\approx$ `turnover`).
2. **Numeric & Context Match**:
   - If normalized values match AND temporal/geographic/scope metadata match $\rightarrow$ **`CORROBORATED`**.
   - If normalized values differ AND temporal/geographic/scope metadata match $\rightarrow$ **`CONTRADICTED`**.
   - If normalized values differ BUT temporal context differs (e.g., FY22 vs FY24) or scope differs (Standalone vs Consolidated) $\rightarrow$ **`CONTEXTUALLY_RECONCILED`**.
3. **LLM Reasoning Fallback**: For ambiguous statements where deterministic rules yield confidence $< 0.50$, the candidate pair with evidence snippets is passed to the LLM reasoning judge.

---

## Why Not Just Use an LLM?

Relying solely on an LLM for multi-document fact matching fails in production for five core reasons:

| Engineering Requirement | Direct LLM / Naive RAG | FactLens Architecture |
| :--- | :--- | :--- |
| **Computational Complexity** | $O(N^2)$ pairwise LLM calls | $O(K \cdot N)$ staged retrieval + vector search |
| **Provenance Integrity** | LLMs hallucinate non-existent quotes & page numbers | Deterministic backend ID whitelisting & string matching |
| **Arithmetic Precision** | LLMs struggle with unit conversions ($12.4\text{M} \rightarrow 12,400,000$) | Python-based deterministic normalization |
| **Auditability** | Black-box output ("These facts contradict") | Structured audit trail with exact source text quotes |
| **Incremental Updates** | Must re-prompt full context on every edit | Incremental processing of new document facts only |

---

## Four Required Assignment Cases

FactLens handles all four core relationship outcomes required by the assignment specification:

### Case 1: Equivalent facts with different wording $\rightarrow$ `CORROBORATED`
- **Document A**: *"Delhivery revenue was INR 4,600 Cr in FY24."*
- **Document B**: *"In FY24, Delhivery reported turnover of ₹4,600 Crores."*
- **Outcome**: `CORROBORATED` (Both statements express normalized value `46000000000.0 INR` for period `FY2024`).

### Case 2: Same context but incompatible values $\rightarrow$ `CONTRADICTED`
- **Document A**: *"Delhivery FY24 Net Profit was INR 100 Cr."*
- **Document B**: *"Delhivery FY24 Net Profit was INR 250 Cr."*
- **Outcome**: `CONTRADICTED` (Direct numerical conflict for identical timeframe `FY2024` and entity `Delhivery`).

### Case 3: Different periods/scopes/units $\rightarrow$ `CONTEXTUALLY_RECONCILED`
- **Document A**: *"Delhivery reported FY22 Revenue of INR 3,800 Cr."*
- **Document B**: *"Delhivery reported FY24 Revenue of INR 4,600 Cr."*
- **Outcome**: `CONTEXTUALLY_RECONCILED` (Surface discrepancy resolved by timeframe difference FY2022 vs FY2024).

### Case 4: Ambiguous statement $\rightarrow$ `REASONING_FAILURE`
- **Document A**: *"Operating updates reflect growth."* (Low extraction confidence, ungrounded quote).
- **Outcome**: `REASONING_FAILURE` (Flags `needs_review: true` with reason `insufficient_context`).

---

## Setup and Run Instructions

### Prerequisites
- **Python**: 3.11+
- **Node.js**: 18+
- **npm**: 9+

### 1. Clone & Configure Environment
```bash
git clone https://github.com/anushka-j18/FactLens-Superjoin-assessment-.git
cd FactLens-Superjoin-assessment-
cp .env.example .env
```

### 2. Backend Setup
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
Backend API will be available at `http://localhost:8000`.

### 3. Frontend Setup
In a new terminal window:
```bash
cd frontend
npm install
npm run dev
```
Web interface will be available at `http://localhost:5173`.

### 4. Upload PDF Documents
- Open `http://localhost:5173` in your browser.
- Click **Upload PDF** in the top navigation bar.
- Select starter PDFs from `data/starter-datasets/delhivery/` or `data/starter-datasets/india-macroeconomy/`.
- Click **Start Ingestion** to trigger PDF page parsing, grounded fact extraction, and cross-document relationship matrix generation.

---

## Environment Variables

Sample `.env.example`:

```ini
APP_NAME=FactLens
ENVIRONMENT=development
BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
ALLOWED_ORIGINS=["http://localhost:5173","http://127.0.0.1:5173"]

# LLM Provider: 'mock' (default, no API key needed) or 'openai'
LLM_PROVIDER=mock
OPENAI_API_KEY=your_openai_api_key_here

# Embedding Provider: 'mock' (default) or 'openai'
EMBEDDING_PROVIDER=mock
```

---

## API Documentation

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/documents` | Upload a PDF file (max 50MB, SHA-256 hash checked). |
| `GET` | `/api/documents` | List all uploaded PDF documents. |
| `GET` | `/api/documents/{id}` | Get document metadata and evidence units. |
| `POST` | `/api/documents/{id}/extract` | Trigger grounded fact extraction on a document. |
| `POST` | `/api/documents/{id}/process_incremental` | Process newly uploaded document incrementally. |
| `GET` | `/api/facts` | List extracted facts with filters (`subject`, `predicate`). |
| `GET` | `/api/facts/{id}/candidates` | Retrieve 2-stage vector semantic candidate matches. |
| `POST` | `/api/relationships/analyze` | Run cross-document relationship reasoning matrix. |
| `GET` | `/api/relationships` | List relationships filtered by `relationship_type`. |
| `GET` | `/api/evaluation/metrics` | Retrieve transparent system audit counts. |
| `GET` | `/health` | API health check and provider status. |

---

## Testing

### Run Backend Pytest Suite
```bash
cd backend
./venv/bin/pytest
```
Output: `33 passed in 0.60s`

### Run Frontend Type Check & Production Build
```bash
cd frontend
npx tsc --noEmit
npm run build
```

---

## Limitations

FactLens prioritizes audit honesty over false certainty. Known current limitations include:

1. **Scanned / Image PDFs**: PyMuPDF extracts text layers natively. Scanned image-only PDFs require pre-processing with OCR (e.g., Tesseract).
2. **Complex Embedded Tables**: Multi-header nested tables in PDFs may split tokens across lines during standard text extraction.
3. **Implicit Claims**: Facts that require multi-hop background domain knowledge not present in the document text are marked as `REASONING_FAILURE` to preserve provenance transparency.

---

## Next Steps

- **OCR Integration**: Integrate Tesseract / PaddleOCR for image-only scanned PDFs.
- **Advanced Table Parsing**: Integrate `pdfplumber` or `unstructured` for multi-row complex table extraction.
- **Scalable Vector Database**: Migrate SQLite vector embeddings to Pgvector or Qdrant for production scale (>100k documents).
- **Human-in-the-Loop Feedback**: Allow analysts to confirm or correct `NEEDS_REVIEW` relationship classifications directly in the UI.

---

## AI Tools Used

- **LLM Usage**: OpenAI GPT-4o-mini used via `LLMProvider` abstraction for structured JSON fact extraction and ambiguous relationship decision-making.
- **Embedding Usage**: OpenAI `text-embedding-3-small` used via `EmbeddingProvider` for dense vector candidate retrieval.
- **Deterministic Logic**: Python code handles PDF binary validation, SHA-256 hash checks, PyMuPDF evidence unit creation, numeric scale normalization, verbatim quote verification, and logger data sanitization.
- **Development Agent**: Built with Antigravity AI agent.

---

## Video Demo

[Demo video](YOUR_VIDEO_LINK)

---

## Additional Notes

- **Database Storage**: Local SQLite database located at `backend/factlens.db`.
- **License**: Engineering internship assignment repository. Developed for Superjoin Fact Knowledge Layer evaluation.
