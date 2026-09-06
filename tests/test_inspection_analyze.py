"""
MRPL Phase 3 — /inspection/analyze endpoint tests.

The RAG ingestion + retrieval boundary (Qdrant/embeddings) and the agent memory
subsystem are stubbed, and ``LLM_PROVIDER=mock`` drives the REAL PlannerAgent /
ToolExecutor / VerifierAgent. No network, OpenAI, Ollama or GPU is required.
Real text PDFs are used for extraction (offline).
"""

import io

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

from src.api.routes.inspection import router as inspection_router
from src.core.auth import get_current_active_user
from src.db.session import get_db
from src.db.models.user import User

from tests.conftest import TestingSessionLocal, _override_get_db  # noqa: F401


_USER = User(id=99, email="inspector@test.local", hashed_password="x",
             is_active=True, is_admin=False)


def make_text_pdf(text="INSPECTION REPORT corrosion observed on equipment surface"):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.drawString(72, 720, text)
    c.showPage()
    c.save()
    return buf.getvalue()


# Deterministic page-tagged evidence returned by the (stubbed) retriever.
_EVIDENCE = [
    {"content": "Visible corrosion is described on the equipment surface.",
     "page_number": 4, "extraction_method": "ocr", "document_id": 42, "score": 0.9},
    {"content": "Weld seam shows a minor surface irregularity.",
     "page_number": 2, "extraction_method": "text", "document_id": 42, "score": 0.8},
]


@pytest.fixture
def ctx(db_session, monkeypatch):
    """Wire a fully offline analyze endpoint; return (client, recorder)."""
    monkeypatch.setenv("LLM_PROVIDER", "mock")

    # Agent memory subsystem -> no-ops (no Qdrant/DB memory needed).
    from src.agent import controller as controller_mod
    monkeypatch.setattr(controller_mod, "retrieve_memory", lambda **kw: [])
    monkeypatch.setattr(controller_mod, "add_memory", lambda **kw: None)

    # RAG ingestion boundary -> deterministic document_id, no embeddings/Qdrant.
    monkeypatch.setattr(
        "src.services.inspection_analysis_service.ingest_extracted_document",
        lambda db, document: {"document_id": 42, "chunks_created": 3,
                              "extraction_method": document.extraction_method},
    )

    # RAG retrieval boundary -> record calls, return page-tagged evidence.
    recorder = {}
    default_evidence = list(_EVIDENCE)

    def fake_retrieve(db, query, limit=5, document_id=None):
        recorder["document_id"] = document_id
        recorder["query"] = query
        return recorder.get("evidence", default_evidence)

    monkeypatch.setattr("src.tools.rag_tool.retrieve_context", fake_retrieve)

    app = FastAPI()
    app.include_router(inspection_router)
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_active_user] = lambda: _USER

    with TestClient(app) as client:
        yield client, recorder
    app.dependency_overrides.clear()


def _analyze(client, pdf=None, query="Identify safety-critical findings"):
    return client.post(
        "/inspection/analyze",
        files={"file": ("report.pdf", pdf or make_text_pdf(), "application/pdf")},
        data={"query": query},
    )


# ----------------------------------------------------------------------
# happy path
# ----------------------------------------------------------------------

