import os
import shutil
import uuid
import hashlib
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from app.models.schemas import (
    Document, Fact, Relationship, ProcessResult, IngestResponse,
    DemoCaseInfo, RelationshipType, ProcessSelectedRequest
)
from app.models.qa_schemas import (
    QARequest, QAVerificationResponse, SampleQuestion
)
from app.services.pdf_processor import PDFProcessor
from app.services.fact_extractor import FactExtractor
from app.services.matcher import FactMatcher
from app.services.relationship_engine import RelationshipEngine
from app.services.consensus_engine import ConsensusEngine
from app.services.qa.orchestrator import QAOrchestrator
from app.db.storage import Storage
from app.demo_generator import DEMO_CASES, DEMO_DIR, generate_all_demo_pdfs

router = APIRouter(prefix="/api")
storage = Storage()
pdf_processor = PDFProcessor()
fact_extractor = FactExtractor()
fact_matcher = FactMatcher()
relationship_engine = RelationshipEngine()
qa_orchestrator = QAOrchestrator()

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ----------------- Document Endpoints -----------------
@router.post("/documents", response_model=IngestResponse)
async def upload_documents(files: List[UploadFile] = File(...)):
    """Upload one or more PDF documents."""
    ingested_docs: List[Document] = []
    
    for f in files:
        if not f.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail=f"File {f.filename} is not a PDF")

        temp_id = f"temp_{uuid.uuid4().hex[:8]}"
        temp_path = os.path.join(UPLOAD_DIR, f"{temp_id}_{f.filename}")
        
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(f.file, buffer)

        # Compute content hash
        hasher = hashlib.sha256()
        with open(temp_path, "rb") as bf:
            for chunk in iter(lambda: bf.read(65536), b""):
                hasher.update(chunk)
        file_hash = hasher.hexdigest()

        # Check if identical file already exists in database
        existing_doc = storage.get_document_by_hash(file_hash)
        if existing_doc:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            ingested_docs.append(existing_doc)
            continue

        doc_id = f"doc_{uuid.uuid4().hex[:8]}"
        save_path = os.path.join(UPLOAD_DIR, f"{doc_id}_{f.filename}")
        os.rename(temp_path, save_path)

        try:
            document, pages = pdf_processor.process_pdf(save_path, document_id=doc_id, original_filename=f.filename)
            document.file_hash = file_hash
            storage.save_document(document)
            ingested_docs.append(document)
        except Exception as e:
            if os.path.exists(save_path):
                os.remove(save_path)
            raise HTTPException(status_code=500, detail=f"Failed to process {f.filename}: {str(e)}")

    return IngestResponse(
        documents=ingested_docs,
        message=f"Successfully uploaded and indexed {len(ingested_docs)} document(s)."
    )

@router.get("/documents", response_model=List[Document])
def list_documents():
    """Returns all ingested documents with page counts and status."""
    return storage.get_documents()

@router.get("/documents/{document_id}", response_model=Document)
def get_document(document_id: str):
    """Returns specific document details including page contents."""
    doc = storage.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc

