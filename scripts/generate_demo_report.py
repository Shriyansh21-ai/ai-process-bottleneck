"""
Generate a small, deterministic SYNTHETIC inspection report for the MRPL demo.

This is NOT a real/confidential MRPL document — every value is invented. It is a
5-page text PDF (no OCR needed, processes quickly) whose content is written to be
relevant to the default analysis query ("identify safety-critical findings") so
the real RAG retrieval surfaces evidence and the pipeline produces findings.

Usage:
    python scripts/generate_demo_report.py [output_path]

Default output: data/demo/mrpl_inspection_report.pdf
"""

import os
import sys
import textwrap

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


# (title, [paragraphs]) per page. Deterministic, synthetic industrial content.
PAGES = [
    (
        "REPORT METADATA AND SURVEY DETAILS",
        [
            "Report reference: MRPL-DEMO-2026-0007 (synthetic sample data).",
            "Location: Refinery Unit 3, crude distillation area.",
            "Date of survey: 12 February 2026. Surveyor: A. Sharma, Level II.",
            "Document control: revision 1, distribution restricted to unit records.",
        ],
    ),
    (
        "SECTION 1 — EQUIPMENT CONDITION",
        [
            "Safety-critical finding requiring attention: pump P-204 casing shows "
            "moderate surface wear and coating breakdown, and the flange gasket "
            "seating is aged.",
            "No active leakage was observed at the time of survey; the condition "
            "should be monitored to prevent deterioration.",
            "Recommendation: monitor the coating and re-inspect at the next "
            "scheduled maintenance window.",
        ],
    ),
    (
        "SECTION 2 — PIPELINE & JOINT INSPECTION",
        [
            "Safety-critical finding requiring attention: weld seam WJ-42 on line "
            "6-P-118 exhibits surface irregularity and a reduced wall thickness "
            "measured by ultrasonic testing.",
            "Continued thinning of the joint could compromise pressure containment "
            "under operating conditions and is safety-relevant.",
            "Recommendation: schedule a detailed fitness-for-service assessment of "
            "the affected joint.",
        ],
    ),
    (
        "SECTION 3 — STRUCTURAL & EQUIPMENT INTEGRITY",
        [
            "Safety-critical finding requiring attention: significant corrosion and "
            "section loss were observed on the support structure and the lower "
            "shell of vessel V-311 near the flange connection.",
            "The affected support is load-bearing; prompt engineering evaluation "
            "of the corrosion is required to assure integrity.",
            "Recommendation: schedule a detailed inspection and maintenance "
            "assessment, and restrict load until the corrosion is evaluated.",
        ],
    ),
    (
        "SECTION 4 — SAFETY OBSERVATIONS",
        [
            "Safety-critical finding requiring attention: the emergency access "
            "walkway has a corroded handrail and a loose grating panel, presenting "
            "a fall hazard to personnel.",
            "A fire-water isolation valve was found partially obstructed, which "
            "could delay emergency response.",
            "Recommendation: rectify the walkway hazards and clear the valve "
            "obstruction without delay.",
        ],
    ),
]


def build_pdf(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    c = canvas.Canvas(path, pagesize=A4)
    width, height = A4

    for title, paragraphs in PAGES:
        y = height - 72
        c.setFont("Helvetica-Bold", 14)
        c.drawString(60, y, title)
        y -= 30
        c.setFont("Helvetica", 11)
        for para in paragraphs:
            for line in textwrap.wrap(para, width=90):
                c.drawString(60, y, line)
                y -= 16
            y -= 8
        c.showPage()

    c.save()


def main() -> None:
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        "data", "demo", "mrpl_inspection_report.pdf"
    )
    build_pdf(out)
    size = os.path.getsize(out)
    print(f"Wrote {out} ({len(PAGES)} pages, {size} bytes)")


if __name__ == "__main__":
    main()
