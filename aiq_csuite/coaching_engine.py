# Dimension-grounded coaching + audience-aware public links for AiQ recommendations.
# Called from app._recommendations; keeps scoring logic in one place.
from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Optional, Tuple

# COURSE_CATALOG is passed in from app._COURSE_CATALOG to avoid circular imports.


def fam_cluster(fam_slug: str) -> str:
    s = (fam_slug or "other").strip()
    m = {
        "hr_people": "people",
        "care_operations": "ops",
        "go_to_market": "gtm",
        "product_engineering": "product",
        "risk_legal": "risk",
        "finance": "fin",
        "general_management": "gm",
    }
    return m.get(s, "gm")


def courses_for_recommendation(
    course_catalog: dict, dimension_code: str, fam_slug: str, job_tech: bool
) -> List[dict]:
    rows = [dict(c) for c in (course_catalog.get(dimension_code) or [])]
    if not rows:
        return []
    fam_slug = (fam_slug or "other").strip() or "other"
    out: List[dict] = []
    for c in rows:
        aud = list(c.get("audiences") or ["*"])
        tlow = (c.get("title") or "").lower()
        if (not job_tech) and (
            "developers" in tlow
            or " for developers" in tlow
            or (aud == ["product_engineering"] and "developers" in tlow)
        ):
            if not (job_tech and "product_engineering" in aud):
                continue
        if "*" in aud or fam_slug in aud:
            out.append(c)
    if not out:
        for c in rows:
            aud = list(c.get("audiences") or ["*"])
            if "*" in aud:
                out.append(c)
    if not out:
        out = rows[:1]
    # Prefer a row that explicitly lists this job family over generic ["*"] only, so product vs HR diverge.
    fam_specific = [c for c in out if fam_slug in (c.get("audiences") or []) and (c.get("audiences") or []) != ["*"]]
    if fam_specific:
        out = fam_specific
    out.sort(key=lambda c: (float(c.get("weight", 5)), c.get("title", "")))
    return out


def pick_one_course(
    course_catalog: dict,
    code: str,
    fam_slug: str,
    job_tech: bool,
    gap: float,
    slot: int,
) -> Optional[dict]:
    cands = courses_for_recommendation(course_catalog, code, fam_slug, job_tech)
    if not cands:
        return None
    h = int(hashlib.md5(f"{fam_slug}|{code}|{slot}|{gap:.2f}".encode("utf-8")).hexdigest()[:8], 16)
    if float(gap) > 1.1:
        return dict(cands[0])
    return dict(cands[h % len(cands)])


