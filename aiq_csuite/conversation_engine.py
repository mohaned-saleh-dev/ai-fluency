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

import re
from typing import Any, Dict, List, Optional

from llm_json import llm_json
from scenario_engine import LADDER_BEATS

# Conversations are ~10 minutes; the cap only exists so a session can't run forever.
MAX_USER_TURNS = 12
# Begin steering toward a warm close after this many participant turns.
WRAP_NUDGE_TURNS = 8
# A beat the participant keeps dodging is marked answered after this many asks, so one
# evasive area cannot eat the whole turn budget and starve the twist.
MAX_ASKS_PER_BEAT = 2

_BEAT_BRIEF = {
    "inputs": "what they actually put into the tool, and what they hold back",
    "output": "what they asked it for, and what came back before they edited it",
    "validation": "what they do between the draft and it reaching its audience",
}

CLOSE_TRAILER = (
    "When you are ready, tap **End session & view results** below — that opens your summary from this chat."
)

_DIM_CHECKLIST = """- D1 Awareness & opportunity: do they know where AI is actually worth using in their work — tools, use cases, and where they'd deliberately NOT use it?
- D2 Prompts & communication: how do they actually brief a model — context, constraints, examples, iteration — versus one-shot vague asks?
- D3 Critical judgment: do they verify AI output before relying on it — a real example of catching something wrong, a habit of checking against source data?
- D4 Workflows & ownership: is AI woven into a real workflow with clear ownership and handoffs, or ad hoc? Who owns the output once it moves on?
- D5 Output quality bar: do they edit and hold a standard for AI-assisted work others will see — tone, accuracy, fit for the audience?
- D6 Responsible use: sensitive data awareness (what never goes into the tool), escalation instincts, knowing their no-go zones."""


# Openers that are unambiguously a verdict on the participant's answer, whatever follows
# them. Stripped regardless of sentence length.
_PRAISE_STEM = re.compile(
    r"^(?:"
    r"(?:oh|ah|wow|ok(?:ay)?|right|yeah)[,!.\s]+)?"
    r"(?:"
    r"(?:that|this|it)(?:'s| is| was| sounds| sounds like| seems| seems like)\s+"
    r"(?:really |very |quite |super |pretty |a |an )*"
    r"(?:great|good|excellent|solid|smart|strong|impressive|insightful|perfect|helpful|"
    r"interesting|useful|fair|sensible|thorough|crucial|key|important)"
    r"|it(?:'s| is) (?:great|good|nice|encouraging|reassuring) to (?:hear|see|know)"
    r"|i (?:love|like|appreciate) (?:that|it|how|the way)"
    r"|(?:great|excellent|perfect|nice|awesome|lovely|brilliant|fantastic)\b"
    r"|(?:good|great|fair|excellent) (?:point|answer|call|question|instinct|shout)"
    r"|makes sense|that makes sense|well said|well put|well done|good job|fair enough"
    r"|having .{0,80}? is (?:a |an )?(?:great|good|smart|solid|sensible|strong)"
    r"|you(?:'re| are) (?:clearly|obviously|evidently) "
    # "It sounds like you have a solid grasp…" — a verdict on *them*, so it needs a
    # praise word nearby; "It sounds like the export goes in whole" has none and stays.
    r"|(?:that|this|it) sounds like you\b.{0,70}?\b"
    r"(?:great|good|solid|strong|thorough|robust|clear|careful|rigorous|disciplined)\b"
    r")",
    re.I,
)

# Softer evaluative openers, stripped only when the sentence carries no substance of its
# own — short, and with no figure or quoted detail to lose.
_PRAISE_SOFT = re.compile(
    r"^(?:that|this|it|sounds)\b.{0,60}?\b(?:great|good|solid|smart|sense|right|clear|fair)\b",
    re.I,
)

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])[\s—-]+")


