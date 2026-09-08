import React, { useState } from 'react';
import { CheckSquare, Search, Eye, Filter } from 'lucide-react';
import { FactItem } from '../services/api';
import { FactDetailModal } from './FactDetailModal';

interface FactListProps {
  facts: FactItem[];
}

export const FactList: React.FC<FactListProps> = ({ facts }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterNeedsReview, setFilterNeedsReview] = useState(false);
  const [selectedFact, setSelectedFact] = useState<FactItem | null>(null);

  const filteredFacts = facts.filter((fact) => {
    const matchesSearch =
      fact.subject.toLowerCase().includes(searchTerm.toLowerCase()) ||
      fact.predicate.toLowerCase().includes(searchTerm.toLowerCase()) ||
      fact.value.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesReview = filterNeedsReview ? fact.needs_review || fact.extraction_status !== 'grounded' : true;

    return matchesSearch && matchesReview;
  });

  return (
    <div>
      {/* Top Header & Filter Controls */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
        <div>
          <h1 style={{ fontSize: '18px', fontWeight: 600, color: 'var(--text-primary)', letterSpacing: '-0.01em' }}>
            Extracted Grounded Facts
          </h1>
          <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
            Structured numerical and semantic facts verified against source page quotes.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{ position: 'relative' }}>
            <Search size={14} style={{ position: 'absolute', left: '10px', top: '9px', color: 'var(--text-muted)' }} />
            <input
              type="text"
              className="search-input"
              style={{ paddingLeft: '30px' }}
              placeholder="Search facts or metrics..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>

          <button
            className={`btn-secondary ${filterNeedsReview ? 'active' : ''}`}
            onClick={() => setFilterNeedsReview(!filterNeedsReview)}
          >
            <Filter size={12} />
            <span>{filterNeedsReview ? 'Showing: Needs Review' : 'Filter Needs Review'}</span>
          </button>
        </div>
      </div>

      {/* Facts Data Table */}
      <div className="table-container">
        {filteredFacts.length === 0 ? (
          <div className="empty-state">
            <CheckSquare size={32} className="empty-icon" />
            <div className="empty-title">No Grounded Facts Found</div>
            <div className="empty-desc">Upload documents and extract facts to view structured claims.</div>
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Subject & Predicate</th>
                <th>Fact Value</th>
                <th>Normalized Value</th>
                <th>Timeframe</th>
                <th>Verbatim Evidence Quote</th>
                <th>Confidence</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredFacts.map((fact) => (
                <tr key={fact.id}>
                  <td>
                    <div>
                      <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{fact.subject}</div>
                      <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{fact.predicate}</div>
                    </div>
                  </td>
                  <td>
                    <span style={{ fontWeight: 600, color: 'var(--accent-primary)' }}>
                      {fact.value} {fact.unit ? `(${fact.unit})` : ''}
                    </span>
                  </td>
                  <td className="font-mono" style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                    {fact.normalized_value !== null && fact.normalized_value !== undefined
                      ? fact.normalized_value.toLocaleString()
                      : '—'}
                  </td>
                  <td>
                    <span className="badge badge-neutral">{fact.temporal_context || 'N/A'}</span>
                  </td>
                  <td style={{ maxWidth: '280px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', fontSize: '11px', color: 'var(--text-secondary)', fontStyle: 'italic' }}>
                    "{fact.verbatim_quote}"
                  </td>
                  <td>
                    <span className={`badge ${fact.confidence_level === 'HIGH' ? 'badge-corroborated' : 'badge-warning'}`}>
                      {(fact.extraction_confidence * 100).toFixed(0)}% ({fact.confidence_level})
                    </span>
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <button
                      className="btn-secondary"
                      style={{ padding: '4px 8px', fontSize: '11px' }}
                      onClick={() => setSelectedFact(fact)}
                    >
                      <Eye size={11} />
                      <span>Inspect</span>
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Fact Detail Modal */}
      {selectedFact && <FactDetailModal fact={selectedFact} onClose={() => setSelectedFact(null)} />}
    </div>
  );
};
