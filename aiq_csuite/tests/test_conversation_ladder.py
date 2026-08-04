"""The interview spine: inputs -> output -> validation, then the twist, then norms.

These exercise the server-side enforcement only — the model is stubbed, because the
point of the ladder is that the sequence holds regardless of what the model returns.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest  # noqa: E402

import conversation_engine as ce  # noqa: E402
import scenario_engine as se  # noqa: E402
from assessment_profiles import build_assessment_block  # noqa: E402


def _variation(func="care_content", fam="care_operations"):
    ass = build_assessment_block("ic", fam, func)
    plan = se.build_scenario_plan(ass, "seed", attempt_no=1, selection_seed="p")
    return {"assessment": ass, "scenario_plan": plan}


def _directive(prompt: str) -> str:
    m = re.search(r"RIGHT NOW:\n(.*?)\n\n", prompt, re.S)
    return m.group(1).strip() if m else ""


def _stub(monkeypatch, *, answers=True, wrap=True):
    """Stand-in model. Reports each beat answered as soon as it is asked (or never, when
    answers=False) and always tries to wrap, so the sequencing we observe is the
    server's, not the model's."""
    seen = []

    def fake(prompt, **kwargs):
        seen.append(prompt)
        d = _directive(prompt)
        return {
            "reply": "ok",
            "coverage": {},
            "wrap": wrap,
            "ladder": {
                "answered": [b for b in ce.LADDER_BEATS if f"[{b.upper()}]" in d] if answers else [],
                "twist_delivered": "spring the twist" in d,
                "standards_asked": "team-norms question now" in d,
            },
        }

    monkeypatch.setattr(ce, "llm_json", fake)
    return seen


# A reply long enough to count as engaging with the question — the server credits a beat
# from the participant's own answer, not from the model's say-so.
REAL_ANSWER = "I would strip the customer identifiers out before anything goes in."
# Too short / evasive to count.
NON_ANSWER = "not sure"


def _run(var, seen, turns=12, ladder_state=None, user_text=REAL_ANSWER):
    """Drive turns until the engine agrees to wrap. Returns the beat order observed."""
    order, hist, state = [], [], ladder_state
    for _ in range(turns):
        r = ce.run_turn(var, hist, user_text, ladder_state=state)
        state = r["ladder"]
        d = _directive(seen[-1])
        for b in ce.LADDER_BEATS:
            if f"[{b.upper()}]" in d:
                order.append(b)
        if "spring the twist" in d:
            order.append("twist")
        if "team-norms question now" in d:
            order.append("standards")
        hist += [{"role": "user", "content": "a"}, {"role": "model", "content": "q"}]
        if r["session_suggests_complete"]:
            order.append("wrap")
            break
    return order, state


def test_beats_are_asked_in_order_then_the_twist_then_norms(monkeypatch):
    seen = _stub(monkeypatch)
    order, state = _run(_variation(), seen)
    assert order == ["inputs", "output", "validation", "twist", "standards", "wrap"]
    assert state["answered"] == list(ce.LADDER_BEATS)


def test_twist_is_never_sprung_before_all_three_are_answered(monkeypatch):
    seen = _stub(monkeypatch)
    order, _ = _run(_variation(), seen)
    assert order.index("twist") > order.index("validation")


def test_model_cannot_wrap_before_the_twist_lands(monkeypatch):
    """The stub asks to wrap on every single turn. The server must refuse until the twist
    has been delivered and answered — it is the highest-signal moment in the interview."""
    seen = _stub(monkeypatch, wrap=True)
    var = _variation()
    hist, state = [], None
    for _ in range(3):
        r = ce.run_turn(var, hist, "a", ladder_state=state)
        state = r["ladder"]
        assert r["session_suggests_complete"] is False
        hist += [{"role": "user", "content": "a"}, {"role": "model", "content": "q"}]


def test_turn_cap_still_closes_the_session(monkeypatch):
    """force_close outranks the ladder — the session can never run past the cap, even
    mid-scenario."""
    _stub(monkeypatch, answers=False, wrap=False)
    r = ce.run_turn(_variation(), [], "a", force_close=True)
    assert r["session_suggests_complete"] is True


def test_evasive_participant_still_reaches_the_twist(monkeypatch):
    """A beat the participant keeps dodging is force-advanced after two asks, so one
    evasive area cannot eat the turn budget and starve the twist."""
    seen = _stub(monkeypatch, answers=False, wrap=False)
    order, state = _run(_variation(), seen, turns=12, user_text=NON_ANSWER)
    assert "twist" in order
    assert state["answered"] == list(ce.LADDER_BEATS)
    assert order.index("twist") <= 2 * len(ce.LADDER_BEATS) + 1


def test_progression_does_not_depend_on_the_model_crediting_it(monkeypatch):
    """A model that never fills in `ladder.answered` — several do — must still see the
    interview advance one beat per substantive reply. Progression is the server's job."""
    monkeypatch.setattr(
        ce,
        "llm_json",
        lambda p, **k: {"reply": "and then?", "coverage": {}, "wrap": False},  # no ladder key
    )
    var, state, hist = _variation(), None, []
    seen_counts = []
    for _ in range(4):
        r = ce.run_turn(var, hist, REAL_ANSWER, ladder_state=state)
        state = r["ladder"]
        seen_counts.append(len(state["answered"]))
        hist += [{"role": "user", "content": REAL_ANSWER}, {"role": "model", "content": r["reply"]}]
    assert seen_counts == [0, 1, 2, 3], f"ladder stalled without model help: {seen_counts}"


