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


def _anchor_msgs(role_line: str):
    return [
        {"role": "model", "content": "What is your role?"},
        {"role": "user", "content": role_line},
    ]


def test_ta_anchor_swaps_people_scenario():
    plan = se.build_scenario_plan(
        {"job_family": "hr_people", "level": "head_of", "job_family_label": "HR"},
        "seed",
    )
    out = se._apply_anchor_context(plan, _anchor_msgs(
        "Head of Talent Acquisition. ChatGPT for job descriptions and outreach."
    ))
    assert out.get("cluster") == "people_ta"
    assert "recruiter" in (out.get("primary") or {}).get("setup", "").lower()


def test_hrbp_anchor_swaps_people_scenario():
    plan = se.build_scenario_plan(
        {"job_family": "hr_people", "level": "head_of", "job_family_label": "HR"},
        "seed",
    )
    out = se._apply_anchor_context(plan, _anchor_msgs(
        "HR Business Partner supporting sales leaders. Copilot for manager coaching notes."
    ))
    assert out.get("cluster") == "people_hrbp"
    assert "performance" in (out.get("primary") or {}).get("setup", "").lower()


def test_er_anchor_swaps_people_scenario():
    plan = se.build_scenario_plan(
        {"job_family": "hr_people", "level": "head_of", "job_family_label": "HR"},
        "seed",
    )
    out = se._apply_anchor_context(plan, _anchor_msgs(
        "Employee relations lead. ChatGPT to summarize investigation notes."
    ))
    assert out.get("cluster") == "people_er"


def test_gtm_sales_anchor_swaps_scenario():
    plan = se.build_scenario_plan(
        {"job_family": "go_to_market", "level": "head_of", "job_family_label": "GTM"},
        "seed",
    )
    out = se._apply_anchor_context(plan, _anchor_msgs(
        "Head of enterprise sales. ChatGPT for outreach personalization."
    ))
    assert out.get("cluster") == "gtm_sales"


def test_standards_question_from_library():
    plan = se._scenario_from_library_key("people_comp")
    q = se._pick_probe("standards", plan, 0)
    assert "comp" in q.lower() or "pay" in q.lower()


def test_anchor_in_flight_user_message_personalizes_before_primary():
    """Regression: anchor answer is user_message, not history — must not mix RTO + TA probes."""
    plan = se.build_scenario_plan(
        {"job_family": "hr_people", "level": "head_of", "job_family_label": "HR"},
        "seed",
    )
    opening_only = [{"role": "model", "content": "What is your role?"}]
    anchor_line = "Head of Talent Acquisition. ChatGPT for job descriptions."
    without_current = se._apply_anchor_context(plan, opening_only)
    assert without_current.get("cluster") == "people"
    with_current = se._apply_anchor_context(
        plan, se._messages_for_context(opening_only, anchor_line)
    )
    assert with_current.get("cluster") == "people_ta"
    assert "offer" in with_current.get("probe_bank", [""])[1].lower()


if __name__ == "__main__":
    test_thin_answer_detection()
    test_complication_signal_skips_portfolio_loop()
    test_banned_stem_detected()
    test_coo_cluster_for_gm_exec()
    test_finalize_uses_thin_probe()
    test_clarification_you_mean_published()
    test_ta_anchor_swaps_people_scenario()
    test_hrbp_anchor_swaps_people_scenario()
    test_er_anchor_swaps_people_scenario()
    test_gtm_sales_anchor_swaps_scenario()
    test_standards_question_from_library()
    test_anchor_in_flight_user_message_personalizes_before_primary()
    print("ok")
