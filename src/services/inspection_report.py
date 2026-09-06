"""
Inspection report export (MRPL Phase 5).

Turns an already-computed :class:`~src.schemas.inspection.InspectionAnalysis`
into a downloadable, professional report. This module is a pure FORMATTER:

  * it does NOT re-run the pipeline, touch the database, call an LLM, or reach
    the network — it only renders data the caller already holds;
  * it only ever emits user-facing inspection information (document metadata,
    findings, verification, the derived agent workflow). No secrets, tokens,
    connection strings, prompts or stack traces can appear because those fields
    are simply not present on ``InspectionAnalysis``.

Two renderers share one content model:

  * :func:`render_report_text` — plain-text report (the single source of content
    truth; trivially testable and used as the ``.txt`` fallback).
  * :func:`render_report_pdf`  — a styled PDF built with reportlab, which is
    already a repository dependency/pattern (see ``scripts/generate_demo_report``).

The PDF is the preferred download format; the text renderer guarantees every
required field is present regardless of PDF layout.
"""

from __future__ import annotations

import io
import re
from typing import List

from src.schemas.inspection import (
    InspectionAnalysis,
    STATUS_ACTION_REQUIRED,
    STATUS_ANALYSIS_FAILED,
    STATUS_NO_FINDINGS,
    STATUS_REVIEW,
    STATUS_VERIFICATION_FAILED,
)

REPORT_TITLE = "MRPL INSPECTION ANALYSIS"
REPORT_FOOTER = "Generated locally by MRPL Inspection Intelligence"

# Human-readable roll-up status labels (the wire values are terse constants).
_STATUS_LABELS = {
    STATUS_NO_FINDINGS: "No findings",
    STATUS_REVIEW: "Review recommended",
    STATUS_ACTION_REQUIRED: "Action required",
    STATUS_VERIFICATION_FAILED: "Verification failed",
    STATUS_ANALYSIS_FAILED: "Analysis failed",
}

# Canonical agent-workflow stages. These mirror exactly what the frontend
# AgentTrace derives from the real run — they are NOT fabricated events, they
# are the fixed pipeline stages whose completion is implied by a produced
# analysis (a run_id + verification verdict).
_WORKFLOW_STAGES = ("Planner", "RAG Retrieval", "Inspection Findings", "Verifier")


def status_label(overall_status: str) -> str:
    """Map a terse overall-status constant to a presentable label."""
    return _STATUS_LABELS.get(overall_status, overall_status or "Unknown")


def _confidence_pct(confidence: float | None) -> str:
    if confidence is None:
        return "—"
    return f"{round(confidence * 100)}%"


def _source_line(page_number, extraction_method) -> str:
    page = f"Page {page_number}" if page_number is not None else "Page —"
    method = (extraction_method or "").upper()
    return f"{page} • {method}" if method else page


def report_filename(analysis: InspectionAnalysis) -> str:
    """A safe, descriptive download filename derived from the document name."""
    base = analysis.document.filename or "inspection"
    # Strip any extension and keep only filename-safe characters.
    base = base.rsplit(".", 1)[0]
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", base).strip("_") or "inspection"
    return f"{base}_inspection_report.pdf"


# ----------------------------------------------------------------------
# plain-text renderer (content source of truth)
# ----------------------------------------------------------------------

_RULE = "-" * 56


