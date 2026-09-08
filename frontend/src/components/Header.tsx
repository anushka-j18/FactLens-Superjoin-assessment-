import React from 'react';
import { Layers, FileText, CheckSquare, GitCompare, Activity, Plus } from 'lucide-react';

interface HeaderProps {
  activeTab: 'overview' | 'documents' | 'facts' | 'relationships' | 'evaluation';
  setActiveTab: (tab: 'overview' | 'documents' | 'facts' | 'relationships' | 'evaluation') => void;
  onUploadClick: () => void;
  apiStatus: 'online' | 'offline' | 'loading';
  providerName?: string;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  setActiveTab,
  onUploadClick,
  apiStatus,
  providerName,
}) => {
  return (
    <header className="top-navbar">
      <div className="nav-left">
        <div className="brand-container">
          <div className="brand-logo">FL</div>
          <span className="brand-title">FactLens</span>
        </div>

        <nav className="nav-links">
          <button
            className={`nav-btn ${activeTab === 'overview' ? 'active' : ''}`}
            onClick={() => setActiveTab('overview')}
          >
            <Layers size={14} />
            <span>Overview</span>
          </button>

          <button
            className={`nav-btn ${activeTab === 'documents' ? 'active' : ''}`}
            onClick={() => setActiveTab('documents')}
          >
            <FileText size={14} />
            <span>Documents</span>
          </button>

          <button
            className={`nav-btn ${activeTab === 'facts' ? 'active' : ''}`}
            onClick={() => setActiveTab('facts')}
          >
            <CheckSquare size={14} />
            <span>Facts</span>
          </button>

          <button
            className={`nav-btn ${activeTab === 'relationships' ? 'active' : ''}`}
            onClick={() => setActiveTab('relationships')}
          >
            <GitCompare size={14} />
            <span>Relationships</span>
          </button>

          <button
            className={`nav-btn ${activeTab === 'evaluation' ? 'active' : ''}`}
            onClick={() => setActiveTab('evaluation')}
          >
            <Activity size={14} />
            <span>Metrics</span>
          </button>
        </nav>
      </div>

      <div className="nav-right">
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', color: 'var(--text-muted)' }}>
          <span
            style={{
              width: 7,
              height: 7,
              borderRadius: '50%',
              backgroundColor: apiStatus === 'online' ? 'var(--status-green)' : apiStatus === 'offline' ? 'var(--status-red)' : 'var(--status-amber)',
            }}
          />
          <span>{apiStatus === 'online' ? `API Online (${providerName || 'Mock'})` : apiStatus === 'offline' ? 'API Offline' : 'Connecting...'}</span>
        </div>

        <button className="btn-primary" onClick={onUploadClick}>
          <Plus size={14} />
          <span>Upload PDF</span>
        </button>
      </div>
    </header>
  );
};
