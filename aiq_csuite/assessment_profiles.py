"""
Formal AiQ profile: level × job family → **frozen dimension weights** (sum 1.0) and
**calibration** text. Weights are computed in code (not LLM-invented) for repeatability;
the assessor must interpret evidence *through* this profile.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

# --- Canonical slugs (API / UI) -------------------------------------------------

LEVELS: List[Dict[str, str]] = [
    {"slug": "ic", "label": "Individual contributor"},
    {"slug": "people_manager", "label": "People manager / team lead"},
    {"slug": "head_of", "label": "Head of function / director"},
    {"slug": "executive", "label": "Executive (VP, C-suite, GM)"},
]

JOB_FAMILIES: List[Dict[str, str]] = [
    {"slug": "general_management", "label": "General management / P&L"},
    {"slug": "product_engineering", "label": "Product, engineering, design & data"},
    {"slug": "go_to_market", "label": "Growth, brand, sales & marketing"},
    {"slug": "care_operations", "label": "Customer care, ops & service delivery"},
    {"slug": "risk_legal", "label": "Risk, legal, compliance & policy"},
    {"slug": "finance", "label": "Finance, strategy, corp dev"},
    {"slug": "hr_people", "label": "HR, people, workplace"},
    {"slug": "other", "label": "Other / not listed"},
]

# Base weights (D1..D6): same as original leadership-heavy product default, sum=1.0
_BASE: Tuple[float, float, float, float, float, float] = (
    0.16,
    0.10,
    0.16,
    0.20,
    0.08,
    0.30,
)
_DIM_ORDER = ("D1", "D2", "D3", "D4", "D5", "D6")

# Small additive deltas; combined then **renormalized** to sum=1.0. Tuned for interpretability, not stats.
# D1 aware, D2 prompts/comm, D3 judgment, D4 workflows/org, D5 brand/narr, D6 risk
_LEVEL_DELTAS: Dict[str, Tuple[float, float, float, float, float, float]] = {
    # More hands-on execution & less “org as system” at IC
    "ic": (0.03, 0.04, 0.04, -0.04, 0.01, -0.08),
    "people_manager": (0.0, 0.02, 0.01, 0.01, 0.0, -0.04),
    "head_of": (-0.01, 0.0, 0.01, 0.03, 0.0, -0.03),
    "executive": (-0.02, -0.01, 0.0, 0.0, 0.0, 0.03),
}
_FAMILY_DELTAS: Dict[str, Tuple[float, float, float, float, float, float]] = {
    "general_management": (0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
    "product_engineering": (0.0, 0.04, 0.03, 0.04, 0.02, -0.13),
    "go_to_market": (0.01, 0.02, 0.02, 0.01, 0.06, -0.12),
    "care_operations": (0.0, 0.02, 0.03, 0.04, 0.03, -0.12),
    "risk_legal": (-0.02, 0.0, 0.02, 0.0, 0.0, 0.0),
    "finance": (0.0, 0.0, 0.03, 0.04, 0.0, -0.07),
    "hr_people": (0.0, 0.0, 0.0, 0.05, 0.02, -0.07),
    "other": (0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
}

DEFAULT_LEVEL = "head_of"
DEFAULT_FAMILY = "general_management"


def _coerce_level(raw: Optional[str]) -> str:
    s = (raw or DEFAULT_LEVEL).strip().lower().replace(" ", "_").replace("-", "_")
    if s in {x["slug"] for x in LEVELS}:
        return s
    if s in ("c_suite", "clevel", "cxo", "vp", "svp", "evp"):
        return "executive"
    if s in ("manager", "team_lead", "pl"):
        return "people_manager"
    if s in ("director", "d_level", "function_head", "head", "head_of", "h"):
        return "head_of"
    if s in ("ic", "individual", "ic_contributor", "ic_"):
        return "ic"
    return DEFAULT_LEVEL


def _coerce_family(raw: Optional[str]) -> str:
    s = (raw or DEFAULT_FAMILY).strip().lower().replace(" ", "_").replace("-", "_")
    if s in {x["slug"] for x in JOB_FAMILIES}:
        return s
    aliases = {
        "revenue": "go_to_market",
        "sales": "go_to_market",
        "marketing": "go_to_market",
        "commercial": "go_to_market",
        "risk": "risk_legal",
        "legal": "risk_legal",
        "compliance": "risk_legal",
        "governance": "risk_legal",
        "customer": "care_operations",
        "support": "care_operations",
        "operations": "care_operations",
        "care": "care_operations",
        "eng": "product_engineering",
        "engineering": "product_engineering",
        "product": "product_engineering",
        "data": "product_engineering",
        "design": "product_engineering",
    }
    return aliases.get(s, DEFAULT_FAMILY)


def is_technical_product_family(family_raw: Optional[str]) -> bool:
    """
    True for product / engineering / design & data — matches public courses aimed at building software.
    Other job families get non-technical D2 and learning picks first.
    """
    return _coerce_family(family_raw) == "product_engineering"


def _norm6(t: Tuple[float, float, float, float, float, float]) -> Tuple[float, ...]:
    a = [max(0.01, float(x)) for x in t]
    s = sum(a)
    return tuple(round(x / s, 4) for x in a)


def _weights_from_deltas(lev: str, fam: str) -> Dict[str, float]:
    ld = _LEVEL_DELTAS.get(lev) or _LEVEL_DELTAS[DEFAULT_LEVEL]
    fd = _FAMILY_DELTAS.get(fam) or _FAMILY_DELTAS["other"]
    if ld is None:  # pragma: no cover
        ld = (0.0,) * 6
    if fd is None:  # pragma: no cover
        fd = (0.0,) * 6
    combined: List[float] = []
    for i in range(6):
        v = _BASE[i] + ld[i] + fd[i]
        combined.append(v)
    n6 = _norm6(tuple(combined))  # type: ignore
    return {c: n6[i] for i, c in enumerate(_DIM_ORDER)}


def profile_id(level: str, family: str) -> str:
    return f"{level}__{family}"


def label_for_level(slug: str) -> str:
    for x in LEVELS:
        if x["slug"] == slug:
            return x["label"]
    return slug


def label_for_family(slug: str) -> str:
    for x in JOB_FAMILIES:
        if x["slug"] == slug:
            return x["label"]
    return slug


# One-line labels for report deck, UI, and API (no markdown).
DIMENSION_DECK_LABELS: Dict[str, str] = {
    "D1": "Awareness & opportunity",
    "D2": "Prompts & comms",
    "D3": "Critical judgment",
    "D4": "Workflows & org design",
    "D5": "Clarity, craft & output fit",
    "D6": "Risk & responsible use",
}

_DIM_NICK: Dict[str, str] = {
    "D1": "awareness & where AI is worth it",
    "D2": "how they brief, steer, and iterate on models or AI work",
    "D3": "challenging confident or thin AI output before it ships",
    "D4": "workflows, ownership, and how work actually moves",
    "D5": "clarity, craft, and fit of AI-assisted *outputs others see* (docs, comms, deliverables) — not “brand” as marketing-only",
    "D6": "responsible use: sensitive data, escalation, no-go zones, judgment — the same *spirit* as org-wide training (security, data, AML): everyone has a real floor, job adds depth",
}


# Directional AiQ 0–100 band *typical* for this seniority in the product (coaching context only, not a gate).
LEVEL_COMPOSITE_TYPICAL: Dict[str, Tuple[float, float]] = {
    "ic": (28.0, 50.0),
    "people_manager": (36.0, 58.0),
    "head_of": (45.0, 68.0),
    "executive": (52.0, 75.0),
}


def typical_composite_for_level(level: str) -> Dict[str, Any]:
    s = _coerce_level(level)
    lo, hi = LEVEL_COMPOSITE_TYPICAL.get(s, (40.0, 60.0))
    return {
        "low": lo,
        "high": hi,
        "mid": round((lo + hi) / 2, 1),
        "caption": "Directional band for this level in this experience — coaching, not a performance target.",
    }


def position_versus_typical_composite(
    aiq: Optional[float], level: str
) -> Dict[str, Any]:
    """
    How the reported composite sits vs. the *typical* band for the chosen seniority.
    """
    t = typical_composite_for_level(level)
    lo, hi = t["low"], t["high"]
    if aiq is None or (isinstance(aiq, str) and not str(aiq).strip()):
        return {
            "key": "unknown",
            "label": "—",
            "tint": "neutral",
        }
    try:
        a = max(0.0, min(100.0, float(aiq)))
    except (TypeError, ValueError):
        return {"key": "unknown", "label": "—", "tint": "neutral"}
    if a < lo - 8.0:
        k, lab, ti = "well_below", "Well below the typical range for your level", "amber"
    elif a < lo:
        k, lab, ti = "below", "Below the typical range for your level", "amber"
    elif a <= hi:
        k, lab, ti = "within", "Within the typical range for your level", "emerald"
    elif a <= hi + 9.0:
        k, lab, ti = "above", "Above the typical range for your level", "violet"
    else:
        k, lab, ti = "well_above", "Well above the typical range for your level", "violet"
    return {"key": k, "label": lab, "tint": ti}


def _top_two_dimensions_by_weight(weights: Dict[str, float]) -> Tuple[str, str]:
    """Tie-break: lower D# first (D1 < D2 < …) when scores are even."""
    ranked = sorted(
        _DIM_ORDER,
        key=lambda c: (-round(float(weights.get(c, 0) or 0.0), 4), c),
    )
    return ranked[0], ranked[1]


