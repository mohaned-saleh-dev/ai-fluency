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

# One concrete, dimension-specific action per area (never the generic “pick a deliverable” line).
# Keys: below (under band), stretch (in band), maintain (above band). Optional cluster overrides.
_DIM_NEXT_STEP: Dict[str, Dict[str, Any]] = {
    "D1": {
        "below": "List every gen-AI or copilot tool your team actually opens in a normal week; for each, write one real task it supports and one task where you would still not use it.",
        "stretch": "Pick one workflow that should use AI but does not yet; name the tool, the owner, and the first small pilot you will run in the next two weeks.",
        "maintain": "Keep a short living inventory of tools and use cases; review quarterly so new hires and partners see what is approved in practice, not only on slides.",
        "product": {
            "below": "Map three shipped or in-flight product/data surfaces that call a model; for each, who owns the prompt, the eval, and the rollback if quality drops.",
            "stretch": "Run a 30-minute review with eng/design: which backlog items truly need a model vs. a script or dashboard — retire one “AI for AI’s sake” item.",
        },
        "ops": {
            "below": "For each customer- or ops-facing AI touchpoint, document which queue owns it and one metric that proves it is working.",
        },
        "gtm": {
            "below": "Have GTM, brand, and sales each name one live AI-assisted workflow (not a pilot deck) and who signs off external-facing output.",
        },
    },
    "D2": {
        "below": "Choose one recurring task (e.g. weekly report, spec, or customer reply); write a reusable prompt template with role, inputs, constraints, and a “bad answer” test before anyone uses it.",
        "stretch": "Add a one-line quality check to an existing prompt library entry you already use — what must be true before you paste the output anywhere.",
        "maintain": "When you improve a prompt that others copy, post the before/after and why it changed so the team does not drift back to vague asks.",
        "people": {
            "below": "Create one shared prompt shell for a people-facing artifact (policy note, manager email, job description) with a mandatory human review line.",
        },
        "risk": {
            "below": "For legal/policy answers assisted by a model, fix a prompt footer: what must be escalated to counsel and what must never be pasted into the tool.",
        },
    },
    "D3": {
        "below": "Write one explicit rule for your role: “I do not send output type X without check Y”; log two real cases this week where you applied or overrode it.",
        "stretch": "Take one model draft you almost shipped; list three factual or logic checks you ran and one you wish you had run earlier.",
        "maintain": "Share one short story in team forum: a time you pushed back on model output and what signal made you stop — not a generic “be careful” reminder.",
        "fin": {
            "below": "For the next deck or model-backed number, require a second source or reviewer before it leaves your desk; note who that is.",
        },
    },
    "D4": {
        "below": "Draw one end-to-end workflow on a single page (request → AI step → human review → delivery); circle the weakest handoff and assign one owner and SLA.",
        "stretch": "Identify one process where AI runs in parallel to the official path; merge or kill the shadow path so there is a single system of record.",
        "maintain": "In your next operating review, ask one question per function: where does AI sit in the cadence, and who is accountable when it fails.",
        "people": {
            "below": "For HR/people cases touching a model, document who may run the tool, who approves, and where the record lives.",
        },
    },
    "D5": {
        "below": "Pick one audience (exec, customer, or cross-functional); take a model draft, mark three edits you required (tone, facts, names), and turn that into a mini checklist for that audience.",
        "stretch": "Before the next shared document goes out, add a “good enough to ship” line: what a reader must still verify even if the draft looks polished.",
        "maintain": "When output quality is already strong, mentor someone else: review their model-assisted draft once and annotate what you would change.",
        "gtm": {
            "below": "Align with brand/legal on one external channel: what the model may draft vs. what must stay human-only; publish in the channel’s playbook.",
        },
    },
    "D6": {
        "below": "List three data types that must never enter your approved tools; post the list where your team looks daily and run one 15-minute “what if we pasted this?” tabletop.",
        "stretch": "Rehearse one escalation path: harmful or wrong model line reaches a stakeholder — first three human actions, with names if possible.",
        "maintain": "Once a quarter, spot-check that vendor/tool settings (retention, logging, regions) still match policy; fix one gap you find.",
        "risk": {
            "below": "Translate one policy paragraph into a front-line rule: what can go into which tool, in language your team uses in standup.",
        },
    },
}


def _resolve_dim_next_step(
    code: str,
    status: str,
    fam_label: str,
    fam_cl: str,
    rationale: str = "",
) -> str:
    """Return one actionable sentence for this dimension; never duplicate generic copy."""
    block = _DIM_NEXT_STEP.get(code) or {}
    tier = "below" if status == "below" else ("maintain" if status == "above" else "stretch")
    cluster_block = block.get(fam_cl)
    if isinstance(cluster_block, dict):
        text = cluster_block.get(tier) or cluster_block.get("stretch") or cluster_block.get("below")
    else:
        text = block.get(tier) or block.get("stretch") or block.get("below")
    if not text:
        text = (
            f"Pick one concrete habit in {fam_label} tied to {code} this week; "
            "write what you will do, who sees the output, and how you will know it worked."
        )
    rat = (rationale or "").strip()
    if rat and len(rat) > 20 and status == "below":
        short = rat if len(rat) <= 120 else rat[:117].rstrip() + "…"
        return f"{text} (From this chat: {short})"
    return text


