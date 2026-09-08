import { useEffect, useState } from 'react';
import { FileText, CheckCircle2, XCircle, AlertCircle, HelpCircle } from 'lucide-react';

interface HealthState {
  status: string;
  app: string;
  environment: string;
  llm_provider: string;
  embedding_provider: string;
}

export default function App() {
  const [health, setHealth] = useState<HealthState | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch('/api/health')
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP error ${res.status}`);
        return res.json();
      })
      .then((data) => {
        setHealth(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  return (
    <div className="app-container">
      <header className="app-header">
        <div className="brand">
          <FileText size={20} color="#38bdf8" />
          <span className="brand-title">FactLens</span>
          <span className="brand-tag">v0.1.0</span>
        </div>
        <div className="status-badge">
          <div className={`status-dot ${error ? 'offline' : ''}`}></div>
          <span>
            {loading
              ? 'Checking API...'
              : error
              ? 'API Offline'
              : `API Online (${health?.llm_provider} LLM)`}
          </span>
        </div>
      </header>

      <main className="app-body">
        <div className="foundation-card">
          <h2>FactLens — Evidence-First Document Intelligence</h2>
          <p>
            Architecture foundation initialized. FactLens extracts semantic and numerical facts
            from PDF filings, binds every fact to verbatim source evidence, and evaluates cross-document relationships.
          </p>
        </div>

        <div className="foundation-card">
          <h2>Mandatory Relationship Reasoning Cases</h2>
          <div className="cases-grid">
            <div className="case-badge corroborated">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
                <CheckCircle2 size={16} color="#34d399" />
                <span className="case-title" style={{ color: '#34d399' }}>Corroborated</span>
              </div>
              <p className="case-desc">Claims match consistently across independent source documents.</p>
            </div>

            <div className="case-badge contradicted">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
                <XCircle size={16} color="#f87171" />
                <span className="case-title" style={{ color: '#f87171' }}>Contradicted</span>
              </div>
              <p className="case-desc">Direct numerical or semantic conflict for the same period/scope.</p>
            </div>

            <div className="case-badge reconciled">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
                <AlertCircle size={16} color="#38bdf8" />
                <span className="case-title" style={{ color: '#38bdf8' }}>Contextually Reconciled</span>
              </div>
              <p className="case-desc">Surface discrepancy resolved by timeframe, scope, or accounting differences.</p>
            </div>

            <div className="case-badge failure">
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
                <HelpCircle size={16} color="#fbbf24" />
                <span className="case-title" style={{ color: '#fbbf24' }}>Extraction / Reasoning Failure</span>
              </div>
              <p className="case-desc">Ambiguous text or unverified evidence preventing explicit linking.</p>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
