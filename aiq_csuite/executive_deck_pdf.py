"""
Real PDF bytes for the AiQ executive deck.

**Primary path:** headless Chrome prints `static/deck/aiq-executive-summary.html` — same
visual layout as `/deck/executive` and browser Print → Save as PDF.

**Fallback (no Chrome on the host):** ReportLab text pages — plain but usable.
"""

from __future__ import annotations

import io
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from assessment_profiles import (
    DIMENSION_DECK_LABELS,
    build_assessment_block,
)

HERE = os.path.dirname(os.path.abspath(__file__))


def _chrome_binary_paths() -> List[str]:
    p: List[str] = []
    if os.name == "nt":
        p.append(
            os.path.join(
                os.environ.get("ProgramFiles", "C:\\Program Files"),
                "Google",
                "Chrome",
                "Application",
                "chrome.exe",
            )
        )
    p.extend(
        [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable",
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser",
            "/opt/google/chrome/chrome",
        ]
    )
    return p


def html_abs_path_to_pdf_bytes(html_abs: str) -> Optional[bytes]:
    """
    Print any local HTML file to PDF with headless Chrome. Shared with session one-pager.
    """
    if not os.path.isfile(html_abs):
        return None
    uri = Path(os.path.normpath(html_abs)).resolve().as_uri()
    fd, out_path = tempfile.mkstemp(suffix=".pdf")
    os.close(fd)
    try:
        for chrome in _chrome_binary_paths():
            if not chrome or not os.path.isfile(chrome):
                continue
            try:
                r = subprocess.run(
                    [
                        chrome,
                        "--headless",
                        "--disable-gpu",
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                        "--no-pdf-header-footer",
                        f"--print-to-pdf={out_path}",
                        uri,
                    ],
                    capture_output=True,
                    text=True,
                    timeout=90,
                )
            except (OSError, subprocess.TimeoutExpired):
                continue
            if r.returncode == 0 and os.path.getsize(out_path) > 1000:
                with open(out_path, "rb") as f:
                    return f.read()
        return None
    finally:
        try:
            os.unlink(out_path)
        except OSError:
            pass


def _try_build_pdf_via_chrome() -> Optional[bytes]:
    """Renders the slide HTML deck; preserves fonts, @page, and per-slide layout."""
    html_path = os.path.join(HERE, "static", "deck", "aiq-executive-summary.html")
    return html_abs_path_to_pdf_bytes(html_path)


def _styles():
    s = getSampleStyleSheet()
    for name, font, size, sp, color, bold in [
        (
            "DeckTitle",
            "Helvetica-Bold",
            20,
            8,
            colors.HexColor("#1a1a18"),
            True,
        ),
        (
            "DeckH1",
            "Helvetica-Bold",
            12,
            4,
            colors.HexColor("#1a1a18"),
            True,
        ),
        ("DeckH2", "Helvetica-Bold", 10, 2, colors.HexColor("#2a3051"), True),
        (
            "DeckBody",
            "Helvetica",
            9,
            2,
            colors.HexColor("#444c6d"),
            False,
        ),
        (
            "DeckMeta",
            "Helvetica",
            7.5,
            2,
            colors.HexColor("#6e6b64"),
            False,
        ),
        (
            "DeckCode",
            "Helvetica",
            7,
            1,
            colors.HexColor("#6e6b64"),
            False,
        ),
    ]:
        s.add(ParagraphStyle(name=name, parent=s["Normal"], fontName=font, fontSize=size, spaceAfter=sp, textColor=color, leading=size * 1.2))
    return s


def _w_fmt(w: Dict[str, float], order: Tuple[str, ...]) -> str:
    parts = [f"{k} {w.get(k, 0) * 100:.0f}%" for k in order]
    return " / ".join(parts)


def _dim_paras(styles) -> List:
    d5_title = "D5: Clarity, craft & output fit (not brand marketing only)"
    d5_def = (
        "Quality, clarity, and appropriateness of model-assisted <b>work product that others read or rely on</b> "
        "(emails, specs, customer replies, code reviews, etc.). Executive and GMT-heavy roles also cover "
        "external narrative; the dimension is <b>universal in intent</b>, not a marketing department label only."
    )
    d6_title = "D6: Risk & responsible use (everyone has a floor)"
    d6_def = (
        "Data, IP, model/vendor access, and judgment under uncertainty. <b>Every</b> role has a baseline in the <i>same spirit</i> as "
        "org-wide <b>security, data protection, and anti-financial crime</b> training. Deeper third-party and regulator "
        "specifics apply where the role (e.g. risk/legal) or the conversation justifies it."
    )
    out: List = [
        Paragraph("<b>Dimensions in this product (highlights, April 2026)</b>", styles["DeckH1"]),
        Spacer(1, 1 * mm),
        Paragraph(d5_title, styles["DeckH2"]),
        Paragraph(d5_def, styles["DeckBody"]),
        Spacer(1, 2 * mm),
        Paragraph(d6_title, styles["DeckH2"]),
        Paragraph(d6_def, styles["DeckBody"]),
    ]
    return out


