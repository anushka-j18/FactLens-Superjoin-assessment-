import React, { useState, useEffect } from 'react';
import { X, CheckSquare, FileText, GitCompare } from 'lucide-react';
import { fetchFactCandidates, FactItem, CandidateMatch } from '../services/api';

interface FactDetailModalProps {
  fact: FactItem | null;
  onClose: () => void;
}

export const FactDetailModal: React.FC<FactDetailModalProps> = ({ fact, onClose }) => {
  const [candidates, setCandidates] = useState<CandidateMatch[]>([]);
  const [loadingCandidates, setLoadingCandidates] = useState<boolean>(false);

  useEffect(() => {
    if (fact) {
      setLoadingCandidates(true);
      fetchFactCandidates(fact.id)
        .then((res) => setCandidates(res.candidates || []))
        .catch(() => setCandidates([]))
        .finally(() => setLoadingCandidates(false));
    }
  }, [fact]);

  if (!fact) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '720px' }}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <CheckSquare size={16} style={{ color: 'var(--status-green)' }} />
            <span className="modal-title">{fact.subject} — {fact.predicate}</span>
          </div>
          <button onClick={onClose} style={{ color: 'var(--text-muted)' }}>
            <X size={16} />
          </button>
        </div>

        <div className="modal-body">
          {/* Main Value & Normalized Output */}
          <div style={{ backgroundColor: 'var(--bg-card)', padding: '16px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)', marginBottom: '16px' }}>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '4px' }}>
              Extracted Fact Value
            </div>
            <div style={{ fontSize: '20px', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '4px' }}>
              {fact.value} {fact.unit ? `(${fact.unit})` : ''}
            </div>
            {fact.normalized_value !== null && fact.normalized_value !== undefined && (
              <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }} className="font-mono">
                Normalized Numeric Value: {fact.normalized_value.toLocaleString()} {fact.currency || ''}
              </div>
            )}
          </div>

          {/* Context Attributes */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px', marginBottom: '16px' }}>
            <div style={{ backgroundColor: 'var(--bg-card)', padding: '10px 12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
              <div style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Timeframe</div>
              <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)' }}>{fact.temporal_context || 'N/A'}</div>
            </div>
            <div style={{ backgroundColor: 'var(--bg-card)', padding: '10px 12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
              <div style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Operating Scope</div>
              <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)' }}>{fact.operating_scope || 'N/A'}</div>
            </div>
            <div style={{ backgroundColor: 'var(--bg-card)', padding: '10px 12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
              <div style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Confidence Tier</div>
              <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)' }}>
                {(fact.extraction_confidence * 100).toFixed(0)}% ({fact.confidence_level})
              </div>
            </div>
          </div>

          {/* Source Evidence Quote */}
          <div style={{ marginBottom: '16px' }}>
            <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <FileText size={14} style={{ color: 'var(--text-secondary)' }} />
              <span>Verbatim Source Evidence (Page {fact.page_number})</span>
            </div>
            <div
              style={{
                backgroundColor: 'var(--bg-root)',
                borderLeft: '3px solid var(--accent-primary)',
                padding: '10px 14px',
                borderRadius: 'var(--radius-sm)',
                fontSize: '12px',
                color: 'var(--text-primary)',
                lineHeight: '1.5',
                fontStyle: 'italic',
              }}
            >
              "{fact.verbatim_quote}"
            </div>
          </div>

          {/* Candidate Matches */}
          <div>
            <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <GitCompare size={14} style={{ color: 'var(--status-blue)' }} />
              <span>2-Stage Vector Semantic Candidates ({candidates.length})</span>
            </div>

            {loadingCandidates ? (
              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Calculating vector similarities...</div>
            ) : candidates.length === 0 ? (
              <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>No candidate matches found across other ingested documents.</div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {candidates.map((cand) => (
                  <div
                    key={cand.fact_id}
                    style={{
                      padding: '8px 12px',
                      backgroundColor: 'var(--bg-card)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: 'var(--radius-sm)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                    }}
                  >
                    <span style={{ fontSize: '12px' }} className="font-mono">
                      Fact #{cand.fact_id.substring(0, 8)}
                    </span>
                    <span className="badge badge-reconciled">
                      Similarity: {(cand.similarity_score * 100).toFixed(1)}%
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
