"""The published dimension-weight tables are a contract.

Weights are what turn identical demonstrated behaviour into different composites per
role, and they are documented externally. If a delta is retuned, these tests fail and the
published table has to move with it — not the other way round.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest  # noqa: E402

from assessment_profiles import _DIM_ORDER, _weights_from_deltas, build_assessment_block  # noqa: E402

# (job_function, job_family) -> published IC weights, D1..D6.
PUBLISHED_IC_WEIGHTS = {
    ("strategy_ops", "finance"): (0.190, 0.140, 0.270, 0.240, 0.070, 0.090),
    ("care_strategy_ops", "finance"): (0.190, 0.140, 0.270, 0.240, 0.070, 0.090),
    ("care_quality", "care_operations"): (0.170, 0.130, 0.310, 0.180, 0.080, 0.130),
    ("care_training", "care_operations"): (0.162, 0.200, 0.238, 0.181, 0.171, 0.048),
    ("care_content", "care_operations"): (0.160, 0.140, 0.250, 0.160, 0.180, 0.110),
}

# Published depth focus per role: the two dimensions the interview goes deep on.
PUBLISHED_DEPTH_FOCUS = {
    ("strategy_ops", "finance"): ("D3", "D4"),
    ("care_quality", "care_operations"): ("D3", "D4"),
    ("care_training", "care_operations"): ("D3", "D2"),
    ("care_content", "care_operations"): ("D3", "D5"),
}


@pytest.mark.parametrize(("key", "expected"), sorted(PUBLISHED_IC_WEIGHTS.items()))
def test_ic_weights_match_published_table(key, expected):
    func, fam = key
    w = _weights_from_deltas("ic", fam, func)
    got = tuple(round(w[c], 3) for c in _DIM_ORDER)
    assert got == expected


@pytest.mark.parametrize(("key", "expected"), sorted(PUBLISHED_IC_WEIGHTS.items()))
def test_weights_always_sum_to_one(key, expected):
    func, fam = key
    w = _weights_from_deltas("ic", fam, func)
    assert sum(w.values()) == pytest.approx(1.0, abs=1e-6)


@pytest.mark.parametrize(("key", "expected"), sorted(PUBLISHED_DEPTH_FOCUS.items()))
def test_depth_focus_matches_published_lean(key, expected):
    func, fam = key
    block = build_assessment_block("ic", fam, func)
    assert tuple(block["depth_focus"]) == expected


def test_head_of_shifts_weight_toward_org_design_and_governance():
    """Moving IC -> Head of moves weight toward D4 (org design) and D6 (governance) and
    away from hands-on execution — the documented reason two people with identical
    behaviour land on different composites."""
    ic = _weights_from_deltas("ic", "finance", "strategy_ops")
    head = _weights_from_deltas("head_of", "finance", "strategy_ops")
    assert head["D4"] > ic["D4"]
    assert head["D6"] > ic["D6"]
    assert head["D2"] < ic["D2"]


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
