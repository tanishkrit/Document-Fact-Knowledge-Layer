# Fact Knowledge Layer: Evidence-First Document Intelligence

An evidence-first, document-agnostic Fact Knowledge Layer built with **Python (FastAPI)** and **React (Vite)**.

The system ingests PDF documents, extracts meaningful numerical and semantic facts, preserves their source evidence and provenance, normalizes values and contexts, and identifies relationships between facts across documents.

The system identifies:

- Corroborating facts
- Contradictions
- Contextual differences
- Uncertain or potentially unreliable relationships

The goal is not only to extract facts, but also to make every result traceable back to the original document evidence.

---

## Features

- PDF upload through the web UI
- Automatic PDF text extraction
- Structured fact extraction
- Page-level source provenance
- Original source text retained for every fact
- Deterministic value normalization
- Cross-document fact matching
- Corroboration detection
- Contradiction detection
- Context-aware reconciliation
- Evidence inspection for relationships
- Duplicate document detection using file hashing
- SQLite-based persistence
- REST API through FastAPI
- React-based interactive interface

---

## Tech Stack

### Backend

- Python
- FastAPI
- Uvicorn
- SQLite
- PyMuPDF

### Frontend

- React
- Vite
- JavaScript
- CSS

### Development

- Git
- GitHub
- AI-assisted development tools for implementation, debugging, testing, and documentation

---

## Setup and Run Instructions

### Prerequisites

Make sure the following are installed:

- Python 3.10+
- Node.js 18+
- npm
- Git

### 1. Clone the Repository

```bash
git clone https://github.com/kopalkhare2/SuperJoin-assignment.git
cd SuperJoin-assignment
```

### 2. Start the Backend

Open a terminal:

```bash
cd backend
python -m pip install -r requirements.txt
python main.py
```

The backend runs at:

```text
http://localhost:8000
```

### 3. Start the Frontend

Open another terminal:

```bash
cd frontend
npm install
npm run dev
```

The frontend runs at:

```text
http://localhost:5173
```

Open the frontend URL in a browser.

### 4. Process PDFs

Upload one or more PDF documents through the UI.

The system processes the documents through the extraction and reasoning pipeline and displays:

1. Extracted facts
2. Source documents
3. Page numbers
4. Original source evidence
5. Cross-document relationships

The application is designed to accept additional PDFs rather than relying on the filenames or facts of the starter dataset.

---

## Architecture

```text
PDF Documents
      |
      v
+------------------+
|  PDF Processor   |
|     PyMuPDF      |
+------------------+
      |
      v
+------------------+
| Fact Extraction  |
+------------------+
      |
      v
+----------------------+
| Fact Validation &    |
| Normalization        |
+----------------------+
      |
      v
+----------------------+
|       SQLite         |
| Facts + Evidence     |
+----------------------+
      |
      v
+----------------------+
| Fact Matching &      |
| Relationship Engine  |
+----------------------+
      |
      +----------------+----------------+
      |                |                |
      v                v                v
Corroboration    Contradiction    Contextualization
      |                |                |
      +----------------+----------------+
                       |
                       v
                  FastAPI API
                       |
                       v
                    React UI
```

---

## Approach

### 1. Document Processing

Each uploaded PDF is processed using PyMuPDF.

For every page, the system extracts text while retaining the page number. This allows extracted facts to remain connected to the exact location from which they originated.

### 2. Fact Extraction

The extraction layer identifies useful numerical and semantic claims from document text.

Each fact is represented using structured fields such as:

- Subject
- Predicate
- Value
- Unit
- Context
- Document
- Page
- Source evidence

The system also performs validation to reduce false positives caused by PDF layouts, tables, dates, CIN numbers, addresses, postal codes, and other numeric fragments that can resemble meaningful facts.

### 3. Evidence and Provenance

A core design decision was to treat provenance as part of the fact itself.

Instead of storing only:

```text
Revenue = ₹8,142 Cr
```

the system retains the document, page, and original source text associated with the fact.

This makes extracted information inspectable and allows users to verify the system's output against the original document.

### 4. Normalization

Documents frequently express the same information using different units or formats.

