import json
import sqlite3
import time
import uuid
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse, unquote

from config import DATABASE_URL, DB_BACKEND, DB_PATH, ensure_instance

try:
    import psycopg2
    from psycopg2.extras import DictCursor
except Exception:  # pragma: no cover - optional dependency locally
    psycopg2 = None  # type: ignore[assignment]
    DictCursor = None  # type: ignore[assignment]


class DBConn:
    """Lightweight compatibility wrapper for sqlite and postgres."""

    def __init__(self):
        ensure_instance()
        self.backend = DB_BACKEND
        if self.backend == "postgres":
            if not DATABASE_URL:
                raise RuntimeError("DB_BACKEND=postgres but DATABASE_URL is empty")
            if psycopg2 is None or DictCursor is None:
                raise RuntimeError(
                    "Postgres backend selected but psycopg2 is not installed. "
                    "Run: pip install psycopg2-binary"
                )
            self._conn = psycopg2.connect(DATABASE_URL, connect_timeout=10)
        else:
            self._conn = sqlite3.connect(DB_PATH)
            self._conn.row_factory = sqlite3.Row

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            self._conn.commit()
        else:
            self._conn.rollback()
        self._conn.close()

    def _sql(self, query: str) -> str:
        if self.backend == "postgres":
            return query.replace("?", "%s")
        return query

    def execute(self, query: str, params: Optional[tuple] = None):
        p = params or ()
        if self.backend == "postgres":
            cur = self._conn.cursor(cursor_factory=DictCursor)
            cur.execute(self._sql(query), p)
            return cur
        return self._conn.execute(query, p)

    def executescript(self, script: str):
        if self.backend == "postgres":
            cur = self._conn.cursor()
            for stmt in script.split(";"):
                q = stmt.strip()
                if q:
                    cur.execute(q)
            return cur
        return self._conn.executescript(script)


def get_conn() -> DBConn:
    return DBConn()


def _ensure_postgres_app_grants(c: DBConn) -> None:
    """Ensure the DATABASE_URL role can read/write AiQ tables (Supabase pooler user may not be owner)."""
    if c.backend != "postgres":
        return
    for tbl in ("sessions", "messages", "events"):
        try:
            c.execute(f"GRANT ALL PRIVILEGES ON TABLE {tbl} TO CURRENT_USER")
        except Exception:
            pass


def _harden_postgres_public_tables(c: DBConn) -> None:
    """
    Supabase exposes `public` via PostgREST (anon JWT + authenticated users).

    Enable RLS on AiQ tables with **no permissive policies** ⇒ default deny for
    roles subject to RLS. Table owners bypass RLS; non-owner app roles need GRANT.

    Revoke only from Supabase API roles (anon/authenticated), not PUBLIC — revoking
    PUBLIC can strip pooler login access when that role is not the table owner.
    """
    if c.backend != "postgres":
        return
    for tbl in ("sessions", "messages", "events"):
        try:
            c.execute(f"ALTER TABLE {tbl} ENABLE ROW LEVEL SECURITY")
        except Exception:
            pass
    for tbl in ("sessions", "messages", "events"):
        for role in ("anon", "authenticated"):
            try:
                c.execute(f"REVOKE ALL ON TABLE {tbl} FROM {role}")
            except Exception:
                pass
    _ensure_postgres_app_grants(c)


def _ensure_session_column(c: DBConn, column: str, ddl_type: str) -> None:
    """Idempotent ALTER TABLE ... ADD COLUMN for both backends.

    SQLite lacks `ADD COLUMN IF NOT EXISTS`, so we probe `PRAGMA table_info` first.
    Postgres uses its built-in idempotent form.
    """
    if c.backend == "postgres":
        try:
            c.execute(f"ALTER TABLE sessions ADD COLUMN IF NOT EXISTS {column} {ddl_type}")
        except Exception:
            pass
        return
    try:
        rows = c.execute("PRAGMA table_info(sessions)").fetchall()
        names = {str(r["name"]) for r in rows}
        if column not in names:
            c.execute(f"ALTER TABLE sessions ADD COLUMN {column} {ddl_type}")
    except Exception:
        pass