def _pick_dims_for_next_steps(gaps: List[dict], max_n: int = 5) -> List[dict]:
    """Prioritize real gaps first, then weakest in-band areas — never repeat one generic line."""
    below = [g for g in gaps if g.get("status") == "below"]
    on_band = [g for g in gaps if g.get("status") == "on"]
    # Weakest relative performance among “on” (smallest positive or negative delta).
    on_band.sort(key=lambda x: float(x.get("delta_vs_target") or 0))
    above = [g for g in gaps if g.get("status") == "above"]
    above.sort(key=lambda x: float(x.get("delta_vs_target") or 0))

    picked: List[dict] = []
    seen: set = set()
    for g in below:
        if g["code"] not in seen:
            picked.append(g)
            seen.add(g["code"])
        if len(picked) >= max_n:
            return picked
    for g in on_band:
        if g["code"] not in seen:
            picked.append(g)
            seen.add(g["code"])
        if len(picked) >= max_n:
            return picked
    for g in above[:2]:
        if g["code"] not in seen and len(picked) < max_n:
            picked.append(g)
            seen.add(g["code"])
    return picked


def _build_next_steps_list(
    gaps: List[dict],
    fam_label: str,
    fam_cl: str,
    coaching_rows: List[dict],
    max_n: int = 5,
) -> List[str]:
    """Dimension-distinct next steps for the PDF (label + action, no copy-paste)."""
    row_by_code = {r.get("code"): r for r in coaching_rows if r.get("code")}
    out: List[str] = []
    for g in _pick_dims_for_next_steps(gaps, max_n=max_n):
        code = g["code"]
        label = g["label"]
        status = g.get("status") or "on"
        rationale = g.get("rationale") or (row_by_code.get(code) or {}).get("rationale") or ""
        action = _resolve_dim_next_step(code, status, fam_label, fam_cl, rationale)
        if status == "below":
            exs = (row_by_code.get(code) or {}).get("exercises") or []
            if exs and exs[0] and exs[0] not in action:
                action = f"{action} This week: {exs[0]}"
        out.append(f"{code} · {label}: {action}")
    return out


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


def _merge_llm_narrative(
    enrich: Dict[str, Any], narrative: Optional[dict]
) -> Dict[str, Any]:
    """Overlay LLM-generated coaching copy when present (scenario-stack sessions)."""
    if not narrative or not isinstance(narrative, dict):
        return enrich
    out = dict(enrich)
    for key in (
        "executive_summary",
        "what_we_saw",
        "strongest_habits",
        "gaps_that_mattered",
        "one_practice_drill",
    ):
        if narrative.get(key):
            out[key] = narrative[key]
    steps: List[str] = []
    for item in narrative.get("next_steps") or []:
        if isinstance(item, dict):
            action = (item.get("action") or "").strip()
            why = (item.get("why") or "").strip()
            horizon = (item.get("horizon") or "").strip()
            success = (item.get("success_looks_like") or "").strip()
            line = action
            if why:
                line = f"{line} — {why}" if line else why
            if horizon and line:
                line = f"[{horizon}] {line}"
            if success and line:
                line = f"{line} (Success: {success})"
            if line:
                steps.append(line)
        elif item:
            steps.append(str(item))
    if steps:
        out["next_steps"] = steps
    habits = narrative.get("strongest_habits") or []
    if habits:
        out["keep_doing"] = [str(h) for h in habits[:5]]
    per = narrative.get("per_dimension") or {}
    if isinstance(per, dict) and per:
        rows = []
        for code, label in DIMENSION_ORDER:
            block = per.get(code) if isinstance(per.get(code), dict) else {}
            nar = (block.get("narrative") or "").strip()
            practice = (block.get("one_practice") or "").strip()
            base = next((r for r in out.get("coaching_rows") or [] if r.get("code") == code), {})
            row = dict(base)
            row["code"] = code
            row["label"] = label
            if nar:
                row["standing"] = nar
            if practice:
                row["focus"] = practice
                row["exercises"] = []
            rows.append(row)
        if rows:
            out["coaching_rows"] = rows
    return out


def build_report_enrichment(
    scores: dict,
    assessment: Optional[dict] = None,
    session_enrichment: Optional[dict] = None,
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

    next_steps = _build_next_steps_list(
        gaps, str(fam_label), fam_cl, coaching_rows, max_n=5
    )

    keep_doing: List[str] = []
    for g in ranked_above[:3]:
        keep_doing.append(
            f"{g['code']} · {g['label']} ({g['actual']:.1f}/10) — {g['status_label']}."
        )

    band = str(scores.get("maturity_band") or "").strip()
    band_blurb = BAND_BLURBS.get(band, "")

    enrich = {
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
    narrative = None
    if session_enrichment and isinstance(session_enrichment, dict):
        narrative = session_enrichment.get("narrative")
    return _merge_llm_narrative(enrich, narrative)