@router.delete("/documents/{document_id}")
def delete_document(document_id: str):
    """Deletes a document, its extracted facts, and associated relationships."""
    doc = storage.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    success = storage.delete_document(document_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete document")

    # Recompute cross-document relationships among remaining facts
    _recompute_all_relationships()
    return {"message": f"Document '{doc.filename}' ({document_id}) deleted successfully."}

# ----------------- Fact Processing Endpoints -----------------
def _recompute_all_relationships():
    """Runs candidate matching and relationship classification across all stored facts."""
    all_facts = storage.get_facts()
    candidate_pairs = fact_matcher.find_candidate_pairs(all_facts)
    
    relationships: List[Relationship] = []
    for fact_a, fact_b, sim_score in candidate_pairs:
        rel = relationship_engine.evaluate_relationship(fact_a, fact_b)
        relationships.append(rel)

    storage.save_relationships(relationships)
    return relationships

@router.post("/documents/analyze-selected")
def analyze_selected_documents(request: ProcessSelectedRequest):
    """
    Extracts facts for the selected documents (if not yet processed) and computes
    cross-document relationships specifically between these documents.
    """
    if not request.document_ids or len(request.document_ids) < 2:
        raise HTTPException(status_code=400, detail="Please select at least 2 documents to analyze together.")
    if len(request.document_ids) > 5:
        raise HTTPException(status_code=400, detail="A maximum of 5 documents can be analyzed together.")

    selected_docs: List[Document] = []
    total_facts_extracted = 0

    for doc_id in request.document_ids:
        doc = storage.get_document(doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")

        # If not yet extracted or if 0 facts were extracted previously, extract facts now
        if doc.processing_status != "completed" or doc.extracted_facts_count == 0:
            if not doc.pages:
                raise HTTPException(status_code=400, detail=f"Document '{doc.filename}' has no indexed pages to extract")
            facts = fact_extractor.extract_facts(doc.id, doc.filename, doc.pages)
            storage.save_facts(facts)
            storage.update_document_status(doc.id, "completed", len(facts))
            total_facts_extracted += len(facts)
            doc = storage.get_document(doc_id)

        selected_docs.append(doc)

    # Recompute relationships globally to keep all relationships up to date
    _recompute_all_relationships()

    # Get relationships specifically involving the selected documents
    selected_relationships = storage.get_relationships(document_ids=request.document_ids)

    return {
        "message": f"Successfully analyzed {len(selected_docs)} documents together.",
        "document_ids": request.document_ids,
        "facts_extracted_in_this_run": total_facts_extracted,
        "relationships_count": len(selected_relationships),
        "relationships": selected_relationships
    }

@router.post("/consensus/matrix")
def get_consensus_matrix(request: ProcessSelectedRequest):
    """
    Computes a consolidated multi-document consensus matrix for 2 to 5 selected documents.
    Aligns common claims across all selected documents and determines consensus / contradiction.
    """
    if not request.document_ids or len(request.document_ids) < 2:
        raise HTTPException(status_code=400, detail="Please select at least 2 documents to view consensus.")
    if len(request.document_ids) > 5:
        raise HTTPException(status_code=400, detail="A maximum of 5 documents can be analyzed together.")

    selected_docs: List[Document] = []
    for doc_id in request.document_ids:
        doc = storage.get_document(doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")
        selected_docs.append(doc)

    facts = storage.get_facts(document_ids=request.document_ids)
    return ConsensusEngine.compute_consensus_matrix(facts, selected_docs)

@router.post("/documents/{document_id}/process", response_model=ProcessResult)
def process_document(document_id: str):
    """Processes document, extracts facts, links evidence, and recalculates relationships."""
    doc = storage.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if not doc.pages:
        raise HTTPException(status_code=400, detail="Document has no indexed pages")

    storage.update_document_status(document_id, "processing")

    try:
        facts = fact_extractor.extract_facts(doc.id, doc.filename, doc.pages)
        storage.save_facts(facts)
        storage.update_document_status(document_id, "completed", len(facts))

        # Recalculate cross-document relationships
        _recompute_all_relationships()

        return ProcessResult(
            document_id=doc.id,
            status="completed",
            facts_extracted=len(facts),
            facts=facts
        )
    except Exception as e:
        storage.update_document_status(document_id, "failed")
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")

@router.post("/process-all")
def process_all_documents():
    """Processes all unprocessed documents."""
    docs = storage.get_documents()
    total_facts = 0
    for d in docs:
        if d.processing_status != "completed" or d.extracted_facts_count == 0:
            full_doc = storage.get_document(d.id)
            if full_doc and full_doc.pages:
                facts = fact_extractor.extract_facts(full_doc.id, full_doc.filename, full_doc.pages)
                storage.save_facts(facts)
                storage.update_document_status(full_doc.id, "completed", len(facts))
                total_facts += len(facts)

    rels = _recompute_all_relationships()
    return {
        "message": f"Processed all documents. Total facts extracted: {total_facts}",
        "relationships_detected": len(rels)
    }

# ----------------- Facts & Relationships -----------------
@router.get("/facts", response_model=List[Fact])
def get_facts(
    document_id: Optional[str] = None,
    document_ids: Optional[List[str]] = Query(None)
):
    """Returns extracted facts and their evidence provenance."""
    parsed_ids = None
    if document_ids:
        parsed_ids = []
        for item in document_ids:
            for sub_id in item.split(","):
                clean = sub_id.strip()
                if clean:
                    parsed_ids.append(clean)
    return storage.get_facts(document_id=document_id, document_ids=parsed_ids)

@router.get("/facts/{fact_id}", response_model=Fact)
def get_fact(fact_id: str):
    fact = storage.get_fact(fact_id)
    if not fact:
        raise HTTPException(status_code=404, detail="Fact not found")
    return fact

@router.get("/relationships", response_model=List[Relationship])
def get_relationships(
    type: Optional[str] = None,
    document_ids: Optional[List[str]] = Query(None)
):
    """Returns cross-document relationships filtered by type and optionally document IDs."""
    parsed_ids = None
    if document_ids:
        parsed_ids = []
        for item in document_ids:
            for sub_id in item.split(","):
                clean = sub_id.strip()
                if clean:
                    parsed_ids.append(clean)
    return storage.get_relationships(rel_type=type, document_ids=parsed_ids)

@router.get("/relationships/{relationship_id}", response_model=Relationship)
def get_relationship_details(relationship_id: str):
    """Returns full relationship inspection with both facts, evidence, and reasoning."""
    rels = storage.get_relationships()
    for r in rels:
        if r.id == relationship_id:
            return r
    raise HTTPException(status_code=404, detail="Relationship not found")

# ----------------- Demo Suite Endpoints -----------------
@router.get("/demo/cases", response_model=List[DemoCaseInfo])
def get_demo_cases():
    """Returns the 4 required demonstration cases."""
    return DEMO_CASES

@router.post("/demo/load/{case_id}")
def load_demo_case(case_id: str):
    """Loads and automatically processes the two PDFs for a specific demonstration case."""
    case = next((c for c in DEMO_CASES if c.id == case_id), None)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

    generate_all_demo_pdfs()

    pdf_a_path = os.path.join(DEMO_DIR, case.document_a_name)
    pdf_b_path = os.path.join(DEMO_DIR, case.document_b_name)

    # Ingest Doc A
    doc_a_id = f"demo_{case_id}_a"
    doc_a, _ = pdf_processor.process_pdf(pdf_a_path, document_id=doc_a_id)
    storage.save_document(doc_a)

    # Ingest Doc B
    doc_b_id = f"demo_{case_id}_b"
    doc_b, _ = pdf_processor.process_pdf(pdf_b_path, document_id=doc_b_id)
    storage.save_document(doc_b)

    # Process facts for both
    facts_a = fact_extractor.extract_facts(doc_a.id, doc_a.filename, doc_a.pages or [])
    storage.save_facts(facts_a)
    storage.update_document_status(doc_a.id, "completed", len(facts_a))

    facts_b = fact_extractor.extract_facts(doc_b.id, doc_b.filename, doc_b.pages or [])
    storage.save_facts(facts_b)
    storage.update_document_status(doc_b.id, "completed", len(facts_b))

    # Recompute relationships
    rels = _recompute_all_relationships()

    return {
        "case": case,
        "document_a": doc_a,
        "document_b": doc_b,
        "facts_extracted": len(facts_a) + len(facts_b),
        "relationships_formed": len(rels),
        "message": f"Successfully loaded and analyzed Demo {case.title}"
    }

@router.post("/clear")
def clear_all():
    """Clears all stored documents, facts, and relationships."""
    storage.clear_all()
    return {"message": "Knowledge layer database reset successfully"}

# ----------------- QA & Verification Endpoints -----------------
@router.post("/qa/ask", response_model=QAVerificationResponse)
def ask_question(request: QARequest):
    """
    Multi-Agent Question Answering with Critic verification, citation attribution,
    and source precedence conflict resolution.
    """
    if not request.question or not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    # Retrieve docs
    if request.document_ids:
        docs = [storage.get_document(doc_id) for doc_id in request.document_ids]
        docs = [d for d in docs if d is not None]
    else:
        # Load all documents with their pages
        raw_docs = storage.get_documents()
        docs = [storage.get_document(d.id) for d in raw_docs]
        docs = [d for d in docs if d is not None]

    if not docs:
        raise HTTPException(status_code=400, detail="No documents available in the corpus to answer questions. Please upload a document first.")

    facts = storage.get_facts(document_ids=request.document_ids)
    relationships = storage.get_relationships(document_ids=request.document_ids)

    return qa_orchestrator.process_question(
        question=request.question,
        documents=docs,
        facts=facts,
        relationships=relationships,
        max_passages=request.max_passages
    )

@router.get("/qa/sample-questions", response_model=List[SampleQuestion])
def get_sample_questions():
    """Returns curated contextual questions for testing verification and precedence."""
    return [
        SampleQuestion(
            id="q1",
            question="What was the company's revenue in FY2024?",
            category="Corroboration & Financial Metrics",
            applicable_document_names=["CompanyX_Annual_Report_2024.pdf", "Financial_Review_FY24.pdf"]
        ),
        SampleQuestion(
            id="q2",
            question="When was the company founded according to the records?",
            category="Contradiction & Conflict Resolution",
            applicable_document_names=["Corp_Overview_Official.pdf", "ThirdParty_Analyst_Brief.pdf"]
        ),
        SampleQuestion(
            id="q3",
            question="What is the employee count or headcount?",
            category="Contextual Differences",
            applicable_document_names=["ESG_Impact_Report_2024.pdf", "Quarterly_Investor_Update_Q4.pdf"]
        ),
        SampleQuestion(
            id="q4",
            question="What is the company's policy on remote work or travel reimbursement?",
            category="Source Precedence & Amendments",
            applicable_document_names=["Policy_Manual_2023.pdf", "Policy_Amendment_2024.pdf"]
        ),
        SampleQuestion(
            id="q5",
            question="What was the total expenditure on quantum computing hardware in 1995?",
            category="Insufficient Evidence Test",
            applicable_document_names=[]
        )
    ]