def strip_evaluative_opener(reply: str, max_strips: int = 2) -> str:
    """Drop leading sentences that grade the participant's answer.

    A backstop, not the primary mechanism — the prompt does the real work. Small models
    reliably ignore "never flatter", and praise is not cosmetic here: telling someone
    their answer was good mid-interview changes what they say next and makes a coaching
    conversation feel like a graded test. Conservative by construction: only *leading*
    sentences go, a sentence carrying a figure or a quote is always kept, and a reply is
    never emptied.
    """
    text = (reply or "").strip()
    for _ in range(max_strips):
        parts = _SENTENCE_SPLIT.split(text, maxsplit=1)
        if len(parts) < 2:
            break
        head, rest = parts[0].strip(), parts[1].strip()
        if not rest:
            break
        hard = bool(_PRAISE_STEM.match(head))
        # Substance guard: digits or quoted material mean the sentence is carrying a real
        # callback, so it stays even if it opens evaluatively.
        thin = len(head.split()) <= 12 and not re.search(r"[\d\"“”']", head)
        soft = thin and bool(_PRAISE_SOFT.match(head))
        if not (hard or soft):
            break
        text = rest
    return text or (reply or "").strip()


def empty_ladder_state() -> Dict[str, Any]:
    return {
        "answered": [],
        "asks": {b: 0 for b in LADDER_BEATS},
        "last_asked": None,
        "twist_delivered": False,
        "standards_asked": False,
    }


_NON_ANSWER = re.compile(
    r"^\s*(idk|dunno|no idea|not sure|nothing|none|n/?a|nope|yes|no|ok(ay)?|sure|maybe|"
    r"i guess|whatever|it depends|same|as above)\b[\s.!?]*$",
    re.I,
)


def is_substantive_answer(text: str) -> bool:
    """Did the participant actually engage with the question they were just asked?

    Used to advance the ladder server-side. The alternative — trusting the model's own
    "they answered it" flag — makes progression a property of the model: a cautious one
    re-asks and burns the turn budget, a lax one skips ahead. Neither is acceptable when
    the turn budget is what decides whether the twist gets asked at all.
    """
    t = (text or "").strip()
    if len(t.split()) < 4:
        return False
    if _NON_ANSWER.match(t):
        return False
    from scenario_engine import _is_clarification_request

    return not _is_clarification_request(t)


def _coerce_ladder_state(raw: Optional[dict]) -> Dict[str, Any]:
    st = empty_ladder_state()
    if not isinstance(raw, dict):
        return st
    answered = raw.get("answered")
    if isinstance(answered, list):
        st["answered"] = [b for b in LADDER_BEATS if b in answered]
    asks = raw.get("asks")
    if isinstance(asks, dict):
        for b in LADDER_BEATS:
            try:
                st["asks"][b] = max(0, int(asks.get(b) or 0))
            except (TypeError, ValueError):
                st["asks"][b] = 0
    la = raw.get("last_asked")
    st["last_asked"] = la if la in LADDER_BEATS else None
    st["twist_delivered"] = bool(raw.get("twist_delivered"))
    st["standards_asked"] = bool(raw.get("standards_asked"))
    return st


def _pending_beat(state: Dict[str, Any]) -> Optional[str]:
    """First beat not yet answered — or force-advanced past if the participant has been
    asked about it twice and still hasn't engaged with it."""
    for b in LADDER_BEATS:
        if b in state["answered"]:
            continue
        if state["asks"].get(b, 0) >= MAX_ASKS_PER_BEAT:
            continue
        return b
    return None


def _credit_prior_beat(prior: Dict[str, Any], user_text: str) -> Dict[str, Any]:
    """Credit the beat put to them last turn when this reply engages with it.

    Runs **before** the directive for this turn is chosen — otherwise the interviewer
    computes what to ask from a state that has not yet seen the answer sitting in front
    of it, and asks every beat twice.

    Progression is decided here, by the server, and not by the model's own "they answered
    it" flag: self-reports differ sharply between model families (a cautious one re-asks
    and burns the turns the twist needs), and the interview shape must not change when
    the model does.
    """
    st = {
        "answered": list(prior["answered"]),
        "asks": dict(prior["asks"]),
        "last_asked": prior.get("last_asked"),
        "twist_delivered": bool(prior["twist_delivered"]),
        "standards_asked": bool(prior["standards_asked"]),
    }
    pending = prior.get("last_asked")
    if (
        pending in LADDER_BEATS
        and pending not in st["answered"]
        and is_substantive_answer(user_text)
    ):
        st["answered"] = [b for b in LADDER_BEATS if b in st["answered"] + [pending]]
    return st


