#!/usr/bin/env python3
"""Generate Tamara AiQ Fluency Assessment SRS PDF from docs/srs source HTML."""

from __future__ import annotations

import io
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DOCS = ROOT / "docs"
HTML_SRC = DOCS / "SRS-Tamara-AiQ-Fluency-Assessment-v1.0.html"
OUT_DEFAULT = DOCS / "SRS-Tamara-AiQ-Fluency-Assessment-v1.0.pdf"

DESIGN_HTML_SRC = DOCS / "Design-Enhancement-Spec-Tamara-AiQ-v1.0.html"
DESIGN_OUT_DEFAULT = DOCS / "Design-Enhancement-Spec-Tamara-AiQ-v1.0.pdf"


def _chrome_paths() -> list[str]:
    p: list[str] = []
    env = (os.environ.get("CHROME_BIN") or os.environ.get("CHROMIUM_BIN") or "").strip()
    if env:
        p.append(env)
    if os.name == "nt":
        pf = os.environ.get("ProgramFiles", r"C:\Program Files")
        p.append(os.path.join(pf, "Google", "Chrome", "Application", "chrome.exe"))
        p.append(os.path.join(pf, "Microsoft", "Edge", "Application", "msedge.exe"))
    p.extend(
        [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable",
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser",
        ]
    )
    return p


def html_to_pdf_chrome(html_path: Path, out_path: Path) -> bool:
    uri = html_path.resolve().as_uri()
    fd, tmp = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)
    try:
        for chrome in _chrome_paths():
            if not chrome or not os.path.isfile(chrome):
                continue
            cmd = [
                chrome,
                "--headless=new",
                "--disable-gpu",
                "--no-sandbox",
                f"--print-to-pdf={tmp}",
                "--print-to-pdf-no-header",
                uri,
            ]
            try:
                subprocess.run(cmd, capture_output=True, timeout=120, check=False)
            except (OSError, subprocess.TimeoutExpired):
                continue
            if os.path.isfile(tmp) and os.path.getsize(tmp) > 5000:
                out_path.parent.mkdir(parents=True, exist_ok=True)
                os.replace(tmp, str(out_path))
                return True
        return False
    finally:
        if os.path.isfile(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass


def html_to_pdf_reportlab(html_path: Path, out_path: Path) -> None:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer

    raw = html_path.read_text(encoding="utf-8")
    body = re.sub(r"<script[\s\S]*?</script>", "", raw, flags=re.I)
    body = re.sub(r"<style[\s\S]*?</style>", "", body, flags=re.I)
    body = re.sub(r"<br\s*/?>", "\n", body, flags=re.I)
    body = re.sub(r"</(p|div|h[1-4]|li|tr)>", "\n", body, flags=re.I)
    body = re.sub(r"<[^>]+>", "", body)
    body = re.sub(r"&nbsp;", " ", body)
    body = re.sub(r"&amp;", "&", body)
    body = re.sub(r"&lt;", "<", body)
    body = re.sub(r"&gt;", ">", body)
    body = re.sub(r"\n{3,}", "\n\n", body)

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title="Tamara AiQ Fluency Assessment SRS v1.0",
    )
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("H1", parent=styles["Heading1"], fontSize=16, spaceAfter=8, textColor=colors.HexColor("#5300BA"))
    h2 = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=12, spaceBefore=10, spaceAfter=6, textColor=colors.HexColor("#5300BA"))
    body_s = ParagraphStyle("Body", parent=styles["Normal"], fontSize=9, leading=12, alignment=TA_JUSTIFY, spaceAfter=4)
    meta = ParagraphStyle("Meta", parent=styles["Normal"], fontSize=8, textColor=colors.grey, alignment=TA_CENTER)

    story = []
    story.append(Paragraph("Tamara AiQ Fluency Assessment", h1))
    story.append(Paragraph("Software Requirements Specification v1.0", h2))
    story.append(Paragraph(datetime.now(timezone.utc).strftime("%d %B %Y (UTC)"), meta))
    story.append(Spacer(1, 6))

    for block in body.split("\n\n"):
        line = block.strip()
        if not line:
            continue
        if len(line) < 80 and re.match(r"^\d+\.\s", line):
            story.append(Paragraph(line, h2))
        elif len(line) < 70 and line.isupper():
            story.append(Paragraph(line, h2))
        elif line.startswith("FR-") or line.startswith("NFR-") or line.startswith("SEC-"):
            story.append(Paragraph(line, body_s))
        else:
            safe = line.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            story.append(Paragraph(safe, body_s))

    doc.build(story)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(buf.getvalue())


def main() -> int:
  # Usage: generate_srs_pdf.py [out.pdf]
  #        generate_srs_pdf.py --design [out.pdf]
    design_mode = "--design" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--design"]
    src = DESIGN_HTML_SRC if design_mode else HTML_SRC
    default_out = DESIGN_OUT_DEFAULT if design_mode else OUT_DEFAULT
    if not src.is_file():
        print(f"Missing source: {src}", file=sys.stderr)
        return 1
    out = Path(args[0]) if args else default_out
    if html_to_pdf_chrome(src, out):
        print(f"Wrote (Chrome): {out}")
        return 0
    html_to_pdf_reportlab(src, out)
    print(f"Wrote (ReportLab fallback): {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
