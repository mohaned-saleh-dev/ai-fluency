"""
Scenario selection + post-session scoring pipeline.

Live conversation turns are handled by conversation_engine (LLM-driven); this module
owns what surrounds them:
- build_scenario_plan / opening_message — pick the scenario material for a session.
- extract_session_evidence → score (llm_service.score_transcript) → participant
  narrative — the report pipeline that runs when a session ends.
- _is_clarification_request — shared heuristic app.py uses in its effort signal.
"""

from __future__ import annotations

import json
import random
import re
from typing import Any, Dict, List, Optional

from coaching_engine import fam_cluster
from config import BASE_DIR
from llm_json import llm_json

_LIBRARY_PATH = BASE_DIR / "knowledge" / "scenario_library.json"

# Facets the evidence extractor reports; they map onto D1..D6 at scoring time.
FACETS = (
    "tools_in_use",
    "prompt_behavior",
    "verification",
    "workflow_ownership",
    "output_bar",
    "risk_floor",
)

_CLARIFY_PATTERNS = re.compile(
    r"(what do you mean|you mean\b|do you mean|are you saying\b|"
    r"i don'?t (understand|get it|follow|know what you)|"
    r"not sure what you (mean|are asking)|can you (clarify|explain|rephrase|simplify|elaborate|repeat|be more specific)|"
    r"could you (clarify|explain|rephrase|simplify|repeat)|come again|say that again|"
    r"rephrase|repeat the question|don'?t understand( the| your)? question|"
    r"unclear|confus(ed|ing)|explain (that|the question|what)|in plain|simpl(er|y that)|"
    r"didn'?t (get|understand)|lost me|what'?s that mean|meaning of|"
    r"was it (already |)(sent|published|posted|live|out)|has it (been |)(sent|published|posted)|"
    r"published already|gone out|went out|still (a |just a )?draft|not yet sent|"
    r"^huh\b|^sorry\?|^what\?|too (complex|complicated|technical)|^wait[, ]|^just to clarify)",
    re.I,
)

_PURPOSE_PATTERNS = re.compile(
    r"(what('?s| is) (the )?(purpose|point|goal|aim|objective)\b|"
    r"why (are we|am i|do we) (doing|having|talking)|"
    r"what('?s| is) this (chat|conversation|session|assessment|thing)? ?(for|about)?\b|"
    r"who are you\b|what are you\b|are you (a |an )?(bot|ai|human)|"
    r"what (do you|will you|happens? (to|with)) (do with )?(my|the) (answers|responses|data|info)|"
    r"is this (a |)(test|exam|graded|scored|evaluation)|"
    r"how long (is|does|will) this|what should i (do|say|answer) here)",
    re.I,
)


def _is_purpose_question(text: str) -> bool:
    """Meta question about the session itself ('what is this chat for?', 'is this a test?')."""
    t = (text or "").strip()
    return bool(t) and len(t.split()) <= 25 and bool(_PURPOSE_PATTERNS.search(t))


def _is_clarification_request(text: str) -> bool:
    """True when the user is asking us to explain/rephrase, not answering the question."""
    t = (text or "").strip()
    if not t:
        return False
    if t and set(t) <= {"?", " "}:
        return True
    if _is_purpose_question(t):
        return True
    if len(t.split()) > 22:
        return False
    if _CLARIFY_PATTERNS.search(t):
        return True
    # Short question without a substantive answer — likely checking scenario facts.
    if t.rstrip().endswith("?") and len(t.split()) <= 14:
        if re.search(
            r"\b(already|published|sent|posted|live|draft|mean|clarify|understand|scenario)\b",
            t,
            re.I,
        ):
            return True
    return False


def _load_library() -> dict:
    return json.loads(_LIBRARY_PATH.read_text(encoding="utf-8"))


def _scenario_cluster(fam: str, level: str) -> str:
    """Pick library cluster. Senior/leadership tiers get a strategic scenario instead of the
    tactical IC one: general_management → coo_office; product_engineering → product_exec;
    care_operations → ops_exec. ic and people_manager keep the hands-on scenario."""
    base = fam_cluster(fam)
    if fam == "general_management" and level in ("head_of", "executive", "people_manager"):
        return "coo_office"
    if fam == "product_engineering" and level in ("head_of", "executive"):
        return "product_exec"
    if fam == "care_operations" and level in ("head_of", "executive"):
        return "ops_exec"
    return base