def _merge_ladder_state(
    prior: Dict[str, Any],
    model_ladder: Any,
    asked_beat: Optional[str],
) -> Dict[str, Any]:
    """Fold the model's read of the transcript in, then record what we just asked.

    The model's ``answered`` claim can only *add* to what the server already credited,
    never hold it back. Monotonic on purpose: a beat that was answered stays answered and
    the twist cannot un-fire, so a model that loses the thread can't send the interview
    back round a loop it already completed.
    """
    st = {
        "answered": list(prior["answered"]),
        "asks": dict(prior["asks"]),
        "last_asked": prior.get("last_asked"),
        "twist_delivered": bool(prior["twist_delivered"]),
        "standards_asked": bool(prior["standards_asked"]),
    }
    if isinstance(model_ladder, dict):
        claimed = model_ladder.get("answered")
        if isinstance(claimed, list):
            for b in LADDER_BEATS:
                if b in claimed and b not in st["answered"] and st["asks"].get(b, 0) > 0:
                    st["answered"].append(b)
        st["twist_delivered"] = st["twist_delivered"] or bool(model_ladder.get("twist_delivered"))
        st["standards_asked"] = st["standards_asked"] or bool(model_ladder.get("standards_asked"))
    # 3. A beat asked to the cap counts as covered — evasion is itself evidence, and the
    #    interview has to keep moving.
    for b in LADDER_BEATS:
        if b not in st["answered"] and st["asks"].get(b, 0) >= MAX_ASKS_PER_BEAT:
            st["answered"].append(b)
    st["answered"] = [b for b in LADDER_BEATS if b in st["answered"]]
    if asked_beat:
        st["asks"][asked_beat] = st["asks"].get(asked_beat, 0) + 1
        st["last_asked"] = asked_beat
    return st


