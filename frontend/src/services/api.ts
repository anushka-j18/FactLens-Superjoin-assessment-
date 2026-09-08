export interface DocumentItem {
  id: string;
  filename: string;
  original_filename: string;
  file_size: number;
  file_hash: string;
  page_count: number;
  processing_status: string;
  extraction_status: string;
  error_message?: string | null;
  knowledge_layer_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeLayerItem {
  id: string;
  name: string;
  description?: string | null;
  created_at: string;
  updated_at: string;
  document_count: number;
  documents?: DocumentItem[];
}

export interface EvidenceUnit {
  id: string;
  document_id: string;
  page_number: number;
  raw_text: string;
  clean_text: string;
  location_metadata: {
    page_width?: number;
    page_height?: number;
    text_blocks?: Array<{
      bbox: [number, number, number, number];
      lines: Array<{
        text: string;
        bbox: [number, number, number, number];
      }>;
    }>;
  };
  created_at: string;
}

export interface FactItem {
  id: string;
  document_id: string;
  evidence_id: string;
  page_number: number;
  subject: string;
  predicate: string;
  value: string;
  normalized_value?: number | null;
  value_type: string;
  unit?: string | null;
  currency?: string | null;
  temporal_context?: string | null;
  geographic_scope?: string | null;
  operating_scope?: string | null;
  qualifiers: Record<string, any>;
  verbatim_quote: string;
  is_inferred: boolean;
  extraction_confidence: number;
  extraction_status: string;
  confidence_level: 'HIGH' | 'MEDIUM' | 'LOW';
  needs_review: boolean;
  created_at: string;
  document?: DocumentItem;
  evidence_unit?: EvidenceUnit;
}

export interface FactRelationship {
  id: string;
  source_fact_id: string;
  target_fact_id: string;
  relationship_type: 'CORROBORATED' | 'CONTRADICTED' | 'CONTEXTUALLY_RECONCILED' | 'REASONING_FAILURE';
  confidence_score: number;
  confidence_level: 'HIGH' | 'MEDIUM' | 'LOW';
  needs_review: boolean;
  failure_reason?: string | null;
  reasoning_summary: string;
  reconciliation_context: Record<string, any>;
  created_at: string;
  source_fact?: FactItem;
  target_fact?: FactItem;
}

export interface EvaluationMetrics {
  facts_extracted: number;
  grounded_facts: number;
  ungrounded_facts: number;
  relationships_classified: number;
  uncertain_relationships: number;
  extraction_failures: number;
  documents_processed: number;
  documents_failed: number;
}

export interface CandidateMatch {
  fact_id: string;
  similarity_score: number;
  matching_criteria: Record<string, any>;
  candidate_fact?: FactItem;
}

export interface CandidateMatchResponse {
  target_fact_id: string;
  total_candidates: number;
  candidates: CandidateMatch[];
}

const API_BASE = '';

export async function fetchHealth() {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error(`Health check failed: ${res.status}`);
  return res.json();
}

export async function uploadDocument(file: File): Promise<DocumentItem> {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE}/api/documents`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const errData = await res.json().catch(() => ({ detail: 'Upload failed' }));
    throw new Error(errData.detail || `Upload failed with status ${res.status}`);
  }

  return res.json();
}

export async function fetchDocuments(): Promise<DocumentItem[]> {
  const res = await fetch(`${API_BASE}/api/documents`);
  if (!res.ok) throw new Error(`Failed to fetch documents: ${res.status}`);
  const data = await res.json();
  return data.documents || [];
}

export async function fetchDocumentDetails(id: string): Promise<DocumentItem & { evidence_units: EvidenceUnit[]; facts: FactItem[] }> {
  const res = await fetch(`${API_BASE}/api/documents/${id}`);
  if (!res.ok) throw new Error(`Failed to fetch document ${id}: ${res.status}`);
  return res.json();
}

export async function extractDocumentFacts(id: string) {
  const res = await fetch(`${API_BASE}/api/documents/${id}/extract`, {
    method: 'POST',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Extraction failed' }));
    throw new Error(err.detail || 'Extraction failed');
  }
  return res.json();
}

export async function fetchFacts(params?: { document_id?: string; subject?: string; predicate?: string }): Promise<FactItem[]> {
  const query = new URLSearchParams();
  if (params?.document_id) query.append('document_id', params.document_id);
  if (params?.subject) query.append('subject', params.subject);
  if (params?.predicate) query.append('predicate', params.predicate);

  const res = await fetch(`${API_BASE}/api/facts?${query.toString()}`);
  if (!res.ok) throw new Error(`Failed to fetch facts: ${res.status}`);
  const data = await res.json();
  return data.facts || [];
}

export async function fetchFactDetails(id: string): Promise<FactItem> {
  const res = await fetch(`${API_BASE}/api/facts/${id}`);
  if (!res.ok) throw new Error(`Failed to fetch fact details: ${res.status}`);
  return res.json();
}

export async function fetchDocumentFacts(documentId: string): Promise<FactItem[]> {
  const res = await fetch(`${API_BASE}/api/documents/${documentId}/facts`);
  if (!res.ok) throw new Error(`Failed to fetch document facts: ${res.status}`);
  return res.json();
}

export async function fetchFactCandidates(factId: string): Promise<CandidateMatchResponse> {
  const res = await fetch(`${API_BASE}/api/facts/${factId}/candidates`);
  if (!res.ok) throw new Error(`Failed to fetch candidates: ${res.status}`);
  return res.json();
}

export async function analyzeRelationships(documentIds?: string[]) {
  const res = await fetch(`${API_BASE}/api/relationships/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ document_ids: documentIds }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Relationship analysis failed' }));
    throw new Error(err.detail || 'Relationship analysis failed');
  }
  return res.json();
}