def build_assessment_block(
    level_raw: Optional[str],
    family_raw: Optional[str],
) -> Dict[str, Any]:
    level = _coerce_level(level_raw)
    fam = _coerce_family(family_raw)
    w = _weights_from_deltas(level, fam)
    pid = profile_id(level, fam)
    a, b = _top_two_dimensions_by_weight(w)
    return {
        "version": 1,
        "level": level,
        "level_label": label_for_level(level),
        "job_family": fam,
        "job_family_label": label_for_family(fam),
        "profile_id": pid,
        "weights": w,
        "depth_focus": [a, b],
        "depth_focus_display": [
            DIMENSION_DECK_LABELS.get(a, a),
            DIMENSION_DECK_LABELS.get(b, b),
        ],
        "typical_composite": typical_composite_for_level(level),
    }


# --- Rigid instructions for the scoring model (repeatable) ------------------------


def scoring_context_block(ass: Dict[str, Any]) -> str:
    w = ass.get("weights") or {}
    L = ass.get("level_label", "")
    F = ass.get("job_family_label", "")
    lines = [
        "**Assessment profile (mandatory; do not override):**",
        f"- **Level (seniority):** {L} — interpret what counts as *strong evidence* for this seniority. "
        "E.g. IC: hands-on use, craft, execution; people manager: team habits & coaching; "
        "head of: function-wide patterns & trade-offs; executive: portfolio, governance, and narrative, "
        "without expecting hands-on minutiae unless offered.",
        f"- **Job family:** {F} — interpret each dimension in *this* professional context. "
        "D2 (prompts/comms) for legal ≠ for sales; D4 (workflows/org) for support ops ≠ for R&D. "
        "If the role would not plausibly own a topic, do **not** penalize absence of that minutiae; look for the family-relevant *kind* of signal.",
        "- **D5 (clarity, craft, output fit):** applies to *every* role: quality and appropriateness of **AI-supported work others see** (internal or external) — not “brand marketing” only. GTM roles may add market-facing narrative; others still have docs, comms, tickets, and deliverables here.",
        "- **Dimension weights (use exactly these; sum = 1.0):**",
    ]
    for c in _DIM_ORDER:
        if c in w:
            lines.append(f"  - {c}: {w[c]:.4f}")
    return "\n".join(lines)