def test_analyze_text_document_produces_findings(ctx):
    client, _ = ctx
    resp = _analyze(client)
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["document"]["document_id"] == 42
    assert body["document"]["filename"] == "report.pdf"
    assert body["document"]["page_count"] == 1
    assert body["overall_status"] == "action_required"  # a HIGH finding present
    assert body["verification"]["approved"] is True
    assert body["run_id"]

    assert len(body["findings"]) == 2
    f0 = body["findings"][0]
    assert f0["severity"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
    assert f0["evidence"]
    assert f0["finding_id"] == "42-F1"


def test_page_provenance_is_preserved(ctx):
    client, _ = ctx
    body = _analyze(client).json()
    pages = {f["page_number"] for f in body["findings"]}
    methods = {f["page_number"]: f["extraction_method"] for f in body["findings"]}
    # Findings cite only retrieved pages, with correct extraction method.
    assert pages <= {2, 4}
    assert methods.get(4) == "ocr"
    assert methods.get(2) == "text"


def test_document_id_propagates_to_retrieval(ctx):
    client, recorder = ctx
    _analyze(client)
    # The ingested document_id reached the retrieval tool -> scoped retrieval.
    assert recorder["document_id"] == 42


def test_ocr_provenance_flows_into_findings(ctx):
    client, recorder = ctx
    recorder["evidence"] = [
        {"content": "Scanned page: corrosion visible near the flange.",
         "page_number": 6, "extraction_method": "ocr", "document_id": 42, "score": 0.9},
    ]
    body = _analyze(client).json()
    assert len(body["findings"]) == 1
    assert body["findings"][0]["page_number"] == 6
    assert body["findings"][0]["extraction_method"] == "ocr"


def test_no_evidence_yields_no_findings(ctx):
    client, recorder = ctx
    recorder["evidence"] = []
    body = _analyze(client).json()
    assert body["findings"] == []
    assert body["overall_status"] == "no_findings"
    assert body["verification"]["approved"] is True


# ----------------------------------------------------------------------
# evidence guard at the endpoint level
# ----------------------------------------------------------------------

def test_fabricated_page_is_rejected_by_verification(ctx, monkeypatch):
    client, _ = ctx
    # Force the findings model to cite a page (99) that was never retrieved.
    import json as _json

    def bad_findings(prompt):
        if "Inspection Findings Synthesizer" in prompt:
            return _json.dumps({"findings": [{
                "title": "Fabricated", "description": "d", "severity": "HIGH",
                "evidence": "made up", "page_number": 99,
                "recommendation": "r", "confidence": 0.9,
            }]})
        # Fall back to the real mock for planner/verifier prompts.
        from src.llm.mock_provider import build_mock_response
        return build_mock_response(prompt)

    monkeypatch.setattr("src.tools.inspection_tool.generate_response", bad_findings)

    body = _analyze(client).json()
    assert body["findings"] == []
    assert body["overall_status"] == "verification_failed"
    assert body["verification"]["approved"] is False
    assert body["verification"]["findings_rejected"] == 1


# ----------------------------------------------------------------------
# ingestion failure
# ----------------------------------------------------------------------

def test_rag_ingestion_failure_is_reported(ctx, monkeypatch):
    client, _ = ctx

    def boom(db, document):
        raise RuntimeError("qdrant down")

    monkeypatch.setattr(
        "src.services.inspection_analysis_service.ingest_extracted_document", boom
    )
    body = _analyze(client).json()
    assert body["overall_status"] == "analysis_failed"
    assert body["verification"]["approved"] is False
    assert any("ingestion failed" in i.lower() for i in body["verification"]["issues"])


# ----------------------------------------------------------------------
# malformed input
# ----------------------------------------------------------------------

def test_empty_query_rejected(ctx):
    client, _ = ctx
    resp = client.post(
        "/inspection/analyze",
        files={"file": ("r.pdf", make_text_pdf(), "application/pdf")},
        data={"query": "   "},
    )
    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "invalid_query"


def test_unsupported_file_type_rejected(ctx):
    client, _ = ctx
    resp = client.post(
        "/inspection/analyze",
        files={"file": ("x.exe", b"MZ not a document", "application/octet-stream")},
        data={"query": "analyze"},
    )
    assert resp.status_code == 415
    assert resp.json()["detail"]["code"] == "unsupported_file_type"


# ----------------------------------------------------------------------
# authentication
# ----------------------------------------------------------------------

def test_analyze_requires_authentication(db_session):
    """Without an auth override and no token, the endpoint is protected (401)."""
    app = FastAPI()
    app.include_router(inspection_router)
    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as client:
        resp = client.post(
            "/inspection/analyze",
            files={"file": ("r.pdf", make_text_pdf(), "application/pdf")},
            data={"query": "analyze"},
        )
    app.dependency_overrides.clear()
    assert resp.status_code == 401
