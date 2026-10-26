import React, { useState, useMemo } from 'react';
import {
  GitCompare, ShieldCheck, AlertTriangle, HelpCircle,
  FileText, Search, Sparkles, Filter, CheckCircle2, ChevronDown,
  ChevronUp, ExternalLink, Info, Layers
} from 'lucide-react';

const VERDICT_CONFIG = {
  CORROBORATES: {
    badgeClass: 'badge-corroborates',
    icon: <ShieldCheck size={14} />,
    title: 'Unanimous Corroboration',
    tagColor: 'var(--color-corroborate)',
    tagBg: 'var(--color-corroborate-bg)'
  },
  CONTRADICTS: {
    badgeClass: 'badge-contradicts',
    icon: <AlertTriangle size={14} />,
    title: 'Conflict Across Filings',
    tagColor: 'var(--color-contradict)',
    tagBg: 'var(--color-contradict-bg)'
  },
  CONTEXTUALIZES: {
    badgeClass: 'badge-contextualizes',
    icon: <GitCompare size={14} />,
    title: 'Temporal / Scope Drift',
    tagColor: 'var(--color-context)',
    tagBg: 'var(--color-context-bg)'
  },
  UNCERTAIN: {
    badgeClass: 'badge-uncertain',
    icon: <HelpCircle size={14} />,
    title: 'Uncertain / Underspecified',
    tagColor: 'var(--text-muted)',
    tagBg: 'var(--bg-card-subtle)'
  }
};

