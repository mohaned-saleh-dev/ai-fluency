"""
Scenario-stack AiQ interview: adaptive probes, evidence extraction, LLM report.
Maps observed fluency to existing D1–D6 at scoring time (no extra dimension).
"""

from __future__ import annotations

import json
import random
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from coaching_engine import fam_cluster
from config import BASE_DIR
from llm_json import llm_json

_LIBRARY_PATH = BASE_DIR / "knowledge" / "scenario_library.json"

PHASES: List[Tuple[str, str]] = [
    ("anchor", "Context"),
    ("primary", "Main scenario"),
    ("complication", "When it goes wrong"),
    ("standards", "Bar for others"),
    ("close", "Wrap-up"),
]

# Tight budgets so a real ~10 min session finishes standards + close (not stuck in primary).
PHASE_MAX_TURNS: Dict[str, int] = {
    "anchor": 1,
    "primary": 2,
    "complication": 1,
    "standards": 1,
    "close": 1,
}

MAX_USER_TURNS = 6

_THIN_PATTERNS = re.compile(
    r"^(nothing specific|not sure|n/?a|no idea|don'?t know|none|no\b|not really|"
    r"nothing yet|tell the team to be careful|be careful|i guess|just use ai|"
    r"move fast|trust the tools|everyone should use ai)",
    re.I,
)
_VAGUE_HYPE = re.compile(
    r"\b(game changer|amazing|all the ai|everything|move fast|trust the tools|"
    r"so much faster|use ai more)\b",
    re.I,
)
_COMPLICATION_SIGNALS = re.compile(
    r"\b(security|incident|pii|customer id|paste|pasted|leak|breach|retention|"
    r"kill the thread|escalat|wrong (number|amount|metric)|hallucin|vendor demo|"
    r"synthetic metric|never goes in|shared gpt|chatgpt thread)\b",
    re.I,
)
_BANNED_STEM = re.compile(
    r"^\s*in the (scenario|context of the scenario|light of the scenario)\b",
    re.I,
)
_IN_SCENARIO_LOOP = re.compile(
    r"\b(in the scenario where you|when evaluating the model-written|"
    r"automation (versus|vs\.?) forecasting|supporting automation)\b",
    re.I,
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
_TA_SIGNALS = re.compile(
    r"\b(talent acquisition|head of ta|ta lead|recruiting|recruiter|"
    r"sourcing|candidate outreach|offer letter|job description|hiring manager|"
    r"applicant tracking|\bats\b)\b",
    re.I,
)
_ER_SIGNALS = re.compile(
    r"\b(employee relations|\ber\b|workplace investigation|disciplinary|"
    r"grievance|harassment|conduct case|investigation)\b",
    re.I,
)
_COMP_SIGNALS = re.compile(
    r"\b(compensation|comp and benefits|total rewards|pay equity|salary band|"
    r"pay review|payroll)\b",
    re.I,
)
_LD_SIGNALS = re.compile(
    r"\b(learning and development|l&d|training team|onboarding program|"
    r"curriculum|enablement|facilitator)\b",
    re.I,
)
_HRBP_SIGNALS = re.compile(
    r"\b(hrbp|hr business partner|people partner|people advisory|"
    r"business partner)\b",
    re.I,
)
_GTM_SALES_SIGNALS = re.compile(
    r"\b(sales|account executive|ae\b|enterprise sales|bdr|sdr|"
    r"revenue team|deal desk)\b",
    re.I,
)
_GTM_BRAND_SIGNALS = re.compile(
    r"\b(brand|communications|comms|creative|pr\b|public relations|"
    r"social media|content marketing)\b",
    re.I,
)

# Most specific match wins (first in list).
_PEOPLE_VARIANTS: List[Tuple[str, re.Pattern]] = [
    ("people_er", _ER_SIGNALS),
    ("people_comp", _COMP_SIGNALS),
    ("people_ld", _LD_SIGNALS),
    ("people_ta", _TA_SIGNALS),
    ("people_hrbp", _HRBP_SIGNALS),
]
_GTM_VARIANTS: List[Tuple[str, re.Pattern]] = [
    ("gtm_brand", _GTM_BRAND_SIGNALS),
    ("gtm_sales", _GTM_SALES_SIGNALS),
]


def _is_clarification_request(text: str) -> bool:
    """True when the user is asking us to explain/rephrase, not answering the question."""
    t = (text or "").strip()
    if not t:
        return False
    if t and set(t) <= {"?", " "}:
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


def _first_anchor_user_message(messages: List[dict]) -> str:
    """First user reply after the opening — their stated role and tools."""
    seen_model = False
    for m in messages:
        role = (m.get("role") or "").strip()
        if role == "model":
            seen_model = True
            continue
        if role == "user" and seen_model:
            return (m.get("content") or "").strip()
    return ""


def _scenario_from_library_key(key: str) -> Dict[str, Any]:
    base = dict(_load_library().get(key) or {})
    if not base:
        return {}
    out: Dict[str, Any] = {
        "cluster": key,
        "primary": {
            "title": base.get("primary_title", ""),
            "setup": base.get("primary_setup", ""),
            "stakes": base.get("primary_stakes", ""),
        },
        "complication": {"inject": base.get("complication_inject", "")},
        "standards": {"focus": base.get("standards_prompt", "")},
    }
    if base.get("probe_bank"):
        out["probe_bank"] = list(base["probe_bank"])
    if base.get("standards_question"):
        out["standards_question"] = base["standards_question"]
    return out


def _pick_variant_key(cluster: str, anchor: str, variants: List[Tuple[str, re.Pattern]]) -> Optional[str]:
    for key, pattern in variants:
        if pattern.search(anchor):
            return key
    return None


def _messages_for_context(history: List[dict], user_message: str) -> List[dict]:
    """History plus the in-flight user reply (not yet appended when plan_and_render runs)."""
    msgs = list(history)
    if (user_message or "").strip():
        msgs.append({"role": "user", "content": user_message})
    return msgs


def _apply_anchor_context(plan: dict, messages: List[dict]) -> dict:
    """Swap generic scenarios for sub-variants when the anchor answer names a specific role."""
    out = dict(plan)
    anchor = _first_anchor_user_message(messages)
    if not anchor:
        return out
    out["anchor_snippet"] = anchor[:400]
    cluster = str(out.get("cluster") or "")
    variant_key: Optional[str] = None
    if cluster == "people":
        variant_key = _pick_variant_key(cluster, anchor, _PEOPLE_VARIANTS)
    elif cluster == "gtm":
        variant_key = _pick_variant_key(cluster, anchor, _GTM_VARIANTS)
    if variant_key:
        picked = _scenario_from_library_key(variant_key)
        if picked:
            out.update(picked)
            out["anchor_role"] = variant_key.replace("people_", "").replace("gtm_", "")
    return out

_THIN_PROBE_BY_PHASE: Dict[str, str] = {
    "primary": (
        "Let's make it concrete — what would you actually do first here?"
    ),
    "complication": (
        "What's the very first thing you'd do once you noticed this?"
    ),
    "standards": (
        "What's one simple rule you'd want everyone on your team to follow before they use AI for this?"
    ),
}

_PUSHBACK_VAGUE = (
    "Faster is good — but is there anything in that AI output you'd want to "
    "double-check by hand before you trusted it?"
)

FACETS = (
    "tools_in_use",
    "prompt_behavior",
    "verification",
    "workflow_ownership",
    "output_bar",
    "risk_floor",
)


def _load_library() -> dict:
    return json.loads(_LIBRARY_PATH.read_text(encoding="utf-8"))


def _scenario_cluster(fam: str, level: str) -> str:
    """Pick library cluster; COO/strategy ops execs get coo_office not generic portfolio."""
    base = fam_cluster(fam)
    if fam in ("general_management",) and level in ("head_of", "executive", "people_manager"):
        return "coo_office"
    return base


def build_scenario_plan(assessment: dict, client_seed: str) -> dict:
    """Role-specific scenario brief stored in variation_json."""
    ass = assessment or {}
    fam = str(ass.get("job_family") or "other")
    level = str(ass.get("level") or "head_of")
    cluster = _scenario_cluster(fam, level)
    lib = _load_library()
    base = dict(lib.get(cluster) or lib.get("gm") or {})
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
        "job_family_label": ass.get("job_family_label") or fam,
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


def _model_turns_in_current_phase(messages: List[dict], phase_history: List[str]) -> int:
    model_count = sum(1 for m in messages if (m.get("role") or "") == "model")
    current = phase_history[-1] if phase_history else "anchor"
    phase_idx = next((i for i, (c, _) in enumerate(PHASES) if c == current), 0)
    prior_budget = sum(PHASE_MAX_TURNS.get(PHASES[i][0], 1) for i in range(phase_idx))
    return max(0, model_count - prior_budget)


def _is_thin_answer(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return True
    words = [w for w in t.split() if w]
    if len(words) <= 8:
        return True
    if _THIN_PATTERNS.search(t):
        return True
    return False


def _is_vague_hype(text: str) -> bool:
    t = (text or "").strip()
    if len(t.split()) > 28:
        return False
    return bool(_VAGUE_HYPE.search(t)) and not re.search(
        r"\b(prompt|paste|check|review|forbid|escalat|security|compliance|owner)\b", t, re.I
    )


def _user_signals_complication(text: str) -> bool:
    return bool(_COMPLICATION_SIGNALS.search(text or ""))


def _recent_assistant_questions(messages: List[dict], n: int = 4) -> List[str]:
    out: List[str] = []
    for m in reversed(messages):
        if (m.get("role") or "") != "model":
            continue
        c = (m.get("content") or "").strip()
        if "?" in c:
            out.append(c.lower())
        if len(out) >= n:
            break
    return out


def _question_is_repetitive(question: str, history: List[dict]) -> bool:
    q = (question or "").strip().lower()
    if _BANNED_STEM.search(q) or _IN_SCENARIO_LOOP.search(q):
        return True
    recent = _recent_assistant_questions(history, 3)
    q_words = set(re.findall(r"[a-z]{4,}", q))
    for prev in recent:
        prev_words = set(re.findall(r"[a-z]{4,}", prev))
        if not q_words:
            continue
        overlap = len(q_words & prev_words) / max(1, len(q_words))
        if overlap >= 0.55:
            return True
    return False


def _pick_probe(phase: str, plan: dict, slot: int) -> str:
    bank = plan.get("probe_bank") or []
    if phase == "primary" and bank:
        return bank[slot % len(bank)]
    if phase == "complication":
        return "What's the first thing you'd do right now to deal with this?"
    if phase == "standards":
        sq = (plan.get("standards_question") or "").strip()
        if sq:
            return sq
        return _THIN_PROBE_BY_PHASE["standards"]
    if phase == "close":
        return "Looking back, what's one thing you'd do differently next time you use AI for something like this?"
    return bank[slot % len(bank)] if bank else _fallback_question(phase, plan, "")


def _finalize_question(
    question: str,
    phase: str,
    plan: dict,
    history: List[dict],
    *,
    thin: bool,
    vague: bool,
    probe_slot: int,
) -> str:
    q = _strip_soft_opener((question or "").strip())
    if vague and phase == "primary":
        return _PUSHBACK_VAGUE
    if thin and phase in _THIN_PROBE_BY_PHASE:
        return _THIN_PROBE_BY_PHASE[phase]
    if not q or "?" not in q or _question_is_repetitive(q, history):
        q = _pick_probe(phase, plan, probe_slot)
    q = _strip_soft_opener(q)
    if _BANNED_STEM.search(q):
        q = _pick_probe(phase, plan, probe_slot + 1)
    return q if "?" in q else _fallback_question(phase, plan, "")


def compute_flow_state(
    messages: List[dict],
    phase_history: List[str],
    *,
    last_user_message: str = "",
    force_close: bool = False,
) -> dict:
    """Derive current phase and turn budget from messages + phase_shift history."""
    current = phase_history[-1] if phase_history else "anchor"
    idx = next((i for i, (c, _) in enumerate(PHASES) if c == current), 0)
    model_turns_in_phase = _model_turns_in_current_phase(messages, phase_history)

    clarifying = _is_clarification_request(last_user_message)
    prior_clarify = 0
    for m in reversed(messages):
        if (m.get("role") or "") != "user":
            continue
        if _is_clarification_request(m.get("content") or ""):
            prior_clarify += 1
        else:
            break
    clarify_streak = (prior_clarify + 1) if clarifying else 0

    max_turns = PHASE_MAX_TURNS.get(current, 2)
    user_turns = sum(1 for m in messages if (m.get("role") or "") == "user")
    must_advance = model_turns_in_phase >= max_turns
    if _is_thin_answer(last_user_message) and current in ("anchor", "primary"):
        must_advance = True
    if _user_signals_complication(last_user_message) and current == "primary":
        must_advance = True
    if force_close:
        must_advance = True
    # A clarification request is not an answer — hold the current question, don't advance.
    if clarifying and not force_close:
        must_advance = False
    pending = [c for c, _ in PHASES[idx + 1 :]]
    next_phase = pending[0] if pending else None
    if force_close:
        next_phase = "close" if current != "close" else None
    elif clarifying:
        next_phase = None
    elif _user_signals_complication(last_user_message) and current == "primary":
        next_phase = "complication"
    next_label = dict(PHASES).get(next_phase or "", "")
    phases_done = list(dict.fromkeys(phase_history))
    return {
        "current_phase": current,
        "current_label": dict(PHASES).get(current, current),
        "phase_index": idx,
        "total_phases": len(PHASES),
        "model_turns_in_phase": model_turns_in_phase,
        "max_turns_in_phase": max_turns,
        "must_advance_phase": must_advance,
        "next_phase": next_phase,
        "next_label": next_label,
        "phases_completed": phases_done,
        "user_turns": user_turns,
        "all_phases_done": current == "close" and must_advance,
        "force_close": force_close,
        "clarifying": clarifying,
        "clarify_streak": clarify_streak,
    }


def _transcript_excerpt(messages: List[dict], max_chars: int = 12000) -> str:
    lines = []
    for m in messages[-24:]:
        role = "USER" if (m.get("role") or "") == "user" else "ASSISTANT"
        lines.append(f"{role}: {(m.get('content') or '')[:2000]}")
    return "\n\n".join(lines)[-max_chars:]


_SOFT_OPENER = re.compile(
    r"^\s*(that[’']?s\s+(great|significant|interesting|smart|clear|a great point|helpful|good)|"
    r"it sounds like|understood|i appreciate|that sounds|great\b|nice\b|wonderful\b|wow\b|"
    r"thanks for sharing|thank you for|i hear you|makes sense)[^\n.!?]*[.!?]?\s*",
    re.IGNORECASE,
)


def _strip_soft_opener(s: str) -> str:
    t = (s or "").lstrip()
    for _ in range(2):
        new = _SOFT_OPENER.sub("", t, count=1).lstrip()
        if new == t:
            break
        t = new
    return t


def _scenario_brief_for(phase: str, plan: dict) -> str:
    """Natural narration for a phase entry — no stage-direction labels shown to the user."""
    if phase == "primary":
        primary = plan.get("primary") or {}
        setup = (primary.get("setup", "") or "").strip()
        stakes = (primary.get("stakes", "") or "").strip()
        body = f"Here's something that could happen in your week. {setup}".strip()
        if stakes:
            body = f"{body} {stakes}"
        return body
    if phase == "complication":
        inject = ((plan.get("complication") or {}).get("inject", "") or "").strip()
        if inject:
            return f"Something goes wrong. {inject}"
    if phase == "standards":
        focus = ((plan.get("standards") or {}).get("focus", "") or "").strip()
        if focus:
            return focus
    return ""


def plan_and_render_turn(
    flow: dict,
    variation: dict,
    history: List[dict],
    user_message: str,
    context_note: str,
) -> dict:
    """
    Server-controlled phase + scenario presentation; LLM only writes the question.
    Returns {reply, phase_shift?, session_suggests_complete, planner_meta}.
    """
    plan = _apply_anchor_context(
        dict(variation.get("scenario_plan") or {}),
        _messages_for_context(history, user_message),
    )
    ass = variation.get("assessment") or {}
    current_phase = flow.get("current_phase") or "anchor"
    must_adv = bool(flow.get("must_advance_phase"))
    next_phase = flow.get("next_phase")
    thin = _is_thin_answer(user_message)
    vague = _is_vague_hype(user_message)
    probe_slot = int(flow.get("model_turns_in_phase") or 0)

    # The user asked us to explain — answer scenario facts, then re-ask; never advance.
    if flow.get("clarifying"):
        last_q = _last_assistant_question(history)
        reply = _answer_clarification(
            user_message,
            last_q,
            current_phase,
            plan,
            simplest=int(flow.get("clarify_streak") or 0) >= 3,
        )
        return {
            "reply": reply,
            "phase_shift": None,
            "session_suggests_complete": False,
            "planner_meta": {
                "phase": current_phase,
                "is_phase_entry": False,
                "clarifying": True,
                "clarify_streak": int(flow.get("clarify_streak") or 0),
            },
        }

    if must_adv and next_phase:
        phase = next_phase
        is_phase_entry = True
    else:
        phase = current_phase
        is_phase_entry = False

    # Server-authored questions — no planner LLM on the hot path (predictable, role-specific).
    out: Dict[str, Any] = {}
    slot = 0 if is_phase_entry else probe_slot
    if thin and phase in _THIN_PROBE_BY_PHASE and not is_phase_entry:
        question = _THIN_PROBE_BY_PHASE[phase]
    elif vague and phase == "primary" and not is_phase_entry:
        question = _PUSHBACK_VAGUE
    elif phase in ("anchor", "primary", "complication", "standards", "close"):
        question = _pick_probe(phase, plan, slot)
    else:
        question = _fallback_question(phase, plan, user_message)

    question = _finalize_question(
        question,
        phase,
        plan,
        history,
        thin=thin and not is_phase_entry,
        vague=vague and not is_phase_entry,
        probe_slot=probe_slot,
    )

    session_complete = bool((out or {}).get("session_complete")) or bool(flow.get("force_close"))
    if phase == "close":
        session_complete = True

    phase_brief = _scenario_brief_for(phase, plan) if is_phase_entry else ""
    # After anchor, acknowledge their role briefly before the scenario.
    if is_phase_entry and phase == "primary" and plan.get("anchor_snippet"):
        role_ack = "Got it — keeping your role in mind."
        phase_brief = f"{role_ack}\n\n{phase_brief}" if phase_brief else role_ack
    body_parts: List[str] = []
    if phase_brief:
        body_parts.append(phase_brief)
    body_parts.append(question)
    reply = "\n\n".join(p for p in body_parts if p).strip()

    if session_complete:
        reply = (
            reply.rstrip()
            + "\n\nWhen you are ready, tap **End session & view results** below — that opens your summary from this chat.\n[SESSION_COMPLETE]"
        )

    phase_shift = None
    if is_phase_entry and phase != current_phase:
        phase_shift = {
            "phase": phase,
            "label": dict(PHASES).get(phase, phase),
        }

    return {
        "reply": reply,
        "phase_shift": phase_shift,
        "session_suggests_complete": session_complete,
        "planner_meta": {
            "internal_tags": (out or {}).get("internal_tags") or [],
            "missing_facets": (out or {}).get("missing_facets") or [],
            "phase": phase,
            "is_phase_entry": is_phase_entry,
            "thin": thin,
            "vague": vague,
        },
    }


def _last_assistant_question(history: List[dict]) -> str:
    for m in reversed(history):
        if (m.get("role") or "") == "model":
            return (m.get("content") or "").strip()
    return ""


def _answer_clarification(
    user_message: str,
    last_q: str,
    phase: str,
    plan: dict,
    *,
    simplest: bool,
) -> str:
    """Answer factual questions about the scenario, then re-ask the same question simply."""
    if simplest or not last_q:
        return _clarification_fallback(user_message, last_q, plan, phase)

    scenario_ctx = json.dumps(
        {
            "primary": plan.get("primary") or {},
            "complication": plan.get("complication") or {},
            "phase": phase,
        },
        ensure_ascii=False,
    )[:1400]
    prompt = f"""The participant is in a work-scenario interview and asked a CLARIFICATION — they are NOT answering yet.

Their clarification: {user_message[:500]}

Last question we asked:
{last_q[:700]}

Scenario context (canonical facts — use these):
{scenario_ctx}

Rules:
- First: answer their clarification in 1-2 short plain sentences. Set facts clearly (e.g. draft not sent yet, still on screen, not published, you're reviewing before it goes out). Use the scenario context.
- Then: repeat essentially the SAME question as last_q, in simpler words. One question only, ending with `?`.
- Do NOT ask about "guidelines" or "rules for the team" unless that was the last question.
- Do NOT switch topic. Max 55 words total.
- No preamble like "Sure" or "Great question".

Return JSON only: {{"reply": "..."}}"""
    try:
        out = llm_json(prompt, temperature=0.15, max_tokens=220)
        reply = _strip_soft_opener((out.get("reply") or "").strip())
        if reply and "?" in reply:
            return reply
    except Exception:
        pass
    return _clarification_fallback(user_message, last_q, plan, phase)


def _clarification_fallback(
    user_message: str, last_q: str, plan: dict, phase: str
) -> str:
    ul = (user_message or "").lower()
    inject = ((plan.get("complication") or {}).get("inject") or "").strip()
    if re.search(r"publish|sent|went out|gone out|live already|posted", ul):
        clarify = (
            "No — it has not gone out yet. You are still looking at a draft on your screen."
        )
    elif re.search(r"you mean|do you mean|rewrote|rewrite|softer", ul) and inject:
        clarify = (
            f"Right — {inject[0].lower()}{inject[1:] if len(inject) > 1 else inject} "
            "Nothing has been sent yet; you caught it while reviewing."
        )
    elif re.search(r"you mean|do you mean", ul):
        clarify = "Let me be clearer about what happened."
    else:
        clarify = "Good question — let me clarify."

    simple_q = _extract_last_question(last_q) or _fallback_question(phase, plan, user_message)
    return f"{clarify} {simple_q}"


def _extract_last_question(text: str) -> str:
    t = (text or "").replace("\n", " ").strip()
    if "?" not in t:
        return ""
    # Last sentence that is actually a question (not the scenario setup paragraph).
    chunks = re.split(r"(?<=[.!?])\s+", t)
    for chunk in reversed(chunks):
        c = chunk.strip()
        if c.endswith("?"):
            return c
    parts = [p.strip() for p in t.split("?") if p.strip()]
    return (parts[-1] + "?") if parts else ""


def _rephrase_simpler(last_q: str, phase: str, plan: dict, *, simplest: bool) -> str:
    """Re-ask the previous question in plainer words. Falls back to a simple phase question."""
    fallback = _fallback_question(phase, plan, "")
    if simplest or not last_q:
        return fallback
    prompt = f"""A person in an interview said they did not understand the last question. Rewrite it in much simpler, everyday language so anyone can understand it. Keep the same meaning. Be warm and brief.

Last question:
{last_q[:700]}

Rules:
- You may add one short plain-language sentence of context, then ONE simple question ending with `?`.
- Max 40 words total. No jargon, no buzzwords, no preamble like "Sure" or "Of course".
Return JSON only: {{"question": "..."}}"""
    try:
        out = llm_json(prompt, temperature=0.2, max_tokens=200)
        q = _strip_soft_opener((out.get("question") or "").strip())
        if q and "?" in q:
            return q
    except Exception:
        pass
    return fallback


def _fallback_question(phase: str, plan: dict, user_message: str) -> str:
    if phase == "anchor":
        return "Which AI tools do you actually use in a normal week, and what do you use them for?"
    if phase == "primary":
        return "What would you do first to handle this?"
    if phase == "complication":
        return "What's the first thing you'd do right now to deal with this?"
    if phase == "standards":
        return "What's one simple rule you'd want your team to follow before they use AI for this?"
    return "Looking back, what's one thing you'd do differently next time?"


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
Rules: quotes short (max 20 words each), paraphrase if needed. confidence low if thin chat. No markdown."""
    try:
        return llm_json(prompt, temperature=0.15, max_tokens=2800)
    except Exception:
        return {"facets": {}, "overall_gaps": [], "strongest_signals": []}


def generate_participant_narrative(
    messages: List[dict],
    evidence: dict,
    scores: dict,
    assessment: dict,
) -> dict:
    ass = assessment or {}
    prompt = f"""Write a **coaching report** for the person who was interviewed. Second person ("you"). Ground every point in the transcript and evidence — no generic HR boilerplate.

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
    from gemini_service import score_transcript

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
    """First line — anchor phase only (one quick question, then a real scenario)."""
    ass = variation.get("assessment") or {}
    fam = ass.get("job_family_label") or "your role"
    return (
        "This is a short AiQ chat — about ten minutes. "
        f"I'll ask how you'd handle one realistic situation in {fam}: what you'd do, what you'd check, who signs off.\n\n"
        "First: in one or two lines, what is your role, and which AI tools do you actually use in a normal week?"
    )


def progress_payload_from_flow(flow: dict, target_sec: int) -> dict:
    done = flow.get("phases_completed") or []
    cur = flow.get("current_phase")
    idx = int(flow.get("phase_index") or 0)
    return {
        "mode": "scenario",
        "phases": [{"code": c, "label": lbl} for c, lbl in PHASES],
        "touched": done,
        "current": cur,
        "current_label": flow.get("current_label") or cur,
        "phase_index": idx,
        "total_phases": len(PHASES),
        "target_sec": target_sec,
        "labels": {c: lbl for c, lbl in PHASES},
    }
