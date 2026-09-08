import React, { useState, useEffect } from 'react';
import { ArrowLeft, FileText, CheckSquare, Play } from 'lucide-react';
import { fetchDocumentDetails, extractDocumentFacts, DocumentItem, EvidenceUnit, FactItem } from '../services/api';

interface DocumentDetailProps {
  documentId: string;
  onBack: () => void;
}

export const DocumentDetail: React.FC<DocumentDetailProps> = ({ documentId, onBack }) => {
  const [doc, setDoc] = useState<DocumentItem | null>(null);
  const [evidenceUnits, setEvidenceUnits] = useState<EvidenceUnit[]>([]);
  const [facts, setFacts] = useState<FactItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [extracting, setExtracting] = useState<boolean>(false);
  const [selectedEvidenceId, setSelectedEvidenceId] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    try {
      const data = await fetchDocumentDetails(documentId);
      setDoc(data);
      setEvidenceUnits(data.evidence_units || []);
      setFacts(data.facts || []);
    } catch (err) {
      console.error('Failed to load document details', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [documentId]);

  const handleExtract = async () => {
    setExtracting(true);
    try {
      await extractDocumentFacts(documentId);
      await loadData();
    } catch (err: any) {
      alert(`Extraction failed: ${err.message}`);
    } finally {
      setExtracting(false);
    }
  };

  if (loading) {
    return (
      <div className="empty-state">
        <div className="empty-title">Loading Document Provenance...</div>
      </div>
    );
  }

  if (!doc) {
    return (
      <div className="empty-state">
        <div className="empty-title">Document Not Found</div>
        <button className="btn-secondary" onClick={onBack} style={{ marginTop: '12px' }}>
          Back to Documents
        </button>
      </div>
    );
  }

  return (
    <div>
      {/* Top Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button className="btn-secondary" onClick={onBack} style={{ padding: '6px' }}>
            <ArrowLeft size={14} />
          </button>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <FileText size={16} style={{ color: 'var(--text-secondary)' }} />
              <h1 style={{ fontSize: '16px', fontWeight: 600, color: 'var(--text-primary)' }}>
                {doc.original_filename}
              </h1>
              <span className="badge badge-neutral">{doc.page_count} Pages</span>
              <span className={`badge ${doc.extraction_status === 'completed' ? 'badge-corroborated' : 'badge-warning'}`}>
                {doc.extraction_status}
              </span>
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }} className="font-mono">
              SHA-256: {doc.file_hash.substring(0, 16)}...
            </div>
          </div>
        </div>

        <button className="btn-primary" onClick={handleExtract} disabled={extracting}>
          <Play size={12} />
          <span>{extracting ? 'Extracting Facts...' : 'Re-Extract Grounded Facts'}</span>
        </button>
      </div>

      {/* Split Viewer Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', height: 'calc(100vh - 160px)' }}>
        {/* Left Pane: Page Evidence Units */}
        <div className="table-container" style={{ display: 'flex', flexDirection: 'column' }}>
          <div style={{ padding: '10px 14px', borderBottom: '1px solid var(--border-subtle)', background: 'var(--bg-card)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '12px', fontWeight: 600 }}>Source Evidence Units ({evidenceUnits.length})</span>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>PyMuPDF Grounded Text</span>
          </div>

          <div style={{ flex: 1, overflowY: 'auto', padding: '12px' }}>
            {evidenceUnits.map((eu) => {
              const isSelected = selectedEvidenceId === eu.id;
              return (
                <div
                  key={eu.id}
                  id={`evidence-${eu.id}`}
                  style={{
                    backgroundColor: isSelected ? 'var(--accent-primary-subtle)' : 'var(--bg-surface)',
                    border: `1px solid ${isSelected ? 'var(--accent-primary)' : 'var(--border-subtle)'}`,
                    borderRadius: 'var(--radius-sm)',
                    padding: '12px',
                    marginBottom: '12px',
                    transition: 'all 0.15s ease',
                  }}
                  onClick={() => setSelectedEvidenceId(eu.id)}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span className="badge badge-neutral">Page {eu.page_number}</span>
                      <span style={{ fontSize: '10px', color: 'var(--text-muted)' }} className="font-mono">
                        {eu.id.substring(0, 8)}
                      </span>
                    </div>
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--text-primary)', whiteSpace: 'pre-wrap', lineHeight: '1.5' }}>
                    {eu.clean_text}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Pane: Derived Grounded Facts */}
        <div className="table-container" style={{ display: 'flex', flexDirection: 'column' }}>
          <div style={{ padding: '10px 14px', borderBottom: '1px solid var(--border-subtle)', background: 'var(--bg-card)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '12px', fontWeight: 600 }}>Extracted Grounded Facts ({facts.length})</span>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Backend Provenance Verified</span>
          </div>

          <div style={{ flex: 1, overflowY: 'auto', padding: '12px' }}>
            {facts.length === 0 ? (
              <div className="empty-state">
                <CheckSquare size={24} className="empty-icon" />
                <div className="empty-title">No Grounded Facts Extracted</div>
                <div className="empty-desc">Click "Re-Extract Grounded Facts" to trigger LLM fact extraction.</div>
              </div>
            ) : (
              facts.map((fact) => {
                const isLinked = selectedEvidenceId === fact.evidence_id;
                return (
                  <div
                    key={fact.id}
                    style={{
                      backgroundColor: isLinked ? 'var(--accent-primary-subtle)' : 'var(--bg-surface)',
                      border: `1px solid ${isLinked ? 'var(--accent-primary)' : 'var(--border-subtle)'}`,
                      borderRadius: 'var(--radius-sm)',
                      padding: '12px',
                      marginBottom: '12px',
                    }}
                    onClick={() => {
                      setSelectedEvidenceId(fact.evidence_id);
                      document.getElementById(`evidence-${fact.evidence_id}`)?.scrollIntoView({ behavior: 'smooth' });
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span style={{ fontWeight: 600, fontSize: '13px', color: 'var(--text-primary)' }}>
                          {fact.subject} — {fact.predicate}
                        </span>
                      </div>
                      <span className="badge badge-neutral">{fact.temporal_context || 'N/A'}</span>
                    </div>

                    <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--accent-primary)', marginBottom: '8px' }}>
                      {fact.value} {fact.unit ? `(${fact.unit})` : ''}
                      {fact.normalized_value !== null && fact.normalized_value !== undefined && (
                        <span style={{ fontSize: '11px', fontWeight: 400, color: 'var(--text-secondary)', marginLeft: '8px' }} className="font-mono">
                          Norm: {fact.normalized_value?.toLocaleString()}
                        </span>
                      )}
                    </div>

                    {/* Verbatim quote box */}
                    <div
                      style={{
                        backgroundColor: 'var(--bg-root)',
                        borderLeft: '3px solid var(--accent-primary)',
                        padding: '6px 10px',
                        borderRadius: '2px',
                        fontSize: '11px',
                        color: 'var(--text-secondary)',
                        fontStyle: 'italic',
                      }}
                    >
                      "{fact.verbatim_quote}"
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
