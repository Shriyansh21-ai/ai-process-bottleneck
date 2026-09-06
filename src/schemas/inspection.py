"""
Structured inspection-analysis schemas (MRPL Phase 3).

These Pydantic models describe the CONTRACT returned by ``POST /inspection/analyze``:
a set of evidence-backed inspection findings produced by the real agent pipeline
(PlannerAgent -> ToolExecutor -> VerifierAgent) plus a deterministic structural
verification of those findings.

Conventions follow the existing project schemas (see ``src.schemas.agent_run``):
Pydantic v2 ``BaseModel`` + ``Field`` descriptions, additive and read-only. The
severity vocabulary is a typed enum so malformed severity strings are rejected
by validation rather than flowing through to the UI.
"""

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class Severity(str, Enum):
    """Controlled severity vocabulary for an inspection finding.

    A typed enum (not a free string) so the verifier/serializer reject any
    value outside this set — the demo must never surface an arbitrary severity.
    """

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


# Severity ordering used to derive the overall status (higher = worse).
_SEVERITY_RANK = {
    Severity.LOW: 0,
    Severity.MEDIUM: 1,
    Severity.HIGH: 2,
    Severity.CRITICAL: 3,
}


def severity_rank(sev: Severity) -> int:
    return _SEVERITY_RANK.get(sev, 0)


class Finding(BaseModel):
    """A single evidence-backed inspection finding.

    Every finding MUST carry evidence and, when available, the source page it
    was drawn from. ``page_number`` is validated against the pages actually
    retrieved from the document (the evidence guard) so the system cannot
    fabricate provenance.
    """

    finding_id: str = Field(..., description="Stable id, derived from document + index")
    title: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    severity: Severity
    evidence: str = Field(..., min_length=1, description="Supporting text from the document")
    page_number: Optional[int] = Field(
        None, ge=1, description="Source page (1-based) when known; never fabricated"
    )
    extraction_method: Optional[str] = Field(
        None, description="How the source page was extracted (text | ocr)"
    )
    recommendation: str = Field(..., min_length=1)
    confidence: float = Field(..., ge=0.0, le=1.0)


class InspectionVerification(BaseModel):
    """Deterministic verification verdict over the produced findings."""

    approved: bool = Field(..., description="True only when every finding passed validation")
    issues: List[str] = Field(
        default_factory=list, description="Human-readable reasons findings were rejected"
    )
    findings_total: int = Field(0, description="Findings proposed by the agent pipeline")
    findings_valid: int = Field(0, description="Findings that passed validation")
    findings_rejected: int = Field(0, description="Findings dropped by validation")


class InspectionDocumentInfo(BaseModel):
    """Provenance-preserving descriptor of the analyzed document."""

    document_id: Optional[int] = Field(
        None, description="RAG/PostgreSQL document id (None if ingestion failed)"
    )
    filename: str
    page_count: int
    extraction_method: str = Field(..., description="Doc-level method: text | ocr | mixed")


# Overall-status vocabulary (kept as constants so callers don't stringly-type).
STATUS_NO_FINDINGS = "no_findings"
STATUS_REVIEW = "review_recommended"
STATUS_ACTION_REQUIRED = "action_required"
STATUS_VERIFICATION_FAILED = "verification_failed"
STATUS_ANALYSIS_FAILED = "analysis_failed"


class InspectionAnalysis(BaseModel):
    """Top-level structured result returned to the client / frontend."""

    analysis_id: str
    document: InspectionDocumentInfo
    overall_status: str = Field(..., description="Roll-up status derived from findings")
    findings: List[Finding] = Field(default_factory=list)
    verification: InspectionVerification
    run_id: Optional[int] = Field(
        None, description="AgentRun id of the underlying agent execution"
    )
