import React, { useState } from 'react';
import { GitCompare, RefreshCw, CheckCircle2, XCircle, Info, AlertTriangle, FileText } from 'lucide-react';
import { FactRelationship } from '../services/api';

interface RelationshipMatrixProps {
  relationships: FactRelationship[];
  onReanalyze: () => void;
}

export const RelationshipMatrix: React.FC<RelationshipMatrixProps> = ({ relationships, onReanalyze }) => {
  const [selectedTab, setSelectedTab] = useState<'ALL' | 'CORROBORATED' | 'CONTRADICTED' | 'CONTEXTUALLY_RECONCILED' | 'REASONING_FAILURE'>('ALL');
  const [analyzing, setAnalyzing] = useState<boolean>(false);

  const filteredRelationships = relationships.filter((rel) => {
    if (selectedTab === 'ALL') return true;
    return rel.relationship_type === selectedTab;
  });

  const handleReanalyzeClick = async () => {
    setAnalyzing(true);
    try {
      await onReanalyze();
    } finally {
      setAnalyzing(false);
    }
  };

  return (
    <div>
      {/* Top Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
        <div>
          <h1 style={{ fontSize: '18px', fontWeight: 600, color: 'var(--text-primary)', letterSpacing: '-0.01em' }}>
            Cross-Document Relationship Matrix
          </h1>
          <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
            Side-by-side evidence audit trail classifying claims across PDF filings into 4 mandatory outcomes.
          </p>
        </div>

        <button className="btn-secondary" onClick={handleReanalyzeClick} disabled={analyzing}>
          <RefreshCw size={12} className={analyzing ? 'animate-spin' : ''} />
          <span>{analyzing ? 'Analyzing...' : 'Re-Run Relationship Reasoning'}</span>
        </button>
      </div>

      {/* Filter Tabs */}
      <div className="filter-bar">
        <div className="tab-group">
          <button
            className={`tab-item ${selectedTab === 'ALL' ? 'active' : ''}`}
            onClick={() => setSelectedTab('ALL')}
          >
            All ({relationships.length})
          </button>

          <button
            className={`tab-item ${selectedTab === 'CORROBORATED' ? 'active' : ''}`}
            onClick={() => setSelectedTab('CORROBORATED')}
          >
            Corroborated ({relationships.filter((r) => r.relationship_type === 'CORROBORATED').length})
          </button>

          <button
            className={`tab-item ${selectedTab === 'CONTRADICTED' ? 'active' : ''}`}
            onClick={() => setSelectedTab('CONTRADICTED')}
          >
            Contradicted ({relationships.filter((r) => r.relationship_type === 'CONTRADICTED').length})
          </button>

          <button
            className={`tab-item ${selectedTab === 'CONTEXTUALLY_RECONCILED' ? 'active' : ''}`}
            onClick={() => setSelectedTab('CONTEXTUALLY_RECONCILED')}
          >
            Contextually Reconciled ({relationships.filter((r) => r.relationship_type === 'CONTEXTUALLY_RECONCILED').length})
          </button>

          <button
            className={`tab-item ${selectedTab === 'REASONING_FAILURE' ? 'active' : ''}`}
            onClick={() => setSelectedTab('REASONING_FAILURE')}
          >
            Needs Review ({relationships.filter((r) => r.relationship_type === 'REASONING_FAILURE').length})
          </button>
        </div>
      </div>

      {/* Relationship Comparison Cards */}
      {filteredRelationships.length === 0 ? (
        <div className="empty-state" style={{ backgroundColor: 'var(--bg-surface)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-md)' }}>
          <GitCompare size={32} className="empty-icon" />
          <div className="empty-title">No Relationships Found in Category "{selectedTab.replace('_', ' ')}"</div>
          <div className="empty-desc">Upload starter datasets under data/starter-datasets/ to test cross-document relationship reasoning.</div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {filteredRelationships.map((rel) => {
            const f1 = rel.source_fact;
            const f2 = rel.target_fact;

            return (
              <div
                key={rel.id}
                style={{
                  backgroundColor: 'var(--bg-surface)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-md)',
                  padding: '16px',
                }}
              >
                {/* Relationship Outcome Header */}
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    paddingBottom: '12px',
                    marginBottom: '12px',
                    borderBottom: '1px solid var(--border-subtle)',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span
                      className={`badge ${
                        rel.relationship_type === 'CORROBORATED'
                          ? 'badge-corroborated'
                          : rel.relationship_type === 'CONTRADICTED'
                          ? 'badge-contradicted'
                          : rel.relationship_type === 'CONTEXTUALLY_RECONCILED'
                          ? 'badge-reconciled'
                          : 'badge-failure'
                      }`}
                      style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                    >
                      {rel.relationship_type === 'CORROBORATED' && <CheckCircle2 size={12} />}
                      {rel.relationship_type === 'CONTRADICTED' && <XCircle size={12} />}
                      {rel.relationship_type === 'CONTEXTUALLY_RECONCILED' && <Info size={12} />}
                      {rel.relationship_type === 'REASONING_FAILURE' && <AlertTriangle size={12} />}
                      <span>{rel.relationship_type.replace('_', ' ')}</span>
                    </span>
                    <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                      Confidence: {(rel.confidence_score * 100).toFixed(0)}% ({rel.confidence_level})
                    </span>
                  </div>

                  {rel.needs_review && (
                    <span className="badge badge-failure">Needs Review</span>
                  )}
                </div>

                {/* Side-by-Side Comparison Grid */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr auto 1fr', gap: '16px', alignItems: 'stretch', marginBottom: '16px' }}>
                  {/* FACT A */}
                  <div
                    style={{
                      backgroundColor: 'var(--bg-card)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: 'var(--radius-sm)',
                      padding: '14px',
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'space-between',
                    }}
                  >
                    <div>
                      <div style={{ fontSize: '10px', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '4px' }}>
                        Fact A (Source Claim)
                      </div>
                      <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '4px' }}>
                        {f1 ? `${f1.subject} — ${f1.predicate}` : `Fact #${rel.source_fact_id.substring(0, 8)}`}
                      </div>
                      <div style={{ fontSize: '18px', fontWeight: 700, color: 'var(--accent-primary)', marginBottom: '6px' }}>
                        {f1 ? f1.value : '—'}
                      </div>

                      <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginBottom: '10px' }}>
                        Timeframe: <span style={{ color: 'var(--text-primary)', fontWeight: 500 }}>{f1?.temporal_context || 'N/A'}</span>
                      </div>
                    </div>

                    {/* Evidence Quote A Box */}
                    {f1?.verbatim_quote && (
                      <div>
                        <div style={{ fontSize: '10px', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <FileText size={10} />
                          <span>Verbatim Evidence (Page {f1.page_number})</span>
                        </div>
                        <div
                          style={{
                            backgroundColor: 'var(--bg-root)',
                            borderLeft: '3px solid var(--accent-primary)',
                            padding: '8px 10px',
                            borderRadius: 'var(--radius-sm)',
                            fontSize: '11px',
                            color: 'var(--text-primary)',
                            lineHeight: '1.4',
                            fontFamily: 'var(--font-mono)',
                          }}
                        >
                          "{f1.verbatim_quote}"
                        </div>
                      </div>
                    )}
                  </div>

                  {/* VS Indicator */}
                  <div
                    style={{
                      fontSize: '11px',
                      fontWeight: 700,
                      color: 'var(--text-muted)',
                      backgroundColor: 'var(--bg-subtle)',
                      padding: '8px 10px',
                      borderRadius: 'var(--radius-sm)',
                      border: '1px solid var(--border-subtle)',
                      alignSelf: 'center',
                    }}
                    className="font-mono"
                  >
                    VS
                  </div>

                  {/* FACT B */}
                  <div
                    style={{
                      backgroundColor: 'var(--bg-card)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: 'var(--radius-sm)',
                      padding: '14px',
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'space-between',
                    }}
                  >
                    <div>
                      <div style={{ fontSize: '10px', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '4px' }}>
                        Fact B (Target Claim)
                      </div>
                      <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '4px' }}>
                        {f2 ? `${f2.subject} — ${f2.predicate}` : `Fact #${rel.target_fact_id.substring(0, 8)}`}
                      </div>
                      <div style={{ fontSize: '18px', fontWeight: 700, color: 'var(--accent-primary)', marginBottom: '6px' }}>
                        {f2 ? f2.value : '—'}
                      </div>

                      <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginBottom: '10px' }}>
                        Timeframe: <span style={{ color: 'var(--text-primary)', fontWeight: 500 }}>{f2?.temporal_context || 'N/A'}</span>
                      </div>
                    </div>

                    {/* Evidence Quote B Box */}
                    {f2?.verbatim_quote && (
                      <div>
                        <div style={{ fontSize: '10px', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '4px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <FileText size={10} />
                          <span>Verbatim Evidence (Page {f2.page_number})</span>
                        </div>
                        <div
                          style={{
                            backgroundColor: 'var(--bg-root)',
                            borderLeft: '3px solid var(--accent-primary)',
                            padding: '8px 10px',
                            borderRadius: 'var(--radius-sm)',
                            fontSize: '11px',
                            color: 'var(--text-primary)',
                            lineHeight: '1.4',
                            fontFamily: 'var(--font-mono)',
                          }}
                        >
                          "{f2.verbatim_quote}"
                        </div>
                      </div>
                    )}
                  </div>
                </div>

                {/* Plain Language Reasoning Rationale */}
                <div
                  style={{
                    backgroundColor: 'var(--bg-card)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: 'var(--radius-sm)',
                    padding: '10px 12px',
                    fontSize: '12px',
                    color: 'var(--text-primary)',
                    lineHeight: '1.5',
                  }}
                >
                  <div style={{ fontSize: '10px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '4px' }}>
                    Reasoning Rationale
                  </div>
                  <div>{rel.reasoning_summary}</div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
