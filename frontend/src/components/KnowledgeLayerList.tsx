import React, { useState } from 'react';
import { Layers, Plus, FileText, Trash2, ChevronRight, FolderPlus, X } from 'lucide-react';
import { KnowledgeLayerItem, createKnowledgeLayer, deleteKnowledgeLayer } from '../services/api';

interface KnowledgeLayerListProps {
  knowledgeLayers: KnowledgeLayerItem[];
  onSelectKnowledgeLayer: (id: string) => void;
  onRefresh: () => void;
}

export const KnowledgeLayerList: React.FC<KnowledgeLayerListProps> = ({
  knowledgeLayers,
  onSelectKnowledgeLayer,
  onRefresh,
}) => {
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    setIsCreating(true);
    setError(null);
    try {
      await createKnowledgeLayer(name.trim(), description.trim());
      setName('');
      setDescription('');
      setIsModalOpen(false);
      onRefresh();
    } catch (err: any) {
      setError(err.message || 'Failed to create knowledge layer');
    } finally {
      setIsCreating(false);
    }
  };

  const handleDelete = async (e: React.MouseEvent, id: string, layerName: string) => {
    e.stopPropagation();
    if (window.confirm(`Are you sure you want to delete knowledge layer "${layerName}" and all its documents?`)) {
      try {
        await deleteKnowledgeLayer(id);
        onRefresh();
      } catch (err: any) {
        alert(err.message || 'Failed to delete knowledge layer');
      }
    }
  };

  return (
    <div className="section-container">
      <div className="section-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h2 style={{ fontSize: '18px', fontWeight: 600, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Layers size={20} style={{ color: 'var(--accent-primary)' }} />
            Knowledge Layers
          </h2>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)', marginTop: '4px' }}>
            Group multi-document collections for cross-document evidence intelligence and reasoning.
          </p>
        </div>
        <button className="btn-primary" onClick={() => setIsModalOpen(true)}>
          <Plus size={15} />
          New Knowledge Layer
        </button>
      </div>

      {knowledgeLayers.length === 0 ? (
        <div
          style={{
            textAlign: 'center',
            padding: '48px 24px',
            backgroundColor: 'var(--bg-card)',
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--border-subtle)',
            marginTop: '16px',
          }}
        >
          <FolderPlus size={36} style={{ color: 'var(--text-muted)', marginBottom: '12px' }} />
          <h3 style={{ fontSize: '15px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '6px' }}>
            No Knowledge Layers Created
          </h3>
          <p style={{ fontSize: '13px', color: 'var(--text-muted)', maxWidth: '420px', margin: '0 auto 16px' }}>
            Create your first knowledge layer (e.g. "Delhivery FY24 Analysis" or "India Macroeconomy") to ingest and analyze multi-document PDFs together.
          </p>
          <button className="btn-primary" onClick={() => setIsModalOpen(true)}>
            <Plus size={15} />
            Create Knowledge Layer
          </button>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '16px', marginTop: '20px' }}>
          {knowledgeLayers.map((layer) => (
            <div
              key={layer.id}
              onClick={() => onSelectKnowledgeLayer(layer.id)}
              style={{
                backgroundColor: 'var(--bg-card)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-md)',
                padding: '16px 20px',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
              }}
              className="hover:border-accent"
            >
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                  <span style={{ fontSize: '15px', fontWeight: 600, color: 'var(--text-primary)' }}>
                    {layer.name}
                  </span>
                  <button
                    onClick={(e) => handleDelete(e, layer.id, layer.name)}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: 'var(--text-muted)',
                      cursor: 'pointer',
                      padding: '4px',
                      borderRadius: '4px',
                    }}
                    title="Delete Knowledge Layer"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
                {layer.description && (
                  <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '12px', lineHeight: '1.4' }}>
                    {layer.description}
                  </p>
                )}
              </div>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: '12px', borderTop: '1px solid var(--border-subtle)' }}>
                <span style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <FileText size={14} />
                  {layer.document_count} {layer.document_count === 1 ? 'document' : 'documents'}
                </span>
                <span style={{ fontSize: '12px', color: 'var(--accent-primary)', fontWeight: 500, display: 'flex', alignItems: 'center', gap: '4px' }}>
                  Open Layer
                  <ChevronRight size={14} />
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Modal for creating a new Knowledge Layer */}
      {isModalOpen && (
        <div className="modal-overlay" onClick={() => setIsModalOpen(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '440px' }}>
            <div className="modal-header">
              <span className="modal-title">Create Knowledge Layer</span>
              <button onClick={() => setIsModalOpen(false)} style={{ color: 'var(--text-muted)' }}>
                <X size={16} />
              </button>
            </div>
            <form onSubmit={handleCreate} className="modal-body">
              {error && (
                <div style={{ color: 'var(--status-red)', fontSize: '12px', marginBottom: '12px' }}>
                  {error}
                </div>
              )}
              <div style={{ marginBottom: '16px' }}>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '6px' }}>
                  Layer Name *
                </label>
                <input
                  type="text"
                  placeholder="e.g. Delhivery FY24 Analysis"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    backgroundColor: 'var(--bg-card)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: 'var(--radius-sm)',
                    color: 'var(--text-primary)',
                    fontSize: '13px',
                  }}
                  required
                  autoFocus
                />
              </div>
              <div style={{ marginBottom: '20px' }}>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '6px' }}>
                  Description (Optional)
                </label>
                <textarea
                  placeholder="e.g. Prospectus, Annual Report, and Earnings Presentation disclosures"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={3}
                  style={{
                    width: '100%',
                    padding: '8px 12px',
                    backgroundColor: 'var(--bg-card)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: 'var(--radius-sm)',
                    color: 'var(--text-primary)',
                    fontSize: '13px',
                    resize: 'vertical',
                  }}
                />
              </div>
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
                <button type="button" className="btn-secondary" onClick={() => setIsModalOpen(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn-primary" disabled={isCreating}>
                  {isCreating ? 'Creating...' : 'Create Layer'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
