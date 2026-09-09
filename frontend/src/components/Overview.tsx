import React from 'react';
import {
  Sparkles,
  ShieldCheck,
  FileText,
  CheckSquare,
  GitCompare,
  AlertTriangle,
  Upload,
  CheckCircle2,
  XCircle,
  Info,
  Layers,
  Zap,
  Scale,
  Search,
} from 'lucide-react';
import { DocumentItem, FactItem, FactRelationship, EvaluationMetrics } from '../services/api';

interface OverviewProps {
  documents: DocumentItem[];
  facts: FactItem[];
  relationships: FactRelationship[];
  metrics: EvaluationMetrics | null;
  onNavigateTab: (tab: 'overview' | 'knowledge-layers' | 'documents' | 'facts' | 'relationships' | 'evaluation') => void;
  onSelectDocument: (docId: string) => void;
  onSelectFact: (factId: string) => void;
  onRefresh: () => void;
  onUploadClick: () => void;
}

export const Overview: React.FC<OverviewProps> = ({
  documents,
  facts,
  relationships,
  metrics,
  onNavigateTab,
  onUploadClick,
}) => {
  const needsReviewRelationships = relationships.filter((r) => r.needs_review || r.relationship_type === 'REASONING_FAILURE');
  const needsReviewFacts = facts.filter((f) => f.needs_review || f.extraction_status !== 'grounded');

  return (
    <div style={{ paddingBottom: '40px' }}>
      {/* Hero Section */}
      <div
        style={{
          background: 'linear-gradient(135deg, rgba(15, 23, 42, 0.9) 0%, rgba(30, 41, 59, 0.9) 100%)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-lg, 12px)',
          padding: '36px 32px',
          marginBottom: '24px',
          position: 'relative',
          overflow: 'hidden',
          boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.3), 0 8px 10px -6px rgba(0, 0, 0, 0.3)',
        }}
      >
        <div
          style={{
            position: 'absolute',
            top: '-50px',
            right: '-50px',
            width: '300px',
            height: '300px',
            background: 'radial-gradient(circle, rgba(59, 130, 246, 0.15) 0%, rgba(0, 0, 0, 0) 70%)',
            pointerEvents: 'none',
          }}
        />

        <div style={{ maxWidth: '860px', position: 'relative', zIndex: 1 }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', backgroundColor: 'rgba(59, 130, 246, 0.12)', border: '1px solid rgba(59, 130, 246, 0.3)', borderRadius: '20px', padding: '4px 12px', marginBottom: '14px', fontSize: '11px', fontWeight: 600, color: 'var(--accent-primary)' }}>
            <Sparkles size={13} />
            <span>EVIDENCE-FIRST DOCUMENT INTELLIGENCE</span>
          </div>

          <h1 style={{ fontSize: '28px', fontWeight: 700, color: '#FFFFFF', letterSpacing: '-0.02em', lineHeight: '1.25', marginBottom: '12px' }}>
            Discover, Ground & Compare Facts Across PDFs With Zero Hallucination
          </h1>

          <p style={{ fontSize: '14px', color: 'var(--text-secondary)', lineHeight: '1.6', marginBottom: '24px' }}>
            FactLens decouples document parsing, verbatim evidence extraction, value normalization, staged candidate retrieval, and cross-document 4-case relationship reasoning to eliminate hallucinations in enterprise intelligence and financial research.
          </p>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
            <button
              className="btn-primary"
              onClick={onUploadClick}
              style={{ padding: '10px 20px', fontSize: '13px', display: 'inline-flex', alignItems: 'center', gap: '8px', boxShadow: '0 4px 14px rgba(59, 130, 246, 0.4)' }}
            >
              <Upload size={15} />
              <span>Upload PDF Document</span>
            </button>

            <button
              className="btn-secondary"
              onClick={() => onNavigateTab('knowledge-layers')}
              style={{ padding: '10px 18px', fontSize: '13px', display: 'inline-flex', alignItems: 'center', gap: '8px' }}
            >
              <Layers size={15} />
              <span>Explore Knowledge Layers</span>
            </button>

            <button
              className="btn-secondary"
              onClick={() => onNavigateTab('facts')}
              style={{ padding: '10px 18px', fontSize: '13px', display: 'inline-flex', alignItems: 'center', gap: '8px' }}
            >
              <CheckSquare size={15} />
              <span>View Facts Catalog</span>
            </button>
          </div>
        </div>
      </div>

      {/* Live System Metrics Bar */}
      <div className="metrics-grid" style={{ marginBottom: '24px' }}>
        <div className="metric-card" style={{ cursor: 'pointer' }} onClick={() => onNavigateTab('documents')}>
          <div className="metric-header">
            <span>Ingested PDF Filings</span>
            <FileText size={14} style={{ color: 'var(--accent-primary)' }} />
          </div>
          <div className="metric-value">{metrics?.documents_processed ?? documents.length}</div>
          <div className="metric-subtitle">PyMuPDF parsed & hashed</div>
        </div>

        <div className="metric-card" style={{ cursor: 'pointer' }} onClick={() => onNavigateTab('facts')}>
          <div className="metric-header">
            <span>Verbatim Grounded Facts</span>
            <CheckSquare size={14} style={{ color: 'var(--status-green)' }} />
          </div>
          <div className="metric-value">{metrics?.grounded_facts ?? facts.length}</div>
          <div className="metric-subtitle">100% backend ID verified</div>
        </div>

        <div className="metric-card" style={{ cursor: 'pointer' }} onClick={() => onNavigateTab('relationships')}>
          <div className="metric-header">
            <span>Analyzed Relationships</span>
            <GitCompare size={14} style={{ color: 'var(--status-blue)' }} />
          </div>
          <div className="metric-value">{metrics?.relationships_classified ?? relationships.length}</div>
          <div className="metric-subtitle">Cross-document pairs</div>
        </div>

        <div className="metric-card" style={{ cursor: 'pointer' }} onClick={() => onNavigateTab('relationships')}>
          <div className="metric-header">
            <span>Review Flags / Failure</span>
            <AlertTriangle size={14} style={{ color: 'var(--status-amber)' }} />
          </div>
          <div className="metric-value" style={{ color: (needsReviewRelationships.length + needsReviewFacts.length) > 0 ? 'var(--status-amber)' : 'inherit' }}>
            {needsReviewRelationships.length + needsReviewFacts.length}
          </div>
          <div className="metric-subtitle">Audit honesty preserved</div>
        </div>
      </div>

      {/* 4 Architectural Pillars */}
      <div style={{ marginBottom: '24px' }}>
        <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Zap size={16} style={{ color: 'var(--accent-primary)' }} />
          <span>Core Intelligence Engine Pillars</span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '14px' }}>
          <div style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-md)', padding: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
              <ShieldCheck size={18} style={{ color: 'var(--status-green)' }} />
              <h3 style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>Evidence Grounding</h3>
            </div>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: '1.5' }}>
              Backend ID whitelisting and verbatim quote matching reject hallucinated page references and synthetic LLM quotes.
            </p>
          </div>

          <div style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-md)', padding: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
              <Scale size={18} style={{ color: 'var(--status-blue)' }} />
              <h3 style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>Value Normalization</h3>
            </div>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: '1.5' }}>
              Zero-LLM deterministic standardization of scales (Lakh, Crore, Million, Billion), percentages (14% → 0.14), and fiscal periods (FY24 → FY2024).
            </p>
          </div>

          <div style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-md)', padding: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
              <Search size={18} style={{ color: 'var(--accent-primary)' }} />
              <h3 style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>2-Stage Retrieval</h3>
            </div>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: '1.5' }}>
              Combines Stage 1 property alias filtering with Stage 2 dense vector embedding similarity to scale from O(N²) to O(K · N).
            </p>
          </div>

          <div style={{ backgroundColor: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-md)', padding: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
              <GitCompare size={18} style={{ color: 'var(--status-amber)' }} />
              <h3 style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>4-Case Reasoning</h3>
            </div>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: '1.5' }}>
              Categorizes claims into Corroborated, Contradicted, Contextually Reconciled, or Reasoning Failure with explicit audit trails.
            </p>
          </div>
        </div>
      </div>

      {/* 4 Relationship Outcome Cards */}
      <div style={{ marginBottom: '24px' }}>
        <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '12px' }}>
          Mandatory Cross-Document Relationship Outcome Categories
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '12px' }}>
          <div
            style={{
              backgroundColor: 'var(--bg-surface)',
              border: '1px solid var(--border-subtle)',
              borderLeft: '3px solid var(--status-green)',
              borderRadius: 'var(--radius-sm)',
              padding: '12px 14px',
              cursor: 'pointer',
            }}
            onClick={() => onNavigateTab('relationships')}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
              <CheckCircle2 size={14} style={{ color: 'var(--status-green)' }} />
              <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--status-green)' }}>CORROBORATED</span>
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Matching claims & values across independent source filings.</div>
          </div>

          <div
            style={{
              backgroundColor: 'var(--bg-surface)',
              border: '1px solid var(--border-subtle)',
              borderLeft: '3px solid var(--status-red)',
              borderRadius: 'var(--radius-sm)',
              padding: '12px 14px',
              cursor: 'pointer',
            }}
            onClick={() => onNavigateTab('relationships')}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
              <XCircle size={14} style={{ color: 'var(--status-red)' }} />
              <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--status-red)' }}>CONTRADICTED</span>
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Direct numerical or semantic conflicts for the exact same period/scope.</div>
          </div>

          <div
            style={{
              backgroundColor: 'var(--bg-surface)',
              border: '1px solid var(--border-subtle)',
              borderLeft: '3px solid var(--status-blue)',
              borderRadius: 'var(--radius-sm)',
              padding: '12px 14px',
              cursor: 'pointer',
            }}
            onClick={() => onNavigateTab('relationships')}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
              <Info size={14} style={{ color: 'var(--status-blue)' }} />
              <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--status-blue)' }}>CONTEXTUALLY RECONCILED</span>
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Surface differences explained by timeframe, scope, or accounting standards.</div>
          </div>

          <div
            style={{
              backgroundColor: 'var(--bg-surface)',
              border: '1px solid var(--border-subtle)',
              borderLeft: '3px solid var(--status-amber)',
              borderRadius: 'var(--radius-sm)',
              padding: '12px 14px',
              cursor: 'pointer',
            }}
            onClick={() => onNavigateTab('relationships')}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
              <AlertTriangle size={14} style={{ color: 'var(--status-amber)' }} />
              <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--status-amber)' }}>NEEDS REVIEW / FAILURE</span>
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Ambiguous text or ungrounded evidence preserving audit honesty.</div>
          </div>
        </div>
      </div>

      {/* Comparison Table Section */}
      <div className="table-container" style={{ marginBottom: '24px' }}>
        <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--border-subtle)', background: 'var(--bg-card)' }}>
          <span style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)' }}>
            Why Not Just Use an LLM or Standard RAG?
          </span>
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th>Engineering Requirement</th>
              <th>Naive RAG / Direct LLM</th>
              <th>FactLens Architecture</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td style={{ fontWeight: 600 }}>Computational Complexity</td>
              <td style={{ color: 'var(--status-red)' }}>O(N²) pairwise LLM calls</td>
              <td style={{ color: 'var(--status-green)', fontWeight: 600 }}>O(K · N) staged retrieval + vector search</td>
            </tr>
            <tr>
              <td style={{ fontWeight: 600 }}>Provenance Integrity</td>
              <td style={{ color: 'var(--status-red)' }}>LLMs hallucinate non-existent quotes & page numbers</td>
              <td style={{ color: 'var(--status-green)', fontWeight: 600 }}>Deterministic backend ID whitelisting & quote check</td>
            </tr>
            <tr>
              <td style={{ fontWeight: 600 }}>Arithmetic Precision</td>
              <td style={{ color: 'var(--status-red)' }}>LLMs struggle with scale conversions ($12.4M → 12,400,000)</td>
              <td style={{ color: 'var(--status-green)', fontWeight: 600 }}>Python-based deterministic normalization engine</td>
            </tr>
            <tr>
              <td style={{ fontWeight: 600 }}>Auditability</td>
              <td style={{ color: 'var(--text-muted)' }}>Black-box text summary</td>
              <td style={{ color: 'var(--status-green)', fontWeight: 600 }}>Structured audit trail with exact source text quotes</td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Quick Action Footer Banner */}
      <div
        style={{
          backgroundColor: 'var(--bg-card)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-md)',
          padding: '20px 24px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        <div>
          <div style={{ fontSize: '15px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '4px' }}>
            Ready to analyze multi-document PDF datasets?
          </div>
          <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
            Upload starter datasets from <code className="font-mono" style={{ backgroundColor: 'var(--bg-surface)', padding: '2px 6px', borderRadius: '4px' }}>data/starter-datasets/</code> or add your own PDFs.
          </div>
        </div>

        <button className="btn-primary" onClick={onUploadClick} style={{ padding: '8px 16px', fontSize: '13px' }}>
          <Upload size={14} />
          <span>Upload PDF Document</span>
        </button>
      </div>
    </div>
  );
};
