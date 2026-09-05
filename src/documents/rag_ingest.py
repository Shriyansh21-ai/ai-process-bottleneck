"""
Bridge from the document representation into the EXISTING RAG pipeline
(MRPL Phase 2).

This does NOT re-implement chunking/embedding/Qdrant — it calls the existing
:func:`src.rag.ingest.ingest_document`, passing per-page structure so provenance
(page number + extraction method) is preserved through to the vector store.
"""

import logging
from typing import Optional

from sqlalchemy.orm import Session

from src.documents.representation import ExtractedDocument

logger = logging.getLogger("documents.rag_ingest")


def ingest_extracted_document(
    db: Session,
    document: ExtractedDocument,
    source: Optional[str] = None,
) -> dict:
    """Ingest an :class:`ExtractedDocument` via the existing RAG pipeline.

    Returns the dict from :func:`src.rag.ingest.ingest_document` (document id,
    chunk count, extraction method, ...). Raises on ingestion failure so the
    caller can report a structured error.
    """
    # Imported lazily so importing the extraction layer never pulls in Qdrant /
    # embedding model / DB models unless ingestion is actually requested.
    from src.rag.ingest import ingest_document

    pages = [
        {"page_number": p.page_number, "text": p.text}
        for p in document.pages
    ]

    result = ingest_document(
        db=db,
        title=document.filename,
        source=source or document.metadata.get("source", "upload"),
        doc_type=document.document_type,
        text=document.text,
        pages=pages,
        extraction_method=document.extraction_method,
    )

    logger.info(
        "document ingested into RAG | file=%s chunks=%s",
        document.filename,
        result.get("chunks_created"),
    )
    return result