def build_scenario_plan(assessment: dict, client_seed: str) -> dict:
    """Role-specific scenario brief stored in variation_json."""
    ass = assessment or {}
    fam = str(ass.get("job_family") or "other")
    level = str(ass.get("level") or "head_of")
    lib = _load_library()
    # A specific job function (e.g. Care → Strategy & Ops) can point at its own scenario,
    # decoupled from the coarse job_family used for dimension weights. Fall back to the
    # family/level cluster when no populated function-specific scenario exists.
    func = str(ass.get("job_function") or "").strip()
    func_entry = lib.get(func) if func else None
    if isinstance(func_entry, dict) and str(func_entry.get("primary_setup") or "").strip():
        cluster = func
    else:
        cluster = _scenario_cluster(fam, level)
    base = dict(lib.get(cluster) or {})
    if not str(base.get("primary_setup") or "").strip():
        # Never run a session on a missing or blank library entry — a scenario with no
        # setup silently degrades the interview into a generic Q&A. Fall back to the
        # generic scenario and record the cluster we actually used.
        cluster = "gm"
        base = dict(lib.get("gm") or {})
    rng = random.Random(client_seed)
    level_note = {
        "ic": "Ask for hands-on detail: their own prompts, edits, and checks.",
        "people_manager": "Ask how they coach the team, not only personal use.",
        "head_of": "Ask for function-wide patterns, owners, and trade-offs.",
        "executive": "Ask for portfolio, governance, and how they set expectations.",
    }.get(level, "Match seniority in depth.")

    return {
        "version": 2,
        "cluster": cluster,
        "level": level,
        "level_note": level_note,
        "job_family_label": ass.get("job_function_label") or ass.get("job_family_label") or fam,
        "primary": {
            "title": base.get("primary_title", "Work scenario"),
            "setup": base.get("primary_setup", ""),
            "stakes": base.get("primary_stakes", ""),
        },
        "complication": {
            "inject": base.get("complication_inject", ""),
        },
        "standards": {
            "focus": base.get("standards_prompt", ""),
        },
        "probe_bank": list(
            base.get("probe_bank")
            or [
                "What would you do first to handle this?",
                "The draft looks good at first glance. What would you check before anyone else sees it?",
                "Who else needs to read or sign off on this before it goes out?",
            ]
        ),
        "standards_question": base.get("standards_question") or "",
        "opening_id": rng.randrange(0, 6),
    }


def _transcript_excerpt(messages: List[dict], max_chars: int = 12000) -> str:
    lines = []
    for m in messages[-24:]:
        role = "USER" if (m.get("role") or "") == "user" else "ASSISTANT"
        lines.append(f"{role}: {(m.get('content') or '')[:2000]}")
    return "\n\n".join(lines)[-max_chars:]


def extract_session_evidence(
    messages: List[dict], variation: dict
) -> dict:
    ass = variation.get("assessment") or {}
    plan = variation.get("scenario_plan") or {}
    prompt = f"""Extract **evidence only** from this AiQ interview transcript. Do not score yet.

Profile: {ass.get("level_label")} / {ass.get("job_family_label")}
Scenario: {json.dumps(plan.get("primary") or {}, ensure_ascii=False)[:800]}

Transcript:
{_transcript_excerpt(messages, 50000)}

Return JSON:
{{
  "facets": {{
    "tools_in_use": {{"observed": "", "confidence": "high|medium|low", "quotes": []}},
    "prompt_behavior": {{...}},
    "verification": {{...}},
    "workflow_ownership": {{...}},
    "output_bar": {{...}},
    "risk_floor": {{...}}
  }},
  "overall_gaps": [],
  "strongest_signals": []
}}
Rules: quotes are short (max 20 words each) **verbatim** excerpts from the USER's own turns — copy word-for-word, never paraphrase or invent; use an empty list when the user said nothing relevant (summaries belong in "observed"). confidence low if thin chat. No markdown."""
    try:
        out = llm_json(prompt, temperature=0.15, max_tokens=2800)
    except Exception:
        return {"facets": {}, "overall_gaps": [], "strongest_signals": []}
    return _ground_facet_quotes(out, messages)


def _ground_facet_quotes(evidence: dict, messages: List[dict]) -> dict:
    """Drop facet quotes that aren't actually grounded in the participant's own words — same
    guard the dimension scorer applies to its evidence_quotes, so nothing downstream (narrative,
    admin) treats an invented line as something the participant said."""
    if not isinstance(evidence, dict):
        return evidence
    facets = evidence.get("facets")
    if not isinstance(facets, dict):
        return evidence

    def norm(s: str) -> str:
        t = re.sub(r"[‘’“”'\"]", "", (s or "").lower())
        t = re.sub(r"[^a-z0-9\s]", " ", t)
        return re.sub(r"\s+", " ", t).strip()

    user_text = norm(
        " ".join(
            str(m.get("content") or "") for m in (messages or []) if (m.get("role") or "") == "user"
        )
    )
    user_words = set(user_text.split())
    for facet in facets.values():
        if not isinstance(facet, dict):
            continue
        raw = facet.get("quotes")
        if isinstance(raw, str):
            raw = [raw]
        cleaned: List[str] = []
        if isinstance(raw, list):
            for q in raw:
                if not isinstance(q, str) or not q.strip():
                    continue
                nq = norm(q)
                grounded = bool(nq) and (nq in user_text)
                if not grounded and nq and user_words:
                    qw = nq.split()
                    grounded = bool(qw) and sum(1 for w in qw if w in user_words) / len(qw) >= 0.8
                if grounded:
                    cleaned.append(q.strip()[:160])
                if len(cleaned) >= 2:
                    break
        facet["quotes"] = cleaned
    return evidence


