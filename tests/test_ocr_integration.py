"""
MRPL Phase 6 — real OCR integration (scanned-PDF) validation.

Three layers, so this file is useful on BOTH a bare dev box and the teammate's
capable machine:

  1. Fixture sanity (always runs): the scanned fixture really has no text layer
     and is 5 pages — i.e. it will genuinely exercise the OCR path.
  2. Deterministic routing (always runs): with a FAKE OCR engine + rasterizer,
     prove the pipeline routes the scanned fixture to OCR and preserves per-page
     provenance — no Tesseract/Poppler/network needed.
  3. REAL OCR (skip-gated): only runs when a real Tesseract binary AND Poppler
     are installed. This is the check the teammate performs. It is skipped
     cleanly on machines without the binaries, so the full suite stays portable.

Ollama is NOT involved here — OCR and LLM validation are separate concerns.
"""

import io
import os
from shutil import which

import pytest
from pypdf import PdfReader

from src.documents import DocumentIntelligencePipeline
from src.documents.ocr import TesseractOCREngine
from src.documents.representation import METHOD_OCR

from scripts.generate_scanned_fixture import build_scanned_pdf_bytes, PAGES

# Import the deterministic fakes already used by the Phase 2 extraction tests
# instead of redefining them.
from tests.test_document_intelligence import FakeOCREngine, FakeRasterizer


_FIXTURE_PATH = os.path.join("data", "demo", "mrpl_scanned_inspection_report.pdf")


def _fixture_bytes() -> bytes:
    """The committed scanned fixture, or a freshly built one (both identical)."""
    if os.path.exists(_FIXTURE_PATH):
        with open(_FIXTURE_PATH, "rb") as fh:
            return fh.read()
    return build_scanned_pdf_bytes()


# ----------------------------------------------------------------------
# real-OCR availability gate (Tesseract binary AND Poppler on PATH)
# ----------------------------------------------------------------------

def _tesseract_available() -> bool:
    return TesseractOCREngine().is_available()


def _poppler_available() -> bool:
    # The pipeline calls pdf2image.convert_from_bytes WITHOUT poppler_path, so
    # poppler must be discoverable on PATH exactly as pdf2image resolves it.
    try:
        import pdf2image  # noqa: F401
    except ImportError:
        return False
    return bool(which("pdftoppm") or which("pdftocairo"))


_OCR_STACK_AVAILABLE = _tesseract_available() and _poppler_available()
_SKIP_REASON = (
    "Real OCR stack unavailable "
    f"(tesseract={_tesseract_available()}, poppler={_poppler_available()}). "
    "Install Tesseract + Poppler to run the real OCR integration test."
)


# ----------------------------------------------------------------------
# 1. fixture sanity (always runs)
# ----------------------------------------------------------------------

def test_scanned_fixture_is_five_pages_with_no_text_layer():
    reader = PdfReader(io.BytesIO(_fixture_bytes()))
    assert len(reader.pages) == len(PAGES) == 5
    # Every page's native text layer is (near) empty -> pipeline routes to OCR.
    for page in reader.pages:
        assert len((page.extract_text() or "").strip()) < 20


# ----------------------------------------------------------------------
# 2. deterministic routing with fake OCR (always runs — no binaries needed)
# ----------------------------------------------------------------------

def test_scanned_fixture_routes_to_ocr_with_fake_engine():
    pipeline = DocumentIntelligencePipeline(
        ocr_engine=FakeOCREngine(text="OCR TEXT FOR SCANNED PAGE", confidence=0.9),
        rasterizer=FakeRasterizer(),
    )
    doc = pipeline.extract(_fixture_bytes(), filename="mrpl_scanned_inspection_report.pdf")

    # Doc-level + per-page method is OCR (no native text layer existed).
    assert doc.extraction_method == METHOD_OCR
    assert doc.page_count == 5
    assert [p.page_number for p in doc.pages] == [1, 2, 3, 4, 5]
    assert all(p.extraction_method == METHOD_OCR for p in doc.pages)
    assert all(p.text.strip() for p in doc.pages)


# ----------------------------------------------------------------------
# 3. REAL OCR (skip-gated on Tesseract + Poppler)
# ----------------------------------------------------------------------

@pytest.mark.skipif(not _OCR_STACK_AVAILABLE, reason=_SKIP_REASON)
def test_real_ocr_pipeline_on_scanned_fixture():
    """Run the REAL document pipeline (Tesseract + Poppler) on the fixture.

    Verifies OCR selection, page count, non-empty OCR text, page numbering,
    per-page extraction_method='ocr', and that page-level provenance survives.
    """
    doc = DocumentIntelligencePipeline().extract(
        _fixture_bytes(), filename="mrpl_scanned_inspection_report.pdf"
    )

    # 3) OCR was selected (no native text layer existed).
    assert doc.extraction_method == METHOD_OCR
    # 4) page count preserved.
    assert doc.page_count == 5
    # 5) non-empty OCR text overall.
    combined = " ".join(p.text for p in doc.pages)
    assert combined.strip(), "real OCR produced no text"
    # 6) page numbers are the ordered 1..5.
    assert [p.page_number for p in doc.pages] == [1, 2, 3, 4, 5]
    # 7) every page is tagged as OCR-extracted.
    assert all(p.extraction_method == METHOD_OCR for p in doc.pages)
    # 8) provenance survives: at least one recognizable synthetic token appears.
    upper = combined.upper()
    assert any(tok in upper for tok in
               ("INSPECTION", "CORROSION", "WELD", "PUMP", "VESSEL", "SAFETY")), (
        f"real OCR text did not contain any expected token: {combined[:200]!r}"
    )
    # per-page OCR yields confidence values (Tesseract reports them).
    assert any(p.confidence is not None for p in doc.pages)
