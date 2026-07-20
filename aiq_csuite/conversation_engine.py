"""
LLM-driven conversational interview engine (v3).

The model owns the conversation: it reacts to what the participant actually said,
introduces the scenario material in its own words when the moment is right, answers
meta questions honestly, and steers toward whichever evidence areas are still thin.
The server's only jobs are the turn cap, the end-of-session trailer, and a compact
progress payload for the UI. No phase state machine, no canned probes, no regex gates.

Scoring is unchanged: it reads the finished transcript (scenario_engine.extract_
session_evidence → score_session_evidence), so the interview style is independent
of how evidence is graded.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from llm_json import llm_json

# Conversations are ~10 minutes; the cap only exists so a session can't run forever.
MAX_USER_TURNS = 12
# Begin steering toward a warm close after this many participant turns.
WRAP_NUDGE_TURNS = 8

CLOSE_TRAILER = (
    "When you are ready, tap **End session & view results** below — that opens your summary from this chat."
)

_DIM_CHECKLIST = """- D1 Awareness & opportunity: do they know where AI is actually worth using in their work — tools, use cases, and where they'd deliberately NOT use it?
- D2 Prompts & communication: how do they actually brief a model — context, constraints, examples, iteration — versus one-shot vague asks?
- D3 Critical judgment: do they verify AI output before relying on it — a real example of catching something wrong, a habit of checking against source data?
- D4 Workflows & ownership: is AI woven into a real workflow with clear ownership and handoffs, or ad hoc? Who owns the output once it moves on?
- D5 Output quality bar: do they edit and hold a standard for AI-assisted work others will see — tone, accuracy, fit for the audience?
- D6 Responsible use: sensitive data awareness (what never goes into the tool), escalation instincts, knowing their no-go zones."""


def _transcript_block(history: List[dict], cap_chars: int = 9000) -> str:
    lines = []
    for m in history:
        role = "THEM" if (m.get("role") or "") == "user" else "YOU"
        lines.append(f"{role}: {(m.get('content') or '').strip()}")
    return "\n\n".join(lines)[-cap_chars:]


def run_turn(
    variation: dict,
    history: List[dict],
    user_text: str,
    *,
    force_close: bool = False,
    context_note: str = "",
) -> Dict[str, Any]:
    """One conversational turn. Returns {reply, session_suggests_complete, coverage}."""
    var = variation or {}
    ass = var.get("assessment") or {}
    plan = var.get("scenario_plan") or {}
    primary = plan.get("primary") or {}
    complication = (plan.get("complication") or {}).get("inject") or ""
    standards = (plan.get("standards") or {}).get("focus") or ""

    role_label = ass.get("job_function_label") or ass.get("job_family_label") or "their role"
    level_label = ass.get("level_label") or ""
    user_turns = sum(1 for m in history if (m.get("role") or "") == "user") + 1

    if force_close:
        server_note = (
            "SERVER NOTE: the turn limit is reached. Close the conversation warmly NOW in 1-2 "
            'sentences (no new question) and set "wrap": true.'
        )
    elif user_turns >= WRAP_NUDGE_TURNS:
        server_note = (
            "SERVER NOTE: the conversation is getting long. Start steering toward a warm wrap-up "
            "within the next turn or two."
        )
    else:
        server_note = ""
    if context_note and "No special flag" not in context_note:
        server_note = (server_note + "\n" if server_note else "") + f"SERVER NOTE: {context_note}"

    scenario_material = f"""SCENARIO MATERIAL — background for YOU. Never paste it verbatim; introduce it naturally, in your own words, woven into the conversation once you understand their role and tools:
- The situation: {primary.get("setup", "")}
- Why it matters: {primary.get("stakes", "")}
- A twist to introduce mid-conversation, once they've engaged with the situation: {complication}
- Toward the end, get their take on team norms: {standards}"""

    prompt = f"""You are the interviewer in "AiQ" — a warm, sharp, genuinely curious conversation partner having a ~10-minute chat with a {level_label or "professional"} working in {role_label} about how they actually use AI in their work. This is a natural conversation between two people, not a survey and not a script.

