import React from 'react';
import { X, ShieldCheck, AlertTriangle, HelpCircle, GitCompare, FileText, CheckCircle2, Sparkles, Quote } from 'lucide-react';

const TYPE_CONFIG = {
  CORROBORATES: {
    badgeClass: 'badge-corroborates',
    icon: <ShieldCheck size={16} />,
    title: 'Claims Corroborate Each Other'
  },
  CONTRADICTS: {
    badgeClass: 'badge-contradicts',
    icon: <AlertTriangle size={16} />,
    title: 'Genuine Contradiction Detected'
  },
  CONTEXTUALIZES: {
    badgeClass: 'badge-contextualizes',
    icon: <GitCompare size={16} />,
    title: 'Apparent Contradiction Resolved by Context'
  },
  UNCERTAIN: {
    badgeClass: 'badge-uncertain',
    icon: <HelpCircle size={16} />,
    title: 'Uncertain / Underspecified Relationship'
  },
  RELATED: {
    badgeClass: 'badge-contextualizes',
    icon: <GitCompare size={16} />,
    title: 'Related Claims'
  }
};

export default function ComparisonModal({ relationship, onClose }) {
  if (!relationship) return null;

  const factA = relationship.fact_a;
  const factB = relationship.fact_b;
  const conf = TYPE_CONFIG[relationship.type] || TYPE_CONFIG.RELATED;
  const confPct = Math.round(relationship.confidence * 100);

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
            <span className={`badge ${conf.badgeClass}`} style={{ fontSize: '0.78rem', padding: '0.3rem 0.75rem' }}>
              {conf.icon}
              {relationship.type}
            </span>
            <span style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--text-primary)', letterSpacing: '-0.015em' }}>
              {factA?.subject} — <span style={{ color: 'var(--primary)', fontWeight: 600 }}>{factA?.predicate}</span>
            </span>
          </div>

          <button
            className="btn btn-ghost btn-sm modal-close-btn"
            onClick={onClose}
            title="Close inspection"
          >
            <X size={18} />
          </button>
        </div>

        {/* Modal Body */}
        <div className="modal-body">
          {/* Reasoning narrative block */}
          <div className="reasoning-panel">
            <div className="reasoning-heading">
              <Sparkles size={16} style={{ color: 'var(--primary)' }} />
              <span>Cross-Document Reasoning Narrative</span>
              <div className="confidence-pill" style={{ marginLeft: 'auto' }}>
                <span className="confidence-pill-dot" />
                <span className="confidence-pill-label">Confidence</span>
                <span className="confidence-pill-val">{confPct}%</span>
              </div>
            </div>
            <div className="reasoning-text">
              {relationship.reason}
            </div>
          </div>

          {/* Side-by-side Evidence & Normalization */}
          <div className="side-by-side-comparison">
            {/* Fact A Side */}
            <div className="side-card">
              <div className="side-card-title">
                <FileText size={15} style={{ color: 'var(--primary)' }} />
                <span className="side-doc-name" title={factA?.evidence.document_name}>
                  {factA?.evidence.document_name}
                </span>
                <span className="side-page-pill">Page {factA?.evidence.page}</span>
              </div>

              {/* Exact Quote */}
              <div className="modal-quote-box">
                <div className="modal-quote-label">
                  <Quote size={11} style={{ display: 'inline', marginRight: '4px' }} />
                  Source Evidence Text
                </div>
                <div className="modal-quote-text">
                  "{factA?.evidence.text}"
                </div>
              </div>

              {/* Normalization Specs */}
              <div className="modal-specs-box">
                <div className="modal-specs-title">Canonical Normalization</div>
                <div className="modal-spec-row">
                  <span className="modal-spec-key">Raw Claim:</span>
                  <strong className="modal-spec-val highlight">{factA?.value.raw}</strong>
                </div>
                {factA?.value.amount !== null && factA?.value.amount !== undefined && (
                  <div className="modal-spec-row">
                    <span className="modal-spec-key">Amount:</span>
                    <strong className="modal-spec-val" style={{ color: 'var(--color-corroborate-text)' }}>
                      {factA?.value.amount.toLocaleString()} {factA?.value.unit || factA?.value.currency || ''}
                    </strong>
                  </div>
                )}
                {factA?.context.time && (
                  <div className="modal-spec-row">
                    <span className="modal-spec-key">Timeframe:</span>
                    <span className="modal-spec-val">{factA.context.time}</span>
                  </div>
                )}
                {factA?.context.scope && (
                  <div className="modal-spec-row">
                    <span className="modal-spec-key">Scope:</span>
                    <span className="modal-spec-val">{factA.context.scope}</span>
                  </div>
                )}
                {factA?.context.geography && (
                  <div className="modal-spec-row">
                    <span className="modal-spec-key">Geography:</span>
                    <span className="modal-spec-val">{factA.context.geography}</span>
                  </div>
                )}
              </div>
            </div>

            {/* Fact B Side */}
            <div className="side-card">
              <div className="side-card-title">
                <FileText size={15} style={{ color: 'var(--primary)' }} />
                <span className="side-doc-name" title={factB?.evidence.document_name}>
                  {factB?.evidence.document_name}
                </span>
                <span className="side-page-pill">Page {factB?.evidence.page}</span>
              </div>

              {/* Exact Quote */}
              <div className="modal-quote-box">
                <div className="modal-quote-label">
                  <Quote size={11} style={{ display: 'inline', marginRight: '4px' }} />
                  Source Evidence Text
                </div>
                <div className="modal-quote-text">
                  "{factB?.evidence.text}"
                </div>
              </div>

              {/* Normal ソSpecs */}
              <div className="modal-specs-box">
                <div className="modal-specs-title">Canonical Normalization</div>
                <div className="modal-spec-row">
                  <span className="modal-spec-key">Raw Claim:</span>
                  <strong className="modal-spec-val highlight">{factB?.value.raw}</strong>
                </div>
                {factB?.value.amount !== null && factB?.value.amount !== undefined && (
                  <div className="modal-spec-row">
                    <span className="modal-spec-key">Amount:</span>
                    <strong className="modal-spec-val" style={{ color: 'var(--color-corroborate-text)' }}>
                      {factB?.value.amount.toLocaleString()} {factB?.value.unit || factB?.value.currency || ''}
                    </strong>
                  </div>
                )}
                {factB?.context.time && (
                  <div className="modal-spec-row">
                    <span className="modal-spec-key">Timeframe:</span>
                    <span className="modal-spec-val">{factB.context.time}</span>
                  </div>
                )}
                {factB?.context.scope && (
                  <div className="modal-spec-row">
                    <span className="modal-spec-key">Scope:</span>
                    <span className="modal-spec-val">{factB.context.scope}</span>
                  </div>
                )}
                {factB?.context.geography && (
                  <div className="modal-spec-row">
                    <span className="modal-spec-key">Geography:</span>
                    <span className="modal-spec-val">{factB.context.geography}</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
