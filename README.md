# TruthGuard: Fact Knowledge Layer

> **Evidence-First Multi-Document Intelligence & Verification Engine**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB.svg?logo=react&logoColor=black)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-5-646CFF.svg?logo=vite&logoColor=white)](https://vitejs.dev/)
[![SQLite](https://img.shields.io/badge/Database-SQLite-003B57.svg?logo=sqlite&logoColor=white)](https://www.sqlite.org/)

An evidence-first, document-agnostic **Fact Knowledge Layer** built with **Python (FastAPI)** and **React (Vite)**. 

The system ingests PDF documents, extracts meaningful numerical and semantic facts, preserves exact source evidence and provenance, normalizes values and contexts, and autonomously determines cross-document relationships.

### Core Capabilities

- **Corroborating Facts**: Identifies facts across documents that validate each other even when expressed differently.
- **Contradiction Detection**: Flags conflicting claims with comparable scope and context.
- **Contextual Differentiation**: Disentangles discrepancies arising from temporal changes, scope differences, geography, or reporting units.
- **Uncertainty & Limitation Tracking**: Refrains from guessing when context is insufficient, exposing the uncertainty with full provenance.

Every single extracted claim and relationship remains traceable back to the source page and verbatim textual snippet.

---

## Features

- **Interactive Web Interface**: Clean, responsive UI with multi-document matrix views and comparison modals.
- **Automated PDF Text Extraction**: Page-aware document parsing using PyMuPDF.
- **Structured Fact Extraction**: Subjects, predicates, values, units, contexts, documents, and pages extracted deterministically.
- **Source Evidence & Provenance**: Verbatim source snippet retained for every extracted fact for one-click verification.
- **Deterministic Value Normalization**: Standardizes currencies, scales (e.g., Crores vs. Millions), date/time periods, and units.
- **Cross-Document Fact Matching**: Entity & predicate resolution across distinct documents.
- **Contradiction & Corroboration Engine**: Automated conflict & corroboration scoring.
- **Context-Aware Reconciliation**: Reconciles apparent conflicts via temporal and scope context.
- **Q&A Verification Pipeline**: Retriever, synthesizer, precedence resolver, and adversarial critic for evidence-backed question answering.
- **Document Deduplication**: SHA-256 content hashing prevents redundant ingestion.
- **SQLite Persistence**: Local, lightweight relational storage for facts, relationships, and evidence.
- **RESTful API**: Fast and modular FastAPI endpoints.

---

## Tech Stack

### Backend
- **Python 3.10+**
- **FastAPI** — High-performance asynchronous REST API
- **Uvicorn** — ASGI web server
- **PyMuPDF (`fitz`)** — PDF document processing & text extraction
- **SQLite** — Relational storage for documents, facts, and relationships

### Frontend
- **React 18** — Component-driven interactive user interface
- **Vite 5** — Modern frontend build tooling
- **Vanilla CSS** — Custom responsive styling with glassmorphism and data visualization

### Development & Tools
- **Git & GitHub** — Version control and repository hosting
- **Pytest** — Backend unit and integration test suite

---

## Setup and Run Instructions

### Prerequisites
Ensure the following tools are installed on your machine:
- **Python 3.10+**
- **Node.js 18+** & **npm**
- **Git**

---

### 1. Clone the Repository

```bash
git clone https://github.com/tanishkrit/Virtusa---Jatayu.git
cd Virtusa---Jatayu
```

---

### 2. Start the Backend

Open a terminal in the project root:

```bash
cd backend
python -m pip install -r requirements.txt
python main.py
```

The backend API will start and be accessible at:
```text
http://localhost:8000
```
Interactive OpenAPI documentation is available at: `http://localhost:8000/docs`

---

### 3. Start the Frontend

Open a second terminal in the project root:

```bash
cd frontend
npm install
npm run dev
```

The frontend application will start and be accessible at:
```text
http://localhost:5173
```

Open `http://localhost:5173` in your browser.

---

### 4. Process PDFs & Run Verifications

1. Upload one or more PDF files via the web UI (pre-packaged sample documents are available in `data/demos/`).
2. The processing pipeline runs extraction, normalization, and relationship reasoning automatically.
3. Review:
   - **Extracted Facts**: Structured values, units, and metrics.
   - **Provenance & Evidence**: Page number and verbatim text highlight.
   - **Relationship Matrix**: Pairwise comparisons identifying corroborations, contradictions, and contextual variances.
   - **Interactive Q&A**: Ask multi-document verification questions and receive evidence-backed answers.

---

## Architecture

```text
       PDF Documents
             |
             v
+--------------------------+
|       PDF Processor      |
|         (PyMuPDF)        |
+--------------------------+
             |
             v
+--------------------------+
|      Fact Extraction     |
|   (Regex, Rules, Layout) |
+--------------------------+
             |
             v
+--------------------------+
|    Fact Validation &     |
|       Normalization      |
+--------------------------+
             |
             v
+--------------------------+
|          SQLite          |
|    (Facts + Evidence)    |
+--------------------------+
             |
             v
+--------------------------+
|      Fact Matching &     |
|    Relationship Engine   |
+--------------------------+
             |
     +-------+--------+
     |                |                |
     v                v                v
Corroboration   Contradiction   Contextualization
     |                |                |
     +-------+--------+
             |
             v
+--------------------------+
|    Q&A & Critic Pipeline |
|  (Retriever/Synthesizer) |
+--------------------------+
             |
             v
        FastAPI API
             |
             v
         React UI
```

---

## Pipeline Approach

### 1. Document Processing
Uploaded PDFs are processed page-by-page using PyMuPDF. Text is extracted while retaining page indices and bounding coordinates, ensuring facts remain tied to exact visual and textual provenance.

### 2. Fact Extraction
The extraction layer identifies key numerical and semantic business metrics (e.g., Revenue, Headcount, Shipments, Operational Centers). Each fact captures:
- `Subject` & `Predicate`
- `Value` & `Normalized Value`
- `Unit` (e.g., Cr, Million, %)
- `Context` (Time period, geography, segment)
- `Source Document` & `Page Number`
- `Verbatim Evidence Snippet`

Filtering heuristics eliminate false positives such as table headers, CIN numbers, pin codes, and address lines.

### 3. Evidence and Provenance
Rather than detached numbers, provenance is stored as an immutable attribute of each fact. Every output is directly verifiable by human auditors through the source text viewer.

### 4. Value & Context Normalization
Metrics expressed across varying formats are normalized:
- **Scales**: Standardizes Indian numerical systems (Lakhs, Crores) and Western scales (Millions, Billions).
- **Currencies**: Converts ISO currency codes and symbols (₹, $, USD, INR).
- **Time/Scope**: Standardizes fiscal years (FY23, FY24) and quarter designations.

### 5. Cross-Document Reasoning
The relationship engine performs pairwise comparisons of candidate facts using:
- Metric compatibility and predicate similarity
- Normalized value proximity
- Temporal period and operational scope alignment
- Evidence confidence

Relationships are categorized into:
- **Corroboration**: Consistent facts reflecting the same metric and timeframe.
- **Contradiction**: Divergent values reported for the same metric, entity, and period without qualifying context.
- **Contextualization**: Different values explained by differing scopes (e.g., Global vs. India division) or reporting periods.
- **Uncertainty**: Ambiguous signals marked for human review.

---

## Required Demonstration Cases

The system specifically addresses the core real-world reasoning cases:

1. **Corroboration**: Identifies identical underlying metrics expressed across different documents or differing representations.
2. **Contradiction**: Flags genuine discrepancies in claims for the same entity and timeframe, providing side-by-side evidence inspection.
3. **Contextual Difference**: Accurately recognizes when numbers differ because one document describes a distinct quarter or regional segment rather than false conflict.
4. **Extraction / Reasoning Limitations**: Gracefully flags complex tables, ambiguous phrases, or unsupported statements, preserving human-in-the-loop auditability.

---

## Video Demo

📺 **[Watch the Demo Video on YouTube](https://youtu.be/AWUER__R0hc)**

The walkthrough demonstrates:
- End-to-end PDF ingestion and automated fact extraction
- Verbatim source evidence inspection
- Cross-document corroboration and contradiction detection
- Context-based difference resolution
- Q&A synthesis with adversarial critic verification

---

## Project Structure

```text
Virtusa---Jatayu/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── routes.py              # REST API endpoints
│   │   ├── db/
│   │   │   └── storage.py             # SQLite database manager
│   │   ├── models/
│   │   │   ├── schemas.py             # Data models for facts & relations
│   │   │   └── qa_schemas.py          # Q&A pipeline schemas
│   │   └── services/
│   │       ├── pdf_processor.py       # PyMuPDF text extractor
│   │       ├── fact_extractor.py      # Fact extraction engine
│   │       ├── normalizer.py          # Units & values normalization
│   │       ├── matcher.py             # Metric matching
│   │       ├── relationship_engine.py # Corroboration & contradiction logic
│   │       ├── consensus_engine.py    # Multi-source consensus resolver
│   │       └── qa/                    # Verification Q&A pipeline
│   │           ├── retriever.py
│   │           ├── synthesizer.py
│   │           ├── precedence.py
│   │           ├── critic.py
│   │           └── orchestrator.py
│   ├── tests/                         # Backend test suite
│   ├── main.py                        # FastAPI application entrypoint
│   └── requirements.txt               # Python dependencies
│
├── frontend/
│   ├── src/
│   │   ├── components/                # UI components (Explorer, Matrix, Q&A)
│   │   ├── App.jsx                    # Root application component
│   │   ├── App.css                    # Component styles
│   │   ├── index.css                  # Design system tokens & base styles
│   │   └── api.js                     # Backend API client
│   ├── package.json
│   └── vite.config.js
│
├── data/
│   └── demos/                         # Sample demonstration PDFs
│
├── goal.md                            # System specifications & requirements
├── package.json                       # Root scripts
├── README.md                          # Project documentation
└── .gitignore
```

---

## Additional Notes

- **Document-Agnostic**: Operates dynamically on arbitrary uploaded PDFs without hardcoded document assumptions.
- **Zero API Keys Required**: Fully functional offline without requiring external paid API subscriptions.
- **Auditability First**: Designed to prioritize transparency and provenance over black-box outputs.

---

## Links

- **GitHub Repository**: [https://github.com/tanishkrit/Virtusa---Jatayu](https://github.com/tanishkrit/Virtusa---Jatayu)
- **Demo Video**: [Watch on YouTube](https://youtu.be/AWUER__R0hc)