def generate_participant_narrative(
    messages: List[dict],
    evidence: dict,
    scores: dict,
    assessment: dict,
) -> dict:
    ass = assessment or {}
    band = str(scores.get("maturity_band") or "")
    dim_scores = {
        f"D{i}": float((scores.get(f"D{i}") or {}).get("score", 0) or 0) for i in range(1, 7)
    }
    if band in ("AiQ1", "AiQ2"):
        tone_rule = (
            "TONE — the scores are in the lower bands, so the report must be candid and "
            "developmental: the executive_summary opens with an honest read of what was missing "
            "(warm, never shaming), and only then names what to build on. Never open with praise, "
            'never use "strong"/"excellent" for any behavior, and never call a habit strong when '
            "its dimension scored below 7."
        )
    elif band == "AiQ3":
        tone_rule = (
            "TONE — mid-band scores: balanced report. Name real strengths and real gaps with equal "
            'weight; reserve "strong" for dimensions that scored 7 or higher.'
        )
    else:
        tone_rule = (
            "TONE — high-band scores: confident report, but still lead the gaps section with the "
            "sharpest remaining gap; no empty superlatives."
        )
    prompt = f"""Write a **coaching report** for the person who was interviewed. Second person ("you"). Ground every point in the transcript and evidence — no generic HR boilerplate.

{tone_rule}
Per-dimension scores for calibration (0-10): {json.dumps(dim_scores)}

Profile: {ass.get("level_label")} / {ass.get("job_family_label")}
Scores (0-10): D1={(scores.get("D1") or {}).get("score")} D2={(scores.get("D2") or {}).get("score")} D3={(scores.get("D3") or {}).get("score")} D4={(scores.get("D4") or {}).get("score")} D5={(scores.get("D5") or {}).get("score")} D6={(scores.get("D6") or {}).get("score")} AiQ={scores.get("AiQ_0_100")} band={scores.get("maturity_band")}
Strength line: {scores.get("strength_1line")}
Risk line: {scores.get("risk_1line")}

Evidence JSON:
{json.dumps(evidence, ensure_ascii=False)[:6000]}

Transcript excerpt:
{_transcript_excerpt(messages, 8000)}

Return JSON only:
{{
  "executive_summary": "2-3 sentences",
  "what_we_saw": ["3-5 bullets tied to their words"],
  "strongest_habits": ["2-4 bullets"],
  "gaps_that_mattered": ["2-4 bullets — gaps in behavior shown, not moral judgment"],
  "next_steps": [
    {{"horizon": "this_week", "action": "specific action", "why": "tied to chat", "success_looks_like": "observable"}}
  ],
  "one_practice_drill": "5-min solo exercise",
  "per_dimension": {{
    "D1": {{"narrative": "2 sentences", "one_practice": "one sentence"}},
    "D2": {{...}},
    "D3": {{...}},
    "D4": {{...}},
    "D5": {{...}},
    "D6": {{...}}
  }}
}}
Rules: 3-5 next_steps, each action must reference something they said or did not show. No phrase "pick a routine deliverable". Strings: no unescaped double quotes inside values."""
    try:
        return llm_json(prompt, temperature=0.25, max_tokens=2400)
    except Exception:
        return {}


def run_post_session_pipeline(
    messages: List[dict], variation: dict
) -> dict:
    """Evidence → scores → narrative. Used on session complete."""
    from llm_service import score_transcript

    evidence = extract_session_evidence(messages, variation)
    scores = score_transcript(messages, variation, evidence=evidence)
    narrative = generate_participant_narrative(
        messages, evidence, scores, variation.get("assessment") or {}
    )
    return {
        "evidence": evidence,
        "scores": scores,
        "narrative": narrative,
        "version": 2,
    }


def opening_message(variation: dict) -> str:
    """First message of a session — asks for role + tools before any scenario appears."""
    ass = variation.get("assessment") or {}
    # Prefer the specific function the participant picked (e.g. "Strategy & Ops (Care)")
    # over the coarse scoring family, which reads wrong to them ("Finance, strategy…").
    fam = ass.get("job_function_label") or ass.get("job_family_label") or "your role"
    try:
        from llm_service import generate_opening_message
        llm = generate_opening_message(
            ass.get("level_label", ""),
            fam,
        )
        if llm:
            return llm
    except Exception:
        pass
    return (
        "This is a short AiQ chat — about ten minutes. "
        f"I'll ask how you'd handle one realistic situation in {fam}: what you'd do, what you'd check, who signs off.\n\n"
        "First: in one or two lines, what is your role, and which AI tools do you actually use in a normal week?"
    )
