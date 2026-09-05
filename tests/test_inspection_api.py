"""
MRPL Phase 2 — /inspection/extract API tests.

Uses TEXT PDFs only (native text path) so no OCR/Tesseract/network is needed.
RAG ingestion is stubbed so no Qdrant/embeddings/OpenAI are required.
"""

import io

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

from src.api.routes.inspection import router as inspection_router
from src.db.session import get_db


def make_text_pdf(text="INSPECTION REPORT weld seam acceptable no defects found"):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.drawString(72, 720, text)
    c.showPage()
    c.save()
    return buf.getvalue()


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(inspection_router)
    app.dependency_overrides[get_db] = lambda: iter([None])
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_extract_text_pdf_no_ingest(client):
    resp = client.post(
        "/inspection/extract",
        files={"file": ("report.pdf", make_text_pdf(), "application/pdf")},
        data={"ingest": "false"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["filename"] == "report.pdf"
    assert body["document_type"] == "pdf"
    assert body["extraction_method"] == "text"
    assert body["page_count"] == 1
    assert "INSPECTION REPORT" in body["text_preview"]
    assert body["pages"][0]["page_number"] == 1
    assert body["ingestion"]["status"] == "skipped"
    assert body["document_id"]
    # Full text must not be dumped in the response.
    assert "text" not in body


def test_extract_unsupported_type_returns_415(client):
    resp = client.post(
        "/inspection/extract",
        files={"file": ("x.exe", b"MZ\x90\x00 not a document", "application/octet-stream")},
        data={"ingest": "false"},
    )
    assert resp.status_code == 415
    assert resp.json()["detail"]["code"] == "unsupported_file_type"


def test_extract_with_ingest_success(client, monkeypatch):
    monkeypatch.setattr(
        "src.api.routes.inspection.ingest_extracted_document",
        lambda db, document: {"document_id": 7, "chunks_created": 2,
                              "extraction_method": "text"},
    )
    resp = client.post(
        "/inspection/extract",
        files={"file": ("r.pdf", make_text_pdf(), "application/pdf")},
        data={"ingest": "true"},
    )
    assert resp.status_code == 200, resp.text
    ingestion = resp.json()["ingestion"]
    assert ingestion["status"] == "success"
    assert ingestion["chunks_created"] == 2


def test_extract_with_ingest_failure_is_reported_not_fatal(client, monkeypatch):
    def boom(db, document):
        raise RuntimeError("qdrant down")

    monkeypatch.setattr(
        "src.api.routes.inspection.ingest_extracted_document", boom
    )
    resp = client.post(
        "/inspection/extract",
        files={"file": ("r.pdf", make_text_pdf(), "application/pdf")},
        data={"ingest": "true"},
    )
    # Extraction still succeeded; ingestion failure is surfaced, not a 500.
    assert resp.status_code == 200, resp.text
    ingestion = resp.json()["ingestion"]
    assert ingestion["status"] == "failed"
    assert ingestion["code"] == "rag_ingestion_failed"
