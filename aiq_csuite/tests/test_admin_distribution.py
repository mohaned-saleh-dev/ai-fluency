"""Distribution stats behind the admin charts.

These exist because a distribution chart is read as evidence. If the spread numbers or
the floor/ceiling rates are wrong, a cohort that the assessment is failing to separate
looks fine on screen — which is the specific failure the chart is meant to catch.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app as A  # noqa: E402


def _rows(composites, dims=None, expected=None):
    """Minimal export-shaped rows: composite plus six dimension scores."""
    out = []
    for i, c in enumerate(composites):
        r = {"AiQ": c}
        for d in range(1, 7):
            r[f"D{d}"] = (dims or {}).get(f"D{d}", [5.0] * len(composites))[i]
        if expected:
            r["expected_score"] = expected[i]
        out.append(r)
    return out


# --- percentiles / spread -------------------------------------------------------------

def test_percentile_interpolates():
    vals = [10.0, 20.0, 30.0, 40.0]
    assert A._pct(vals, 0.0) == 10.0
    assert A._pct(vals, 1.0) == 40.0
    assert A._pct(vals, 0.5) == 25.0


def test_percentile_handles_degenerate_input():
    assert A._pct([], 0.5) is None
    assert A._pct([7.0], 0.5) == 7.0


def test_spread_reports_iqr_and_sd():
    s = A._spread([10.0, 20.0, 30.0, 40.0, 50.0])
    assert s["n"] == 5
    assert s["median"] == 30.0
    assert s["min"] == 10.0 and s["max"] == 50.0
    assert s["iqr"] == pytest.approx(20.0, abs=0.1)
    assert s["sd"] > 0


def test_spread_of_identical_scores_is_zero():
    """The signature of an instrument that is not separating anyone."""
    s = A._spread([50.0] * 12)
    assert s["sd"] == 0.0
    assert s["iqr"] == 0.0


def test_spread_of_empty_set_does_not_crash():
    assert A._spread([])["n"] == 0


# --- histogram ------------------------------------------------------------------------

def test_histogram_bins_cover_every_score_exactly_once():
    comps = [0.0, 9.9, 10.0, 55.5, 99.9, 100.0]
    dist = A._distribution_block(_rows(comps))
    assert sum(b["n"] for b in dist["composite"]["bins"]) == len(comps), "a score fell outside all bins"


def test_histogram_top_bin_includes_a_perfect_score():
    """100.0 must land in 90-100 rather than vanishing off the end."""
    dist = A._distribution_block(_rows([100.0]))
    assert dist["composite"]["bins"][-1]["n"] == 1


def test_unscored_sessions_are_excluded_not_counted_as_zero():
    """An abandoned run has no composite. Treating it as 0 would drag the whole cohort
    down and invent a floor spike that is not there."""
    rows = _rows([60.0, 70.0]) + [{"AiQ": "", "D1": ""}]
    dist = A._distribution_block(rows)
    assert dist["composite"]["n"] == 2
    assert dist["composite"]["min"] == 60.0


# --- per-dimension discrimination -----------------------------------------------------

def test_floor_and_ceiling_rates_flag_a_dead_dimension():
    n = 10
    dims = {"D1": [2.0] * n, "D2": [9.0] * n, "D3": [5.0] * n}
    dist = A._distribution_block(_rows([50.0] * n, dims))
    by = {d["code"]: d for d in dist["dimensions"]}
    assert by["D1"]["at_floor_pct"] == 100.0
    assert by["D2"]["at_ceiling_pct"] == 100.0
    # A dimension parked in the middle is equally dead — caught by sd, not by the bands.
    assert by["D3"]["at_floor_pct"] == 0.0
    assert by["D3"]["sd"] == 0.0


def test_anchor_bands_partition_the_cohort():
    dims = {"D1": [1.0, 3.0, 5.0, 7.0, 8.0, 10.0]}
    dist = A._distribution_block(_rows([50.0] * 6, dims))
    d1 = next(d for d in dist["dimensions"] if d["code"] == "D1")
    b = d1["anchor_bands"]
    assert b["low"] + b["mid"] + b["high"] == 6
    assert b["low"] == 2 and b["high"] == 2 and b["mid"] == 2


def test_every_dimension_is_reported_even_when_unscored():
    dist = A._distribution_block([])
    assert [d["code"] for d in dist["dimensions"]] == [f"D{i}" for i in range(1, 7)]


# --- self-predicted vs measured -------------------------------------------------------

def test_self_vs_actual_pairs_only_when_a_prediction_exists():
    rows = _rows([60.0, 70.0, 80.0], expected=[55, "", 75])
    pairs = A._distribution_block(rows)["self_vs_actual"]
    assert len(pairs) == 2
    assert {"expected": 55.0, "actual": 60.0} in pairs


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
