"""
Document intelligence pipeline (MRPL Phase 2).

Single entry point that converges the text-PDF and scanned/OCR paths onto one
:class:`ExtractedDocument`:

    bytes ─▶ validate (type, size) ─▶ detect kind
                                         │
                    ┌────────────────────┴───────────────────┐
                 PDF │                                        │ image
                     ▼                                        ▼
             TextPDFExtractor                            OCRExtractor
                     │  (per-page scanned-detection)          │
                     ▼                                        │
          OCRExtractor for scanned pages ◀────(if needed)     │
                     └────────────────────┬───────────────────┘
                                          ▼
                                 ExtractedDocument
                                          │
                                          ▼
                         (optional) existing RAG ingestion

The OCR engine and rasterizer are injectable so the pipeline is fully testable
with a deterministic fake — no Tesseract/poppler required for the unit tests.
"""

import hashlib
import logging
import os
import re
from typing import List, Optional

from src.documents.config import (
    get_document_max_bytes,
    get_image_extensions,
    get_allowed_extensions,
    get_text_min_chars,
)
from src.documents.errors import (
    EmptyDocumentError,
    FileTooLargeError,
    InvalidImageError,
    UnsupportedFileTypeError,
)
from src.documents.extractors import OCRExtractor, TextPDFExtractor
from src.documents.ocr import (
    OCREngine,
    PDFRasterizer,
    get_default_ocr_engine,
    get_default_rasterizer,
)
from src.documents.representation import (
    METHOD_EMPTY,
    METHOD_MIXED,
    METHOD_OCR,
    METHOD_TEXT,
    TYPE_IMAGE,
    TYPE_PDF,
    ExtractedDocument,
    PageContent,
)

logger = logging.getLogger("documents.pipeline")

_PDF_MAGIC = b"%PDF"
_FILENAME_SAFE = re.compile(r"[^A-Za-z0-9._-]+")


def sanitize_filename(filename: Optional[str]) -> str:
    """Return a safe basename (no path components, bounded length)."""
    if not filename:
        return "upload"
    # Strip any directory components from both separators, then whitelist chars.
    base = os.path.basename(filename.replace("\\", "/"))
    base = _FILENAME_SAFE.sub("_", base).strip("._") or "upload"
    return base[:120]


def _extension(filename: str) -> str:
    _, ext = os.path.splitext(filename)
    return ext.lower().lstrip(".")


def _document_id(data: bytes) -> str:
    """Deterministic id derived from content (stable across identical uploads)."""
    return hashlib.sha256(data).hexdigest()[:16]


class DocumentIntelligencePipeline:
    """Extracts a normalized document from raw upload bytes."""

    def __init__(
        self,
        ocr_engine: Optional[OCREngine] = None,
        rasterizer: Optional[PDFRasterizer] = None,
    ):
        # Constructed lazily via the default factories only when OCR is actually
        # required, so importing/using the text path never needs the OCR stack.
        self._ocr_engine = ocr_engine
        self._rasterizer = rasterizer

    # -- lazy OCR wiring ----------------------------------------------------
    def _get_ocr_extractor(self) -> OCRExtractor:
        engine = self._ocr_engine or get_default_ocr_engine()
        rasterizer = self._rasterizer or get_default_rasterizer()
        return OCRExtractor(ocr_engine=engine, rasterizer=rasterizer)

    # -- validation ---------------------------------------------------------
    def _validate(self, filename: str, data: bytes) -> str:
        if not data:
            raise EmptyDocumentError("The uploaded file is empty.")

        max_bytes = get_document_max_bytes()
        if len(data) > max_bytes:
            raise FileTooLargeError(
                f"File exceeds the maximum allowed size of {max_bytes} bytes."
            )

        ext = _extension(filename)
        is_pdf = ext == "pdf" or data[:4] == _PDF_MAGIC
        if is_pdf:
            return TYPE_PDF
        if ext in get_image_extensions():
            return TYPE_IMAGE
        # Unknown extension: last chance — sniff an image with Pillow.
        if self._looks_like_image(data):
            return TYPE_IMAGE

        raise UnsupportedFileTypeError(
            f"Unsupported file type '.{ext or 'unknown'}'. Allowed: "
            f"{', '.join(sorted(get_allowed_extensions()))}."
        )

    @staticmethod
    def _looks_like_image(data: bytes) -> bool:
        try:
            from PIL import Image  # local import; Pillow is optional
        except ImportError:  # pragma: no cover
            return False
        try:
            import io
            img = Image.open(io.BytesIO(data))
            img.verify()
            return True
        except Exception:
            return False

    # -- main entry ---------------------------------------------------------
    def extract(self, data: bytes, filename: str) -> ExtractedDocument:
        safe_name = sanitize_filename(filename)
        doc_type = self._validate(safe_name, data)
        document_id = _document_id(data)

        # Metadata carries provenance + a bit of diagnostics (NEVER document text).
        metadata = {
            "byte_size": len(data),
            "source": "upload",
        }

        if doc_type == TYPE_PDF:
            pages = self._extract_pdf(data)
        else:
            pages = self._extract_image(data)

        # Converge: fail closed if nothing usable came out of EITHER path.
        total_chars = sum(p.char_count for p in pages)
        if not pages or total_chars == 0:
            raise EmptyDocumentError(
                "No readable text could be extracted from the document."
            )

        extraction_method = self._document_method(pages)

        logger.info(
            "document extracted | file=%s type=%s pages=%d method=%s chars=%d",
            safe_name, doc_type, len(pages), extraction_method, total_chars,
        )

        return ExtractedDocument(
            document_id=document_id,
            filename=safe_name,
            document_type=doc_type,
            extraction_method=extraction_method,
            pages=pages,
            metadata=metadata,
        )

    # -- PDF path -----------------------------------------------------------
    def _extract_pdf(self, data: bytes) -> List[PageContent]:
        text_pages = TextPDFExtractor().extract(data)

        threshold = get_text_min_chars()
        scanned_indices = [
            i for i, p in enumerate(text_pages)
            if p.char_count < threshold
        ]

        # Whole document (or some pages) is scanned -> route those to OCR.
        if scanned_indices:
            # Raises OCRUnavailableError (clear, non-silent) if the OCR stack is
            # missing — even though some text pages may exist, we do not quietly
            # drop the scanned pages.
            ocr_pages = self._get_ocr_extractor().extract_pdf_pages(
                data, page_indices=scanned_indices
            )
            by_index = {p.page_number - 1: p for p in ocr_pages}
            for i in scanned_indices:
                if i in by_index:
                    text_pages[i] = by_index[i]

        return text_pages

    # -- image path ---------------------------------------------------------
    def _extract_image(self, data: bytes) -> List[PageContent]:
        return self._get_ocr_extractor().extract_image(data)

    # -- doc-level method ---------------------------------------------------
    @staticmethod
    def _document_method(pages: List[PageContent]) -> str:
        methods = {p.extraction_method for p in pages if p.char_count > 0}
        if not methods:
            return METHOD_EMPTY
        if methods == {METHOD_TEXT}:
            return METHOD_TEXT
        if methods == {METHOD_OCR}:
            return METHOD_OCR
        return METHOD_MIXED