def render_report_text(analysis: InspectionAnalysis) -> str:
    """Render the full inspection report as plain text."""
    doc = analysis.document
    ver = analysis.verification
    lines: List[str] = []

    lines.append(_RULE)
    lines.append(REPORT_TITLE)
    lines.append(_RULE)
    lines.append("")

    # -- document information -------------------------------------------
    lines.append("Document Information")
    lines.append("")
    lines.append(f"Filename: {doc.filename}")
    lines.append("Document Type: Inspection Report")
    lines.append(f"Pages: {doc.page_count}")
    lines.append(f"Extraction Method: {(doc.extraction_method or '').upper() or '—'}")
    lines.append(f"Analysis Status: {status_label(analysis.overall_status)}")
    lines.append(f"Finding Count: {len(analysis.findings)}")
    lines.append("")

    # -- findings -------------------------------------------------------
    lines.append(_RULE)
    lines.append("INSPECTION FINDINGS")
    lines.append(_RULE)
    lines.append("")
    if analysis.findings:
        for i, f in enumerate(analysis.findings, start=1):
            lines.append(f"Finding: {i}")
            lines.append(f"Severity: {f.severity.value}")
            lines.append(f"Title: {f.title}")
            lines.append(f"Description: {f.description}")
            lines.append(f"Evidence: {f.evidence}")
            lines.append(f"Source: {_source_line(f.page_number, f.extraction_method)}")
            lines.append(f"Confidence: {_confidence_pct(f.confidence)}")
            lines.append(f"Recommendation: {f.recommendation}")
            lines.append("")
    else:
        lines.append("No findings were tied to document evidence.")
        lines.append("")

    # -- verification ---------------------------------------------------
    lines.append(_RULE)
    lines.append("VERIFICATION")
    lines.append(_RULE)
    lines.append("")
    lines.append(
        f"Verification Status: {'Approved' if ver.approved else 'Requires review'}"
    )
    lines.append(f"Valid Findings: {ver.findings_valid}")
    lines.append(f"Rejected Findings: {ver.findings_rejected}")
    if ver.issues:
        lines.append("Verification Issues:")
        for issue in ver.issues:
            lines.append(f"  - {issue}")
    else:
        lines.append("Verification Issues: None")
    lines.append("")

    # -- agent workflow -------------------------------------------------
    lines.append(_RULE)
    lines.append("AGENT WORKFLOW")
    lines.append(_RULE)
    lines.append("")
    for stage in _WORKFLOW_STAGES:
        lines.append(stage)
    lines.append("")

    lines.append(_RULE)
    lines.append(REPORT_FOOTER)

    return "\n".join(lines)


# ----------------------------------------------------------------------
# PDF renderer (preferred download format)
# ----------------------------------------------------------------------

# Severity -> accent colour, mirroring the UI severity palette intent.
_SEVERITY_HEX = {
    "LOW": "#2f855a",
    "MEDIUM": "#b7791f",
    "HIGH": "#c05621",
    "CRITICAL": "#c53030",
}