The system therefore normalizes values where possible, including:

- Numeric scales
- Units
- Currency representations
- Dates
- Context and scope

This allows relationships to be detected even when the original representations differ.

### 5. Cross-Document Reasoning

Candidate facts are compared across documents using their semantic dimensions and contextual information.

The relationship engine considers:

- Metric / predicate compatibility
- Value similarity
- Units and scale
- Time period
- Scope
- Context
- Evidence quality

Relationships are classified as:

**Corroboration**

Two facts describe the same underlying information and are consistent after normalization.

**Contradiction**

Two comparable facts refer to the same context but contain materially different values.

**Contextualization**

Two values appear different but the difference can be explained by factors such as time period, scope, or units.

**Uncertainty**

The system cannot confidently determine the relationship and avoids presenting an uncertain result as a definitive conclusion.

---

## Required Demonstration Cases

The implementation demonstrates the four cases requested in the assignment.

### 1. Corroboration

The system identifies information that is consistent across documents even when the values are expressed differently.

### 2. Contradiction

The system flags potentially conflicting facts when they appear to refer to the same metric and context.

The UI allows the user to inspect the underlying evidence before deciding whether the difference represents a genuine contradiction.

### 3. Contextual Difference

The system distinguishes differences caused by context.

For example, two documents may report different customer counts because they describe different reporting periods. Instead of treating the values as automatically contradictory, the relationship engine considers the time context.

### 4. Extraction / Reasoning Failure

PDFs can contain complex tables, formatting, footnotes, and numbers that resemble facts.

During development, extraction errors were identified where numeric fragments or table values could be incorrectly interpreted as business facts.

Validation rules and predicate/context checks were added to reduce these errors.

The system also preserves the original evidence so that questionable results can be inspected rather than treated as unquestionable truth.

---

## Video Demo

### Demo Video

[Watch the demo video on YouTube](https://youtu.be/AWUER__R0hc)

The demo shows:

- PDF processing
- Fact extraction
- Source evidence and provenance
- Cross-document corroboration
- Context-based differences
- Contradiction detection
- Evidence inspection
- Handling of extraction/reasoning limitations
- Uploading additional PDF documents

---

## Limitations and Next Steps

### Current Limitations

- PDF extraction quality depends on document layout and text quality.
- Highly complex tables can still produce ambiguous extraction results.
- Semantic matching is currently based primarily on deterministic rules and normalized fact dimensions.
- Some relationships may require human verification when the available context is insufficient.
- The prototype is optimized for understandable behavior rather than large-scale production workloads.

### Next Steps

Potential improvements include:

- Better table-aware PDF extraction
- More advanced semantic similarity for fact matching
- Confidence calibration based on historical extraction quality
- Improved handling of long and complex PDFs
- Incremental document processing at larger scale
- More sophisticated temporal and scope reasoning
- Additional visualization of the fact relationship graph
- More extensive automated evaluation using unseen document sets

---

## Project Structure

```text
SuperJoin-assignment/
│
├── backend/
│   ├── main.py
│   ├── routes.py
│   ├── storage.py
│   ├── pdf_processor.py
│   ├── fact_extractor.py
│   ├── matcher.py
│   ├── relationship_engine.py
│   └── ...
│
├── frontend/
│   ├── src/
│   ├── package.json
│   └── ...
│
├── data/
│   └── demos/
│
├── goal.md
├── package.json
├── README.md
└── .gitignore
```

---

## Additional Notes

- The system is intentionally document-agnostic and does not depend on hard-coded facts from the starter PDFs.
- Uploaded documents are deduplicated using their content hash.
- Source evidence is retained alongside extracted facts to support verification.
- The implementation prioritizes explainability and traceability over treating every extracted value as automatically correct.
- The starter dataset consists of the three Delhivery documents provided with the assignment.
- No credentials or paid API keys are required to run the project.
- The project was developed and tested locally using the setup instructions above.

---

## Links

- **GitHub Repository:** https://github.com/kopalkhare2/SuperJoin-assignment
- **Demo Video:** https://youtu.be/AWUER__R0hc#   V i r t u s a - - - J a t a y u  
 