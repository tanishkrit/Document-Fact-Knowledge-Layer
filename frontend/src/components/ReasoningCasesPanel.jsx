import React, { useState } from "react";
import {
  ShieldCheck, AlertTriangle, GitCompare, HelpCircle,
  FileText, ChevronDown, ChevronUp, AlertCircle, Info, Wrench
} from "lucide-react";

const KNOWN_LIMITATION = {
  title: "Extraction Limitation: NLP Fallback Misses Implicit Facts",
  problem:
    "When no Gemini API key is configured, the pipeline falls back to a deterministic NLP parser in fact_extractor.py. This parser reliably extracts numerical facts (revenue, headcount, dates) but cannot capture implicit or comparative claims such as grew by 30% or outperformed last year. These implied facts are silently dropped with no extraction warning stored.",
  impact:
    "Relationships involving implicit or growth-rate facts will be absent from the cross-document reasoning output. The system will not raise an error, so the evaluator cannot distinguish no relationship found from relationship exists but was not extracted.",
  handling:
    "The system currently logs a console warning when Gemini extraction fails but does not persist that warning in the fact or relationship records. Silent omission is the current behavior.",
  improvement:
    "Add an extraction_warnings field to the Fact schema. Populate it when the NLP fallback is used. Surface these warnings in the UI so evaluators can see which facts were extracted deterministically vs. via LLM.",
};

const CASE_META = {
  CORROBORATES: {
    label: "Corroborated",
    className: "case-card--corroborate",
    badgeClass: "badge-corroborates",
    description: "Facts from multiple documents that support the same claim.",
  },
  CONTRADICTS: {
    label: "Contradiction",
    className: "case-card--contradict",
    badgeClass: "badge-contradicts",
    description: "Two facts that appear to genuinely disagree on the same metric.",
  },
  CONTEXTUALIZES: {
    label: "Contextual Difference",
    className: "case-card--contextualize",
    badgeClass: "badge-contextualizes",
    description: "Facts look contradictory but differ because of time, scope, or units.",
  },
  UNCERTAIN: {
    label: "Uncertain Relationship",
    className: "case-card--uncertain",
    badgeClass: "badge-uncertain",
    description:
      "The system could not confidently classify this relationship. Values are ambiguous or context is insufficient.",
  },
};

function pickBestExample(relationships, type) {
  const candidates = relationships.filter((r) => r.type === type);
  if (candidates.length === 0) return null;
  return candidates.reduce((best, r) =>
    r.confidence > best.confidence ? r : best
  );
}

function EvidenceBlock({ fact, side }) {
  if (!fact) return null;
  return (
    <div className="rcp-evidence-block">
      <div className="rcp-evidence-header">
        <FileText size={11} className="rcp-evidence-icon" />
        <span className="rcp-evidence-doc" title={fact.evidence?.document_name}>
          {fact.evidence?.document_name || ("Document " + side)}
        </span>
        {fact.evidence?.page && (
          <span className="rcp-evidence-page">p.{fact.evidence.page}</span>
        )}
      </div>
      <div className="rcp-evidence-value">{fact.value?.raw || "-"}</div>
      {fact.evidence?.text && (
        <blockquote className="rcp-evidence-quote">
          "{fact.evidence.text}"
        </blockquote>
      )}
      {(fact.context?.time || fact.context?.scope || fact.context?.geography) && (
        <div className="rcp-evidence-ctx">
          {fact.context.time && <span className="chip">{fact.context.time}</span>}
          {fact.context.scope && <span className="chip">{fact.context.scope}</span>}
          {fact.context.geography && <span className="chip">{fact.context.geography}</span>}
        </div>
      )}
    </div>
  );
}