def render_report_pdf(analysis: InspectionAnalysis) -> bytes:
    """Render the inspection report as a styled PDF (bytes)."""
    # Imported lazily so a machine without reportlab can still import this module
    # and use the text renderer.
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        HRFlowable,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )
    from xml.sax.saxutils import escape

    doc = analysis.document
    ver = analysis.verification

    base = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=base["Title"], fontSize=20, spaceAfter=2,
                        textColor=colors.HexColor("#1a202c"))
    section = ParagraphStyle("section", parent=base["Heading2"], fontSize=13,
                             spaceBefore=14, spaceAfter=6,
                             textColor=colors.HexColor("#2b6cb0"))
    label = ParagraphStyle("label", parent=base["Normal"], fontSize=9,
                           textColor=colors.HexColor("#718096"))
    body = ParagraphStyle("body", parent=base["Normal"], fontSize=10,
                          leading=14, alignment=TA_LEFT)
    finding_title = ParagraphStyle("ftitle", parent=base["Heading3"], fontSize=11,
                                   spaceBefore=2, spaceAfter=2)
    small = ParagraphStyle("small", parent=base["Normal"], fontSize=8.5,
                           textColor=colors.HexColor("#718096"))
    footer = ParagraphStyle("footer", parent=base["Normal"], fontSize=8.5,
                            textColor=colors.HexColor("#a0aec0"))
    evidence = ParagraphStyle("evidence", parent=body, fontSize=9.5,
                              leftIndent=8, textColor=colors.HexColor("#4a5568"))

    def esc(value) -> str:
        return escape("" if value is None else str(value))

    story = []
    story.append(Paragraph(REPORT_TITLE, h1))
    story.append(HRFlowable(width="100%", thickness=1,
                            color=colors.HexColor("#cbd5e0")))
    story.append(Spacer(1, 6))

    # -- document information (2-column info table) ---------------------
    story.append(Paragraph("Document Information", section))
    info_rows = [
        ("Filename", doc.filename),
        ("Document Type", "Inspection Report"),
        ("Pages", doc.page_count),
        ("Extraction Method", (doc.extraction_method or "").upper() or "—"),
        ("Analysis Status", status_label(analysis.overall_status)),
        ("Finding Count", len(analysis.findings)),
    ]
    info_table = Table(
        [[Paragraph(k, label), Paragraph(esc(v), body)] for k, v in info_rows],
        colWidths=[45 * mm, 120 * mm],
        hAlign="LEFT",
    )
    info_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(info_table)

    # -- findings -------------------------------------------------------
    story.append(Paragraph("Inspection Findings", section))
    if analysis.findings:
        for i, f in enumerate(analysis.findings, start=1):
            sev = f.severity.value
            accent = colors.HexColor(_SEVERITY_HEX.get(sev, "#718096"))
            header = (
                f'<font color="{_SEVERITY_HEX.get(sev, "#718096")}">'
                f'<b>[{esc(sev)}]</b></font> &nbsp;{esc(f.title)}'
            )
            block = [
                [Paragraph(f"Finding {i}", small)],
                [Paragraph(header, finding_title)],
                [Paragraph(esc(f.description), body)],
                [Paragraph(f"<b>Evidence:</b> {esc(f.evidence)}", evidence)],
                [Paragraph(
                    f"Source: {esc(_source_line(f.page_number, f.extraction_method))}"
                    f" &nbsp;|&nbsp; Confidence: {esc(_confidence_pct(f.confidence))}",
                    small,
                )],
                [Paragraph(f"<b>Recommendation:</b> {esc(f.recommendation)}", body)],
            ]
            t = Table(block, colWidths=[165 * mm], hAlign="LEFT")
            t.setStyle(TableStyle([
                ("LINEBEFORE", (0, 0), (0, -1), 3, accent),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f7fafc")),
            ]))
            story.append(t)
            story.append(Spacer(1, 8))
    else:
        story.append(Paragraph("No findings were tied to document evidence.", body))

    # -- verification ---------------------------------------------------
    story.append(Paragraph("Verification", section))
    story.append(Paragraph(
        f"<b>Verification Status:</b> "
        f"{'Approved' if ver.approved else 'Requires review'}", body))
    story.append(Paragraph(f"<b>Valid Findings:</b> {ver.findings_valid}", body))
    story.append(Paragraph(f"<b>Rejected Findings:</b> {ver.findings_rejected}", body))
    if ver.issues:
        story.append(Paragraph("<b>Verification Issues:</b>", body))
        for issue in ver.issues:
            story.append(Paragraph(f"&bull; {esc(issue)}", evidence))
    else:
        story.append(Paragraph("<b>Verification Issues:</b> None", body))

    # -- agent workflow -------------------------------------------------
    story.append(Paragraph("Agent Workflow", section))
    for stage in _WORKFLOW_STAGES:
        story.append(Paragraph(f"&bull; {esc(stage)}", body))

    story.append(Spacer(1, 14))
    story.append(HRFlowable(width="100%", thickness=0.75,
                            color=colors.HexColor("#e2e8f0")))
    story.append(Spacer(1, 4))
    story.append(Paragraph(REPORT_FOOTER, footer))

    buf = io.BytesIO()
    pdf = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=18 * mm, bottomMargin=18 * mm,
        title="MRPL Inspection Analysis",
    )
    pdf.build(story)
    return buf.getvalue()
