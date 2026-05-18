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

PHASE_MAX_TURNS: Dict[str, int] = {
    "anchor": 1,
    "primary": 4,
    "complication": 2,
    "standards": 2,
    "close": 1,
}

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


def build_scenario_plan(assessment: dict, client_seed: str) -> dict:
    """Role-specific scenario brief stored in variation_json."""
    ass = assessment or {}
    fam = str(ass.get("job_family") or "other")
    cluster = fam_cluster(fam)
    lib = _load_library()
    base = dict(lib.get(cluster) or lib.get("gm") or {})
    rng = random.Random(client_seed)
    level = str(ass.get("level") or "head_of")
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


def compute_flow_state(
    messages: List[dict],
    phase_history: List[str],
) -> dict:
    """Derive current phase and turn budget from messages + phase_shift history."""
    current = phase_history[-1] if phase_history else "anchor"
    idx = next((i for i, (c, _) in enumerate(PHASES) if c == current), 0)
    last_shift_at = 0.0
    # Count model turns since current phase started (approximate via streak in phase)
    model_turns_in_phase = 0
    if phase_history:
        # Count model messages after we entered current phase
        phase_start_idx = len(phase_history) - 1
        model_count = sum(1 for m in messages if (m.get("role") or "") == "model")
        # Rough: subtract model turns from prior phases using max turns
        prior_budget = sum(
            PHASE_MAX_TURNS.get(PHASES[i][0], 2) for i in range(idx)
        )
        model_turns_in_phase = max(0, model_count - prior_budget)
    else:
        model_turns_in_phase = sum(1 for m in messages if (m.get("role") or "") == "model")

    max_turns = PHASE_MAX_TURNS.get(current, 3)
    user_turns = sum(1 for m in messages if (m.get("role") or "") == "user")
    must_advance = model_turns_in_phase >= max_turns
    pending = [c for c, _ in PHASES[idx + 1 :]]
    next_phase = pending[0] if pending else None
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

    if must_adv and next_phase:
        phase = next_phase
        is_phase_entry = True
    else:
        phase = current_phase
        is_phase_entry = False

    plan_json = json.dumps(plan, ensure_ascii=False)[:4000]
    phase_brief = _scenario_brief_for(phase, plan) if is_phase_entry else ""
    primary_brief_for_context = _scenario_brief_for("primary", plan)
    prompt = f"""You are the AiQ interview **planner**. Write the next single question for the participant.

**Participant profile:** {ass.get("level_label") or ass.get("level")} in {ass.get("job_family_label") or "their role"}.
{plan.get("level_note") or ""}

**Scenario plan (canonical; stay in their role):**
{plan_json}

**Current phase:** {phase}
**Is this a phase entry turn (server-decided):** {is_phase_entry}
**Phase brief the server WILL prepend (do not repeat it verbatim):** {phase_brief or "(none)"}

**Recent transcript (last turns):**
{_transcript_excerpt(history + [{"role": "user", "content": user_message}])}

**Last user message:** {user_message[:3500]}

**Hard rules (must follow exactly):**
- Output JSON only with keys: `question` (string), `session_complete` (bool), `internal_tags` (array of D1..D6), `missing_facets` (array).
- `question` is ONE sentence (or two short) ending with `?`. Under 60 words. No bullet lists.
- **NEVER** start with: "That's", "It sounds like", "Understood", "Great", "Nice", "Wow", "I appreciate", "Thanks for sharing", "That sounds", "Makes sense". No praise of their last answer. No "I" assistant voice.
- Phase rules:
  - `anchor`: a quick warm question about their role and the AI tools they actually use this week. No scenario yet.
  - `primary`: ask how **they** would handle the scenario the server prepended — concrete first move, prompt, inputs, what they would refuse to let the model do. Reference the scenario explicitly (their action in *that* situation).
  - `complication`: ask what they do **right now** about the twist (first action, who, what they stop). Concrete next steps, not reflection.
  - `standards`: ask how they set the bar for others on this kind of work — owners, review, what gets escalated.
  - `close`: one short reflection question. If you have decent signal, set `session_complete: true`.
- Do NOT use `[Dim: Dx]` banners. Do NOT mention "dimensions" or six areas.
- Do NOT keep drilling the same micro-point if the user just said "nothing specific" or gave a thin answer — move forward into the next concrete action in the scenario.
- Never ask about QA of human agents, support chats, or AI chatbot training unless they raised it.
"""
    try:
        out = llm_json(prompt, temperature=0.3, max_tokens=600)
    except Exception:
        out = {}

    question = _strip_soft_opener((out.get("question") or "").strip())
    if not question or "?" not in question:
        question = _fallback_question(phase, plan, user_message)

    session_complete = bool(out.get("session_complete"))
    if phase == "close":
        session_complete = True

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
            "internal_tags": out.get("internal_tags") or [],
            "missing_facets": out.get("missing_facets") or [],
            "phase": phase,
            "is_phase_entry": is_phase_entry,
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
