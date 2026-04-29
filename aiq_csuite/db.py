import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import DB_PATH, ensure_instance


def get_conn() -> sqlite3.Connection:
    ensure_instance()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    ensure_instance()
    with get_conn() as c:
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                created_at REAL NOT NULL,
                started_at REAL,
                ended_at REAL,
                target_role TEXT DEFAULT 'c_level',
                client_seed TEXT,
                variation_json TEXT,
                last_scores_json TEXT,
                completed INTEGER DEFAULT 0,
                user_agent TEXT,
                client_meta_json TEXT
            );
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at REAL NOT NULL,
                flags_json TEXT,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            );
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                type TEXT NOT NULL,
                payload_json TEXT,
                created_at REAL NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            );
            CREATE INDEX IF NOT EXISTS idx_msg_sess ON messages(session_id);
            CREATE INDEX IF NOT EXISTS idx_ev_sess ON events(session_id);
            """
        )


def new_session(
    user_agent: str,
    client_meta: Optional[dict],
    variation: dict,
    target_role: Optional[str] = None,
) -> str:
    sid = str(uuid.uuid4())
    now = time.time()
    tr = target_role if (target_role and str(target_role).strip()) else "all_levels"
    with get_conn() as c:
        c.execute(
            """INSERT INTO sessions (id, created_at, started_at, user_agent, client_meta_json, variation_json, target_role)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                sid,
                now,
                now,
                user_agent or "",
                json.dumps(client_meta or {}),
                json.dumps(variation),
                tr,
            ),
        )
    return sid


def insert_message(
    session_id: str, role: str, content: str, flags: Optional[dict] = None
) -> str:
    mid = str(uuid.uuid4())
    with get_conn() as c:
        c.execute(
            """INSERT INTO messages (id, session_id, role, content, created_at, flags_json)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (mid, session_id, role, content, time.time(), json.dumps(flags) if flags else None),
        )
    return mid


def list_messages(session_id: str) -> List[Dict[str, Any]]:
    with get_conn() as c:
        rows = c.execute(
            "SELECT id, role, content, created_at, flags_json FROM messages WHERE session_id = ? ORDER BY created_at",
            (session_id,),
        ).fetchall()
    out = []
    for r in rows:
        out.append(
            {
                "id": r["id"],
                "role": r["role"],
                "content": r["content"],
                "created_at": r["created_at"],
                "flags": json.loads(r["flags_json"]) if r["flags_json"] else None,
            }
        )
    return out


def get_dimension_shift_codes(session_id: str) -> List[str]:
    """First-seen order of unique dimension codes from dim_shift events."""
    with get_conn() as c:
        rows = c.execute(
            "SELECT payload_json FROM events WHERE session_id = ? AND type = 'dim_shift' ORDER BY created_at",
            (session_id,),
        ).fetchall()
    seen: set = set()
    out: List[str] = []
    for r in rows:
        p = json.loads(r[0] or "{}")
        code = p.get("code")
        if code and code not in seen:
            seen.add(code)
            out.append(code)
    return out


def insert_event(session_id: str, type_: str, payload: Optional[dict] = None):
    eid = str(uuid.uuid4())
    with get_conn() as c:
        c.execute(
            "INSERT INTO events (id, session_id, type, payload_json, created_at) VALUES (?, ?, ?, ?, ?)",
            (eid, session_id, type_, json.dumps(payload or {}), time.time()),
        )


def end_session(
    session_id: str, scores: Optional[dict] = None, last_scores: Optional[dict] = None
):
    with get_conn() as c:
        c.execute(
            "UPDATE sessions SET ended_at = ?, completed = 1, last_scores_json = ? WHERE id = ?",
            (time.time(), json.dumps(scores) if scores else (json.dumps(last_scores) if last_scores else None), session_id),
        )


def update_last_scores(session_id: str, scores: dict):
    with get_conn() as c:
        c.execute("UPDATE sessions SET last_scores_json = ? WHERE id = ?", (json.dumps(scores), session_id))


def session_stats(session_id: str) -> Dict[str, Any]:
    with get_conn() as c:
        s = c.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if not s:
            return {}
        msgs = c.execute("SELECT role FROM messages WHERE session_id = ?", (session_id,)).fetchall()
        blurs = c.execute(
            "SELECT COUNT(*) FROM events WHERE session_id = ? AND type IN ('tab_blur', 'window_blur')",
            (session_id,),
        ).fetchone()
    first = s["started_at"] or s["created_at"]
    end = s["ended_at"] or time.time()
    user_left = blurs[0] > 0 if blurs else False
    return {
        "session_id": session_id,
        "created_at": s["created_at"],
        "ended_at": s["ended_at"],
        "duration_sec": round(max(0, end - first), 1) if first else 0,
        "message_count": len(msgs),
        "user_messages": len([1 for m in msgs if m["role"] == "user"]),
        "model_messages": len(
            [1 for m in msgs if m["role"] in ("model", "assistant", "ai")]
        ),
        "tab_blur_count": int(blurs[0]) if blurs else 0,
        "user_switched_tab_yes_no": "Y" if user_left else "N",
        "variation": json.loads(s["variation_json"]) if s["variation_json"] else {},
        "last_scores": json.loads(s["last_scores_json"]) if s["last_scores_json"] else None,
        "user_agent": s["user_agent"],
        "client_meta": json.loads(s["client_meta_json"]) if s["client_meta_json"] else {},
    }


def expire_stale_open_sessions(max_age_sec: float) -> int:
    """
    Set ended_at and completed for sessions that are still 'open' but older than max_age_sec
    (from created_at). Preserves last_scores_json if any scoring was already stored.
    """
    now = time.time()
    with get_conn() as c:
        cur = c.execute(
            """
            UPDATE sessions
            SET ended_at = ?, completed = 1
            WHERE ended_at IS NULL AND (? - created_at) > ?
            """,
            (now, now, max_age_sec),
        )
        return int(cur.rowcount or 0)


def delete_session(session_id: str) -> bool:
    """Remove session and all messages/events. Returns False if id did not exist."""
    with get_conn() as c:
        row = c.execute("SELECT 1 FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if not row:
            return False
        c.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        c.execute("DELETE FROM events WHERE session_id = ?", (session_id,))
        c.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    return True


def list_sessions_for_admin(limit: int = 200) -> List[Dict[str, Any]]:
    with get_conn() as c:
        rows = c.execute(
            "SELECT id, created_at, ended_at, last_scores_json, user_agent, completed FROM sessions ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    out: List[Dict[str, Any]] = []
    for s in rows:
        stats = session_stats(s["id"])
        out.append(
            {
                "id": s["id"],
                "created_at": s["created_at"],
                "ended_at": s["ended_at"],
                "completed": s["completed"],
                "user_agent": s["user_agent"],
                "summary": stats,
            }
        )
    return out