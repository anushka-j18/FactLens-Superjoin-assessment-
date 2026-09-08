# FactLens Architecture & System Design

FactLens is an evidence-first document intelligence platform that ingests multiple PDF documents, extracts structured numerical and semantic facts with verbatim provenance, and analyzes relationships between facts across documents.

---

## 1. System Architecture & Boundaries

```
┌────────────────────────────────────────────────────────────────────────┐
│                          FactLens Frontend                             │
│       React 18 + TypeScript + Vite + Developer-Focused CSS           │
│  - Split-view document viewer with evidence bounding box highlights   │
│  - Interactive relationship matrices & audit trails                    │
│  - Dynamic PDF upload & ingestion triggers                            │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP / REST API
┌───────────────────────────────────▼────────────────────────────────────┐
│                           FastAPI Backend                              │
│ ┌──────────────────────┐ ┌────────────────────┐ ┌────────────────────┐ │
│ │  Ingestion Service   │ │ Extraction Service │ │ Reasoning Engine   │ │
│ │  (PyMuPDF Parser)    │ │  (LLM + Verbatim)  │ │(4-Case Classifier) │ │
│ └──────────┬───────────┘ └─────────┬──────────┘ └─────────┬──────────┘ │
└────────────┼───────────────────────┼──────────────────────┼────────────┘
             │                       │                      │
┌────────────▼───────────────────────▼──────────────────────▼────────────┐
│                             Storage Layer                              │
│  SQLite (SQLAlchemy ORM)  •  Vector Embeddings  •  Raw PDF Storage     │
└────────────────────────────────────────────────────────────────────────┘
```

### Component Boundaries:
1. **Frontend**: Pure client-side UI for uploading PDFs, inspecting extracted facts, viewing verbatim evidence side-by-side with original PDF pages, and reviewing relationship audit trails.
2. **Backend REST API**: FastAPI server exposing endpoints for document upload, processing status, fact retrieval, candidate matching, and relationship reasoning.
3. **Ingestion Layer**: PyMuPDF-based parser responsible solely for converting PDF documents into structured pages, text blocks, and line bounding box coordinates.
4. **Extraction Layer**: Combines LLM structured generation with deterministic quote-matching to output structured facts containing exact page character offsets and bounding boxes.
5. **Reasoning Layer**: Candidate pairing engine (via semantic embeddings) + LLM-based 4-case classifier (Corroborated, Contradicted, Contextually Reconciled, Reasoning Failure).
6. **Storage Layer**: SQLite via SQLAlchemy storing document metadata, raw pages, extracted facts, candidate pairs, and relationship decisions.

---

## 2. End-to-End Data Flow

```
1. PDF Upload ────► 2. Ingestion ────► 3. Fact Extraction ────► 4. Candidate Matching
   (Save file &       (PyMuPDF extract   (LLM JSON Schema +       (Embedding cosine
    calc SHA-256)      pages & boxes)     Verbatim validation)     similarity threshold)
                                                                            │
                                                                            ▼
6. UI Rendering ◄──── 5. Relationship Reasoning ◄───────────────────────────┘
   (Evidence viewer &    (Classify: Corroborated / Contradicted /
    reasoning trail)      Reconciled / Extraction Failure)
```

---

## 3. Database Schema & Proposed Entities

```
+------------------+       +-------------------+       +--------------------+
|    Document      |       |   DocumentPage    |       |        Fact        |
+------------------+       +-------------------+       +--------------------+
| id (UUID/PK)     |<───┐  | id (PK)           |  ┌───>| id (UUID/PK)       |
| filename         |    └──| document_id (FK)  |  │    | document_id (FK)   |
| hash (SHA-256)   |       | page_number       |  │    | page_number        |
| page_count       |       | text_content      |──┼───>| fact_type          |
| status           |       | bbox_data (JSON)  |  │    | metric_name        |
| created_at       |       +-------------------+  │    | raw_value          |
+------------------+                              │    | normalized_value   |
                                                  │    | unit               |
                                                  │    | verbatim_quote     |
                                                  │    | bbox (JSON)        |
                                                  │    +---------┬----------+
                                                                 │
                                                                 ▼
                                                       +--------------------+
                                                       |  FactRelationship  |
                                                       +--------------------+
                                                       | id (UUID/PK)       |
                                                       | source_fact_id(FK) |
                                                       | target_fact_id(FK) |
                                                       | relationship_type  |
                                                       | confidence_score   |
                                                       | reasoning_summary  |
                                                       | reconciliation_ctx |
                                                       +--------------------+
```

