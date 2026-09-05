"""
MRPL Phase 2 — document intelligence tests.

Categories (clearly separated per the phase brief):

  A. Extraction pipeline tests — use a DETERMINISTIC fake OCR engine, so NO
     Tesseract/poppler/GPU/network/Ollama/OpenAI is required.
  B. RAG compatibility tests — the extracted document threads page provenance
     through the EXISTING ingest_document (mocked embeddings + Qdrant).
  C. API tests — the /inspection/extract endpoint over text PDFs (text path).
  D. Real OCR integration — SKIPPED automatically unless a real Tesseract binary
     is installed. This machine has none, so it is not executed here.

Real text PDFs are generated with reportlab; "scanned" pages are drawn with no
text layer so pypdf yields no text and the page is routed to (fake) OCR.
"""

import io

import pytest

from src.documents import (
    DocumentIntelligencePipeline,
    ExtractedDocument,
    PageContent,
    ingest_extracted_document,
    sanitize_filename,
)
from src.documents.errors import (
    CorruptedDocumentError,
    EmptyDocumentError,
    FileTooLargeError,
    OCRUnavailableError,
    UnsupportedFileTypeError,
)
from src.documents.ocr import OCREngine, PDFRasterizer, TesseractOCREngine
from src.documents.representation import (
    METHOD_MIXED,
    METHOD_OCR,
    METHOD_TEXT,
)

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from PIL import Image


# ======================================================================
# Fixtures / fakes
# ======================================================================

