"""
MRPL Phase 5 — inspection report export tests.

Covers the pure report formatter (text + PDF) and the POST /inspection/report
endpoint. Everything runs fully offline (no LLM, network, DB or pipeline): the
report is a deterministic rendering of an already-computed InspectionAnalysis.
"""

import io

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pypdf import PdfReader

from src.api.routes.inspection import router as inspection_router
from src.schemas.inspection import (
    Finding,
    InspectionAnalysis,
    InspectionDocumentInfo,
    InspectionVerification,
)
from src.services.inspection_report import (
    render_report_pdf,
    render_report_text,
    report_filename,
)


def _analysis(**overrides):
    data = dict(
        analysis_id="ins-42-7",
        document=InspectionDocumentInfo(
            document_id=42,
            filename="mrpl_inspection_report.pdf",
            page_count=5,
            extraction_method="mixed",
        ),
        overall_status="action_required",
        findings=[
            Finding(
                finding_id="42-F1",
                title="Corrosion detected on vessel V-311",
                description="Significant corrosion and section loss on the support.",
                severity="HIGH",
                evidence="Visible corrosion is described near the flange connection.",
                page_number=4,
                extraction_method="ocr",
                recommendation="Schedule a detailed inspection and restrict load.",
                confidence=0.91,
            ),
            Finding(
                finding_id="42-F2",
                title="Equipment wear on pump P-204",
                description="Coating breakdown and aged gasket seating.",
                severity="MEDIUM",
                evidence="Pump casing shows moderate surface wear.",
                page_number=2,
                extraction_method="text",
                recommendation="Monitor and re-inspect at the next window.",
                confidence=0.82,
            ),
        ],
        verification=InspectionVerification(
            approved=True, issues=[], findings_total=2, findings_valid=2,
            findings_rejected=0,
        ),
        run_id=7,
    )
    data.update(overrides)
    return InspectionAnalysis(**data)


# ----------------------------------------------------------------------
# text renderer — the content source of truth
# ----------------------------------------------------------------------

def test_report_text_contains_document_information():
    txt = render_report_text(_analysis())
    assert "MRPL INSPECTION ANALYSIS" in txt
    assert "Filename: mrpl_inspection_report.pdf" in txt
    assert "Pages: 5" in txt
    assert "Extraction Method: MIXED" in txt
    assert "Analysis Status: Action required" in txt
    assert "Finding Count: 2" in txt


def test_report_text_contains_every_finding_with_all_fields():
    txt = render_report_text(_analysis())
    # both findings present
    assert "Corrosion detected on vessel V-311" in txt
    assert "Equipment wear on pump P-204" in txt
    # severity
    assert "Severity: HIGH" in txt
    assert "Severity: MEDIUM" in txt
    # evidence
    assert "Visible corrosion is described near the flange connection." in txt
    assert "Pump casing shows moderate surface wear." in txt
    # page provenance + extraction method
    assert "Source: Page 4 • OCR" in txt
    assert "Source: Page 2 • TEXT" in txt
    # confidence
    assert "Confidence: 91%" in txt
    assert "Confidence: 82%" in txt
    # recommendation
    assert "Schedule a detailed inspection and restrict load." in txt
    assert "Monitor and re-inspect at the next window." in txt


def test_report_text_contains_verification_and_workflow():
    txt = render_report_text(_analysis())
    assert "VERIFICATION" in txt
    assert "Verification Status: Approved" in txt
    assert "Valid Findings: 2" in txt
    assert "Rejected Findings: 0" in txt
    assert "Verification Issues: None" in txt
    # agent workflow stages (derived, not fabricated)
    for stage in ("Planner", "RAG Retrieval", "Inspection Findings", "Verifier"):
        assert stage in txt
    assert "Generated locally by MRPL Inspection Intelligence" in txt


def test_report_text_lists_verification_issues_when_rejected():
    txt = render_report_text(_analysis(
        overall_status="verification_failed",
        findings=[],
        verification=InspectionVerification(
            approved=False,
            issues=["page 12 was not in the retrieved evidence"],
            findings_total=1, findings_valid=0, findings_rejected=1,
        ),
    ))
    assert "Verification Status: Requires review" in txt
    assert "Rejected Findings: 1" in txt
    assert "page 12 was not in the retrieved evidence" in txt
    assert "No findings were tied to document evidence." in txt


def test_report_text_never_leaks_internal_identifiers():
    # analysis_id / run_id / document_id are internal — they must not appear as
    # user-facing lines in the report body.
    txt = render_report_text(_analysis())
    assert "ins-42-7" not in txt
    assert "run_id" not in txt.lower()


# ----------------------------------------------------------------------
# PDF renderer
# ----------------------------------------------------------------------

def test_report_pdf_is_valid_and_carries_content():
    pdf = render_report_pdf(_analysis())
    assert isinstance(pdf, bytes)
    assert pdf[:4] == b"%PDF"

    reader = PdfReader(io.BytesIO(pdf))
    assert len(reader.pages) >= 1
    text = " ".join((p.extract_text() or "") for p in reader.pages)
    assert "MRPL INSPECTION ANALYSIS" in text
    assert "Corrosion detected on vessel V-311" in text
    assert "HIGH" in text
    assert "Approved" in text


def test_report_filename_is_safe_and_descriptive():
    assert report_filename(_analysis()) == "mrpl_inspection_report_inspection_report.pdf"
    weird = _analysis(document=InspectionDocumentInfo(
        document_id=1, filename="../../etc/pa ss wd.PDF", page_count=1,
        extraction_method="text",
    ))
    name = report_filename(weird)
    assert "/" not in name and "\\" not in name and " " not in name
    assert name.endswith("_inspection_report.pdf")


# ----------------------------------------------------------------------
# endpoint
# ----------------------------------------------------------------------

def _client():
    app = FastAPI()
    app.include_router(inspection_router)
    return TestClient(app)


def test_report_endpoint_returns_pdf_attachment():
    client = _client()
    resp = client.post("/inspection/report", json=_analysis().model_dump())
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"] == "application/pdf"
    assert "attachment" in resp.headers["content-disposition"]
    assert resp.content[:4] == b"%PDF"

    reader = PdfReader(io.BytesIO(resp.content))
    text = " ".join((p.extract_text() or "") for p in reader.pages)
    assert "Corrosion detected on vessel V-311" in text


def test_report_endpoint_rejects_malformed_body():
    client = _client()
    resp = client.post("/inspection/report", json={"not": "an analysis"})
    assert resp.status_code == 422


def test_report_endpoint_handles_generation_failure(monkeypatch):
    client = _client()

    def boom(analysis):
        raise RuntimeError("render exploded")

    monkeypatch.setattr(
        "src.api.routes.inspection.render_report_pdf", boom
    )
    resp = client.post("/inspection/report", json=_analysis().model_dump())
    assert resp.status_code == 500
    assert resp.json()["detail"]["code"] == "report_failed"
