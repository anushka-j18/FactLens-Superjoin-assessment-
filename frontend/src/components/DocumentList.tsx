import React, { useState } from 'react';
import { FileText, Play, Eye, Loader2, CheckCircle2 } from 'lucide-react';
import { DocumentItem } from '../services/api';

interface DocumentListProps {
  documents: DocumentItem[];
  onSelectDocument: (docId: string) => void;
  onExtractFacts: (docId: string) => Promise<void>;
  onUploadClick: () => void;
}

export const DocumentList: React.FC<DocumentListProps> = ({
  documents,
  onSelectDocument,
  onExtractFacts,
  onUploadClick,
}) => {
  const [extractingId, setExtractingId] = useState<string | null>(null);

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const handleExtractClick = async (docId: string) => {
    setExtractingId(docId);
    try {
      await onExtractFacts(docId);
    } finally {
      setExtractingId(null);
    }
  };

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
        <div>
          <h1 style={{ fontSize: '18px', fontWeight: 600, color: 'var(--text-primary)', letterSpacing: '-0.01em' }}>
            Ingested PDF Documents
          </h1>
          <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
            Uploaded PDF filings, parsed evidence units, and grounded fact status.
          </p>
        </div>
        <button className="btn-primary" onClick={onUploadClick}>
          Upload New PDF
        </button>
      </div>

      <div className="table-container">
        {documents.length === 0 ? (
          <div className="empty-state">
            <FileText size={32} className="empty-icon" />
            <div className="empty-title">No PDF Documents Ingested</div>
            <div className="empty-desc">
              Upload a PDF filing to parse page-level evidence units and extract grounded numerical/semantic facts.
            </div>
            <button className="btn-primary" onClick={onUploadClick}>
              Upload PDF
            </button>
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Filename</th>
                <th>File Size</th>
                <th>Page Count</th>
                <th>Ingestion Status</th>
                <th>Fact Extraction</th>
                <th>Uploaded</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => {
                const isExtracting = extractingId === doc.id;
                return (
                  <tr key={doc.id}>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <FileText size={14} style={{ color: 'var(--text-secondary)' }} />
                        <span
                          style={{ fontWeight: 600, color: 'var(--text-primary)', cursor: 'pointer' }}
                          onClick={() => onSelectDocument(doc.id)}
                        >
                          {doc.original_filename}
                        </span>
                      </div>
                    </td>
                    <td className="font-mono" style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                      {formatBytes(doc.file_size)}
                    </td>
                    <td>{doc.page_count} pages</td>
                    <td>
                      <span
                        className={`badge ${
                          doc.processing_status === 'completed'
                            ? 'badge-corroborated'
                            : doc.processing_status === 'failed'
                            ? 'badge-contradicted'
                            : 'badge-neutral'
                        }`}
                      >
                        {doc.processing_status}
                      </span>
                    </td>
                    <td>
                      <span
                        className={`badge ${
                          doc.extraction_status === 'completed'
                            ? 'badge-corroborated'
                            : doc.extraction_status === 'partially_processed'
                            ? 'badge-reconciled'
                            : doc.extraction_status === 'failed' || doc.extraction_status === 'no_facts_found'
                            ? 'badge-failure'
                            : 'badge-neutral'
                        }`}
                      >
                        {isExtracting ? 'extracting...' : doc.extraction_status}
                      </span>
                    </td>
                    <td style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                      {new Date(doc.created_at).toLocaleDateString()}
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '6px' }}>
                        <button
                          className="btn-secondary"
                          style={{ padding: '4px 8px', fontSize: '11px' }}
                          onClick={() => handleExtractClick(doc.id)}
                          disabled={isExtracting}
                          title="Trigger Fact Extraction & Relationship Analysis"
                        >
                          {isExtracting ? (
                            <>
                              <Loader2 size={11} className="animate-spin" />
                              <span>Extracting...</span>
                            </>
                          ) : doc.extraction_status === 'completed' ? (
                            <>
                              <CheckCircle2 size={11} style={{ color: 'var(--status-green)' }} />
                              <span>Re-Extract</span>
                            </>
                          ) : (
                            <>
                              <Play size={11} />
                              <span>Extract</span>
                            </>
                          )}
                        </button>
                        <button
                          className="btn-secondary"
                          style={{ padding: '4px 8px', fontSize: '11px' }}
                          onClick={() => onSelectDocument(doc.id)}
                          title="View Document & Evidence"
                        >
                          <Eye size={11} />
                          <span>Inspect</span>
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};