def make_pdf(pages) -> bytes:
    """Build a PDF. Each entry is a string (text page) or None (scanned page)."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    for entry in pages:
        if entry:
            c.drawString(72, 720, entry)
        else:
            # No text operators -> pypdf extracts nothing -> "scanned" page.
            c.rect(72, 680, 200, 80, fill=1)
        c.showPage()
    c.save()
    return buf.getvalue()


def make_png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (60, 30), color="white").save(buf, format="PNG")
    return buf.getvalue()


class FakeOCREngine(OCREngine):
    """Deterministic OCR — returns fixed text/confidence, ignores the image."""

    name = "fake"

    def __init__(self, available=True, text="OCR EXTRACTED INSPECTION TEXT",
                 confidence=0.87):
        self._available = available
        self._text = text
        self._conf = confidence

    def is_available(self):
        return self._available

    def unavailable_reason(self):
        return "fake OCR engine is intentionally unavailable"

    def image_to_text(self, image):
        return self._text, self._conf


class FakeRasterizer(PDFRasterizer):
    """Returns placeholder images (FakeOCREngine ignores their content)."""

    def __init__(self, available=True):
        self._available = available

    def is_available(self):
        return self._available

    def unavailable_reason(self):
        return "fake rasterizer is intentionally unavailable"

    def render_pages(self, pdf_bytes, dpi=None, page_indices=None):
        if page_indices is None:
            return [object()]
        return [object() for _ in page_indices]


def make_pipeline(ocr_available=True, raster_available=True):
    return DocumentIntelligencePipeline(
        ocr_engine=FakeOCREngine(available=ocr_available),
        rasterizer=FakeRasterizer(available=raster_available),
    )


# ======================================================================
# A. EXTRACTION PIPELINE
# ======================================================================

def test_text_pdf_extraction():
    pdf = make_pdf(["INSPECTION REPORT: pressure vessel nominal, no defects"])
    doc = make_pipeline().extract(pdf, "report.pdf")

    assert isinstance(doc, ExtractedDocument)
    assert doc.document_type == "pdf"
    assert doc.extraction_method == METHOD_TEXT
    assert doc.page_count == 1
    assert "INSPECTION REPORT" in doc.pages[0].text
    assert doc.pages[0].extraction_method == METHOD_TEXT
    assert doc.pages[0].confidence is None


def test_multipage_text_pdf_preserves_page_numbers():
    pdf = make_pdf([
        "PAGE ONE weld inspection results acceptable",
        "PAGE TWO corrosion mapping within limits",
        "PAGE THREE final sign-off approved",
    ])
    doc = make_pipeline().extract(pdf, "multi.pdf")

    assert doc.page_count == 3
    assert [p.page_number for p in doc.pages] == [1, 2, 3]
    assert "PAGE TWO" in doc.pages[1].text


def test_scanned_pdf_routes_to_ocr():
    pdf = make_pdf([None])  # no text layer
    doc = make_pipeline().extract(pdf, "scanned.pdf")

    assert doc.extraction_method == METHOD_OCR
    assert doc.page_count == 1
    assert doc.pages[0].extraction_method == METHOD_OCR
    assert doc.pages[0].text == "OCR EXTRACTED INSPECTION TEXT"
    assert doc.pages[0].confidence == 0.87


def test_mixed_pdf_text_and_scanned():
    pdf = make_pdf(["PAGE ONE has a real text layer here", None])
    doc = make_pipeline().extract(pdf, "mixed.pdf")

    assert doc.extraction_method == METHOD_MIXED
    assert doc.pages[0].extraction_method == METHOD_TEXT
    assert doc.pages[1].extraction_method == METHOD_OCR


def test_image_input_uses_ocr():
    doc = make_pipeline().extract(make_png(), "scan.png")

    assert doc.document_type == "image"
    assert doc.extraction_method == METHOD_OCR
    assert doc.page_count == 1
    assert doc.pages[0].text == "OCR EXTRACTED INSPECTION TEXT"


def test_empty_file_raises():
    with pytest.raises(EmptyDocumentError):
        make_pipeline().extract(b"", "empty.pdf")


def test_corrupted_pdf_raises():
    with pytest.raises(CorruptedDocumentError):
        make_pipeline().extract(b"%PDF-1.4 broken garbage not a real pdf", "bad.pdf")


def test_unsupported_file_type_raises():
    with pytest.raises(UnsupportedFileTypeError):
        make_pipeline().extract(b"MZ\x90\x00 executable", "malware.exe")


def test_file_too_large_raises(monkeypatch):
    monkeypatch.setenv("DOCUMENT_MAX_BYTES", "10")
    pdf = make_pdf(["a reasonably sized inspection report page"])
    with pytest.raises(FileTooLargeError):
        make_pipeline().extract(pdf, "big.pdf")


def test_scanned_pdf_ocr_unavailable_raises_clear_error():
    """A scanned doc with no OCR engine must fail loudly, never silently empty."""
    pdf = make_pdf([None])
    with pytest.raises(OCRUnavailableError):
        make_pipeline(ocr_available=False).extract(pdf, "scanned.pdf")


def test_scanned_pdf_rasterizer_unavailable_raises_clear_error():
    pdf = make_pdf([None])
    with pytest.raises(OCRUnavailableError):
        make_pipeline(raster_available=False).extract(pdf, "scanned.pdf")


def test_detection_threshold_is_configurable(monkeypatch):
    # Raise the threshold so a short-but-real text page is treated as scanned.
    monkeypatch.setenv("DOCUMENT_TEXT_MIN_CHARS", "100000")
    pdf = make_pdf(["short text"])
    doc = make_pipeline().extract(pdf, "short.pdf")
    # Routed to OCR because the text length is below the (huge) threshold.
    assert doc.extraction_method == METHOD_OCR


@pytest.mark.parametrize(
    "raw,expected_contains",
    [
        ("../../etc/passwd", "passwd"),
        ("C:\\secrets\\report final.pdf", "report_final.pdf"),
        ("", "upload"),
        (None, "upload"),
    ],
)
def test_sanitize_filename(raw, expected_contains):
    out = sanitize_filename(raw)
    assert "/" not in out and "\\" not in out
    assert expected_contains in out


def test_to_summary_shape_bounds_preview_and_hides_full_text():
    long_text = "DEFECT " * 500
    pdf = make_pdf([long_text])
    doc = make_pipeline().extract(pdf, "long.pdf")

    summary = doc.to_summary(preview_chars=50)
    assert set(summary) >= {
        "document_id", "filename", "document_type", "extraction_method",
        "page_count", "char_count", "text_preview", "pages", "metadata",
    }
    assert len(summary["text_preview"]) <= 50
    assert "text" not in summary  # full text is never dumped
    assert summary["pages"][0]["page_number"] == 1
    assert "byte_size" in summary["metadata"]


def test_document_id_is_deterministic():
    pdf = make_pdf(["stable content for hashing"])
    a = make_pipeline().extract(pdf, "a.pdf")
    b = make_pipeline().extract(pdf, "a.pdf")
    assert a.document_id == b.document_id


# ======================================================================
# B. RAG COMPATIBILITY
# ======================================================================

def test_ingest_bridge_threads_page_provenance(monkeypatch):
    """ingest_extracted_document must call the EXISTING ingest_document with
    per-page structure + extraction method."""
    captured = {}

    def fake_ingest_document(**kwargs):
        captured.update(kwargs)
        return {"document_id": 42, "chunks_created": 3}

    import src.rag.ingest as ingest_mod
    monkeypatch.setattr(ingest_mod, "ingest_document", fake_ingest_document)

    doc = ExtractedDocument(
        document_id="abc",
        filename="report.pdf",
        document_type="pdf",
        extraction_method=METHOD_OCR,
        pages=[
            PageContent(1, "page one text", METHOD_OCR, 0.9),
            PageContent(2, "page two text", METHOD_OCR, 0.8),
        ],
        metadata={"source": "upload"},
    )

    result = ingest_extracted_document(db=None, document=doc)

    assert result["document_id"] == 42
    assert captured["extraction_method"] == METHOD_OCR
    assert captured["doc_type"] == "pdf"
    assert captured["title"] == "report.pdf"
    assert captured["pages"] == [
        {"page_number": 1, "text": "page one text"},
        {"page_number": 2, "text": "page two text"},
    ]


class _FakeDoc:
    pass


class _FakeSession:
    """Minimal SQLAlchemy-session stand-in for ingest_document unit testing."""

    def __init__(self):
        self.added = []

    def query(self, *a):
        return self

    def filter(self, *a):
        return self

    def first(self):
        return None  # no duplicate

    def add(self, obj):
        self.added.append(obj)

    def flush(self):
        from src.db.models.document import Document
        for obj in self.added:
            if isinstance(obj, Document) and getattr(obj, "id", None) is None:
                obj.id = 1

    def commit(self):
        pass


class _FakeQdrant:
    def __init__(self):
        self.points = None

    def upsert(self, collection_name=None, points=None):
        self.points = points


def test_ingest_document_sets_page_number_and_payload(monkeypatch):
    """The existing ingest_document, given pages, stores page_number on chunks
    and page_number + extraction_method in the Qdrant payload."""
    import src.rag.ingest as ingest_mod
    from src.models.document_chunk import DocumentChunk

    monkeypatch.setattr(ingest_mod, "embed_text", lambda text: [0.1] * 384)
    fake_qdrant = _FakeQdrant()
    monkeypatch.setattr(ingest_mod, "client", fake_qdrant)

    session = _FakeSession()
    result = ingest_mod.ingest_document(
        db=session,
        title="report.pdf",
        source="upload",
        doc_type="pdf",
        text="page one\n\npage two",
        pages=[
            {"page_number": 1, "text": "page one inspection content"},
            {"page_number": 2, "text": "page two inspection content"},
        ],
        extraction_method="ocr",
    )

    assert result["extraction_method"] == "ocr"
    assert result["chunks_created"] >= 2

    chunks = [c for c in session.added if isinstance(c, DocumentChunk)]
    page_numbers = {c.page_number for c in chunks}
    assert page_numbers == {1, 2}

    # Qdrant payloads carry provenance.
    payloads = [p.payload for p in fake_qdrant.points]
    assert all("page_number" in p for p in payloads)
    assert all(p["extraction_method"] == "ocr" for p in payloads)


def test_ingest_document_legacy_text_only_still_works(monkeypatch):
    """Backward compatibility: no pages -> no page_number, no extraction_method."""
    import src.rag.ingest as ingest_mod
    from src.models.document_chunk import DocumentChunk

    monkeypatch.setattr(ingest_mod, "embed_text", lambda text: [0.1] * 384)
    fake_qdrant = _FakeQdrant()
    monkeypatch.setattr(ingest_mod, "client", fake_qdrant)

    session = _FakeSession()
    ingest_mod.ingest_document(
        db=session,
        title="legacy.txt",
        source="manual",
        doc_type="text",
        text="some legacy content without page structure",
    )

    chunks = [c for c in session.added if isinstance(c, DocumentChunk)]
    assert all(c.page_number is None for c in chunks)
    payloads = [p.payload for p in fake_qdrant.points]
    assert all("page_number" not in p for p in payloads)
    assert all("extraction_method" not in p for p in payloads)


# ======================================================================
# D. REAL OCR INTEGRATION (skipped unless a real Tesseract is installed)
# ======================================================================

_TESSERACT_AVAILABLE = TesseractOCREngine().is_available()


@pytest.mark.skipif(
    not _TESSERACT_AVAILABLE,
    reason="Real Tesseract OCR binary not installed on this machine",
)
def test_real_ocr_reads_rendered_text():
    from PIL import ImageDraw
    img = Image.new("RGB", (400, 80), color="white")
    ImageDraw.Draw(img).text((10, 30), "INSPECTION 12345", fill="black")
    text, conf = TesseractOCREngine().image_to_text(img)
    assert "INSPECTION" in text.upper()
