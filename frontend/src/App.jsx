import React, { useState, useEffect } from 'react';
import { api } from './api';
import Header from './components/Header';
import DocumentSidebar from './components/DocumentSidebar';
import RelationshipMatrix from './components/RelationshipMatrix';
import FactExplorer from './components/FactExplorer';
import ComparisonModal from './components/ComparisonModal';
import MultiDocumentMatrix from './components/MultiDocumentMatrix';
import ReasoningCasesPanel from './components/ReasoningCasesPanel';
import QAInterface from './components/QAInterface';
import { GitCompare, Layers, Search, Filter, RefreshCw, AlertCircle, Sparkles, PanelLeftOpen, FileText, Database, Link2, MessageSquare } from 'lucide-react';

export default function App() {
  const [theme, setTheme] = useState('light');
  const [activeTab, setActiveTab] = useState('QA'); // 'QA', 'CASES', 'CONSENSUS', 'RELATIONSHIPS', 'FACTS'
  
  // Data states
  const [documents, setDocuments] = useState([]);
  const [facts, setFacts] = useState([]);
  const [relationships, setRelationships] = useState([]);
  const [consensusData, setConsensusData] = useState(null); // Multi-document consensus matrix
  
  // UI states
  const [selectedDocId, setSelectedDocId] = useState(null);
  const [selectedDocIds, setSelectedDocIds] = useState([]); // Selected for multi-file joint analysis (2-5 files)
  const [focusedDocIds, setFocusedDocIds] = useState(null); // Active joint analysis filter
  const [selectedRelationship, setSelectedRelationship] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [relFilter, setRelFilter] = useState('ALL'); // ALL, CORROBORATES, CONTRADICTS, CONTEXTUALIZES, UNCERTAIN
  const [isSidebarOpen, setIsSidebarOpen] = useState(true); // Responsive collapsible sidebar
  
  // Loading states
  const [isUploading, setIsUploading] = useState(false);
  const [uploadStage, setUploadStage] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingStage, setProcessingStage] = useState('');
  const [isAnalyzingSelected, setIsAnalyzingSelected] = useState(false);
  const [analyzeStage, setAnalyzeStage] = useState('');
  const [deletingDocId, setDeletingDocId] = useState(null);
  const [isClearing, setIsClearing] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);

  // Sync theme attribute on document root
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  // Helper to ensure documents list is strictly unique by file_hash or id
  const deduplicateDocs = (docList) => {
    if (!Array.isArray(docList)) return [];
    const seen = new Set();
    return docList.filter((doc) => {
      const key = doc.file_hash ? doc.file_hash : (doc.id || doc.filename);
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  };

  // Initial load
  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    try {
      const [docs, storedFacts, storedRels] = await Promise.all([
        api.getDocuments(),
        api.getFacts(),
        api.getRelationships(),
      ]);
      setDocuments(deduplicateDocs(docs));
      setFacts(storedFacts);
      setRelationships(storedRels);
    } catch (err) {
      console.error('Initial load error:', err);
      setErrorMsg('Could not connect to Fact Knowledge Layer API (http://localhost:8000). Ensure the backend is running.');
    }
  };

  const refreshKnowledgeData = async (filterDocIds = focusedDocIds) => {
    try {
      const [docs, storedFacts, storedRels] = await Promise.all([
        api.getDocuments(),
        api.getFacts(selectedDocId, filterDocIds),
        api.getRelationships(null, filterDocIds),
      ]);
      setDocuments(deduplicateDocs(docs));
      setFacts(storedFacts);
      setRelationships(storedRels);

      if (filterDocIds && filterDocIds.length >= 2) {
        const matrix = await api.getConsensusMatrix(filterDocIds).catch(() => null);
        setConsensusData(matrix);
      }
    } catch (err) {
      console.error('Refresh error:', err);
    }
  };

  const handleToggleTheme = () => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

  // Document upload handler
  const handleUpload = async (fileList) => {
    setIsUploading(true);
    setUploadStage('Uploading files...');
    setErrorMsg(null);
    try {
      setUploadStage('Extracting text from PDFs...');
      await api.uploadDocuments(fileList);
      setUploadStage('Indexing pages...');
      await refreshKnowledgeData();
    } catch (err) {
      setErrorMsg(err.message);
    } finally {
      setIsUploading(false);
      setUploadStage('');
    }
  };

  // Process single document
  const handleProcessDocument = async (docId) => {
    setIsProcessing(true);
    setProcessingStage('Extracting text...');
    setErrorMsg(null);
    try {
      setProcessingStage('Discovering facts...');
      await api.processDocument(docId);
      setProcessingStage('Linking evidence & building relationships...');
      await refreshKnowledgeData();
    } catch (err) {
      setErrorMsg(err.message);
    } finally {
      setIsProcessing(false);
      setProcessingStage('');
    }
  };

  // Process all documents
  const handleProcessAll = async () => {
    setIsProcessing(true);
    setProcessingStage('Processing documents...');
    setErrorMsg(null);
    try {
      setProcessingStage('Extracting text & discovering facts...');
      await api.processAll();
      setProcessingStage('Comparing facts across documents...');
      await refreshKnowledgeData();
    } catch (err) {
      setErrorMsg(err.message);
    } finally {
      setIsProcessing(false);
      setProcessingStage('');
    }
  };

  // Multi-document selection toggle (capped at 5 files)
  const handleToggleSelectDoc = (docId) => {
    setErrorMsg(null);
    setSelectedDocIds((prev) => {
      if (prev.includes(docId)) {
        return prev.filter((id) => id !== docId);
      }
      if (prev.length >= 5) {
        setErrorMsg('Maximum 5 files can be selected simultaneously for comparison.');
        return prev;
      }
      return [...prev, docId];
    });
  };

  // Clear multi-doc selection
  const handleClearSelection = () => {
    setSelectedDocIds([]);
  };

  // Analyze 2 to 5 selected documents together
  const handleAnalyzeSelected = async () => {
    if (selectedDocIds.length < 2) return;
    if (selectedDocIds.length > 5) {
      setErrorMsg('A maximum of 5 documents can be analyzed together.');
      return;
    }
    setIsAnalyzingSelected(true);
    setAnalyzeStage('Triggering pairwise reasoning engine...');
    setErrorMsg(null);
    try {
      // 1. Trigger pairwise reasoning engine
      setAnalyzeStage('Extracting facts from selected documents...');
      await api.analyzeSelected(selectedDocIds);
      setFocusedDocIds([...selectedDocIds]);

      setAnalyzeStage('Comparing facts & building relationships...');
      // 2. Fetch facts, relationships, and the N-way consensus matrix simultaneously
      const [docs, storedFacts, storedRels, consensusRes] = await Promise.all([
        api.getDocuments(),
        api.getFacts(null, selectedDocIds),
        api.getRelationships(null, selectedDocIds),
        api.getConsensusMatrix(selectedDocIds).catch((err) => {
          console.warn('Failed to compute consensus matrix:', err);
          return null;
        }),
      ]);
      setDocuments(deduplicateDocs(docs));
      setFacts(storedFacts);
      setRelationships(storedRels);
      setConsensusData(consensusRes);

      // Default to the Multi-File Consensus Matrix tab so user immediately sees singular points compared side-by-side
      setActiveTab('CONSENSUS');
      setRelFilter('ALL');
      setSearchQuery('');

      // Auto-scroll to results stage when not in full-screen / narrow viewports
      setTimeout(() => {
        const stageEl = document.getElementById('main-stage') || document.querySelector('.main-content');
        if (stageEl && window.innerWidth < 1024) {
          stageEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
      }, 120);
    } catch (err) {
      setErrorMsg(err.message);
    } finally {
      setIsAnalyzingSelected(false);
      setAnalyzeStage('');
    }
  };

  // Clear joint focus filter
  const handleClearFocus = async () => {
    setFocusedDocIds(null);
    setConsensusData(null);
    setActiveTab('RELATIONSHIPS');
    setRelFilter('ALL');
    setSearchQuery('');
    try {
      const [docs, storedFacts, storedRels] = await Promise.all([
        api.getDocuments(),
        api.getFacts(selectedDocId),
        api.getRelationships(),
      ]);
      setDocuments(deduplicateDocs(docs));
      setFacts(storedFacts);
      setRelationships(storedRels);
    } catch (err) {
      console.error('Error clearing focus:', err);
    }
  };

  // Delete a document
  const handleDeleteDocument = async (docId, filename) => {
    if (!window.confirm(`Are you sure you want to delete "${filename}"? All associated extracted facts and relationships will be removed.`)) {
      return;
    }

    setDeletingDocId(docId);
    setErrorMsg(null);
    try {
      await api.deleteDocument(docId);

      if (selectedDocId === docId) {
        setSelectedDocId(null);
      }
      setSelectedDocIds((prev) => prev.filter((id) => id !== docId));

      let newFocused = focusedDocIds;
      if (focusedDocIds && focusedDocIds.includes(docId)) {
        const remaining = focusedDocIds.filter((id) => id !== docId);
        newFocused = remaining.length >= 2 ? remaining : null;
        setFocusedDocIds(newFocused);
      }

      let newConsensus = null;
      if (newFocused && newFocused.length >= 2) {
        newConsensus = await api.getConsensusMatrix(newFocused).catch(() => null);
      }
      setConsensusData(newConsensus);
      if (!newFocused && activeTab === 'CONSENSUS') {
        setActiveTab('RELATIONSHIPS');
      }

      const [docs, storedFacts, storedRels] = await Promise.all([
        api.getDocuments(),
        api.getFacts(selectedDocId === docId ? null : selectedDocId, newFocused),
        api.getRelationships(null, newFocused),
      ]);
      setDocuments(deduplicateDocs(docs));
      setFacts(storedFacts);
      setRelationships(storedRels);
    } catch (err) {
      setErrorMsg(err.message);
    } finally {
      setDeletingDocId(null);
    }
  };

  // Clear entire database
  const handleClearAll = async () => {
    if (!window.confirm('Reset all documents, facts, and relationships?')) return;
    setIsClearing(true);
    try {
      await api.clearAll();
      setSelectedDocId(null);
      setSelectedDocIds([]);
      setFocusedDocIds(null);
      setConsensusData(null);
      setActiveTab('RELATIONSHIPS');
      setDocuments([]);
      setFacts([]);
      setRelationships([]);
    } catch (err) {
      setErrorMsg(err.message);
    } finally {
      setIsClearing(false);
    }
  };

  // Select all processed documents (up to 5)
  const handleSelectAll = () => {
    const processedIds = documents
      .filter((d) => d.processing_status === 'completed' && d.extracted_facts_count > 0)
      .map((d) => d.id)
      .slice(0, 5);
    setSelectedDocIds(processedIds);
  };

  // Counts for filter pills
  const relCounts = {
    ALL: relationships.length,
    CORROBORATES: relationships.filter((r) => r.type === 'CORROBORATES').length,
    CONTRADICTS: relationships.filter((r) => r.type === 'CONTRADICTS').length,
    CONTEXTUALIZES: relationships.filter((r) => r.type === 'CONTEXTUALIZES').length,
    UNCERTAIN: relationships.filter((r) => r.type === 'UNCERTAIN').length,
  };

  return (
    <div className="app-container">
      {/* Top Header */}
      <Header
        theme={theme}
        toggleTheme={handleToggleTheme}
        onClearAll={handleClearAll}
        isClearing={isClearing}
        isSidebarOpen={isSidebarOpen}
        toggleSidebar={() => setIsSidebarOpen((prev) => !prev)}
      />

      {/* Stats Overview Bar */}
      <div className="stats-bar" id="knowledge-stats-bar">
        <div className="stats-bar-item">
          <FileText size={14} className="stats-bar-icon" />
          <span className="stats-bar-value">{documents.length}</span>
          <span className="stats-bar-label">Documents</span>
        </div>
        <div className="stats-bar-divider" />
        <div className="stats-bar-item">
          <Database size={14} className="stats-bar-icon" />
          <span className="stats-bar-value">{facts.length}</span>
          <span className="stats-bar-label">Facts Extracted</span>
        </div>
        <div className="stats-bar-divider" />
        <div className="stats-bar-item">
          <Link2 size={14} className="stats-bar-icon" />
          <span className="stats-bar-value">{relationships.length}</span>
          <span className="stats-bar-label">Relationships</span>
        </div>
        {(isUploading || isProcessing || isAnalyzingSelected) && (
          <>
            <div className="stats-bar-divider" />
            <div className="stats-bar-item stats-bar-processing">
              <RefreshCw size={13} className="animate-spin" />
              <span className="stats-bar-processing-label">
                {isUploading ? uploadStage || 'Uploading...' : isProcessing ? processingStage || 'Processing...' : analyzeStage || 'Analyzing...'}
              </span>
            </div>
          </>
        )}
      </div>

      {/* Error alert if any */}
      {errorMsg && (
        <div style={{ background: 'var(--color-contradict-bg)', borderBottom: '1px solid var(--color-contradict-border)', padding: '0.65rem 1.5rem', color: 'var(--color-contradict)', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <AlertCircle size={15} />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Dashboard 2-Column Grid */}
      <div className={`dashboard-grid ${!isSidebarOpen ? 'sidebar-collapsed' : ''}`}>
        {/* Left Sidebar: Documents */}
        <DocumentSidebar
          documents={documents}
          onUpload={handleUpload}
          isUploading={isUploading}
          onProcessDocument={handleProcessDocument}
          onProcessAll={handleProcessAll}
          isProcessing={isProcessing}
          selectedDocId={selectedDocId}
          onSelectDoc={(id) => {
            setSelectedDocId(id);
            api.getFacts(id, focusedDocIds).then(setFacts);
          }}
          selectedDocIds={selectedDocIds}
          onToggleSelectDoc={handleToggleSelectDoc}
          onAnalyzeSelected={handleAnalyzeSelected}
          onClearSelection={handleClearSelection}
          onSelectAll={handleSelectAll}
          isAnalyzingSelected={isAnalyzingSelected}
          onDeleteDocument={handleDeleteDocument}
          deletingDocId={deletingDocId}
          isOpen={isSidebarOpen}
          onToggleSidebar={() => setIsSidebarOpen(false)}
        />

        {/* Center Main Stage */}
        <main className="main-content" id="main-stage">
          {!isSidebarOpen && (
            <button
              id="reopen-sidebar-btn"
              className="btn btn-outline btn-sm sidebar-reopen-btn"
              onClick={() => setIsSidebarOpen(true)}
              title="Open Documents Sidebar"
            >
              <PanelLeftOpen size={14} />
              <span>Show Documents ({documents.length})</span>
            </button>
          )}
          {/* Joint Multi-File Analysis Banner */}
          {focusedDocIds && focusedDocIds.length > 0 && (
            <div className="joint-analysis-banner" id="joint-analysis-banner">
              <div className="joint-analysis-info">
                <Sparkles size={20} className="joint-analysis-icon" />
                <div className="joint-analysis-text">
                  <div className="joint-analysis-title">
                    Joint Multi-File Analysis Active ({focusedDocIds.length} files)
                  </div>
                  <div className="joint-analysis-docs">
                    <span>Showing cross-document interactions between:</span>
                    {focusedDocIds.map((id) => {
                      const doc = documents.find((d) => d.id === id);
                      return (
                        <span key={id} className="joint-doc-tag">
                          {doc ? doc.filename : id}
                        </span>
                      );
                    })}
                  </div>
                </div>
              </div>

              <button
                id="show-all-docs-btn"
                className="btn btn-outline btn-sm"
                onClick={handleClearFocus}
              >
                Show All Documents
              </button>
            </div>
          )}

          {/* View Mode Tabs */}
          <div className="view-tabs">
            {/* QA & Verification Interface */}
            <button
              id="tab-qa"
              className={`view-tab ${activeTab === 'QA' ? 'active' : ''}`}
              onClick={() => setActiveTab('QA')}
            >
              <MessageSquare size={16} />
              Ask & Verify
            </button>

            {/* Required Reasoning Cases — always visible once relationships exist */}
            {relationships.length > 0 && (
              <button
                id="tab-cases"
                className={`view-tab ${activeTab === 'CASES' ? 'active' : ''}`}
                onClick={() => setActiveTab('CASES')}
              >
                <Sparkles size={16} />
                Required Cases
              </button>
            )}

            {focusedDocIds && focusedDocIds.length >= 2 && (
              <button
                id="tab-consensus"
                className={`view-tab ${activeTab === 'CONSENSUS' ? 'active' : ''}`}
                onClick={() => setActiveTab('CONSENSUS')}
              >
                <GitCompare size={16} />
                Multi-File Matrix ({consensusData?.total_points || 0} Points)
              </button>
            )}

            <button
              id="tab-relationships"
              className={`view-tab ${activeTab === 'RELATIONSHIPS' ? 'active' : ''}`}
              onClick={() => setActiveTab('RELATIONSHIPS')}
            >
              <GitCompare size={16} />
              {focusedDocIds && focusedDocIds.length >= 2
                ? `Pairwise Reasoning (${relationships.length})`
                : `Cross-Document Reasoning (${relationships.length})`}
            </button>

            <button
              id="tab-facts"
              className={`view-tab ${activeTab === 'FACTS' ? 'active' : ''}`}
              onClick={() => setActiveTab('FACTS')}
            >
              <Layers size={16} />
              Extracted Facts & Provenance ({facts.length})
            </button>
          </div>

          {/* Filter & Search Bar (Only shown for Relationships and Facts tabs) */}
          {activeTab !== 'CONSENSUS' && activeTab !== 'QA' && (
            <div className="filter-bar">
              <div className="search-input-wrapper">
                <Search size={15} className="search-icon" />
                <input
                  id="search-facts-input"
                  type="text"
                  placeholder={activeTab === 'RELATIONSHIPS' ? "Search entities, values, or documents..." : "Search subject, predicate, or quote..."}
                  className="search-input"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>

              {activeTab === 'RELATIONSHIPS' && (
                <div className="filter-pills">
                  <button
                    className={`filter-pill ${relFilter === 'ALL' ? 'active' : ''}`}
                    onClick={() => setRelFilter('ALL')}
                  >
                    All ({relCounts.ALL})
                  </button>
                  <button
                    className={`filter-pill ${relFilter === 'CORROBORATES' ? 'active' : ''}`}
                    onClick={() => setRelFilter('CORROBORATES')}
                  >
                    Corroborates ({relCounts.CORROBORATES})
                  </button>
                  <button
                    className={`filter-pill ${relFilter === 'CONTRADICTS' ? 'active' : ''}`}
                    onClick={() => setRelFilter('CONTRADICTS')}
                  >
                    Contradictions ({relCounts.CONTRADICTS})
                  </button>
                  <button
                    className={`filter-pill ${relFilter === 'CONTEXTUALIZES' ? 'active' : ''}`}
                    onClick={() => setRelFilter('CONTEXTUALIZES')}
                  >
                    Contextualized ({relCounts.CONTEXTUALIZES})
                  </button>
                  <button
                    className={`filter-pill ${relFilter === 'UNCERTAIN' ? 'active' : ''}`}
                    onClick={() => setRelFilter('UNCERTAIN')}
                  >
                    Uncertain ({relCounts.UNCERTAIN})
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Tab Views */}
          {activeTab === 'QA' ? (
            <QAInterface
              documents={documents}
              selectedDocIds={selectedDocIds}
              focusedDocIds={focusedDocIds}
              onOpenComparisonModal={(rel) => setSelectedRelationship(rel)}
            />
          ) : activeTab === 'CASES' ? (
            <ReasoningCasesPanel
              relationships={relationships}
              onInspect={(rel) => setSelectedRelationship(rel)}
            />
          ) : activeTab === 'CONSENSUS' ? (
            <MultiDocumentMatrix
              consensusData={consensusData}
              isLoading={isAnalyzingSelected}
              onRefresh={() => {
                if (focusedDocIds && focusedDocIds.length >= 2) {
                  api.getConsensusMatrix(focusedDocIds).then(setConsensusData);
                }
              }}
            />
          ) : activeTab === 'RELATIONSHIPS' ? (
            <RelationshipMatrix
              relationships={relationships}
              onSelectRelationship={(rel) => setSelectedRelationship(rel)}
              activeFilter={relFilter}
              searchQuery={searchQuery}
            />
          ) : (
            <FactExplorer
              facts={facts}
              searchQuery={searchQuery}
              onSelectFact={(fact) => {
                // Find matching relationship if any
                const match = relationships.find(
                  (r) => r.fact_a_id === fact.id || r.fact_b_id === fact.id
                );
                if (match) setSelectedRelationship(match);
              }}
            />
          )}
        </main>
      </div>

      {/* Side-by-Side Comparison / Evidence Inspection Modal */}
      {selectedRelationship && (
        <ComparisonModal
          relationship={selectedRelationship}
          onClose={() => setSelectedRelationship(null)}
        />
      )}
    </div>
  );
}
