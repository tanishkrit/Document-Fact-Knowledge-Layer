# TruthGuard --- Evidence-First Document Verification

## 1. Project Goal

Build **TruthGuard**, an evidence-first document intelligence system
that extracts facts from multiple PDFs, preserves the source evidence
for every fact, and checks how claims relate across documents.

Unlike a basic document chatbot that retrieves passages and produces a
blended answer, TruthGuard must actively verify its draft answer. It
should identify corroborating claims, genuine contradictions, contextual
differences, outdated information, and unsupported statements. When the
available evidence cannot establish which claim is correct, the system
must disclose the uncertainty rather than guess.

The project combines the core **Fact Knowledge Layer** with a
question-answering workflow that uses a retriever, synthesizer, and
critic/adversary.

## 2. Core Questions

The system should help users answer:

-   What does each document claim?
-   Where, exactly, is each claim supported?
-   Which claims are corroborated by other documents?
-   Which claims genuinely conflict?
-   Can apparent conflicts be explained by time, geography, scope,
    units, or definitions?
-   Is one source newer or explicitly superseding another?
-   Which statements in a proposed answer are unsupported?
-   What evidence supports the final conclusion, and what remains
    uncertain?

## 3. Core Principles

1.  **Evidence before assertion:** Every extracted fact and material
    answer claim must link to source evidence.
2.  **Context before contradiction:** Different values are not
    contradictions until relevant context has been compared.
3.  **Provenance over blended answers:** Preserve each source's position
    and explain conflicts rather than silently merging them.
4.  **Deterministic where possible:** Use code for parsing,
    normalization, validation, dates, and unit conversions.
5.  **LLM where necessary:** Use language models for fact extraction,
    semantic matching, and nuanced interpretation.
6.  **Honest uncertainty:** If the evidence is insufficient or
    conflicting without a defensible resolution, say so.
7.  **Document-agnostic design:** Do not hard-code filenames, known
    entities, page numbers, predicates, or facts from demonstration
    PDFs.

## 4. Minimum Viable Product

### 4.1 PDF Ingestion

-   Allow users to upload multiple PDF documents.
-   Assign each document a stable ID and record its filename, upload
    time, page count, and processing status.
-   Extract text while preserving page boundaries and source locations
    where available.
-   Keep the original document associated with every extracted fact and
    evidence passage.
-   For the initial version, prioritize text-based PDFs. OCR for scanned
    documents can be a future extension.

### 4.2 Fact Extraction

Extract meaningful factual claims from document text without assuming a
fixed set of fields.

Represent each fact using a generic structure:

-   **Subject:** the entity or thing the claim concerns.
-   **Predicate:** the relationship or property being stated.
-   **Value/object:** the claimed value or statement.
-   **Context:** relevant time, geography, population, scope, and
    measurement definition.
-   **Qualification:** wording such as "approximately," "at least," or
    "estimated."
-   **Confidence:** the system's estimated confidence in extraction.
-   **Evidence:** document ID, page number, and the supporting source
    text.

Example:

``` json
{
  "subject": "Company X",
  "predicate": "revenue",
  "value": {
    "type": "number",
    "amount": 1200000000,
    "unit": "USD"
  },
  "context": {
    "time": "FY2024",
    "geography": "Global",
    "scope": null
  },
  "qualification": null,
  "confidence": 0.94,
  "evidence": {
    "document_id": "doc_001",
    "page": 12,
    "text": "The company generated revenue of $1.2 billion in FY2024."
  }
}
```

The schema may evolve, but it must remain flexible enough for unseen
document types.

### 4.3 Evidence and Provenance

Every extracted fact must preserve, at minimum:

-   Document ID
-   Page number
-   Exact supporting text

Where possible, also preserve text-block identifiers, character offsets,
and bounding boxes. Users should be able to navigate from a fact to the
document and passage that supports it.

A fact without traceable evidence must not be presented as verified.

### 4.4 Normalization and Context

Before comparing facts, normalize equivalent representations using
deterministic code wherever possible.

Examples:

-   `$1.2 billion` and `$1,200 million`
-   `5,000 employees` and `5K employees`
-   Equivalent dates, currencies, units, and numerical scales

Extract context that may affect whether two claims are comparable:

-   Time period or effective date
-   Geography
-   Population or organizational scope
-   Units and measurement definitions
-   Qualifications and estimates
-   Document version, publication date, and explicit supersession
    references

Missing context must remain unknown; the system must not invent it.

### 4.5 Related-Fact Matching

Find candidate facts that may describe the same claim using a
combination of:

-   Subject similarity
-   Predicate similarity
-   Semantic meaning
-   Context compatibility
-   Embedding-based retrieval

Avoid comparing every fact with every other fact as the corpus grows.
Matching should identify candidates for verification, not decide truth
on its own.

### 4.6 Relationship Classification

The initial relationship labels are:

-   **CORROBORATES:** compatible evidence supports the same underlying
    claim.
-   **CONTRADICTS:** claims are incompatible under sufficiently
    equivalent context.
-   **CONTEXTUALIZES:** an apparent difference is explained by different
    time, scope, geography, units, or definitions.
-   **RELATED:** claims are relevant to one another but do not establish
    one of the above relationships.
-   **UNCERTAIN:** evidence is insufficient to confidently classify the
    relationship.

Every classification must include a human-readable explanation and links
to the evidence on both sides.

## 5. TruthGuard Multi-Agent Verification

The minimum viable question-answering architecture has three logical
agents and a resolution step. These can initially be implemented as
separate functions or modules; a complex agent framework is not
required.

### 5.1 Retriever Agent

-   Accept a user's question.
-   Retrieve relevant passages and extracted facts from the document
    corpus using keyword search, embeddings, or both.
-   Return candidate evidence with document IDs, page numbers, and
    version/date metadata.
-   Prefer relevant evidence over large amounts of loosely related text.

### 5.2 Synthesizer Agent

-   Draft a candidate answer using only the retrieved evidence.
-   Attach source citations to material claims.
-   Distinguish direct evidence from inference.
-   Avoid filling gaps with unsupported knowledge.

### 5.3 Critic / Adversary Agent

Actively challenge the candidate answer instead of merely approving it.

It should check:

-   **Direct contradictions:** Do retrieved passages make incompatible
    claims?
-   **Staleness and supersession:** Is there a newer version or an
    explicit amendment that replaces an older rule?
-   **Context mismatches:** Are different dates, geographies,
    populations, units, or definitions being compared incorrectly?
-   **Unsupported claims:** Does the draft contain assertions not backed
    by the retrieved evidence?
-   **Citation validity:** Do the cited passages actually support the
    claims attached to them?
-   **Missing evidence:** Is the available corpus insufficient to answer
    confidently?

The critic should return identified issues, supporting passages, and a
reason for each issue. It must not invent a resolution simply to make
the answer sound decisive.

### 5.4 Resolution Step

When verification identifies a genuine conflict, TruthGuard must not
silently blend the claims or arbitrarily choose one.

It should do one of the following:

1.  **Resolve with evidence:** Prefer a source only when the corpus
    supports the decision---for example, an explicit amendment that
    supersedes an earlier policy.
2.  **Present both positions:** Explain each claim, its source,
    date/version, and supporting evidence.
3.  **Report unresolved uncertainty:** State that the available
    documents do not establish which claim should be trusted.

The final response should include the conclusion, relevant citations,
the conflict or verification findings, and any remaining uncertainty. If
a critic identifies a problem, the synthesizer may revise the answer and
the critic should re-check it, subject to a bounded number of review
rounds.

## 6. High-Level Architecture

