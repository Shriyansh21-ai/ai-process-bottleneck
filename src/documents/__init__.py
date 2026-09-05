"""
Document intelligence layer (MRPL Phase 2).

Converts uploaded inspection documents (text PDF, scanned PDF, or image) into a
single normalized :class:`ExtractedDocument`, preserving page-level provenance,
then (optionally) feeds them into the EXISTING RAG pipeline.

Public surface::

    from src.documents import DocumentIntelligencePipeline, ExtractedDocument
    from src.documents import ingest_extracted_document
    from src.documents.errors import DocumentError, OCRUnavailableError
"""

from src.documents.errors import (
    CorruptedDocumentError,
    DocumentError,
    EmptyDocumentError,
    FileTooLargeError,
    InvalidImageError,
    OCRUnavailableError,
    UnsupportedFileTypeError,
)
from src.documents.pipeline import (
    DocumentIntelligencePipeline,
    sanitize_filename,
)
from src.documents.rag_ingest import ingest_extracted_document
from src.documents.representation import (
    ExtractedDocument,
    PageContent,
)

__all__ = [
    "DocumentIntelligencePipeline",
    "ExtractedDocument",
    "PageContent",
    "ingest_extracted_document",
    "sanitize_filename",
    "DocumentError",
    "UnsupportedFileTypeError",
    "FileTooLargeError",
    "CorruptedDocumentError",
    "EmptyDocumentError",
    "InvalidImageError",
    "OCRUnavailableError",
]