def _standing_focus_ex(
    code: str, label: str, fam: str, cluster: str, actual: float, target: float, gnum: float
) -> Tuple[str, str, List[str]]:
    if gnum < 0.15:
        st = f"{label} ({code}): in band this run at {actual:.1f} vs a typical ~{target:.0f} for the level (gap {gnum:.1f} is small)."
        fo = f"Keep the habit; once a month, spot-check one {fam} process where a model is involved so standards do not slip."
        ex = [
            f"Pick a routine {fam} deliverable; skim how models were used and add one “good/weak” line to a shared note.",
            "Mention in standup one case where a human overrode the model, so the team remembers the bar.",
        ]
        return st, fo, ex

    st = f"{label} ({code}): this run {actual:.1f} on the rubric, reference for the level is about {target:.0f} (gap {gnum:.1f} points). The focus below matches this {fam} area."

    f1: Dict[str, Any] = {
        "D1": {
            "default": f"Name real tools and live use cases in {fam} — not a slide of future possibilities.",
            "people": "Tie D1 to people work: which HR or manager workflows already use a copilot, and which do not (yet).",
            "ops": f"Tie D1 to queues: where does gen-AI touch a customer or {fam} touchpoint, and is it the same in every team?",
            "gtm": "Tie D1 to revenue-facing moments: GTM, sales, and brand each name one in-production use.",
            "product": "Tie D1 to shipped and planned product/data use: drop slide-only “ideas” in favour of 3 real examples.",
        },
        "D2": {
            "default": f"For {fam}, standardize prompts and checks on 2–3 recurring tasks instead of ad-hoc chats.",
            "people": "D2: shared prompt shells for people programs, plus a review line before anything employee-facing goes out.",
            "product": "D2: prompt + expected failure cases next to the design doc or test plan.",
            "risk": "D2: fixed prompt structure for policy answers, with “must escalate to Legal” in the same template.",
        },
        "D3": {
            "default": f"Be explicit in {fam} about what you never send without a check, and prove you followed it in real work.",
            "fin": "D3: for numbers and models in filings or decks, a second set of eyes or data source, every time.",
            "ops": "D3: when a model answers a live customer, what is the minimum edit and who is accountable for it?",
        },
        "D4": {
            "default": f"Clarify owners and systems for one {fam} process end-to-end (AI is one step, not a parallel shadow process).",
            "people": "D4: HR/people: who may run AI, who approves, and where the record lives for a case or letter.",
            "ops": f"D4: for {fam} queues, name the owner of a late or bad AI-assisted reply before it leaves the org.",
        },
        "D5": {
            "default": f"D5: align tone, fact checks, and audience for anything others read, particular to {fam} stakeholders.",
            "gtm": "D5: for external and exec copy, a short GTM+legal/brand line on what the model is allowed to draft vs not.",
        },
        "D6": {
            "default": f"D6: non-negotiables for {fam} data in models, plus a rehearsed “stop the line” path, not a policy no one has used.",
            "risk": f"D6: {fam} and risk work—classification of what can enter which tool, in terms your front line can act on.",
        },
    }
    dim_f = f1.get(code) or {
        "default": f"Pick one {fam} habit in {label} you can see in a week, tied to a named workflow."
    }
    fo = dim_f.get(cluster) or dim_f.get("default")
    if not fo and dim_f:
        fo = next(iter(dim_f.values()))

    exmap: Dict[str, List[str]] = {
        "D1": [
            f"3 tools the team used this week for {fam} work, each with: task, time saved or not, and when you would not use the tool there.",
            "Kill or merge one “AI project” with no user and no data after 6 weeks; replace with one 20-minute try on a real {fam} task.",
        ],
        "D2": [
            f"One {fam} task, two prompt versions: role, inputs, bad-answer test; keep the better version in a shared file.",
            "A “reread before send” rule for one high-risk channel, written in 4 bullets everyone can see.",
        ],
        "D3": [
            f"One rule: “I do not send {fam} output of type X without Y” and log 2 real borderline cases in a week.",
            f"3 examples of {fam} output you edited or binned, with one line each: what was wrong in the first draft.",
        ],
        "D4": [
            f"1-page: request to outcome for 1 {fam} workflow; circle 1 handoff, add 1 person or SLA, only there.",
            f"One retro question: if an AI-suggested line went wrong in {fam}, which role owns the fix, first?",
        ],
        "D5": [
            f"1 audience, 1 model draft: mark 3 edits (tone, fact, names) before you would send; save the list as a checklist once.",
            "2 drafts, self-scored: what would you do differently the next time you use a model for that audience?",
        ],
        "D6": [
            f"3 “never in the model” for {fam} and one escalation; pin where your team can see it, not a PDF buried in a drive.",
            "15-minute tabletop: wrong or harmful line gets to a customer; first three human actions, in order, with names if possible.",
        ],
    }
    ex = exmap.get(
        code,
        [
            f"1 {fam} month: 1 before/after where a human check changed a model line.",
            "15 minutes: one test next week, written in 2 sentences and dated.",
        ],
    )
    return st, fo, ex


def build_coaching_dimension_row(
    course_catalog: dict,
    g: dict,
    fam_label: str,
    fam_slug: str,
    cluster: str,
    add_course: bool,
    c_slot: int,
    job_tech: bool,
) -> Dict[str, Any]:
    code = str(g.get("code") or "")
    label = str(g.get("label") or "")
    actual = float(g.get("actual", 0))
    target = float(g.get("target", 0))
    gnum = float(g.get("gap", 0))
    standing, focus, exercises = _standing_focus_ex(
        code, label, fam_label, cluster, actual, target, gnum
    )
    course: Optional[dict] = None
    if add_course and gnum > 0.1:
        pc = pick_one_course(course_catalog, code, fam_slug, job_tech, gnum, c_slot)
        if pc and pc.get("url"):
            course = {
                "title": pc.get("title"),
                "provider": pc.get("provider"),
                "url": pc.get("url"),
                "why": (pc.get("why") or "").strip(),
            }
    return {
        "code": code,
        "label": label,
        "standing": standing,
        "focus": focus,
        "exercises": exercises,
        "suggested_read": course,
        "meta": f"Actual {actual:.1f} · level band ~{target:.0f} · gap {gnum:.1f}",
    }
