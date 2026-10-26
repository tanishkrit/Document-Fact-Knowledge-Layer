import React, { useState, useEffect, useRef } from 'react';
import {
  MessageSquare,
  ShieldCheck,
  AlertTriangle,
  HelpCircle,
  Sparkles,
  Search,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  FileText,
  Clock,
  ArrowRight,
  RefreshCw,
  CheckCircle2,
  XCircle,
  Info
} from 'lucide-react';
import { api } from '../api';

export default function QAInterface({
  documents = [],
  selectedDocIds = [],
  focusedDocIds = null,
  onOpenComparisonModal,
}) {
  const [question, setQuestion] = useState('');
  const [sampleQuestions, setSampleQuestions] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [qaResult, setQaResult] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);
  const [activeSubTab, setActiveSubTab] = useState('CLAIMS'); // CLAIMS, CRITIC, PRECEDENCE, PASSAGES
  const [selectedCitationId, setSelectedCitationId] = useState(null);
  const passagesRef = useRef(null);

  // Load sample questions
  useEffect(() => {
    api.getSampleQuestions()
      .then(setSampleQuestions)
      .catch((err) => console.warn('Could not load sample questions:', err));
  }, []);

  // Determine active document scope
  const activeScopeDocIds = focusedDocIds || (selectedDocIds.length > 0 ? selectedDocIds : null);
  const activeDocCount = activeScopeDocIds ? activeScopeDocIds.length : documents.length;

  const handleAsk = async (queryText = question) => {
    const q = (queryText || '').trim();
    if (!q) return;

    setIsLoading(true);
    setErrorMsg(null);
    setQaResult(null);

    try {
      const res = await api.askQuestion(q, activeScopeDocIds);
      setQaResult(res);
      // Auto-select precedence tab if a conflict was detected
      if (res.conflict_resolution && res.conflict_resolution.status !== 'NO_CONFLICT') {
        setActiveSubTab('PRECEDENCE');
      } else {
        setActiveSubTab('CLAIMS');
      }
    } catch (err) {
      setErrorMsg(err.message || 'Verification pipeline encountered an error');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSelectSample = (sampleQ) => {
    setQuestion(sampleQ.question);
    handleAsk(sampleQ.question);
  };

  const handleCitationClick = (citId) => {
    setSelectedCitationId(citId);
    setActiveSubTab('PASSAGES');
    setTimeout(() => {
      const el = document.getElementById(`citation-card-${citId}`);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    }, 100);
  };

  const getVerdictBadge = (verdict) => {
    switch (verdict) {
      case 'VERIFIED':
        return (
          <span className="qa-verdict-badge verdict-verified">
            <ShieldCheck size={14} />
            Verified by TruthGuard
          </span>
        );
      case 'CONFLICT_DETECTED':
        return (
          <span className="qa-verdict-badge verdict-conflict">
            <AlertTriangle size={14} />
            Conflict / Contradiction Detected
          </span>
        );
      case 'INSUFFICIENT_EVIDENCE':
        return (
          <span className="qa-verdict-badge verdict-insufficient">
            <HelpCircle size={14} />
            Insufficient Corpus Evidence
          </span>
        );
      default:
        return (
          <span className="qa-verdict-badge verdict-uncertain">
            <Info size={14} />
            {verdict}
          </span>
        );
    }
  };

  return (
    <div className="qa-container">
      {/* Search & Query Card */}
      <div className="qa-query-card">
        <div className="qa-header-row">
          <div className="qa-header-title">
            <MessageSquare size={18} className="qa-title-icon" />
            <h3>Evidence-First Question Answering & Verification</h3>
          </div>
          <div className="qa-scope-indicator">
            <FileText size={13} />
            <span>
              Searching {activeScopeDocIds ? `${activeDocCount} Selected Document(s)` : `All ${documents.length} Document(s)`}
            </span>
          </div>
        </div>

        <p className="qa-subtitle">
          Ask questions across your document corpus. TruthGuard synthesizes claims with exact citations, runs an adversary critic to challenge contradictions, and applies source precedence.
        </p>

        {/* Input Bar */}
        <form
          className="qa-input-wrapper"
          onSubmit={(e) => {
            e.preventDefault();
            handleAsk();
          }}
        >
          <Search size={18} className="qa-search-icon" />
          <input
            type="text"
            className="qa-input"
            id="qa-question-input"
            placeholder="Ask a question (e.g. 'What was the FY2024 revenue?' or 'When was the company founded?')..."
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            disabled={isLoading}
          />
          <button
            type="submit"
            className="btn btn-primary qa-submit-btn"
            id="qa-submit-btn"
            disabled={isLoading || !question.trim()}
          >
            {isLoading ? (
              <>
                <RefreshCw size={14} className="animate-spin" />
                <span>Verifying...</span>
              </>
            ) : (
              <>
                <Sparkles size={14} />
                <span>Verify & Answer</span>
              </>
            )}
          </button>
        </form>

        {/* Sample Question Chips */}
        {sampleQuestions.length > 0 && (
          <div className="qa-samples-wrapper">
            <span className="qa-samples-label">Suggested Test Questions:</span>
            <div className="qa-samples-list">
              {sampleQuestions.map((sq) => (
                <button
                  key={sq.id}
                  type="button"
                  className="qa-sample-chip"
                  onClick={() => handleSelectSample(sq)}
                  disabled={isLoading}
                  title={`Category: ${sq.category}`}
                >
                  {sq.question}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Error Alert */}
      {errorMsg && (
        <div className="qa-error-alert">
          <AlertTriangle size={16} />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Loading Skeleton */}
      {isLoading && (
        <div className="qa-loading-stage">
          <div className="qa-loading-spinner-wrap">
            <RefreshCw size={28} className="animate-spin text-primary" />
          </div>
          <div className="qa-loading-steps">
            <div className="qa-loading-step">1. Retrieving candidate passages & temporal metadata...</div>
            <div className="qa-loading-step">2. Synthesizing claim decomposition & attaching citations...</div>
            <div className="qa-loading-step">3. Adversary Critic challenging draft for contradictions...</div>
            <div className="qa-loading-step">4. Applying source precedence & amendment resolution...</div>
          </div>
        </div>
      )}

      {/* Verification Result Section */}
      {qaResult && !isLoading && (
        <div className="qa-result-stage" id="qa-result-stage">
          {/* Main Answer Card */}
          <div className="qa-answer-card">
            <div className="qa-answer-header">
              <div className="qa-answer-q-tag">
                <span className="qa-q-label">Question:</span>
                <span className="qa-q-text">"{qaResult.question}"</span>
              </div>
              <div className="qa-answer-verdict-wrap">
                {getVerdictBadge(qaResult.verdict)}
              </div>
            </div>

            <div className="qa-answer-body">
              <div className="qa-answer-lead">Synthesized Answer & Evidence:</div>
              <p className="qa-answer-narrative">{qaResult.final_answer}</p>
            </div>

            {/* Quick Citations Bar */}
            {qaResult.citations && qaResult.citations.length > 0 && (
              <div className="qa-quick-citations">
                <span className="qa-quick-citations-label">Source Evidence Citations:</span>
                <div className="qa-citations-chips">
                  {qaResult.citations.map((c) => (
                    <button
                      key={c.citation_id}
                      type="button"
                      className={`qa-citation-chip ${selectedCitationId === c.citation_id ? 'active' : ''}`}
                      onClick={() => handleCitationClick(c.citation_id)}
                      title={`Page ${c.page} in ${c.document_name}`}
                    >
                      <FileText size={12} />
                      <span>{c.document_name} (p. {c.page})</span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Verification Stats Footer */}
            <div className="qa-answer-footer">
              <div className="qa-stat-item">
                <span className="qa-stat-label">Claims Analyzed:</span>
                <span className="qa-stat-val">{qaResult.claims?.length || 0}</span>
              </div>
              <div className="qa-stat-divider" />
              <div className="qa-stat-item">
                <span className="qa-stat-label">Critic Iterations:</span>
                <span className="qa-stat-val">{qaResult.iterations_run}</span>
              </div>
              <div className="qa-stat-divider" />
              <div className="qa-stat-item">
                <span className="qa-stat-label">Retrieved Passages:</span>
                <span className="qa-stat-val">{qaResult.retrieved_passages_count}</span>
              </div>
            </div>
          </div>

          {/* Inspection Sub-Navigation Tabs */}
          <div className="qa-subtabs-nav">
            <button
              className={`qa-subtab-btn ${activeSubTab === 'CLAIMS' ? 'active' : ''}`}
              onClick={() => setActiveSubTab('CLAIMS')}
            >
              <CheckCircle2 size={15} />
              <span>Discrete Claims ({qaResult.claims?.length || 0})</span>
            </button>

            <button
              className={`qa-subtab-btn ${activeSubTab === 'CRITIC' ? 'active' : ''}`}
              onClick={() => setActiveSubTab('CRITIC')}
            >
              <ShieldCheck size={15} />
              <span>Adversary Critic Audit ({qaResult.critic_history?.length || 0} Rounds)</span>
            </button>

            {qaResult.conflict_resolution && (
              <button
                className={`qa-subtab-btn qa-subtab-conflict ${activeSubTab === 'PRECEDENCE' ? 'active' : ''}`}
                onClick={() => setActiveSubTab('PRECEDENCE')}
              >
                <AlertTriangle size={15} />
                <span>
                  Source Precedence & Conflicts ({qaResult.conflict_resolution.status === 'RESOLVED_BY_PRECEDENCE' ? 'Resolved' : 'Unresolved'})
                </span>
              </button>
            )}

            <button
              className={`qa-subtab-btn ${activeSubTab === 'PASSAGES' ? 'active' : ''}`}
              onClick={() => setActiveSubTab('PASSAGES')}
            >
              <FileText size={15} />
              <span>Retrieved Provenance ({qaResult.citations?.length || 0})</span>
            </button>
          </div>

          {/* Sub-Tab Contents */}
          <div className="qa-subtab-stage">
            {/* 1. CLAIMS TAB */}
            {activeSubTab === 'CLAIMS' && (
              <div className="qa-claims-panel">
                <div className="qa-panel-intro">
                  Every factual assertion is isolated and audited. Directly supported claims are derived directly from quoted evidence, while inferences represent deductive synthesis.
                </div>
                <div className="qa-claims-grid">
                  {qaResult.claims?.map((claim, idx) => (
                    <div
                      key={claim.claim_id || idx}
                      className={`qa-claim-card ${claim.claim_type === 'inference' ? 'qa-claim-inference' : 'qa-claim-direct'}`}
                    >
                      <div className="qa-claim-header">
                        <span className={`qa-claim-type-pill ${claim.claim_type}`}>
                          {claim.claim_type === 'directly_supported' ? 'Direct Evidence' : claim.claim_type === 'inference' ? 'Inference' : 'Unsupported'}
                        </span>
                        <span className="qa-claim-confidence">
                          Confidence: {Math.round((claim.confidence || 0.9) * 100)}%
                        </span>
                      </div>
                      <div className="qa-claim-text">"{claim.text}"</div>
                      {claim.provenance_note && (
                        <div className="qa-claim-provenance">
                          <Info size={12} />
                          <span>{claim.provenance_note}</span>
                        </div>
                      )}
                      {claim.citation_ids && claim.citation_ids.length > 0 && (
                        <div className="qa-claim-citations">
                          <span>Attached Citations:</span>
                          {claim.citation_ids.map((cid) => (
                            <button
                              key={cid}
                              type="button"
                              className="qa-claim-cit-link"
                              onClick={() => handleCitationClick(cid)}
                            >
                              {cid}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 2. CRITIC AUDIT TAB */}
            {activeSubTab === 'CRITIC' && (
              <div className="qa-critic-panel">
                <div className="qa-panel-intro">
                  The Critic is an independent adversary that challenges draft answers for contradictions, missing citations, context mismatches, and stale policy versions.
                </div>
                <div className="qa-critic-rounds">
                  {qaResult.critic_history?.map((report, idx) => (
                    <div key={idx} className="qa-critic-round-card">
                      <div className="qa-critic-round-header">
                        <div className="qa-round-indicator">
                          <span className="qa-round-num">Round {report.round_number}</span>
                          <span className={`qa-round-status ${report.passed ? 'status-pass' : 'status-issues'}`}>
                            {report.passed ? 'Verification Passed' : `${report.issues.length} Flaw(s) Identified`}
                          </span>
                        </div>
                        <span className="qa-round-summary">{report.summary}</span>
                      </div>

                      {report.issues && report.issues.length > 0 ? (
                        <div className="qa-critic-issues-list">
                          {report.issues.map((issue, issueIdx) => (
                            <div key={issueIdx} className={`qa-issue-item severity-${issue.severity}`}>
                              <div className="qa-issue-header">
                                <span className="qa-issue-type">{issue.issue_type}</span>
                                <span className={`qa-issue-severity badge-${issue.severity}`}>
                                  {issue.severity.toUpperCase()} PRIORITY
                                </span>
                              </div>
                              <div className="qa-issue-desc">{issue.description}</div>
                              {issue.recommendation && (
                                <div className="qa-issue-rec">
                                  <strong>Adversary Action:</strong> {issue.recommendation}
                                </div>
                              )}
                              {issue.counter_evidence && (
                                <div className="qa-issue-counter">
                                  <span className="qa-counter-title">Counter-Evidence Passage:</span>
                                  <div className="qa-counter-quote">
                                    "{issue.counter_evidence.quote_text}"
                                    <span className="qa-counter-doc">
                                      — {issue.counter_evidence.document_name} (p. {issue.counter_evidence.page})
                                    </span>
                                  </div>
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="qa-critic-clean-pass">
                          <CheckCircle2 size={16} className="text-success" />
                          <span>No unsupported assertions or unacknowledged contradictions were found.</span>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 3. PRECEDENCE & CONFLICTS TAB */}
            {activeSubTab === 'PRECEDENCE' && qaResult.conflict_resolution && (
              <div className="qa-precedence-panel">
                <div className="qa-panel-intro">
                  When documents present opposing facts, TruthGuard evaluates effective dates and amendment metadata. If authority or dates do not decisively resolve the conflict, both positions are preserved side-by-side.
                </div>

                <div className={`qa-precedence-summary-box ${qaResult.conflict_resolution.status}`}>
                  <div className="qa-precedence-status-row">
                    <span className="qa-precedence-label">Resolution Status:</span>
                    <span className="qa-precedence-tag">
                      {qaResult.conflict_resolution.status === 'RESOLVED_BY_PRECEDENCE'
                        ? 'RESOLVED BY SOURCE PRECEDENCE'
                        : 'UNRESOLVED CONFLICT (BOTH POSITIONS RETAINED)'}
                    </span>
                  </div>
                  <div className="qa-precedence-rationale">
                    <strong>Precedence Rationale:</strong> {qaResult.conflict_resolution.rationale}
                  </div>
                </div>

                {/* Dual Position Side-by-Side Comparison */}
                {qaResult.conflict_resolution.positions && qaResult.conflict_resolution.positions.length >= 2 && (
                  <div className="qa-dual-positions-grid">
                    {qaResult.conflict_resolution.positions.map((pos, pIdx) => {
                      const isPreferred = qaResult.conflict_resolution.preferred_position?.document_id === pos.document_id;
                      return (
                        <div
                          key={pIdx}
                          className={`qa-position-card ${isPreferred ? 'position-preferred' : ''}`}
                        >
                          <div className="qa-position-header">
                            <span className="qa-pos-index">Position {pIdx === 0 ? 'A' : 'B'}</span>
                            {isPreferred && (
                              <span className="qa-preferred-badge">
                                <ShieldCheck size={12} />
                                Governs by Precedence
                              </span>
                            )}
                          </div>

                          <div className="qa-position-doc-name">
                            <FileText size={14} />
                            <span>{pos.document_name}</span>
                          </div>

                          <div className="qa-position-meta">
                            {pos.effective_date && (
                              <div className="qa-pos-meta-item">
                                <Clock size={12} />
                                <span>Effective: {pos.effective_date}</span>
                              </div>
                            )}
                            <div className="qa-pos-meta-item">
                              <span>Page: {pos.page}</span>
                            </div>
                          </div>

                          <div className="qa-position-value">
                            <span className="qa-val-label">Claimed Value:</span>
                            <span className="qa-val-text">{pos.claimed_value}</span>
                          </div>

                          <div className="qa-position-quote">
                            <span className="qa-quote-label">Exact Source Text:</span>
                            <p>"{pos.evidence_text}"</p>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}

            {/* 4. PASSAGES & PROVENANCE TAB */}
            {activeSubTab === 'PASSAGES' && (
              <div className="qa-passages-panel" ref={passagesRef}>
                <div className="qa-panel-intro">
                  Every citation links directly to the underlying document, page, and text passage.
                </div>
                <div className="qa-passages-grid">
                  {qaResult.citations?.map((cit) => (
                    <div
                      key={cit.citation_id}
                      id={`citation-card-${cit.citation_id}`}
                      className={`qa-passage-card ${selectedCitationId === cit.citation_id ? 'citation-selected' : ''}`}
                    >
                      <div className="qa-passage-header">
                        <div className="qa-passage-cit-id">{cit.citation_id}</div>
                        <div className="qa-passage-doc-info">
                          <FileText size={13} />
                          <span className="qa-passage-doc-name">{cit.document_name}</span>
                          <span className="qa-passage-page">Page {cit.page}</span>
                        </div>
                      </div>

                      <div className="qa-passage-quote">
                        "{cit.quote_text}"
                      </div>

                      <div className="qa-passage-footer">
                        {cit.effective_date && (
                          <span className="qa-meta-pill">
                            Effective: {cit.effective_date}
                          </span>
                        )}
                        {cit.publication_date && (
                          <span className="qa-meta-pill">
                            Published: {cit.publication_date}
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