``` text
PDF Upload
    |
    v
PDF Processor
(text extraction + page tracking)
    |
    v
Document / Page / Evidence Storage
    |
    v
Fact Extraction
    |
    v
Structured Fact Layer
(subject, predicate, value, context,
 qualification, confidence, evidence)
    |
    v
Normalization
    |
    v
Related-Fact Retrieval
    |
    v
Relationship Detection
(corroborates / contradicts /
 contextualizes / related / uncertain)
    |
    +------------------------------+
                                   |
User Question                      |
    |                              |
    v                              |
Retriever Agent -------------------+
    |
    v
Synthesizer Agent
    |
    v
Critic / Adversary Agent
    |
    v
Resolution Step
(resolve with evidence / show both
 positions / report uncertainty)
    |
    v
Answer with citations and reasoning
```

## 7. Suggested Technology Stack

Choose the simplest stack that supports a reliable end-to-end
demonstration.

-   **Language:** Python
-   **API:** FastAPI
-   **Validation and schemas:** Pydantic
-   **PDF processing:** PyMuPDF
-   **LLM:** a model/API suitable for structured extraction and
    reasoning
-   **Embeddings:** sentence-transformers or an embedding API
-   **Initial database:** SQLite
-   **Vector search:** a lightweight local index or Chroma/FAISS if
    needed
-   **Frontend:** Streamlit for a fast prototype, or React + Vite +
    Tailwind CSS for a separate frontend

The first version does not need every listed technology. Keep components
replaceable and avoid adding infrastructure before it is useful. If an
external model/API is used, document that the system requires network
access for those calls; do not claim full offline support unless it is
implemented and tested.

## 8. Initial Data Model

The core entities are:

### Document

-   `id`
-   `filename`
-   `uploaded_at`
-   `page_count`
-   `metadata`
-   `processing_status`

### Evidence

-   `id`
-   `document_id`
-   `page_number`
-   `text`
-   `location` (optional text offsets or bounding box)

### Fact

-   `id`
-   `subject`
-   `predicate`
-   `value`
-   `unit` (optional)
-   `context`
-   `qualification`
-   `confidence`
-   `evidence_id`
-   `embedding` (optional)

### Relationship

-   `id`
-   `fact_a`
-   `fact_b`
-   `type`
-   `confidence`
-   `reason`
-   `evidence_refs`

### Verification Run

-   `id`
-   `question`
-   `retrieved_evidence`
-   `candidate_answer`
-   `critic_findings`
-   `resolution`
-   `final_answer`
-   `citations`

Use Pydantic models to validate LLM outputs before storing or using
them.

## 9. Initial API

A small API is sufficient for the first version:

-   `POST /documents` --- upload a PDF.
-   `POST /documents/{document_id}/process` --- extract text and facts.
-   `GET /documents` --- list uploaded documents and processing status.
-   `GET /facts` --- return extracted facts and their evidence.
-   `GET /relationships` --- list detected cross-document relationships.
-   `GET /relationships/{relationship_id}` --- inspect both facts,
    evidence, classification, and reason.
-   `POST /questions` --- run retrieval, synthesis, critique, and
    resolution for a question.

The exact endpoint design may evolve. Keep responses structured and make
citations usable by the frontend.

## 10. User Interface

The UI should emphasize inspection and explainability rather than
looking like an ordinary chatbot.

Users should be able to:

1.  Upload multiple PDFs and see processing status.
2.  Browse extracted facts.
3.  Open a fact and inspect its source document, page, and evidence
    text.
4.  Filter relationships by type.
5.  Compare related facts side by side.
6.  Ask a question about the document corpus.
7.  Inspect the candidate answer's citations and the critic's findings.
8.  See how conflicts were resolved---or why they remain unresolved.

For every detected conflict, show the competing claims, source passages,
dates/versions, contextual comparison, classification, and explanation.

## 11. Required Demonstration Cases

The final demonstration must cover all four cases below.

### Case 1 --- Corroboration

Two documents express the same fact differently.

Show: - Both extracted facts - Their source evidence - Normalized
values - The `CORROBORATES` relationship - Why the claims are compatible

### Case 2 --- Genuine Contradiction

Two documents make incompatible claims under equivalent context.

Show: - Both claims and citations - Relevant context - The `CONTRADICTS`
relationship - The critic's finding - How the final answer presents the
conflict without hiding it

### Case 3 --- Apparent Contradiction

