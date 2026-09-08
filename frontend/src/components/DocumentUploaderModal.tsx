import React, { useState } from 'react';
import { Upload, X, CheckCircle2, AlertTriangle, Loader2 } from 'lucide-react';
import { uploadDocument, extractDocumentFacts, analyzeRelationships, DocumentItem } from '../services/api';

interface DocumentUploaderModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUploadSuccess: (doc: DocumentItem) => void;
}

type StepStatus = 'idle' | 'in_progress' | 'completed' | 'failed';

export const DocumentUploaderModal: React.FC<DocumentUploaderModalProps> = ({
  isOpen,
  onClose,
  onUploadSuccess,
}) => {
  const [file, setFile] = useState<File | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const [step1, setStep1] = useState<StepStatus>('idle');
  const [step2, setStep2] = useState<StepStatus>('idle');
  const [step3, setStep3] = useState<StepStatus>('idle');

  if (!isOpen) return null;

  const handleFileDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile.type === 'application/pdf' || droppedFile.name.endsWith('.pdf')) {
        setFile(droppedFile);
        setErrorMessage(null);
      } else {
        setErrorMessage('Please select a valid PDF file (.pdf).');
      }
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0]);
      setErrorMessage(null);
    }
  };

  const startPipeline = async () => {
    if (!file) return;

    setErrorMessage(null);
    setStep1('in_progress');
    setStep2('idle');
    setStep3('idle');

    try {
      const doc = await uploadDocument(file);
      setStep1('completed');

      setStep2('in_progress');
      await extractDocumentFacts(doc.id);
      setStep2('completed');

      setStep3('in_progress');
      await analyzeRelationships();
      setStep3('completed');

      setTimeout(() => {
        onUploadSuccess(doc);
        resetState();
        onClose();
      }, 600);
    } catch (err: any) {
      if (step1 === 'in_progress') setStep1('failed');
      else if (step2 === 'in_progress') setStep2('failed');
      else if (step3 === 'in_progress') setStep3('failed');
      setErrorMessage(err.message || 'An error occurred during ingestion.');
    }
  };

  const resetState = () => {
    setFile(null);
    setErrorMessage(null);
    setStep1('idle');
    setStep2('idle');
    setStep3('idle');
  };

  const isProcessing = step1 === 'in_progress' || step2 === 'in_progress' || step3 === 'in_progress';

  return (
    <div className="modal-overlay" onClick={isProcessing ? undefined : onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <span className="modal-title">Upload PDF Document</span>
          {!isProcessing && (
            <button onClick={onClose} style={{ color: 'var(--text-muted)' }}>
              <X size={16} />
            </button>
          )}
        </div>

        <div className="modal-body">
          {errorMessage && (
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
              <span>{errorMessage}</span>
            </div>
          )}

          {!isProcessing && step3 !== 'completed' && (
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setIsDragOver(true);
              }}
              onDragLeave={() => setIsDragOver(false)}
              onDrop={handleFileDrop}
              style={{
                border: `2px dashed ${isDragOver ? 'var(--accent-primary)' : 'var(--border-subtle)'}`,
                backgroundColor: isDragOver ? 'var(--accent-primary-subtle)' : 'var(--bg-card)',
                borderRadius: 'var(--radius-md)',
                padding: '32px 16px',
                textAlign: 'center',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
                marginBottom: '16px',
              }}
              onClick={() => document.getElementById('pdf-file-input')?.click()}
            >
              <input
                id="pdf-file-input"
                type="file"
                accept=".pdf,application/pdf"
                style={{ display: 'none' }}
                onChange={handleFileSelect}
              />
              <Upload size={24} style={{ color: 'var(--text-secondary)', marginBottom: '8px' }} />
              <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '4px' }}>
                {file ? file.name : 'Click or drag PDF here to upload'}
              </div>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                {file ? `${(file.size / (1024 * 1024)).toFixed(2)} MB` : 'Supports PDF documents up to 50 MB'}
              </div>
            </div>
          )}

          {(step1 !== 'idle' || step2 !== 'idle' || step3 !== 'idle') && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', margin: '16px 0' }}>
              <StepRow label="1. Uploading PDF & Verifying Hash" status={step1} />
              <StepRow label="2. Extracting Grounded Facts & Verbatim Quotes" status={step2} />
              <StepRow label="3. Analyzing Cross-Document Relationships" status={step3} />
            </div>
          )}

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '16px' }}>
            {!isProcessing && (
              <button className="btn-secondary" onClick={onClose}>
                Cancel
              </button>
            )}
            {file && !isProcessing && step3 !== 'completed' && (
              <button className="btn-primary" onClick={startPipeline}>
                Start Ingestion
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

const StepRow: React.FC<{ label: string; status: StepStatus }> = ({ label, status }) => {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '10px 12px',
        backgroundColor: 'var(--bg-card)',
        borderRadius: 'var(--radius-sm)',
        border: '1px solid var(--border-subtle)',
      }}
    >
      <span style={{ fontSize: '12px', fontWeight: 500, color: status === 'idle' ? 'var(--text-muted)' : 'var(--text-primary)' }}>
        {label}
      </span>
      {status === 'in_progress' && <Loader2 size={14} className="animate-spin" style={{ color: 'var(--accent-primary)' }} />}
      {status === 'completed' && <CheckCircle2 size={14} style={{ color: 'var(--status-green)' }} />}
      {status === 'failed' && <X size={14} style={{ color: 'var(--status-red)' }} />}
    </div>
  );
};
