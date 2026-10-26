from typing import Optional, List, Dict, Any, Union
from enum import Enum
from pydantic import BaseModel, Field

class ClaimType(str, Enum):
    DIRECTLY_SUPPORTED = "directly_supported"
    INFERENCE = "inference"
    UNSUPPORTED = "unsupported"

class CitationItem(BaseModel):
    citation_id: str
    document_id: str
    document_name: str
    page: int
    quote_text: str
    location: Optional[Dict[str, Any]] = None
    publication_date: Optional[str] = None
    effective_date: Optional[str] = None

class ClaimItem(BaseModel):
    claim_id: str
    text: str
    claim_type: ClaimType
    citation_ids: List[str] = []
    confidence: float = Field(default=0.9, ge=0.0, le=1.0)
    provenance_note: Optional[str] = None

class CriticIssueSeverity(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class CriticIssueType(str, Enum):
    CONTRADICTION = "CONTRADICTION"
    UNGROUNDED_CLAIM = "UNGROUNDED_CLAIM"
    INVALID_CITATION = "INVALID_CITATION"
    CONTEXT_MISMATCH = "CONTEXT_MISMATCH"
    STALE_VERSION = "STALE_VERSION"
    MISSING_EVIDENCE = "MISSING_EVIDENCE"

class CriticIssue(BaseModel):
    issue_type: CriticIssueType
    severity: CriticIssueSeverity
    description: str
    affected_claim_id: Optional[str] = None
    counter_evidence: Optional[CitationItem] = None
    recommendation: Optional[str] = None

class CriticReport(BaseModel):
    round_number: int
    passed: bool
    issues: List[CriticIssue] = []
    summary: str

class ConflictPosition(BaseModel):
    document_id: str
    document_name: str
    effective_date: Optional[str] = None
    publication_date: Optional[str] = None
    version: Optional[str] = None
    claimed_value: str
    evidence_text: str
    page: int
    authority: Optional[str] = None

class ConflictResolutionStatus(str, Enum):
    NO_CONFLICT = "NO_CONFLICT"
    RESOLVED_BY_PRECEDENCE = "RESOLVED_BY_PRECEDENCE"
    UNRESOLVED_CONFLICT = "UNRESOLVED_CONFLICT"
    CONTEXT_EXPLAINED = "CONTEXT_EXPLAINED"

class ConflictResolution(BaseModel):
    status: ConflictResolutionStatus
    rationale: str
    preferred_position: Optional[ConflictPosition] = None
    positions: List[ConflictPosition] = []
    is_superseded: bool = False
    superseding_document_name: Optional[str] = None

class QAVerdict(str, Enum):
    VERIFIED = "VERIFIED"
    CONFLICT_DETECTED = "CONFLICT_DETECTED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    UNCERTAIN = "UNCERTAIN"

class QAVerificationResponse(BaseModel):
    question_id: str
    question: str
    verdict: QAVerdict
    final_answer: str
    draft_answer: Optional[str] = None
    claims: List[ClaimItem] = []
    citations: List[CitationItem] = []
    critic_history: List[CriticReport] = []
    iterations_run: int = 1
    conflict_resolution: Optional[ConflictResolution] = None
    retrieved_passages_count: int = 0
    insufficient_evidence_reason: Optional[str] = None

class QARequest(BaseModel):
    question: str
    document_ids: Optional[List[str]] = None
    max_passages: int = 8

class SampleQuestion(BaseModel):
    id: str
    question: str
    category: str
    applicable_document_names: List[str] = []
