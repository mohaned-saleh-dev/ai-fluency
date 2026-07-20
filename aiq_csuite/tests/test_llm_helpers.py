"""Unit tests for llm_service pure helpers (no LLM calls)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import llm_service as llm  # noqa: E402
import scenario_engine as se  # noqa: E402


def test_ground_evidence_quotes_drops_invented():
    msgs = [
        {"role": "model", "content": "q?"},
        {"role": "user", "content": "I use Copilot daily and check every number against the source."},
    ]
    out = {
        "D1": {
            "score": 5,
            "rationale_1line": "x",
            "evidence_quotes": [
                "I use Copilot daily",  # verbatim -> keep
                "I built an enterprise governance council last year",  # invented -> drop
            ],
        }
    }
    grounded = llm._ground_evidence_quotes(out, msgs)
    q = grounded["D1"]["evidence_quotes"]
    assert q == ["I use Copilot daily"]


def test_ground_evidence_quotes_tolerates_minor_requoting():
    msgs = [
        {"role": "model", "content": "q?"},
        {"role": "user", "content": "We never put customer card numbers into a public model, full stop."},
    ]
    out = {"D6": {"score": 8, "rationale_1line": "x", "evidence_quotes": [
        "never put customer card numbers into a public model"
    ]}}
    grounded = llm._ground_evidence_quotes(out, msgs)
    assert len(grounded["D6"]["evidence_quotes"]) == 1


def test_strip_session_complete_flag():
    body, done = llm.strip_session_complete_flag("Thanks!\n[SESSION_COMPLETE]")
    assert done is True and body == "Thanks!"
    body2, done2 = llm.strip_session_complete_flag("No flag here.")
    assert done2 is False and body2 == "No flag here."


def test_parse_scoring_json_recovers_fenced():
    raw = "```json\n{\"D1\": {\"score\": 5}}\n```"
    out = llm.parse_scoring_json_object(raw)
    assert out["D1"]["score"] == 5


def test_band_for_composite_boundaries():
    assert llm._band_for_composite(0) == "AiQ1"
    assert llm._band_for_composite(25) == "AiQ1"
    assert llm._band_for_composite(26) == "AiQ2"
    assert llm._band_for_composite(55) == "AiQ2"
    assert llm._band_for_composite(56) == "AiQ3"
    assert llm._band_for_composite(80) == "AiQ3"
    assert llm._band_for_composite(81) == "AiQ4"
    assert llm._band_for_composite(100) == "AiQ4"


def test_ground_facet_quotes_drops_invented():
    msgs = [
        {"role": "model", "content": "q?"},
        {"role": "user", "content": "I run triage with an AI assist tool across three queues."},
    ]
    evidence = {
        "facets": {
            "tools_in_use": {
                "observed": "uses AI assist",
                "confidence": "medium",
                "quotes": [
                    "I run triage with an AI assist tool",  # verbatim -> keep
                    "we deployed a fine-tuned model in production",  # invented -> drop
                ],
            }
        }
    }
    out = se._ground_facet_quotes(evidence, msgs)
    assert out["facets"]["tools_in_use"]["quotes"] == ["I run triage with an AI assist tool"]


def test_sanitize_scrubs_assessor_voice_aliases():
    """Report rationales must never reach the participant in third-person assessor voice —
    including 'the candidate' / 'the respondent' / 'the subject' (regression: only
    user/participant/interviewee were caught)."""
    out = {
        "D1": {"score": 5, "rationale_1line": "The candidate shows risky data habits."},
        "D2": {"score": 5, "rationale_1line": "The respondent gave vague answers."},
        "D3": {"score": 5, "rationale_1line": "The subject did not verify outputs."},
        "D4": {"score": 5, "rationale_1line": "You verify outputs against the source."},
        "strength_1line": "The participant iterates well.",
        "risk_1line": "You paste sensitive data into public tools.",
    }
    s = llm.sanitize_scoring_for_participant_view(out)
    for dim in ("D1", "D2", "D3"):
        low = s[dim]["rationale_1line"].lower()
        assert "candidate" not in low and "respondent" not in low and "subject" not in low
    # second-person lines pass through untouched
    assert s["D4"]["rationale_1line"] == "You verify outputs against the source."
    assert "participant" not in s["strength_1line"].lower()
    assert s["risk_1line"] == "You paste sensitive data into public tools."


def test_backfill_quotes_from_evidence_rescues_evidenced_dim():
    """If the scorer paraphrased (grounding emptied its quotes) but the evidence facet holds
    grounded verbatim quotes, the dimension keeps its score instead of being capped
    (regression: strong transcripts lost D4 to the cap when the scorer failed to copy
    a quote verbatim, despite the workflow_ownership facet holding one)."""
    msgs = [
        {"role": "model", "content": "q?"},
        {"role": "user", "content": "Every readout has a named owner who re-runs the source query before it goes up."},
    ]
    out = {"D4": {"score": 7.5, "evidence_quotes": []}}
    evidence = {
        "facets": {
            "workflow_ownership": {
                "observed": "clear ownership",
                "quotes": ["a named owner who re-runs the source query"],
            }
        }
    }
    fixed = llm._backfill_quotes_from_evidence(out, evidence, msgs)
    fixed = llm._cap_unevidenced_scores(fixed)
    assert fixed["D4"]["score"] == 7.5
    assert fixed["D4"]["evidence_quotes"] == ["a named owner who re-runs the source query"]
    assert fixed["D4"].get("quotes_backfilled_from_evidence") is True


def test_backfill_ignores_ungrounded_facet_quotes():
    """Facet quotes that are not actually the participant's words must not rescue a score."""
    msgs = [
        {"role": "model", "content": "q?"},
        {"role": "user", "content": "I just send whatever the tool writes."},
    ]
    out = {"D4": {"score": 8.0, "evidence_quotes": []}}
    evidence = {
        "facets": {
            "workflow_ownership": {
                "observed": "x",
                "quotes": ["we operate a rigorous federated governance model"],  # invented
            }
        }
    }
    fixed = llm._backfill_quotes_from_evidence(out, evidence, msgs)
    fixed = llm._cap_unevidenced_scores(fixed)
    assert fixed["D4"]["score"] == 3.0
    assert fixed["D4"]["evidence_quotes"] == []


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-q"]))
