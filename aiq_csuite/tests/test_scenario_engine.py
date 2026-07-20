"""Unit tests for scenario_engine's kept surface: scenario routing + shared heuristics.
(The live turn machinery moved to conversation_engine; scoring paths need an LLM and are
exercised by scripts/run_scoring_validation.py instead.)"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scenario_engine as se  # noqa: E402


# --- cluster routing (family × level) -------------------------------------------------

def test_cluster_routing_senior_tiers_get_strategic_scenarios():
    assert se._scenario_cluster("care_operations", "executive") == "ops_exec"
    assert se._scenario_cluster("care_operations", "head_of") == "ops_exec"
    assert se._scenario_cluster("product_engineering", "executive") == "product_exec"
    assert se._scenario_cluster("general_management", "people_manager") == "coo_office"


def test_cluster_routing_hands_on_tiers_keep_base_cluster():
    assert se._scenario_cluster("care_operations", "ic") == "ops"
    assert se._scenario_cluster("product_engineering", "ic") == "product"
    assert se._scenario_cluster("finance", "ic") == "fin"
    assert se._scenario_cluster("hr_people", "ic") == "people"


# --- function-specific scenario decoupling --------------------------------------------

def _assessment(level, family, function=None):
    from assessment_profiles import build_assessment_block

    return build_assessment_block(level, family, function)


def test_job_function_selects_dedicated_scenario():
    """Care → Strategy & Ops routes to its own scenario while keeping finance weights."""
    ass = _assessment("ic", "finance", "care_strategy_ops")
    plan = se.build_scenario_plan(ass, "seed-1")
    assert plan["cluster"] == "care_strategy_ops"
    assert plan["primary"]["title"] == "The Monday readout"
    # The participant-facing label is the function they picked, not the scoring family.
    assert plan["job_family_label"] == "Strategy & Ops (Care)"


def test_no_function_falls_back_to_family_cluster():
    ass = _assessment("ic", "finance", None)
    plan = se.build_scenario_plan(ass, "seed-1")
    assert plan["cluster"] == "fin"
    assert plan["primary"]["title"] == "Board deck numbers"


def _fake_library_with_blank(monkeypatch, blank_keys):
    """Real library with the given entries blanked — a synthetic fixture so tests never
    depend on (or encourage) blank scaffolds in the shipped scenario_library.json."""
    lib = se._load_library()
    for k in blank_keys:
        lib[k] = {f: "" for f in ("primary_title", "primary_setup", "primary_stakes",
                                  "complication_inject", "standards_prompt",
                                  "standards_question")} | {"probe_bank": []}
    monkeypatch.setattr(se, "_load_library", lambda: lib)
    return lib


def test_unpopulated_function_scenario_falls_back(monkeypatch):
    """A function key whose library entry has a blank primary_setup must not be selected."""
    _fake_library_with_blank(monkeypatch, ["ops"])
    ass = dict(_assessment("ic", "care_operations", None))
    ass["job_function"] = "ops"
    plan = se.build_scenario_plan(ass, "seed-1")
    # The blank entry is skipped on the function path AND on the family path (which also
    # resolves to "ops" here), so the plan lands on the generic scenario, never a blank one.
    assert plan["cluster"] == "gm"
    assert plan["primary"]["setup"].strip()


def test_blank_family_cluster_falls_back_to_generic(monkeypatch):
    """If a family-routed cluster entry is ever blanked, sessions get the generic scenario
    instead of silently running with no scenario material (regression: ops/ops_exec were
    blanked as scaffolds and care_operations sessions lost their scenario entirely)."""
    _fake_library_with_blank(monkeypatch, ["ops_exec"])
    ass = _assessment("executive", "care_operations", None)
    plan = se.build_scenario_plan(ass, "seed-1")
    assert plan["cluster"] == "gm"
    assert plan["primary"]["setup"].strip()


def test_all_router_reachable_clusters_are_populated():
    """Every cluster the family x level router can emit must have real scenario content
    in the shipped library — a blank entry silently degrades live interviews."""
    from assessment_profiles import JOB_FAMILIES, LEVELS

    lib = se._load_library()
    required = ("primary_title", "primary_setup", "primary_stakes",
                "complication_inject", "standards_prompt")
    for fam in (x["slug"] for x in JOB_FAMILIES):
        for lev in (x["slug"] for x in LEVELS):
            cluster = se._scenario_cluster(fam, lev)
            entry = lib.get(cluster)
            assert isinstance(entry, dict), f"{fam}/{lev} -> {cluster}: missing from library"
            for field in required:
                assert str(entry.get(field) or "").strip(), (
                    f"{fam}/{lev} -> {cluster}: blank {field}"
                )


# --- clarification / purpose heuristics (used by app.py effort signal) ----------------

def test_purpose_questions_detected():
    assert se._is_purpose_question("Okay, but what is the purpose of this chat")
    assert se._is_purpose_question("is this a test?")
    assert se._is_purpose_question("who are you")
    assert not se._is_purpose_question("I'd check the numbers against the export first.")


def test_clarification_detection():
    assert se._is_clarification_request("what do you mean?")
    assert se._is_clarification_request("Okay, but what is the purpose of this chat")
    assert se._is_clarification_request("?")
    assert not se._is_clarification_request(
        "I'd clean the export, remove customer names, then ask for grouping by queue."
    )


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__, "-q"]))
