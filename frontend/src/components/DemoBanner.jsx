import React from 'react';
import { Play, CheckCircle2, AlertTriangle, HelpCircle, GitCompare, Sparkles } from 'lucide-react';

const CASE_ICONS = {
  case_1: <CheckCircle2 size={13} className="text-emerald-400" />,
  case_2: <AlertTriangle size={13} className="text-rose-400" />,
  case_3: <GitCompare size={13} className="text-cyan-400" />,
  case_4: <HelpCircle size={13} className="text-amber-400" />
};

export default function DemoBanner({ demoCases, activeCaseId, onLoadDemo, isLoadingDemo }) {
  return (
    <nav aria-label="Demonstration Cases" className="demo-banner">
      <span className="demo-banner-label">
        <Sparkles size={14} style={{ color: 'var(--primary)' }} />
        Demo Cases:
      </span>

      {demoCases.map((c) => {
        const isActive = activeCaseId === c.id;
        return (
          <button
            key={c.id}
            id={`demo-btn-${c.id}`}
            className={`demo-pill ${isActive ? 'active' : ''}`}
            onClick={() => onLoadDemo(c.id)}
            disabled={isLoadingDemo}
            title={c.description}
          >
            {CASE_ICONS[c.id] || <Play size={12} />}
            <span>{c.title}</span>
          </button>
        );
      })}
    </nav>
  );
}
