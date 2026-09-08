import React from 'react';
import { Activity, ShieldCheck, AlertCircle, FileCheck, RefreshCw } from 'lucide-react';
import { EvaluationMetrics } from '../services/api';

interface EvaluationViewProps {
  metrics: EvaluationMetrics | null;
  onRefresh: () => void;
}

export const EvaluationView: React.FC<EvaluationViewProps> = ({ metrics, onRefresh }) => {
  return (
    <div>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
        <div>
          <h1 style={{ fontSize: '18px', fontWeight: 600, color: 'var(--text-primary)', letterSpacing: '-0.01em' }}>
            System Audit & Evaluation Metrics
          </h1>
          <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
            Transparent audit counts for grounded facts, ungrounded claims, and relationship confidence.
          </p>
        </div>

        <button className="btn-secondary" onClick={onRefresh}>
          <RefreshCw size={12} />
          <span>Refresh Metrics</span>
        </button>
      </div>

      {/* Metrics Cards Grid */}
      <div className="metrics-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}>
        <div className="metric-card">
          <div className="metric-header">
            <span>Total Facts Extracted</span>
            <FileCheck size={14} style={{ color: 'var(--text-secondary)' }} />
          </div>
          <div className="metric-value">{metrics?.facts_extracted ?? 0}</div>
          <div className="metric-subtitle">Identified by extraction pipeline</div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <span>Grounded Facts</span>
            <ShieldCheck size={14} style={{ color: 'var(--status-green)' }} />
          </div>
          <div className="metric-value" style={{ color: 'var(--status-green)' }}>
            {metrics?.grounded_facts ?? 0}
          </div>
          <div className="metric-subtitle">Verbatim quote verified in PDF text</div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <span>Ungrounded / Rejected</span>
            <AlertCircle size={14} style={{ color: 'var(--status-red)' }} />
          </div>
          <div className="metric-value" style={{ color: (metrics?.ungrounded_facts ?? 0) > 0 ? 'var(--status-red)' : 'inherit' }}>
            {metrics?.ungrounded_facts ?? 0}
          </div>
          <div className="metric-subtitle">Hallucinations blocked by backend</div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <span>Relationships Classified</span>
            <Activity size={14} style={{ color: 'var(--status-blue)' }} />
          </div>
          <div className="metric-value">{metrics?.relationships_classified ?? 0}</div>
          <div className="metric-subtitle">Evaluated across distinct files</div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <span>Uncertain / Reasoning Failure</span>
            <AlertCircle size={14} style={{ color: 'var(--status-amber)' }} />
          </div>
          <div className="metric-value" style={{ color: (metrics?.uncertain_relationships ?? 0) > 0 ? 'var(--status-amber)' : 'inherit' }}>
            {metrics?.uncertain_relationships ?? 0}
          </div>
          <div className="metric-subtitle">Ambiguous context flagging review</div>
        </div>
      </div>

      {/* Audit Policy & Transparency Principles Card */}
      <div className="table-container" style={{ padding: '20px', marginTop: '16px' }}>
        <h2 style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '8px' }}>
          FactLens Audit & Anti-Hallucination Guarantees
        </h2>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px', fontSize: '12px', color: 'var(--text-secondary)', lineHeight: '1.6' }}>
          <div style={{ backgroundColor: 'var(--bg-card)', padding: '12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
            <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: '4px' }}>1. Strict ID Whitelisting</div>
            The backend injects explicit evidence IDs into LLM prompts and rejects any extracted fact whose returned evidence ID does not map to a real database EvidenceUnit.
          </div>

          <div style={{ backgroundColor: 'var(--bg-card)', padding: '12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
            <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: '4px' }}>2. Deterministic Quote Verification</div>
            Verbatim quote strings are verified against source page text before saving. Paraphrased or invented quotes are rejected immediately.
          </div>

          <div style={{ backgroundColor: 'var(--bg-card)', padding: '12px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
            <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: '4px' }}>3. Zero-LLM Arithmetic Normalization</div>
            Numeric values, scales ($10M $\rightarrow$ 10,000,000.0), percentages, and currencies are normalized deterministically in Python code to prevent LLM arithmetic errors.
          </div>
        </div>
      </div>
    </div>
  );
};
