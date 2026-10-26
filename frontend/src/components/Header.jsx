import React from 'react';
import { Layers, Moon, Sun, Trash2, PanelLeftClose, PanelLeftOpen } from 'lucide-react';

export default function Header({
  theme,
  toggleTheme,
  onClearAll,
  isClearing,
  isSidebarOpen = true,
  toggleSidebar
}) {
  return (
    <header className="app-header">
      <div className="header-brand">
        {toggleSidebar && (
          <button
            id="sidebar-toggle-btn"
            className="btn btn-ghost btn-sm sidebar-toggle-btn"
            onClick={toggleSidebar}
            title={isSidebarOpen ? 'Collapse sidebar to expand analysis' : 'Expand documents sidebar'}
            aria-label="Toggle Sidebar"
          >
            {isSidebarOpen ? <PanelLeftClose size={16} /> : <PanelLeftOpen size={16} />}
          </button>
        )}

        <div className="logo-badge">
          <Layers size={19} />
        </div>
        <div className="header-title-block">
          <h1 id="app-title">
            Fact Knowledge Layer
          </h1>
          <p className="header-subtitle">
            Evidence-grounded extraction &nbsp;·&nbsp; normalization &nbsp;·&nbsp; cross-document reasoning
          </p>
        </div>
      </div>

      <div className="header-actions">
        <button
          id="clear-db-btn"
          className="btn btn-outline btn-sm"
          onClick={onClearAll}
          disabled={isClearing}
          title="Reset all documents and extracted facts"
        >
          <Trash2 size={13} />
          <span className="btn-text-hide-mobile">{isClearing ? 'Resetting...' : 'Reset Layer'}</span>
        </button>

        <button
          id="theme-toggle-btn"
          className="btn btn-outline btn-sm"
          onClick={toggleTheme}
          title="Toggle Light / Dark Mode"
        >
          {theme === 'dark' ? <Sun size={14} /> : <Moon size={14} />}
        </button>
      </div>
    </header>
  );
}
