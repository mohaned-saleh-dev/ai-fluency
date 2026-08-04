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
    """Care → Strategy & Ops is the same job as Strategy & Ops: it aliases onto the one
    S&O pool rather than carrying a duplicate scenario of its own, so a participant can't
    reach a second set of variants by picking the other label."""
    ass = _assessment("ic", "finance", "care_strategy_ops")
    plan = se.build_scenario_plan(ass, "seed-1")
    assert plan["role_key"] == "strategy_ops"
    assert plan["cluster"] in se._SCENARIO_VARIANTS["strategy_ops"]
    # The participant-facing label is still the function they picked, not the scoring family.
    assert plan["job_family_label"] == "Strategy & Ops (Care)"


def test_alias_and_canonical_function_share_one_pool():
    lib = se._load_library()
    assert "care_strategy_ops" not in lib, "alias must not carry a duplicate library entry"
    assert se.canonical_function("care_strategy_ops") == "strategy_ops"
    assert se.scenario_pool_for(_assessment("ic", "finance", "care_strategy_ops")) == (
        se.scenario_pool_for(_assessment("ic", "finance", "strategy_ops"))
    )


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


def test_scenario_variants_are_populated_and_seed_stable():
    """Each of the four functions with multiple scenarios has every variant populated, and a
    given client_seed always resolves to the same variant (session-stable), while different
    seeds are able to land on different variants (not always the first one)."""
    lib = se._load_library()
    seen_per_func = {}
    for func, variants in se._SCENARIO_VARIANTS.items():
        for v in variants:
            entry = lib.get(v)
            assert isinstance(entry, dict), f"{func}: missing variant {v}"
            assert str(entry.get("primary_setup") or "").strip(), f"{func}: blank variant {v}"
        ass = _assessment("ic", "care_operations", func)
        # Same seed -> same scenario every time.
        first = se.build_scenario_plan(ass, "stable-seed")["cluster"]
        again = se.build_scenario_plan(ass, "stable-seed")["cluster"]
        assert first == again
        seen_per_func[func] = {
            se.build_scenario_plan(ass, f"seed-{i}")["cluster"] for i in range(30)
        }
    for func, seen in seen_per_func.items():
        assert len(seen) > 1, f"{func}: variants never diversify across seeds"


# --- scenario pool shape (the published spec) -----------------------------------------

def test_pool_sizes_match_published_spec():
    """Strategy & Ops carries 6 variants spread across verticals; each Care role carries 3.
    Pool size is also the retake cap, so this is the number the report and the cap quote."""
    assert len(se._SCENARIO_VARIANTS["strategy_ops"]) == 6
    for role in ("care_quality", "care_training", "care_content"):
        assert len(se._SCENARIO_VARIANTS[role]) == 3


def test_every_pool_scenario_has_the_question_ladder_and_twist():
    """The interview shape is data, not prose: inputs -> output -> validation, then a
    twist. A variant missing any of these would silently fall back to free-form probing."""
    lib = se._load_library()
    for func, variants in se._SCENARIO_VARIANTS.items():
        for v in variants:
            e = lib[v]
            ladder = e.get("question_ladder")
            assert isinstance(ladder, dict), f"{v}: no question_ladder"
            for beat in se.LADDER_BEATS:
                assert str(ladder.get(beat) or "").strip(), f"{v}: blank ladder beat {beat}"
            for field in ("complication_inject", "gauging", "standards_question"):
                assert str(e.get(field) or "").strip(), f"{v}: blank {field}"


def test_scenarios_are_tool_agnostic():
    """Scenarios name 'an AI tool', never a specific vendor — the assessment is about how
    someone works with a model, not which brand their team happens to license."""
    import json

    assert "ChatGPT" not in json.dumps(se._load_library(), ensure_ascii=False)


def test_strategy_ops_scenarios_are_vertical_agnostic():
    """S&O roles are assessed on the same pool regardless of which vertical they support,
    so no S&O scenario may assume a contact-centre frame."""
    lib = se._load_library()
    banned = ("ticket", "queue", "helpdesk", "agent")
    for v in se._SCENARIO_VARIANTS["strategy_ops"]:
        blob = " ".join(
            str(lib[v].get(f) or "") for f in ("primary_setup", "primary_stakes")
        ).lower()
        for word in banned:
            assert word not in blob, f"{v}: S&O scenario assumes a Care frame ({word!r})"


# --- retake rotation ------------------------------------------------------------------

def test_retake_rotates_through_every_variant_without_repeating():
    ass = _assessment("ic", "finance", "strategy_ops")
    pool = se.scenario_pool_for(ass)[1]
    served: list = []
    for attempt in range(1, len(pool) + 1):
        plan = se.build_scenario_plan(
            ass, f"session-{attempt}", attempt_no=attempt, served=served,
            selection_seed="participant-1",
        )
        assert plan["cluster"] not in served, "a retake served a scenario already seen"
        assert plan["attempt"]["number"] == attempt
        assert not plan["attempt"]["pool_exhausted"]
        served.append(plan["cluster"])
    assert sorted(served) == sorted(pool), "rotation did not cover the whole pool"


def test_pool_exhaustion_is_flagged_after_the_cap():
    ass = _assessment("ic", "care_operations", "care_quality")
    pool = se.scenario_pool_for(ass)[1]
    plan = se.build_scenario_plan(
        ass, "s", attempt_no=len(pool) + 1, served=pool, selection_seed="p"
    )
    assert plan["attempt"]["pool_exhausted"] is True


def test_first_attempt_is_stable_across_restarts():
    """Abandoning and restarting attempt 1 must land on the same scenario — the session
    seed changes every time, so selection has to key off the participant, not the session."""
    ass = _assessment("ic", "finance", "strategy_ops")
    picks = {
        se.build_scenario_plan(
            ass, f"fresh-session-{i}", attempt_no=1, served=[], selection_seed="participant-9"
        )["cluster"]
        for i in range(12)
    }
    assert len(picks) == 1


def test_different_participants_spread_across_the_pool():
    ass = _assessment("ic", "finance", "strategy_ops")
    picks = {
        se.build_scenario_plan(
            ass, "s", attempt_no=1, served=[], selection_seed=f"participant-{i}"
        )["cluster"]
        for i in range(40)
    }
    assert len(picks) > 1, "first attempts never diversify across participants"


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