def init_db():
    ensure_instance()
    with get_conn() as c:
        if DB_BACKEND == "postgres":
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    created_at DOUBLE PRECISION NOT NULL,
                    started_at DOUBLE PRECISION,
                    ended_at DOUBLE PRECISION,
                    target_role TEXT DEFAULT 'c_level',
                    client_seed TEXT,
                    variation_json TEXT,
                    last_scores_json TEXT,
                    completed INTEGER DEFAULT 0,
                    user_agent TEXT,
                    client_meta_json TEXT,
                    participant_name TEXT
                )
                """
            )
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL REFERENCES sessions(id),
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at DOUBLE PRECISION NOT NULL,
                    flags_json TEXT
                )
                """
            )
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL REFERENCES sessions(id),
                    type TEXT NOT NULL,
                    payload_json TEXT,
                    created_at DOUBLE PRECISION NOT NULL
                )
                """
            )
            c.execute("CREATE INDEX IF NOT EXISTS idx_msg_sess ON messages(session_id)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_ev_sess ON events(session_id)")
            _harden_postgres_public_tables(c)
        else:
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
                    client_meta_json TEXT,
                    participant_name TEXT
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
        # Idempotent migrations for pre-existing DBs (older rows lack newer columns).
        _ensure_session_column(c, "participant_name", "TEXT")
        _ensure_session_column(c, "session_enrichment_json", "TEXT")
        if DB_BACKEND == "postgres":
            _ensure_postgres_app_grants(c)


def parse_database_url_meta(url: Optional[str] = None) -> Dict[str, Any]:
    """Safe summary of DATABASE_URL for /api/health/db (no password)."""
    raw = (url if url is not None else DATABASE_URL) or ""
    if not raw.strip():
        return {"configured": False}
    u = raw.strip()
    if u.startswith("postgres://"):
        u = "postgresql://" + u[len("postgres://") :]
    try:
        p = urlparse(u)
        user = unquote(p.username or "")
        host = p.hostname or ""
        ref = ""
        if user.startswith("postgres."):
            ref = user.split(".", 1)[1]
        elif host.startswith("db.") and host.endswith(".supabase.co"):
            ref = host[3 : -len(".supabase.co")]
        return {
            "configured": True,
            "mode": "direct"
            if host.startswith("db.") and user == "postgres"
            else ("pooler" if "pooler.supabase.com" in host else "postgres"),
            "host": host,
            "port": p.port,
            "user": user,
            "project_ref": ref or None,
            "database": (p.path or "").lstrip("/") or "postgres",
            "has_sslmode": "sslmode" in (p.query or "").lower(),
        }
    except Exception as ex:
        return {"configured": True, "parse_error": str(ex)[:120]}


def db_connectivity_hint(error: str, meta: Optional[Dict[str, Any]] = None) -> str:
    err = (error or "").lower()
    m = meta or parse_database_url_meta()
    if "tenant" in err and "not found" in err:
        ref = m.get("project_ref") or "YOUR_PROJECT_REF"
        return (
            "Supabase pooler rejected postgres.{ref} on {host}. Copy the URI from "
            "Supabase → Connect (do not guess aws-0 vs aws-1). For Render, prefer "
            "Direct connection: postgresql://postgres:PASSWORD@db.{ref}.supabase.co:5432/postgres"
            "?sslmode=require (set as DATABASE_URL or DATABASE_DIRECT_URL).".format(
                ref=ref, host=m.get("host") or "pooler host"
            )
        )
    if "password authentication failed" in err:
        return "Database password is wrong. Reset in Supabase → Database → Reset password, URL-encode special chars in DATABASE_URL."
    if "could not translate host" in err or "name or service not known" in err:
        return "DATABASE_URL host is invalid. Copy host exactly from Supabase Connect."
    if not m.get("configured"):
        return "DATABASE_URL is empty on this server; app is using SQLite or misconfigured env."
    return "Verify DATABASE_URL in Render matches Supabase Connect, then Manual Deploy."


def check_db_health() -> Dict[str, Any]:
    """Lightweight connectivity probe for /api/health/db (no admin token)."""
    conn = parse_database_url_meta()
    try:
        init_db()
        with get_conn() as c:
            row = c.execute("SELECT COUNT(*) AS session_count FROM sessions").fetchone()
        return {
            "ok": True,
            "backend": DB_BACKEND,
            "session_count": _count_from_row(row, 0),
            "connection": conn,
        }
    except Exception as e:
        err = str(e)[:400]
        return {
            "ok": False,
            "backend": DB_BACKEND,
            "error": err,
            "connection": conn,
            "hint": db_connectivity_hint(err, conn),
        }


def db_unavailable_payload() -> Dict[str, Any]:
    h = check_db_health()
    return {
        "error": "database_unavailable",
        "message": h.get("error") or "database connection failed",
        "hint": h.get("hint"),
        "connection": h.get("connection"),
    }


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


def get_phase_shift_codes(session_id: str) -> List[str]:
    """First-seen order of phase codes from phase_shift events."""
    with get_conn() as c:
        rows = c.execute(
            "SELECT payload_json FROM events WHERE session_id = ? AND type = 'phase_shift' ORDER BY created_at",
            (session_id,),
        ).fetchall()
    seen: set = set()
    out: List[str] = []
    for r in rows:
        p = json.loads(_row_get(r, "payload_json") or "{}")
        code = p.get("phase")
        if code and code not in seen:
            seen.add(code)
            out.append(code)
    return out


def update_session_variation(session_id: str, variation: dict):
    with get_conn() as c:
        c.execute(
            "UPDATE sessions SET variation_json = ? WHERE id = ?",
            (json.dumps(variation), session_id),
        )


def update_session_enrichment(session_id: str, enrichment: dict):
    with get_conn() as c:
        c.execute(
            "UPDATE sessions SET session_enrichment_json = ? WHERE id = ?",
            (json.dumps(enrichment), session_id),
        )


def get_session_enrichment(session_id: str) -> dict:
    with get_conn() as c:
        row = c.execute(
            "SELECT session_enrichment_json FROM sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
    if not row:
        return {}
    try:
        raw = row["session_enrichment_json"]
    except (KeyError, TypeError):
        raw = row[0] if row else None
    if not raw:
        return {}
    try:
        o = json.loads(raw)
        return o if isinstance(o, dict) else {}
    except (json.JSONDecodeError, TypeError):
        return {}


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
        p = json.loads(_row_get(r, "payload_json") or "{}")
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


def _row_get(row, key, default=None):
    """Tolerant accessor for sqlite Row and psycopg2 DictRow (name or index)."""
    if row is None:
        return default
    if isinstance(key, int):
        try:
            return row[key]
        except (KeyError, IndexError, TypeError):
            return default
    try:
        return row[key]
    except (KeyError, IndexError, TypeError):
        pass
    try:
        if hasattr(row, "keys"):
            kl = str(key).lower()
            for k in row.keys():
                if str(k).lower() == kl:
                    return row[k]
    except (KeyError, IndexError, TypeError, AttributeError):
        pass
    return default


def _count_from_row(row, default: int = 0) -> int:
    """COUNT(*) result row — sqlite uses index 0; postgres DictRow uses a column name."""
    if row is None:
        return default
    for key in ("blur_count", "session_count", "count", "COUNT(*)", "count_1"):
        v = _row_get(row, key, None)
        if v is not None:
            try:
                return int(v)
            except (TypeError, ValueError):
                pass
    try:
        return int(row[0])
    except (KeyError, IndexError, TypeError, ValueError):
        return default


def session_stats(session_id: str) -> Dict[str, Any]:
    with get_conn() as c:
        s = c.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if not s:
            return {}
        msgs = c.execute("SELECT role FROM messages WHERE session_id = ?", (session_id,)).fetchall()
        blurs = c.execute(
            "SELECT COUNT(*) AS blur_count FROM events WHERE session_id = ? AND type IN ('tab_blur', 'window_blur')",
            (session_id,),
        ).fetchone()
    blur_n = _count_from_row(blurs, 0)
    first = s["started_at"] or s["created_at"]
    end = s["ended_at"] or time.time()
    user_left = blur_n > 0
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
        "tab_blur_count": blur_n,
        "user_switched_tab_yes_no": "Y" if user_left else "N",
        "variation": json.loads(s["variation_json"]) if s["variation_json"] else {},
        "last_scores": json.loads(s["last_scores_json"]) if s["last_scores_json"] else None,
        "user_agent": s["user_agent"],
        "client_meta": json.loads(s["client_meta_json"]) if s["client_meta_json"] else {},
        "participant_name": _row_get(s, "participant_name") or "",
    }


def set_session_participant_name(session_id: str, name: Optional[str]) -> bool:
    """Set/clear the admin-only participant name. Returns False if id did not exist."""
    cleaned = (name or "").strip()[:120] or None
    with get_conn() as c:
        row = c.execute("SELECT 1 FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if not row:
            return False
        c.execute(
            "UPDATE sessions SET participant_name = ? WHERE id = ?",
            (cleaned, session_id),
        )
    return True


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