### Detailed Entity Specs:
- **`Document`**: Tracks uploaded files, SHA-256 hashes to prevent duplicate ingestion, processing status, and page counts.
- **`DocumentPage`**: Stores plain text extracted per page alongside line-level bounding box maps for instant evidence lookup.
- **`Fact`**: Captures extracted claims (numerical or semantic), standard metric names, raw values, normalized numeric values, units, exact verbatim quote strings, and JSON bounding boxes.
- **`FactEmbedding`**: Stores dense vector representations of fact statements for semantic candidate matching across documents.
- **`FactRelationship`**: Stores directed or undirected pairwise evaluations between facts across documents, categorized into one of four mandatory outcomes.

---

## 4. AI vs. Deterministic Responsibilities

| Subsystem | Deterministic Responsibilities | AI / LLM Responsibilities |
| :--- | :--- | :--- |
| **Ingestion** | PyMuPDF page parsing, layout line/block extraction, SHA-256 hashing. | None. |
| **Fact Extraction** | Verbatim quote validation, character index matching, numeric standardizing ($1,200 \rightarrow 1200000000$). | Unstructured text understanding, identifying entity/attribute pairs, extracting candidate facts. |
| **Candidate Matching** | Entity-attribute matching rules, vector similarity index calculations. | Dense semantic embedding generation. |
| **Relationship Reasoning** | Pre-filtering non-overlapping metrics, exact numeric match/mismatch checks. | Deep context comparison, evaluating timeframe differences (FY22 vs FY24), scope differences (standalone vs consolidated), classifying relationship into 4 required outcomes. |

---

## 5. Relationship Reasoning Strategy (4 Mandatory Cases)

FactLens evaluates pairs of candidate facts across documents and classifies them into exactly one of four core categories:

1. **`CORROBORATED`**:
   - Both facts reference the same underlying metric/entity/timeframe and report consistent values or assertions.
   - *Example*: Document A and Document B both state Delhivery FY24 Revenue was ₹4,600 Cr.

2. **`CONTRADICTED / LIKELY CONTRADICTION`**:
   - Both facts reference the exact same entity, metric, and timeframe, but report mutually exclusive numbers or conflicting assertions.
   - *Example*: Document A states FY24 Net Profit was ₹100 Cr while Document B states Net Profit was ₹150 Cr for the same period and reporting entity.

3. **`CONTEXTUALLY RECONCILED`**:
   - The numbers or statements appear different on the surface, but are resolved by contextual factors such as different reporting timeframes (FY22 vs FY24), scope (Standalone vs Consolidated), accounting standards (IndAS vs IFRS), or currency units.
   - *Example*: Document A lists 2022 Revenue while Document B lists 2024 Revenue; both are true in their respective contextual scopes.

4. **`EXTRACTION / REASONING FAILURE`**:
   - The facts cannot be conclusively linked because evidence is incomplete, verbatim quotes cannot be verified against source text, or LLM output is ambiguous.
   - Preserves audit transparency rather than making false assertions.

---

## 6. Provider Abstractions & Extensibility

- **LLM Abstraction**: `LLMProvider` interface defining standard async `complete()` and `structured_predict()` methods. Allows seamless switching between OpenAI, Anthropic, Gemini, or local models via `.env` configuration.
- **Embedding Abstraction**: `EmbeddingProvider` interface defining `embed_text()` and `embed_batch()`. Supports OpenAI embeddings, HuggingFace sentence-transformers, or custom vector providers.
## 7. LLM Rationale & Backend Provenance Validation