def interviewer_profile_note(ass: Optional[Dict[str, Any]]) -> str:
    if not ass or not ass.get("level"):
        return ""
    L = ass.get("level_label", "")
    F = ass.get("job_family_label", "")
    w = ass.get("weights") or {}
    wshow = "/".join(f"{c}:{w[c]:.0%}" for c in _DIM_ORDER if c in w)
    depth = (ass or {}).get("depth_focus")
    a = b = ""
    if (
        isinstance(depth, (list, tuple))
        and len(depth) >= 2
        and all(isinstance(x, str) for x in depth[:2])
    ):
        a, b = depth[0], depth[1]
    else:
        a, b = _top_two_dimensions_by_weight(w)
    d_a = _DIM_NICK.get(a, a)
    d_b = _DIM_NICK.get(b, b)
    return (
        f"**Session calibration (use for tone & altitude; do not recite to user):** "
        f"Participant is **{L}** in **{F}**. **Purpose: reflection and coaching, not a ranking or exam.** Calibrate tone to invite *their* next step, not judgment. "
        f"Match question depth: exec → portfolio, trade-offs, and how they set expectations; IC → craft and concrete work; in between, split the difference. "
        f"**Every** substantive question must stay anchored to how they work with *generative AI* (models, copilots, AI in their workflows) in *that* job — not to generic “process / QA of people” with no model in the frame. "
        f"Elicit evidence in rough proportion to: {wshow} — *without* naming D-codes, weights, or 'dimensions' to the user.\n\n"
        f"**Session shape (structural; internal only):** "
        f"Aim to **touch** all **six** AiQ angles **once each** in a *light* way (one main question per area when you naturally change angle). "
        f"Then go **in depth** on **exactly these two** areas for *this* profile: **{a}** and **{b}** (interpret as: {d_a}; and {d_b}.). "
        f"“In depth” = one clear extra pass each: a follow-up to sharpen *concrete* behavior, trade-off, or habit, **or** a second main question in that same angle — still respect your global follow-up and dimension limits. "
        f"**D5** for *every* role: treat as **quality, clarity, and appropriateness of AI-supported work product others see** (emails, specs, support replies, code reviews, etc.), not as “brand marketing” only for GTM. "
        f"**D6** for *every* role: cover the **universal** floor in the *spirit* of org-wide **security, data, AML-style** training: what they *never* put in a model, when they *escalate*, where the line is, without assuming everyone owns Regulator/ vendor diligence — **deeper** policy and third-party *only* if they are in risk_legal *or* they *raised* compliance, vendors, or regulators in this chat."
    )


# Legacy sessions without an assessment block
def default_assessment() -> Dict[str, Any]:
    return build_assessment_block(DEFAULT_LEVEL, DEFAULT_FAMILY)