export async function fetchRelationships(params?: { relationship_type?: string; document_id?: string }): Promise<FactRelationship[]> {
  const query = new URLSearchParams();
  if (params?.relationship_type) query.append('relationship_type', params.relationship_type);
  if (params?.document_id) query.append('document_id', params.document_id);

  const res = await fetch(`${API_BASE}/api/relationships?${query.toString()}`);
  if (!res.ok) throw new Error(`Failed to fetch relationships: ${res.status}`);
  const data = await res.json();
  return data.relationships || [];
}

export async function fetchEvaluationMetrics(): Promise<EvaluationMetrics> {
  const res = await fetch(`${API_BASE}/api/evaluation/metrics`);
  if (!res.ok) throw new Error(`Failed to fetch evaluation metrics: ${res.status}`);
  return res.json();
}

export async function fetchKnowledgeLayers(): Promise<KnowledgeLayerItem[]> {
  const res = await fetch(`${API_BASE}/api/knowledge-layers`);
  if (!res.ok) throw new Error(`Failed to fetch knowledge layers: ${res.status}`);
  const data = await res.json();
  return data.knowledge_layers || [];
}

export async function createKnowledgeLayer(name: string, description?: string): Promise<KnowledgeLayerItem> {
  const res = await fetch(`${API_BASE}/api/knowledge-layers`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, description }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Failed to create knowledge layer' }));
    throw new Error(err.detail || 'Failed to create knowledge layer');
  }
  return res.json();
}

export async function fetchKnowledgeLayerDetails(id: string): Promise<KnowledgeLayerItem> {
  const res = await fetch(`${API_BASE}/api/knowledge-layers/${id}`);
  if (!res.ok) throw new Error(`Failed to fetch knowledge layer ${id}: ${res.status}`);
  return res.json();
}

export async function deleteKnowledgeLayer(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/knowledge-layers/${id}`, { method: 'DELETE' });
  if (!res.ok) throw new Error(`Failed to delete knowledge layer: ${res.status}`);
}

export async function uploadDocumentsToKnowledgeLayer(klId: string, files: File[]): Promise<DocumentItem[]> {
  const formData = new FormData();
  files.forEach((file) => formData.append('files', file));

  const res = await fetch(`${API_BASE}/api/knowledge-layers/${klId}/documents`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const errData = await res.json().catch(() => ({ detail: 'Batch upload failed' }));
    throw new Error(errData.detail || `Upload failed with status ${res.status}`);
  }

  return res.json();
}
