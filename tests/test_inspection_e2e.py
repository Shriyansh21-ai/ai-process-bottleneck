"""
MRPL Phase 3 — the most important test: the COMPLETE inspection pipeline.

    inspection document
        -> extraction (real DocumentIntelligencePipeline, text PDF)
        -> RAG ingestion/retrieval (boundary stubbed: no Qdrant/embeddings)
        -> PlannerAgent      (REAL, driven by LLM_PROVIDER=mock)
        -> ToolExecutor      (REAL: rag_retrieval -> inspection_findings)
        -> VerifierAgent     (REAL)
        -> InspectionVerifier (REAL, deterministic)
        -> InspectionAnalysis

Only the LLM (mock provider), the RAG ingest/retrieve boundary and the agent
memory subsystem are stubbed — everything else is the production code path,
including AgentRun + step_execution persistence. The AgentController is NOT
faked. Uses LLM_PROVIDER=mock. No network, OpenAI, Ollama or GPU.
"""

import asyncio
import io

import pytest
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

from src.services.inspection_analysis_service import InspectionAnalysisService
from src.db.models.agent_run import AgentRun
from src.db.models.step_execution import StepExecution

from tests.conftest import TestingSessionLocal


def make_text_pdf(text="INSPECTION REPORT corrosion observed; weld seam acceptable"):
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.drawString(72, 720, text)
    c.showPage()
    c.save()
    return buf.getvalue()


_EVIDENCE = [
    {"content": "Significant corrosion observed on the equipment surface.",
     "page_number": 4, "extraction_method": "ocr", "document_id": 77, "score": 0.93},
    {"content": "Weld seam inspection recorded a minor irregularity.",
     "page_number": 3, "extraction_method": "text", "document_id": 77, "score": 0.82},
]


@pytest.fixture(autouse=True)
def _pipeline_env(db_session, monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")

    from src.agent import controller as controller_mod
    monkeypatch.setattr(controller_mod, "retrieve_memory", lambda **kw: [])
    monkeypatch.setattr(controller_mod, "add_memory", lambda **kw: None)

    monkeypatch.setattr(
        "src.services.inspection_analysis_service.ingest_extracted_document",
        lambda db, document: {"document_id": 77, "chunks_created": 4,
                              "extraction_method": document.extraction_method},
    )
    monkeypatch.setattr(
        "src.tools.rag_tool.retrieve_context",
        lambda db, query, limit=5, document_id=None: list(_EVIDENCE),
    )
    # Speed up any (unexpected) tool retries.
    from src.agent import executor as ex
    monkeypatch.setattr(ex, "RETRY_DELAY_SECONDS", 0)


def test_full_inspection_pipeline_end_to_end():
    db = TestingSessionLocal()
    try:
        service = InspectionAnalysisService(db=db, session_id="e2e", user_id=None)
        analysis = asyncio.run(
            service.analyze(
                make_text_pdf(),
                filename="inspection_report.pdf",
                query="Identify safety-critical findings requiring attention.",
            )
        )

        # --- structured findings with provenance -------------------------
        assert analysis.overall_status == "action_required"
        assert analysis.verification.approved is True
        assert len(analysis.findings) == 2

        f = analysis.findings[0]
        assert f.severity.value == "HIGH"
        assert f.page_number == 4
        assert f.extraction_method == "ocr"
        assert f.evidence
        assert 0.0 <= f.confidence <= 1.0
        assert analysis.document.document_id == 77
        assert analysis.run_id is not None

        # --- the REAL agent pipeline actually ran + persisted ------------
        run = db.query(AgentRun).filter(AgentRun.id == analysis.run_id).first()
        assert run is not None
        assert run.status in ("success", "completed")

        steps = (
            db.query(StepExecution)
            .filter(StepExecution.agent_run_id == analysis.run_id)
            .all()
        )
        tools_run = {s.tool_name for s in steps}
        # Proof the genuine executor ran the inspection plan (not a shortcut).
        assert "rag_retrieval" in tools_run
        assert "inspection_findings" in tools_run
        assert all(s.status == "success" for s in steps)
    finally:
        db.close()
