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

from src.db.session import get_db
from src.documents import (
    DocumentIntelligencePipeline,
    ingest_extracted_document,
)
from src.documents.config import get_preview_chars
from src.documents.errors import DocumentError

logger = logging.getLogger("api.inspection")

router = APIRouter(prefix="/inspection", tags=["Inspection"])


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