def _build_executive_deck_pdf_bytes_reportlab_fallback() -> bytes:
    """Plain A4 text deck when headless Chrome is not available (e.g. some servers)."""
    st = _styles()
    a = build_assessment_block("executive", "general_management")
    w: Dict[str, float] = dict(a.get("weights") or {})
    depth: List[str] = list(a.get("depth_focus") or [])
    depth_lbl = " & ".join(
        DIMENSION_DECK_LABELS.get(d, d) for d in (depth if len(depth) >= 2 else ("D6", "D4"))
    )

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title="AiQ Executive Deck — Tamara",
    )
    story: List[Any] = []

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    # --- Page 1 cover ---
    story.append(Spacer(1, 24 * mm))
    story.append(Paragraph("Tamara", st["DeckMeta"]))
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph("The AiQ Framework", st["DeckTitle"]))
    story.append(Spacer(1, 2 * mm))
    story.append(
        Paragraph(
            "Executive deck — <b>PDF v1.2</b> (product sync, conversational assessment, dimension labels).<br/>"
            "Generated: " + stamp,
            st["DeckBody"],
        )
    )
    story.append(Spacer(1, 6 * mm))
    story.append(
        Paragraph(
            "A structured way to discuss <b>AI fluency (AiQ)</b> in real work: awareness, "
            "steering models, judgment, workflow fit, how outputs read to others, and responsible use — "
            "with <b>role-specific weighting</b> and a short leadership-oriented conversational flow in product.",
            st["DeckBody"],
        )
    )
    story.append(PageBreak())

    # --- Thesis page ---
    story.append(Paragraph("Thesis", st["DeckH1"]))
    story.append(
        Paragraph(
            "AiQ measures <b>how effectively people use and govern generative AI in their work</b> — not a coding quiz. "
            "It is complementary to traditional IQ and EQ. High AiQ: augmentation with real judgment, not unthinking automation.",
            st["DeckBody"],
        )
    )
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph("Composite score", st["DeckH2"]))
    story.append(
        Paragraph(
            "AiQ (0–100) = 10 x sum( weight_i x dimension_i ) with <b>weights fixed in product</b> for level x job family; "
            "maturity band AiQ1–AiQ4 is derived from the composite. Executive roles emphasise D4 (workflows / operating model) "
            "and D6 (governance) — see table below for one reference profile.",
            st["DeckBody"],
        )
    )
    story.append(PageBreak())

    # --- D5 / D6 product alignment ---
    story.extend(_dim_paras(st))
    story.append(PageBreak())

    # --- Reference weights (exemplar) ---
    story.append(Paragraph("Reference profile (example): Executive + General management", st["DeckH1"]))
    story.append(
        Paragraph(
            f"<b>Depth in conversation:</b> the live assessment aims for a light pass across <b>all six</b> areas, with "
            f"extra time on the two <b>highest-weight dimensions for that profile</b> - in this example: {depth_lbl}.",
            st["DeckBody"],
        )
    )
    story.append(Spacer(1, 2 * mm))
    order = ("D1", "D2", "D3", "D4", "D5", "D6")
    row = [""] + [DIMENSION_DECK_LABELS.get(d, d) for d in order]
    wrow = ["Weight"] + [f"{w.get(d, 0) * 100:.0f}%" for d in order]
    t = Table([row, wrow], colWidths=[22 * mm] + [24 * mm] * 6, repeatRows=0)
    t.setStyle(
        TableStyle(
            [
                ("FONTSIZE", (0, 0), (-1, -1), 6.5),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#6e6b64")),
                ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor("#1a1a18")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 2),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#e8e6e1")),
            ]
        )
    )
    story.append(t)
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph("Plain form: " + _w_fmt(w, order), st["DeckCode"]))
    story.append(PageBreak())

    # --- Conversational assessment (pilot) ---
    story.append(Paragraph("Conversational assessment in the product (pilot)", st["DeckH1"]))
    for item in [
        "Self-serve <b>~10 minutes</b>, one clear question at a time; <b>no survey grid</b>.",
        "Aim: <b>broad pass</b> on every dimension, with <b>more depth on two</b> dimensions chosen for that run from "
        "<b>level &times; job family</b> (fixed weights; example depth pair above for exec / GM).",
        "UI topic counts are <b>not</b> a 6/6 completion checklist; the model may close when enough signal exists.",
        "Session purpose: <b>reflection and coaching</b> - a provisional one-page read from the chat, <b>not</b> a hiring pass/fail in this design.",
    ]:
        story.append(Paragraph(f"&bull; {item}", st["DeckBody"]))
        story.append(Spacer(1, 0.5 * mm))
    story.append(Spacer(1, 2 * mm))
    story.append(
        Paragraph(
            "Scoring: model-graded JSON, participant-facing text avoids 'internal assessor' blame language; output can be a "
            "<b>downloaded real PDF</b> from the server in addition to on-screen summary.",
            st["DeckCode"],
        )
    )
    story.append(PageBreak())

    # --- Six dimensions (short) ---
    story.append(Paragraph("Six dimensions (short names)", st["DeckH1"]))
    for d in order:
        story.append(Paragraph(f"<b>{d}</b> {DIMENSION_DECK_LABELS.get(d, d)}", st["DeckBody"]))
    story.append(Spacer(1, 2 * mm))
    story.append(
        Paragraph(
            "Full level-by-level matrix remains in the framework doc; D5 and D6 definitions above match the 2026 product and RAG.",
            st["DeckCode"],
        )
    )
    story.append(Spacer(1, 3 * mm))
    story.append(Paragraph("End of deck.", st["DeckMeta"]))

    doc.build(story)
    return buf.getvalue()


def build_executive_deck_pdf_bytes() -> bytes:
    """
    Full slide layout PDF (Chrome) when possible; else ReportLab fallback.
    """
    b = _try_build_pdf_via_chrome()
    if b:
        return b
    return _build_executive_deck_pdf_bytes_reportlab_fallback()
