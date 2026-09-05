"""
Document-intelligence configuration (MRPL Phase 2).

Env-var driven, matching the existing project convention (see ``src.config``).
Every value has a safe default so the layer works out of the box.
"""

import os

# Allowed upload extensions (lower-case, no dot). PDFs plus common raster images.
_ALLOWED_EXTENSIONS = {
    "pdf",
    "png", "jpg", "jpeg", "tif", "tiff", "bmp", "webp",
}
_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "tif", "tiff", "bmp", "webp"}


def get_allowed_extensions() -> set:
    return set(_ALLOWED_EXTENSIONS)


def get_image_extensions() -> set:
    return set(_IMAGE_EXTENSIONS)


def get_document_max_bytes() -> int:
    """Max accepted upload size (``DOCUMENT_MAX_BYTES``, default 20 MiB).

    NOTE: the global :class:`BodySizeLimitMiddleware` (``MAX_REQUEST_BYTES``,
    default 1 MiB) runs first. To accept real scanned reports, raise
    ``MAX_REQUEST_BYTES`` to at least ``DOCUMENT_MAX_BYTES`` for the deployment.
    """
    try:
        value = int(os.getenv("DOCUMENT_MAX_BYTES", str(20 * 1024 * 1024)))
        return value if value > 0 else 20 * 1024 * 1024
    except (TypeError, ValueError):
        return 20 * 1024 * 1024


def get_text_min_chars() -> int:
    """Per-page char threshold below which a page is treated as scanned.

    Deterministic heuristic (no ML): a native text layer yields far more than a
    handful of characters; a scanned image page yields ~0 from pypdf.
    Configurable via ``DOCUMENT_TEXT_MIN_CHARS`` (default 20).
    """
    try:
        value = int(os.getenv("DOCUMENT_TEXT_MIN_CHARS", "20"))
        return value if value >= 0 else 20
    except (TypeError, ValueError):
        return 20


def get_ocr_dpi() -> int:
    """Rasterization DPI for OCR (``DOCUMENT_OCR_DPI``, default 200)."""
    try:
        value = int(os.getenv("DOCUMENT_OCR_DPI", "200"))
        return value if value > 0 else 200
    except (TypeError, ValueError):
        return 200


def get_ocr_language() -> str:
    """Tesseract language(s) (``DOCUMENT_OCR_LANG``, default ``eng``)."""
    return os.getenv("DOCUMENT_OCR_LANG", "eng").strip() or "eng"


def get_preview_chars() -> int:
    """How many chars of extracted text to return in API previews (default 500)."""
    try:
        value = int(os.getenv("DOCUMENT_PREVIEW_CHARS", "500"))
        return value if value > 0 else 500
    except (TypeError, ValueError):
        return 500
