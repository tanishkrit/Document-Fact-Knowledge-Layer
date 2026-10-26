import React, { useState, useEffect } from 'react';
import { ShieldCheck, AlertTriangle, HelpCircle, GitCompare, ChevronRight, ChevronLeft, FileText } from 'lucide-react';

const TYPE_CONFIG = {
  CORROBORATES: {
    badgeClass: 'badge-corroborates',
    icon: <ShieldCheck size={13} />,
    label: 'Corroborates'
  },
  CONTRADICTS: {
    badgeClass: 'badge-contradicts',
    icon: <AlertTriangle size={13} />,
    label: 'Contradiction'
  },
  CONTEXTUALIZES: {
    badgeClass: 'badge-contextualizes',
    icon: <GitCompare size={13} />,
    label: 'Contextualizes'
  },
  UNCERTAIN: {
    badgeClass: 'badge-uncertain',
    icon: <HelpCircle size={13} />,
    label: 'Uncertain'
  },
  RELATED: {
    badgeClass: 'badge-contextualizes',
    icon: <GitCompare size={13} />,
    label: 'Related'
  }
};

export default function RelationshipMatrix({ relationships, onSelectRelationship, activeFilter, searchQuery = '' }) {
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(24);

  // Reset page when filter or search changes
  useEffect(() => {
    setCurrentPage(1);
  }, [activeFilter, searchQuery]);

  let filteredRels = activeFilter === 'ALL'
    ? relationships
    : relationships.filter((r) => r.type === activeFilter);

  if (searchQuery.trim()) {
    const q = searchQuery.toLowerCase().trim();
    filteredRels = filteredRels.filter((r) => {
      const subjA = r.fact_a?.subject || '';
      const subjB = r.fact_b?.subject || '';
      const predA = r.fact_a?.predicate || '';
      const predB = r.fact_b?.predicate || '';
      const reason = r.reason || '';
      const docA = r.fact_a?.evidence?.document_name || '';
      const docB = r.fact_b?.evidence?.document_name || '';
      const valA = r.fact_a?.value?.raw || '';
      const valB = r.fact_b?.value?.raw || '';
      return (
        subjA.toLowerCase().includes(q) ||
        subjB.toLowerCase().includes(q) ||
        predA.toLowerCase().includes(q) ||
        predB.toLowerCase().includes(q) ||
        reason.toLowerCase().includes(q) ||
        docA.toLowerCase().includes(q) ||
        docB.toLowerCase().includes(q) ||
        valA.toLowerCase().includes(q) ||
        valB.toLowerCase().includes(q)
      );
    });
  }

  const totalItems = filteredRels.length;
  const isShowAll = pageSize === 'ALL';
  const totalPages = isShowAll ? 1 : Math.max(1, Math.ceil(totalItems / pageSize));
  const safePage = Math.min(currentPage, totalPages);
  const startIndex = isShowAll ? 0 : (safePage - 1) * pageSize;
  const endIndex = isShowAll ? totalItems : Math.min(startIndex + pageSize, totalItems);
  const paginatedRels = filteredRels.slice(startIndex, endIndex);

  if (filteredRels.length === 0) {
    return (
      <div className="empty-state">
        <GitCompare size={40} style={{ opacity: 0.4 }} />
        <h3 style={{ fontSize: '1rem', color: 'var(--text-primary)' }}>No Cross-Document Relationships Found</h3>
        <p style={{ fontSize: '0.85rem', maxWidth: '420px', lineHeight: 1.5 }}>
          Select 2 or more documents from the sidebar and click "Analyze Selected" to detect corroborations, contradictions, and context differences across documents.
        </p>
      </div>
    );
  }

  return (
    <div className="matrix-wrapper" style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
      {/* Top Pagination Toolbar */}
      <div className="matrix-toolbar" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.8rem', color: 'var(--text-secondary)', padding: '0.2rem 0' }}>
        <div>
          Showing <strong style={{ color: 'var(--text-primary)' }}>{totalItems === 0 ? 0 : startIndex + 1}–{endIndex}</strong> of <strong style={{ color: 'var(--text-primary)' }}>{totalItems}</strong> relationships
          {activeFilter !== 'ALL' && <span> (filtered by <strong>{activeFilter.toLowerCase()}</strong>)</span>}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
            <span style={{ fontSize: '0.75rem' }}>Per page:</span>
            {[24, 48, 'ALL'].map((size) => (
              <button
                key={size}
                id={`page-size-btn-${size}`}
                className="btn btn-ghost btn-sm"
                style={{
                  padding: '0.15rem 0.45rem',
                  fontSize: '0.72rem',
                  background: pageSize === size ? 'var(--primary-subtle)' : 'transparent',
                  color: pageSize === size ? 'var(--primary)' : 'var(--text-secondary)',
                  border: pageSize === size ? '1px solid #c7d2fe' : '1px solid transparent',
                  fontWeight: pageSize === size ? 600 : 400
                }}
                onClick={() => {
                  setPageSize(size);
                  setCurrentPage(1);
                }}
              >
                {size === 'ALL' ? 'All' : size}
              </button>
            ))}
          </div>

          {!isShowAll && totalPages > 1 && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
              <button
                id="pagination-prev-btn"
                className="btn btn-outline btn-sm"
                disabled={safePage <= 1}
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                style={{ padding: '0.2rem 0.4rem' }}
                title="Previous Page"
              >
                <ChevronLeft size={14} />
              </button>
              <span style={{ fontSize: '0.75rem', fontWeight: 600, padding: '0 0.3rem' }}>
                {safePage} / {totalPages}
              </span>
              <button
                id="pagination-next-btn"
                className="btn btn-outline btn-sm"
                disabled={safePage >= totalPages}
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                style={{ padding: '0.2rem 0.4rem' }}
                title="Next Page"
              >
                <ChevronRight size={14} />
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Cards Grid */}
      <div className="relationships-grid">
        {paginatedRels.map((rel) => {
          const conf = TYPE_CONFIG[rel.type] || TYPE_CONFIG.RELATED;
          const factA = rel.fact_a;
          const factB = rel.fact_b;
          const confPct = Math.round(rel.confidence * 100);

          return (
            <div
              key={rel.id}
              id={`rel-card-${rel.id}`}
              className={`rel-card ${rel.type}`}
              onClick={() => onSelectRelationship(rel)}
            >
              <div className="rel-card-header">
                <span className={`badge ${conf.badgeClass}`}>
                  {conf.icon}
                  {conf.label}
                </span>

                <div className="confidence-pill" title={`Dynamic Confidence: ${confPct}%`}>
                  <span className="confidence-pill-dot" />
                  <span className="confidence-pill-label">Conf</span>
                  <span className="confidence-pill-val">{confPct}%</span>
                </div>
              </div>

              {/* Soft Side-by-side comparison tiles */}
              <div className="rel-comparison-tiles">
                <div className="rel-tile rel-tile-left">
                  <div className="rel-tile-header">
                    <FileText size={11} className="rel-tile-icon" />
                    <span className="rel-tile-doc" title={factA?.evidence.document_name}>
                      {factA ? factA.evidence.document_name : 'Document A'}
                    </span>
                    {factA?.evidence?.page && (
                      <span className="rel-tile-page">p.{factA.evidence.page}</span>
                    )}
                  </div>
                  <div className="rel-tile-val">
                    {factA ? factA.value.raw : 'Fact A'}
                  </div>
                </div>

                <div className="rel-tiles-divider">
                  <span className="rel-vs-chip">vs</span>
                </div>

                <div className="rel-tile rel-tile-right">
                  <div className="rel-tile-header">
                    <FileText size={11} className="rel-tile-icon" />
                    <span className="rel-tile-doc" title={factB?.evidence.document_name}>
                      {factB ? factB.evidence.document_name : 'Document B'}
                    </span>
                    {factB?.evidence?.page && (
                      <span className="rel-tile-page">p.{factB.evidence.page}</span>
                    )}
                  </div>
                  <div className="rel-tile-val">
                    {factB ? factB.value.raw : 'Fact B'}
                  </div>
                </div>
              </div>

              {/* Reasoning narrative preview */}
              <p className="rel-reasoning-snippet">
                {rel.reason}
              </p>

              <div className="rel-card-footer">
                <span className="rel-inspect-link">Inspect Evidence & Provenance</span>
                <ChevronRight size={14} />
              </div>
            </div>
          );
        })}
      </div>

      {/* Bottom Pagination Bar */}
      {!isShowAll && totalPages > 1 && (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.6rem', padding: '1rem 0' }}>
          <button
            className="btn btn-outline btn-sm"
            disabled={safePage <= 1}
            onClick={() => {
              setCurrentPage((p) => Math.max(1, p - 1));
              const mainEl = document.querySelector('.main-content');
              if (mainEl) mainEl.scrollTop = 0;
            }}
          >
            <ChevronLeft size={14} /> Previous
          </button>
          <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
            Page {safePage} of {totalPages} ({totalItems} items)
          </span>
          <button
            className="btn btn-outline btn-sm"
            disabled={safePage >= totalPages}
            onClick={() => {
              setCurrentPage((p) => Math.min(totalPages, p + 1));
              const mainEl = document.querySelector('.main-content');
              if (mainEl) mainEl.scrollTop = 0;
            }}
          >
            Next <ChevronRight size={14} />
          </button>
        </div>
      )}
    </div>
  );
}