### Why LLMs are Used for Fact Extraction
Unstructured PDF documents (financial filings, annual reports, economic surveys) express facts in highly diverse syntactic structures, tables, footnotes, and narrative prose. LLMs provide:
1. **Domain-Agnostic Understanding**: Ability to identify arbitrary entity-attribute-value triples without brittle hardcoded regex rules or fixed schemas.
2. **Context & Metadata Extraction**: Disambiguating temporal scope (e.g., FY24, Q4 FY24) and qualifiers (accounting standards, reporting currency).
3. **Structured Normalization**: Formatting extracted data into standardized JSON structures adhering to backend Pydantic schemas.

### Why Provenance is Validated by Backend
LLMs are prone to hallucinations, including inventing non-existent evidence IDs, page numbers, or paraphrasing quotes. FactLens enforces an **Evidence-First Architecture** where LLM outputs are treated as *untrusted candidates*:
1. **Backend ID Whitelisting**: The backend injects real database `evidence_id`s into the LLM prompt. Upon receiving LLM candidate output, the backend verifies that `evidence_id` belongs to an existing `EvidenceUnit` of that document. Any hallucinated ID results in immediate rejection.
2. **Verbatim Quote Verification**: The backend deterministically matches `verbatim_quote` strings against `clean_text` and `raw_text` of the source page. If the LLM invents or heavily paraphrases a quote, the fact is rejected.
3. **Deterministic Value Normalization**: Raw numeric strings (e.g. `₹4,600 Cr`, `$12.4 million`, `14%`) are normalized into standard float values (e.g. `46000000000.0`, `12400000.0`, `0.14`) deterministically by backend code rather than relying on LLM arithmetic.


## 9. Cross-Document Relationship Reasoning Strategy (4 Mandatory Cases)

FactLens pairs candidate facts across distinct documents and classifies each relationship into exactly one of four core outcome categories.

```
                  ┌─────────────────────────────────────┐
                  │ Candidate Fact Pair across Docs A&B │
                  └──────────────────┬──────────────────┘
                                     │
                  ┌──────────────────▼──────────────────┐
                  │ FactNormalizer.are_facts_comparable │
                  └──────────────────┬──────────────────┘
                                     │
           ┌─────────────────────────┼─────────────────────────┐
           │                         │                         │
┌──────────▼──────────┐   ┌──────────▼──────────┐   ┌──────────▼──────────┐
│   Values & Context  │   │  Values Conflict,   │   │  Values Differ, but │
│    Match Exactly    │   │  Period/Scope Match │   │ Period/Scope Differ │
└──────────┬──────────┘   └──────────┬──────────┘   └──────────┬──────────┘
           │                         │                         │
┌──────────▼──────────┐   ┌──────────▼──────────┐   ┌──────────▼──────────┐
│    CORROBORATED     │   │     CONTRADICTED    │   │     CONTEXTUALLY    │
│                     │   │                     │   │     RECONCILED      │
└─────────────────────┘   └─────────────────────┘   └─────────────────────┘
                                                               │
                                                    If evidence is ungrounded
                                                    or confidence < 0.5:
                                                    ┌─────────────────────┐
                                                    │  REASONING_FAILURE  │
                                                    └─────────────────────┘
```

### Detailed 4-Case Category Specifications
1. **`CORROBORATED`**:
   - Both documents report consistent numerical values or assertions for the same subject, predicate, and temporal/geographic scope.
   - *Example*: Document A and Document B both state Delhivery FY24 Revenue was `INR 4,600 Cr`.
2. **`CONTRADICTED`**:
   - Documents report mutually exclusive numerical values or assertions for the exact same subject, predicate, timeframe, and operating scope.
   - *Example*: Document A states FY24 Revenue was `INR 4,600 Cr` while Document B states `INR 5,200 Cr` for the same entity and fiscal year.
3. **`CONTEXTUALLY_RECONCILED`**:
   - Surface discrepancies between numbers or statements are resolved by contextual factors such as different reporting periods (FY22 vs FY24), operating scopes (Standalone vs Consolidated), or currencies (`INR` vs `USD`).
   - *Example*: Document A lists FY22 Revenue as `INR 3,800 Cr` while Document B lists FY24 Revenue as `INR 4,600 Cr`. Both are true within their respective fiscal scopes.
4. **`REASONING_FAILURE`**:
   - Evidence confidence is below threshold, text is ambiguous, or verbatim quotes cannot be verified against source text. Preserves audit transparency rather than asserting false links.