{scenario_material}

INTERNAL CHECKLIST — you are quietly listening for concrete evidence in six areas. Never name or number these to the participant:
{_DIM_CHECKLIST}

HOW TO BEHAVE:
- React to what they just said, specifically — pick up their words and build on them. Never ignore a question they asked you.
- One question per turn, at most. Keep your turns short: 1-4 sentences.
- Never grade or flatter ("great answer", "smart approach"), and never open a reply with praise or a compliment ("It's great to hear...", "That sounds impressive") — react to the substance instead. Never lecture or give advice mid-interview.
- If they ask what this chat is, why you're asking, or whether it's a test: answer honestly and briefly (a short, relaxed assessment of how they work with AI; about ten minutes; no trick questions; they get a personal report at the end), then pick the conversation back up naturally.
- Early on, learn their actual role and which AI tools they really use, conversationally — you need that to make the scenario land.
- If an answer is vague or thin, don't repeat the question — make it concrete and specific, warmly.
- If they say something surprising, risky, or interesting, follow it. The scenario is material, not a rail.
- Silently compare the transcript against your checklist and steer toward the thinnest areas.
- When most areas have real evidence and the scenario has run its course — or the chat is getting long — wrap up warmly in 1-2 sentences (thank them, no new question) and set "wrap": true.

TRANSCRIPT SO FAR:
{_transcript_block(history)}

THEIR LAST MESSAGE:
{user_text.strip()[:2000]}

{server_note}

Return JSON only, exactly this shape:
{{"reply": "your next conversational turn", "coverage": {{"D1": false, "D2": false, "D3": false, "D4": false, "D5": false, "D6": false}}, "wrap": false}}
"coverage" marks true for each checklist area that now has CONCRETE evidence anywhere in the transcript (their words, not your questions). "wrap" is true only when your reply is closing the conversation."""

    out: Dict[str, Any] = {}
    try:
        out = llm_json(prompt, temperature=0.6, max_tokens=600) or {}
    except Exception:
        out = {}

    reply = str(out.get("reply") or "").strip()
    if not reply:
        # Minimal, honest fallback — keeps the conversation alive without pretending.
        reply = "Sorry, I lost my train of thought for a second — could you say that again, or add a bit more detail?"
    coverage_raw = out.get("coverage") or {}
    coverage = {k: bool(coverage_raw.get(k)) for k in ("D1", "D2", "D3", "D4", "D5", "D6")}
    wrap = bool(out.get("wrap")) or force_close

    if wrap and "End session & view results" not in reply:
        reply = reply.rstrip() + "\n\n" + CLOSE_TRAILER

    return {
        "reply": reply,
        "session_suggests_complete": wrap,
        "coverage": coverage,
    }


_PARTS = [
    ("intro", "Getting started"),
    ("conversation", "The conversation"),
    ("wrap", "Wrap-up"),
]


def progress_payload(messages: List[dict], target_sec: int) -> Dict[str, Any]:
    """Soft 3-part progress for the header bar — no scripted phases to report anymore."""
    user_turns = sum(1 for m in messages if (m.get("role") or "") == "user")
    last_model = next(
        ((m.get("content") or "") for m in reversed(messages) if (m.get("role") or "") == "model"),
        "",
    )
    if "End session & view results" in last_model:
        current = "wrap"
    elif user_turns <= 1:
        current = "intro"
    else:
        current = "conversation"
    idx = next(i for i, (c, _) in enumerate(_PARTS) if c == current)
    return {
        "mode": "scenario",
        "phases": [{"code": c, "label": lbl} for c, lbl in _PARTS],
        "touched": [c for c, _ in _PARTS[: idx + 1]],
        "current": current,
        "current_label": dict(_PARTS)[current],
        "phase_index": idx,
        "total_phases": len(_PARTS),
        "target_sec": target_sec,
        "labels": {c: lbl for c, lbl in _PARTS},
        "user_turns": user_turns,
    }
