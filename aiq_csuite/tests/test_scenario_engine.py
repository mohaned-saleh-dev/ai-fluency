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
    assert "three bullets" in q.lower()
