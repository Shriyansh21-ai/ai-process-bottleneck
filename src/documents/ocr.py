"""
OCR / rasterization abstractions (MRPL Phase 2).

Sovereign-by-design: the primary OCR path is a LOCAL engine (Tesseract via the
``pytesseract`` wrapper) — no cloud OCR. The abstraction lets a local vision
model be plugged in later (implement :class:`OCREngine`) without touching the
extraction pipeline.

Everything here is import-guarded and availability-checked. If the local OCR
toolchain is absent (``pytesseract``/Tesseract binary, or ``pdf2image``/poppler
for rasterizing PDF pages), the components report themselves unavailable and the
pipeline raises a clear :class:`~src.documents.errors.OCRUnavailableError` — it
never silently returns empty text.

System dependencies (documented in ``requirements-ocr.txt``):
  * Tesseract OCR engine  (Debian/Ubuntu: ``apt-get install tesseract-ocr``)
  * Poppler utilities     (Debian/Ubuntu: ``apt-get install poppler-utils``)
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

from src.documents.config import get_ocr_dpi, get_ocr_language
from src.documents.errors import InvalidImageError, OCRUnavailableError

logger = logging.getLogger("documents.ocr")

# --- Optional imports (never break the core app when absent) -----------------
try:
    import pytesseract
except ImportError:  # pragma: no cover
    pytesseract = None

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None

try:
    import pdf2image
except ImportError:  # pragma: no cover
    pdf2image = None


# ======================================================================
# OCR ENGINE ABSTRACTION
# ======================================================================

class OCREngine(ABC):
    """Turns a single image into text (+ optional confidence)."""

    name: str = "base-ocr"

    @abstractmethod
    def is_available(self) -> bool:
        """Whether this engine can actually run in the current environment."""

    @abstractmethod
    def image_to_text(self, image) -> Tuple[str, Optional[float]]:
        """Return ``(text, confidence)`` for one PIL image.

        ``confidence`` is a 0..1 mean over recognised words, or ``None`` when the
        engine cannot report it.
        """

    def unavailable_reason(self) -> str:
        """Actionable message describing what to install. Override as needed."""
        return "No OCR engine is available."


class TesseractOCREngine(OCREngine):
    """Local OCR via Tesseract (the ``pytesseract`` wrapper)."""

    name = "tesseract"

    def __init__(self, language: Optional[str] = None):
        self.language = language or get_ocr_language()

    def is_available(self) -> bool:
        if pytesseract is None:
            return False
        try:
            # Probes for the actual Tesseract BINARY, not just the wrapper.
            pytesseract.get_tesseract_version()
            return True
        except Exception:
            return False

    def unavailable_reason(self) -> str:
        if pytesseract is None:
            return (
                "pytesseract is not installed. Install the OCR extras: "
                "pip install -r requirements-ocr.txt"
            )
        return (
            "The Tesseract OCR binary was not found on PATH. Install it "
            "(Debian/Ubuntu: 'apt-get install tesseract-ocr'; "
            "macOS: 'brew install tesseract'; "
            "Windows: install the Tesseract build and add it to PATH)."
        )

    def image_to_text(self, image) -> Tuple[str, Optional[float]]:
        if not self.is_available():
            raise OCRUnavailableError(self.unavailable_reason())

        try:
            # image_to_data gives per-word confidences; average the valid ones.
            data = pytesseract.image_to_data(
                image,
                lang=self.language,
                output_type=pytesseract.Output.DICT,
            )
        except OCRUnavailableError:
            raise
        except Exception as exc:
            # e.g. an unreadable/invalid image handed to the engine.
            raise InvalidImageError(f"OCR failed to read the image: {exc}") from exc

        words = data.get("text", [])
        confs = data.get("conf", [])
        kept_words = []
        kept_confs = []
        for word, conf in zip(words, confs):
            if word and word.strip():
                kept_words.append(word)
                try:
                    c = float(conf)
                except (TypeError, ValueError):
                    c = -1.0
                if c >= 0:
                    kept_confs.append(c)

        text = " ".join(kept_words)
        confidence = (
            round(sum(kept_confs) / len(kept_confs) / 100.0, 4)
            if kept_confs
            else None
        )
        return text, confidence


# ======================================================================
# PDF PAGE RASTERIZER (for the scanned-PDF -> OCR path)
# ======================================================================

class PDFRasterizer:
    """Renders PDF pages to images so an :class:`OCREngine` can read them.

    Backed by ``pdf2image`` (poppler). Kept as a small concrete class rather than
    an ABC — a future vision-model path can render differently by supplying its
    own object with the same ``render_pages`` signature.
    """

    def is_available(self) -> bool:
        return pdf2image is not None

    def unavailable_reason(self) -> str:
        if pdf2image is None:
            return (
                "pdf2image is not installed. Install the OCR extras: "
                "pip install -r requirements-ocr.txt"
            )
        return (
            "Poppler was not found (required by pdf2image to rasterize PDFs). "
            "Install it (Debian/Ubuntu: 'apt-get install poppler-utils'; "
            "macOS: 'brew install poppler'; Windows: install poppler and add "
            "its bin/ to PATH)."
        )

    def render_pages(
        self,
        pdf_bytes: bytes,
        dpi: Optional[int] = None,
        page_indices: Optional[List[int]] = None,
    ) -> List["Image.Image"]:
        """Render pages to PIL images.

        ``page_indices`` is a 0-based list; when None, all pages are rendered.
        Raises :class:`OCRUnavailableError` when poppler/pdf2image is missing.
        """
        if pdf2image is None:
            raise OCRUnavailableError(self.unavailable_reason())

        dpi = dpi or get_ocr_dpi()
        try:
            images = pdf2image.convert_from_bytes(pdf_bytes, dpi=dpi)
        except Exception as exc:
            # pdf2image raises PDFInfoNotInstalledError etc. when poppler is
            # missing; treat all render failures as "OCR unavailable" with an
            # actionable message rather than a stack trace.
            raise OCRUnavailableError(
                f"{self.unavailable_reason()} (underlying error: {exc})"
            ) from exc

        if page_indices is None:
            return images
        return [images[i] for i in page_indices if 0 <= i < len(images)]


# ======================================================================
# DEFAULT FACTORIES
# ======================================================================

def get_default_ocr_engine() -> OCREngine:
    """The default local OCR engine for this phase (Tesseract)."""
    return TesseractOCREngine()


def get_default_rasterizer() -> PDFRasterizer:
    return PDFRasterizer()
