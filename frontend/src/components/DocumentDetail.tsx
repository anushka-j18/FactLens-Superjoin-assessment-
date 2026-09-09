import React, { useState, useEffect } from 'react';
import { ArrowLeft, FileText, CheckSquare, Play, AlertTriangle, Info } from 'lucide-react';
import { fetchDocumentDetails, extractDocumentFacts, DocumentItem, EvidenceUnit, FactItem } from '../services/api';
import { FactDetailModal } from './FactDetailModal';

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
  const [selectedFact, setSelectedFact] = useState<FactItem | null>(null);
  const [extractionMessage, setExtractionMessage] = useState<string | null>(null);

  const loadData = async () => {
    setLoading(true);
    try {
      const data = await fetchDocumentDetails(documentId);
      setDoc(data);
      setEvidenceUnits(data.evidence_units || []);
      setFacts(data.facts || []);
      if (data.error_message) {
        setExtractionMessage(data.error_message);
      }
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
    setExtractionMessage(null);
    try {
      const result = await extractDocumentFacts(documentId);
      if (result.extraction_status === 'mock_configured') {
        setExtractionMessage('LLM provider is configured as mock. Configure a supported LLM provider to extract facts.');
      } else if (result.error_message) {
        setExtractionMessage(result.error_message);
      }
      await loadData();
    } catch (err: any) {
      setExtractionMessage(err.message || 'Extraction failed');
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
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
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
              <span className={`badge ${
                doc.extraction_status === 'completed' ? 'badge-corroborated' :
                doc.extraction_status === 'mock_configured' ? 'badge-warning' :
                doc.extraction_status === 'failed' ? 'badge-contradicted' : 'badge-neutral'
              }`}>
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

      {/* Warning/Error Banner */}
      {extractionMessage && (
        <div
          style={{
            backgroundColor: doc.extraction_status === 'mock_configured' ? 'rgba(234, 179, 8, 0.1)' : 'rgba(239, 68, 68, 0.1)',
            border: `1px solid ${doc.extraction_status === 'mock_configured' ? 'var(--status-amber)' : 'var(--status-red)'}`,
            borderRadius: 'var(--radius-sm)',
            padding: '10px 14px',
            marginBottom: '12px',
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            fontSize: '12px',
            color: 'var(--text-primary)',
          }}
        >
          <AlertTriangle size={16} style={{ color: doc.extraction_status === 'mock_configured' ? 'var(--status-amber)' : 'var(--status-red)', flexShrink: 0 }} />
          <div>{extractionMessage}</div>
        </div>
      )}

      {/* Split Viewer Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', height: 'calc(100vh - 180px)' }}>
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
                        ID: {eu.id.substring(0, 8)}
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
                <div className="empty-title">Extracted Grounded Facts (0)</div>
                <div className="empty-desc" style={{ maxWidth: '320px', marginTop: '6px' }}>
                  {doc.extraction_status === 'mock_configured'
                    ? 'LLM provider is set to mock. Configure a supported LLM provider (OpenAI) to extract real facts.'
                    : 'Click "Re-Extract Grounded Facts" to trigger LLM fact extraction.'}
                </div>
                <button
                  className="btn-primary"
                  onClick={handleExtract}
                  disabled={extracting}
                  style={{ marginTop: '14px' }}
                >
                  <Play size={12} />
                  <span>{extracting ? 'Extracting Facts...' : 'Extract Grounded Facts'}</span>
                </button>
              </div>
            ) : (
              facts.map((fact) => {
                const isLinked = selectedEvidenceId === fact.evidence_id || (fact.evidence_ids && fact.evidence_ids.includes(selectedEvidenceId || ''));
                const confLevel = fact.confidence_level || 'HIGH';
                const badgeClass =
                  confLevel === 'HIGH' ? 'badge-corroborated' :
                  confLevel === 'MEDIUM' ? 'badge-reconciled' : 'badge-warning';

                return (
                  <div
                    key={fact.id}
                    style={{
                      backgroundColor: isLinked ? 'var(--accent-primary-subtle)' : 'var(--bg-surface)',
                      border: `1px solid ${isLinked ? 'var(--accent-primary)' : 'var(--border-subtle)'}`,
                      borderRadius: 'var(--radius-sm)',
                      padding: '12px',
                      marginBottom: '12px',
                      cursor: 'pointer',
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
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span className={`badge ${badgeClass}`}>{confLevel} CONFIDENCE</span>
                        <button
                          className="btn-secondary"
                          style={{ padding: '2px 6px', fontSize: '10px' }}
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedFact(fact);
                          }}
                        >
                          <Info size={10} style={{ marginRight: '3px' }} />
                          Inspect
                        </button>
                      </div>
                    </div>

                    <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--accent-primary)', marginBottom: '8px' }}>
                      {fact.value} {fact.unit ? `(${fact.unit})` : ''}
                      {fact.normalized_value !== null && fact.normalized_value !== undefined && (
                        <span style={{ fontSize: '11px', fontWeight: 400, color: 'var(--text-secondary)', marginLeft: '8px' }} className="font-mono">
                          Norm: {fact.normalized_value?.toLocaleString()}
                        </span>
                      )}
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', fontSize: '11px', color: 'var(--text-muted)' }}>
                      <span>Period: {fact.temporal_context || 'N/A'}</span>
                      <span>•</span>
                      <span>Scope: {fact.operating_scope || 'Company-wide'}</span>
                      <span>•</span>
                      <span className="font-mono">
                        Page {fact.page_number} ({fact.evidence_ids?.length || 1} evidence unit)
                      </span>
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

      {/* Fact Inspect Modal */}
      {selectedFact && (
        <FactDetailModal fact={selectedFact} onClose={() => setSelectedFact(null)} />
      )}
    </div>
  );
};

