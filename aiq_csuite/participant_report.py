"""
Participant-facing report enrichment: gaps, coaching focus, and next steps from scores.
Used by session_report_pdf (and kept importable without loading Flask).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from assessment_profiles import is_technical_product_family
from coaching_engine import build_coaching_dimension_row, fam_cluster

DIMENSION_ORDER: List[Tuple[str, str]] = [
    ("D1", "Awareness & opportunity"),
    ("D2", "Prompts & comms"),
    ("D3", "Critical judgment"),
    ("D4", "Workflows & org design"),
    ("D5", "Clarity, craft & output fit"),
    ("D6", "Risk & responsible use"),
]

BAND_BLURBS: Dict[str, str] = {
    "AiQ1": "Early stage: AI shows up inconsistently in your work. Focus on naming real tools, one workflow, and basic judgment before scaling use.",
    "AiQ2": "Working fluency: you use AI effectively in parts of your role. Tighten prompts, review habits, and how outputs are shared with others.",
    "AiQ3": "Builder level: solid day-to-day use with room to systematize workflows, quality bars, and responsible-use habits across the team.",
    "AiQ4": "Strategist level: strong personal fluency; emphasis shifts to setting expectations, governance, and how others adopt AI in the function.",
}


def expected_dim_targets(level: str, assessment: Optional[dict]) -> Dict[str, float]:
    base = {
        "ic": 5.6,
        "people_manager": 6.1,
        "head_of": 6.6,
        "executive": 7.0,
    }.get((level or "head_of").strip(), 6.2)
    w = (assessment or {}).get("weights") or {}
    avg_w = (sum(float(w.get(k, 0.0)) for k, _ in DIMENSION_ORDER) / 6.0) if w else 0.1667
    out: Dict[str, float] = {}
    for code, _ in DIMENSION_ORDER:
        ww = float(w.get(code, avg_w)) if w else avg_w
        out[code] = round(max(4.5, min(8.8, base + (ww - avg_w) * 8.0)), 2)
    return out


def _gap_status(actual: float, target: float) -> Tuple[str, float, float]:
    delta = round(actual - target, 2)
    shortfall = round(max(0.0, target - actual), 2)
    if delta > 0.1:
        return "above", delta, shortfall
    if delta < -0.1:
        return "below", delta, shortfall
    return "on", delta, shortfall


def _status_label(status: str, delta: float, shortfall: float) -> str:
    if status == "above":
        return f"{abs(delta):.1f} above the typical band for your level"
    if status == "below":
        return f"{shortfall:.1f} below the typical band — worth a focused push"
    return "In the typical band for your level"


def build_report_enrichment(
    scores: dict, assessment: Optional[dict] = None
) -> Dict[str, Any]:
    """Coaching rows, priority next steps, and copy blocks for the participant PDF."""
    ass = dict(assessment) if assessment else {}
    level = str(ass.get("level") or "head_of")
    fam_label = ass.get("job_family_label") or str(ass.get("job_family") or "your role")
    if len(str(fam_label)) < 2:
        fam_label = "your role"
    fam_key = str(ass.get("job_family") or "other")
    fam_cl = fam_cluster(fam_key)
    job_tech = is_technical_product_family(ass.get("job_family"))
    targets = expected_dim_targets(level, ass)

    gaps: List[dict] = []
    for code, label in DIMENSION_ORDER:
        block = scores.get(code) if isinstance(scores.get(code), dict) else {}
        actual = float(block.get("score") or 0.0)
        target = float(targets.get(code) or 6.0)
        status, delta, shortfall = _gap_status(actual, target)
        gaps.append(
            {
                "code": code,
                "label": label,
                "actual": actual,
                "target": target,
                "gap": shortfall,
                "delta_vs_target": delta,
                "status": status,
                "status_label": _status_label(status, delta, shortfall),
                "rationale": (block.get("rationale_1line") or "").strip(),
            }
        )

    gaps.sort(key=lambda x: (x["gap"], -x["delta_vs_target"]), reverse=True)
    g_by = {g["code"]: g for g in gaps}
    ranked_below = [g for g in gaps if g["status"] == "below"]
    ranked_above = [g for g in gaps if g["status"] == "above"]

    coaching_rows: List[dict] = []
    link_set = {g["code"] for g in ranked_below[:4]}
    c_slot = 0
    for code, _lab in DIMENSION_ORDER:
        g = g_by[code]
        add_course = g["code"] in link_set and g.get("gap", 0) > 0.1
        if add_course:
            c_slot += 1
        row = build_coaching_dimension_row(
            {},  # no external course links in PDF (keeps report self-contained)
            g,
            str(fam_label),
            fam_key,
            fam_cl,
            add_course=False,
            c_slot=0,
            job_tech=job_tech,
        )
        row["status"] = g["status"]
        row["status_label"] = g["status_label"]
        row["actual"] = g["actual"]
        row["target"] = g["target"]
        if g["rationale"]:
            row["rationale"] = g["rationale"]
        coaching_rows.append(row)

    next_steps: List[str] = []
    for row in coaching_rows:
        if row.get("status") != "below":
            continue
        code = row.get("code") or ""
        focus = (row.get("focus") or "").strip()
        exs = row.get("exercises") or []
        if focus:
            next_steps.append(f"{code}: {focus}")
        if exs and len(next_steps) < 8:
            next_steps.append(f"{code} (this week): {exs[0]}")

    if not next_steps:
        for row in coaching_rows:
            exs = row.get("exercises") or []
            if exs:
                next_steps.append(f"{row.get('code')}: {exs[0]}")
            if len(next_steps) >= 4:
                break

    keep_doing: List[str] = []
    for g in ranked_above[:3]:
        keep_doing.append(
            f"{g['code']} · {g['label']} ({g['actual']:.1f}/10) — {g['status_label']}."
        )

    band = str(scores.get("maturity_band") or "").strip()
    band_blurb = BAND_BLURBS.get(band, "")

    return {
        "gaps": gaps,
        "coaching_rows": coaching_rows,
        "next_steps": next_steps[:8],
        "keep_doing": keep_doing,
        "band_blurb": band_blurb,
        "ranked_below": ranked_below,
        "profile_line": " · ".join(
            x for x in (ass.get("level_label") or "", ass.get("job_family_label") or "") if x
        ),
    }
