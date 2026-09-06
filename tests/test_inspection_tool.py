"""
MRPL Phase 3 — unit tests for the inspection findings tool + verifier.

No network, no Qdrant, no OpenAI, no Ollama, no GPU. The mock LLM provider is
used via the real provider abstraction.
"""

import os

import pytest

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg2://t:t@localhost:5432/t")

from src.tools.inspection_tool import synthesize_inspection_findings
from src.agent.inspection_verifier import InspectionVerifier
from src.schemas.inspection import Severity


@pytest.fixture(autouse=True)
def _mock_provider(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "mock")


_EVIDENCE = [
    {"content": "Visible corrosion on equipment surface.", "page_number": 4,
     "extraction_method": "ocr"},
    {"content": "Weld seam shows minor surface irregularity.", "page_number": 2,
     "extraction_method": "text"},
]


# ----------------------------------------------------------------------
# findings tool
# ----------------------------------------------------------------------

def test_tool_produces_findings_from_explicit_evidence():
    out = synthesize_inspection_findings({"query": "find issues", "evidence": _EVIDENCE})
    assert out["degraded"] is False
    assert len(out["findings"]) == 2
    # Every finding cites a page present in the evidence.
    pages = {e["page_number"] for e in _EVIDENCE}
    assert all(f["page_number"] in pages for f in out["findings"])
    assert out["evidence"] == _EVIDENCE or len(out["evidence"]) == 2


def test_tool_harvests_evidence_from_context():
    context = {
        1: {"tool": "rag_retrieval", "output": _EVIDENCE},
    }
    out = synthesize_inspection_findings({"query": "q", "context": context})
    assert len(out["findings"]) == 2


def test_tool_no_evidence_returns_empty():
    out = synthesize_inspection_findings({"query": "q", "evidence": []})
    assert out["findings"] == []
    assert out["degraded"] is False


def test_tool_reports_degraded_when_offline(monkeypatch):
    import src.tools.inspection_tool as tool_mod
    monkeypatch.setattr(
        tool_mod, "generate_response",
        lambda prompt: '{"degraded": true, "approved": false, "confidence": 0.0}',
    )
    out = synthesize_inspection_findings({"query": "q", "evidence": _EVIDENCE})
    assert out["degraded"] is True
    assert out["findings"] == []


# ----------------------------------------------------------------------
# verifier
# ----------------------------------------------------------------------

def _raw(page=4, severity="HIGH", confidence=0.9, **over):
    base = {
        "title": "t", "description": "d", "severity": severity,
        "evidence": "corrosion", "page_number": page,
        "recommendation": "r", "confidence": confidence,
    }
    base.update(over)
    return base


def test_verifier_accepts_valid_finding():
    valid, verdict = InspectionVerifier().verify(
        [_raw(page=4)], retrieved_pages={4}, page_method={4: "ocr"}, document_id=42
    )
    assert verdict["approved"] is True
    assert len(valid) == 1
    assert valid[0]["finding_id"] == "42-F1"
    assert valid[0]["extraction_method"] == "ocr"
    assert valid[0]["severity"] == Severity.HIGH.value


def test_verifier_rejects_invalid_severity():
    valid, verdict = InspectionVerifier().verify(
        [_raw(severity="SEVERE")], retrieved_pages={4}, page_method={4: "ocr"},
        document_id=1,
    )
    assert verdict["approved"] is False
    assert valid == []
    assert "invalid severity" in verdict["issues"][0]


def test_verifier_rejects_page_not_in_evidence():
    valid, verdict = InspectionVerifier().verify(
        [_raw(page=12)], retrieved_pages={2, 4, 7}, page_method={}, document_id=1,
    )
    assert verdict["approved"] is False
    assert valid == []
    assert "not in the retrieved evidence" in verdict["issues"][0]


def test_verifier_rejects_missing_page_number():
    valid, verdict = InspectionVerifier().verify(
        [_raw(page=None)], retrieved_pages={4}, page_method={4: "ocr"}, document_id=1,
    )
    assert verdict["approved"] is False
    assert "no page_number" in verdict["issues"][0]


def test_verifier_rejects_missing_evidence():
    valid, verdict = InspectionVerifier().verify(
        [_raw(evidence="")], retrieved_pages={4}, page_method={4: "ocr"}, document_id=1,
    )
    assert verdict["approved"] is False
    assert "evidence" in verdict["issues"][0]


def test_verifier_rejects_confidence_out_of_range():
    valid, verdict = InspectionVerifier().verify(
        [_raw(confidence=1.7)], retrieved_pages={4}, page_method={4: "ocr"},
        document_id=1,
    )
    assert verdict["approved"] is False
    assert "confidence" in verdict["issues"][0]


def test_verifier_degraded_fails_closed():
    valid, verdict = InspectionVerifier().verify(
        [_raw()], retrieved_pages={4}, page_method={4: "ocr"}, document_id=1,
        degraded=True,
    )
    assert verdict["approved"] is False
    assert valid == []


def test_verifier_zero_findings_is_approved_clean():
    valid, verdict = InspectionVerifier().verify(
        [], retrieved_pages={4}, page_method={4: "ocr"}, document_id=1,
    )
    assert verdict["approved"] is True
    assert valid == []
    assert verdict["findings_total"] == 0


def test_verifier_mixed_valid_and_invalid_drops_invalid_and_flags():
    valid, verdict = InspectionVerifier().verify(
        [_raw(page=4), _raw(page=99)],
        retrieved_pages={4}, page_method={4: "text"}, document_id=7,
    )
    # One valid finding is returned; the invalid one is dropped + reported.
    assert len(valid) == 1
    assert verdict["approved"] is False
    assert verdict["findings_valid"] == 1
    assert verdict["findings_rejected"] == 1
