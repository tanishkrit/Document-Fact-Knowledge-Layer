import React, { useRef, useState } from 'react';
import {
  Upload, FileText, CheckCircle2, Clock, RefreshCw,
  Trash2, CheckSquare, Square, Sparkles, X, GitCompare, PanelLeftClose, ListChecks
} from 'lucide-react';

export default function DocumentSidebar({
  documents = [],
  onUpload,
  isUploading,
  onProcessDocument,
  onProcessAll,
  isProcessing,
  selectedDocId,
  onSelectDoc,
  selectedDocIds = [],
  onToggleSelectDoc,
  onAnalyzeSelected,
  onClearSelection,
  onSelectAll,
  isAnalyzingSelected,
  onDeleteDocument,
  deletingDocId,
  isOpen = true,
  onToggleSidebar
}) {
  const fileInputRef = useRef(null);
  const [isDragOver, setIsDragOver] = useState(false);

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      onUpload(e.dataTransfer.files);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      onUpload(e.target.files);
    }
  };

  const hasUnprocessed = documents.some((d) => d.processing_status !== 'completed' || d.extracted_facts_count === 0);
  const selectedCount = selectedDocIds.length;

  return (
    <aside className={`documents-sidebar ${!isOpen ? 'collapsed' : ''}`} id="documents-sidebar">
      <div className="section-header">
        <span className="section-title">
          <FileText size={15} />
          Documents ({documents.length})
        </span>

        <div className="section-header-actions" style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
          {hasUnprocessed && documents.length > 0 && (
            <button
              id="process-all-btn"
              className="btn btn-primary btn-sm"
              onClick={onProcessAll}
              disabled={isProcessing}
            >
              <RefreshCw size={12} className={isProcessing ? 'animate-spin' : ''} />
              {isProcessing ? 'Processing...' : 'Process All'}
            </button>
          )}

          {onToggleSidebar && (
            <button
              type="button"
              className="btn btn-ghost btn-sm sidebar-collapse-trigger"
              onClick={onToggleSidebar}
              title="Collapse sidebar"
            >
              <PanelLeftClose size={15} />
            </button>
          )}
        </div>
      </div>

      {/* Upload Dropzone */}
      <div
        id="pdf-dropzone"
        className={`dropzone ${isDragOver ? 'dragover' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileChange}
          accept="application/pdf"
          multiple
          style={{ display: 'none' }}
        />
        <Upload size={20} className="dropzone-icon" />
        <div className="dropzone-title">
          {isUploading ? 'Uploading & Indexing...' : 'Upload PDF Documents'}
        </div>
        <div className="dropzone-subtitle">Drag & drop or click to browse</div>
      </div>

      {/* Multi-Selection Action Toolbar */}
      {selectedCount > 0 ? (
        <div className="multi-select-bar" id="multi-select-bar">
          <div className="multi-select-info">
            <GitCompare size={14} className="multi-select-icon" />
            <span>
              <strong>{selectedCount}</strong>/5 {selectedCount === 1 ? 'file' : 'files'} selected
            </span>
          </div>

          <div className="multi-select-actions">
            <button
              id="analyze-selected-btn"
              className="btn btn-primary btn-sm multi-analyze-btn"
              onClick={onAnalyzeSelected}
              disabled={selectedCount < 2 || selectedCount > 5 || isAnalyzingSelected}
              title={
                selectedCount < 2
                  ? 'Select at least 2 files to analyze together'
                  : selectedCount > 5
                  ? 'Maximum 5 files can be analyzed together'
                  : 'Run joint multi-document comparison across selected files'
              }
            >
              <Sparkles size={13} className={isAnalyzingSelected ? 'animate-spin' : ''} />
              {isAnalyzingSelected ? 'Analyzing...' : `Analyze (${selectedCount})`}
            </button>

            <button
              className="btn btn-ghost btn-sm"
              onClick={onClearSelection}
              title="Clear selection"
            >
              <X size={13} />
            </button>
          </div>
        </div>
      ) : (
        documents.length >= 2 && (
          <div className="multi-select-hint">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.5rem' }}>
              <span>Select 2–5 files to compare together</span>
              {onSelectAll && documents.filter(d => d.processing_status === 'completed').length >= 2 && (
                <button
                  className="btn btn-ghost btn-sm"
                  style={{ fontSize: '0.72rem', padding: '0.15rem 0.45rem' }}
                  onClick={onSelectAll}
                  title="Select all processed documents"
                >
                  <ListChecks size={12} /> Select all
                </button>
              )}
            </div>
          </div>
        )
      )}

      {/* Document List */}
      <div className="doc-list">
        {documents.length === 0 ? (
          <div className="sidebar-empty-state">
            <p>No documents uploaded yet.</p>
            <span>Upload 2 or more PDF documents to extract facts and discover cross-document relationships.</span>
          </div>
        ) : (
          documents.map((doc) => {
            const isSingleSelected = selectedDocId === doc.id;
            const isMultiSelected = selectedDocIds.includes(doc.id);
            const isDeleting = deletingDocId === doc.id;

            return (
              <div
                key={doc.id}
                id={`doc-card-${doc.id}`}
                className={`doc-card ${isMultiSelected ? 'selected-multi' : ''} ${isSingleSelected ? 'selected-single' : ''}`}
                style={{
                  opacity: isDeleting ? 0.4 : 1,
                }}
                onClick={() => onSelectDoc(isSingleSelected ? null : doc.id)}
              >
                <div className="doc-card-top">
                  <div className="doc-card-left">
                    <button
                      type="button"
                      className={`doc-checkbox-btn ${isMultiSelected ? 'checked' : ''}`}
                      disabled={selectedCount >= 5 && !isMultiSelected}
                      title={
                        isMultiSelected
                          ? 'Deselect from joint comparison'
                          : selectedCount >= 5
                          ? 'Maximum 5 files can be selected simultaneously'
                          : 'Select for joint comparison'
                      }
                      onClick={(e) => {
                        e.stopPropagation();
                        onToggleSelectDoc(doc.id);
                      }}
                    >
                      {isMultiSelected ? (
                        <CheckSquare size={16} />
                      ) : (
                        <Square size={16} />
                      )}
                    </button>
                    <span className="doc-filename" title={doc.filename}>
                      {doc.filename}
                    </span>
                  </div>

                  <div className="doc-card-actions">
                    {doc.processing_status === 'completed' && doc.extracted_facts_count > 0 ? (
                      <span className="badge badge-corroborates" style={{ fontSize: '0.65rem' }}>
                        <CheckCircle2 size={11} /> Ready
                      </span>
                    ) : doc.processing_status === 'processing' ? (
                      <span className="badge badge-contextualizes" style={{ fontSize: '0.65rem' }}>
                        <Clock size={11} className="animate-spin" /> Processing
                      </span>
                    ) : (
                      <button
                        className="btn btn-outline btn-sm"
                        style={{ padding: '0.15rem 0.4rem', fontSize: '0.7rem' }}
                        onClick={(e) => {
                          e.stopPropagation();
                          onProcessDocument(doc.id);
                        }}
                        disabled={isProcessing}
                      >
                        Extract
                      </button>
                    )}

                    {/* Delete document button */}
                    <button
                      type="button"
                      className="btn-icon-danger"
                      title={`Delete "${doc.filename}"`}
                      onClick={(e) => {
                        e.stopPropagation();
                        onDeleteDocument(doc.id, doc.filename);
                      }}
                      disabled={isDeleting}
                    >
                      <Trash2 size={13} className={isDeleting ? 'animate-spin' : ''} />
                    </button>
                  </div>
                </div>

                <div className="doc-meta">
                  <span>{doc.page_count} {doc.page_count === 1 ? 'page' : 'pages'}</span>
                  <span>•</span>
                  <span>{doc.extracted_facts_count} facts extracted</span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </aside>
  );
}