Two claims look inconsistent but differ in time, geography, population,
units, or definition.

Show: - Both claims and evidence - The contextual difference - The
`CONTEXTUALIZES` relationship - Why a direct contradiction would be
misleading

### Case 4 --- Verification Failure

At least one extraction or reasoning failure must be documented
honestly.

Explain: - What happened - Why the system failed - How the issue was
detected - What mitigation exists - What should be improved

## 12. Generalization Requirements

TruthGuard must not depend on:

-   Specific filenames or page numbers
-   Known companies or entities
-   Hard-coded facts, values, or predicates
-   Rules written only for the demonstration PDFs
-   Assumptions that all facts are numerical

The same pipeline should handle new PDFs containing previously unseen
subjects and fact types. If a relationship cannot be established from
the available evidence, return `UNCERTAIN` instead of forcing a label.

## 13. Quality and Evaluation

Evaluate the system on more than whether its final answer sounds
plausible.

Track, at minimum:

-   **Extraction quality:** Are claims represented accurately?
-   **Evidence fidelity:** Does the cited passage support the extracted
    fact?
-   **Relationship quality:** Are corroborations, contradictions, and
    contextual differences classified correctly?
-   **Citation coverage:** Are material answer claims supported by
    citations?
-   **Unsupported-claim rate:** Does the answer assert anything absent
    from the evidence?
-   **Uncertainty handling:** Does the system abstain when the corpus
    cannot justify a conclusion?
-   **Robustness:** Does it work on documents outside the initial
    examples?

Use a small, manually reviewed test set to record expected facts,
relationships, and acceptable answers. Report known limitations rather
than claiming perfect accuracy.

## 14. Performance and Incremental Processing

Correctness and traceability take priority over maximum speed in Version
1.

Design for future improvements such as: - Processing independent
pages/chunks concurrently - Embedding-based candidate retrieval rather
than exhaustive pairwise comparisons - Caching extracted text, validated
facts, normalized values, and embeddings - Incremental processing so a
newly uploaded document is compared with existing facts without
reprocessing everything - Background jobs for large documents

These optimizations should follow a reliable baseline implementation.

## 15. Initial Scope vs. Future Scope

### Version 1 --- Required

-   Multiple PDF uploads
-   Text extraction with page tracking
-   Generic fact extraction
-   Evidence and provenance storage
-   Context extraction and normalization
-   Related-fact retrieval
-   Relationship classification
-   Retriever, synthesizer, and critic workflow
-   Evidence-based resolution or explicit uncertainty
-   Answer citations and human-readable explanations
-   API and simple UI
-   Four demonstration cases, including a documented failure

### Future Extensions

-   OCR for scanned PDFs
-   More robust table extraction
-   Exact text highlighting in the PDF viewer
-   Multi-language documents
-   Advanced version history and temporal reasoning
-   Human review and correction
-   Confidence calibration
-   PostgreSQL + pgvector
-   Background processing and incremental ingestion
-   Knowledge graph visualization
-   More advanced agent orchestration

Implement these only after the core extraction, evidence, and
verification pipeline works reliably.

## 16. Definition of Done

TruthGuard is ready for its initial demonstration when a user can:

1.  Upload multiple PDFs.
2.  Process them into source-linked facts.
3.  Inspect a fact and trace it to its original page and evidence.
4.  View related facts across documents.
5.  See whether claims corroborate, contradict, contextualize, or remain
    uncertain.
6.  Ask a question and receive an answer grounded in retrieved passages.
7.  Inspect how the critic challenged the draft and what the resolution
    step did.
8.  See citations for material claims and an explicit explanation of
    unresolved conflicts.
9.  Run all four demonstration cases, including a documented failure.

## 17. Final Success Criterion

The central question TruthGuard must answer is:

> **What do the documents claim, where is each claim supported, how do
> the claims relate, and what can we responsibly conclude from the
> evidence?**

The final product should be an **auditable document knowledge and
verification system**, not merely a PDF chatbot. Its value comes from
traceable facts, active adversarial checking, transparent conflict
handling, and honest uncertainty.
