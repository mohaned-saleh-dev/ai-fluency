import hashlib
import json
import os
import re
import time
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from flask import Flask, Response, jsonify, request, send_from_directory

# Run from aiq_csuite/ directory
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import config
from config import (
    ADMIN_SECRET,
    ADMIN_SECRETS,
    OLLAMA_MODEL,
    SESSION_MAX_AGE_SEC,
    TARGET_DURATION_SEC,
    ensure_instance,
    normalize_admin_token,
)

# AiQ six dimensions (labels for APIs / UI)
DIMENSION_ORDER: List[Tuple[str, str]] = [
    ("D1", "Awareness & opportunity"),
    ("D2", "Prompts & comms"),
    ("D3", "Critical judgment"),
    ("D4", "Workflows & org design"),
    ("D5", "Clarity, craft & output fit"),
    ("D6", "Risk & responsible use"),
]
from db import (
    get_conn,
    get_dimension_shift_codes,
    init_db,
    new_session,
    insert_message,
    list_messages,
    insert_event,
    end_session,
    session_stats,
    delete_session,
    expire_stale_open_sessions,
)
import gemini_service as gs
from assessment_profiles import (
    DEFAULT_FAMILY,
    DEFAULT_LEVEL,
    JOB_FAMILIES,
    LEVELS,
    build_assessment_block,
    is_technical_product_family,
)
from ollama_client import resolve_backend
from coaching_engine import build_coaching_dimension_row, fam_cluster, pick_one_course

GEMINI_API_KEY = config.GEMINI_API_KEY


def _llm_status() -> tuple:
    """(ok, backend, detail, model_name)."""
    mode, detail = resolve_backend(GEMINI_API_KEY)
    mname: str
    if mode == "gemini":
        mname = config.GEMINI_MODEL
    elif mode == "ollama":
        mname = OLLAMA_MODEL
    else:
        mname = ""
    return (mode != "error"), mode, detail, mname


app = Flask(
    __name__,
    static_folder="static",
    static_url_path="/static",
    template_folder="templates",
)


def _admin_ok() -> bool:
    secrets = {normalize_admin_token(s) for s in ADMIN_SECRETS if normalize_admin_token(s)}
    if not secrets:
        return False
    token = normalize_admin_token(request.args.get("token") or "")
    if token and token in secrets:
        return True
    # Some networks / extensions interfere with Authorization; this header is a fallback.
    xt = normalize_admin_token((request.headers.get("X-Aiq-Admin-Token") or ""))
    if xt and xt in secrets:
        return True
    auth = (request.headers.get("Authorization") or "").strip()
    if auth[:7].lower() == "bearer ":
        bearer = normalize_admin_token(auth[7:])
        if bearer and bearer in secrets:
            return True
    return False


def _expire_stale_sessions() -> int:
    """End sessions that are still open but past SESSION_MAX_AGE_SEC from created_at. Returns rows updated."""
    return expire_stale_open_sessions(SESSION_MAX_AGE_SEC)


_DECK_DIR = os.path.join(HERE, "static", "deck")

# —— Executive AiQ deck (Slideshow HTML + generated PDF) — not the in-chat one-page session report. ——


@app.route("/")
def index():
    return send_from_directory(HERE, "static/index.html")


@app.route("/deck/executive.pdf", methods=["GET"])
def aiq_deck_executive_pdf():
    """
    **Real PDF** — executive deck (product copy aligned with D5/D6, 6+2 flow, weights, reflection framing).
    """
    from executive_deck_pdf import build_executive_deck_pdf_bytes

    try:
        data = build_executive_deck_pdf_bytes()
    except Exception as e:
        return jsonify({"error": f"Could not build PDF: {e!s}"}), 500
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    return Response(
        data,
        mimetype="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="AiQ-Executive-Deck-Tamara-{stamp}.pdf"',
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
        },
    )


@app.route("/deck/executive", methods=["GET"])
def aiq_deck_executive():
    """
    Slide-style HTML (legacy slide layout). For the canonical **PDF**, use **/deck/executive.pdf**.
    """
    return send_from_directory(_DECK_DIR, "aiq-executive-summary.html")


@app.route("/deck/executive-memo", methods=["GET"])
def aiq_deck_executive_memo():
    """Long-form executive read-ahead (`aiq-executive-document.html`)."""
    return send_from_directory(_DECK_DIR, "aiq-executive-document.html")


@app.route("/admin", strict_slashes=False)
def admin():
    """
    The HTML is public (no secret in the URL); session list requires the secret on
    /api/admin/* (Bearer or ?token=). Open /admin, paste AIQ_ADMIN_SECRET, Save, Load sessions.
    """
    return send_from_directory(HERE, "static/admin.html")


@app.route("/api/health", methods=["GET"])
def health():
    ok, mode, detail, mname = _llm_status()
    return jsonify(
        {
            "ok": ok,
            "backend": mode,
            "detail": detail,
            "model": mname or (config.GEMINI_MODEL if GEMINI_API_KEY else ""),
        }
    )


@app.route("/api/assessment/options", methods=["GET"])
def assessment_options():
    """Level × job family choices; weights are fixed in code (see `assessment_profiles.py`)."""
    return jsonify(
        {
            "levels": LEVELS,
            "job_families": JOB_FAMILIES,
            "defaults": {"level": DEFAULT_LEVEL, "job_family": DEFAULT_FAMILY},
        }
    )


@app.route("/api/health/llm", methods=["GET"])
def health_llm():
    ok, mode, detail, mname = _llm_status()
    return jsonify(
        {
            "ok": ok,
            "backend": mode,
            "detail": detail,
            "model": mname,
        }
    )


def _resume_dimension_shifts_for_client(messages: List[dict], ev_rows: List) -> List[dict]:
    """Map dim_shift events to chat indices so the UI can replay topic banners."""
    model_idxs = [i for i, m in enumerate(messages) if (m.get("role") or "") == "model"]
    out: List[dict] = []
    for k, r in enumerate(ev_rows):
        try:
            payload = json.loads(r["payload_json"] or "{}")
        except (json.JSONDecodeError, TypeError, KeyError):
            continue
        code = payload.get("code")
        if not code:
            continue
        label = str(payload.get("label") or "")[:120]
        idx_k = k + 1
        if idx_k >= len(model_idxs):
            break
        out.append({"insert_before_index": model_idxs[idx_k], "code": str(code), "label": label})
    return out


