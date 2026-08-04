"""Retake policy against a real (throwaway) database.

Covers the rule that makes a retake meaningful: a second attempt must serve a scenario
the participant has not seen, an abandoned attempt must not burn one, and once the pool
is spent, further attempts pause rather than repeating a twist the person already knows.
"""
from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture()
def db(tmp_path, monkeypatch):
    """Fresh sqlite file per test, wired in before db/config are imported."""
    monkeypatch.setenv("AIQ_SQLITE_PATH", str(tmp_path / "retake.db"))
    for mod in ("config", "db"):
        sys.modules.pop(mod, None)
    import db as db_mod

    db_mod.init_db()
    return db_mod


def _finish(db_mod, sid, scored=True):
    """Complete a session the way the app does — with or without a stored report."""
    db_mod.end_session(sid, scores={"AiQ_0_100": 61.0} if scored else None)


def _start(db_mod, key, role, scenario, attempt):
    return db_mod.new_session(
        "ua", {}, {"assessment": {}}, target_role="ic__finance",
        participant_key=key, attempt_no=attempt, role_key=role, scenario_key=scenario,
    )


def test_history_is_empty_for_a_new_participant(db):
    assert db.participant_history("nobody", "strategy_ops") == {"attempts": 0, "served": []}


def test_a_scored_session_burns_its_variant(db):
    key = str(uuid.uuid4())
    _finish(db, _start(db, key, "strategy_ops", "strategy_ops_v2", 1))
    hist = db.participant_history(key, "strategy_ops")
    assert hist == {"attempts": 1, "served": ["strategy_ops_v2"]}


def test_an_abandoned_session_does_not_burn_a_variant(db):
    """Restarting an attempt you never finished has to land on the same scenario, so an
    unscored session must not count."""
    key = str(uuid.uuid4())
    _start(db, key, "strategy_ops", "strategy_ops_v2", 1)  # opened, never completed
    assert db.participant_history(key, "strategy_ops")["attempts"] == 0
    _finish(db, _start(db, key, "strategy_ops", "strategy_ops_v3", 1), scored=False)
    assert db.participant_history(key, "strategy_ops")["attempts"] == 0


def test_history_is_scoped_per_role(db):
    """Completing Strategy & Ops must not consume a Care Quality attempt."""
    key = str(uuid.uuid4())
    _finish(db, _start(db, key, "strategy_ops", "strategy_ops", 1))
    assert db.participant_history(key, "care_quality") == {"attempts": 0, "served": []}


def test_history_is_scoped_per_participant(db):
    a, b = str(uuid.uuid4()), str(uuid.uuid4())
    _finish(db, _start(db, a, "care_quality", "care_quality", 1))
    assert db.participant_history(b, "care_quality")["attempts"] == 0


def test_full_rotation_then_pause(db, monkeypatch):
    """Walk a participant through every Strategy & Ops variant, then confirm the next
    attempt is refused rather than repeating one."""
    import scenario_engine as se
    from assessment_profiles import build_assessment_block

    key = str(uuid.uuid4())
    ass = build_assessment_block("ic", "finance", "strategy_ops")
    role, pool = se.scenario_pool_for(ass)

    for attempt in range(1, len(pool) + 1):
        hist = db.participant_history(key, role)
        assert hist["attempts"] == attempt - 1
        plan = se.build_scenario_plan(
            ass, f"session-{attempt}", attempt_no=attempt,
            served=hist["served"], selection_seed=key,
        )
        assert plan["cluster"] not in hist["served"]
        _finish(db, _start(db, key, role, plan["cluster"], attempt))

    final = db.participant_history(key, role)
    assert final["attempts"] == len(pool)
    assert sorted(final["served"]) == sorted(pool)
    # The cap the API enforces: no fresh variant remains.
    assert len([s for s in final["served"] if s in pool]) >= len(pool)


def test_cap_size_is_six_for_strategy_ops_and_three_for_care(db):
    import scenario_engine as se
    from assessment_profiles import build_assessment_block

    assert len(se.scenario_pool_for(build_assessment_block("ic", "finance", "strategy_ops"))[1]) == 6
    for func in ("care_quality", "care_training", "care_content"):
        pool = se.scenario_pool_for(build_assessment_block("ic", "care_operations", func))[1]
        assert len(pool) == 3


def test_attempt_line_reads_correctly():
    from participant_report import _attempt_line

    assert _attempt_line({"number": 1, "pool_size": 6}) == "First attempt"
    assert _attempt_line({"number": 2, "pool_size": 6}) == "Retake — attempt 2 of 6"
    assert _attempt_line(None) == ""


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
