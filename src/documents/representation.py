"""
Internal document representation (MRPL Phase 2).

Both extraction paths — a text PDF parsed with pypdf, and a scanned PDF/image
run through OCR — converge on the SAME :class:`ExtractedDocument`. Everything
downstream (RAG ingestion, the API response, and later the agent/UI) consumes
this single shape, so it must preserve PAGE-LEVEL provenance: the demo needs to
say "this finding came from page 4, extracted by OCR".

These are plain dataclasses (no DB coupling) — the representation is produced by
the extraction pipeline before any persistence decision is made.
"""

from dataclasses import dataclass, field
from typing import List, Optional

# Extraction-method vocabulary (kept as constants so callers don't stringly-type).
METHOD_TEXT = "text"      # native PDF text layer (pypdf)
METHOD_OCR = "ocr"        # rendered page / image run through OCR
METHOD_MIXED = "mixed"    # document has both text and OCR pages
METHOD_EMPTY = "empty"    # no usable text could be extracted

# Document-type vocabulary.
TYPE_PDF = "pdf"
TYPE_IMAGE = "image"


@dataclass
class PageContent:
    """One page's extracted text plus how it was obtained."""

    page_number: int                       # 1-based
    text: str
    extraction_method: str                 # METHOD_TEXT | METHOD_OCR
    confidence: Optional[float] = None      # OCR mean confidence 0..1 (None for text)

    @property
    def char_count(self) -> int:
        return len(self.text or "")

    def to_summary(self) -> dict:
        """Provenance-only view (no full text) for API responses."""
        return {
            "page_number": self.page_number,
            "extraction_method": self.extraction_method,
            "char_count": self.char_count,
            "confidence": self.confidence,
        }


@dataclass
class ExtractedDocument:
    """The converged representation of an ingested document."""

    document_id: str
    filename: str
    document_type: str                     # TYPE_PDF | TYPE_IMAGE
    extraction_method: str                 # doc-level: text | ocr | mixed | empty
    pages: List[PageContent] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    @property
    def page_count(self) -> int:
        return len(self.pages)

    @property
    def text(self) -> str:
        """Full document text (pages joined). Kept out of default API output."""
        return "\n\n".join(p.text for p in self.pages if p.text)

    @property
    def char_count(self) -> int:
        return len(self.text)

    def preview(self, limit: int = 500) -> str:
        """First ``limit`` characters of the extracted text (for UI display)."""
        snippet = self.text[:limit]
        return snippet

    def to_summary(self, preview_chars: int = 500) -> dict:
        """Compact, provenance-preserving view for API/UI.

        Deliberately does NOT include the full extracted text — only a bounded
        preview — because the documents are confidential and can be large.
        """
        return {
            "document_id": self.document_id,
            "filename": self.filename,
            "document_type": self.document_type,
            "extraction_method": self.extraction_method,
            "page_count": self.page_count,
            "char_count": self.char_count,
            "text_preview": self.preview(preview_chars),
            "pages": [p.to_summary() for p in self.pages],
            "metadata": self.metadata,
        }
