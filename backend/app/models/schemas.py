from typing import Optional, List, Dict, Any, Union
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime

class RelationshipType(str, Enum):
    CORROBORATES = "CORROBORATES"
    CONTRADICTS = "CONTRADICTS"
    CONTEXTUALIZES = "CONTEXTUALIZES"
    RELATED = "RELATED"
    UNCERTAIN = "UNCERTAIN"

class FactValueType(str, Enum):
    NUMBER = "number"
    STRING = "string"
    BOOLEAN = "boolean"
    DATE = "date"
    RANGE = "range"

class FactValue(BaseModel):
    type: FactValueType = FactValueType.STRING
    raw: str
    amount: Optional[float] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    unit: Optional[str] = None
    currency: Optional[str] = None

class FactContext(BaseModel):
    time: Optional[str] = None          # e.g., "FY2024", "2015", "Q1 2025"
    time_normalized: Optional[str] = None # e.g., "2024", "2025-Q1"
    geography: Optional[str] = None     # e.g., "Global", "India", "North America"
    scope: Optional[str] = None         # e.g., "Full-time employees", "Worldwide", "Enterprise customers"
    condition: Optional[str] = None     # conditional clause if any

class EvidenceLocation(BaseModel):
    bbox: Optional[List[float]] = None  # [x0, y0, x1, y1]
    char_start: Optional[int] = None
    char_end: Optional[int] = None
    block_no: Optional[int] = None

class Evidence(BaseModel):
    id: str
    document_id: str
    document_name: str
    page: int
    text: str
    location: Optional[EvidenceLocation] = None

class Fact(BaseModel):
    id: str
    subject: str
    predicate: str
    value: FactValue
    context: FactContext
    qualification: Optional[str] = None  # approximately, at least, more than, etc.
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)
    evidence: Evidence

class Relationship(BaseModel):
    id: str
    fact_a_id: str
    fact_b_id: str
    fact_a: Optional[Fact] = None
    fact_b: Optional[Fact] = None
    type: RelationshipType
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    reason: str
    context_diff: Optional[Dict[str, Any]] = None
    value_diff: Optional[Dict[str, Any]] = None

class PageData(BaseModel):
    page_number: int
    text: str
    blocks: Optional[List[Dict[str, Any]]] = None

class Document(BaseModel):
    id: str
    filename: str
    upload_time: str
    page_count: int
    file_path: str
    file_hash: Optional[str] = None
    processing_status: str = "pending" # pending, processing, completed, failed
    error_message: Optional[str] = None
    extracted_facts_count: int = 0
    pages: Optional[List[PageData]] = None

class IngestResponse(BaseModel):
    documents: List[Document]
    message: str

class ProcessResult(BaseModel):
    document_id: str
    status: str
    facts_extracted: int
    facts: List[Fact]

class ProcessSelectedRequest(BaseModel):
    document_ids: List[str]

class DemoCaseInfo(BaseModel):
    id: str
    title: str
    case_type: RelationshipType
    description: str
    document_a_name: str
    document_b_name: str
    expected_outcome: str
    why_it_matters: str
