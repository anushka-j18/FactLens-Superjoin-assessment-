import React, { useState, useEffect } from 'react';
import { ArrowLeft, FileText, Upload, Plus, AlertTriangle, CheckCircle2, X, Loader2, Eye } from 'lucide-react';
import {
  KnowledgeLayerItem,
  DocumentItem,
  fetchKnowledgeLayerDetails,
  uploadDocumentsToKnowledgeLayer,
} from '../services/api';

interface KnowledgeLayerDetailProps {
  knowledgeLayerId: string;
  onBack: () => void;
  onSelectDocument: (docId: string) => void;
}

export const KnowledgeLayerDetail: React.FC<KnowledgeLayerDetailProps> = ({
  knowledgeLayerId,
  onBack,
  onSelectDocument,
}) => {
  const [layer, setLayer] = useState<KnowledgeLayerItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Multi-file Upload Modal State
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const loadDetails = async () => {
    setLoading(true);
    try {
      const data = await fetchKnowledgeLayerDetails(knowledgeLayerId);
      setLayer(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load knowledge layer details');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDetails();
  }, [knowledgeLayerId]);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const newFiles = Array.from(e.target.files).filter(
        (f) => f.type === 'application/pdf' || f.name.toLowerCase().endsWith('.pdf')
      );
      if (newFiles.length === 0) {
        setUploadError('Please select valid PDF files (.pdf).');
        return;
      }
      setSelectedFiles((prev) => [...prev, ...newFiles]);
      setUploadError(null);
    }
  };

  const handleRemoveFile = (index: number) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const handleStartBatchUpload = async () => {
    if (selectedFiles.length === 0) return;

    setIsUploading(true);
    setUploadError(null);

    try {
      await uploadDocumentsToKnowledgeLayer(knowledgeLayerId, selectedFiles);
      setSelectedFiles([]);
      setIsUploadModalOpen(false);
      await loadDetails();
    } catch (err: any) {
      setUploadError(err.message || 'Batch PDF upload failed.');
    } finally {
      setIsUploading(false);
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: '48px' }}>
        <Loader2 size={24} className="animate-spin" style={{ color: 'var(--accent-primary)' }} />
      </div>
    );
  }

  if (error || !layer) {
    return (
      <div style={{ padding: '24px' }}>
        <button className="btn-secondary" onClick={onBack} style={{ marginBottom: '16px' }}>
          <ArrowLeft size={14} /> Back to Knowledge Layers
        </button>
        <div style={{ color: 'var(--status-red)', fontSize: '13px' }}>
          {error || 'Knowledge Layer not found.'}
        </div>
      </div>
    );
  }

  return (
    <div className="section-container">
      {/* Header Navigation & Info */}
      <button className="btn-secondary" onClick={onBack} style={{ marginBottom: '16px' }}>
        <ArrowLeft size={14} /> Back to Knowledge Layers
      </button>

      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          paddingBottom: '20px',
          borderBottom: '1px solid var(--border-subtle)',
          marginBottom: '24px',
        }}
      >
        <div>
          <h1 style={{ fontSize: '20px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '4px' }}>
            {layer.name}
          </h1>
          {layer.description && (
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>{layer.description}</p>
          )}
          <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '8px' }}>
            {layer.documents?.length || 0} {layer.documents?.length === 1 ? 'document' : 'documents'} in this Knowledge Layer
          </div>
        </div>

        <button className="btn-primary" onClick={() => setIsUploadModalOpen(true)}>
          <Plus size={15} />
          Add PDFs
        </button>
      </div>

      {/* Documents List in Knowledge Layer */}
      <h3 style={{ fontSize: '15px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '12px' }}>
        Documents in Layer
      </h3>

      {!layer.documents || layer.documents.length === 0 ? (
        <div
          style={{
            textAlign: 'center',
            padding: '36px 20px',
            backgroundColor: 'var(--bg-card)',
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--border-subtle)',
          }}
        >
          <FileText size={32} style={{ color: 'var(--text-muted)', marginBottom: '8px' }} />
          <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
            No documents uploaded to this layer yet. Click "+ Add PDFs" to upload 1 or more PDF files.
          </p>
        </div>
      ) : (
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Document Name</th>
                <th>Status</th>
                <th>Pages</th>
                <th>File Size</th>
                <th>Uploaded</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {layer.documents.map((doc: DocumentItem) => (
                <tr key={doc.id} onClick={() => onSelectDocument(doc.id)} style={{ cursor: 'pointer' }}>
                  <td>
                    <div style={{ fontWeight: 500, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <FileText size={15} style={{ color: 'var(--accent-primary)' }} />
                      {doc.original_filename}
                    </div>
                  </td>
                  <td>
                    {doc.processing_status === 'completed' && (
                      <span className="badge badge-green" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                        <CheckCircle2 size={12} /> COMPLETED
                      </span>
                    )}
                    {doc.processing_status === 'failed' && (
                      <span className="badge badge-red" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }} title={doc.error_message || ''}>
                        <AlertTriangle size={12} /> FAILED
                      </span>
                    )}
                    {doc.processing_status === 'processing' && (
                      <span className="badge badge-yellow" style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                        <Loader2 size={12} className="animate-spin" /> PROCESSING
                      </span>
                    )}
                    {doc.processing_status === 'uploaded' && (
                      <span className="badge badge-gray">UPLOADED</span>
                    )}
                  </td>
                  <td style={{ color: 'var(--text-secondary)' }}>{doc.page_count} pages</td>
                  <td style={{ color: 'var(--text-muted)' }}>{(doc.file_size / (1024 * 1024)).toFixed(2)} MB</td>
                  <td style={{ color: 'var(--text-muted)' }}>{new Date(doc.created_at).toLocaleDateString()}</td>
                  <td style={{ textAlign: 'right' }}>
                    <button
                      className="btn-secondary"
                      style={{ padding: '4px 8px', fontSize: '11px' }}
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectDocument(doc.id);
                      }}
                    >
                      <Eye size={13} /> Inspect Evidence
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Multi-file Upload Modal */}
      {isUploadModalOpen && (
        <div className="modal-overlay" onClick={isUploading ? undefined : () => setIsUploadModalOpen(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '520px' }}>
            <div className="modal-header">
              <span className="modal-title">Upload PDFs to "{layer.name}"</span>
              {!isUploading && (
                <button onClick={() => setIsUploadModalOpen(false)} style={{ color: 'var(--text-muted)' }}>
                  <X size={16} />
                </button>
              )}
            </div>

            <div className="modal-body">
              {uploadError && (
                <div
                  style={{
                    backgroundColor: 'var(--status-red-bg)',
                    border: '1px solid rgba(239, 68, 68, 0.3)',
                    padding: '10px 12px',
                    borderRadius: 'var(--radius-sm)',
                    color: 'var(--status-red)',
                    fontSize: '12px',
                    marginBottom: '16px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                  }}
                >
                  <AlertTriangle size={14} />
                  <span>{uploadError}</span>
                </div>
              )}

              {!isUploading && (
                <div
                  style={{
                    border: '2px dashed var(--border-subtle)',
                    backgroundColor: 'var(--bg-card)',
                    borderRadius: 'var(--radius-md)',
                    padding: '28px 16px',
                    textAlign: 'center',
                    cursor: 'pointer',
                    marginBottom: '16px',
                  }}
                  onClick={() => document.getElementById('multi-pdf-file-input')?.click()}
                >
                  <input
                    id="multi-pdf-file-input"
                    type="file"
                    multiple
                    accept=".pdf,application/pdf"
                    style={{ display: 'none' }}
                    onChange={handleFileSelect}
                  />
                  <Upload size={24} style={{ color: 'var(--text-secondary)', marginBottom: '8px' }} />
                  <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '4px' }}>
                    Click to select MULTIPLE PDF files
                  </div>
                  <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                    Select 1 or more PDF documents (e.g. Prospectus, Annual Report, Presentation)
                  </div>
                </div>
              )}

              {/* Selected Files List */}
              {selectedFiles.length > 0 && (
                <div style={{ marginBottom: '16px' }}>
                  <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '8px' }}>
                    Selected Files ({selectedFiles.length}):
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', maxHeight: '160px', overflowY: 'auto' }}>
                    {selectedFiles.map((file, i) => (
                      <div
                        key={i}
                        style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                          padding: '6px 10px',
                          backgroundColor: 'var(--bg-card)',
                          borderRadius: 'var(--radius-sm)',
                          border: '1px solid var(--border-subtle)',
                          fontSize: '12px',
                        }}
                      >
                        <span style={{ color: 'var(--text-primary)', fontWeight: 500 }}>{file.name}</span>
                        {!isUploading && (
                          <button
                            onClick={() => handleRemoveFile(i)}
                            style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
                          >
                            <X size={14} />
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {isUploading && (
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px', padding: '16px 0', fontSize: '13px', color: 'var(--text-primary)' }}>
                  <Loader2 size={18} className="animate-spin" style={{ color: 'var(--accent-primary)' }} />
                  Ingesting and extracting page evidence for {selectedFiles.length} PDFs...
                </div>
              )}

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '16px' }}>
                {!isUploading && (
                  <button className="btn-secondary" onClick={() => setIsUploadModalOpen(false)}>
                    Cancel
                  </button>
                )}
                {selectedFiles.length > 0 && !isUploading && (
                  <button className="btn-primary" onClick={handleStartBatchUpload}>
                    Start Ingestion ({selectedFiles.length} PDFs)
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