def _ladder_directive(
    ladder: Dict[str, str],
    state: Dict[str, Any],
    twist: str,
    standards_question: str,
) -> tuple:
    """(directive text, beat this turn is asking). Server-computed so the model cannot
    skip a beat, ask two at once, or spring the twist early."""
    pending = _pending_beat(state)
    if pending:
        first = not state["answered"] and state["asks"].get(pending, 0) == 0
        lead = (
            "They have not been given the situation yet. Once you know their role and the "
            "tools they actually use, set the situation up in two or three sentences of your "
            "own and then ask this, as one question:\n"
            if first
            else "Ask this next, as one question, picking up their actual words:\n"
        )
        repeat = (
            "\nThey have already been asked this once and talked around it. Do not repeat the "
            "question — make it concrete and specific, warmly, then move on regardless of what "
            "you get."
            if state["asks"].get(pending, 0) >= 1
            else ""
        )
        return (
            f"{lead}  [{pending.upper()}] {ladder[pending]}\n"
            f"  (What you need from it: {_BEAT_BRIEF[pending]}.){repeat}",
            pending,
        )
    if not state["twist_delivered"] and twist:
        return (
            "All three questions are answered — now spring the twist. Deliver it in your own "
            "words, keeping every specific detail intact, and close with what would have "
            "caught it:\n"
            f"  {twist}\n"
            "Do not soften it and do not answer it for them.",
            None,
        )
    if not state["standards_asked"] and standards_question:
        return (
            "The twist has landed. Ask them the team-norms question now, in your own words:\n"
            f"  {standards_question}",
            None,
        )
    return (
        "The scenario has run its course. Wrap up warmly in 1-2 sentences (thank them, no new "
        'question) and set "wrap": true.',
        None,
    )


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
    ladder_state: Optional[dict] = None,
) -> Dict[str, Any]:
    """One conversational turn.

    Returns {reply, session_suggests_complete, coverage, ladder}. ``ladder`` is the
    updated ladder state and must be handed back on the next turn — it is what keeps the
    three questions in order and the twist held until they are all answered.
    """
    var = variation or {}
    ass = var.get("assessment") or {}
    plan = var.get("scenario_plan") or {}
    primary = plan.get("primary") or {}
    complication = (plan.get("complication") or {}).get("inject") or ""
    standards = (plan.get("standards") or {}).get("focus") or ""
    standards_question = str(plan.get("standards_question") or "").strip()

    ladder_raw = plan.get("question_ladder")
    ladder: Dict[str, str] = (
        {b: str(ladder_raw.get(b) or "").strip() for b in LADDER_BEATS}
        if isinstance(ladder_raw, dict)
        else {}
    )
    has_ladder = bool(ladder) and all(ladder.get(b) for b in LADDER_BEATS)
    state = _coerce_ladder_state(ladder_state)
    if has_ladder:
        # Take their answer into account before deciding what to ask next.
        state = _credit_prior_beat(state, user_text)
    asked_beat: Optional[str] = None

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

    ladder_block = ""
    ladder_now = ""
    ladder_rules = ""
    ladder_json_field = ""
    ladder_json_note = ""
    if has_ladder and not force_close:
        directive, asked_beat = _ladder_directive(ladder, state, complication, standards_question)
        beats = "\n".join(
            f"  {i}. [{b.upper()}] {ladder[b]}" for i, b in enumerate(LADDER_BEATS, start=1)
        )
        ladder_block = f"""
SCENARIO SPINE — this interview has a fixed shape. These three questions get asked in this order, one per turn:
{beats}
Then, and only then, the twist. Then the team-norms question. Then the wrap.
The wording above is the substance to get at, not a script to read out: put each one in your own words, anchored to what they just told you. Never show them as a list, never ask two at once, and never let the twist out early — it only works if they have already committed to how they'd work.
"""
        # Kept at the very end of the prompt, immediately before the output spec: the
        # step the model must actually perform is the last thing it reads.
        ladder_now = f"""
RIGHT NOW:
{directive}
"""
        ladder_rules = (
            "\n- The spine outranks your own sense of where to go next. This reply MUST carry out "
            "the RIGHT NOW step — a related-but-different question does not count and wastes the "
            "turn. Reacting to what they said is how you open it, not a substitute for it.\n"
            "- If they ask you something, answer it briefly first, then still do the RIGHT NOW step."
        )
        ladder_json_field = (
            ', "ladder": {"answered": [], "twist_delivered": false, "standards_asked": false}'
        )
        ladder_json_note = (
            '\n"ladder.answered" lists which of "inputs", "output", "validation" the participant '
            "has now given a real answer to anywhere in the transcript — judge from their words, "
            "not from whether you asked. A dodge or a non-answer does not count. "
            '"twist_delivered" is true once you have put the twist to them; "standards_asked" is '
            "true once you have asked the team-norms question."
        )

    prompt = f"""You are the interviewer in "AiQ" — a warm, sharp, genuinely curious conversation partner having a ~10-minute chat with a {level_label or "professional"} working in {role_label} about how they actually use AI in their work. This is a natural conversation between two people, not a survey and not a script.

{scenario_material}
{ladder_block}
INTERNAL CHECKLIST — you are quietly listening for concrete evidence in six areas. Never name or number these to the participant:
{_DIM_CHECKLIST}

HOW TO OPEN EVERY REPLY (this is the rule people notice most — get it right):
Start your reply with ONE of exactly two moves:
  (a) the question itself, or
  (b) a flat, neutral restatement of a *specific* thing they said — a detail, number, or name they used — with no adjective judging it.
Then continue. An interviewer who praises answers tells the person they are doing well, which changes what they say next and makes this feel like a test being graded. Stay neutral and curious the whole way through.

  THEM: "I strip the customer names out before I paste anything in."
  BAD:  "That's great — really good instinct." → grades them.
  BAD:  "It's great to hear you strip the names out." → praise dressed as a restatement.
  GOOD: "So the names come out first. What about the rest of the columns — what stays in?"

  THEM: "I ask it for three bullets with the driver called out."
  BAD:  "That sounds like a solid approach."
  GOOD: "Three bullets with the driver named. What came back the first time you asked for that?"

Words that must never appear about their answer: great, good, excellent, solid, smart, impressive, insightful, perfect, love, well done, makes sense. Never open with "That's...", "It's great...", "It sounds like you...", or "Having ... is a ...".

HOW TO BEHAVE:
- React to what they just said, specifically — pick up their words and build on them. Never ignore a question they asked you.
- One question per turn, at most. Keep your turns short: 1-4 sentences.
- Do not lecture or give advice mid-interview. You are collecting how they work, not improving it.
- If they ask what this chat is, why you're asking, or whether it's a test: answer honestly and briefly (a short, relaxed assessment of how they work with AI; about ten minutes; no trick questions; they get a personal report at the end), then pick the conversation back up naturally.
- Early on, learn their actual role and which AI tools they really use, conversationally — you need that to make the scenario land.
- If an answer is vague or thin, don't repeat the question — make it concrete and specific, warmly.
- If they say something surprising, risky, or interesting, follow it. The scenario is material, not a rail.
- Silently compare the transcript against your checklist and steer toward the thinnest areas.
- When most areas have real evidence and the scenario has run its course — or the chat is getting long — wrap up warmly in 1-2 sentences (thank them, no new question) and set "wrap": true.{ladder_rules}

TRANSCRIPT SO FAR:
{_transcript_block(history)}

THEIR LAST MESSAGE:
{user_text.strip()[:2000]}

{server_note}
{ladder_now}
Return JSON only, exactly this shape:
{{"reply": "your next conversational turn", "coverage": {{"D1": false, "D2": false, "D3": false, "D4": false, "D5": false, "D6": false}}, "wrap": false{ladder_json_field}}}
"coverage" marks true for each checklist area that now has CONCRETE evidence anywhere in the transcript (their words, not your questions). "wrap" is true only when your reply is closing the conversation.{ladder_json_note}"""

    out: Dict[str, Any] = {}
    try:
        out = llm_json(prompt, temperature=0.6, max_tokens=600) or {}
    except Exception:
        out = {}

    reply = str(out.get("reply") or "").strip()
    if not reply:
        # Minimal, honest fallback — keeps the conversation alive without pretending.
        reply = "Sorry, I lost my train of thought for a second — could you say that again, or add a bit more detail?"
    else:
        reply = strip_evaluative_opener(reply)
    coverage_raw = out.get("coverage") or {}
    coverage = {k: bool(coverage_raw.get(k)) for k in ("D1", "D2", "D3", "D4", "D5", "D6")}
    wrap = bool(out.get("wrap")) or force_close

    if has_ladder:
        twist_was_delivered = state["twist_delivered"]
        state = _merge_ladder_state(state, out.get("ladder"), asked_beat)
        # Hold the close until the arc has actually finished: the twist has to be put to
        # them, they have to get a turn to answer it, and the team-norms question has to
        # land. A model that wraps early would drop the highest-signal moment in the
        # interview. force_close (turn cap) always wins — the session still can't run on.
        if wrap and not force_close:
            twist_pending = not state["twist_delivered"] or not twist_was_delivered
            standards_pending = bool(standards_question) and not state["standards_asked"]
            if twist_pending or standards_pending:
                wrap = False

    if wrap and "End session & view results" not in reply:
        reply = reply.rstrip() + "\n\n" + CLOSE_TRAILER

    return {
        "reply": reply,
        "session_suggests_complete": wrap,
        "coverage": coverage,
        "ladder": state if has_ladder else None,
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
