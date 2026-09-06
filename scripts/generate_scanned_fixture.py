"""
Generate a small, deterministic SCANNED-style inspection PDF for OCR validation.

This is NOT a real/confidential document — every value is invented. Unlike
``scripts/generate_demo_report.py`` (which writes a native TEXT PDF), this script
renders each page as a raster IMAGE and embeds it in the PDF, so the PDF has
**no selectable text layer**. That forces the document pipeline down the OCR
path (``pypdf`` reads ~0 characters per page -> the page is treated as scanned).

The teammate validates the REAL OCR path against this fixture on a machine with
Tesseract + Poppler installed. On this dev box (no Tesseract/Poppler) the fixture
can still be *generated* and its scanned-ness verified (the OCR integration test
skips cleanly when the binaries are absent).

Content: 5 pages, one distinct MRPL-style finding area per page, so page-level
provenance can be verified after OCR:

    Page 1  Inspection metadata
    Page 2  Equipment wear
    Page 3  Weld / joint issue
    Page 4  Corrosion
    Page 5  Safety hazard

Usage:
    python scripts/generate_scanned_fixture.py [output_path]

Default output: data/demo/mrpl_scanned_inspection_report.pdf
"""

from __future__ import annotations

import io
import os
import sys

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

# A4 raster canvas at ~150 DPI. Large, high-contrast text so Tesseract reads it
# reliably at the pipeline's default 200-DPI rasterization.
_IMG_W, _IMG_H = 1240, 1754

# (title, [body lines]) per page — deterministic synthetic industrial content.
PAGES = [
    (
        "INSPECTION REPORT METADATA",
        [
            "Report reference: MRPL-SCAN-2026-0042 (synthetic sample).",
            "Location: Refinery Unit 7, crude distillation area.",
            "Date of survey: 03 March 2026.",
            "Surveyor: R. Mehta, Level II.",
            "Document control: revision 1, restricted to unit records.",
        ],
    ),
    (
        "SECTION 1 - EQUIPMENT CONDITION",
        [
            "Finding: pump P-118 casing shows moderate surface wear",
            "and coating breakdown. The gasket seating is aged.",
            "No active leakage observed at the time of survey.",
            "Recommendation: monitor coating and re-inspect at the",
            "next scheduled maintenance window.",
        ],
    ),
    (
        "SECTION 2 - WELD AND JOINT INSPECTION",
        [
            "Finding: weld seam WJ-19 on line 8-P-204 exhibits a",
            "surface irregularity and reduced wall thickness by",
            "ultrasonic testing. Continued thinning could compromise",
            "pressure containment and is safety-relevant.",
            "Recommendation: schedule a fitness-for-service assessment.",
        ],
    ),
    (
        "SECTION 3 - CORROSION AND INTEGRITY",
        [
            "Finding: significant corrosion and section loss observed",
            "on the support structure and lower shell of vessel V-402",
            "near the flange connection. The support is load-bearing.",
            "Recommendation: schedule detailed inspection and restrict",
            "load until the corrosion is evaluated by engineering.",
        ],
    ),
    (
        "SECTION 4 - SAFETY OBSERVATIONS",
        [
            "Finding: the emergency access walkway has a corroded",
            "handrail and a loose grating panel, a fall hazard to",
            "personnel. A fire-water isolation valve was found",
            "partially obstructed, delaying emergency response.",
            "Recommendation: rectify walkway hazards and clear the valve.",
        ],
    ),
]


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    """A scalable font. Prefer a common TrueType, fall back to Pillow's default."""
    for name in ("arial.ttf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    # Pillow >= 10 supports a size argument on the built-in default font.
    return ImageFont.load_default(size=size)


def render_page_image(title: str, lines: list[str]) -> Image.Image:
    """Render one page of text onto a white raster image (no text layer)."""
    img = Image.new("RGB", (_IMG_W, _IMG_H), color="white")
    draw = ImageDraw.Draw(img)

    title_font = _load_font(56)
    body_font = _load_font(40)

    margin = 90
    y = margin
    draw.text((margin, y), title, fill="black", font=title_font)
    y += 110
    draw.line([(margin, y), (_IMG_W - margin, y)], fill="black", width=3)
    y += 50

    for line in lines:
        draw.text((margin, y), line, fill="black", font=body_font)
        y += 70

    # A faint page marker aids visual provenance checks (kept OCR-friendly).
    draw.text((margin, _IMG_H - 120), title.split(" - ")[0], fill="black",
              font=body_font)
    return img


def build_scanned_pdf_bytes() -> bytes:
    """Build the multi-page scanned-style PDF (images only) and return bytes."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4
    for title, lines in PAGES:
        image = render_page_image(title, lines)
        c.drawImage(ImageReader(image), 0, 0, width=width, height=height)
        c.showPage()
    c.save()
    return buf.getvalue()


def main() -> None:
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        "data", "demo", "mrpl_scanned_inspection_report.pdf"
    )
    os.makedirs(os.path.dirname(out), exist_ok=True)
    data = build_scanned_pdf_bytes()
    with open(out, "wb") as fh:
        fh.write(data)
    print(f"Wrote {out} ({len(PAGES)} scanned pages, {len(data)} bytes)")


if __name__ == "__main__":
    main()
