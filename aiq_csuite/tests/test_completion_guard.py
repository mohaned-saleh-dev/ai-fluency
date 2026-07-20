"""Tests for session completion guards and rate limiting."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_tmpdir = tempfile.mkdtemp()
os.environ["AIQ_SQLITE_PATH"] = os.path.join(_tmpdir, "test_guards.db")

import app as aiq_app  # noqa: E402


def test_rate_limiter_allows_under_limit():
    aiq_app._rate_buckets.clear()
    for _ in range(5):
        assert not aiq_app._rate_limited("test:1.2.3.4", 10)


def test_rate_limiter_blocks_over_limit():
    aiq_app._rate_buckets.clear()
    for _ in range(10):
        assert not aiq_app._rate_limited("test:1.2.3.4", 10)
    assert aiq_app._rate_limited("test:1.2.3.4", 10)


def test_rate_limiter_resets_after_window():
    aiq_app._rate_buckets.clear()
    old_time = aiq_app.time.time() - 120
    aiq_app._rate_buckets["test:1.2.3.4"] = [old_time] * 10
    assert not aiq_app._rate_limited("test:1.2.3.4", 10)


def test_session_effort_signal_detects_thin():
    msgs = [
        {"role": "user", "content": "idk"},
        {"role": "model", "content": "Okay, tell me more"},
        {"role": "user", "content": "not sure"},
        {"role": "model", "content": "What do you think?"},
        {"role": "user", "content": "yes"},
        {"role": "model", "content": "Anything else?"},
        {"role": "user", "content": "no"},
    ]
    sig = aiq_app._session_effort_signal(msgs)
    assert sig["level"] == "thin"
    assert sig["thin_ratio"] == 1.0


def test_session_effort_signal_detects_light():
    msgs = [
        {"role": "user", "content": "I use ChatGPT sometimes for quick drafting"},
        {"role": "model", "content": "What for?"},
        {"role": "user", "content": "For writing emails and summarizing meetings"},
        {"role": "model", "content": "How do you check them?"},
        {"role": "user", "content": "I just send them after a quick check"},
    ]
    sig = aiq_app._session_effort_signal(msgs)
    assert sig["level"] == "light"


def test_session_effort_signal_detects_ok():
    msgs = [
        {
            "role": "user",
            "content": "I'm a product manager and I use ChatGPT for drafting specs, Copilot for code reviews, and sometimes Claude for research. I always iterate on the prompts if the first output is off.",
        },
        {"role": "model", "content": "How do you verify the output?"},
        {
            "role": "user",
            "content": "I check requirements against our PRD, run them by the engineer, and verify compliance rules before finalizing.",
        },
    ]
    sig = aiq_app._session_effort_signal(msgs)
    assert sig["level"] == "ok"


def test_complete_rejects_zero_replies():
    client = aiq_app.app.test_client()
    with aiq_app.app.app_context():
        aiq_app.init_db()
        sid = aiq_app.new_session("test", {}, {})
        r = client.post(f"/api/session/{sid}/complete")
        assert r.status_code == 400
        body = r.get_json()
        assert body.get("code") == "no_replies_yet"


def test_complete_rejects_thin_session():
    client = aiq_app.app.test_client()
    with aiq_app.app.app_context():
        aiq_app.init_db()
        ass = aiq_app.build_assessment_block("head_of", "general_management")
        var = {"assessment": ass}
        sid = aiq_app.new_session("test", {}, var)
        for text in ["idk", "not sure", "yes"]:
            aiq_app.insert_message(sid, "user", text)
            aiq_app.insert_message(sid, "model", "Tell me more")
        r = client.post(f"/api/session/{sid}/complete")
        assert r.status_code == 400
        body = r.get_json()
        assert body.get("code") == "not_enough_data"


def test_complete_rejects_short_session():
    client = aiq_app.app.test_client()
    with aiq_app.app.app_context():
        aiq_app.init_db()
        ass = aiq_app.build_assessment_block("head_of", "general_management")
        var = {"assessment": ass}
        sid = aiq_app.new_session("test", {}, var)
        aiq_app.insert_message(sid, "user", "Hello")
        aiq_app.insert_message(sid, "model", "Hi there")
        r = client.post(f"/api/session/{sid}/complete")
        assert r.status_code == 400
        body = r.get_json()
        assert body.get("code") == "not_enough_data"


if __name__ == "__main__":
    test_rate_limiter_allows_under_limit()
    print("rate limiter under limit: ok")
    test_rate_limiter_blocks_over_limit()
    print("rate limiter over limit: ok")
    test_rate_limiter_resets_after_window()
    print("rate limiter window reset: ok")
    test_session_effort_signal_detects_thin()
    print("effort thin: ok")
    test_session_effort_signal_detects_light()
    print("effort light: ok")
    test_session_effort_signal_detects_ok()
    print("effort ok: ok")
    test_complete_rejects_zero_replies()
    print("complete rejects zero replies: ok")
    test_complete_rejects_thin_session()
    print("complete rejects thin: ok")
    test_complete_rejects_short_session()
    print("complete rejects short: ok")
    print("all ok")
