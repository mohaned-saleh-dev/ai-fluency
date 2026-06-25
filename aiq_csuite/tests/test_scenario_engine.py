"""Unit tests for scenario-stack guards (no LLM)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scenario_engine as se  # noqa: E402


def test_thin_answer_detection():
    assert se._is_thin_answer("Nothing specific.")
    assert se._is_thin_answer("Tell the team to be careful.")
    assert not se._is_thin_answer(
        "I paste anonymized requirements, forbid invented policy, second human reviews."
    )


def test_complication_signal_skips_portfolio_loop():
    assert se._user_signals_complication("Kill the thread, ping security, check retention.")


def test_banned_stem_detected():
    q = "In the scenario where you must choose between automation and forecasting, what criteria?"
    assert se._question_is_repetitive(q, [])


def test_coo_cluster_for_gm_exec():
    assert se._scenario_cluster("general_management", "head_of") == "coo_office"
    assert se._scenario_cluster("product_engineering", "head_of") == "product"


def test_finalize_uses_thin_probe():
    q = se._finalize_question(
        "In the scenario where you choose automation, what trade-offs?",
        "primary",
        {"probe_bank": ["probe a", "probe b", "probe c"]},
        [],
        thin=True,
        vague=False,
        probe_slot=1,
    )
    assert "concrete" in q.lower() or "first" in q.lower()


def test_clarification_you_mean_published():
    assert se._is_clarification_request(
        "you mean it rewrote it and it was published already?"
    )


def test_ta_anchor_swaps_people_scenario():
    plan = se.build_scenario_plan(
        {"job_family": "hr_people", "level": "head_of", "job_family_label": "HR"},
        "seed",
    )
    messages = [
        {"role": "model", "content": "What is your role?"},
        {
            "role": "user",
            "content": "Head of Talent Acquisition. ChatGPT for job descriptions and outreach.",
        },
    ]
    out = se._apply_anchor_context(plan, messages)
    assert out.get("cluster") == "people_ta"
    assert "recruiter" in (out.get("primary") or {}).get("setup", "").lower()


if __name__ == "__main__":
    test_thin_answer_detection()
    test_complication_signal_skips_portfolio_loop()
    test_banned_stem_detected()
    test_coo_cluster_for_gm_exec()
    test_finalize_uses_thin_probe()
    test_clarification_you_mean_published()
    test_ta_anchor_swaps_people_scenario()
    print("ok")
