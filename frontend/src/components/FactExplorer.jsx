import React, { useState, useEffect } from 'react';
import { BookOpen, Layers, CheckCircle, Clock, MapPin, Globe, Sparkles, ChevronLeft, ChevronRight } from 'lucide-react';

export default function FactExplorer({ facts, searchQuery, onSelectFact }) {
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(24);

  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery]);

  const filteredFacts = facts.filter((f) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      f.subject.toLowerCase().includes(q) ||
      f.predicate.toLowerCase().includes(q) ||
      f.value.raw.toLowerCase().includes(q) ||
      f.evidence.document_name.toLowerCase().includes(q) ||
      (f.context.time && f.context.time.toLowerCase().includes(q))
    );
  });

  const totalItems = filteredFacts.length;
  const isShowAll = pageSize === 'ALL';
  const totalPages = isShowAll ? 1 : Math.max(1, Math.ceil(totalItems / pageSize));
  const safePage = Math.min(currentPage, totalPages);
  const startIndex = isShowAll ? 0 : (safePage - 1) * pageSize;
  const endIndex = isShowAll ? totalItems : Math.min(startIndex + pageSize, totalItems);
  const paginatedFacts = filteredFacts.slice(startIndex, endIndex);

  if (filteredFacts.length === 0) {
    return (
      <div className="empty-state">
        <Layers size={40} style={{ opacity: 0.4 }} />
        <h3 style={{ fontSize: '1rem', color: 'var(--text-primary)' }}>No Extracted Facts Found</h3>
        <p style={{ fontSize: '0.85rem', maxWidth: '400px' }}>
          Upload PDF documents and run extraction to view structured facts, deterministic normalizations, and provenance.
        </p>
      </div>
    );
  }

  return (
    <div className="facts-wrapper" style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
      {/* Top Pagination Toolbar */}
      <div className="matrix-toolbar" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.8rem', color: 'var(--text-secondary)', padding: '0.2rem 0' }}>
        <div>
          Showing <strong style={{ color: 'var(--text-primary)' }}>{totalItems === 0 ? 0 : startIndex + 1}–{endIndex}</strong> of <strong style={{ color: 'var(--text-primary)' }}>{totalItems}</strong> extracted facts
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
            <span style={{ fontSize: '0.75rem' }}>Per page:</span>
            {[24, 48, 'ALL'].map((size) => (
              <button
                key={size}
                id={`facts-page-size-${size}`}
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
      <div className="facts-grid">
        {paginatedFacts.map((fact) => {
          const hasNormalized = fact.value.amount !== null && fact.value.amount !== undefined;
          return (
            <div
              key={fact.id}
              id={`fact-card-${fact.id}`}
              className="fact-card"
              onClick={() => onSelectFact && onSelectFact(fact)}
            >
              <div className="fact-header">
                <div>
                  <div className="fact-predicate">{fact.predicate}</div>
                  <div className="fact-subject">{fact.subject}</div>
                </div>

                {fact.qualification && (
                  <span className="chip" style={{ color: 'var(--color-uncertain)', borderColor: 'var(--color-uncertain-border)' }}>
                    {fact.qualification}
                  </span>
                )}
              </div>

              <div className="fact-value-box">
                <span className="fact-raw-value">{fact.value.raw}</span>
                {hasNormalized && (
                  <span className="fact-normalized-val" title="Canonical Normalized Amount">
                    ≈ {fact.value.amount.toLocaleString()} {fact.value.unit || fact.value.currency || ''}
                  </span>
                )}
              </div>

              {/* Context Dimension Chips */}
              <div className="fact-context-chips">
                {fact.context.time && (
                  <span className="chip" title="Temporal Context">
                    <Clock size={10} style={{ display: 'inline', marginRight: '3px' }} />
                    {fact.context.time}
                  </span>
                )}
                {fact.context.geography && (
                  <span className="chip" title="Geographical Context">
                    <Globe size={10} style={{ display: 'inline', marginRight: '3px' }} />
                    {fact.context.geography}
                  </span>
                )}
                {fact.context.scope && (
                  <span className="chip" title="Scope / Population Context">
                    <MapPin size={10} style={{ display: 'inline', marginRight: '3px' }} />
                    {fact.context.scope}
                  </span>
                )}
              </div>

              {/* Evidence quote */}
              <blockquote className="fact-evidence-quote" title="Exact source quote">
                "{fact.evidence.text}"
              </blockquote>

              {/* Provenance Footer */}
              <div className="fact-provenance-footer">
                <span className="fact-doc-tag" title={fact.evidence.document_name}>
                  <BookOpen size={11} />
                  <span className="fact-doc-name">{fact.evidence.document_name}</span>
                </span>
                <span className="fact-page-badge">Page {fact.evidence.page}</span>
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
            Page {safePage} of {totalPages} ({totalItems} facts)
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
