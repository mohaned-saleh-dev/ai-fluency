"""
AiQ session summary PDF: rich HTML + headless Chrome when available, else ReportLab.
"""

from __future__ import annotations

import html
import io
import os
import tempfile
from typing import Any, Dict, List, Optional, Tuple

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from assessment_profiles import position_versus_typical_composite, typical_composite_for_level
from executive_deck_pdf import html_abs_path_to_pdf_bytes
from participant_report import DIMENSION_ORDER, build_report_enrichment

DIMENSION_ROWS = DIMENSION_ORDER


def _esc(s: Any) -> str:
    return html.escape(str(s) if s is not None else "", quote=True)


def _build_report_html(scores: dict, assessment: Optional[dict]) -> str:
    enrich = build_report_enrichment(scores, assessment)
    aiq = scores.get("AiQ_0_100")
    try:
        aiq_s = f"{float(aiq):.1f}" if aiq is not None and aiq != "" else "—"
    except (TypeError, ValueError):
        aiq_s = "—"
    band = scores.get("maturity_band") or "—"
    ass: Dict[str, Any] = dict(assessment) if assessment else {}
    if ass.get("level") and "typical_composite" not in ass:
        ass = {**ass, "typical_composite": typical_composite_for_level(str(ass.get("level")))}
    aiqf: Optional[float] = None
    try:
        if aiq is not None and aiq != "":
            aiqf = float(aiq)
    except (TypeError, ValueError):
        aiqf = None
    pvt = position_versus_typical_composite(aiqf, str(ass.get("level") or "head_of"))
    tc = ass.get("typical_composite") or {}
    tlo, thi = (tc.get("low"), tc.get("high"))
    if isinstance(tlo, (int, float)) and isinstance(thi, (int, float)):
        tlo, thi = float(tlo), float(thi)
        zl, zw = tlo, max(0.0, thi - tlo)
        mlp = max(0.0, min(100.0, aiqf)) if aiqf is not None else 50.0
    else:
        tlo, thi, zl, zw, mlp = 40.0, 60.0, 40.0, 20.0, 50.0
    st = (scores.get("strength_1line") or "").strip()
    rk = (scores.get("risk_1line") or "").strip()
    profile = enrich.get("profile_line") or ""
    band_blurb = (enrich.get("band_blurb") or "").strip()

    # --- Score vs expectation table ---
    score_rows = []
    for g in enrich.get("gaps") or []:
        sc = g.get("actual")
        tgt = g.get("target")
        status = g.get("status") or "on"
        badge_cls = "badge-above" if status == "above" else ("badge-below" if status == "below" else "badge-on")
        rat = (g.get("rationale") or "").strip()
        rat_html = f'<p class="dim-rat">{_esc(rat)}</p>' if rat else ""
        score_rows.append(
            f'<tr class="dim-row dim-row--{status}">'
            f'<td class="dim-id"><b>{_esc(g.get("code"))}</b><br/><span class="dim-name">{_esc(g.get("label"))}</span></td>'
            f'<td class="dim-sc">{_esc(f"{sc:.1f}" if isinstance(sc, (int, float)) else "—")}<span class="dim-of">/10</span></td>'
            f'<td class="dim-tgt">~{_esc(f"{tgt:.1f}" if isinstance(tgt, (int, float)) else "—")}</td>'
            f'<td class="dim-st"><span class="badge {badge_cls}">{_esc(g.get("status_label") or "")}</span></td>'
            f"</tr>"
            + (f'<tr class="dim-rat-row"><td colspan="4">{rat_html}</td></tr>' if rat_html else "")
        )
    score_table = (
        "<table class='score-tbl'><thead><tr>"
        "<th>Dimension</th><th>Your score</th><th>Typical band</th><th>Vs. band</th>"
        "</tr></thead><tbody>"
        + "".join(score_rows)
        + "</tbody></table>"
    )

    # --- Per-dimension coaching detail ---
    detail_blocks: List[str] = []
    for row in enrich.get("coaching_rows") or []:
        code = row.get("code") or ""
        label = row.get("label") or ""
        standing = (row.get("standing") or "").strip()
        focus = (row.get("focus") or "").strip()
        exs = row.get("exercises") or []
        ex_html = ""
        if exs:
            ex_html = "<ul class='ex-list'>" + "".join(f"<li>{_esc(x)}</li>" for x in exs[:2]) + "</ul>"
        detail_blocks.append(
            f'<section class="dim-detail">'
            f'<h3>{_esc(code)} · {_esc(label)}</h3>'
            + (f'<p class="standing">{_esc(standing)}</p>' if standing else "")
            + (f'<p class="focus-lbl"><span class="focus-tag">Focus</span> {_esc(focus)}</p>' if focus else "")
            + ex_html
            + "</section>"
        )
    details_html = "\n".join(detail_blocks)

    # --- Next steps ---
    next_steps = enrich.get("next_steps") or []
    ns_html = ""
    if next_steps:
        ns_html = (
            '<section class="section page-break">'
            '<h2 class="sec-h">Suggested next steps</h2>'
            '<p class="sec-lede">Practical moves for the next 2–4 weeks, grounded in where this conversation showed the most room to grow. '
            "Pick one or two to start; you do not need to do everything at once.</p>"
            "<ol class='steps'>"
            + "".join(f"<li>{_esc(s)}</li>" for s in next_steps)
            + "</ol></section>"
        )

    keep = enrich.get("keep_doing") or []
    keep_html = ""
    if keep:
        keep_html = (
            '<section class="section keep">'
            '<h2 class="sec-h">Strengths to keep</h2>'
            "<ul>"
            + "".join(f"<li>{_esc(k)}</li>" for k in keep)
            + "</ul></section>"
        )

    pull = f'<p class="pull"><span class="pull-tag">Strength</span> {_esc(st)}</p>' if st else ""
    watch = (
        f'<p class="watch"><span class="wlab">Watch</span> {_esc(rk)}</p>' if rk else ""
    )
    pvt_lbl = _esc(pvt.get("label", "")) if pvt.get("key") != "unknown" else "—"
    cap_txt = _esc((tc or {}).get("caption") or "")
    lvl_lbl = _esc(ass.get("level_label") or "this level")
    bmk_html = f"""<div class="bmk">
  <p class="bmk-t">Where you sit vs. others at your level</p>
  <p class="bmk-p">For <b>{lvl_lbl}</b>, a directional composite band is <b>{tlo:.0f}–{thi:.0f}</b> on the 0–100 scale (not a pass/fail line).</p>
  <div class="bmk-rail"><div class="bmk-zone" style="left:{zl}%;width:{zw}%"></div>
  <div class="bmk-tick" style="left:{mlp}%"></div></div>
  <p class="bmk-v"><strong>{_esc(aiq_s)}</strong> — {pvt_lbl}</p>
  <p class="bmk-cap">{cap_txt}</p>
</div>"""
    if pvt.get("key") == "unknown":
        bmk_html = ""

    band_section = ""
    if band_blurb:
        band_section = (
            f'<section class="section band-note">'
            f'<h2 class="sec-h">What {_esc(band)} means for you</h2>'
            f'<p class="sec-lede">{_esc(band_blurb)}</p>'
            f"</section>"
        )

    overview = (
        '<section class="section">'
        '<h2 class="sec-h">What this conversation suggests</h2>'
        '<p class="sec-lede">This report summarizes one AiQ chat — how you described using AI in real work, '
        "scored against six fluency dimensions with weights for your seniority and job family. "
        "It is meant for reflection and coaching, not a hiring decision or final label.</p>"
        + pull
        + watch
        + "</section>"
    )

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"/>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
<style>
@page {{ size: A4; margin: 12mm 14mm; }}
body {{ font-family: 'Plus Jakarta Sans', sans-serif; color: #1a1a1b; background: #fff; font-size: 9pt; line-height: 1.45; margin: 0; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
.page-break {{ page-break-before: always; }}
h1 {{ font-size: 17pt; font-weight: 800; margin: 0 0 2mm; letter-spacing: -0.02em; }}
.sec-h {{ font-size: 11pt; font-weight: 800; margin: 0 0 2.5mm; color: #1a1a1b; }}
.sec-lede {{ font-size: 8.5pt; color: #4a4843; margin: 0 0 3mm; max-width: 68ch; }}
.band {{ display: inline-block; background: #5300ba; color: #fff; font-size: 6.5pt; font-weight: 800; letter-spacing: 0.12em; text-transform: uppercase; padding: 3px 8px; border-radius: 999px; margin-bottom: 3mm; }}
.hero {{ display: flex; gap: 7mm; align-items: flex-start; margin-bottom: 4mm; padding-bottom: 3mm; border-bottom: 1px solid #e8e2f4; }}
.gau {{ text-align: center; min-width: 88px; flex-shrink: 0; }}
.gnum {{ font-size: 28pt; font-weight: 800; color: #5300ba; line-height: 1; }}
.gs {{ font-size: 7pt; color: #6a6875; margin-top: 2px; }}
.profile {{ font-size: 8.5pt; color: #5c5a65; margin: 0 0 2mm; }}
.pull, .watch {{ font-size: 8.5pt; margin: 0 0 2mm; padding: 2mm 2.5mm; border-radius: 6px; }}
.pull {{ background: #f0faf4; border-left: 3px solid #059669; }}
.pull-tag {{ font-size: 6.5pt; font-weight: 800; text-transform: uppercase; color: #059669; margin-right: 2mm; }}
.watch {{ background: #f3effb; border-left: 3px solid #5300ba; }}
.wlab {{ font-size: 6.5pt; font-weight: 800; text-transform: uppercase; color: #5300ba; margin-right: 2mm; }}
.bmk {{ margin: 3mm 0; padding: 3mm; background: #f8f6ff; border-radius: 8px; border: 1px solid #e8e2f4; }}
.bmk-t {{ margin: 0 0 1.5mm; font-size: 7pt; font-weight: 800; text-transform: uppercase; letter-spacing: 0.08em; color: #5300ba; }}
.bmk-p, .bmk-v {{ margin: 0 0 1.5mm; font-size: 8pt; }}
.bmk-cap {{ margin: 0; font-size: 6.5pt; color: #6e6b78; }}
.bmk-rail {{ position: relative; height: 14px; margin: 2mm 0; background: #e4e0ee; border-radius: 7px; }}
.bmk-zone {{ position: absolute; top: 0; height: 14px; background: rgba(150,0,241,0.22); border-radius: 6px; }}
.bmk-tick {{ position: absolute; top: 0; width: 5px; height: 14px; margin-left: -2px; background: #5300ba; border-radius: 2px; }}
.score-tbl {{ width: 100%; border-collapse: collapse; font-size: 8pt; margin: 2mm 0 4mm; }}
.score-tbl th {{ text-align: left; font-size: 6.5pt; text-transform: uppercase; letter-spacing: 0.06em; color: #6e6b78; padding: 1.5mm 2mm; border-bottom: 2px solid #1a1a1b; }}
.score-tbl td {{ padding: 2mm; vertical-align: top; border-bottom: 1px solid #efeaf8; }}
.dim-id {{ width: 32%; }}
.dim-name {{ font-size: 7pt; font-weight: 500; color: #6e6b78; }}
.dim-sc {{ font-size: 11pt; font-weight: 800; color: #5300ba; white-space: nowrap; }}
.dim-of {{ font-size: 7pt; font-weight: 600; color: #9a96a8; }}
.dim-tgt {{ color: #4a4843; white-space: nowrap; }}
.dim-st {{ font-size: 7.5pt; }}
.dim-rat-row td {{ padding-top: 0; border-bottom: 1px solid #e8e2f4; }}
.dim-rat {{ margin: 0 0 2mm; font-size: 7.5pt; color: #4a4843; font-style: italic; }}
.badge {{ display: inline-block; padding: 1px 6px; border-radius: 4px; font-size: 6.5pt; font-weight: 700; }}
.badge-above {{ background: #ecfdf3; color: #047857; }}
.badge-on {{ background: #f3effb; color: #5300ba; }}
.badge-below {{ background: #fff7ed; color: #c2410c; }}
.dim-detail {{ margin: 0 0 3mm; padding: 2.5mm 3mm; border: 1px solid #e8e2f4; border-radius: 8px; page-break-inside: avoid; }}
.dim-detail h3 {{ margin: 0 0 1.5mm; font-size: 8.5pt; font-weight: 800; }}
.standing {{ margin: 0 0 1.5mm; font-size: 7.5pt; color: #4a4843; }}
.focus-lbl {{ margin: 0 0 1mm; font-size: 8pt; }}
.focus-tag {{ font-size: 6.5pt; font-weight: 800; text-transform: uppercase; color: #c2410c; margin-right: 2mm; }}
.ex-list {{ margin: 0; padding-left: 4mm; font-size: 7.5pt; color: #3d3a48; }}
.ex-list li {{ margin-bottom: 1mm; }}
.steps {{ margin: 0; padding-left: 5mm; font-size: 8.5pt; }}
.steps li {{ margin-bottom: 2.5mm; }}
.keep ul {{ margin: 0; padding-left: 4mm; font-size: 8pt; }}
.foot {{ font-size: 7pt; color: #8a8794; margin-top: 5mm; padding-top: 2mm; border-top: 1px solid #e8e2f4; }}
.section {{ margin: 4mm 0; }}
</style></head><body>
<span class="band">{_esc(band)}</span>
<h1>Your AiQ report</h1>
<div class="hero">
  <div class="gau"><div class="gnum">{_esc(aiq_s)}</div><div class="gs">Composite · 0–100</div></div>
  <div>
    <p class="profile"><b>Profile:</b> {_esc(profile) if profile else "—"}</p>
    <p class="profile" style="margin-top:0">Six dimensions below are weighted for this profile. Scores are 0–10 from this chat only.</p>
  </div>
</div>
{bmk_html}
{overview}
{band_section}
<section class="section">
<h2 class="sec-h">Scores by dimension</h2>
<p class="sec-lede">“Typical band” is a directional reference for your level and role — not a target you must hit in one session.</p>
{score_table}
</section>
<section class="section">
<h2 class="sec-h">Deeper notes &amp; how to improve</h2>
<p class="sec-lede">For each area: where you landed, what to focus on, and a concrete practice you can try this week.</p>
{details_html}
</section>
{ns_html}
{keep_html}
<p class="foot">Provisional · reflection and coaching from this conversation only · not a hiring score or final HR label.</p>
</body></html>"""


def _build_reportlab_fallback(scores: dict, assessment: Optional[dict]) -> bytes:
    enrich = build_report_enrichment(scores, assessment)
    st0 = getSampleStyleSheet()
    st0.add(ParagraphStyle(name="T", parent=st0["Normal"], fontSize=8.5, spaceAfter=3, leading=11))
    st0.add(ParagraphStyle(name="H", parent=st0["Heading1"], fontSize=13, spaceAfter=5))
    st0.add(ParagraphStyle(name="H2", parent=st0["Heading2"], fontSize=10, spaceAfter=4))
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        rightMargin=14 * mm,
        leftMargin=14 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
    )
    ass = assessment or {}
    aiq = scores.get("AiQ_0_100", "—")
    prof = enrich.get("profile_line") or f"{ass.get('level_label', '')} · {ass.get('job_family_label', '')}"
    aiq_num = aiq
    try:
        aiq_num = float(aiq) if aiq is not None and aiq != "" else None
    except (TypeError, ValueError):
        aiq_num = None
    pvt2 = position_versus_typical_composite(aiq_num, str(ass.get("level") or "head_of"))
    story = [
        Paragraph(
            f"<b>Your AiQ report</b> &nbsp; {html.escape(str(scores.get('maturity_band', '—')))}",
            st0["H"],
        ),
        Paragraph(f"Composite: {html.escape(str(aiq))} &nbsp;|&nbsp; {html.escape(prof)}", st0["T"]),
        Paragraph(f"<i>{html.escape(pvt2.get('label', '—'))}</i>", st0["T"]),
        Spacer(1, 2 * mm),
    ]
    st_line = (scores.get("strength_1line") or "").strip()
    rk_line = (scores.get("risk_1line") or "").strip()
    if st_line:
        story.append(Paragraph(f"<b>Strength:</b> {html.escape(st_line)}", st0["T"]))
    if rk_line:
        story.append(Paragraph(f"<b>Watch:</b> {html.escape(rk_line)}", st0["T"]))
    blurb = (enrich.get("band_blurb") or "").strip()
    if blurb:
        story.append(Paragraph(f"<b>Band note:</b> {html.escape(blurb)}", st0["T"]))
    story.append(Paragraph("<b>Scores by dimension</b>", st0["H2"]))
    for g in enrich.get("gaps") or []:
        rat = (g.get("rationale") or "").strip()
        story.append(
            Paragraph(
                f"<b>{html.escape(g.get('code', ''))} {html.escape(g.get('label', ''))}</b>: "
                f"{g.get('actual', '—')}/10 (typical ~{g.get('target', '—')}) — "
                f"{html.escape(g.get('status_label', ''))}. "
                f"{html.escape(rat[:400])}",
                st0["T"],
            )
        )
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph("<b>Suggested next steps</b>", st0["H2"]))
    for i, step in enumerate(enrich.get("next_steps") or [], 1):
        story.append(Paragraph(f"{i}. {html.escape(step[:500])}", st0["T"]))
    if enrich.get("keep_doing"):
        story.append(Paragraph("<b>Strengths to keep</b>", st0["H2"]))
        for k in enrich.get("keep_doing") or []:
            story.append(Paragraph(f"• {html.escape(k[:400])}", st0["T"]))
    story.append(Spacer(1, 2 * mm))
    story.append(
        Paragraph(
            "<i>Provisional · for reflection and coaching from this one chat.</i>",
            st0["T"],
        )
    )
    doc.build(story)
    return buf.getvalue()


def build_session_report_pdf_bytes(scores: dict, assessment: Optional[dict] = None) -> bytes:
    if not isinstance(scores, dict):
        scores = {}
    html_s = _build_report_html(scores, assessment)
    fd, path = tempfile.mkstemp(suffix=".html")
    os.close(fd)
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(html_s)
        pdf = html_abs_path_to_pdf_bytes(path)
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass
    if pdf and len(pdf) > 500:
        return pdf
    return _build_reportlab_fallback(scores, assessment)