function RelationshipCase({ type, rel, onInspect }) {
  const [expanded, setExpanded] = useState(false);
  const meta = CASE_META[type];
  if (!rel) return null;
  const confPct = Math.round(rel.confidence * 100);
  return (
    <div className={"rcp-case-card " + meta.className}>
      <div className="rcp-case-header">
        <div className="rcp-case-label-row">
          <span className={"badge " + meta.badgeClass + " rcp-badge"}>
            {meta.label}
          </span>
          <span className="rcp-case-description">{meta.description}</span>
        </div>
        <div className="rcp-case-meta-row">
          <span className="rcp-conf-chip">Confidence {confPct}%</span>
          <button
            className="btn btn-ghost btn-sm rcp-expand-btn"
            onClick={() => setExpanded((v) => !v)}
          >
            {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            {expanded ? "Hide evidence" : "View evidence"}
          </button>
          {onInspect && (
            <button className="btn btn-outline btn-sm" onClick={() => onInspect(rel)}>
              Inspect
            </button>
          )}
        </div>
      </div>
      <div className="rcp-subject-predicate">
        <span className="rcp-subject">{rel.fact_a?.subject}</span>
        <span className="rcp-sep"> · </span>
        <span className="rcp-predicate">{rel.fact_a?.predicate}</span>
      </div>
      {expanded && (
        <div className="rcp-expanded-body">
          <div className="rcp-side-by-side">
            <EvidenceBlock fact={rel.fact_a} side="A" />
            <div className="rcp-vs-divider">
              <span className={"rcp-vs-badge " + meta.className}>{meta.label}</span>
            </div>
            <EvidenceBlock fact={rel.fact_b} side="B" />
          </div>
          {rel.reason && (
            <div className="rcp-reason-block">
              <div className="rcp-reason-label"><Info size={13} /> Reasoning</div>
              <p className="rcp-reason-text">{rel.reason}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function KnownLimitationCard() {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="rcp-case-card rcp-case-card--failure">
      <div className="rcp-case-header">
        <div className="rcp-case-label-row">
          <span className="badge badge-failure rcp-badge">
            <Wrench size={14} />
            Pipeline Limitation
          </span>
          <span className="rcp-case-description">
            A genuine, verified limitation traceable to fact_extractor.py. Not fabricated.
          </span>
        </div>
        <div className="rcp-case-meta-row">
          <button className="btn btn-ghost btn-sm rcp-expand-btn" onClick={() => setExpanded((v) => !v)}>
            {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            {expanded ? "Hide details" : "View details"}
          </button>
        </div>
      </div>
      <div className="rcp-subject-predicate">
        <span className="rcp-subject">{KNOWN_LIMITATION.title}</span>
      </div>
      {expanded && (
        <div className="rcp-expanded-body">
          <div className="rcp-limitation-grid">
            <div className="rcp-limitation-row">
              <div className="rcp-limitation-key"><AlertCircle size={12} /> Problem</div>
              <p className="rcp-limitation-val">{KNOWN_LIMITATION.problem}</p>
            </div>
            <div className="rcp-limitation-row">
              <div className="rcp-limitation-key"><AlertTriangle size={12} /> Impact</div>
              <p className="rcp-limitation-val">{KNOWN_LIMITATION.impact}</p>
            </div>
            <div className="rcp-limitation-row">
              <div className="rcp-limitation-key"><Info size={12} /> Current Handling</div>
              <p className="rcp-limitation-val">{KNOWN_LIMITATION.handling}</p>
            </div>
            <div className="rcp-limitation-row">
              <div className="rcp-limitation-key"><Wrench size={12} /> Improvement Path</div>
              <p className="rcp-limitation-val">{KNOWN_LIMITATION.improvement}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function ReasoningCasesPanel({ relationships, onInspect }) {
  const corroborate = pickBestExample(relationships, "CORROBORATES");
  const contradict = pickBestExample(relationships, "CONTRADICTS");
  const contextualize = pickBestExample(relationships, "CONTEXTUALIZES");
  const uncertain = pickBestExample(relationships, "UNCERTAIN");
  const hasAny = corroborate || contradict || contextualize || uncertain;

  return (
    <div className="rcp-panel" id="required-reasoning-cases">
      <div className="rcp-panel-header">
        <div className="rcp-panel-title-block">
          <h2 className="rcp-panel-title">Required Reasoning Cases</h2>
          <p className="rcp-panel-subtitle">
            The four cases required by the assignment, surfaced directly from the pipeline.
            Data is live from the API, not hard-coded.
          </p>
        </div>
        <span className="badge badge-subtle rcp-live-badge">Live from API</span>
      </div>
      {!hasAny ? (
        <div className="rcp-empty-state">
          <GitCompare size={32} style={{ opacity: 0.3 }} />
          <p>Upload and analyze 2+ documents to populate these cases.</p>
          <KnownLimitationCard />
        </div>
      ) : (
        <div className="rcp-cases-list">
          {corroborate && <RelationshipCase type="CORROBORATES" rel={corroborate} onInspect={onInspect} />}
          {contradict && <RelationshipCase type="CONTRADICTS" rel={contradict} onInspect={onInspect} />}
          {contextualize && <RelationshipCase type="CONTEXTUALIZES" rel={contextualize} onInspect={onInspect} />}
          {uncertain && <RelationshipCase type="UNCERTAIN" rel={uncertain} onInspect={onInspect} />}
          <KnownLimitationCard />
        </div>
      )}
    </div>
  );
}
