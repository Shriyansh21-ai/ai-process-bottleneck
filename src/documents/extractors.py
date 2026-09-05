"""
Document extractors (MRPL Phase 2).

    DocumentExtractor (ABC)
        ├── TextPDFExtractor   — native PDF text layer via pypdf
        └── OCRExtractor       — scanned PDF / image via an OCREngine

Each produces a list of :class:`~src.documents.representation.PageContent`; the
pipeline (:mod:`src.documents.pipeline`) decides which extractor to run per page
and converges the results into one :class:`ExtractedDocument`.
"""

import io
import logging
from typing import List, Optional

from src.documents.config import get_ocr_dpi
from src.documents.errors import (
    CorruptedDocumentError,
    InvalidImageError,
    OCRUnavailableError,
)
from src.documents.ocr import OCREngine, PDFRasterizer
from src.documents.representation import (
    METHOD_OCR,
    METHOD_TEXT,
    PageContent,
)

logger = logging.getLogger("documents.extractors")

try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover
    PdfReader = None

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None


class DocumentExtractor:
    """Marker base for extractors.

    Concrete extractors expose their own entry point(s) — ``TextPDFExtractor``
    has ``extract(pdf_bytes)`` while ``OCRExtractor`` has ``extract_pdf_pages``
    and ``extract_image`` — because their inputs differ. All produce
    :class:`~src.documents.representation.PageContent` lists.
    """


class TextPDFExtractor(DocumentExtractor):
    """Extracts the native text layer of a PDF, one PageContent per page."""

    def extract(self, pdf_bytes: bytes) -> List[PageContent]:
        if PdfReader is None:  # pragma: no cover - pypdf is a core dependency
            raise CorruptedDocumentError("pypdf is not installed")

        try:
            reader = PdfReader(io.BytesIO(pdf_bytes))
        except Exception as exc:
            raise CorruptedDocumentError(
                f"The PDF could not be opened (corrupted or not a PDF): {exc}"
            ) from exc

        pages: List[PageContent] = []
        for index, page in enumerate(reader.pages):
            try:
                text = page.extract_text() or ""
            except Exception:
                # A single unreadable page must not abort the whole document;
                # record it as empty text so OCR can be routed to it later.
                text = ""
            pages.append(
                PageContent(
                    page_number=index + 1,
                    text=text.strip(),
                    extraction_method=METHOD_TEXT,
                    confidence=None,
                )
            )
        return pages


class OCRExtractor(DocumentExtractor):
    """OCRs scanned PDF pages or a standalone image.

    Requires an available :class:`OCREngine`; PDF input additionally requires a
    :class:`PDFRasterizer`. Missing tools raise
    :class:`~src.documents.errors.OCRUnavailableError` — never silent empties.
    """

    def __init__(
        self,
        ocr_engine: OCREngine,
        rasterizer: Optional[PDFRasterizer] = None,
    ):
        self.ocr_engine = ocr_engine
        self.rasterizer = rasterizer or PDFRasterizer()

    # -- PDF: render selected pages, OCR each -------------------------------
    def extract_pdf_pages(
        self,
        pdf_bytes: bytes,
        page_indices: List[int],
        dpi: Optional[int] = None,
    ) -> List[PageContent]:
        if not self.ocr_engine.is_available():
            raise OCRUnavailableError(self.ocr_engine.unavailable_reason())
        if not self.rasterizer.is_available():
            raise OCRUnavailableError(self.rasterizer.unavailable_reason())

        images = self.rasterizer.render_pages(
            pdf_bytes, dpi=dpi or get_ocr_dpi(), page_indices=page_indices
        )

        pages: List[PageContent] = []
        for offset, image in enumerate(images):
            page_index = page_indices[offset]
            text, confidence = self.ocr_engine.image_to_text(image)
            pages.append(
                PageContent(
                    page_number=page_index + 1,
                    text=(text or "").strip(),
                    extraction_method=METHOD_OCR,
                    confidence=confidence,
                )
            )
        return pages

    # -- Standalone image --------------------------------------------------
    def extract_image(self, image_bytes: bytes) -> List[PageContent]:
        if not self.ocr_engine.is_available():
            raise OCRUnavailableError(self.ocr_engine.unavailable_reason())
        if Image is None:  # pragma: no cover
            raise InvalidImageError("Pillow is not installed")

        try:
            image = Image.open(io.BytesIO(image_bytes))
            image.load()
        except Exception as exc:
            raise InvalidImageError(
                f"The uploaded file is not a readable image: {exc}"
            ) from exc

        text, confidence = self.ocr_engine.image_to_text(image)
        return [
            PageContent(
                page_number=1,
                text=(text or "").strip(),
                extraction_method=METHOD_OCR,
                confidence=confidence,
            )
        ]