export default function MultiDocumentMatrix({
  consensusData,
  isLoading = false,
  onRefresh
}) {
  const [filterVerdict, setFilterVerdict] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedQuotes, setExpandedQuotes] = useState({});

  const points = consensusData?.consensus_points || [];
  const documents = consensusData?.documents || [];
  const totalSelected = consensusData?.document_ids?.length || documents.length || 0;

  // Filter and search logic
  const filteredPoints = useMemo(() => {
    return points.filter((pt) => {
      // Verdict filter
      if (filterVerdict !== 'ALL' && pt.verdict !== filterVerdict) {
        return false;
      }
      // Search query
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchesSubj = pt.subject?.toLowerCase().includes(q);
        const matchesPred = pt.predicate?.toLowerCase().includes(q);
        const matchesSummary = pt.summary?.toLowerCase().includes(q);
        const matchesClaim = pt.claims?.some(
          (c) =>
            c.raw_value?.toLowerCase().includes(q) ||
            c.evidence_quote?.toLowerCase().includes(q) ||
            c.document_name?.toLowerCase().includes(q)
        );
        return matchesSubj || matchesPred || matchesSummary || matchesClaim;
      }
      return true;
    });
  }, [points, filterVerdict, searchQuery]);

  // Counts by verdict
  const counts = useMemo(() => {
    return {
      ALL: points.length,
      CORROBORATES: points.filter((p) => p.verdict === 'CORROBORATES').length,
      CONTRADICTS: points.filter((p) => p.verdict === 'CONTRADICTS').length,
      CONTEXTUALIZES: points.filter((p) => p.verdict === 'CONTEXTUALIZES').length,
      UNCERTAIN: points.filter((p) => p.verdict === 'UNCERTAIN').length,
    };
  }, [points]);

  const toggleExpandQuote = (claimKey) => {
    setExpandedQuotes((prev) => ({
      ...prev,
      [claimKey]: !prev[claimKey]
    }));
  };

  if (isLoading) {
    return (
      <div className="consensus-loading-state">
        <Sparkles size={28} className="animate-spin text-primary" />
        <h3>Computing Multi-Document Consensus Matrix...</h3>
        <p>Aligning singular metrics and verifying consistency across {totalSelected} selected files.</p>
      </div>
    );
  }

  if (!consensusData || points.length === 0) {
    return (
      <div className="consensus-empty-state">
        <div className="consensus-empty-icon">
          <GitCompare size={36} />
        </div>
        <h3>No Shared Multi-Document Points Discovered</h3>
        <p>
          The selected documents did not contain common predicates with
          overlapping entities to align in a shared consensus matrix.
        </p>
        {onRefresh && (
          <button className="btn btn-outline btn-sm" onClick={onRefresh} style={{ marginTop: '1rem' }}>
            Re-evaluate Consensus
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="multi-doc-matrix-container" id="multi-doc-matrix-view">
      {/* Overview Banner */}
      <div className="consensus-hero-card">
        <div className="consensus-hero-header">
          <div className="consensus-hero-badge">
            <Sparkles size={14} />
            <span>N-Way Consensus Engine</span>
          </div>
          <span className="consensus-hero-count">
            Comparing <strong>{totalSelected} Documents</strong> across <strong>{points.length} Singular Points</strong>
          </span>
        </div>

        <p className="consensus-hero-desc">
          Each row synthesizes a common subject and metric aligned side-by-side across all reporting files.
          Discrepancies are automatically classified as <strong>Unanimous Corroboration</strong>, <strong>Temporal/Scope Drift</strong>, or <strong>Direct Conflict</strong>.
        </p>

        {/* Participating document chips */}
        <div className="consensus-doc-chips">
          <span className="consensus-chips-label">Participating Files:</span>
          {documents.map((doc, idx) => (
            <div key={doc.id} className="consensus-doc-chip" title={`${doc.filename} (${doc.page_count} pages)`}>
              <span className="consensus-doc-chip-index">Doc {idx + 1}</span>
              <FileText size={12} />
              <span className="consensus-doc-chip-name">{doc.filename}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="consensus-filter-bar">
        <div className="search-input-wrapper">
          <Search size={15} className="search-icon" />
          <input
            id="search-consensus-input"
            type="text"
            placeholder="Search metric, entity, or claim value..."
            className="search-input"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        <div className="filter-pills">
          <button
            className={`filter-pill ${filterVerdict === 'ALL' ? 'active' : ''}`}
            onClick={() => setFilterVerdict('ALL')}
          >
            All Points ({counts.ALL})
          </button>
          <button
            className={`filter-pill ${filterVerdict === 'CONTRADICTS' ? 'active' : ''}`}
            onClick={() => setFilterVerdict('CONTRADICTS')}
          >
            Conflicts ({counts.CONTRADICTS})
          </button>
          <button
            className={`filter-pill ${filterVerdict === 'CORROBORATES' ? 'active' : ''}`}
            onClick={() => setFilterVerdict('CORROBORATES')}
          >
            Corroborated ({counts.CORROBORATES})
          </button>
          <button
            className={`filter-pill ${filterVerdict === 'CONTEXTUALIZES' ? 'active' : ''}`}
            onClick={() => setFilterVerdict('CONTEXTUALIZES')}
          >
            Context Drift ({counts.CONTEXTUALIZES})
          </button>
          {counts.UNCERTAIN > 0 && (
            <button
              className={`filter-pill ${filterVerdict === 'UNCERTAIN' ? 'active' : ''}`}
              onClick={() => setFilterVerdict('UNCERTAIN')}
            >
              Uncertain ({counts.UNCERTAIN})
            </button>
          )}
        </div>
      </div>

      {/* Results Header */}
      <div className="consensus-results-meta">
        <span>Showing {filteredPoints.length} of {points.length} multi-document points</span>
      </div>

      {/* Matrix Cards List */}
      <div className="consensus-cards-list">
        {filteredPoints.map((pt, pIdx) => {
          const cfg = VERDICT_CONFIG[pt.verdict] || VERDICT_CONFIG.UNCERTAIN;
          const confPct = Math.round(pt.confidence * 100);

          return (
            <div key={pt.id || pIdx} className="consensus-card" id={`consensus-point-${pIdx}`}>
              {/* Card Header */}
              <div className="consensus-card-header">
                <div className="consensus-card-entity">
                  <span className="consensus-point-subject">{pt.subject}</span>
                  <span className="consensus-point-separator">•</span>
                  <span className="consensus-point-predicate">{pt.predicate}</span>
                </div>

                <div className="consensus-card-badges">
                  <span className={`badge ${cfg.badgeClass}`}>
                    {cfg.icon}
                    {cfg.title}
                  </span>
                  <span className="badge badge-confidence" title="Mean factual extraction confidence across reporting files">
                    {confPct}% conf
                  </span>
                  <span className="consensus-participation-badge">
                    {pt.participating_count} of {pt.total_selected} files reported
                  </span>
                </div>
              </div>

              {/* Multi-Way Synthesis Narrative */}
              <div className="consensus-card-narrative">
                <Info size={14} className="consensus-narrative-icon" />
                <p className="consensus-narrative-text">{pt.summary}</p>
              </div>

              {/* Side-by-side Document Claims Grid (2 to 5 columns) */}
              <div
                className="consensus-claims-grid"
                style={{
                  gridTemplateColumns: `repeat(${Math.min(pt.claims.length, 5)}, minmax(0, 1fr))`
                }}
              >
                {pt.claims.map((claim, cIdx) => {
                  const claimKey = `${pt.id}_${claim.document_id}_${cIdx}`;
                  const isExpanded = !!expandedQuotes[claimKey];

                  if (!claim.has_claim) {
                    return (
                      <div key={claim.document_id || cIdx} className="consensus-claim-col empty-col">
                        <div className="consensus-col-header">
                          <span className="consensus-col-doc-num">Doc {cIdx + 1}</span>
                          <span className="consensus-col-doc-name" title={claim.document_name}>
                            {claim.document_name}
                          </span>
                        </div>
                        <div className="consensus-col-empty-body">
                          <span className="consensus-empty-dash">—</span>
                          <span className="consensus-empty-label">Not mentioned in this filing</span>
                        </div>
                      </div>
                    );
                  }

                  return (
                    <div key={claim.document_id || cIdx} className="consensus-claim-col active-col">
                      {/* Column Header */}
                      <div className="consensus-col-header">
                        <div className="consensus-col-header-left">
                          <span className="consensus-col-doc-num">Doc {cIdx + 1}</span>
                          <span className="consensus-col-doc-name" title={claim.document_name}>
                            {claim.document_name}
                          </span>
                        </div>
                        {claim.page && (
                          <span className="consensus-col-page-tag" title={`Page ${claim.page}`}>
                            p. {claim.page}
                          </span>
                        )}
                      </div>

                      {/* Claim Value Highlight */}
                      <div className="consensus-col-value-box">
                        <div className="consensus-col-raw-value">
                          {claim.raw_value}
                        </div>
                        {claim.unit && (
                          <div className="consensus-col-unit">
                            {claim.unit}
                          </div>
                        )}
                      </div>

                      {/* Context Tags (Time, Scope, Geography) */}
                      {(claim.time || claim.scope || claim.geography) && (
                        <div className="consensus-col-context-tags">
                          {claim.time && (
                            <span className="consensus-ctx-tag time-tag" title="Time / Reporting Period">
                              {claim.time}
                            </span>
                          )}
                          {claim.scope && (
                            <span className="consensus-ctx-tag scope-tag" title="Scope / Accounting Category">
                              {claim.scope}
                            </span>
                          )}
                          {claim.geography && (
                            <span className="consensus-ctx-tag geo-tag" title="Geography">
                              {claim.geography}
                            </span>
                          )}
                        </div>
                      )}

                      {/* Evidence Quote */}
                      {claim.evidence_quote && (
                        <div className="consensus-col-quote-box">
                          <p className={`consensus-col-quote-text ${isExpanded ? 'expanded' : ''}`}>
                            "{claim.evidence_quote}"
                          </p>
                          {claim.evidence_quote.length > 110 && (
                            <button
                              type="button"
                              className="consensus-quote-toggle-btn"
                              onClick={() => toggleExpandQuote(claimKey)}
                            >
                              {isExpanded ? (
                                <>Less <ChevronUp size={11} /></>
                              ) : (
                                <>Expand quote <ChevronDown size={11} /></>
                              )}
                            </button>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
