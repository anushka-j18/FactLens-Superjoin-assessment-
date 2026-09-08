import React from 'react';
import { FileText, CheckSquare, GitCompare, AlertTriangle, ArrowRight, RefreshCw } from 'lucide-react';
import { DocumentItem, FactItem, FactRelationship, EvaluationMetrics } from '../services/api';

interface OverviewProps {
  documents: DocumentItem[];
  facts: FactItem[];
  relationships: FactRelationship[];
  metrics: EvaluationMetrics | null;
  onNavigateTab: (tab: 'documents' | 'facts' | 'relationships' | 'evaluation') => void;
  onSelectDocument: (docId: string) => void;
  onSelectFact: (factId: string) => void;
  onRefresh: () => void;
}

export const Overview: React.FC<OverviewProps> = ({
  documents,
  facts,
  relationships,
  metrics,
  onNavigateTab,
  onRefresh,
}) => {
  const needsReviewRelationships = relationships.filter((r) => r.needs_review || r.relationship_type === 'REASONING_FAILURE');
  const needsReviewFacts = facts.filter((f) => f.needs_review || f.extraction_status !== 'grounded');

  return (
    <div>
      {/* Header bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
        <div>
          <h1 style={{ fontSize: '18px', fontWeight: 600, color: 'var(--text-primary)', letterSpacing: '-0.01em' }}>
            System Dashboard
          </h1>
          <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
            Evidence-first document intelligence overview & recent audit findings.
          </p>
        </div>
        <button className="btn-secondary" onClick={onRefresh}>
          <RefreshCw size={13} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Metrics Row */}
      <div className="metrics-grid">
        <div className="metric-card" style={{ cursor: 'pointer' }} onClick={() => onNavigateTab('documents')}>
          <div className="metric-header">
            <span>Documents Ingested</span>
            <FileText size={14} style={{ color: 'var(--text-secondary)' }} />
          </div>
          <div className="metric-value">{metrics?.documents_processed ?? documents.length}</div>
          <div className="metric-subtitle">PDF filings & report datasets</div>
        </div>

        <div className="metric-card" style={{ cursor: 'pointer' }} onClick={() => onNavigateTab('facts')}>
          <div className="metric-header">
            <span>Grounded Facts</span>
            <CheckSquare size={14} style={{ color: 'var(--status-green)' }} />
          </div>
          <div className="metric-value">{metrics?.grounded_facts ?? facts.length}</div>
          <div className="metric-subtitle">Verified against verbatim text</div>
        </div>

        <div className="metric-card" style={{ cursor: 'pointer' }} onClick={() => onNavigateTab('relationships')}>
          <div className="metric-header">
            <span>Analyzed Relationships</span>
            <GitCompare size={14} style={{ color: 'var(--status-blue)' }} />
          </div>
          <div className="metric-value">{metrics?.relationships_classified ?? relationships.length}</div>
          <div className="metric-subtitle">Across distinct PDF documents</div>
        </div>

        <div className="metric-card" style={{ cursor: 'pointer' }} onClick={() => onNavigateTab('relationships')}>
          <div className="metric-header">
            <span>Needs Review</span>
            <AlertTriangle size={14} style={{ color: 'var(--status-amber)' }} />
          </div>
          <div className="metric-value" style={{ color: needsReviewRelationships.length > 0 ? 'var(--status-amber)' : 'inherit' }}>
            {needsReviewRelationships.length + needsReviewFacts.length}
          </div>
          <div className="metric-subtitle">Ambiguous claims or low confidence</div>
        </div>
      </div>

      {/* Main Grid: Left Needs Review, Right Recent Findings */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '16px' }}>
        {/* Needs Review Alert Section */}
        <div className="table-container">
          <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <AlertTriangle size={14} style={{ color: 'var(--status-amber)' }} />
              <span style={{ fontSize: '13px', fontWeight: 600 }}>Needs Review / Uncertain Items</span>
            </div>
            <button style={{ fontSize: '11px', color: 'var(--accent-primary)' }} onClick={() => onNavigateTab('relationships')}>
              View All
            </button>
          </div>

          {needsReviewRelationships.length === 0 && needsReviewFacts.length === 0 ? (
            <div className="empty-state">
              <div className="empty-title">All Items Grounded</div>
              <div className="empty-desc">No ambiguous context or ungrounded claims requiring review.</div>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              {needsReviewRelationships.map((rel) => (
                <div
                  key={rel.id}
                  style={{
                    padding: '12px 16px',
                    borderBottom: '1px solid var(--border-subtle)',
                    display: 'flex',
                    alignItems: 'flex-start',
                    justifyContent: 'space-between',
                    gap: '12px',
                  }}
                >
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
                      <span className="badge badge-failure">Needs Review</span>
                      <span style={{ fontSize: '11px', color: 'var(--text-muted)' }} className="font-mono">
                        {rel.failure_reason || 'insufficient_context'}
                      </span>
                    </div>
                    <div style={{ fontSize: '12px', color: 'var(--text-primary)', lineHeight: '1.4' }}>
                      {rel.reasoning_summary}
                    </div>
                  </div>
                  <button className="btn-secondary" style={{ padding: '4px 8px', fontSize: '11px' }} onClick={() => onNavigateTab('relationships')}>
                    Inspect
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Recent Findings List */}
        <div className="table-container">
          <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: '13px', fontWeight: 600 }}>Recent Findings & Corroborations</span>
            <button style={{ fontSize: '11px', color: 'var(--accent-primary)' }} onClick={() => onNavigateTab('relationships')}>
              View Matrix <ArrowRight size={11} style={{ display: 'inline' }} />
            </button>
          </div>

          {relationships.length === 0 ? (
            <div className="empty-state">
              <div className="empty-title">No Relationships Analyzed</div>
              <div className="empty-desc">Upload documents and extract facts to view cross-document findings.</div>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              {relationships.slice(0, 5).map((rel) => (
                <div
                  key={rel.id}
                  style={{
                    padding: '12px 16px',
                    borderBottom: '1px solid var(--border-subtle)',
                    display: 'flex',
                    alignItems: 'flex-start',
                    justifyContent: 'space-between',
                    gap: '12px',
                  }}
                >
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
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
                      >
                        {rel.relationship_type.replace('_', ' ')}
                      </span>
                      <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                        Score: {(rel.confidence_score * 100).toFixed(0)}% ({rel.confidence_level})
                      </span>
                    </div>
                    <div style={{ fontSize: '12px', color: 'var(--text-primary)', lineHeight: '1.4' }}>
                      {rel.reasoning_summary}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
