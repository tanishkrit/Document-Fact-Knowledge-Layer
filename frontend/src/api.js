const API_BASE_URL = 'http://localhost:8000/api';

export const api = {
  // Document endpoints
  async getDocuments() {
    const res = await fetch(`${API_BASE_URL}/documents`);
    if (!res.ok) throw new Error('Failed to fetch documents');
    return res.json();
  },

  async getDocument(id) {
    const res = await fetch(`${API_BASE_URL}/documents/${id}`);
    if (!res.ok) throw new Error(`Failed to fetch document ${id}`);
    return res.json();
  },

  async uploadDocuments(fileList) {
    const formData = new FormData();
    for (const file of fileList) {
      formData.append('files', file);
    }
    const res = await fetch(`${API_BASE_URL}/documents`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Upload failed' }));
      throw new Error(err.detail || 'Upload failed');
    }
    return res.json();
  },

  async deleteDocument(id) {
    const res = await fetch(`${API_BASE_URL}/documents/${id}`, {
      method: 'DELETE',
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to delete document' }));
      throw new Error(err.detail || 'Failed to delete document');
    }
    return res.json();
  },

  async processDocument(id) {
    const res = await fetch(`${API_BASE_URL}/documents/${id}/process`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error(`Failed to process document ${id}`);
    return res.json();
  },

  async processAll() {
    const res = await fetch(`${API_BASE_URL}/process-all`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error('Failed to process all documents');
    return res.json();
  },

  async analyzeSelected(documentIds) {
    const res = await fetch(`${API_BASE_URL}/documents/analyze-selected`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ document_ids: documentIds }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to analyze selected documents' }));
      throw new Error(err.detail || 'Failed to analyze selected documents');
    }
    return res.json();
  },

  // Facts endpoints
  async getFacts(documentId = null, documentIds = null) {
    const params = new URLSearchParams();
    if (documentId) params.append('document_id', documentId);
    if (documentIds && documentIds.length > 0) {
      params.append('document_ids', documentIds.join(','));
    }
    const queryString = params.toString();
    const url = queryString ? `${API_BASE_URL}/facts?${queryString}` : `${API_BASE_URL}/facts`;
    const res = await fetch(url);
    if (!res.ok) throw new Error('Failed to fetch facts');
    return res.json();
  },

  async getFact(id) {
    const res = await fetch(`${API_BASE_URL}/facts/${id}`);
    if (!res.ok) throw new Error(`Failed to fetch fact ${id}`);
    return res.json();
  },

  // Relationships endpoints
  async getRelationships(type = null, documentIds = null) {
    const params = new URLSearchParams();
    if (type && type !== 'ALL') params.append('type', type);
    if (documentIds && documentIds.length > 0) {
      params.append('document_ids', documentIds.join(','));
    }
    const queryString = params.toString();
    const url = queryString ? `${API_BASE_URL}/relationships?${queryString}` : `${API_BASE_URL}/relationships`;
    const res = await fetch(url);
    if (!res.ok) throw new Error('Failed to fetch relationships');
    return res.json();
  },

  async getRelationship(id) {
    const res = await fetch(`${API_BASE_URL}/relationships/${id}`);
    if (!res.ok) throw new Error(`Failed to fetch relationship ${id}`);
    return res.json();
  },

  // Consensus Matrix for 2 to 5 files
  async getConsensusMatrix(documentIds) {
    const res = await fetch(`${API_BASE_URL}/consensus/matrix`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ document_ids: documentIds }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to fetch consensus matrix' }));
      throw new Error(err.detail || 'Failed to fetch consensus matrix');
    }
    return res.json();
  },

  // Demo Suite endpoints
  async getDemoCases() {
    const res = await fetch(`${API_BASE_URL}/demo/cases`);
    if (!res.ok) throw new Error('Failed to fetch demo cases');
    return res.json();
  },

  async loadDemoCase(caseId) {
    const res = await fetch(`${API_BASE_URL}/demo/load/${caseId}`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error(`Failed to load demo case ${caseId}`);
    return res.json();
  },

  async clearAll() {
    const res = await fetch(`${API_BASE_URL}/clear`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error('Failed to clear database');
    return res.json();
  },

  // QA & Multi-Agent Verification
  async askQuestion(question, documentIds = null, maxPassages = 8) {
    const res = await fetch(`${API_BASE_URL}/qa/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question,
        document_ids: documentIds && documentIds.length > 0 ? documentIds : null,
        max_passages: maxPassages,
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to process question' }));
      throw new Error(err.detail || 'Failed to process question');
    }
    return res.json();
  },

  async getSampleQuestions() {
    const res = await fetch(`${API_BASE_URL}/qa/sample-questions`);
    if (!res.ok) throw new Error('Failed to fetch sample questions');
    return res.json();
  }
};
