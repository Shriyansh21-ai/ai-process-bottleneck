"""
Inspection document intelligence API (MRPL Phase 2).

Minimal upload endpoint that:

    upload file  ->  extract text (text-PDF or OCR)  ->  optional RAG ingest
                 ->  return provenance-preserving metadata

It returns enough for a frontend to display the result (filename, page count,
extraction method, a bounded text preview, per-page provenance, RAG ingestion
status, document id) WITHOUT dumping the full confidential text.

This is intentionally NOT the final MRPL workflow endpoint (no approval, no
findings synthesis) — it is the reusable ingestion foundation.
"""

import logging

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from src.core.auth import get_current_active_user
from src.db.models.user import User
from src.db.session import get_db
from src.documents import (
    DocumentIntelligencePipeline,
    ingest_extracted_document,
)
from src.documents.config import get_preview_chars
from src.documents.errors import DocumentError
from src.schemas.inspection import InspectionAnalysis
from src.services.inspection_analysis_service import InspectionAnalysisService

logger = logging.getLogger("api.inspection")

router = APIRouter(prefix="/inspection", tags=["Inspection"])

# Bound the analysis instruction so a single request cannot drive unbounded
# LLM token cost (mirrors the /run QueryRequest bound).
_MAX_QUERY_CHARS = 2000


@router.post("/extract")
async def extract_inspection_document(
    file: UploadFile = File(...),
    ingest: bool = Form(False),
    db: Session = Depends(get_db),
):
    """Extract text from an uploaded inspection document.

    Query/form param ``ingest`` (default False): when true, the extracted
    document is also pushed into the existing RAG pipeline (chunk + embed +
    Qdrant). Extraction always runs first, so a downstream ingestion failure
    still returns the extraction result with a clear ingestion error.
    """
    data = await file.read()

    # --- extraction (always) ---------------------------------------------
    pipeline = DocumentIntelligencePipeline()
    try:
        document = pipeline.extract(data, filename=file.filename)
    except DocumentError as err:
        # Structured, content-free error -> mapped HTTP status.
        raise HTTPException(status_code=err.http_status, detail=err.to_dict())
    except Exception:
        logger.exception("Unexpected extraction failure")
        raise HTTPException(
            status_code=500,
            detail={"error": "Extraction failed", "code": "extraction_failed"},
        )

    response = document.to_summary(preview_chars=get_preview_chars())

    # --- optional RAG ingestion ------------------------------------------
    if ingest:
        try:
            result = ingest_extracted_document(db, document)
            response["ingestion"] = {"status": "success", **result}
        except Exception as exc:
            # Do not fail the whole request — extraction already succeeded.
            logger.warning("RAG ingestion failed for uploaded document: %s", exc)
            response["ingestion"] = {
                "status": "failed",
                "error": str(exc),
                "code": "rag_ingestion_failed",
            }
    else:
        response["ingestion"] = {"status": "skipped"}

    return response


@router.post("/analyze", response_model=InspectionAnalysis)
async def analyze_inspection_document(
    file: UploadFile = File(...),
    query: str = Form(
        "Analyze this inspection report and identify safety-critical findings "
        "requiring attention."
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Full MRPL vertical slice: document -> structured, evidence-backed findings.

    Pipeline (all EXISTING components):

        upload -> extract/OCR (page provenance) -> RAG ingest ->
        PlannerAgent -> ToolExecutor (rag_retrieval + inspection_findings) ->
        VerifierAgent -> deterministic findings verification -> InspectionAnalysis

    Works identically under ``LLM_PROVIDER=mock`` and ``LLM_PROVIDER=ollama``.
    """
    query = (query or "").strip()
    if not query:
        raise HTTPException(
            status_code=422,
            detail={"error": "query must not be empty", "code": "invalid_query"},
        )
    if len(query) > _MAX_QUERY_CHARS:
        raise HTTPException(
            status_code=422,
            detail={"error": "query is too long", "code": "query_too_long"},
        )

    data = await file.read()

    service = InspectionAnalysisService(
        db=db,
        session_id=f"inspection-{current_user.id}",
        user_id=current_user.id,
    )

    try:
        analysis = await service.analyze(data, filename=file.filename, query=query)
    except DocumentError as err:
        # Structured, content-free extraction/validation error -> HTTP status.
        raise HTTPException(status_code=err.http_status, detail=err.to_dict())
    except HTTPException:
        raise
    except Exception:
        logger.exception("Unexpected inspection-analysis failure")
        raise HTTPException(
            status_code=500,
            detail={"error": "Analysis failed", "code": "analysis_failed"},
        )

    return analysis