def test_a_non_answer_does_not_advance_the_ladder(monkeypatch):
    """Crediting a beat off a shrug would let someone skip the whole interview by typing
    'idk' three times — the force-advance cap is the only way past an unanswered beat."""
    monkeypatch.setattr(
        ce, "llm_json", lambda p, **k: {"reply": "say more?", "coverage": {}, "wrap": False}
    )
    var, state, hist = _variation(), None, []
    r = ce.run_turn(var, hist, "idk", ladder_state=state)
    assert r["ladder"]["answered"] == []


def test_a_beat_is_not_credited_on_the_turn_it_is_asked(monkeypatch):
    """The participant cannot have answered a question that has only just been put to
    them, however eagerly the model reports otherwise."""
    monkeypatch.setattr(
        ce,
        "llm_json",
        lambda p, **k: {
            "reply": "what goes in?",
            "coverage": {},
            "wrap": False,
            "ladder": {"answered": list(ce.LADDER_BEATS)},
        },
    )
    r = ce.run_turn(_variation(), [], REAL_ANSWER)
    assert r["ladder"]["answered"] == []


def test_ladder_state_is_monotonic(monkeypatch):
    """A model that loses the thread cannot send the interview back round a loop it has
    already completed."""
    prior = {
        "answered": list(ce.LADDER_BEATS),
        "asks": {b: 1 for b in ce.LADDER_BEATS},
        "twist_delivered": True,
        "standards_asked": True,
    }
    merged = ce._merge_ladder_state(prior, {"answered": [], "twist_delivered": False}, None)
    assert merged["answered"] == list(ce.LADDER_BEATS)
    assert merged["twist_delivered"] is True


def test_a_beat_is_only_credited_once_it_has_been_asked(monkeypatch):
    """A model claiming the participant answered something we never put to them does not
    get to skip a beat."""
    fresh = ce.empty_ladder_state()
    merged = ce._merge_ladder_state(fresh, {"answered": list(ce.LADDER_BEATS)}, None)
    assert merged["answered"] == []


# --- interviewer tone --------------------------------------------------------------
#
# Every string below is a verbatim reply gpt-4o-mini produced during a live pilot run
# against the earlier prompt, which already said "never open a reply with praise". The
# model ignored it on 6 of 6 turns, so the guard is code, not instructions.

LIVE_PRAISE_OPENERS = [
    "That's interesting! So, as a senior analyst, what would you put in first?",
    "That makes sense — keeping identifiers out is critical. So what do you ask the tool to do?",
    "That sounds like a solid output, especially with a tidy narrative. How do you feel about it?",
    "It's great to hear that you tie every number back to the raw export. Now, fast forward to Sunday night.",
    "It sounds like you have a solid grasp on what the numbers mean. If the tool pinned it on one cause, what next?",
    "Having a second pair of eyes is a smart practice, especially for quality. What else matters?",
]

# Replies that must survive untouched: neutral restatements, callbacks carrying a figure,
# bare questions, and the closing line.
MUST_SURVIVE = [
    "So the names come out first. What about the rest of the columns?",
    "You said the segment was 4% of volume. What made you check that?",
    "That 4% figure is the part I want to dig into. Where did it come from?",
    "What did you ask it for exactly?",
    "Thanks for talking this through with me — that's everything I needed.",
    "It sounds like the export goes in whole. Does anything get held back?",
    "So you'd send it as-is. Who reads it first?",
]


@pytest.mark.parametrize("reply", LIVE_PRAISE_OPENERS)
def test_praise_openers_are_stripped(reply):
    out = ce.strip_evaluative_opener(reply)
    assert out != reply, "praise opener survived"
    assert out.strip(), "reply was emptied"
    lowered = out.lower()
    for word in ("great", "solid", "smart practice", "makes sense", "interesting!"):
        assert not lowered.startswith(word)


@pytest.mark.parametrize("reply", MUST_SURVIVE)
def test_substantive_replies_are_never_touched(reply):
    assert ce.strip_evaluative_opener(reply) == reply


def test_stripper_never_empties_a_reply():
    """A turn that is nothing but praise still has to say something — an empty bubble is
    worse than a warm one."""
    assert ce.strip_evaluative_opener("That's excellent.").strip()
    assert ce.strip_evaluative_opener("Great!").strip()


def test_stripper_runs_on_every_live_turn(monkeypatch):
    """The guard is wired into run_turn, not just available as a helper."""
    monkeypatch.setattr(
        ce,
        "llm_json",
        lambda p, **k: {
            "reply": "That's a great answer. What goes into the tool first?",
            "coverage": {},
            "wrap": False,
            "ladder": {},
        },
    )
    r = ce.run_turn(_variation(), [], "a")
    assert r["reply"].startswith("What goes into the tool first?")


def test_legacy_scenarios_without_a_ladder_stay_free_form(monkeypatch):
    """Scenarios outside the four-role pool have no ladder and must keep the original
    conversational behaviour rather than breaking."""
    seen = _stub(monkeypatch)
    var = _variation(func=None, fam="general_management")
    assert not var["scenario_plan"]["question_ladder"]
    r = ce.run_turn(var, [], "a")
    assert r["ladder"] is None
    assert "SCENARIO SPINE" not in seen[-1]
    assert r["session_suggests_complete"] is True


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
