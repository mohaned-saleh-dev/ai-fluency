"""
One-page AiQ session summary as PDF: HTML + headless Chrome when available, else ReportLab.
"""

from __future__ import annotations

import html
import io
import os
import tempfile
from typing import Any, Dict, List, Optional, Tuple

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from assessment_profiles import position_versus_typical_composite, typical_composite_for_level
from executive_deck_pdf import html_abs_path_to_pdf_bytes

DIMENSION_ROWS: List[Tuple[str, str]] = [
    ("D1", "Awareness & opportunity"),
    ("D2", "Prompts & comms"),
    ("D3", "Critical judgment"),
    ("D4", "Workflows & org design"),
    ("D5", "Clarity, craft & output fit"),
    ("D6", "Risk & responsible use"),
]


def _esc(s: Any) -> str:
    return html.escape(str(s) if s is not None else "", quote=True)


def _build_onepage_html(scores: dict, assessment: Optional[dict]) -> str:
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
    wmap = (ass.get("weights") or {}) if isinstance(ass, dict) else {}
    st = (scores.get("strength_1line") or "").strip()
    rk = (scores.get("risk_1line") or "").strip()
    profile = " · ".join(
        x for x in (ass.get("level_label") or "", ass.get("job_family_label") or "") if x
    )
    grid_items = []
    for d, name in DIMENSION_ROWS:
        b = scores.get(d)
        if not isinstance(b, dict):
            b = {}
        sc = b.get("score")
        wt = wmap.get(d)
        wpart = f' <span class="w">({int(float(wt) * 100)}% w)</span>' if isinstance(wt, (int, float)) else ""
        scs = f"{_esc(sc)}/10" if sc is not None and sc != "" else "—/10"
        grid_items.append(
            f'<div class="dcell"><span class="dtitle">{_esc(d)} · {_esc(name)}</span>{wpart} '
            f'<span class="dsc">{scs}</span><div class="cl"></div></div>'
        )
    grid_html = "\n".join(grid_items)
    rlines: List[str] = []
    for d, name in DIMENSION_ROWS:
        b = scores.get(d)
        if not isinstance(b, dict):
            b = {}
        r = (b.get("rationale_1line") or "").strip()
        if not r:
            continue
        rlines.append(
            f'<p class="rline"><b>{_esc(d)} — {_esc(name)}</b> {_esc(r)}</p>'
        )
    rlines_html = "\n".join(rlines)
    pull = f'<p class="pull">{_esc(st)}</p>' if st else ""
    watch = f'<p class="watch"><span class="wlab">Watch</span> {_esc(rk)}</p>' if rk else ""
    pvt_lbl = _esc(pvt.get("label", "")) if pvt.get("key") != "unknown" else "—"
    cap_txt = _esc((tc or {}).get("caption") or "")
    lvl_lbl = _esc(ass.get("level_label") or "this level")
    bmk_html = f"""<div class="bmk" style="margin:4mm 0 3mm; padding:3.5mm 4mm; background:#f8f6ff; border-radius:10px; border:1px solid #e8e2f4;">
  <p style="margin:0 0 2.5mm; font-size:7.5pt; font-weight:800; text-transform:uppercase; letter-spacing:0.1em; color:#5300ba">Vs. typical for your level</p>
  <p style="margin:0 0 2.5mm; font-size:8.5pt; color:#3d3a48">For <b>{lvl_lbl}</b>, a directional band is <b>{tlo:.0f}–{thi:.0f}</b> on the 0–100 composite.</p>
  <div style="position:relative; height:16px; margin:3.5mm 0 2mm; background:#e4e0ee; border-radius:8px;">
  <div style="position:absolute; left:{zl}%; width:{zw}%; top:0; height:16px; background:rgba(150,0,241,0.25); border-radius:6px"></div>
  <div style="position:absolute; left:{mlp}%; top:0; width:6px; height:16px; margin-left:-3px; background:#5300ba; border-radius:2px"></div>
  </div>
  <p style="margin:0; font-size:8.5pt; color:#1a1a1b; font-weight:700"><strong>{_esc(aiq_s)}</strong> — {pvt_lbl}</p>
  <p style="margin:1.2mm 0 0; font-size:6.5pt; color:#6e6b78; line-height:1.3">{cap_txt}</p>
</div>"""
    if pvt.get("key") == "unknown":
        bmk_html = ""
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"/>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
@page {{ size: A4; margin: 14mm; }}
body {{ font-family: 'Plus Jakarta Sans', sans-serif; color: #1a1a1b; background: #fff; font-size: 9.5pt; line-height: 1.45; margin: 0; padding: 0; -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
h1 {{ font-size: 18pt; font-weight: 800; margin: 0 0 2mm; letter-spacing: -0.02em; color: #1a1a1b; }}
.band {{ display: inline-block; background: #5300ba; color: #fff; font-size: 6.5pt; font-weight: 800; letter-spacing: 0.12em; text-transform: uppercase; padding: 3px 8px; border-radius: 999px; margin-bottom: 4mm; }}
.hero {{ display: flex; gap: 8mm; align-items: flex-start; margin-bottom: 4mm; }}
.gau {{ text-align: center; min-width: 100px; }}
.gnum {{ font-size: 32pt; font-weight: 800; color: #5300ba; line-height: 1; }}
.gs {{ font-size: 7.5pt; color: #6a6875; margin-top: 2px; }}
.profile {{ font-size: 8.5pt; color: #5c5a65; margin: 0 0 3mm; max-width: 50ch; }}
.w {{ font-weight: 600; color: #7a7890; font-size: 7.5pt; }}
.grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 2mm; font-size: 8.5pt; margin: 3mm 0; clear: both; }}
.dcell {{ border: 1px solid #e4e0f0; border-radius: 6px; padding: 2mm; position: relative; }}
.dtitle {{ font-size: 6.5pt; font-weight: 800; text-transform: uppercase; letter-spacing: 0.04em; color: #6e6b78; display: block; margin-bottom: 1mm; padding-right: 36pt; }}
.dsc {{ position: absolute; top: 2mm; right: 2mm; font-size: 10pt; font-weight: 800; color: #5300ba; }}
.cl {{ clear: both; height: 0; }}
.rline b {{ color: #1a1a1b; font-size: 8.2pt; }}
.rline {{ font-size: 8pt; color: #3d3a48; margin: 2.5mm 0; border-bottom: 1px solid #efeaf8; padding-bottom: 2mm; }}
.rline:last-child {{ border-bottom: none; }}
.pull, .watch {{ font-size: 8.5pt; margin: 0 0 2mm; }}
.watch {{ background: #f3effb; border-radius: 8px; padding: 2.5mm 3mm; }}
.wlab {{ font-size: 7pt; font-weight: 800; text-transform: uppercase; letter-spacing: 0.1em; color: #5300ba; margin-right: 2mm; }}
.foot {{ font-size: 7.5pt; color: #8a8794; margin-top: 4mm; }}
</style></head><body>
<span class="band">{_esc(band)}</span>
<h1>Your AiQ snapshot</h1>
<div class="hero">
  <div class="gau"><div class="gnum">{_esc(aiq_s)}</div><div class="gs">AiQ · 0–100</div></div>
  <div>
    <p class="profile"><b>Scored for:</b> {_esc(profile) if profile else "—"}</p>
    {pull}
    {watch}
  </div>
</div>
{bmk_html}
<div class="grid">
{grid_html}
</div>
<div class="rblock">{rlines_html}</div>
<p class="foot">Provisional · for reflection and coaching from this one chat, not a hiring score or final label.</p>
</body></html>
"""


def _build_reportlab_fallback(scores: dict, assessment: Optional[dict]) -> bytes:
    st0 = getSampleStyleSheet()
    st0.add(ParagraphStyle(name="T", parent=st0["Normal"], fontSize=9, spaceAfter=3))
    st0.add(ParagraphStyle(name="H", parent=st0["Heading1"], fontSize=14, spaceAfter=4))
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=16 * mm, leftMargin=16 * mm, topMargin=16 * mm, bottomMargin=16 * mm)
    ass = assessment or {}
    aiq = scores.get("AiQ_0_100", "—")
    prof = f"{ass.get('level_label', '')} · {ass.get('job_family_label', '')}"
    aiq_num = aiq
    try:
        aiq_num = float(aiq) if aiq is not None and aiq != "" else None
    except (TypeError, ValueError):
        aiq_num = None
    pvt2 = position_versus_typical_composite(aiq_num, str(ass.get("level") or "head_of"))
    tc2 = typical_composite_for_level(str(ass.get("level") or "head_of"))
    bench = (
        f"Vs. level band ({tc2['low']:.0f}–{tc2['high']:.0f} on 0–100, directional): {html.escape(pvt2.get('label', '—'))}"
    )
    story = [
        Paragraph(f"<b>Your AiQ snapshot</b> &nbsp; {html.escape(str(scores.get('maturity_band', '—')))}", st0["H"]),
        Paragraph(f"Composite: {html.escape(str(aiq))} &nbsp;|&nbsp; {html.escape(prof)}", st0["T"]),
        Paragraph(f"<i>{bench}</i>", st0["T"]),
        Spacer(1, 3 * mm),
    ]
    for d, name in DIMENSION_ROWS:
        b = scores.get(d) if isinstance(scores.get(d), dict) else {}
        sc = b.get("score", "—") if isinstance(b, dict) else "—"
        r = (b.get("rationale_1line") or "") if isinstance(b, dict) else ""
        story.append(Paragraph(f"<b>{d} {name}</b>: {sc}/10. {html.escape(r[:500])}", st0["T"]))
    story.append(Spacer(1, 3 * mm))
    story.append(
        Paragraph(
            "<i>Provisional · for reflection and coaching from this one chat.</i>", st0["T"]
        )
    )
    doc.build(story)
    return buf.getvalue()


def build_session_report_pdf_bytes(scores: dict, assessment: Optional[dict] = None) -> bytes:
    if not isinstance(scores, dict):
        scores = {}
    html_s = _build_onepage_html(scores, assessment)
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
