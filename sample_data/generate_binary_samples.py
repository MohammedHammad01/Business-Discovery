"""Generates the binary sample inputs (a PDF and a screenshot PNG) from text.

Binary fixtures are generated rather than committed so the repository stays
diff-friendly. Run once after installing the backend requirements:

    python sample_data/generate_binary_samples.py

Produces:
    sample_data/current-process.pdf   -- the procedure document
    sample_data/current-app.png       -- a screenshot of the spreadsheet "system"
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:  # pragma: no cover
    sys.exit("PyMuPDF is required: pip install PyMuPDF")

HERE = Path(__file__).parent

SPREADSHEET_ROWS = [
    ("PR-2026-0417", "Bexley", "Replacement circulation pump", "1,240.00", "Sam Fisher", "Pending", "09/03/2026"),
    ("PR-2026-0418", "Croydon", "LED lighting upgrade (phase 1)", "4,850.00", "Sam Fisher", "Pending", "09/03/2026"),
    ("PR-2026-0419", "Bexley", "Filter cartridges x12", "186.40", "Anita Rao", "Approved", "10/03/2026"),
    ("PR-2026-0420", "Sutton", "Emergency drain clearance", "", "Sam Fisher", "Pending", "10/03/2026"),
    ("PR-2026-0421", "Bexley", "Boiler flue repair - URGENT", "2,300.00", "Sam Fisher", "Pending", "13/03/2026"),
    ("PR-2026-0422", "Croydon", "Signage replacement", "410.00", "Anita Rao", "Approved", "13/03/2026"),
]


def build_pdf() -> Path:
    source = (HERE / "current-process.md").read_text(encoding="utf-8")
    doc = fitz.open()
    page = doc.new_page()
    writer = fitz.TextWriter(page.rect)
    font = fitz.Font("helv")
    bold = fitz.Font("hebo")
    y = 60.0

    for line in source.splitlines():
        stripped = line.strip()
        if y > 770:
            writer.write_text(page)
            page = doc.new_page()
            writer = fitz.TextWriter(page.rect)
            y = 60.0
        if not stripped:
            y += 8
            continue
        is_heading = stripped.startswith("#")
        text = stripped.lstrip("# ").replace("`", "")
        writer.append((56, y), text, font=bold if is_heading else font, fontsize=13 if is_heading else 10)
        y += 20 if is_heading else 14

    writer.write_text(page)
    target = HERE / "current-process.pdf"
    doc.save(target)
    doc.close()
    return target


def build_screenshot() -> Path:
    """A synthetic screenshot of the spreadsheet the client uses today."""
    doc = fitz.open()
    page = doc.new_page(width=1000, height=460)
    font, bold = fitz.Font("helv"), fitz.Font("hebo")
    writer = fitz.TextWriter(page.rect)

    page.draw_rect(fitz.Rect(0, 0, 1000, 46), color=None, fill=(0.13, 0.36, 0.24))
    writer.append((16, 29), "PurchaseRequests.xlsx  -  Shared Drive (Read Only)", font=bold, fontsize=13)

    page.draw_rect(fitz.Rect(0, 46, 1000, 78), color=None, fill=(0.92, 0.94, 0.92))
    headers = ["Ref", "Site", "Description", "Value (GBP)", "Approver", "Status", "Raised"]
    xs = [16, 130, 220, 520, 640, 780, 890]
    for x, header in zip(xs, headers):
        writer.append((x, 68), header, font=bold, fontsize=10)

    y = 104
    for row in SPREADSHEET_ROWS:
        for x, cell in zip(xs, row):
            writer.append((x, y), cell or "-", font=font, fontsize=10)
        page.draw_line(fitz.Point(8, y + 10), fitz.Point(992, y + 10), color=(0.85, 0.87, 0.9), width=0.6)
        y += 34

    writer.append((16, y + 24), "Comment (A. Rao): chased Sam re 0417 again 12/03", font=font, fontsize=9)
    writer.append((16, y + 42), "Comment (A. Rao): 0420 - waiting on price before routing", font=font, fontsize=9)
    writer.write_text(page, color=(0.11, 0.14, 0.19))

    # White header text has to be written separately from the dark body text.
    header_writer = fitz.TextWriter(page.rect)
    header_writer.append((16, 29), "PurchaseRequests.xlsx  -  Shared Drive (Read Only)", font=bold, fontsize=13)
    header_writer.write_text(page, color=(1, 1, 1))

    target = HERE / "current-app.png"
    page.get_pixmap(dpi=110).save(target)
    doc.close()
    return target


if __name__ == "__main__":
    print(f"wrote {build_pdf()}")
    print(f"wrote {build_screenshot()}")