@app.route("/api/session/<session_id>", methods=["GET"])
def get_session_resume(session_id: str):
    """Public read for resuming an in-progress chat (bookmark / reload / new tab)."""
    init_db()
    _expire_stale_sessions()
    with get_conn() as c:
        row = c.execute(
            "SELECT variation_json, ended_at, started_at, created_at FROM sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
    if not row:
        return jsonify({"error": "Unknown session"}), 404
    var = json.loads(row[0] or "{}")
    assessment = (var or {}).get("assessment") if isinstance(var, dict) else None
    ended = row[1] is not None and row[1] != 0
    started_at = float(row[2] or row[3] or 0.0)
    msgs = list_messages(session_id)
    public_msgs = [{"role": m["role"], "content": m["content"]} for m in msgs]
    with get_conn() as c:
        ev_rows = c.execute(
            "SELECT payload_json FROM events WHERE session_id = ? AND type = ? ORDER BY created_at",
            (session_id, "dim_shift"),
        ).fetchall()
    shifts = _resume_dimension_shifts_for_client(msgs, ev_rows)
    return jsonify(
        {
            "session_id": session_id,
            "ended": ended,
            "assessment": assessment,
            "messages": public_msgs,
            "dimension_shifts": shifts,
            "target_duration_sec": TARGET_DURATION_SEC,
            "started_at": started_at,
        }
    )


@app.route("/api/session/start", methods=["POST"])
def start_session():
    ok, _, detail, _ = _llm_status()
    if not ok:
        return jsonify({"error": detail or "No LLM backend. See /api/health/llm."}), 503
    body = request.get_json(force=True) or {}
    client_seed = str(body.get("seed") or (request.remote_addr, time.time()))
    user_agent = request.headers.get("User-Agent", "")
    client_meta = body.get("client_meta")
    level = body.get("level")
    job_family = body.get("job_family")
    init_db()
    ensure_instance()
    var = gs.build_variation_for_session(client_seed)
    ass = build_assessment_block(level, job_family)
    var["assessment"] = ass
    sid = new_session(
        user_agent, client_meta, var, target_role=ass.get("profile_id", "all_levels")
    )
    opening = gs.opening_message(var)
    insert_message(sid, "model", opening)
    return jsonify(
        {
            "session_id": sid,
            "opening": opening,
            "target_duration_sec": TARGET_DURATION_SEC,
            "assessment": ass,
            "variation_themes_sample": {k: v for k, v in var.items() if str(k).endswith("_theme")},
        }
    )


@app.route("/api/session/<session_id>/event", methods=["POST"])
def track_event(session_id: str):
    init_db()
    _expire_stale_sessions()
    with get_conn() as c:
        s = c.execute("SELECT ended_at FROM sessions WHERE id = ?", (session_id,)).fetchone()
    if not s:
        return jsonify({"ok": False, "error": "Unknown session"}), 404
    if s[0] is not None and s[0] != 0:
        return jsonify(
            {
                "ok": False,
                "error": "session_ended",
                "message": "This session has ended (time limit or completed).",
            }
        ), 410
    b = request.get_json(force=True) or {}
    et = b.get("type", "beacon")
    insert_event(session_id, et, b)
    return jsonify({"ok": True})


@app.route("/api/session/<session_id>/message", methods=["POST"])
def send_message(session_id: str):
    ok, _, detail, _ = _llm_status()
    if not ok:
        return jsonify({"error": detail or "No LLM backend. See /api/health/llm."}), 503
    b = request.get_json(force=True) or {}
    user_text = (b.get("text") or "").strip()
    if not user_text or len(user_text) > 12000:
        return jsonify({"error": "Invalid text"}), 400

    init_db()
    _expire_stale_sessions()
    rag = gs.get_rag_for_app()
    with get_conn() as c:
        row = c.execute(
            "SELECT variation_json, ended_at FROM sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
    if not row:
        return jsonify({"error": "Unknown session"}), 404
    if row[1] is not None and row[1] != 0:
        return jsonify(
            {
                "error": "This session has ended (time limit or completed). Start a new assessment.",
                "code": "session_ended",
            }
        ), 410
    var = json.loads(row[0] or "{}")
    if not (var or {}).get("assessment"):
        a = build_assessment_block(
            (var or {}).get("level") or DEFAULT_LEVEL, (var or {}).get("job_family") or DEFAULT_FAMILY
        )
        var = {**var, "assessment": a}

    likelihood, reason = gs.classify_ai_paste_likeness(user_text)
    flags: dict = {}
    if likelihood >= 0.6:
        flags = {"suspected_generic_ai": True, "likelihood": round(likelihood, 2), "reason": reason}
        ctx = (
            "The user's last reply *may* have been generic. Do not accuse. In one short question, ask for **one concrete example** (a real trade-off, a moment, who was in the room) — **not** a compliance lecture, **not** a request for team-level audit criteria. (Signal: {reason})"
        )
    else:
        ctx = "No special flag on this turn."

    insert_message(session_id, "user", user_text, flags if flags else None)
    all_m = list_messages(session_id)
    if not all_m or all_m[-1]["role"] != "user":
        return jsonify({"error": "State error"}), 500
    hist = [{"role": m["role"], "content": m["content"]} for m in all_m[:-1]]

    try:
        reply = gs.run_interviewer_reply(
            rag,
            var,
            hist,
            user_text,
            ctx,
        )
    except Exception as e:
        err = str(e)
        code = 503 if "429" in err or "ResourceExhausted" in type(e).__name__ or "quota" in err.lower() else 502
        return jsonify({"error": err[:500]}), code
    if not (reply and reply.strip()):
        return jsonify({"error": "Empty model response"}), 502
    reply, dimension_shift = gs.parse_dimension_banner(reply)
    reply, session_suggests_complete = gs.strip_session_complete_flag(reply)
    if not (reply and reply.strip()):
        return jsonify({"error": "Empty model response"}), 502
    insert_message(session_id, "model", reply)
    if dimension_shift and dimension_shift.get("code"):
        insert_event(
            session_id,
            "dim_shift",
            {
                "code": str(dimension_shift.get("code")),
                "label": (dimension_shift.get("label") or "")[:120],
            },
        )
    st = session_stats(session_id)
    return jsonify(
        {
            "reply": reply,
            "session_suggests_complete": bool(session_suggests_complete),
            "dimension_shift": dimension_shift,
            "session_id": session_id,
            "model_flags": flags,
            "stats": st,
        }
    )


def _session_readiness_payload(session_id: str) -> dict:
    st = session_stats(session_id)
    if not st.get("session_id"):
        return {}
    codes = get_dimension_shift_codes(session_id)
    n = len(codes)
    all_c = [d[0] for d in DIMENSION_ORDER]
    missing = [c for c in all_c if c not in set(codes)]
    elapsed = float(st.get("duration_sec") or 0.0)
    u = int(st.get("user_messages") or 0)
    target = int(TARGET_DURATION_SEC)
    guide_remaining = max(0, target - elapsed)
    by_code = {c: label for c, label in DIMENSION_ORDER}
    # ~1 min per not-yet-signalled focus area, capped (rough UX hint, not a promise)
    approx_extra = min(target, max(0, (6 - n) * 60))
    dim_pct = round(100.0 * n / 6.0, 1)
    if n >= 6:
        w_level = "none"
    elif n < 4:
        w_level = "strong"
    else:
        w_level = "soft"
    return {
        "session_id": session_id,
        "dimension_codes_touched": codes,
        "dimensions_touched": n,
        "dimensions_total": 6,
        "dimension_breadth_percent": dim_pct,
        "dimension_labels": {c: by_code[c] for c in all_c},
        "dimensions_missing": [
            {"code": c, "label": by_code.get(c, c)} for c in missing
        ],
        "user_turns": u,
        "elapsed_sec": round(elapsed, 1),
        "target_sec": target,
        "guide_time_remaining_sec": round(guide_remaining, 0),
        "approx_time_for_remaining_angles_sec": round(approx_extra, 0),
        "has_coverage_signal": n > 0,
        "warning_level": w_level,
        "breadth_incomplete": n < 6,
        "topic_label_note": (
            "The “/6” count is how many times a new topic label appeared in this chat, "
            "not a checklist the interviewer must finish. You can end anytime; the summary still reflects the transcript."
        ),
    }


@app.route("/api/session/<session_id>/readiness", methods=["GET"])
def session_readiness(session_id: str):
    init_db()
    _expire_stale_sessions()
    with get_conn() as c:
        row = c.execute("SELECT id FROM sessions WHERE id = ?", (session_id,)).fetchone()
    if not row:
        return jsonify({"error": "not found"}), 404
    payload = _session_readiness_payload(session_id)
    if not payload:
        return jsonify({"error": "not found"}), 404
    return jsonify(payload)


@app.route("/api/session/<session_id>/complete", methods=["POST"])
def complete(session_id: str):
    init_db()
    _expire_stale_sessions()
    msgs = list_messages(session_id)
    with get_conn() as c:
        row = c.execute(
            "SELECT variation_json FROM sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
    if not row:
        return jsonify({"error": "not found"}), 404
    var = json.loads(row[0] or "{}")
    mlist = [{"role": m["role"], "content": m["content"]} for m in msgs]
    try:
        scores = gs.score_transcript(mlist, var)
    except Exception as e:
        msg = (str(e) or "Scoring failed")[:500]
        user_msg = (
            "We couldn’t finish scoring that run. Tap “View results” to try again. "
            "If it happens again, wait a few seconds and retry, or use a local Ollama model for this step."
        )
        if "could not read as json" in msg.lower() or "jsondecode" in type(e).__name__.lower():
            user_msg = (
                "The scoring step returned data we could not read. Please tap “View results” again. "
                "If the problem repeats, try again in a few minutes."
            )
        return jsonify({"error": user_msg, "detail": msg}), 500
    st_done = session_stats(session_id)
    n_dims = len(get_dimension_shift_codes(session_id))
    insert_event(
        session_id,
        "aiq_scoring_ok",
        {
            "user_turns": st_done.get("user_messages"),
            "topic_labels_touched": n_dims,
        },
    )
    end_session(session_id, scores=scores)
    ass = (var or {}).get("assessment")
    if ass and isinstance(ass, dict) and "typical_composite" not in ass and ass.get("level"):
        from assessment_profiles import typical_composite_for_level

        ass = {**ass, "typical_composite": typical_composite_for_level(str(ass.get("level")))}
    return jsonify(
        {
            "scores": scores,
            "session_id": session_id,
            "assessment": ass,
        }
    )


@app.route("/api/session/<session_id>/report.pdf", methods=["GET"])
def session_report_pdf(session_id: str):
    """One-page summary PDF; requires a completed run with stored scores."""
    init_db()
    _expire_stale_sessions()
    with get_conn() as c:
        row = c.execute(
            "SELECT last_scores_json, variation_json FROM sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
    if not row or not row["last_scores_json"]:
        return jsonify(
            {"error": "No report for this session yet. Complete the session first."}
        ), 404
    scores = json.loads(row["last_scores_json"])
    var = json.loads((row["variation_json"] or "{}") or "{}")
    ass = (var or {}).get("assessment")
    from session_report_pdf import build_session_report_pdf_bytes

    try:
        data = build_session_report_pdf_bytes(scores, ass)
    except Exception as e:
        return jsonify({"error": f"Could not build PDF: {e!s}"}), 500
    short = (session_id or "").replace("-", "")[:8] or "session"
    return Response(
        data,
        mimetype="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="AiQ-snapshot-{short}.pdf"',
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        },
    )


def _iso(ts: Optional[float]) -> Optional[str]:
    if ts is None:
        return None
    try:
        return datetime.fromtimestamp(float(ts), tz=timezone.utc).isoformat()
    except Exception:
        return None


def _percentile(vals: List[float], p: float) -> Optional[float]:
    if not vals:
        return None
    a = sorted(float(x) for x in vals)
    if len(a) == 1:
        return round(a[0], 3)
    k = (len(a) - 1) * p
    f = int(k)
    c = min(len(a) - 1, f + 1)
    if f == c:
        return round(a[f], 3)
    d = k - f
    return round(a[f] + (a[c] - a[f]) * d, 3)


def _format_duration_words(total_sec: float) -> str:
    s = max(0, int(round(float(total_sec or 0.0))))
    m, r = divmod(s, 60)
    h, m = divmod(m, 60)
    parts: List[str] = []
    if h:
        parts.append(f"{h} hour{'s' if h != 1 else ''}")
    if m:
        parts.append(f"{m} minute{'s' if m != 1 else ''}")
    if r or not parts:
        parts.append(f"{r} second{'s' if r != 1 else ''}")
    return " ".join(parts)


def _format_duration_words_from_seconds(sec: Optional[float]) -> Optional[str]:
    if sec is None:
        return None
    try:
        return _format_duration_words(float(sec))
    except Exception:
        return None


_TOOL_HINTS = [
    "chatgpt",
    "copilot",
    "claude",
    "gemini",
    "perplexity",
    "cursor",
    "notion ai",
    "openai",
    "llm",
    "prompt",
    "ai assistant",
]
_RISK_HINTS = ["risk", "privacy", "pii", "compliance", "policy", "guardrail", "ip", "security"]
_EVIDENCE_HINTS = ["because", "for example", "we built", "we changed", "we decided", "impact", "metric", "kpi"]

# Each row may set `audiences`: a list of job_family slugs from assessment_profiles, or ["*"] for any.
# `weight` is a tie-break: lower = prefer when the gap to target is large (more foundational / urgent).
_COURSE_CATALOG: Dict[str, List[dict]] = {
    "D1": [
        {
            "title": "AI for Everyone (Andrew Ng)",
            "provider": "Coursera",
            "url": "https://www.coursera.org/learn/ai-for-everyone",
            "why": "Framing where AI helps; good general anchor when the gap is about awareness of options.",
            "audiences": ["*"],
            "weight": 1,
        },
        {
            "title": "Introduction to generative AI (Microsoft)",
            "provider": "Microsoft Learn",
            "url": "https://learn.microsoft.com/en-us/training/paths/introduction-generative-artificial-intelligence/",
            "why": "Fits people-facing and ops leaders who use Microsoft 365; fast orientation for big D1 gaps.",
            "audiences": ["hr_people", "care_operations", "go_to_market", "general_management", "finance", "other"],
            "weight": 2,
        },
        {
            "title": "Generative AI learning path (Google Cloud)",
            "provider": "Google",
            "url": "https://www.cloudskillsboost.google/paths/183",
            "why": "Strong when product or data roles need a portfolio-style map of use cases, not a generic slide deck.",
            "audiences": ["product_engineering", "finance"],
            "weight": 3,
        },
    ],
    "D2": [
        {
            "title": "Generative AI: prompt engineering for everyone (IBM)",
            "provider": "Coursera / IBM",
            "url": "https://www.coursera.org/learn/generative-ai-prompt-engineering-for-everyone",
            "why": "Default for HR, GTM, care, and generalist roles: structured prompts without programming.",
            "audiences": ["hr_people", "care_operations", "go_to_market", "general_management", "risk_legal", "other"],
            "weight": 1,
        },
        {
            "title": "What is Microsoft Copilot?",
            "provider": "Microsoft Learn",
            "url": "https://learn.microsoft.com/en-us/training/modules/introduction-microsoft-365-copilot",
            "why": "Ties D2 to tools people already pay for; best when answers were thin on *which* app they use in anger.",
            "audiences": ["*"],
            "weight": 2,
        },
        {
            "title": "OpenAI prompt engineering guide",
            "provider": "OpenAI",
            "url": "https://platform.openai.com/docs/guides/prompt-engineering",
            "why": "Dense reference: structure, eval; fits roles that already use ChatGPT/ API-style workflows.",
            "audiences": ["*"],
            "weight": 3,
        },
        {
            "title": "ChatGPT Prompt Engineering for Developers",
            "provider": "DeepLearning.AI",
            "url": "https://learn.deeplearning.ai/courses/chatgpt-prompt-eng",
            "why": "Only for product/eng when D2 is weak and the job ships software or data products.",
            "audiences": ["product_engineering"],
            "weight": 1,
        },
    ],
    "D3": [
        {
            "title": "Think Again I: How to Reason and Argue (Duke)",
            "provider": "Coursera",
            "url": "https://www.coursera.org/learn/think-again-1",
            "why": "Universal habit for critiquing model text; good for legal, people, and strategy roles.",
            "audiences": ["*"],
            "weight": 1,
        },
        {
            "title": "Introduction to data basics for decision-making",
            "provider": "Microsoft Learn",
            "url": "https://learn.microsoft.com/en-us/training/paths/introduction-to-data-basics/",
            "why": "Pushes evidence habits for finance, product, and ops; pairs with D3 when answers lacked numbers.",
            "audiences": ["product_engineering", "finance", "go_to_market", "care_operations", "general_management"],
            "weight": 2,
        },
    ],
    "D4": [
        {
            "title": "Business process management basics",
            "provider": "Coursera / University of Haifa",
            "url": "https://www.coursera.org/learn/bpm",
            "why": "Map request → handoff → owner: core for people, care, and GTM with messy routing.",
            "audiences": ["*"],
            "weight": 1,
        },
        {
            "title": "Agile foundations",
            "provider": "Atlassian (free)",
            "url": "https://www.atlassian.com/agile",
            "why": "Lightweight when product/eng D4 issues are more iteration cadence than a formal BPM tool.",
            "audiences": ["product_engineering", "go_to_market"],
            "weight": 2,
        },
    ],
    "D5": [
        {
            "title": "Generative AI in the enterprise (writing & tone)",
            "provider": "Microsoft Learn (Copilot content)",
            "url": "https://adoption.microsoft.com/en-us/copilot/",
            "why": "Exec and customer comms: scenario prompts, tone control — fits GTM, people, and generalists.",
            "audiences": ["go_to_market", "hr_people", "general_management", "other"],
            "weight": 1,
        },
        {
            "title": "Write with AI (editing in English; adapt to your language policy)",
            "provider": "Coursera / Macquarie",
            "url": "https://www.coursera.org/learn/englishforcareerdevelopment",
            "why": "Drafts that others read: structure and edit when D5 is weak on “good enough to ship.”",
            "audiences": ["*"],
            "weight": 2,
        },
    ],
    "D6": [
        {
            "title": "Responsible AI: applying principles (Google Cloud)",
            "provider": "Coursera / Google",
            "url": "https://www.coursera.org/learn/responsible-ai-applying-ai-principles-with-google-cloud",
            "why": "Governance framing: legal, people, and risk families often need this when D6 is a large gap.",
            "audiences": ["risk_legal", "hr_people", "finance", "care_operations", "general_management"],
            "weight": 1,
        },
        {
            "title": "Data privacy and protection fundamentals",
            "provider": "Microsoft",
            "url": "https://learn.microsoft.com/en-us/training/paths/secure-azure-data-services/",
            "why": "Data-classification and “do not model” when security/privacy and eng stacks lean Microsoft.",
            "audiences": ["*"],
            "weight": 2,
        },
    ],
}

_TOPIC_FALLBACK = [
    {
        "dimension": "D1",
        "title": "Opportunity framing workshop",
        "kind": "topic",
        "why": "Practice translating AI initiatives into measurable business outcomes for your role.",
    },
    {
        "dimension": "D2",
        "title": "Prompt library sprint",
        "kind": "topic",
        "why": "Build 10 reusable prompt templates for recurring decisions in your workflow.",
    },
    {
        "dimension": "D3",
        "title": "Output review rubric",
        "kind": "topic",
        "why": "Define a lightweight checklist for accuracy, completeness, and escalation triggers.",
    },
    {
        "dimension": "D4",
        "title": "Workflow mapping session",
        "kind": "topic",
        "why": "Document where AI sits in your team’s operating cadence and who owns each step.",
    },
    {
        "dimension": "D5",
        "title": "Quality bar calibration",
        "kind": "topic",
        "why": "Align on what “good enough” looks like for AI-assisted deliverables your stakeholders read.",
    },
    {
        "dimension": "D6",
        "title": "Responsible-use tabletop",
        "kind": "topic",
        "why": "Run a 45-minute scenario drill on sensitive data, vendor access, and escalation paths.",
    },
]


def _count_matches(text: str, hints: List[str]) -> int:
    low = text.lower()
    n = 0
    for h in hints:
        if h in low:
            n += 1
    return n


def _analyze_user_response(text: str, flags: Optional[dict] = None) -> Dict[str, Any]:
    low = text.lower()
    words = [w for w in text.strip().split() if w]
    w = len(words)
    specificity = min(10.0, round((w / 14.0) + (0.8 if any(ch.isdigit() for ch in text) else 0.0), 2))
    tool_sig = min(10.0, round(_count_matches(low, _TOOL_HINTS) * 2.2, 2))
    risk_sig = min(10.0, round(_count_matches(low, _RISK_HINTS) * 2.0, 2))
    evidence_sig = min(10.0, round(_count_matches(low, _EVIDENCE_HINTS) * 1.8, 2))
    reflection_sig = min(
        10.0,
        round(
            (1.4 if "i" in low or "we" in low else 0.4)
            + (1.8 if "because" in low or "trade-off" in low else 0.0)
            + (1.6 if "learned" in low or "realized" in low else 0.0),
            2,
        ),
    )
    directness = min(10.0, round((10.0 if w > 0 else 0.0) - (1.5 if "don't make sense" in low else 0.0), 2))

    signals = []
    if tool_sig >= 4:
        signals.append("Mentions concrete AI tools/workflows.")
    if evidence_sig >= 4:
        signals.append("Provides cause/evidence framing.")
    if risk_sig >= 4:
        signals.append("Acknowledges governance/risk concerns.")
    if specificity >= 6:
        signals.append("Specific and reasonably concrete response.")
    gaps = []
    if tool_sig < 3:
        gaps.append("Tools still light here — if they have named several use cases, gently pivot to a different one they mentioned rather than re-drilling the same thread.")
    if evidence_sig < 3:
        gaps.append("Outcomes still broad — one soft ask for a real example; if the answer stays thin, switch topic to another area of their work.")
    if reflection_sig < 3:
        gaps.append("Reflection light — one open question on trade-offs; if they do not go deep, change angle (another tool/workflow) with no pressure.")
    if risk_sig < 2:
        gaps.append("Controls not explicit yet — one question on who sees what or what never goes in the model; keep it optional, not ‘compliance test’ tone.")

    # One optional, turn-specific line (only when “Strengths” bullets would be empty on their own for this angle).
    style_callout: Optional[str] = None
    if not signals and tool_sig < 2.5:
        style_callout = "No tool names this turn — ask for one product or surface; if they already gave several shallow examples, move to a different one they named."
    elif not signals and evidence_sig < 2.5:
        style_callout = "Still high-level — one gentle nudge for a real moment; if they are brief again, switch to a new angle (different task or tool) without pushing."
    elif not signals and w < 22:
        style_callout = "Short answer — invite one more detail; if that still feels light, switch gears to another part of their AI use."

    return {
        "word_count": w,
        "flags": flags or {},
        "scores": {
            "specificity": specificity,
            "tool_specificity": tool_sig,
            "risk_awareness": risk_sig,
            "evidence_strength": evidence_sig,
            "reflection_depth": reflection_sig,
            "directness": directness,
        },
        "signals": signals,
        "gaps": gaps,
        "style_callout": style_callout,
        "next_probe": (
            "They may have more than one AI use case: if this thread stays surface-level after one rephrase, thank them, pivot to another use case or tool they mentioned, or a fresh angle — do not interrogate the same line."
            if gaps
            else "Broaden: another workflow or tool, or a leadership / handoff angle so the chat stays easy, not a drill."
        ),
    }


def _ai_likelihood_from_text(text: str) -> float:
    """
    Lightweight 0–100 heuristic (not a classifier model). Complements optional paste flags.
    """
    t = (text or "").strip()
    if not t:
        return 0.0
    low = t.lower()
    score = 0.0
    if len(t) > 900:
        score += 12
    if low.count("\n\n") >= 3:
        score += 10
    boiler = (
        "furthermore",
        "in conclusion",
        "in summary",
        "it is important to note",
        "as an ai",
        "i cannot",
        "best practices",
        "leverage",
        "synergy",
        "holistic",
    )
    score += min(35.0, sum(6 for b in boiler if b in low))
    if t.count("—") + t.count("–") >= 3:
        score += 6
    if re.search(r"\b\d{1,2}\.\s", t):
        score += 5
    return float(max(0.0, min(100.0, round(score, 1))))


def _evaluation_payload(analysis: Dict[str, Any], ai_like: float) -> Dict[str, Any]:
    """Structured evaluation for the admin table (readability) — not a block of one paragraph."""
    out: Dict[str, Any] = {
        "strengths": list(analysis.get("signals") or []),
        "coaching_angles": list(analysis.get("gaps") or []),
        "next_step": str(analysis.get("next_probe") or "").strip(),
        "ai_likelihood": {
            "score_0_100": float(ai_like),
            "note": "Heuristic 0–100 for paste-like phrasing; not proof of who wrote the text.",
        },
    }
    if analysis.get("style_callout"):
        out["style_callout"] = analysis["style_callout"]
    fl = (analysis.get("flags") or {}).get("suspected_generic_ai")
    if fl:
        out["client_flag"] = "This reply was also marked as possibly pasted or very generic; confirm with a concrete follow-up."
    return out


def _expected_dim_targets(level: str, assessment: Optional[dict]) -> Dict[str, float]:
    base = {
        "ic": 5.6,
        "people_manager": 6.1,
        "head_of": 6.6,
        "executive": 7.0,
    }.get((level or "head_of").strip(), 6.2)
    w = (assessment or {}).get("weights") or {}
    avg_w = (sum(float(w.get(k, 0.0)) for k, _ in DIMENSION_ORDER) / 6.0) if w else 0.1667
    out: Dict[str, float] = {}
    for code, _ in DIMENSION_ORDER:
        ww = float(w.get(code, avg_w)) if w else avg_w
        out[code] = round(max(4.5, min(8.8, base + (ww - avg_w) * 8.0)), 2)
    return out


def _user_mention_snippets(user_analyses: List[dict], n: int = 2) -> str:
    """Short hints from the transcript to ground recommendations in their words."""
    out: List[str] = []
    for a in user_analyses or []:
        c = (a.get("content") or "").strip()
        if len(c) < 15:
            continue
        t = c.replace("\n", " ")[:200]
        if t:
            out.append("…" + t + ("…" if len(c) > 200 else ""))
        if len(out) >= n:
            break
    return " ".join(out) if out else ""


def _coaching_to_summary_lines(rows: List[dict], limit: int = 12) -> List[str]:
    out: List[str] = []
    for r in rows or []:
        c = (r or {}).get("code") or ""
        f = (r or {}).get("focus") or ""
        if c and f:
            out.append(f"{c} — {f}"[:500])
        exs = (r or {}).get("exercises") or []
        if c and exs and len(out) < limit:
            out.append(f"{c} (try this week) — {exs[0]}"[:500])
        if len(out) >= limit:
            break
    return out


def _recommendations(scores: Dict[str, Any], assessment: Optional[dict], user_analyses: List[dict]) -> Dict[str, Any]:
    ass = assessment or {}
    level = str(ass.get("level") or "head_of")
    fam = ass.get("job_family_label") or str(ass.get("job_family") or "your role")
    if len(str(fam)) < 2:
        fam = "your role"
    targets = _expected_dim_targets(level, ass)
    gaps = []
    for code, label in DIMENSION_ORDER:
        block = scores.get(code) if isinstance(scores.get(code), dict) else {}
        actual = float(block.get("score") or 0.0)
        target = float(targets.get(code) or 6.0)
        gap = round(target - actual, 2)
        gaps.append({"code": code, "label": label, "actual": actual, "target": target, "gap": gap})
    gaps.sort(key=lambda x: x["gap"], reverse=True)
    top_gaps = gaps[:6]

    job_tech = is_technical_product_family(ass.get("job_family"))
    tool_avg = 0.0
    if user_analyses:
        tool_avg = sum(float(a.get("scores", {}).get("tool_specificity", 0.0)) for a in user_analyses) / len(
            user_analyses
        )
    snippets = _user_mention_snippets(user_analyses, 2)

    aiq: Optional[float] = None
    if scores.get("AiQ_0_100") is not None:
        aiq = float(scores.get("AiQ_0_100") or 0.0)


    g_by: Dict[str, dict] = {g["code"]: g for g in gaps}
    fam_key = str(ass.get("job_family") or "other")
    fam_cl = fam_cluster(fam_key)
    ranked = sorted([g for g in gaps if g["gap"] > 0.1], key=lambda x: -x["gap"])
    link_set = {g["code"] for g in ranked[:4]}

    coaching_by_dimension: List[dict] = []
    c_slot = 0
    for code, _lab in DIMENSION_ORDER:
        g = g_by[code]
        add_l = g["code"] in link_set and g.get("gap", 0) > 0.1
        if add_l:
            c_slot += 1
        coaching_by_dimension.append(
            build_coaching_dimension_row(
                _COURSE_CATALOG,
                g,
                str(fam),
                fam_key,
                fam_cl,
                add_l,
                c_slot if add_l else 0,
                job_tech,
            )
        )

    priority_next_steps = _coaching_to_summary_lines(coaching_by_dimension, limit=12)
    priority_actions: List[dict] = []
    tool_actions = [
        f"Reply signal: how often they named specific tools in their answers: avg {tool_avg:.1f} / 10 in this run (0 = almost none named)."
    ]
    if snippets:
        tool_actions.append("Transcript excerpt (from their answers in this run): " + snippets)

    learn_plan: List[Dict[str, Any]] = []
    seen_urls: set = set()
    for row in coaching_by_dimension:
        s = (row or {}).get("suggested_read")
        if not s or not s.get("url"):
            continue
        u = s.get("url")
        if u in seen_urls or len(learn_plan) >= 4:
            continue
        seen_urls.add(u)
        g = g_by.get(row.get("code") or "")
        learn_plan.append(
            {
                "kind": "course",
                "dimension": row.get("code"),
                "gap": (g or {}).get("gap"),
                "title": s.get("title"),
                "provider": s.get("provider"),
                "url": u,
                "why": (s.get("why") or "")
                + f" (Picked for {row.get('code')}, {fam} profile, and gap. One applied 30–45 min task, then file prompt + output.)",
            }
        )
    if not learn_plan and ranked:
        g0 = ranked[0]
        pc = pick_one_course(
            _COURSE_CATALOG, g0["code"], fam_key, job_tech, g0.get("gap", 0) or 0, 0
        )
        if pc and pc.get("url"):
            learn_plan.append(
                {
                    "kind": "course",
                    "dimension": g0["code"],
                    "gap": g0["gap"],
                    "title": pc["title"],
                    "provider": pc.get("provider"),
                    "url": pc["url"],
                    "why": (pc.get("why") or "") + f" (Largest gap for {fam}.)",
                }
            )
    if not learn_plan:
        t0 = _TOPIC_FALLBACK[0]
        learn_plan.append(
            {
                "kind": "topic",
                "dimension": t0["dimension"],
                "gap": None,
                "title": t0["title"],
                "provider": "Self-directed",
                "url": None,
                "why": t0["why"] + f" (No public course row matched; use this in place of an external link for {fam}.)",
            }
        )

    next_30 = [
        {
            "week": 1,
            "title": "Baseline + instrumentation",
            "objectives": [
                "Pick 3 recurring workflows you will standardize on (draft, analysis, review).",
                "Define success metrics per workflow (time, quality, risk incidents).",
            ],
            "deliverables": [
                "One-page workflow map per task (inputs, AI step, human review, outputs).",
                "A shared prompt template library (5 prompts minimum).",
            ],
            "cadence": ["Mon: map workflows", "Wed: pilot prompts", "Fri: review outputs with rubric"],
            "metrics": ["Baseline minutes per task", "Defect rate on AI-assisted outputs"],
        },
        {
            "week": 2,
            "title": "Quality system + ownership",
            "objectives": [
                "Install a lightweight review rubric for AI-assisted work others rely on.",
                "Assign explicit owners for escalation and redaction decisions.",
            ],
            "deliverables": [
                "Rubric v1 + examples of pass/fail",
                "Escalation matrix (who decides when model output is uncertain)",
            ],
            "cadence": ["Tue: rubric workshop", "Thu: red-team 10 outputs", "Fri: tighten prompts"],
            "metrics": ["Rubric pass rate", "Rework cycles"],
        },
        {
            "week": 3,
            "title": "Risk posture + vendor boundaries",
            "objectives": [
                "Document what must never enter a model, and what requires legal review.",
                "Clarify vendor/tool approval path for new AI surfaces.",
            ],
            "deliverables": [
                "Data classification cheat sheet for the team",
                "Vendor checklist (data residency, logging, retention)",
            ],
            "cadence": ["Mon: policy alignment", "Wed: tabletop scenarios", "Fri: publish guardrails"],
            "metrics": ["Policy exceptions count", "Training completion"],
        },
        {
            "week": 4,
            "title": "Measure impact + iterate",
            "objectives": [
                "Compare before/after on the 3 workflows from week 1.",
                "Decide what to scale vs. what to stop.",
            ],
            "deliverables": [
                "Impact report (quant + qualitative)",
                "Quarterly roadmap for next 90 days",
            ],
            "cadence": ["Mon: measure", "Wed: stakeholder review", "Fri: commit roadmap"],
            "metrics": ["Minutes saved", "Quality delta", "Incidents avoided"],
        },
    ]
    return {
        "context": {
            "level": ass.get("level_label") or level,
            "job_family": fam,
            "aiq_score": scores.get("AiQ_0_100"),
        },
        "dimension_gaps": top_gaps,
        "tool_actions": tool_actions,
        "priority_actions": priority_actions,
        "priority_next_steps": priority_next_steps,
        "coaching_by_dimension": coaching_by_dimension,
        "learning_plan": learn_plan,
        "next_30_days": next_30,
    }


def _build_session_telemetry(
    session_row, msgs: list, events: list, stats: dict, assessment: Optional[dict], scores: Dict[str, Any]
) -> dict:
    start_ts = session_row["started_at"] or session_row["created_at"] or 0.0
    end_ts = session_row["ended_at"] or (msgs[-1]["created_at"] if msgs else start_ts)
    duration = max(0.0, float(end_ts or 0.0) - float(start_ts or 0.0))
    proc_msgs = []
    turn_idx = 0
    generic_flags = 0
    for i, m in enumerate(msgs):
        role = str(m.get("role") or "")
        if role == "user":
            turn_idx += 1
        c = str(m.get("content") or "")
        words = len([w for w in c.strip().split() if w])
        chars = len(c)
        flags = m.get("flags") or {}
        if isinstance(flags, dict) and flags.get("suspected_generic_ai"):
            generic_flags += 1
        proc = {
            "idx": i + 1,
            "turn_idx": turn_idx if role in ("user", "model", "assistant", "ai") else None,
            "role": role,
            "created_at": m.get("created_at"),
            "created_at_iso": _iso(m.get("created_at")),
            "offset_sec": round(max(0.0, float(m.get("created_at") or 0.0) - float(start_ts or 0.0)), 3),
            "chars": chars,
            "words": words,
            "flags": flags if isinstance(flags, dict) else {},
            "content": c,
        }
        proc_msgs.append(proc)

    event_counts: Dict[str, int] = {}
    for e in events:
        et = str(e.get("type") or "unknown")
        event_counts[et] = event_counts.get(et, 0) + 1
    tab_blur = int(stats.get("tab_blur_count") or event_counts.get("tab_blur", 0) or 0)
    tab_focus = int(event_counts.get("tab_focus", 0) or 0)
    dim_shift_ct = int(event_counts.get("dim_shift", 0) or 0)
    window_blur = int(event_counts.get("window_blur", 0) or 0)
    # tab_blur_count (session_stats) = tab Blur + window Blur, so one source for "left" signal
    left_context_during_assessment = int(stats.get("tab_blur_count") or 0) > 0
    signals_in_this_session = ", ".join(
        f"{k} ({v})" for k, v in sorted(event_counts.items(), key=lambda x: (-x[1], x[0])) if v > 0
    )

    focus_away_log: List[Dict[str, Any]] = []
    for e in events:
        et = str(e.get("type") or "")
        if et in ("tab_blur", "tab_focus", "window_blur"):
            p = e.get("payload") or {}
            if not isinstance(p, dict):
                p = {}
            focus_away_log.append(
                {
                    "type": et,
                    "at": e.get("created_at"),
                    "at_iso": _iso(e.get("created_at")) if e.get("created_at") else None,
                    "page_title": p.get("page_title"),
                    "url_path": p.get("page_url") or p.get("path"),
                    "visibility": p.get("visibility"),
                    "detail_note": p.get("note"),
                }
            )
    if len(focus_away_log) > 60:
        focus_away_log = focus_away_log[-60:]

    dim_events = [e for e in events if e.get("type") == "dim_shift"]
    dim_labels = []
    seen_codes = set()
    for d in dim_events:
        payload = d.get("payload") or {}
        c = str(payload.get("code") or "")
        if c and c not in seen_codes:
            seen_codes.add(c)
            dim_labels.append({"code": c, "label": payload.get("label") or c})

    last_interviewer_text = ""
    last_interviewer_ts: Optional[float] = None
    compose_durations: List[float] = []
    interaction_rows: List[Dict[str, Any]] = []
    user_turn_for_analysis: List[Dict[str, Any]] = []

    for pm in proc_msgs:
        role = str(pm.get("role") or "")
        if role in ("model", "assistant", "ai"):
            last_interviewer_text = str(pm.get("content") or "")
            last_interviewer_ts = float(pm.get("created_at") or 0.0)
            continue
        if role != "user":
            continue
        content_u = str(pm.get("content") or "")
        flags_u = pm.get("flags") if isinstance(pm.get("flags"), dict) else {}
        ua = _analyze_user_response(content_u, flags_u)
        user_ts = float(pm.get("created_at") or 0.0)
        compose_sec: Optional[float] = None
        if last_interviewer_ts:
            compose_sec = max(0.0, user_ts - last_interviewer_ts)
            compose_durations.append(compose_sec)
        ai_like = _ai_likelihood_from_text(content_u)
        if isinstance(flags_u, dict) and flags_u.get("suspected_generic_ai"):
            ai_like = float(max(ai_like, 72.0))
        ev_payload = _evaluation_payload(ua, ai_like)
        row = {
            "turn_idx": pm.get("turn_idx"),
            "interviewer_question": last_interviewer_text,
            "user_response": content_u,
            "evaluation": ev_payload,
            "compose_sec": round(compose_sec, 3) if compose_sec is not None else None,
            "compose_duration_human": _format_duration_words_from_seconds(compose_sec),
            "ai_likelihood_0_100": ai_like,
            "analysis": ua,
        }
        interaction_rows.append(row)
        user_turn_for_analysis.append(
            {
                "idx": pm.get("idx"),
                "turn_idx": pm.get("turn_idx"),
                "offset_sec": pm.get("offset_sec"),
                "analysis": ua,
                "content": content_u,
            }
        )

    avg_compose = round(sum(compose_durations) / len(compose_durations), 3) if compose_durations else None
    ai_vals = [float(r.get("ai_likelihood_0_100") or 0.0) for r in interaction_rows]
    session_ai_like = round(sum(ai_vals) / len(ai_vals), 1) if ai_vals else None

    expected_targets = _expected_dim_targets(str((assessment or {}).get("level") or "head_of"), assessment)
    dim_comparison = []
    for code, label in DIMENSION_ORDER:
        block = scores.get(code) if isinstance(scores.get(code), dict) else {}
        actual = float(block.get("score") or 0.0)
        target = float(expected_targets.get(code) or 6.0)
        dim_comparison.append(
            {
                "code": code,
                "label": label,
                "actual": actual,
                "target": target,
                "delta_vs_target": round(actual - target, 2),
            }
        )

    telemetry = {
        "kpis": {
            "duration_sec": round(duration, 3),
            "duration_human": _format_duration_words(duration),
            "message_total": len(proc_msgs),
            "user_messages": int(stats.get("user_messages") or 0),
            "model_messages": int(stats.get("model_messages") or 0),
            "behavior_events_total": len(events),
            "behavior_events_by_type": event_counts,
            "behavior_events_caption": (
                "Counts anonymized client signals recorded during the run "
                "(for example tab visibility changes, window blur, and guide navigation events)."
            ),
            "tab_blur_count": tab_blur,
            "tab_focus_count": tab_focus,
            "left_assessment_context": left_context_during_assessment,
            "left_context_note": (
                "Yes = at least one time this page lost focus (tab or window blur). We **cannot** read the title/URL of other sites’ tabs (browser privacy) — the log only shows *this* assessment page and visibility state. "
                "It usually means another tab, app, or window. Not a full-screen recording."
                if left_context_during_assessment
                else "No focus-away events in this run."
            ),
            "focus_away_log": focus_away_log,
            "session_signal_summary": signals_in_this_session,
            "client_event_types_legend": [
                {
                    "type": "tab_blur",
                    "meaning": "The assessment page was hidden (e.g. other tab, minimize) — we only know *this* page, not the destination tab.",
                },
                {
                    "type": "window_blur",
                    "meaning": "The browser window lost focus (another app, or another window). Still no access to *which* other tab in that window (browser policy).",
                },
                {
                    "type": "tab_focus",
                    "meaning": "User returned to the page / page became visible again.",
                },
                {
                    "type": "dim_shift",
                    "meaning": "Interviewer advanced to another AiQ topic label (emitted with the next model turn).",
                },
                {
                    "type": "aiq_scoring_ok",
                    "meaning": "Scoring step completed; payload records rough coverage stats.",
                },
                {
                    "type": "beacon / other",
                    "meaning": "Client heartbeat or custom event sent to /api/session/.../event.",
                },
            ],
            "tab_blur_definition": (
                "“Blur events” = count of tab_blur: each time the tab/window was left or the page became hidden, "
                "as reported by the browser. Same event stream can reflect switching apps or opening another window."
            ),
            "generic_ai_flagged_user_messages": generic_flags,
            "avg_compose_sec_per_user_message": avg_compose,
            "avg_compose_human_per_user_message": _format_duration_words_from_seconds(avg_compose),
            "session_ai_likelihood_0_100": session_ai_like,
            "dimension_shifts": dim_shift_ct,
            "dimensions_touched": dim_labels,
        },
        "messages": proc_msgs,
        "events_summary": {
            "total": len(events),
            "by_type": event_counts,
        },
        "interaction_turns": interaction_rows,
        "response_analysis": user_turn_for_analysis,
        "charts": {
            "compose_time_by_turn": [
                {
                    "turn_idx": int(r.get("turn_idx") or 0),
                    "compose_sec": float(r.get("compose_sec") or 0.0),
                }
                for r in interaction_rows
                if r.get("compose_sec") is not None
            ],
            "user_signal_by_turn": [
                {
                    "turn_idx": int(u.get("turn_idx") or 0),
                    **(u.get("analysis", {}).get("scores") or {}),
                }
                for u in user_turn_for_analysis
            ],
            "dimension_score_vs_target": dim_comparison,
        },
        "actionable_insights": _recommendations(scores, assessment, user_turn_for_analysis),
    }
    return telemetry


@app.route("/api/admin/sessions", methods=["GET"])
def admin_sessions():
    init_db()
    _expire_stale_sessions()
    if not _admin_ok():
        return jsonify(
            {
                "error": "unauthorized",
                "hint": (
                    "The admin password is only the value on the right of AIQ_ADMIN_SECRET= in aiq_csuite/.env — "
                    "not the name AIQ_ADMIN_SECRET, and no 'export' keyword. If the line is still the "
                    "placeholder from .env.example (replace_with_long_random), the token is exactly that. "
                    "After editing .env, restart the Flask app, then try again."
                ),
            }
        ), 401
    with get_conn() as c:
        rows = c.execute(
            "SELECT id, created_at, ended_at, last_scores_json, user_agent, completed, variation_json FROM sessions ORDER BY created_at DESC LIMIT 200"
        ).fetchall()
    out = []
    for r in rows:
        s = session_stats(r["id"])
        out.append(
            {
                "id": r["id"],
                "created_at": r["created_at"],
                "created_at_iso": _iso(r["created_at"]),
                "ended_at": r["ended_at"],
                "ended_at_iso": _iso(r["ended_at"]),
                "completed": r["completed"],
                "user_agent": r["user_agent"],
                "last_scores": json.loads(r["last_scores_json"])
                if r["last_scores_json"]
                else None,
                "assessment": (json.loads(r["variation_json"] or "{}") or {}).get("assessment"),
                "stats": s,
            }
        )
    return jsonify({"sessions": out})


@app.route("/api/admin/sessions/<session_id>", methods=["GET"])
def admin_one(session_id: str):
    init_db()
    _expire_stale_sessions()
    if not _admin_ok():
        return (
            jsonify(
                {
                    "error": "unauthorized",
                    "hint": (
                        "Use only the value after AIQ_ADMIN_SECRET= in aiq_csuite/.env; restart the app after you change it."
                    ),
                }
            ),
            401,
        )
    import json as jsm
    with get_conn() as c:
        s = c.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    if not s:
        return jsonify({"error": "not found"}), 404
    msgs = list_messages(session_id)
    with get_conn() as c:
        evs = c.execute(
            "SELECT * FROM events WHERE session_id = ? ORDER BY created_at",
            (session_id,),
        ).fetchall()
    events = [
        {
            "type": e["type"],
            "created_at": e["created_at"],
            "created_at_iso": _iso(e["created_at"]),
            "payload": jsm.loads(e["payload_json"]) if e["payload_json"] else {},
        }
        for e in evs
    ]
    st = session_stats(session_id)
    variation = json.loads(s["variation_json"] or "{}") if s["variation_json"] else {}
    assessment = (variation or {}).get("assessment") or {}
    scores = json.loads(s["last_scores_json"] or "{}") if s["last_scores_json"] else {}
    telemetry = _build_session_telemetry(s, msgs, events, st, assessment, scores)
    return jsonify(
        {
            "session": {k: s[k] for k in s.keys()},
            "stats": st,
            "assessment": assessment,
            "scores": scores,
            "telemetry": telemetry,
        }
    )


@app.route("/api/admin/sessions/<session_id>", methods=["DELETE"])
def admin_delete_session(session_id: str):
    init_db()
    if not _admin_ok():
        return jsonify({"error": "unauthorized"}), 401
    if delete_session(session_id):
        return jsonify({"ok": True})
    return jsonify({"error": "not found"}), 404


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5020)), debug=True)
