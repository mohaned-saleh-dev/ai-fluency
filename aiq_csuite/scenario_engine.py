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

_THIN_PROBE_BY_PHASE: Dict[str, str] = {
    "primary": (
        "You gave a light answer — in three bullets, what would you paste into the model as input, "
        "what must it never invent, and who must read the output before anyone else acts on it?"
    ),
    "complication": (
        "Stay concrete: in the next hour, what is your first action, what do you stop immediately, "
        "and what data never goes into that tool again?"
    ),
    "standards": (
        "Who on your team must follow this bar, and what is the one check you require before "
        "AI-assisted work leaves your function?"
    ),
}

_PUSHBACK_VAGUE = (
    "You named speed but not a check — for this scenario, name one output you would "
    "**not** send without a human edit, and what you would verify line by line."
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
        "probe_bank": [
            "Walk through the first thing you would ask a model to do here — role, inputs, and what must not be invented.",
            "The output looks confident but may be wrong — what do you check before anyone else sees it?",
            "Who else must be in the loop before this ships, and what is the minimum bar?",
        ],
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
        return (
            "What are your first three moves in the next hour — who do you call, what do you stop, "
            "and what never goes into the tool again?"
        )
    if phase == "standards":
        focus = (plan.get("standards") or {}).get("focus", "")
        return focus or _THIN_PROBE_BY_PHASE["standards"]
    if phase == "close":
        return "What is one habit you would change next week in how you work with AI on this kind of task?"
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

    max_turns = PHASE_MAX_TURNS.get(current, 2)
    user_turns = sum(1 for m in messages if (m.get("role") or "") == "user")
    must_advance = model_turns_in_phase >= max_turns
    if _is_thin_answer(last_user_message) and current in ("anchor", "primary"):
        must_advance = True
    if _user_signals_complication(last_user_message) and current == "primary":
        must_advance = True
    if force_close:
        must_advance = True
    pending = [c for c, _ in PHASES[idx + 1 :]]
    next_phase = pending[0] if pending else None
    if force_close:
        next_phase = "close" if current != "close" else None
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
    if phase == "primary":
        primary = plan.get("primary") or {}
        title = primary.get("title", "Work scenario")
        setup = primary.get("setup", "")
        stakes = primary.get("stakes", "")
        body = f"**Scenario — {title}.** {setup}".strip()
        if stakes:
            body = f"{body} Why it matters: {stakes}"
        return body
    if phase == "complication":
        comp = plan.get("complication") or {}
        inject = comp.get("inject", "")
        if inject:
            return f"**Twist in the same scenario.** {inject}"
    if phase == "standards":
        focus = (plan.get("standards") or {}).get("focus", "")
        if focus:
            return f"**Stepping back from your own work — bar for others.** {focus}"
    if phase == "close":
        return "**One last reflection.**"
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
    plan = variation.get("scenario_plan") or {}
    ass = variation.get("assessment") or {}
    current_phase = flow.get("current_phase") or "anchor"
    must_adv = bool(flow.get("must_advance_phase"))
    next_phase = flow.get("next_phase")
    thin = _is_thin_answer(user_message)
    vague = _is_vague_hype(user_message)
    probe_slot = int(flow.get("model_turns_in_phase") or 0)

    if must_adv and next_phase:
        phase = next_phase
        is_phase_entry = True
    else:
        phase = current_phase
        is_phase_entry = False

    # Server-authored questions for thin/vague — skip LLM entirely.
    if thin and phase in _THIN_PROBE_BY_PHASE and not is_phase_entry:
        question = _THIN_PROBE_BY_PHASE[phase]
        out: Dict[str, Any] = {}
    elif vague and phase == "primary" and not is_phase_entry:
        question = _PUSHBACK_VAGUE
        out = {}
    elif is_phase_entry and phase == "complication":
        question = _pick_probe("complication", plan, probe_slot)
        out = {}
    elif is_phase_entry and phase == "standards":
        question = _pick_probe("standards", plan, probe_slot)
        out = {}
    elif is_phase_entry and phase == "close":
        question = _pick_probe("close", plan, 0)
        out = {}
    else:
        plan_json = json.dumps(plan, ensure_ascii=False)[:4000]
        phase_brief = _scenario_brief_for(phase, plan) if is_phase_entry else ""
        server_probe = _pick_probe(phase, plan, probe_slot) if phase != "anchor" else ""
        prompt = f"""You are the AiQ interview **planner**. Write the next single question for the participant.

**Participant profile:** {ass.get("level_label") or ass.get("level")} in {ass.get("job_family_label") or "their role"}.
{plan.get("level_note") or ""}

**Scenario plan (canonical; stay in their role):**
{plan_json}

**Current phase:** {phase}
**Is this a phase entry turn (server-decided):** {is_phase_entry}
**Phase brief the server WILL prepend (do not repeat verbatim):** {phase_brief or "(none)"}
**If you need a concrete angle, adapt this probe (do not copy "In the scenario where"):** {server_probe}

**Recent transcript (last turns):**
{_transcript_excerpt(history + [{"role": "user", "content": user_message}])}

**Last user message:** {user_message[:3500]}
**Thin / low-signal reply:** {thin}
**Vague hype without checks:** {vague}

**Hard rules (must follow exactly):**
- Output JSON only: `question`, `session_complete`, `internal_tags`, `missing_facets`.
- `question`: ONE short question ending with `?`. Max 45 words. No bullet lists.
- **FORBIDDEN openers:** That's, It sounds like, Understood, Great, Nice, In the scenario where, In the context of the scenario, In light of the vendor.
- **FORBIDDEN:** repeating automation-vs-forecasting framing if already asked. Ask a NEW concrete angle (prompt text, check, owner, escalation).
- Phase rules:
  - `anchor`: role + tools they actually use. No scenario body.
  - `primary` (entry): how they handle the scenario — first prompt, inputs, forbidden inventions.
  - `primary` (follow-up): ONE different angle — verification step OR who signs off OR what they refuse to paste.
  - `complication`: next-hour actions only (who, stop, never-in-tool).
  - `standards`: bar for others — owners, minimum check.
  - `close`: one reflection; session_complete true.
- If thin reply: ask for three bullets (input / forbid / who reads), do not ask another trade-off question.
- Never mention dimensions or [Dim: Dx].
"""
        try:
            out = llm_json(prompt, temperature=0.25, max_tokens=500)
        except Exception:
            out = {}
        question = (out.get("question") or "").strip()

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


def _fallback_question(phase: str, plan: dict, user_message: str) -> str:
    if phase == "anchor":
        return "Which AI tools do you actually open in a normal week, and for what kind of work?"
    if phase == "primary":
        return "In this scenario, what is the very first prompt you would give a model — role, inputs, and what would you forbid it to invent?"
    if phase == "complication":
        return "What do you do in the next hour, in order: first call, what you stop, and what never goes into the tool again?"
    if phase == "standards":
        return "Who else must follow this bar on your team, and what is the minimum check before AI-assisted work goes out?"
    return "What is one thing you would do differently next week in how you work with AI on this kind of task?"


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
        return llm_json(prompt, temperature=0.25, max_tokens=4000)
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
    plan = variation.get("scenario_plan") or {}
    ass = variation.get("assessment") or {}
    fam = ass.get("job_family_label") or "your role"
    primary_title = (plan.get("primary") or {}).get("title", "a real work scenario")
    return (
        "This is a short AiQ conversation — about ten minutes. "
        f"I'll walk you through one scenario tailored to {fam} (\"{primary_title}\") and ask how you'd actually handle it with AI: prompts, checks, who owns what.\n\n"
        "First, so I can pitch the scenario at the right altitude: in one or two lines, what is your role, and which AI or copilot tools do you actually open in a normal week (and roughly for what)?"
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
